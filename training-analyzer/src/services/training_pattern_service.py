"""
Training Pattern Service for detecting training patterns from workout history.

This service is part of the AI agentic system. Instead of asking the user
"How many days per week do you train?", the AI uses this service to detect
patterns automatically from the activity database.

Pattern detection includes:
- Training frequency (days per week)
- Typical long run day
- Rest days
- Session durations
- Cross-training activities
- Preferred workout times
- Weekly distance and load averages
"""

import sqlite3
import statistics
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from contextlib import contextmanager

from ..db.database import TrainingDatabase, get_default_db_path


@dataclass
class TrainingPatterns:
    """
    Detected training patterns from workout history.

    This dataclass captures the athlete's training habits as detected
    from their historical activity data. Used by the AI agent to understand
    the athlete's routine without asking questions.
    """

    # Training frequency (8-week rolling average)
    avg_days_per_week: float

    # Day of week for long runs (0=Monday, 6=Sunday)
    typical_long_run_day: Optional[int] = None

    # Days with consistently zero activity (0=Monday, 6=Sunday)
    typical_rest_days: List[int] = field(default_factory=list)

    # 90th percentile of session durations in minutes
    max_session_duration_min: int = 60

    # Whether athlete does strength training
    does_strength: bool = False

    # Whether athlete cross-trains (cycling, swimming, etc.)
    does_cross_training: bool = False

    # Preferred time of day: "morning", "afternoon", or "evening"
    preferred_time_of_day: str = "morning"

    # Average weekly running distance in km
    avg_weekly_distance_km: float = 0.0

    # Average weekly training load (HRSS/TRIMP)
    avg_weekly_load: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "avg_days_per_week": round(self.avg_days_per_week, 1),
            "typical_long_run_day": self.typical_long_run_day,
            "typical_long_run_day_name": self._day_name(self.typical_long_run_day),
            "typical_rest_days": self.typical_rest_days,
            "typical_rest_days_names": [self._day_name(d) for d in self.typical_rest_days],
            "max_session_duration_min": self.max_session_duration_min,
            "does_strength": self.does_strength,
            "does_cross_training": self.does_cross_training,
            "preferred_time_of_day": self.preferred_time_of_day,
            "avg_weekly_distance_km": round(self.avg_weekly_distance_km, 1),
            "avg_weekly_load": round(self.avg_weekly_load, 1),
        }

    @staticmethod
    def _day_name(day_index: Optional[int]) -> Optional[str]:
        """Convert day index to name."""
        if day_index is None:
            return None
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        if 0 <= day_index <= 6:
            return days[day_index]
        return None


