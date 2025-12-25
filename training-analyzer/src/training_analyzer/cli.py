#!/usr/bin/env python3
"""
Training Analyzer CLI.

AI-powered workout analysis with training load and fitness metrics.

Usage:
    training-analyzer setup --max-hr 185 --rest-hr 50
    training-analyzer enrich --days 30
    training-analyzer fitness --days 7
    training-analyzer status
    training-analyzer today           # Get today's training recommendation
    training-analyzer summary --days 7    # Weekly training summary
    training-analyzer why             # Explain today's recommendation
"""

import argparse
import sys
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional

from .db.database import TrainingDatabase
from .services.enrichment import EnrichmentService
from .services.coach import CoachService
from .metrics.zones import calculate_hr_zones_karvonen, estimate_max_hr_from_age


# ANSI color codes
class Colors:
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def get_risk_color(risk_zone: str) -> str:
    """Get color for risk zone."""
    colors = {
        "optimal": Colors.GREEN,
        "undertrained": Colors.BLUE,
        "caution": Colors.YELLOW,
        "danger": Colors.RED,
    }
    return colors.get(risk_zone, Colors.RESET)


def get_zone_color(zone: str) -> str:
    """Get color for readiness zone."""
    colors = {
        "green": Colors.GREEN,
        "yellow": Colors.YELLOW,
        "red": Colors.RED,
    }
    return colors.get(zone, Colors.RESET)


def format_tsb(tsb: float) -> str:
    """Format TSB with color."""
    if tsb > 25:
        color = Colors.GREEN
        status = "Fresh"
    elif tsb > 0:
        color = Colors.GREEN
        status = "Positive"
    elif tsb > -10:
        color = Colors.YELLOW
        status = "Neutral"
    elif tsb > -25:
        color = Colors.YELLOW
        status = "Fatigued"
    else:
        color = Colors.RED
        status = "Very Fatigued"
    return f"{color}{tsb:+.1f} ({status}){Colors.RESET}"


def cmd_setup(args, db: TrainingDatabase):
    """Configure user profile for personalized metrics."""
    print()
    print(f"{Colors.BOLD}Training Analyzer - Profile Setup{Colors.RESET}")
    print("=" * 40)
    print()

    # Get current profile
    profile = db.get_user_profile()

    # Interactive setup if no arguments provided
    if not any([args.max_hr, args.rest_hr, args.threshold_hr, args.age]):
        print("Current profile:")
        print(f"  Max HR: {profile.max_hr}")
        print(f"  Rest HR: {profile.rest_hr}")
        print(f"  Threshold HR: {profile.threshold_hr}")
        print(f"  Age: {profile.age}")
        print(f"  Gender: {profile.gender}")
        print()
        print("To update, use options like:")
        print("  training-analyzer setup --max-hr 185 --rest-hr 50 --age 35")
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
        print(f"Estimated max HR from age: {estimated_max}")
        print("(Use --max-hr to override if you know your actual max)")

    print("Profile updated:")
    print(f"  Max HR: {updated.max_hr}")
    print(f"  Rest HR: {updated.rest_hr}")
    print(f"  Threshold HR: {updated.threshold_hr}")
    print(f"  Age: {updated.age}")
    print(f"  Gender: {updated.gender}")
    print()

    # Show calculated zones
    if updated.max_hr and updated.rest_hr:
        zones = calculate_hr_zones_karvonen(updated.max_hr, updated.rest_hr)
        print("Heart Rate Zones (Karvonen method):")
        print(f"  Zone 1 (Recovery):  {zones.zone1[0]}-{zones.zone1[1]} bpm")
        print(f"  Zone 2 (Aerobic):   {zones.zone2[0]}-{zones.zone2[1]} bpm")
        print(f"  Zone 3 (Tempo):     {zones.zone3[0]}-{zones.zone3[1]} bpm")
        print(f"  Zone 4 (Threshold): {zones.zone4[0]}-{zones.zone4[1]} bpm")
        print(f"  Zone 5 (VO2max):    {zones.zone5[0]}-{zones.zone5[1]} bpm")
    print()


