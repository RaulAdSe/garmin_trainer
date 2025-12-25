"""
Performance Trend Analysis

Track how fitness metrics evolve over time and detect patterns.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from datetime import date, datetime, timedelta


@dataclass
class FitnessTrend:
    """Fitness trend over a period."""

    period_start: date
    period_end: date
    ctl_start: float
    ctl_end: float
    ctl_change: float           # Absolute change
    ctl_change_pct: float       # Percentage change
    weekly_load_avg: float
    trend_direction: str        # 'improving', 'maintaining', 'declining'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "ctl_start": round(self.ctl_start, 1),
            "ctl_end": round(self.ctl_end, 1),
            "ctl_change": round(self.ctl_change, 1),
            "ctl_change_pct": round(self.ctl_change_pct, 1),
            "weekly_load_avg": round(self.weekly_load_avg, 1),
            "trend_direction": self.trend_direction,
        }


@dataclass
class PerformanceTrend:
    """Track pace at same HR over time (efficiency indicator)."""

    date: date
    avg_hr: int
    avg_pace: float             # sec/km
    efficiency_score: float     # Higher = more efficient

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "date": self.date.isoformat(),
            "avg_hr": self.avg_hr,
            "avg_pace": round(self.avg_pace, 1),
            "efficiency_score": round(self.efficiency_score, 2),
        }


def _parse_date(date_value: Any) -> Optional[date]:
    """Parse date from string or date object."""
    if date_value is None:
        return None
    if isinstance(date_value, date):
        return date_value
    if isinstance(date_value, datetime):
        return date_value.date()
    if isinstance(date_value, str):
        try:
            return datetime.strptime(date_value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _determine_trend_direction(change_pct: float) -> str:
    """Determine trend direction from percentage change."""
    if change_pct > 5.0:
        return "improving"
    elif change_pct < -5.0:
        return "declining"
    else:
        return "maintaining"


def calculate_fitness_trend(
    fitness_history: List[dict],
    period_days: int = 28
) -> Optional[FitnessTrend]:
    """
    Calculate fitness trend over the given period.

    Args:
        fitness_history: List of fitness metric dictionaries with 'date', 'ctl', 'daily_load'
        period_days: Number of days to analyze (default 28 = 4 weeks)

    Returns:
        FitnessTrend object or None if insufficient data
    """
    if not fitness_history or len(fitness_history) < 2:
        return None

    # Sort by date
    sorted_history = sorted(
        fitness_history,
        key=lambda x: _parse_date(x.get("date")) or date.min
    )

    # Filter to period
    end_date = _parse_date(sorted_history[-1].get("date"))
    if end_date is None:
        return None

    start_date = end_date - timedelta(days=period_days)

    period_data = [
        h for h in sorted_history
        if (_parse_date(h.get("date")) or date.min) >= start_date
    ]

    if len(period_data) < 2:
        return None

    # Get start and end CTL
    first_entry = period_data[0]
    last_entry = period_data[-1]

    ctl_start = first_entry.get("ctl", 0) or 0
    ctl_end = last_entry.get("ctl", 0) or 0

    # Calculate change
    ctl_change = ctl_end - ctl_start
    if ctl_start > 0:
        ctl_change_pct = (ctl_change / ctl_start) * 100
    else:
        ctl_change_pct = 0.0 if ctl_end == 0 else 100.0

    # Calculate weekly load average
    total_load = sum(h.get("daily_load", 0) or 0 for h in period_data)
    weeks = max(1, period_days / 7)
    weekly_load_avg = total_load / weeks

    # Determine trend direction
    trend_direction = _determine_trend_direction(ctl_change_pct)

    actual_start = _parse_date(first_entry.get("date")) or start_date
    actual_end = _parse_date(last_entry.get("date")) or end_date

    return FitnessTrend(
        period_start=actual_start,
        period_end=actual_end,
        ctl_start=ctl_start,
        ctl_end=ctl_end,
        ctl_change=ctl_change,
        ctl_change_pct=ctl_change_pct,
        weekly_load_avg=weekly_load_avg,
        trend_direction=trend_direction,
    )


def calculate_pace_at_hr_trend(
    activities: List[dict],
    target_hr_zone: Tuple[int, int],
    period_days: int = 90
) -> List[PerformanceTrend]:
    """
    Track pace at a given HR range over time.

    If you're running faster at the same HR, you're getting fitter.
    This is a key efficiency indicator.

    Args:
        activities: List of activity dictionaries with 'date', 'avg_hr',
                   'pace_sec_per_km', 'distance_km'
        target_hr_zone: Tuple of (min_hr, max_hr) to filter activities
        period_days: Number of days to analyze (default 90 = ~3 months)

    Returns:
        List of PerformanceTrend objects, one per qualifying activity
    """
    if not activities:
        return []

    min_hr, max_hr = target_hr_zone
    end_date = date.today()
    start_date = end_date - timedelta(days=period_days)

    trends = []

    for activity in activities:
        # Parse date
        activity_date = _parse_date(activity.get("date"))
        if activity_date is None or activity_date < start_date:
            continue

        # Get HR and pace
        avg_hr = activity.get("avg_hr")
        pace = activity.get("pace_sec_per_km")
        distance = activity.get("distance_km", 0) or 0

        # Filter by HR zone and minimum distance (at least 3km)
        if avg_hr is None or pace is None:
            continue
        if not (min_hr <= avg_hr <= max_hr):
            continue
        if distance < 3.0:
            continue

        # Calculate efficiency score
        # Higher HR relative to zone midpoint = less efficient
        # Lower pace = more efficient
        # Efficiency = zone_midpoint * 1000 / (avg_hr * pace)
        zone_midpoint = (min_hr + max_hr) / 2

        # Normalize: faster pace at lower HR = higher efficiency
        # Baseline: 5 min/km at zone midpoint HR = 1.0
        baseline_pace = 300.0  # 5 min/km in seconds
        efficiency_score = (zone_midpoint / avg_hr) * (baseline_pace / pace)

        trends.append(PerformanceTrend(
            date=activity_date,
            avg_hr=avg_hr,
            avg_pace=pace,
            efficiency_score=efficiency_score,
        ))

    # Sort by date
    trends.sort(key=lambda x: x.date)

    return trends


def detect_overtraining_signals(
    fitness_history: List[dict],
    wellness_history: List[dict]
) -> List[str]:
    """
    Detect potential overtraining signals:
    - Declining HRV trend
    - Increasing resting HR
    - Decreasing performance despite training
    - Elevated recovery time
    - High training load with declining CTL

    Args:
        fitness_history: List of fitness metrics with 'date', 'ctl', 'atl', 'tsb', 'acwr'
        wellness_history: List of wellness data with 'date', 'hrv', 'resting_hr', etc.

    Returns:
        List of warning signals detected
    """
    signals = []

    # Check fitness history signals if available
    if fitness_history:
        recent_fitness = fitness_history[-7:] if len(fitness_history) >= 7 else fitness_history

        # Check for ACWR danger zone
        high_acwr_days = sum(
            1 for f in recent_fitness
            if (f.get("acwr") or 0) > 1.3
        )

        if high_acwr_days >= 3:
            signals.append(
                f"ACWR has been elevated (>1.3) for {high_acwr_days} of the last 7 days - "
                "injury risk is high"
            )

        # Check for prolonged negative TSB
        negative_tsb_days = sum(
            1 for f in recent_fitness
            if (f.get("tsb") or 0) < -20
        )

        if negative_tsb_days >= 5:
            signals.append(
                f"TSB has been very negative (<-20) for {negative_tsb_days} of the last 7 days - "
                "consider a recovery week"
            )

        # Check CTL trend (is fitness declining despite training?)
        if len(fitness_history) >= 14:
            week1_ctl = sum(f.get("ctl", 0) or 0 for f in fitness_history[-14:-7]) / 7
            week2_ctl = sum(f.get("ctl", 0) or 0 for f in fitness_history[-7:]) / 7
            week1_load = sum(f.get("daily_load", 0) or 0 for f in fitness_history[-14:-7])
            week2_load = sum(f.get("daily_load", 0) or 0 for f in fitness_history[-7:])

            # If load is maintained or increased but CTL is declining
            if week2_load >= week1_load * 0.9 and week2_ctl < week1_ctl - 2:
                signals.append(
                    "Fitness (CTL) is declining despite maintained training load - "
                    "possible overreaching or inadequate recovery"
                )

    # Check wellness data if available
    if wellness_history:
        recent_wellness = wellness_history[-7:] if len(wellness_history) >= 7 else wellness_history

        # Check HRV trend
        hrv_values = [
            w.get("hrv_last_night_avg") or w.get("hrv")
            for w in recent_wellness
            if w.get("hrv_last_night_avg") or w.get("hrv")
        ]

        if len(hrv_values) >= 5:
            first_half_avg = sum(hrv_values[:len(hrv_values)//2]) / (len(hrv_values)//2)
            second_half_avg = sum(hrv_values[len(hrv_values)//2:]) / (len(hrv_values) - len(hrv_values)//2)

            if second_half_avg < first_half_avg * 0.85:
                signals.append(
                    "HRV has declined by >15% over the past week - "
                    "indicating increased stress or insufficient recovery"
                )

        # Check resting HR trend
        rhr_values = [
            w.get("resting_hr") or w.get("rest_hr")
            for w in recent_wellness
            if w.get("resting_hr") or w.get("rest_hr")
        ]

        if len(rhr_values) >= 5:
            first_half_avg = sum(rhr_values[:len(rhr_values)//2]) / (len(rhr_values)//2)
            second_half_avg = sum(rhr_values[len(rhr_values)//2:]) / (len(rhr_values) - len(rhr_values)//2)

            if second_half_avg > first_half_avg * 1.1:
                signals.append(
                    "Resting heart rate has increased by >10% over the past week - "
                    "possible sign of fatigue or illness"
                )

        # Check for consistently low Body Battery
        bb_values = [
            w.get("body_battery_high") or w.get("body_battery_charged") or w.get("body_battery")
            for w in recent_wellness
            if w.get("body_battery_high") or w.get("body_battery_charged") or w.get("body_battery")
        ]

        if bb_values:
            avg_bb = sum(bb_values) / len(bb_values)
            if avg_bb < 40:
                signals.append(
                    f"Average Body Battery is low ({avg_bb:.0f}/100) - "
                    "energy reserves are depleted, prioritize recovery"
                )

        # Check sleep quality
        sleep_scores = [
            w.get("sleep_score")
            for w in recent_wellness
            if w.get("sleep_score")
        ]

        if sleep_scores:
            avg_sleep = sum(sleep_scores) / len(sleep_scores)
            if avg_sleep < 60:
                signals.append(
                    f"Average sleep score is low ({avg_sleep:.0f}/100) - "
                    "poor sleep compromises recovery"
                )

    return signals


def generate_trend_summary(
    fitness_trend: Optional[FitnessTrend],
    performance_trends: List[PerformanceTrend],
    overtraining_signals: List[str]
) -> str:
    """
    Generate a human-readable summary of trends.

    Args:
        fitness_trend: Fitness trend over the period
        performance_trends: List of performance efficiency trends
        overtraining_signals: List of warning signals

    Returns:
        Summary text
    """
    parts = []

    if fitness_trend:
        if fitness_trend.trend_direction == "improving":
            parts.append(
                f"Your fitness has improved by {fitness_trend.ctl_change:.1f} points "
                f"({fitness_trend.ctl_change_pct:+.1f}%) over the past "
                f"{(fitness_trend.period_end - fitness_trend.period_start).days} days."
            )
        elif fitness_trend.trend_direction == "declining":
            parts.append(
                f"Your fitness has decreased by {abs(fitness_trend.ctl_change):.1f} points "
                f"({fitness_trend.ctl_change_pct:+.1f}%) over the past "
                f"{(fitness_trend.period_end - fitness_trend.period_start).days} days."
            )
        else:
            parts.append(
                f"Your fitness has remained stable over the past "
                f"{(fitness_trend.period_end - fitness_trend.period_start).days} days."
            )

        parts.append(
            f"Average weekly training load: {fitness_trend.weekly_load_avg:.0f}."
        )

    if len(performance_trends) >= 2:
        first_efficiency = performance_trends[0].efficiency_score
        last_efficiency = performance_trends[-1].efficiency_score
        efficiency_change = ((last_efficiency - first_efficiency) / first_efficiency) * 100

        if efficiency_change > 5:
            parts.append(
                f"Your running efficiency has improved by {efficiency_change:.0f}% - "
                "you're running faster at the same heart rate."
            )
        elif efficiency_change < -5:
            parts.append(
                f"Your running efficiency has declined by {abs(efficiency_change):.0f}% - "
                "this could indicate fatigue or detraining."
            )

    if overtraining_signals:
        parts.append("")
        parts.append("Warning signals detected:")
        for signal in overtraining_signals:
            parts.append(f"  - {signal}")

    return "\n".join(parts) if parts else "Insufficient data for trend analysis."


def generate_ascii_chart(
    values: List[float],
    labels: List[str],
    title: str = "",
    width: int = 50,
    height: int = 10
) -> str:
    """
    Generate an ASCII chart for terminal display.

    Args:
        values: List of numeric values to plot
        labels: List of labels for x-axis (e.g., dates)
        title: Chart title
        width: Chart width in characters
        height: Chart height in lines

    Returns:
        ASCII chart string
    """
    if not values:
        return "No data to display"

    lines = []

    if title:
        lines.append(title)
        lines.append("-" * len(title))

    min_val = min(values)
    max_val = max(values)
    val_range = max_val - min_val if max_val != min_val else 1

    # Create chart rows
    for row in range(height, 0, -1):
        threshold = min_val + (row / height) * val_range
        row_chars = []

        # Y-axis label
        if row == height:
            label = f"{max_val:6.1f} |"
        elif row == 1:
            label = f"{min_val:6.1f} |"
        elif row == height // 2:
            mid_val = (max_val + min_val) / 2
            label = f"{mid_val:6.1f} |"
        else:
            label = "       |"

        row_chars.append(label)

        # Data points
        for val in values:
            if val >= threshold:
                row_chars.append("*")
            else:
                row_chars.append(" ")

        lines.append("".join(row_chars))

    # X-axis
    lines.append("       +" + "-" * len(values))

    # X-axis labels (show first, middle, last)
    if labels:
        if len(labels) >= 3:
            x_label = f"       {labels[0]}" + " " * (len(values) // 2 - len(labels[0])) + labels[len(labels)//2] + " " * (len(values) - len(values)//2 - len(labels[-1]) - len(labels[len(labels)//2])) + labels[-1]
        else:
            x_label = f"       {labels[0]}"
        lines.append(x_label[:width + 10])

    return "\n".join(lines)