class TrainingPatternService:
    """
    Service for detecting training patterns from workout history.

    This service analyzes the athlete's activity database to detect
    patterns that would otherwise require asking the user. The AI agent
    can use this service to understand:

    - How often the athlete trains
    - When they typically do long runs
    - Which days they rest
    - Whether they do strength training or cross-training
    - When they prefer to work out
    - Their typical weekly volume

    Example usage:
        service = TrainingPatternService()
        patterns = service.detect_all()
        # Access pattern data:
        # patterns.avg_days_per_week -> training frequency
        # patterns.typical_long_run_day_name -> long run day
    """

    # Constants for pattern detection
    WEEKS_TO_ANALYZE = 8  # Rolling window for frequency analysis
    LONG_RUN_MIN_DISTANCE_KM = 15.0  # Minimum distance for "long run"
    LONG_RUN_MIN_DURATION_MIN = 90  # Minimum duration for "long run"
    REST_DAY_THRESHOLD_PCT = 80  # Percent of weeks with no activity to be "rest day"

    # Sport type detection patterns
    STRENGTH_SPORT_TYPES = [
        "strength", "weight", "gym", "fitness", "training",
        "cross_training", "workout", "functional"
    ]
    CROSS_TRAINING_SPORT_TYPES = [
        "cycling", "swimming", "biking", "bike", "pool",
        "elliptical", "rowing", "ski", "skate", "hike", "hiking"
    ]

    # Time of day buckets (hour ranges)
    TIME_BUCKETS = {
        "morning": (5, 12),     # 5:00 AM - 12:00 PM
        "afternoon": (12, 17),  # 12:00 PM - 5:00 PM
        "evening": (17, 22),    # 5:00 PM - 10:00 PM
    }

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        training_db: Optional[TrainingDatabase] = None,
    ):
        """
        Initialize the training pattern service.

        Args:
            db_path: Path to SQLite database. If not provided, uses default.
            training_db: TrainingDatabase instance. If provided, uses this instead.
        """
        if training_db is not None:
            self._training_db = training_db
            self._db_path = training_db.db_path
        else:
            self._db_path = Path(db_path) if db_path else get_default_db_path()
            self._training_db = None

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        if self._training_db is not None:
            # Use the training database's connection mechanism
            with self._training_db._get_connection() as conn:
                yield conn
        else:
            # Create our own connection
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def detect_all(self, user_id: Optional[str] = None) -> TrainingPatterns:
        """
        Detect all training patterns from workout history.

        This is the main entry point for the AI agent to get athlete patterns.
        All patterns are detected from the last 8 weeks of activity data.

        Args:
            user_id: Optional user ID for multi-tenant filtering (future use)

        Returns:
            TrainingPatterns dataclass with all detected patterns
        """
        end_date = date.today()
        start_date = end_date - timedelta(weeks=self.WEEKS_TO_ANALYZE)

        # Fetch activities for the analysis window
        activities = self._fetch_activities(start_date, end_date)

        if not activities:
            # Return defaults if no activities
            return TrainingPatterns(
                avg_days_per_week=0.0,
                typical_long_run_day=None,
                typical_rest_days=list(range(7)),  # All days are rest days
                max_session_duration_min=0,
                does_strength=False,
                does_cross_training=False,
                preferred_time_of_day="morning",
                avg_weekly_distance_km=0.0,
                avg_weekly_load=0.0,
            )

        # Detect each pattern
        avg_days = self._detect_avg_days_per_week(activities, start_date, end_date)
        long_run_day = self._detect_long_run_day(activities)
        rest_days = self._detect_rest_days(activities, start_date, end_date)
        max_duration = self._detect_max_session_duration(activities)
        does_strength = self._detect_strength_training(activities)
        does_cross = self._detect_cross_training(activities)
        time_pref = self._detect_preferred_time(activities)
        weekly_distance = self._detect_avg_weekly_distance(activities, start_date, end_date)
        weekly_load = self._detect_avg_weekly_load(activities, start_date, end_date)

        return TrainingPatterns(
            avg_days_per_week=avg_days,
            typical_long_run_day=long_run_day,
            typical_rest_days=rest_days,
            max_session_duration_min=max_duration,
            does_strength=does_strength,
            does_cross_training=does_cross,
            preferred_time_of_day=time_pref,
            avg_weekly_distance_km=weekly_distance,
            avg_weekly_load=weekly_load,
        )

    def _fetch_activities(
        self,
        start_date: date,
        end_date: date,
    ) -> List[Dict]:
        """
        Fetch activities from the database for the given date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of activity dictionaries with relevant fields
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    activity_id,
                    date,
                    start_time,
                    sport_type,
                    activity_type,
                    duration_min,
                    distance_km,
                    hrss,
                    trimp
                FROM activity_metrics
                WHERE date >= ? AND date <= ?
                ORDER BY date DESC
                """,
                (start_date.isoformat(), end_date.isoformat()),
            ).fetchall()

            return [dict(row) for row in rows]

    def _detect_avg_days_per_week(
        self,
        activities: List[Dict],
        start_date: date,
        end_date: date,
    ) -> float:
        """
        Calculate average training days per week.

        Counts distinct dates with activities in the analysis window,
        then divides by the number of weeks.

        Args:
            activities: List of activity dictionaries
            start_date: Start of analysis window
            end_date: End of analysis window

        Returns:
            Average days per week (0.0 to 7.0)
        """
        # Get unique dates with activities
        unique_dates = set()
        for activity in activities:
            activity_date = activity.get("date")
            if activity_date:
                if isinstance(activity_date, str):
                    unique_dates.add(activity_date)
                else:
                    unique_dates.add(activity_date.isoformat())

        # Calculate number of weeks in the window
        total_days = (end_date - start_date).days + 1
        weeks = max(1, total_days / 7)

        return len(unique_dates) / weeks

    def _detect_long_run_day(self, activities: List[Dict]) -> Optional[int]:
        """
        Detect the typical day for long runs.

        A "long run" is defined as:
        - Distance >= 15km, OR
        - Duration >= 90 minutes

        Returns the mode of weekdays for long runs.

        Args:
            activities: List of activity dictionaries

        Returns:
            Day index (0=Monday, 6=Sunday) or None if no long runs found
        """
        long_run_days = []

        for activity in activities:
            distance_km = activity.get("distance_km") or 0
            duration_min = activity.get("duration_min") or 0
            activity_date_str = activity.get("date")

            # Check if this qualifies as a long run
            is_long = (
                distance_km >= self.LONG_RUN_MIN_DISTANCE_KM or
                duration_min >= self.LONG_RUN_MIN_DURATION_MIN
            )

            if is_long and activity_date_str:
                try:
                    if isinstance(activity_date_str, str):
                        activity_date = datetime.strptime(activity_date_str, "%Y-%m-%d").date()
                    else:
                        activity_date = activity_date_str
                    long_run_days.append(activity_date.weekday())
                except (ValueError, AttributeError):
                    continue

        if not long_run_days:
            return None

        # Return the mode (most common day)
        counter = Counter(long_run_days)
        most_common = counter.most_common(1)
        return most_common[0][0] if most_common else None

    def _detect_rest_days(
        self,
        activities: List[Dict],
        start_date: date,
        end_date: date,
    ) -> List[int]:
        """
        Detect typical rest days (days with consistently zero activity).

        A day is considered a "rest day" if it has zero activities
        in more than 80% of the weeks analyzed.

        Args:
            activities: List of activity dictionaries
            start_date: Start of analysis window
            end_date: End of analysis window

        Returns:
            List of day indices (0=Monday, 6=Sunday) that are rest days
        """
        # Count activities per day of week per week
        # Structure: {week_start: {day_of_week: count}}
        weeks_activity: Dict[str, Dict[int, int]] = {}

        for activity in activities:
            activity_date_str = activity.get("date")
            if not activity_date_str:
                continue

            try:
                if isinstance(activity_date_str, str):
                    activity_date = datetime.strptime(activity_date_str, "%Y-%m-%d").date()
                else:
                    activity_date = activity_date_str

                # Get the week start (Monday)
                week_start = activity_date - timedelta(days=activity_date.weekday())
                week_key = week_start.isoformat()

                day_of_week = activity_date.weekday()

                if week_key not in weeks_activity:
                    weeks_activity[week_key] = {d: 0 for d in range(7)}

                weeks_activity[week_key][day_of_week] += 1
            except (ValueError, AttributeError):
                continue

        if not weeks_activity:
            return list(range(7))  # All days are rest days if no activities

        # Calculate rest day frequency
        total_weeks = len(weeks_activity)
        rest_day_counts = {d: 0 for d in range(7)}

        for week_data in weeks_activity.values():
            for day, count in week_data.items():
                if count == 0:
                    rest_day_counts[day] += 1

        # Identify days that are rest days in >80% of weeks
        threshold = self.REST_DAY_THRESHOLD_PCT / 100 * total_weeks
        rest_days = [
            day for day, count in rest_day_counts.items()
            if count >= threshold
        ]

        return sorted(rest_days)

    def _detect_max_session_duration(self, activities: List[Dict]) -> int:
        """
        Calculate the 90th percentile of session durations.

        This represents the "maximum typical" session length,
        useful for planning workout durations.

        Args:
            activities: List of activity dictionaries

        Returns:
            90th percentile duration in minutes (integer)
        """
        durations = []

        for activity in activities:
            duration = activity.get("duration_min")
            if duration and duration > 0:
                durations.append(float(duration))

        if not durations:
            return 60  # Default to 60 minutes

        # Calculate 90th percentile
        durations.sort()
        percentile_idx = int(len(durations) * 0.9)
        percentile_idx = min(percentile_idx, len(durations) - 1)

        return int(durations[percentile_idx])

    def _detect_strength_training(self, activities: List[Dict]) -> bool:
        """
        Detect whether the athlete does strength training.

        Looks for activities with sport_type containing strength-related keywords.

        Args:
            activities: List of activity dictionaries

        Returns:
            True if any strength training activities found
        """
        for activity in activities:
            sport_type = (activity.get("sport_type") or "").lower()
            activity_type = (activity.get("activity_type") or "").lower()

            for keyword in self.STRENGTH_SPORT_TYPES:
                if keyword in sport_type or keyword in activity_type:
                    return True

        return False

    def _detect_cross_training(self, activities: List[Dict]) -> bool:
        """
        Detect whether the athlete cross-trains.

        Cross-training includes cycling, swimming, and other non-running sports.

        Args:
            activities: List of activity dictionaries

        Returns:
            True if any cross-training activities found
        """
        for activity in activities:
            sport_type = (activity.get("sport_type") or "").lower()
            activity_type = (activity.get("activity_type") or "").lower()

            for keyword in self.CROSS_TRAINING_SPORT_TYPES:
                if keyword in sport_type or keyword in activity_type:
                    return True

        return False

    def _detect_preferred_time(self, activities: List[Dict]) -> str:
        """
        Detect preferred time of day for workouts.

        Groups workout start times into buckets:
        - morning: 5:00 AM - 12:00 PM
        - afternoon: 12:00 PM - 5:00 PM
        - evening: 5:00 PM - 10:00 PM

        Returns the mode (most common bucket).

        Args:
            activities: List of activity dictionaries

        Returns:
            "morning", "afternoon", or "evening"
        """
        time_counts = {"morning": 0, "afternoon": 0, "evening": 0}

        for activity in activities:
            start_time = activity.get("start_time")
            if not start_time:
                continue

            try:
                # Parse the start time to extract hour
                if isinstance(start_time, str):
                    # Handle formats like "2024-01-15T07:30:00" or "07:30:00"
                    if "T" in start_time:
                        time_part = start_time.split("T")[1]
                    else:
                        time_part = start_time

                    hour = int(time_part.split(":")[0])
                else:
                    hour = start_time.hour if hasattr(start_time, "hour") else 12

                # Categorize the hour
                for bucket, (start_hour, end_hour) in self.TIME_BUCKETS.items():
                    if start_hour <= hour < end_hour:
                        time_counts[bucket] += 1
                        break
            except (ValueError, AttributeError, IndexError):
                continue

        # Return the most common time bucket
        if sum(time_counts.values()) == 0:
            return "morning"  # Default

        return max(time_counts, key=time_counts.get)

    def _detect_avg_weekly_distance(
        self,
        activities: List[Dict],
        start_date: date,
        end_date: date,
    ) -> float:
        """
        Calculate average weekly running distance.

        Only includes running activities (sport_type containing "run").

        Args:
            activities: List of activity dictionaries
            start_date: Start of analysis window
            end_date: End of analysis window

        Returns:
            Average weekly distance in km
        """
        total_distance = 0.0

        for activity in activities:
            sport_type = (activity.get("sport_type") or "").lower()
            activity_type = (activity.get("activity_type") or "").lower()

            # Only count running activities
            if "run" in sport_type or "run" in activity_type:
                distance = activity.get("distance_km") or 0
                total_distance += float(distance)

        # Calculate number of weeks
        total_days = (end_date - start_date).days + 1
        weeks = max(1, total_days / 7)

        return total_distance / weeks

    def _detect_avg_weekly_load(
        self,
        activities: List[Dict],
        start_date: date,
        end_date: date,
    ) -> float:
        """
        Calculate average weekly training load (HRSS/TRIMP).

        Uses HRSS if available, falls back to TRIMP.

        Args:
            activities: List of activity dictionaries
            start_date: Start of analysis window
            end_date: End of analysis window

        Returns:
            Average weekly training load
        """
        total_load = 0.0

        for activity in activities:
            hrss = activity.get("hrss") or 0
            trimp = activity.get("trimp") or 0

            # Prefer HRSS, fall back to TRIMP
            load = float(hrss) if hrss > 0 else float(trimp)
            total_load += load

        # Calculate number of weeks
        total_days = (end_date - start_date).days + 1
        weeks = max(1, total_days / 7)

        return total_load / weeks

    # === Individual Pattern Detection Methods (Public API) ===

    def get_training_frequency(self, weeks: int = 8) -> float:
        """
        Get the average training frequency (days per week).

        Args:
            weeks: Number of weeks to analyze (default: 8)

        Returns:
            Average training days per week
        """
        end_date = date.today()
        start_date = end_date - timedelta(weeks=weeks)
        activities = self._fetch_activities(start_date, end_date)
        return self._detect_avg_days_per_week(activities, start_date, end_date)

    def get_long_run_pattern(self) -> Optional[Tuple[int, str]]:
        """
        Get the typical long run day.

        Returns:
            Tuple of (day_index, day_name) or None if no pattern detected
        """
        end_date = date.today()
        start_date = end_date - timedelta(weeks=self.WEEKS_TO_ANALYZE)
        activities = self._fetch_activities(start_date, end_date)
        day_idx = self._detect_long_run_day(activities)

        if day_idx is None:
            return None

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday",
                     "Friday", "Saturday", "Sunday"]
        return (day_idx, day_names[day_idx])

    def get_cross_training_types(self) -> List[str]:
        """
        Get the types of cross-training the athlete does.

        Returns:
            List of unique cross-training sport types
        """
        end_date = date.today()
        start_date = end_date - timedelta(weeks=self.WEEKS_TO_ANALYZE)
        activities = self._fetch_activities(start_date, end_date)

        cross_training_types = set()

        for activity in activities:
            sport_type = (activity.get("sport_type") or "").lower()
            activity_type = (activity.get("activity_type") or "").lower()

            for keyword in self.CROSS_TRAINING_SPORT_TYPES:
                if keyword in sport_type:
                    cross_training_types.add(sport_type)
                elif keyword in activity_type:
                    cross_training_types.add(activity_type)

        return sorted(list(cross_training_types))


# Singleton instance
_training_pattern_service: Optional[TrainingPatternService] = None


def get_training_pattern_service(
    db_path: Optional[str] = None,
) -> TrainingPatternService:
    """
    Get the training pattern service singleton.

    This function provides a global singleton instance of TrainingPatternService.
    The singleton is lazily initialized on first call.

    Args:
        db_path: Optional database path. Only used on first initialization.
                 Ignored on subsequent calls.

    Returns:
        TrainingPatternService singleton instance

    Example:
        # First call initializes with default path
        service = get_training_pattern_service()

        # Get patterns
        patterns = service.detect_all()
        # Access: patterns.avg_days_per_week
    """
    global _training_pattern_service

    if _training_pattern_service is None:
        _training_pattern_service = TrainingPatternService(db_path=db_path)

    return _training_pattern_service


def reset_training_pattern_service() -> None:
    """
    Reset the singleton instance.

    Useful for testing or when the database path needs to change.
    """
    global _training_pattern_service
    _training_pattern_service = None
