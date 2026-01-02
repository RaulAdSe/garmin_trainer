"""
Workout Comparison Service.

Provides functionality for comparing workouts and normalizing time series data
for overlay comparison in charts.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class NormalizationMode(str, Enum):
    """Normalization mode for workout comparison."""
    TIME = "time"  # Normalize by elapsed time
    DISTANCE = "distance"  # Normalize by distance (percentage of total)
    PERCENTAGE = "percentage"  # Normalize by percentage of workout completion


@dataclass
class ComparisonTarget:
    """A workout available for comparison."""
    activity_id: str
    name: str
    activity_type: str
    date: str
    duration_min: float
    distance_km: Optional[float] = None
    avg_hr: Optional[int] = None
    avg_pace_sec_km: Optional[float] = None
    similarity_score: float = 0.0
    is_pr: bool = False
    quick_selection_type: Optional[str] = None  # "best_10k", "last_similar", "pr"


@dataclass
class NormalizedTimeSeries:
    """Time series data normalized for comparison."""
    timestamps: List[float]  # Normalized timestamps (0 to 100 for percentage)
    heart_rate: List[Optional[float]] = field(default_factory=list)
    pace: List[Optional[float]] = field(default_factory=list)
    power: List[Optional[float]] = field(default_factory=list)
    cadence: List[Optional[float]] = field(default_factory=list)
    elevation: List[Optional[float]] = field(default_factory=list)


@dataclass
class ComparisonStats:
    """Statistics comparing two workouts."""
    hr_avg_diff: Optional[float] = None  # Difference in average HR
    hr_max_diff: Optional[float] = None  # Difference in max HR
    pace_avg_diff: Optional[float] = None  # Difference in average pace
    power_avg_diff: Optional[float] = None  # Difference in average power
    duration_diff: float = 0.0  # Difference in duration (seconds)
    distance_diff: Optional[float] = None  # Difference in distance (meters)
    improvement_metrics: Dict[str, float] = field(default_factory=dict)  # % improvement per metric


@dataclass
class WorkoutComparison:
    """Complete comparison between two workouts."""
    primary_id: str
    comparison_id: str
    normalization_mode: NormalizationMode
    primary_series: NormalizedTimeSeries
    comparison_series: NormalizedTimeSeries
    stats: ComparisonStats
    sample_count: int = 100  # Number of normalized sample points


class ComparisonService:
    """
    Service for comparing workouts and normalizing time series data.
    """

    def __init__(self, training_db, workout_repository=None):
        self._training_db = training_db
        self._workout_repository = workout_repository

    def find_comparable_workouts(
        self,
        activity_id: str,
        user_id: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ComparisonTarget]:
        """
        Find workouts comparable to the given activity.

        Finds similar workouts based on:
        - Activity type match
        - Similar distance (within 20%)
        - Similar duration (within 30%)

        Also includes quick selection targets like "Best 10K" and "PR workouts".

        Args:
            activity_id: The reference activity ID
            user_id: The user's ID
            limit: Maximum number of results
            filters: Optional filters (workout_type, date_range, min_distance, max_distance)

        Returns:
            List of comparable workout targets with similarity scores
        """
        # Get the reference activity
        reference = self._training_db.get_activity_metrics(activity_id)
        if not reference:
            return []

        # Get all user activities
        all_activities = self._training_db.get_all_activity_metrics(user_id)
        if not all_activities:
            return []

        # Filter and score activities
        comparable = []
        for activity in all_activities:
            # Skip the reference activity itself
            if activity.activity_id == activity_id:
                continue

            # Apply filters
            if filters:
                if filters.get("workout_type") and activity.activity_type != filters["workout_type"]:
                    continue
                if filters.get("date_start"):
                    if activity.date < filters["date_start"]:
                        continue
                if filters.get("date_end"):
                    if activity.date > filters["date_end"]:
                        continue
                if filters.get("min_distance") and activity.distance_km:
                    if activity.distance_km < filters["min_distance"]:
                        continue
                if filters.get("max_distance") and activity.distance_km:
                    if activity.distance_km > filters["max_distance"]:
                        continue

            # Calculate similarity score
            similarity = self._calculate_similarity(reference, activity)
            if similarity > 0.3:  # Minimum threshold
                target = ComparisonTarget(
                    activity_id=activity.activity_id,
                    name=activity.activity_name or f"{activity.activity_type} - {activity.date}",
                    activity_type=activity.activity_type or "unknown",
                    date=activity.date,
                    duration_min=activity.duration_min or 0.0,
                    distance_km=activity.distance_km,
                    avg_hr=activity.avg_hr,
                    avg_pace_sec_km=activity.pace_sec_per_km,
                    similarity_score=similarity,
                )
                comparable.append(target)

        # Sort by similarity and limit
        comparable.sort(key=lambda x: x.similarity_score, reverse=True)

        # Add quick selections
        quick_selections = self._find_quick_selections(reference, comparable)

        # Merge quick selections at the front
        result = quick_selections + [c for c in comparable if c not in quick_selections]

        return result[:limit]

    def _calculate_similarity(self, reference, candidate) -> float:
        """
        Calculate similarity score between two activities.

        Score is based on:
        - Activity type match (40% weight)
        - Distance similarity (30% weight)
        - Duration similarity (30% weight)
        """
        score = 0.0

        # Activity type match
        if reference.activity_type == candidate.activity_type:
            score += 0.4
        elif self._are_similar_types(reference.activity_type, candidate.activity_type):
            score += 0.2

        # Distance similarity (within 20%)
        if reference.distance_km and candidate.distance_km:
            distance_ratio = min(reference.distance_km, candidate.distance_km) / max(reference.distance_km, candidate.distance_km)
            if distance_ratio > 0.8:
                score += 0.3 * distance_ratio
            elif distance_ratio > 0.5:
                score += 0.15 * distance_ratio
        elif not reference.distance_km and not candidate.distance_km:
            # Both have no distance - partial match
            score += 0.15

        # Duration similarity (within 30%)
        if reference.duration_min and candidate.duration_min:
            duration_ratio = min(reference.duration_min, candidate.duration_min) / max(reference.duration_min, candidate.duration_min)
            if duration_ratio > 0.7:
                score += 0.3 * duration_ratio
            elif duration_ratio > 0.4:
                score += 0.15 * duration_ratio
        elif not reference.duration_min and not candidate.duration_min:
            score += 0.15

        return score

    def _are_similar_types(self, type1: str, type2: str) -> bool:
        """Check if two activity types are similar."""
        similar_groups = [
            {"running", "trail_running", "treadmill_running", "track_running"},
            {"cycling", "road_biking", "mountain_biking", "indoor_cycling"},
            {"swimming", "pool_swimming", "open_water_swimming"},
            {"walking", "hiking"},
        ]

        type1_lower = (type1 or "").lower()
        type2_lower = (type2 or "").lower()

        for group in similar_groups:
            if type1_lower in group and type2_lower in group:
                return True

        return False

    def _find_quick_selections(
        self,
        reference,
        candidates: List[ComparisonTarget],
    ) -> List[ComparisonTarget]:
        """
        Find quick selection targets (Best 10K, Last Similar, PR).
        """
        quick_selections = []

        # Find "Last Similar" - most recent similar workout
        if candidates:
            # Sort by date to find most recent
            by_date = sorted(candidates, key=lambda x: x.date, reverse=True)
            for c in by_date:
                if c.similarity_score > 0.6:
                    c.quick_selection_type = "last_similar"
                    quick_selections.append(c)
                    break

        # Find best workout by pace for the same activity type
        same_type = [c for c in candidates if c.activity_type == reference.activity_type]
        if same_type:
            # For running: lower pace is better
            with_pace = [c for c in same_type if c.avg_pace_sec_km and c.avg_pace_sec_km > 0]
            if with_pace:
                best_pace = min(with_pace, key=lambda x: x.avg_pace_sec_km or float('inf'))
                if best_pace not in quick_selections:
                    best_pace.quick_selection_type = "best_pace"
                    best_pace.is_pr = True
                    quick_selections.append(best_pace)

        # Find distance-specific PRs (e.g., Best 10K)
        distance_categories = [
            (4.8, 5.2, "best_5k"),
            (9.5, 10.5, "best_10k"),
            (20, 22, "best_half_marathon"),
            (40, 44, "best_marathon"),
        ]

        ref_distance = reference.distance_km or 0
        for min_d, max_d, label in distance_categories:
            if min_d <= ref_distance <= max_d:
                # Find best in this distance category
                in_category = [
                    c for c in same_type
                    if c.distance_km and min_d <= c.distance_km <= max_d
                ]
                if in_category:
                    best = min(in_category, key=lambda x: x.avg_pace_sec_km or float('inf'))
                    if best not in quick_selections:
                        best.quick_selection_type = label
                        best.is_pr = True
                        quick_selections.append(best)
                break

        return quick_selections

    def get_normalized_data(
        self,
        activity_id: str,
        mode: NormalizationMode = NormalizationMode.PERCENTAGE,
        sample_count: int = 100,
    ) -> Optional[NormalizedTimeSeries]:
        """
        Get time series data normalized for comparison.

        Args:
            activity_id: The activity ID
            mode: Normalization mode (time, distance, percentage)
            sample_count: Number of output sample points

        Returns:
            Normalized time series data or None if not available
        """
        # This would typically fetch from Garmin API - for now we simulate
        # In a real implementation, this would call the workouts route
        # to get activity details and normalize the time series

        # Placeholder: return empty normalized series
        return NormalizedTimeSeries(
            timestamps=list(range(sample_count)),
            heart_rate=[None] * sample_count,
            pace=[None] * sample_count,
            power=[None] * sample_count,
            cadence=[None] * sample_count,
            elevation=[None] * sample_count,
        )

    def normalize_time_series(
        self,
        time_series: Dict[str, List[Dict[str, Any]]],
        mode: NormalizationMode = NormalizationMode.PERCENTAGE,
        sample_count: int = 100,
    ) -> NormalizedTimeSeries:
        """
        Normalize raw time series data to fixed sample count.

        Args:
            time_series: Raw time series data from activity details
            mode: Normalization mode
            sample_count: Number of output sample points

        Returns:
            Normalized time series data
        """
        result = NormalizedTimeSeries(
            timestamps=[i / (sample_count - 1) * 100 for i in range(sample_count)],
        )

        # Normalize each metric
        if "heart_rate" in time_series and time_series["heart_rate"]:
            result.heart_rate = self._resample_series(
                time_series["heart_rate"],
                "hr",
                sample_count,
            )

        if "pace_or_speed" in time_series and time_series["pace_or_speed"]:
            result.pace = self._resample_series(
                time_series["pace_or_speed"],
                "value",
                sample_count,
            )

        if "power" in time_series and time_series["power"]:
            result.power = self._resample_series(
                time_series["power"],
                "power",
                sample_count,
            )

        if "cadence" in time_series and time_series["cadence"]:
            result.cadence = self._resample_series(
                time_series["cadence"],
                "cadence",
                sample_count,
            )

        if "elevation" in time_series and time_series["elevation"]:
            result.elevation = self._resample_series(
                time_series["elevation"],
                "elevation",
                sample_count,
            )

        return result

    def _resample_series(
        self,
        data: List[Dict[str, Any]],
        value_key: str,
        target_count: int,
    ) -> List[Optional[float]]:
        """
        Resample a time series to the target number of samples.
        Uses linear interpolation.
        """
        if not data:
            return [None] * target_count

        # Extract values and timestamps
        values = []
        timestamps = []
        for point in data:
            if value_key in point and point[value_key] is not None:
                values.append(float(point[value_key]))
                timestamps.append(float(point.get("timestamp", len(timestamps))))

        if not values:
            return [None] * target_count

        # Normalize timestamps to 0-1 range
        min_ts = min(timestamps)
        max_ts = max(timestamps)
        if max_ts == min_ts:
            return [values[0]] * target_count

        normalized_ts = [(t - min_ts) / (max_ts - min_ts) for t in timestamps]

        # Interpolate to target count
        result = []
        for i in range(target_count):
            target_t = i / (target_count - 1)

            # Find surrounding points
            left_idx = 0
            for j, t in enumerate(normalized_ts):
                if t <= target_t:
                    left_idx = j
                else:
                    break

            right_idx = min(left_idx + 1, len(normalized_ts) - 1)

            if left_idx == right_idx:
                result.append(values[left_idx])
            else:
                # Linear interpolation
                t_left = normalized_ts[left_idx]
                t_right = normalized_ts[right_idx]
                v_left = values[left_idx]
                v_right = values[right_idx]

                if t_right == t_left:
                    result.append(v_left)
                else:
                    ratio = (target_t - t_left) / (t_right - t_left)
                    interpolated = v_left + ratio * (v_right - v_left)
                    result.append(interpolated)

        return result

    def calculate_comparison_stats(
        self,
        primary_series: NormalizedTimeSeries,
        comparison_series: NormalizedTimeSeries,
        primary_info: Optional[Dict[str, Any]] = None,
        comparison_info: Optional[Dict[str, Any]] = None,
    ) -> ComparisonStats:
        """
        Calculate comparison statistics between two normalized series.
        """
        stats = ComparisonStats()

        # Heart rate comparison
        primary_hr = [v for v in primary_series.heart_rate if v is not None]
        comparison_hr = [v for v in comparison_series.heart_rate if v is not None]

        if primary_hr and comparison_hr:
            primary_avg_hr = sum(primary_hr) / len(primary_hr)
            comparison_avg_hr = sum(comparison_hr) / len(comparison_hr)
            stats.hr_avg_diff = primary_avg_hr - comparison_avg_hr

            primary_max_hr = max(primary_hr)
            comparison_max_hr = max(comparison_hr)
            stats.hr_max_diff = primary_max_hr - comparison_max_hr

            # Calculate improvement percentage
            if comparison_avg_hr > 0:
                stats.improvement_metrics["hr_efficiency"] = (
                    (comparison_avg_hr - primary_avg_hr) / comparison_avg_hr * 100
                )

        # Pace comparison (lower is better for running)
        primary_pace = [v for v in primary_series.pace if v is not None and v > 0]
        comparison_pace = [v for v in comparison_series.pace if v is not None and v > 0]

        if primary_pace and comparison_pace:
            primary_avg_pace = sum(primary_pace) / len(primary_pace)
            comparison_avg_pace = sum(comparison_pace) / len(comparison_pace)
            stats.pace_avg_diff = primary_avg_pace - comparison_avg_pace

            # Improvement: negative diff is improvement for pace
            if comparison_avg_pace > 0:
                stats.improvement_metrics["pace"] = (
                    (comparison_avg_pace - primary_avg_pace) / comparison_avg_pace * 100
                )

        # Power comparison
        primary_power = [v for v in primary_series.power if v is not None and v > 0]
        comparison_power = [v for v in comparison_series.power if v is not None and v > 0]

        if primary_power and comparison_power:
            primary_avg_power = sum(primary_power) / len(primary_power)
            comparison_avg_power = sum(comparison_power) / len(comparison_power)
            stats.power_avg_diff = primary_avg_power - comparison_avg_power

            if comparison_avg_power > 0:
                stats.improvement_metrics["power"] = (
                    (primary_avg_power - comparison_avg_power) / comparison_avg_power * 100
                )

        # Duration and distance from basic info
        if primary_info and comparison_info:
            primary_duration = primary_info.get("duration_sec", 0)
            comparison_duration = comparison_info.get("duration_sec", 0)
            stats.duration_diff = primary_duration - comparison_duration

            primary_distance = primary_info.get("distance_m")
            comparison_distance = comparison_info.get("distance_m")
            if primary_distance and comparison_distance:
                stats.distance_diff = primary_distance - comparison_distance

        return stats

    def compare_workouts(
        self,
        primary_id: str,
        comparison_id: str,
        mode: NormalizationMode = NormalizationMode.PERCENTAGE,
        sample_count: int = 100,
    ) -> Optional[WorkoutComparison]:
        """
        Compare two workouts and return normalized data for overlay.

        Args:
            primary_id: Primary workout ID (current workout)
            comparison_id: Comparison workout ID
            mode: Normalization mode
            sample_count: Number of sample points

        Returns:
            Complete workout comparison or None if data not available
        """
        # Get normalized data for both workouts
        primary_series = self.get_normalized_data(primary_id, mode, sample_count)
        comparison_series = self.get_normalized_data(comparison_id, mode, sample_count)

        if not primary_series or not comparison_series:
            return None

        # Calculate stats
        stats = self.calculate_comparison_stats(primary_series, comparison_series)

        return WorkoutComparison(
            primary_id=primary_id,
            comparison_id=comparison_id,
            normalization_mode=mode,
            primary_series=primary_series,
            comparison_series=comparison_series,
            stats=stats,
            sample_count=sample_count,
        )