def cmd_enrich(args, db: TrainingDatabase):
    """Enrich activities with training metrics (HRSS, TRIMP, zones)."""
    print()
    print(f"{Colors.BOLD}Training Analyzer - Enrichment{Colors.RESET}")
    print("=" * 40)
    print()

    service = EnrichmentService(training_db=db)

    # Check for n8n database
    if not service.n8n_db_path:
        print(f"{Colors.YELLOW}Warning: n8n database not found.{Colors.RESET}")
        print("Set N8N_DB_PATH environment variable to point to your n8n database.")
        print()
        print("Example:")
        print("  export N8N_DB_PATH=~/.n8n/database.sqlite")
        print()
        return

    print(f"Reading activities from: {service.n8n_db_path}")
    print(f"Processing last {args.days} days...")
    print()

    try:
        result = service.run_full_enrichment(
            days=args.days,
            load_metric=args.metric,
        )

        print(f"Activities processed: {result['activities_processed']}")
        print(f"Activities enriched:  {result['activities_enriched']}")
        print(f"Fitness days calc:    {result['fitness_days_calculated']}")
        print()

        if result['activities_enriched'] > 0:
            print(f"{Colors.GREEN}Enrichment complete!{Colors.RESET}")
            print("Run 'training-analyzer fitness' to see your fitness metrics.")
        else:
            print(f"{Colors.YELLOW}No activities enriched.{Colors.RESET}")
            print("Make sure you have activities in the n8n raw_activities table.")

    except Exception as e:
        print(f"{Colors.RED}Error during enrichment: {e}{Colors.RESET}")
        sys.exit(1)

    print()


def cmd_fitness(args, db: TrainingDatabase):
    """Show fitness metrics (CTL, ATL, TSB, ACWR)."""
    print()
    print(f"{Colors.BOLD}Training Analyzer - Fitness Metrics{Colors.RESET}")
    print("=" * 50)
    print()

    # Get date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=args.days)

    metrics = db.get_fitness_range(start_date.isoformat(), end_date.isoformat())

    if not metrics:
        print("No fitness data available.")
        print("Run 'training-analyzer enrich' first to calculate metrics.")
        print()
        return

    # Print header
    print(f"{'Date':<12} {'Load':>7} {'CTL':>7} {'ATL':>7} {'TSB':>8} {'ACWR':>6} {'Risk':<12}")
    print("-" * 65)

    # Print each day
    for m in metrics:
        risk_color = get_risk_color(m.risk_zone)
        tsb_str = f"{m.tsb:+.1f}"

        print(
            f"{m.date:<12} "
            f"{m.daily_load:>7.1f} "
            f"{m.ctl:>7.1f} "
            f"{m.atl:>7.1f} "
            f"{tsb_str:>8} "
            f"{m.acwr:>6.2f} "
            f"{risk_color}{m.risk_zone:<12}{Colors.RESET}"
        )

    print()
    print("Legend:")
    print(f"  CTL = Chronic Training Load (fitness, 42-day)")
    print(f"  ATL = Acute Training Load (fatigue, 7-day)")
    print(f"  TSB = Training Stress Balance (form = CTL - ATL)")
    print(f"  ACWR = Acute:Chronic Workload Ratio (injury risk)")
    print()


def cmd_status(args, db: TrainingDatabase):
    """Show current training status and risk zone."""
    print()
    print(f"{Colors.BOLD}Training Analyzer - Status{Colors.RESET}")
    print("=" * 40)
    print()

    # Get profile
    profile = db.get_user_profile()

    # Get latest fitness metrics
    latest = db.get_latest_fitness_metrics()

    if not latest:
        print("No fitness data available yet.")
        print()
        print("To get started:")
        print("  1. Setup your profile: training-analyzer setup --max-hr 185 --rest-hr 50")
        print("  2. Enrich activities:  training-analyzer enrich --days 30")
        print()
        return

    # Get today's activities
    today = datetime.now().date().isoformat()
    today_activities = db.get_activities_for_date(today)

    # Display current status
    risk_color = get_risk_color(latest.risk_zone)

    print(f"  Date: {latest.date}")
    print()
    print(f"  {Colors.BOLD}Fitness (CTL):{Colors.RESET}  {latest.ctl:.1f}")
    print(f"  {Colors.BOLD}Fatigue (ATL):{Colors.RESET}  {latest.atl:.1f}")
    print(f"  {Colors.BOLD}Form (TSB):{Colors.RESET}     {format_tsb(latest.tsb)}")
    print(f"  {Colors.BOLD}ACWR:{Colors.RESET}           {latest.acwr:.2f}")
    print()
    print(f"  {Colors.BOLD}Risk Zone:{Colors.RESET}      {risk_color}{latest.risk_zone.upper()}{Colors.RESET}")
    print()

    # Training recommendation
    if latest.acwr > 1.5:
        print(f"  {Colors.RED}Recommendation: High injury risk. Reduce training load.{Colors.RESET}")
    elif latest.acwr > 1.3:
        print(f"  {Colors.YELLOW}Recommendation: Elevated risk. Consider an easy day.{Colors.RESET}")
    elif latest.acwr < 0.8:
        print(f"  {Colors.BLUE}Recommendation: Undertrained. Safe to increase load.{Colors.RESET}")
    else:
        if latest.tsb > 10:
            print(f"  {Colors.GREEN}Recommendation: Fresh! Good day for a hard workout.{Colors.RESET}")
        elif latest.tsb > -10:
            print(f"  {Colors.GREEN}Recommendation: Optimal zone. Moderate training OK.{Colors.RESET}")
        else:
            print(f"  {Colors.YELLOW}Recommendation: Fatigued. Consider recovery.{Colors.RESET}")

    print()

    # Today's activities
    if today_activities:
        total_load = sum(a.hrss or 0 for a in today_activities)
        print(f"  Today's activities: {len(today_activities)}")
        print(f"  Today's load (HRSS): {total_load:.1f}")
    else:
        print("  No activities recorded today.")

    print()


