#!/usr/bin/env python3
"""
trAIner CLI.

AI-powered workout analysis with training load and fitness metrics.

Usage:
    trainer setup --max-hr 185 --rest-hr 50
    trainer enrich --days 30
    trainer fitness --days 7
    trainer status
    trainer today           # Get today's training recommendation
    trainer summary --days 7    # Weekly training summary
    trainer why             # Explain today's recommendation
    trainer trends --weeks 4    # Show fitness trends
    trainer week --weeks 1      # Detailed weekly analysis
    trainer goal             # Show/set race goals
    trainer dashboard        # Complete training dashboard
"""

import argparse
import sys
import json
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.text import Text
from rich import box

from .db.database import TrainingDatabase
from .services.enrichment import EnrichmentService
from .services.coach import CoachService
from .metrics.zones import calculate_hr_zones_karvonen, estimate_max_hr_from_age
from .analysis.trends import (
    calculate_fitness_trend,
    detect_overtraining_signals,
    generate_ascii_chart,
)
from .analysis.weekly import (
    analyze_week,
    format_weekly_summary,
    generate_zone_bar_chart,
)
from .analysis.goals import (
    RaceDistance,
    RaceGoal,
    calculate_training_paces,
    assess_goal_progress,
    format_goal_progress,
    parse_time,
)

console = Console()


def get_risk_color(risk_zone: str) -> str:
    """Get rich color for risk zone."""
    colors = {
        "optimal": "green",
        "undertrained": "blue",
        "caution": "yellow",
        "danger": "red",
    }
    return colors.get(risk_zone, "white")


def get_zone_color(zone: str) -> str:
    """Get rich color for readiness zone."""
    colors = {
        "green": "green",
        "yellow": "yellow",
        "red": "red",
    }
    return colors.get(zone, "white")


def format_tsb_rich(tsb: float) -> Text:
    """Format TSB with rich colors."""
    if tsb > 25:
        color = "green"
        status = "Fresh"
    elif tsb > 0:
        color = "green"
        status = "Positive"
    elif tsb > -10:
        color = "yellow"
        status = "Neutral"
    elif tsb > -25:
        color = "yellow"
        status = "Fatigued"
    else:
        color = "red"
        status = "Very Fatigued"
    return Text(f"{tsb:+.1f} ({status})", style=color)


def cmd_setup(args, db: TrainingDatabase):
    """Configure user profile for personalized metrics."""
    console.print()
    console.print(Panel("[bold]trAIner - Profile Setup[/bold]"))
    console.print()

    # Get current profile
    profile = db.get_user_profile()

    # Interactive setup if no arguments provided
    if not any([args.max_hr, args.rest_hr, args.threshold_hr, args.age]):
        table = Table(title="Current Profile", box=box.ROUNDED)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Max HR", str(profile.max_hr))
        table.add_row("Rest HR", str(profile.rest_hr))
        table.add_row("Threshold HR", str(profile.threshold_hr))
        table.add_row("Age", str(profile.age))
        table.add_row("Gender", profile.gender)

        console.print(table)
        console.print()
        console.print("To update, use options like:")
        console.print("  trainer setup --max-hr 185 --rest-hr 50 --age 35")
        return

    # Update profile with provided values
    updated = db.update_user_profile(
        max_hr=args.max_hr,
        rest_hr=args.rest_hr,
        threshold_hr=args.threshold_hr,
        age=args.age,
        gender=args.gender,
    )

    # If age provided but not max_hr, estimate it
    if args.age and not args.max_hr:
        estimated_max = estimate_max_hr_from_age(args.age)
        console.print(f"[yellow]Estimated max HR from age: {estimated_max}[/yellow]")
        console.print("(Use --max-hr to override if you know your actual max)")
        console.print()

    console.print("[green]Profile updated![/green]")
    console.print()

    # Show updated profile
    table = Table(title="Updated Profile", box=box.ROUNDED)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Max HR", str(updated.max_hr))
    table.add_row("Rest HR", str(updated.rest_hr))
    table.add_row("Threshold HR", str(updated.threshold_hr))
    table.add_row("Age", str(updated.age))
    table.add_row("Gender", updated.gender)

    console.print(table)
    console.print()

    # Show calculated zones
    if updated.max_hr and updated.rest_hr:
        zones = calculate_hr_zones_karvonen(updated.max_hr, updated.rest_hr)

        zone_table = Table(title="Heart Rate Zones (Karvonen method)", box=box.ROUNDED)
        zone_table.add_column("Zone", style="cyan")
        zone_table.add_column("Name", style="white")
        zone_table.add_column("Range", style="green")

        zone_table.add_row("1", "Recovery", f"{zones.zone1[0]}-{zones.zone1[1]} bpm")
        zone_table.add_row("2", "Aerobic", f"{zones.zone2[0]}-{zones.zone2[1]} bpm")
        zone_table.add_row("3", "Tempo", f"{zones.zone3[0]}-{zones.zone3[1]} bpm")
        zone_table.add_row("4", "Threshold", f"{zones.zone4[0]}-{zones.zone4[1]} bpm")
        zone_table.add_row("5", "VO2max", f"{zones.zone5[0]}-{zones.zone5[1]} bpm")

        console.print(zone_table)
    console.print()


