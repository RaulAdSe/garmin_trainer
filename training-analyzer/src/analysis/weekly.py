"""
Weekly Training Analysis

Comprehensive weekly summaries with load distribution, compliance, and insights.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import json


@dataclass
class WeeklyAnalysis:
    """Complete weekly training analysis."""

    week_start: date
    week_end: date

    # Volume
    total_distance_km: float
    total_duration_min: float
    total_load: float           # Sum of HRSS/TRIMP
    activity_count: int

    # Distribution
    zone1_pct: float
    zone2_pct: float
    zone3_pct: float
    zone4_pct: float
    zone5_pct: float

    # Load management
    week_over_week_change: float
    is_recovery_week: bool
    load_vs_target: float       # % of target weekly load

    # Fitness changes
    ctl_change: float
    atl_change: float

    # Insights
    insights: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "total_distance_km": round(self.total_distance_km, 2),
            "total_duration_min": round(self.total_duration_min, 1),
            "total_load": round(self.total_load, 1),
            "activity_count": self.activity_count,
            "zone_distribution": {
                "zone1_pct": round(self.zone1_pct, 1),
                "zone2_pct": round(self.zone2_pct, 1),
                "zone3_pct": round(self.zone3_pct, 1),
                "zone4_pct": round(self.zone4_pct, 1),
                "zone5_pct": round(self.zone5_pct, 1),
            },
            "week_over_week_change": round(self.week_over_week_change, 1),
            "is_recovery_week": self.is_recovery_week,
            "load_vs_target": round(self.load_vs_target, 1),
            "ctl_change": round(self.ctl_change, 1),
            "atl_change": round(self.atl_change, 1),
            "insights": self.insights,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


def _parse_date(date_value: Any) -> Optional[date]:
    """Parse date from string or date object."""
    if date_value is None:
        return None
    if isinstance(date_value, date) and not isinstance(date_value, datetime):
        return date_value
    if isinstance(date_value, datetime):
        return date_value.date()
    if isinstance(date_value, str):
        try:
            return datetime.strptime(date_value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _calculate_zone_distribution(activities: List[dict]) -> Dict[str, float]:
    """Calculate weighted zone distribution across activities."""
    total_duration = 0.0
    zone_durations = {
        "zone1": 0.0,
        "zone2": 0.0,
        "zone3": 0.0,
        "zone4": 0.0,
        "zone5": 0.0,
    }

    for activity in activities:
        duration = activity.get("duration_min", 0) or 0

        # Get zone percentages
        z1_pct = activity.get("zone1_pct", 0) or 0
        z2_pct = activity.get("zone2_pct", 0) or 0
        z3_pct = activity.get("zone3_pct", 0) or 0
        z4_pct = activity.get("zone4_pct", 0) or 0
        z5_pct = activity.get("zone5_pct", 0) or 0

        # Convert to minutes and accumulate
        zone_durations["zone1"] += duration * (z1_pct / 100)
        zone_durations["zone2"] += duration * (z2_pct / 100)
        zone_durations["zone3"] += duration * (z3_pct / 100)
        zone_durations["zone4"] += duration * (z4_pct / 100)
        zone_durations["zone5"] += duration * (z5_pct / 100)
        total_duration += duration

    if total_duration == 0:
        return {f"zone{i}_pct": 0.0 for i in range(1, 6)}

    return {
        "zone1_pct": (zone_durations["zone1"] / total_duration) * 100,
        "zone2_pct": (zone_durations["zone2"] / total_duration) * 100,
        "zone3_pct": (zone_durations["zone3"] / total_duration) * 100,
        "zone4_pct": (zone_durations["zone4"] / total_duration) * 100,
        "zone5_pct": (zone_durations["zone5"] / total_duration) * 100,
    }


def analyze_week(
    activities: List[dict],
    fitness_metrics: List[dict],
    target_weekly_load: Optional[float] = None,
    previous_week_load: Optional[float] = None,
) -> WeeklyAnalysis:
    """
    Generate comprehensive weekly analysis.

    Args:
        activities: List of activity dictionaries with metrics
        fitness_metrics: List of daily fitness metrics
        target_weekly_load: Target load for the week (optional)
        previous_week_load: Previous week's total load (optional)

    Returns:
        WeeklyAnalysis object with complete analysis
    """
    if not activities:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        return WeeklyAnalysis(
            week_start=week_start,
            week_end=week_end,
            total_distance_km=0.0,
            total_duration_min=0.0,
            total_load=0.0,
            activity_count=0,
            zone1_pct=0.0,
            zone2_pct=0.0,
            zone3_pct=0.0,
            zone4_pct=0.0,
            zone5_pct=0.0,
            week_over_week_change=0.0,
            is_recovery_week=True,
            load_vs_target=0.0,
            ctl_change=0.0,
            atl_change=0.0,
            insights=["No activities recorded this week."],
        )

    # Determine week boundaries from activities
    activity_dates = [
        _parse_date(a.get("date"))
        for a in activities
        if _parse_date(a.get("date"))
    ]

    if activity_dates:
        min_date = min(activity_dates)
        max_date = max(activity_dates)
        week_start = min_date - timedelta(days=min_date.weekday())
        week_end = week_start + timedelta(days=6)
    else:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

    # Calculate totals
    total_distance = sum(a.get("distance_km", 0) or 0 for a in activities)
    total_duration = sum(a.get("duration_min", 0) or 0 for a in activities)
    total_load = sum(a.get("hrss", 0) or a.get("trimp", 0) or 0 for a in activities)
    activity_count = len(activities)

    # Calculate zone distribution
    zone_dist = _calculate_zone_distribution(activities)

    # Calculate week-over-week change
    if previous_week_load and previous_week_load > 0:
        week_over_week_change = ((total_load - previous_week_load) / previous_week_load) * 100
    else:
        week_over_week_change = 0.0

    # Determine if recovery week (load < 70% of recent average)
    is_recovery_week = total_load < (target_weekly_load or 300) * 0.7

    # Calculate load vs target
    if target_weekly_load and target_weekly_load > 0:
        load_vs_target = (total_load / target_weekly_load) * 100
    else:
        load_vs_target = 0.0

    # Calculate CTL/ATL change
    ctl_change = 0.0
    atl_change = 0.0

    if fitness_metrics and len(fitness_metrics) >= 2:
        # Sort by date
        sorted_metrics = sorted(
            fitness_metrics,
            key=lambda x: _parse_date(x.get("date")) or date.min
        )

        # Get start and end of week metrics
        week_metrics = [
            m for m in sorted_metrics
            if (d := _parse_date(m.get("date"))) and week_start <= d <= week_end
        ]

        if len(week_metrics) >= 2:
            ctl_change = (week_metrics[-1].get("ctl", 0) or 0) - (week_metrics[0].get("ctl", 0) or 0)
            atl_change = (week_metrics[-1].get("atl", 0) or 0) - (week_metrics[0].get("atl", 0) or 0)

    # Generate insights
    analysis = WeeklyAnalysis(
        week_start=week_start,
        week_end=week_end,
        total_distance_km=total_distance,
        total_duration_min=total_duration,
        total_load=total_load,
        activity_count=activity_count,
        zone1_pct=zone_dist["zone1_pct"],
        zone2_pct=zone_dist["zone2_pct"],
        zone3_pct=zone_dist["zone3_pct"],
        zone4_pct=zone_dist["zone4_pct"],
        zone5_pct=zone_dist["zone5_pct"],
        week_over_week_change=week_over_week_change,
        is_recovery_week=is_recovery_week,
        load_vs_target=load_vs_target,
        ctl_change=ctl_change,
        atl_change=atl_change,
        insights=[],
    )

    analysis.insights = generate_weekly_insights(analysis)

    return analysis


def generate_weekly_insights(analysis: WeeklyAnalysis) -> List[str]:
    """
    Generate insights from weekly data.

    Args:
        analysis: WeeklyAnalysis object

    Returns:
        List of insight strings
    """
    insights = []

    # Load change insight
    if analysis.week_over_week_change > 20:
        insights.append(
            f"Training load increased {analysis.week_over_week_change:.0f}% week-over-week. "
            "Be mindful of injury risk with rapid increases."
        )
    elif analysis.week_over_week_change < -20:
        insights.append(
            f"Training load decreased {abs(analysis.week_over_week_change):.0f}% week-over-week. "
            "This may be a planned recovery week or reduced training."
        )
    elif abs(analysis.week_over_week_change) <= 10:
        insights.append("Training load is consistent with previous week.")

    # Zone distribution insight (80/20 rule check)
    low_intensity_pct = analysis.zone1_pct + analysis.zone2_pct
    high_intensity_pct = analysis.zone4_pct + analysis.zone5_pct

    if low_intensity_pct >= 75 and low_intensity_pct <= 85:
        insights.append(
            f"{low_intensity_pct:.0f}% of time in Zone 1-2 - good adherence to 80/20 polarized training."
        )
    elif low_intensity_pct < 65:
        insights.append(
            f"Only {low_intensity_pct:.0f}% of time in Zone 1-2. "
            "Consider adding more easy aerobic work for better base building."
        )
    elif low_intensity_pct > 90:
        insights.append(
            f"{low_intensity_pct:.0f}% of time in Zone 1-2. "
            "Consider adding some higher intensity work to improve fitness."
        )

    # Zone 3 warning (too much moderate intensity)
    if analysis.zone3_pct > 25:
        insights.append(
            f"Zone 3 (tempo) is {analysis.zone3_pct:.0f}% of training. "
            "Consider polarizing more - either easy or hard, less middle."
        )

    # Recovery week insight
    if analysis.is_recovery_week:
        insights.append("This appears to be a recovery week with reduced load.")

    # Fitness change insight
    if analysis.ctl_change > 2:
        insights.append(
            f"Fitness (CTL) improved by {analysis.ctl_change:.1f} points this week."
        )
    elif analysis.ctl_change < -2:
        insights.append(
            f"Fitness (CTL) decreased by {abs(analysis.ctl_change):.1f} points. "
            "This may indicate detraining or planned rest."
        )

    # Target compliance
    if analysis.load_vs_target > 0:
        if analysis.load_vs_target >= 90 and analysis.load_vs_target <= 110:
            insights.append(
                f"Hit {analysis.load_vs_target:.0f}% of target load - great adherence!"
            )
        elif analysis.load_vs_target > 110:
            insights.append(
                f"Exceeded target load by {analysis.load_vs_target - 100:.0f}%. "
                "Monitor recovery and consider backing off next week."
            )
        elif analysis.load_vs_target < 70:
            insights.append(
                f"Only achieved {analysis.load_vs_target:.0f}% of target load. "
                "Consider adjusting targets or prioritizing consistency."
            )

    # Activity count insight
    if analysis.activity_count >= 6:
        insights.append(
            f"High training frequency with {analysis.activity_count} sessions. "
            "Ensure adequate recovery between sessions."
        )
    elif analysis.activity_count <= 2:
        insights.append(
            f"Low training frequency with only {analysis.activity_count} sessions. "
            "Consider adding easy sessions for consistency."
        )

    return insights


def format_weekly_summary(analysis: WeeklyAnalysis) -> str:
    """
    Format weekly analysis for display.

    Args:
        analysis: WeeklyAnalysis object

    Returns:
        Formatted summary string
    """
    lines = []

    # Header
    lines.append(f"Week of {analysis.week_start.strftime('%b %d')} - {analysis.week_end.strftime('%b %d')}")
    lines.append("=" * 50)
    lines.append("")

    # Volume summary
    lines.append("Volume:")
    lines.append(f"  Activities:    {analysis.activity_count}")
    lines.append(f"  Distance:      {analysis.total_distance_km:.1f} km")
    lines.append(f"  Duration:      {analysis.total_duration_min:.0f} min")
    lines.append(f"  Training Load: {analysis.total_load:.0f}")
    lines.append("")

    # Zone distribution
    lines.append("Zone Distribution:")
    lines.append(f"  Zone 1 (Recovery):  {analysis.zone1_pct:5.1f}%")
    lines.append(f"  Zone 2 (Aerobic):   {analysis.zone2_pct:5.1f}%")
    lines.append(f"  Zone 3 (Tempo):     {analysis.zone3_pct:5.1f}%")
    lines.append(f"  Zone 4 (Threshold): {analysis.zone4_pct:5.1f}%")
    lines.append(f"  Zone 5 (VO2max):    {analysis.zone5_pct:5.1f}%")
    lines.append("")

    # Load management
    lines.append("Load Management:")
    if analysis.week_over_week_change != 0:
        direction = "+" if analysis.week_over_week_change > 0 else ""
        lines.append(f"  Week-over-week: {direction}{analysis.week_over_week_change:.1f}%")

    if analysis.load_vs_target > 0:
        lines.append(f"  Target compliance: {analysis.load_vs_target:.0f}%")

    if analysis.is_recovery_week:
        lines.append("  Type: Recovery week")
    lines.append("")

    # Fitness changes
    if analysis.ctl_change != 0 or analysis.atl_change != 0:
        lines.append("Fitness Changes:")
        lines.append(f"  CTL change: {analysis.ctl_change:+.1f}")
        lines.append(f"  ATL change: {analysis.atl_change:+.1f}")
        lines.append("")

    # Insights
    if analysis.insights:
        lines.append("Insights:")
        for insight in analysis.insights:
            # Wrap long insights
            if len(insight) > 60:
                words = insight.split()
                current_line = "  - "
                for word in words:
                    if len(current_line) + len(word) > 65:
                        lines.append(current_line)
                        current_line = "    " + word + " "
                    else:
                        current_line += word + " "
                lines.append(current_line.rstrip())
            else:
                lines.append(f"  - {insight}")

    return "\n".join(lines)


def generate_zone_bar_chart(analysis: WeeklyAnalysis, width: int = 40) -> str:
    """
    Generate an ASCII bar chart of zone distribution.

    Args:
        analysis: WeeklyAnalysis object
        width: Width of the bar in characters

    Returns:
        ASCII bar chart string
    """
    zones = [
        ("Z1", analysis.zone1_pct, "Recovery"),
        ("Z2", analysis.zone2_pct, "Aerobic"),
        ("Z3", analysis.zone3_pct, "Tempo"),
        ("Z4", analysis.zone4_pct, "Threshold"),
        ("Z5", analysis.zone5_pct, "VO2max"),
    ]

    lines = ["Zone Distribution:"]

    for zone_name, pct, description in zones:
        bar_width = int((pct / 100) * width)
        bar = "#" * bar_width
        lines.append(f"  {zone_name} |{bar:<{width}}| {pct:5.1f}% ({description})")

    return "\n".join(lines)
