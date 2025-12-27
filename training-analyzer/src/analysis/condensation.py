"""
Workout Time-Series Data Condensation Module.

This module condenses raw time-series data (HR, pace, elevation, splits) into
compact statistical summaries for LLM analysis, reducing token usage by ~95%
while preserving coaching-relevant insights.

Key metrics:
- HR: drift, variability (CV), zone transitions
- Pace: consistency score, fade index, negative/positive splits
- Elevation: terrain classification, climb analysis
- Splits: trend detection, consistency scoring
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import statistics


class TrendDirection(str, Enum):
    """Pace or HR trend direction."""
    ACCELERATING = "accelerating"
    DECELERATING = "decelerating"
    STEADY = "steady"
    VARIABLE = "variable"


class TerrainType(str, Enum):
    """Terrain classification based on elevation gain."""
    FLAT = "flat"           # <50m gain
    ROLLING = "rolling"     # 50-200m gain
    HILLY = "hilly"         # 200-500m gain
    MOUNTAINOUS = "mountainous"  # >500m gain


@dataclass
class HRSummary:
    """Condensed heart rate time-series summary."""

    # Central tendency
    mean: float = 0.0
    std_dev: float = 0.0
    cv: float = 0.0  # Coefficient of variation (std/mean * 100)

    # Temporal patterns
    hr_drift: float = 0.0  # % change (last 10min vs first 10min)
    hr_drift_bpm: int = 0  # Absolute drift in bpm
    time_to_steady_sec: int = 0  # Time until HR stabilizes
    peak_hr: int = 0
    peak_time_pct: float = 0.0  # When peak occurred (% of workout)

    # Zone dynamics
    zone_transitions: int = 0  # Number of zone boundary crossings
    dominant_zone: int = 0  # Zone with highest time

    # Interval detection
    is_interval_workout: bool = False  # High CV + many zone transitions

    def to_prompt_text(self) -> str:
        """Format as concise text for LLM prompt."""
        lines = []

        # Stability indicator
        if self.cv < 8:
            stability = "very steady"
        elif self.cv < 12:
            stability = "steady"
        elif self.cv < 18:
            stability = "moderate variability"
        else:
            stability = "high variability (intervals)"

        lines.append(f"HR: avg {self.mean:.0f} bpm, {stability} (CV={self.cv:.1f}%)")

        # Drift analysis (only if significant)
        if abs(self.hr_drift) > 5:
            drift_sign = "+" if self.hr_drift > 0 else ""
            lines.append(f"HR Drift: {drift_sign}{self.hr_drift:.1f}% ({drift_sign}{self.hr_drift_bpm} bpm)")

        # Peak timing
        if self.peak_hr > 0:
            timing = "early" if self.peak_time_pct < 33 else "middle" if self.peak_time_pct < 67 else "late"
            lines.append(f"Peak: {self.peak_hr} bpm ({timing} in workout)")

        # Zone transitions (indicator of workout structure)
        if self.zone_transitions > 6:
            lines.append(f"Zone transitions: {self.zone_transitions} (structured intervals)")
        elif self.zone_transitions > 2:
            lines.append(f"Zone transitions: {self.zone_transitions}")

        return " | ".join(lines)


@dataclass
class PaceSummary:
    """Condensed pace/speed time-series summary."""

    # Consistency
    mean_pace: float = 0.0  # sec/km for running
    std_dev: float = 0.0
    consistency_score: float = 0.0  # 0-100, higher = more consistent

    # Split analysis
    negative_split_ratio: float = 1.0  # <1.0 = negative split (good)
    fade_index: float = 1.0  # last 25% / first 25% - >1.0 = fading

    # Best/worst comparison
    best_km_pace: float = 0.0
    worst_km_pace: float = 0.0
    best_worst_delta: float = 0.0  # Difference in sec/km

    # Trend
    trend: TrendDirection = TrendDirection.STEADY
    trend_slope: float = 0.0  # sec/km per split (negative = speeding up)

    def format_pace(self, pace_sec: float) -> str:
        """Format pace as min:sec/km."""
        if pace_sec <= 0:
            return "N/A"
        mins = int(pace_sec // 60)
        secs = int(pace_sec % 60)
        return f"{mins}:{secs:02d}/km"

    def to_prompt_text(self) -> str:
        """Format as concise text for LLM prompt."""
        lines = []

        # Consistency rating
        if self.consistency_score >= 90:
            consistency = "excellent"
        elif self.consistency_score >= 75:
            consistency = "good"
        elif self.consistency_score >= 60:
            consistency = "moderate"
        else:
            consistency = "inconsistent"

        lines.append(f"Pace: avg {self.format_pace(self.mean_pace)}, {consistency} consistency ({self.consistency_score:.0f}/100)")

        # Split analysis
        if self.negative_split_ratio < 0.98:
            lines.append(f"Negative split: second half {(1 - self.negative_split_ratio) * 100:.0f}% faster")
        elif self.negative_split_ratio > 1.03:
            lines.append(f"Positive split: second half {(self.negative_split_ratio - 1) * 100:.0f}% slower")

        # Fade analysis
        if self.fade_index > 1.08:
            lines.append(f"Fade: final 25% was {(self.fade_index - 1) * 100:.0f}% slower")
        elif self.fade_index < 0.95:
            lines.append(f"Strong finish: final 25% was {(1 - self.fade_index) * 100:.0f}% faster")

        # Best/worst spread
        if self.best_worst_delta > 30:
            lines.append(f"Range: {self.format_pace(self.best_km_pace)} to {self.format_pace(self.worst_km_pace)}")

        return " | ".join(lines)


@dataclass
class ElevationSummary:
    """Condensed elevation profile summary."""

    # Totals
    total_gain_m: float = 0.0
    total_loss_m: float = 0.0
    net_change: float = 0.0

    # Profile
    climb_count: int = 0  # Distinct climbs (>10m gain over >100m)
    avg_climb_grade_pct: float = 0.0
    max_grade_pct: float = 0.0

    # Terrain classification
    terrain_type: TerrainType = TerrainType.FLAT

    def to_prompt_text(self) -> str:
        """Format as concise text for LLM prompt."""
        if self.total_gain_m < 10 and self.total_loss_m < 10:
            return "Terrain: flat"

        lines = []
        lines.append(f"Elevation: +{self.total_gain_m:.0f}m / -{self.total_loss_m:.0f}m ({self.terrain_type.value})")

        if self.climb_count > 0:
            lines.append(f"Climbs: {self.climb_count}, avg grade {self.avg_climb_grade_pct:.1f}%")

        return " | ".join(lines)


@dataclass
class SplitsSummary:
    """Condensed per-km splits summary."""

    # Key splits
    total_splits: int = 0
    fastest_split: int = 0  # Split number
    fastest_pace: float = 0.0
    slowest_split: int = 0
    slowest_pace: float = 0.0

    # Trends
    trend: TrendDirection = TrendDirection.STEADY
    trend_slope: float = 0.0  # sec/km per split

    # Consistency
    avg_pace: float = 0.0
    splits_within_5pct: int = 0  # Number of splits within 5% of average
    even_split_score: float = 0.0  # 0-100

    # Effort distribution
    first_half_avg: float = 0.0
    second_half_avg: float = 0.0

    def format_pace(self, pace_sec: float) -> str:
        """Format pace as min:sec/km."""
        if pace_sec <= 0:
            return "N/A"
        mins = int(pace_sec // 60)
        secs = int(pace_sec % 60)
        return f"{mins}:{secs:02d}/km"

    def to_prompt_text(self) -> str:
        """Format as concise text for LLM prompt."""
        if self.total_splits == 0:
            return ""

        lines = []

        # Summary
        lines.append(f"Splits ({self.total_splits}km): {self.splits_within_5pct}/{self.total_splits} within 5% of avg")

        # Best/worst
        lines.append(f"Fastest: km {self.fastest_split} ({self.format_pace(self.fastest_pace)})")
        lines.append(f"Slowest: km {self.slowest_split} ({self.format_pace(self.slowest_pace)})")

        # Trend
        if self.trend != TrendDirection.STEADY:
            lines.append(f"Trend: {self.trend.value}")

        # Even split score
        if self.even_split_score >= 90:
            lines.append("Even-split: excellent pacing")
        elif self.even_split_score < 70:
            lines.append(f"Even-split score: {self.even_split_score:.0f}/100 (inconsistent)")

        return " | ".join(lines)


@dataclass
class CondensedWorkoutData:
    """Complete condensed workout data for LLM consumption."""

    hr_summary: Optional[HRSummary] = None
    pace_summary: Optional[PaceSummary] = None
    elevation_summary: Optional[ElevationSummary] = None
    splits_summary: Optional[SplitsSummary] = None

    # Quick insights (pre-computed coaching observations)
    insights: List[str] = field(default_factory=list)

    def to_prompt_data(self) -> str:
        """
        Format all condensed data for LLM prompt.

        Returns compact text summary (~200-300 tokens) capturing key dynamics.
        """
        sections = []

        if self.hr_summary and self.hr_summary.mean > 0:
            sections.append(self.hr_summary.to_prompt_text())

        if self.pace_summary and self.pace_summary.mean_pace > 0:
            sections.append(self.pace_summary.to_prompt_text())

        if self.elevation_summary and (self.elevation_summary.total_gain_m > 10 or self.elevation_summary.total_loss_m > 10):
            sections.append(self.elevation_summary.to_prompt_text())

        if self.splits_summary and self.splits_summary.total_splits > 0:
            sections.append(self.splits_summary.to_prompt_text())

        # Add insights
        if self.insights:
            insights_text = "Key Observations: " + "; ".join(self.insights)
            sections.append(insights_text)

        return "\n".join(sections)


# =============================================================================
# Calculation Functions
# =============================================================================

def calculate_hr_summary(
    hr_points: List[Dict[str, Any]],
    hr_zones: Optional[Dict[int, Tuple[int, int]]] = None,
    duration_sec: int = 0
) -> HRSummary:
    """
    Calculate HR summary from time-series data.

    Args:
        hr_points: List of {timestamp: int, hr: int} points
        hr_zones: Optional dict of zone -> (min_hr, max_hr)
        duration_sec: Total workout duration

    Returns:
        HRSummary with calculated statistics
    """
    summary = HRSummary()

    if not hr_points or len(hr_points) < 10:
        return summary

    hrs = [p.get("hr", 0) for p in hr_points if p.get("hr", 0) > 0]
    timestamps = [p.get("timestamp", 0) for p in hr_points]

    if len(hrs) < 10:
        return summary

    # Basic statistics
    summary.mean = statistics.mean(hrs)
    summary.std_dev = statistics.stdev(hrs) if len(hrs) > 1 else 0
    summary.cv = (summary.std_dev / summary.mean * 100) if summary.mean > 0 else 0

    # Peak HR and timing
    summary.peak_hr = max(hrs)
    peak_idx = hrs.index(summary.peak_hr)
    total_duration = max(timestamps) - min(timestamps) if timestamps else duration_sec
    if total_duration > 0 and peak_idx < len(timestamps):
        summary.peak_time_pct = (timestamps[peak_idx] / total_duration) * 100

    # HR Drift: Compare first 10 min to last 10 min
    ten_min_sec = 600
    first_10_hrs = [p.get("hr", 0) for p in hr_points if p.get("timestamp", 0) < ten_min_sec and p.get("hr", 0) > 0]
    last_10_hrs = [p.get("hr", 0) for p in hr_points if p.get("timestamp", 0) > (total_duration - ten_min_sec) and p.get("hr", 0) > 0]

    if first_10_hrs and last_10_hrs:
        first_avg = statistics.mean(first_10_hrs)
        last_avg = statistics.mean(last_10_hrs)
        summary.hr_drift = ((last_avg - first_avg) / first_avg) * 100 if first_avg > 0 else 0
        summary.hr_drift_bpm = int(last_avg - first_avg)

    # Time to steady state (when 30-sec rolling avg stabilizes within 5% of overall avg)
    if len(hrs) > 30:
        window_size = 30
        overall_avg = summary.mean
        threshold = overall_avg * 0.05

        for i in range(len(hrs) - window_size):
            window_avg = statistics.mean(hrs[i:i + window_size])
            if abs(window_avg - overall_avg) < threshold:
                if i < len(timestamps):
                    summary.time_to_steady_sec = timestamps[i]
                break

    # Zone transitions (if zones provided)
    if hr_zones:
        current_zone = None
        transitions = 0
        zone_times: Dict[int, int] = {z: 0 for z in hr_zones.keys()}

        for hr in hrs:
            for zone, (min_hr, max_hr) in hr_zones.items():
                if min_hr <= hr <= max_hr:
                    zone_times[zone] = zone_times.get(zone, 0) + 1
                    if current_zone is not None and current_zone != zone:
                        transitions += 1
                    current_zone = zone
                    break

        summary.zone_transitions = transitions
        if zone_times:
            summary.dominant_zone = max(zone_times, key=zone_times.get)

    # Detect if this is an interval workout
    summary.is_interval_workout = summary.cv > 12 and summary.zone_transitions > 6

    return summary


def calculate_pace_summary(
    pace_points: List[Dict[str, Any]],
    splits: Optional[List[Dict[str, Any]]] = None
) -> PaceSummary:
    """
    Calculate pace summary from time-series or splits data.

    Args:
        pace_points: List of {timestamp: int, value: float} (pace in sec/km)
        splits: Optional list of split data with pace info

    Returns:
        PaceSummary with calculated statistics
    """
    summary = PaceSummary()

    # Use splits if available (more reliable than raw time-series)
    if splits and len(splits) >= 2:
        paces = []
        for split in splits:
            pace = split.get("pace") or split.get("avg_pace") or split.get("duration", 0)
            if pace and pace > 0:
                paces.append(pace)

        if len(paces) >= 2:
            summary.mean_pace = statistics.mean(paces)
            summary.std_dev = statistics.stdev(paces)
            cv = (summary.std_dev / summary.mean_pace * 100) if summary.mean_pace > 0 else 0
            summary.consistency_score = max(0, min(100, 100 - (cv * 5)))

            # Best and worst
            summary.best_km_pace = min(paces)
            summary.worst_km_pace = max(paces)
            summary.fastest_split = paces.index(summary.best_km_pace) + 1
            summary.slowest_split = paces.index(summary.worst_km_pace) + 1
            summary.best_worst_delta = summary.worst_km_pace - summary.best_km_pace

            # Split analysis
            mid = len(paces) // 2
            first_half = paces[:mid]
            second_half = paces[mid:]
            if first_half and second_half:
                first_avg = statistics.mean(first_half)
                second_avg = statistics.mean(second_half)
                summary.negative_split_ratio = second_avg / first_avg if first_avg > 0 else 1.0

            # Fade index
            quarter = max(1, len(paces) // 4)
            first_quarter = paces[:quarter]
            last_quarter = paces[-quarter:]
            if first_quarter and last_quarter:
                first_q_avg = statistics.mean(first_quarter)
                last_q_avg = statistics.mean(last_quarter)
                summary.fade_index = last_q_avg / first_q_avg if first_q_avg > 0 else 1.0

            # Trend detection (simple linear regression)
            if len(paces) >= 3:
                n = len(paces)
                x_mean = (n - 1) / 2
                y_mean = summary.mean_pace

                numerator = sum((i - x_mean) * (p - y_mean) for i, p in enumerate(paces))
                denominator = sum((i - x_mean) ** 2 for i in range(n))

                if denominator > 0:
                    summary.trend_slope = numerator / denominator

                    # Classify trend
                    if abs(summary.trend_slope) < 2:
                        summary.trend = TrendDirection.STEADY
                    elif summary.trend_slope < -2:
                        summary.trend = TrendDirection.ACCELERATING
                    elif summary.trend_slope > 2:
                        summary.trend = TrendDirection.DECELERATING

                    # Check for high variability
                    if cv > 15:
                        summary.trend = TrendDirection.VARIABLE

    # Fallback to raw pace points if no splits
    elif pace_points and len(pace_points) >= 10:
        paces = [p.get("value", 0) for p in pace_points if 120 < p.get("value", 0) < 900]  # 2:00-15:00/km
        if paces:
            summary.mean_pace = statistics.mean(paces)
            summary.std_dev = statistics.stdev(paces) if len(paces) > 1 else 0
            cv = (summary.std_dev / summary.mean_pace * 100) if summary.mean_pace > 0 else 0
            summary.consistency_score = max(0, min(100, 100 - (cv * 3)))  # Less strict for raw data
            summary.best_km_pace = min(paces)
            summary.worst_km_pace = max(paces)
            summary.best_worst_delta = summary.worst_km_pace - summary.best_km_pace

    return summary


def calculate_elevation_summary(
    elevation_points: List[Dict[str, Any]],
    distance_km: float = 0.0
) -> ElevationSummary:
    """
    Calculate elevation summary from time-series data.

    Args:
        elevation_points: List of {timestamp: int, elevation: float}
        distance_km: Total distance for grade calculations

    Returns:
        ElevationSummary with calculated statistics
    """
    summary = ElevationSummary()

    if not elevation_points or len(elevation_points) < 5:
        return summary

    elevations = [p.get("elevation", 0) for p in elevation_points]

    # Calculate gain and loss
    total_gain = 0.0
    total_loss = 0.0
    climb_count = 0
    current_climb_gain = 0.0
    climbing = False
    grades = []

    for i in range(1, len(elevations)):
        delta = elevations[i] - elevations[i - 1]

        if delta > 0:
            total_gain += delta
            current_climb_gain += delta
            if not climbing:
                climbing = True
        else:
            total_loss += abs(delta)
            if climbing and current_climb_gain > 10:  # Significant climb
                climb_count += 1
                if distance_km > 0:
                    # Approximate grade for this climb
                    climb_distance = distance_km * 1000 / len(elevations) * 10  # rough estimate
                    if climb_distance > 0:
                        grade = (current_climb_gain / climb_distance) * 100
                        grades.append(grade)
            climbing = False
            current_climb_gain = 0

    # Handle final climb
    if climbing and current_climb_gain > 10:
        climb_count += 1

    summary.total_gain_m = total_gain
    summary.total_loss_m = total_loss
    summary.net_change = total_gain - total_loss
    summary.climb_count = climb_count

    if grades:
        summary.avg_climb_grade_pct = statistics.mean(grades)
        summary.max_grade_pct = max(grades)

    # Terrain classification
    if total_gain < 50:
        summary.terrain_type = TerrainType.FLAT
    elif total_gain < 200:
        summary.terrain_type = TerrainType.ROLLING
    elif total_gain < 500:
        summary.terrain_type = TerrainType.HILLY
    else:
        summary.terrain_type = TerrainType.MOUNTAINOUS

    return summary


def calculate_splits_summary(splits: List[Dict[str, Any]]) -> SplitsSummary:
    """
    Calculate splits summary from per-km/mile split data.

    Args:
        splits: List of split data dicts with pace, duration, etc.

    Returns:
        SplitsSummary with calculated statistics
    """
    summary = SplitsSummary()

    if not splits or len(splits) < 2:
        return summary

    # Extract paces
    paces = []
    for split in splits:
        pace = split.get("pace") or split.get("avg_pace") or split.get("duration", 0)
        if pace and 120 < pace < 900:  # 2:00-15:00/km sanity check
            paces.append(pace)

    if len(paces) < 2:
        return summary

    summary.total_splits = len(paces)
    summary.avg_pace = statistics.mean(paces)

    # Best/worst
    summary.fastest_pace = min(paces)
    summary.slowest_pace = max(paces)
    summary.fastest_split = paces.index(summary.fastest_pace) + 1
    summary.slowest_split = paces.index(summary.slowest_pace) + 1

    # Splits within 5% of average
    threshold = summary.avg_pace * 0.05
    summary.splits_within_5pct = sum(1 for p in paces if abs(p - summary.avg_pace) <= threshold)

    # Half comparison
    mid = len(paces) // 2
    summary.first_half_avg = statistics.mean(paces[:mid])
    summary.second_half_avg = statistics.mean(paces[mid:])

    # Even split score
    if summary.first_half_avg > 0:
        diff_pct = abs(summary.first_half_avg - summary.second_half_avg) / summary.avg_pace * 100
        summary.even_split_score = max(0, min(100, 100 - (diff_pct * 5)))

    # Trend (simple linear regression)
    n = len(paces)
    x_mean = (n - 1) / 2
    y_mean = summary.avg_pace

    numerator = sum((i - x_mean) * (p - y_mean) for i, p in enumerate(paces))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator > 0:
        summary.trend_slope = numerator / denominator

        if abs(summary.trend_slope) < 2:
            summary.trend = TrendDirection.STEADY
        elif summary.trend_slope < -2:
            summary.trend = TrendDirection.ACCELERATING
        else:
            summary.trend = TrendDirection.DECELERATING

        # Check for high variability
        cv = statistics.stdev(paces) / summary.avg_pace * 100 if summary.avg_pace > 0 else 0
        if cv > 12:
            summary.trend = TrendDirection.VARIABLE

    return summary


def extract_insights(
    hr_summary: Optional[HRSummary],
    pace_summary: Optional[PaceSummary],
    elevation_summary: Optional[ElevationSummary],
    splits_summary: Optional[SplitsSummary]
) -> List[str]:
    """
    Extract coaching-relevant insights from summaries.

    Returns list of short insight strings.
    """
    insights = []

    # HR insights
    if hr_summary and hr_summary.mean > 0:
        if hr_summary.hr_drift > 8:
            insights.append(f"Cardiac drift: +{hr_summary.hr_drift:.0f}% (hydration/fatigue concern)")
        elif hr_summary.hr_drift < -5:
            insights.append(f"HR decreased over time (good aerobic efficiency)")

        if hr_summary.cv < 6:
            insights.append("Exceptionally steady HR (well-controlled effort)")
        elif hr_summary.is_interval_workout:
            insights.append("Interval pattern detected")

    # Pace insights
    if pace_summary and pace_summary.mean_pace > 0:
        if pace_summary.negative_split_ratio < 0.97:
            insights.append("Strong negative split execution")
        elif pace_summary.negative_split_ratio > 1.05:
            insights.append("Positive split - started too fast")

        if pace_summary.fade_index > 1.12:
            insights.append(f"Significant fade in final quarter ({(pace_summary.fade_index - 1) * 100:.0f}% slower)")
        elif pace_summary.fade_index < 0.92:
            insights.append("Strong finish - accelerated in final quarter")

        if pace_summary.consistency_score >= 92:
            insights.append("Exceptional pacing consistency")

    # Elevation insights
    if elevation_summary and elevation_summary.total_gain_m > 100:
        if elevation_summary.terrain_type == TerrainType.MOUNTAINOUS:
            insights.append(f"Mountainous terrain: {elevation_summary.total_gain_m:.0f}m gain")

    # Splits insights
    if splits_summary and splits_summary.total_splits > 0:
        if splits_summary.even_split_score >= 95:
            insights.append("Near-perfect even pacing")
        elif splits_summary.even_split_score < 65:
            insights.append("Uneven pacing - room for improvement")

        if splits_summary.fastest_split == 1:
            insights.append("Fastest km was first - consider controlled start")
        elif splits_summary.fastest_split == splits_summary.total_splits:
            insights.append("Fastest km was last - strong finishing kick")

    return insights


def condense_workout_data(
    time_series: Optional[Dict[str, Any]] = None,
    splits: Optional[List[Dict[str, Any]]] = None,
    hr_zones: Optional[Dict[int, Tuple[int, int]]] = None,
    duration_sec: int = 0,
    distance_km: float = 0.0
) -> CondensedWorkoutData:
    """
    Main function to condense all workout time-series data.

    Args:
        time_series: Dict with heart_rate, pace_or_speed, elevation, cadence lists
        splits: List of per-km split data
        hr_zones: Dict of zone -> (min_hr, max_hr)
        duration_sec: Total workout duration in seconds
        distance_km: Total distance in km

    Returns:
        CondensedWorkoutData ready for LLM consumption
    """
    condensed = CondensedWorkoutData()

    if time_series:
        # HR summary
        hr_points = time_series.get("heart_rate", [])
        if hr_points:
            condensed.hr_summary = calculate_hr_summary(hr_points, hr_zones, duration_sec)

        # Pace summary
        pace_points = time_series.get("pace_or_speed", [])
        condensed.pace_summary = calculate_pace_summary(pace_points, splits)

        # Elevation summary
        elevation_points = time_series.get("elevation", [])
        if elevation_points:
            condensed.elevation_summary = calculate_elevation_summary(elevation_points, distance_km)

    # Splits summary
    if splits:
        condensed.splits_summary = calculate_splits_summary(splits)

        # Also calculate pace from splits if not done
        if not condensed.pace_summary or condensed.pace_summary.mean_pace == 0:
            condensed.pace_summary = calculate_pace_summary([], splits)

    # Extract insights
    condensed.insights = extract_insights(
        condensed.hr_summary,
        condensed.pace_summary,
        condensed.elevation_summary,
        condensed.splits_summary
    )

    return condensed