def cmd_stats(args, db: TrainingDatabase):
    """Show database statistics."""
    stats = db.get_stats()

    print()
    print(f"{Colors.BOLD}Training Analyzer - Database Stats{Colors.RESET}")
    print("=" * 40)
    print()
    print(f"Database: {stats['db_path']}")
    print(f"Total activities: {stats['total_activities']}")
    print(f"Total fitness days: {stats['total_fitness_days']}")

    if stats['activity_date_range']['earliest']:
        print(
            f"Activity range: {stats['activity_date_range']['earliest']} "
            f"to {stats['activity_date_range']['latest']}"
        )

    if stats['fitness_date_range']['earliest']:
        print(
            f"Fitness range: {stats['fitness_date_range']['earliest']} "
            f"to {stats['fitness_date_range']['latest']}"
        )
    print()


def cmd_today(args, db: TrainingDatabase):
    """Get today's training recommendation."""
    print()
    print(f"{Colors.BOLD}Training Analyzer - Today's Briefing{Colors.RESET}")
    print("=" * 50)
    print()

    coach = CoachService(training_db=db)

    try:
        briefing = coach.get_daily_briefing()
    except Exception as e:
        print(f"{Colors.RED}Error getting briefing: {e}{Colors.RESET}")
        sys.exit(1)

    # Data availability
    sources = briefing["data_sources"]
    if not sources["wellness_available"] and not sources["fitness_available"]:
        print(f"{Colors.YELLOW}Limited data available.{Colors.RESET}")
        print("For better recommendations:")
        print("  - Run 'training-analyzer enrich' for training load data")
        print("  - Set WELLNESS_DB_PATH for recovery data")
        print()

    # Readiness section
    readiness = briefing["readiness"]
    zone_color = get_zone_color(readiness["zone"])
    print(f"  {Colors.BOLD}Date:{Colors.RESET}           {briefing['date']}")
    print(f"  {Colors.BOLD}Readiness:{Colors.RESET}      {zone_color}{readiness['score']:.0f}/100 ({readiness['zone'].upper()}){Colors.RESET}")
    print()

    # Recommendation section
    rec = briefing["recommendation"]
    workout_type = rec["workout_type"].upper()
    duration = rec["duration_min"]

    print(f"  {Colors.BOLD}Recommended:{Colors.RESET}    {Colors.CYAN}{workout_type}{Colors.RESET}")
    if duration > 0:
        print(f"  {Colors.BOLD}Duration:{Colors.RESET}       {duration} minutes")
    print(f"  {Colors.BOLD}Intensity:{Colors.RESET}      {rec['intensity_description']}")
    if rec["hr_zone_target"]:
        print(f"  {Colors.BOLD}Target:{Colors.RESET}         {rec['hr_zone_target']}")
    print()
    print(f"  {Colors.BOLD}Reason:{Colors.RESET}         {rec['reason']}")
    print()

    # Alternatives
    if rec["alternatives"]:
        print(f"  {Colors.BOLD}Alternatives:{Colors.RESET}   {', '.join(rec['alternatives'])}")

    # Warnings
    if rec["warnings"]:
        for warning in rec["warnings"]:
            print(f"  {Colors.YELLOW}!{Colors.RESET} {warning}")

    print()

    # Training status (if available)
    if briefing["training_status"]:
        ts = briefing["training_status"]
        print(f"  {Colors.BOLD}Training Status:{Colors.RESET}")
        print(f"    CTL: {ts['ctl']:.1f}  |  ATL: {ts['atl']:.1f}  |  TSB: {ts['tsb']:+.1f}  |  ACWR: {ts['acwr']:.2f}")
        print()

    # Weekly load
    wl = briefing["weekly_load"]
    if wl["target"] > 0:
        pct = (wl["current"] / wl["target"]) * 100
        print(f"  {Colors.BOLD}Weekly Load:{Colors.RESET}    {wl['current']:.0f} / {wl['target']:.0f} ({pct:.0f}%)")
    print()

    # Narrative
    print(f"{Colors.BOLD}Summary:{Colors.RESET}")
    print()
    print(f"  {briefing['narrative']}")
    print()