def cmd_enrich(args, db: TrainingDatabase):
    """Enrich activities with training metrics (HRSS, TRIMP, zones)."""
    console.print()
    console.print(Panel("[bold]trAIner - Enrichment[/bold]"))
    console.print()

    service = EnrichmentService(training_db=db)

    # Check for n8n database
    if not service.n8n_db_path:
        console.print("[yellow]Warning: n8n database not found.[/yellow]")
        console.print("Set N8N_DB_PATH environment variable to point to your n8n database.")
        console.print()
        console.print("Example:")
        console.print("  export N8N_DB_PATH=~/.n8n/database.sqlite")
        console.print()
        return

    console.print(f"Reading activities from: {service.n8n_db_path}")
    console.print(f"Processing last {args.days} days...")
    console.print()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Enriching activities...", total=None)
            result = service.run_full_enrichment(
                days=args.days,
                load_metric=args.metric,
            )
            progress.update(task, completed=True)

        # Show results
        table = Table(title="Enrichment Results", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")

        table.add_row("Activities processed", str(result['activities_processed']))
        table.add_row("Activities enriched", str(result['activities_enriched']))
        table.add_row("Fitness days calculated", str(result['fitness_days_calculated']))

        console.print(table)
        console.print()

        if result['activities_enriched'] > 0:
            console.print("[green]Enrichment complete![/green]")
            console.print("Run 'trainer fitness' to see your fitness metrics.")
        else:
            console.print("[yellow]No activities enriched.[/yellow]")
            console.print("Make sure you have activities in the n8n raw_activities table.")

    except Exception as e:
        console.print(f"[red]Error during enrichment: {e}[/red]")
        sys.exit(1)

    console.print()


def cmd_fitness(args, db: TrainingDatabase):
    """Show fitness metrics (CTL, ATL, TSB, ACWR)."""
    console.print()
    console.print(Panel("[bold]trAIner - Fitness Metrics[/bold]"))
    console.print()

    # Get date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=args.days)

    metrics = db.get_fitness_range(start_date.isoformat(), end_date.isoformat())

    if not metrics:
        console.print("No fitness data available.")
        console.print("Run 'trainer enrich' first to calculate metrics.")
        console.print()
        return

    # Create table
    table = Table(title=f"Fitness Metrics (Last {args.days} Days)", box=box.ROUNDED)
    table.add_column("Date", style="cyan")
    table.add_column("Load", justify="right")
    table.add_column("CTL", justify="right")
    table.add_column("ATL", justify="right")
    table.add_column("TSB", justify="right")
    table.add_column("ACWR", justify="right")
    table.add_column("Risk", style="bold")

    for m in metrics:
        risk_color = get_risk_color(m.risk_zone)
        tsb_color = "green" if m.tsb > 0 else "yellow" if m.tsb > -10 else "red"

        table.add_row(
            m.date,
            f"{m.daily_load:.1f}",
            f"{m.ctl:.1f}",
            f"{m.atl:.1f}",
            Text(f"{m.tsb:+.1f}", style=tsb_color),
            f"{m.acwr:.2f}",
            Text(m.risk_zone.upper(), style=risk_color),
        )

    console.print(table)
    console.print()

    # Legend
    legend = Table(title="Legend", box=box.SIMPLE, show_header=False)
    legend.add_column("Term")
    legend.add_column("Description")
    legend.add_row("CTL", "Chronic Training Load (fitness, 42-day)")
    legend.add_row("ATL", "Acute Training Load (fatigue, 7-day)")
    legend.add_row("TSB", "Training Stress Balance (form = CTL - ATL)")
    legend.add_row("ACWR", "Acute:Chronic Workload Ratio (injury risk)")

    console.print(legend)
    console.print()


def cmd_status(args, db: TrainingDatabase):
    """Show current training status and risk zone."""
    console.print()
    console.print(Panel("[bold]trAIner - Status[/bold]"))
    console.print()

    # Get latest fitness metrics
    latest = db.get_latest_fitness_metrics()

    if not latest:
        console.print("No fitness data available yet.")
        console.print()
        console.print("To get started:")
        console.print("  1. Setup your profile: trainer setup --max-hr 185 --rest-hr 50")
        console.print("  2. Enrich activities:  trainer enrich --days 30")
        console.print()
        return

    # Status panel
    risk_color = get_risk_color(latest.risk_zone)

    status_text = f"""
[cyan]Date:[/cyan]           {latest.date}

[cyan]Fitness (CTL):[/cyan]  {latest.ctl:.1f}
[cyan]Fatigue (ATL):[/cyan]  {latest.atl:.1f}
[cyan]Form (TSB):[/cyan]     {format_tsb_rich(latest.tsb)}
[cyan]ACWR:[/cyan]           {latest.acwr:.2f}

[cyan]Risk Zone:[/cyan]      [{risk_color}]{latest.risk_zone.upper()}[/{risk_color}]
"""

    console.print(Panel(status_text, title="Current Status", box=box.ROUNDED))

    # Training recommendation
    if latest.acwr > 1.5:
        console.print("[red]Recommendation: High injury risk. Reduce training load.[/red]")
    elif latest.acwr > 1.3:
        console.print("[yellow]Recommendation: Elevated risk. Consider an easy day.[/yellow]")
    elif latest.acwr < 0.8:
        console.print("[blue]Recommendation: Undertrained. Safe to increase load.[/blue]")
    else:
        if latest.tsb > 10:
            console.print("[green]Recommendation: Fresh! Good day for a hard workout.[/green]")
        elif latest.tsb > -10:
            console.print("[green]Recommendation: Optimal zone. Moderate training OK.[/green]")
        else:
            console.print("[yellow]Recommendation: Fatigued. Consider recovery.[/yellow]")

    console.print()

    # Today's activities
    today = datetime.now().date().isoformat()
    today_activities = db.get_activities_for_date(today)

    if today_activities:
        total_load = sum(a.hrss or 0 for a in today_activities)
        console.print(f"Today's activities: {len(today_activities)}")
        console.print(f"Today's load (HRSS): {total_load:.1f}")
    else:
        console.print("No activities recorded today.")

    console.print()


def cmd_stats(args, db: TrainingDatabase):
    """Show database statistics."""
    stats = db.get_stats()

    console.print()
    console.print(Panel("[bold]trAIner - Database Stats[/bold]"))
    console.print()

    table = Table(box=box.ROUNDED)
    table.add_column("Statistic", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Database", str(stats['db_path']))
    table.add_row("Total activities", str(stats['total_activities']))
    table.add_row("Total fitness days", str(stats['total_fitness_days']))

    if stats['activity_date_range']['earliest']:
        table.add_row(
            "Activity range",
            f"{stats['activity_date_range']['earliest']} to {stats['activity_date_range']['latest']}"
        )

    if stats['fitness_date_range']['earliest']:
        table.add_row(
            "Fitness range",
            f"{stats['fitness_date_range']['earliest']} to {stats['fitness_date_range']['latest']}"
        )

    console.print(table)
    console.print()


def cmd_today(args, db: TrainingDatabase):
    """Get today's training recommendation."""
    console.print()
    console.print(Panel("[bold]trAIner - Today's Briefing[/bold]"))
    console.print()

    coach = CoachService(training_db=db)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing...", total=None)
            briefing = coach.get_daily_briefing()
            progress.update(task, completed=True)
    except Exception as e:
        console.print(f"[red]Error getting briefing: {e}[/red]")
        sys.exit(1)

    # Data availability
    sources = briefing["data_sources"]
    if not sources["wellness_available"] and not sources["fitness_available"]:
        console.print("[yellow]Limited data available.[/yellow]")
        console.print("For better recommendations:")
        console.print("  - Run 'trainer enrich' for training load data")
        console.print("  - Set WELLNESS_DB_PATH for recovery data")
        console.print()

    # Readiness section
    readiness = briefing["readiness"]
    zone_color = get_zone_color(readiness["zone"])

    # Create readiness panel
    readiness_text = f"""
[cyan]Date:[/cyan]           {briefing['date']}
[cyan]Readiness:[/cyan]      [{zone_color}]{readiness['score']:.0f}/100 ({readiness['zone'].upper()})[/{zone_color}]
"""

    console.print(Panel(readiness_text, title="Readiness", box=box.ROUNDED))

    # Recommendation section
    rec = briefing["recommendation"]
    workout_type = rec["workout_type"].upper()

    rec_text = f"""
[bold cyan]Recommended:[/bold cyan]    [bold]{workout_type}[/bold]
[cyan]Duration:[/cyan]       {rec['duration_min']} minutes
[cyan]Intensity:[/cyan]      {rec['intensity_description']}
"""
    if rec["hr_zone_target"]:
        rec_text += f"[cyan]Target:[/cyan]         {rec['hr_zone_target']}\n"

    rec_text += f"\n[cyan]Reason:[/cyan]         {rec['reason']}"

    console.print(Panel(rec_text, title="Workout Recommendation", box=box.ROUNDED))

    # Alternatives
    if rec["alternatives"]:
        console.print(f"[dim]Alternatives: {', '.join(rec['alternatives'])}[/dim]")

    # Warnings
    if rec["warnings"]:
        for warning in rec["warnings"]:
            console.print(f"[yellow]! {warning}[/yellow]")

    console.print()

    # Training status (if available)
    if briefing["training_status"]:
        ts = briefing["training_status"]
        status_text = f"CTL: {ts['ctl']:.1f}  |  ATL: {ts['atl']:.1f}  |  TSB: {ts['tsb']:+.1f}  |  ACWR: {ts['acwr']:.2f}"
        console.print(f"[dim]Training Status: {status_text}[/dim]")

    # Weekly load
    wl = briefing["weekly_load"]
    if wl["target"] > 0:
        pct = (wl["current"] / wl["target"]) * 100
        console.print(f"[dim]Weekly Load: {wl['current']:.0f} / {wl['target']:.0f} ({pct:.0f}%)[/dim]")

    console.print()

    # Narrative
    console.print(Panel(briefing['narrative'], title="Summary", box=box.ROUNDED))
    console.print()


def cmd_summary(args, db: TrainingDatabase):
    """Show weekly training summary."""
    console.print()
    console.print(Panel("[bold]trAIner - Weekly Summary[/bold]"))
    console.print()

    coach = CoachService(training_db=db)

    try:
        # Calculate weeks_back from days
        weeks_back = 0
        if args.days > 7:
            weeks_back = (args.days - 1) // 7

        summary = coach.get_weekly_summary(weeks_back=weeks_back)
    except Exception as e:
        console.print(f"[red]Error getting summary: {e}[/red]")
        sys.exit(1)

    # Week header
    console.print(f"Week: {summary['week_start']} to {summary['week_end']}")
    console.print()

    # Stats table
    table = Table(box=box.ROUNDED, show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Total Load", f"{summary['total_load']:.0f}")
    if summary['target_load'] > 0:
        pct = (summary['total_load'] / summary['target_load']) * 100
        table.add_row("Target Load", f"{summary['target_load']:.0f} ({pct:.0f}% achieved)")
    table.add_row("Workouts", str(summary['workout_count']))
    table.add_row("Duration", f"{summary['total_duration_min']:.0f} minutes")
    table.add_row("Distance", f"{summary['total_distance_km']:.1f} km")

    console.print(table)
    console.print()

    # Distribution
    dist_table = Table(title="Weekly Distribution", box=box.ROUNDED, show_header=False)
    dist_table.add_column("Type")
    dist_table.add_column("Count")

    dist_table.add_row("Hard days", str(summary['hard_days']))
    dist_table.add_row("Easy days", str(summary['easy_days']))
    dist_table.add_row("Rest days", str(summary['rest_days']))

    console.print(dist_table)
    console.print()

    # Fitness change
    if summary['ctl_start'] > 0 or summary['ctl_end'] > 0:
        change = summary['ctl_change']
        if change > 0:
            change_color = "green"
            change_symbol = "+"
        elif change < 0:
            change_color = "red"
            change_symbol = ""
        else:
            change_color = "white"
            change_symbol = ""

        console.print(
            f"[cyan]Fitness Change:[/cyan] {summary['ctl_start']:.1f} -> {summary['ctl_end']:.1f} "
            f"[{change_color}]({change_symbol}{change:.1f})[/{change_color}]"
        )
        console.print()

    # Narrative
    console.print(Panel(summary['narrative'], title="Summary", box=box.ROUNDED))
    console.print()


def cmd_why(args, db: TrainingDatabase):
    """Explain why today's workout was recommended."""
    console.print()
    console.print(Panel("[bold]trAIner - Recommendation Explained[/bold]"))
    console.print()

    coach = CoachService(training_db=db)

    try:
        explanation = coach.get_why_explanation()
    except Exception as e:
        console.print(f"[red]Error generating explanation: {e}[/red]")
        sys.exit(1)

    console.print(explanation)
    console.print()


def cmd_trends(args, db: TrainingDatabase):
    """Show fitness trends over time."""
    console.print()
    console.print(Panel("[bold]trAIner - Fitness Trends[/bold]"))
    console.print()

    # Get fitness history
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=args.weeks * 7)

    fitness_data = db.get_fitness_range(start_date.isoformat(), end_date.isoformat())

    if not fitness_data:
        console.print("No fitness data available for trend analysis.")
        console.print("Run 'trainer enrich' first.")
        console.print()
        return

    # Convert to dict format
    fitness_history = [m.to_dict() for m in fitness_data]

    # Calculate fitness trend
    trend = calculate_fitness_trend(fitness_history, period_days=args.weeks * 7)

    if trend:
        # Trend summary
        direction_color = {
            "improving": "green",
            "maintaining": "yellow",
            "declining": "red",
        }.get(trend.trend_direction, "white")

        trend_table = Table(title="Fitness Trend", box=box.ROUNDED)
        trend_table.add_column("Metric", style="cyan")
        trend_table.add_column("Value", style="white")

        trend_table.add_row("Period", f"{trend.period_start} to {trend.period_end}")
        trend_table.add_row("CTL Start", f"{trend.ctl_start:.1f}")
        trend_table.add_row("CTL End", f"{trend.ctl_end:.1f}")
        trend_table.add_row(
            "CTL Change",
            Text(f"{trend.ctl_change:+.1f} ({trend.ctl_change_pct:+.1f}%)", style=direction_color)
        )
        trend_table.add_row("Weekly Load Avg", f"{trend.weekly_load_avg:.0f}")
        trend_table.add_row("Trend", Text(trend.trend_direction.upper(), style=direction_color))

        console.print(trend_table)
        console.print()

    # CTL Chart
    ctl_values = [m.ctl for m in reversed(fitness_data)]
    ctl_dates = [m.date[-5:] for m in reversed(fitness_data)]  # MM-DD format

    if len(ctl_values) > 3:
        chart = generate_ascii_chart(
            ctl_values,
            ctl_dates,
            title=f"CTL Trend (Last {args.weeks} Weeks)",
            height=8,
        )
        console.print(Panel(chart, box=box.ROUNDED))
        console.print()

    # Check for overtraining signals
    coach = CoachService(training_db=db)
    wellness_history = []

    # Try to get wellness data
    try:
        for i in range(min(14, len(fitness_data))):
            day = end_date - timedelta(days=i)
            wellness = coach.get_wellness_data(day.isoformat())
            if wellness:
                wellness_history.append(wellness)
    except Exception:
        pass

    signals = detect_overtraining_signals(fitness_history, wellness_history)

    if signals:
        console.print("[bold red]Warning Signals Detected:[/bold red]")
        for signal in signals:
            console.print(f"  [yellow]![/yellow] {signal}")
        console.print()
    else:
        console.print("[green]No overtraining signals detected.[/green]")
        console.print()


def cmd_week(args, db: TrainingDatabase):
    """Show detailed weekly analysis."""
    console.print()
    console.print(Panel("[bold]trAIner - Weekly Analysis[/bold]"))
    console.print()

    # Calculate week dates
    today = date.today()
    current_monday = today - timedelta(days=today.weekday())
    target_monday = current_monday - timedelta(weeks=args.weeks - 1)
    target_sunday = target_monday + timedelta(days=6)

    # Get activities
    activities = db.get_activities_range(
        target_monday.isoformat(),
        target_sunday.isoformat(),
    )

    # Get fitness metrics
    fitness_data = db.get_fitness_range(
        target_monday.isoformat(),
        target_sunday.isoformat(),
    )

    fitness_dicts = [m.to_dict() for m in fitness_data]
    activity_dicts = [a.to_dict() for a in activities]

    # Analyze the week
    analysis = analyze_week(
        activities=activity_dicts,
        fitness_metrics=fitness_dicts,
    )

    # Display formatted summary
    console.print(format_weekly_summary(analysis))
    console.print()

    # Zone distribution bar chart
    if analysis.activity_count > 0:
        console.print(Panel(generate_zone_bar_chart(analysis), box=box.ROUNDED))
        console.print()


def cmd_goal(args, db: TrainingDatabase):
    """Set or show race goals."""
    console.print()
    console.print(Panel("[bold]trAIner - Race Goals[/bold]"))
    console.print()

    # If setting a new goal
    if args.distance and args.target and args.date:
        # Parse distance
        distance = RaceDistance.from_string(args.distance)
        if not distance:
            console.print(f"[red]Unknown distance: {args.distance}[/red]")
            console.print("Valid options: 5k, 10k, half, marathon")
            return

        # Parse target time
        try:
            target_sec = parse_time(args.target)
        except ValueError as e:
            console.print(f"[red]Invalid time format: {e}[/red]")
            console.print("Use format like '1:45:00' or '25:00'")
            return

        # Parse date
        try:
            race_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            console.print("[red]Invalid date format. Use YYYY-MM-DD[/red]")
            return

        # Save goal
        goal_id = db.save_race_goal(
            race_date=race_date.isoformat(),
            distance=distance.value,
            target_time_sec=target_sec,
            notes=args.notes,
        )

        console.print(f"[green]Goal saved! (ID: {goal_id})[/green]")
        console.print()

        # Show training paces
        goal = RaceGoal(
            race_date=race_date,
            distance=distance,
            target_time_sec=target_sec,
        )

        paces = calculate_training_paces(goal)

        pace_table = Table(title="Training Paces", box=box.ROUNDED)
        pace_table.add_column("Type", style="cyan")
        pace_table.add_column("Pace", style="green")
        pace_table.add_column("Description")

        for pace_type, info in paces.items():
            pace_table.add_row(
                info["name"],
                info["pace_formatted"],
                info["description"][:40] + "..." if len(info["description"]) > 40 else info["description"]
            )

        console.print(pace_table)
        console.print()

    else:
        # Show existing goals
        goals = db.get_race_goals(upcoming_only=True)

        if not goals:
            console.print("No upcoming race goals set.")
            console.print()
            console.print("To set a goal:")
            console.print("  trainer goal --distance half --target 1:45:00 --date 2025-04-15")
            console.print()
            return

        # Display goals
        for goal_data in goals:
            distance = RaceDistance.from_string(str(goal_data['distance']))
            if not distance:
                # Try to match by value
                for rd in RaceDistance:
                    if abs(rd.value - float(goal_data['distance'])) < 0.1:
                        distance = rd
                        break

            if not distance:
                continue

            goal = RaceGoal(
                race_date=datetime.strptime(goal_data['race_date'], "%Y-%m-%d").date(),
                distance=distance,
                target_time_sec=goal_data['target_time_sec'],
            )

            # Get current fitness
            coach = CoachService(training_db=db)
            fitness = coach.get_fitness_metrics()
            activities = coach.get_recent_activities(days=30)

            progress = assess_goal_progress(
                goal=goal,
                current_fitness=fitness or {},
                recent_activities=activities,
            )

            console.print(Panel(format_goal_progress(progress), box=box.ROUNDED))
            console.print()


def cmd_dashboard(args, db: TrainingDatabase):
    """Show complete training dashboard."""
    console.print()
    console.print(Panel("[bold]trAIner - Dashboard[/bold]", style="cyan"))
    console.print()

    coach = CoachService(training_db=db)

    # Get today's briefing
    try:
        briefing = coach.get_daily_briefing()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    # Create layout with multiple panels

    # 1. Today's Recommendation (main focus)
    readiness = briefing["readiness"]
    rec = briefing["recommendation"]
    zone_color = get_zone_color(readiness["zone"])

    today_text = f"""
[bold]Readiness:[/bold] [{zone_color}]{readiness['score']:.0f}/100[/{zone_color}] ({readiness['zone'].upper()})

[bold]Today's Workout:[/bold]
  Type: [cyan]{rec['workout_type'].upper()}[/cyan]
  Duration: {rec['duration_min']} min
  {rec['intensity_description']}
"""
    console.print(Panel(today_text, title="Today", box=box.ROUNDED))

    # 2. Current Fitness Status
    if briefing["training_status"]:
        ts = briefing["training_status"]
        risk_color = get_risk_color(ts['risk_zone'])

        fitness_text = f"""
CTL (Fitness):  {ts['ctl']:.1f}
ATL (Fatigue):  {ts['atl']:.1f}
TSB (Form):     {ts['tsb']:+.1f}
ACWR:           {ts['acwr']:.2f}
Risk Zone:      [{risk_color}]{ts['risk_zone'].upper()}[/{risk_color}]
"""
        console.print(Panel(fitness_text, title="Fitness Status", box=box.ROUNDED))

    # 3. Weekly Progress
    wl = briefing["weekly_load"]
    if wl["target"] > 0:
        pct = (wl["current"] / wl["target"]) * 100
        bar_width = 30
        filled = int((pct / 100) * bar_width)
        filled = min(filled, bar_width)

        bar = "[green]" + "#" * filled + "[/green]" + "[dim]" + "-" * (bar_width - filled) + "[/dim]"

        weekly_text = f"""
Weekly Load: {wl['current']:.0f} / {wl['target']:.0f} ({pct:.0f}%)
[{bar}]
Workouts: {wl['workout_count']}
"""
        console.print(Panel(weekly_text, title="This Week", box=box.ROUNDED))

    # 4. Upcoming Goals
    goals = db.get_race_goals(upcoming_only=True)
    if goals:
        goal_lines = []
        for g in goals[:2]:  # Show max 2 goals
            goal_lines.append(f"  {g['race_date']}: {g['distance']}K target")

        goal_text = "\n".join(goal_lines)
        console.print(Panel(goal_text, title="Upcoming Goals", box=box.ROUNDED))

    # 5. Summary narrative
    console.print()
    console.print(f"[italic]{briefing['narrative']}[/italic]")
    console.print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="trAIner - AI-powered workout analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  trainer setup --max-hr 185 --rest-hr 50 --age 35
  trainer enrich --days 30
  trainer fitness --days 7
  trainer status
  trainer today
  trainer summary --days 7
  trainer why
  trainer trends --weeks 4
  trainer week --weeks 1
  trainer goal --distance half --target 1:45:00 --date 2025-04-15
  trainer dashboard
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command
    setup_p = subparsers.add_parser("setup", help="Configure user profile")
    setup_p.add_argument("--max-hr", type=int, help="Maximum heart rate")
    setup_p.add_argument("--rest-hr", type=int, help="Resting heart rate")
    setup_p.add_argument("--threshold-hr", type=int, help="Threshold heart rate (LTHR)")
    setup_p.add_argument("--age", type=int, help="Age in years")
    setup_p.add_argument(
        "--gender",
        choices=["male", "female"],
        help="Gender (affects TRIMP calculation)",
    )

    # Enrich command
    enrich_p = subparsers.add_parser(
        "enrich", help="Enrich activities with training metrics"
    )
    enrich_p.add_argument(
        "--days", "-d", type=int, default=30, help="Number of days to process"
    )
    enrich_p.add_argument(
        "--metric",
        choices=["hrss", "trimp"],
        default="hrss",
        help="Load metric to use for fitness calculation",
    )

    # Fitness command
    fitness_p = subparsers.add_parser("fitness", help="Show fitness metrics")
    fitness_p.add_argument(
        "--days", "-d", type=int, default=7, help="Number of days to show"
    )

    # Status command
    subparsers.add_parser("status", help="Show current training status")

    # Stats command
    subparsers.add_parser("stats", help="Show database statistics")

    # Today command
    subparsers.add_parser("today", help="Get today's training recommendation")

    # Summary command
    summary_p = subparsers.add_parser("summary", help="Show weekly training summary")
    summary_p.add_argument(
        "--days", "-d", type=int, default=7, help="Days to summarize"
    )

    # Why command
    subparsers.add_parser("why", help="Explain why today's workout was recommended")

    # Trends command
    trends_p = subparsers.add_parser("trends", help="Show fitness trends over time")
    trends_p.add_argument(
        "--weeks", "-w", type=int, default=4, help="Number of weeks to analyze"
    )

    # Week command
    week_p = subparsers.add_parser("week", help="Show detailed weekly analysis")
    week_p.add_argument(
        "--weeks", "-w", type=int, default=1, help="Weeks back (1 = current week)"
    )

    # Goal command
    goal_p = subparsers.add_parser("goal", help="Set or show race goals")
    goal_p.add_argument(
        "--distance",
        type=str,
        help="Race distance (5k, 10k, half, marathon)"
    )
    goal_p.add_argument(
        "--target",
        type=str,
        help="Target time (e.g., '1:45:00' or '25:00')"
    )
    goal_p.add_argument(
        "--date",
        type=str,
        help="Race date (YYYY-MM-DD)"
    )
    goal_p.add_argument(
        "--notes",
        type=str,
        help="Optional notes about the goal"
    )

    # Dashboard command
    subparsers.add_parser("dashboard", help="Show complete training dashboard")

    args = parser.parse_args()

    # Initialize database
    db = TrainingDatabase()

    # Route to appropriate command
    if args.command == "setup":
        cmd_setup(args, db)
    elif args.command == "enrich":
        cmd_enrich(args, db)
    elif args.command == "fitness":
        cmd_fitness(args, db)
    elif args.command == "status":
        cmd_status(args, db)
    elif args.command == "stats":
        cmd_stats(args, db)
    elif args.command == "today":
        cmd_today(args, db)
    elif args.command == "summary":
        cmd_summary(args, db)
    elif args.command == "why":
        cmd_why(args, db)
    elif args.command == "trends":
        cmd_trends(args, db)
    elif args.command == "week":
        cmd_week(args, db)
    elif args.command == "goal":
        cmd_goal(args, db)
    elif args.command == "dashboard":
        cmd_dashboard(args, db)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