def cmd_summary(args, db: TrainingDatabase):
    """Show weekly training summary."""
    print()
    print(f"{Colors.BOLD}Training Analyzer - Weekly Summary{Colors.RESET}")
    print("=" * 50)
    print()

    coach = CoachService(training_db=db)

    try:
        # Calculate weeks_back from days
        weeks_back = 0
        if args.days > 7:
            weeks_back = (args.days - 1) // 7

        summary = coach.get_weekly_summary(weeks_back=weeks_back)
    except Exception as e:
        print(f"{Colors.RED}Error getting summary: {e}{Colors.RESET}")
        sys.exit(1)

    print(f"  Week: {summary['week_start']} to {summary['week_end']}")
    print()

    # Load summary
    print(f"  {Colors.BOLD}Total Load:{Colors.RESET}      {summary['total_load']:.0f}")
    if summary['target_load'] > 0:
        pct = (summary['total_load'] / summary['target_load']) * 100
        print(f"  {Colors.BOLD}Target Load:{Colors.RESET}     {summary['target_load']:.0f} ({pct:.0f}% achieved)")
    print(f"  {Colors.BOLD}Workouts:{Colors.RESET}        {summary['workout_count']}")
    print(f"  {Colors.BOLD}Duration:{Colors.RESET}        {summary['total_duration_min']:.0f} minutes")
    print(f"  {Colors.BOLD}Distance:{Colors.RESET}        {summary['total_distance_km']:.1f} km")
    print()

    # Distribution
    print(f"  {Colors.BOLD}Distribution:{Colors.RESET}")
    print(f"    Hard days:  {summary['hard_days']}")
    print(f"    Easy days:  {summary['easy_days']}")
    print(f"    Rest days:  {summary['rest_days']}")
    print()

    # Fitness change
    if summary['ctl_start'] > 0 or summary['ctl_end'] > 0:
        print(f"  {Colors.BOLD}Fitness Change:{Colors.RESET}")
        change = summary['ctl_change']
        if change > 0:
            change_color = Colors.GREEN
            change_symbol = "+"
        elif change < 0:
            change_color = Colors.RED
            change_symbol = ""
        else:
            change_color = Colors.RESET
            change_symbol = ""
        print(
            f"    CTL: {summary['ctl_start']:.1f} -> {summary['ctl_end']:.1f} "
            f"({change_color}{change_symbol}{change:.1f}{Colors.RESET})"
        )
        print()

    # Narrative
    print(f"{Colors.BOLD}Summary:{Colors.RESET}")
    print()
    print(f"  {summary['narrative']}")
    print()


def cmd_why(args, db: TrainingDatabase):
    """Explain why today's workout was recommended."""
    print()
    print(f"{Colors.BOLD}Training Analyzer - Recommendation Explained{Colors.RESET}")
    print("=" * 50)
    print()

    coach = CoachService(training_db=db)

    try:
        explanation = coach.get_why_explanation()
    except Exception as e:
        print(f"{Colors.RED}Error generating explanation: {e}{Colors.RESET}")
        sys.exit(1)

    print(explanation)
    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Training Analyzer - AI-powered workout analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  training-analyzer setup --max-hr 185 --rest-hr 50 --age 35
  training-analyzer enrich --days 30
  training-analyzer fitness --days 7
  training-analyzer status
  training-analyzer today
  training-analyzer summary --days 7
  training-analyzer why
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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
