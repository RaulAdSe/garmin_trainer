"""
Deviation detection service for comparing planned vs actual workouts.

This service:
- Compares completed workouts against planned sessions
- Calculates deviation metrics (load, duration, intensity)
- Classifies deviations as: as_planned, easier, harder, skipped, extra
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..models.deviation import (
    DeviationType,
    DeviationMetrics,
    PlanDeviation,
)
from ..models.plans import (
    TrainingPlan,
    TrainingWeek,
    PlannedSession,
    WorkoutType,
)


logger = logging.getLogger(__name__)


# Tolerance thresholds for deviation classification
LOAD_TOLERANCE_PCT = 15.0       # +/- 15% load is considered "as planned"
DURATION_TOLERANCE_PCT = 15.0   # +/- 15% duration is considered "as planned"
HARDER_THRESHOLD_PCT = 20.0     # > 20% more load = harder
EASIER_THRESHOLD_PCT = -20.0    # < -20% load = easier


@dataclass
class WorkoutData:
    """Normalized workout data from various sources."""
    workout_id: str
    date: date
    activity_type: str
    duration_min: float
    load: float  # HRSS or TRIMP
    distance_km: Optional[float] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    intensity_zone: Optional[str] = None

    @classmethod
    def from_activity_dict(cls, activity: Dict[str, Any]) -> "WorkoutData":
        """Create from activity dictionary."""
        # Parse date - handle both string and date objects
        activity_date = activity.get("date")
        if isinstance(activity_date, str):
            activity_date = datetime.strptime(activity_date, "%Y-%m-%d").date()
        elif isinstance(activity_date, datetime):
            activity_date = activity_date.date()

        # Calculate load from HRSS or TRIMP
        load = activity.get("hrss") or activity.get("trimp") or 0.0

        return cls(
            workout_id=activity.get("activity_id") or activity.get("id", ""),
            date=activity_date,
            activity_type=activity.get("activity_type", "running"),
            duration_min=activity.get("duration_min", 0.0),
            load=float(load),
            distance_km=activity.get("distance_km"),
            avg_hr=activity.get("avg_hr"),
            max_hr=activity.get("max_hr"),
        )


class DeviationDetectionService:
    """
    Service for detecting deviations between planned and actual workouts.

    This service compares completed workouts against planned sessions
    to identify when athletes deviate from their training plan.
    """

    def __init__(
        self,
        load_tolerance_pct: float = LOAD_TOLERANCE_PCT,
        duration_tolerance_pct: float = DURATION_TOLERANCE_PCT,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialize the deviation detection service.

        Args:
            load_tolerance_pct: Percentage tolerance for load comparison
            duration_tolerance_pct: Percentage tolerance for duration comparison
            logger: Optional logger instance
        """
        self.load_tolerance_pct = load_tolerance_pct
        self.duration_tolerance_pct = duration_tolerance_pct
        self._logger = logger or logging.getLogger(__name__)

    def detect_deviation(
        self,
        plan: TrainingPlan,
        workout: WorkoutData,
    ) -> Optional[PlanDeviation]:
        """
        Detect deviation between a completed workout and planned session.

        Args:
            plan: The training plan
            workout: The completed workout data

        Returns:
            PlanDeviation if the workout corresponds to a planned session,
            None if no matching session found
        """
        # Find the planned session for this date
        planned_session, week_number, day_of_week = self._find_planned_session(
            plan, workout.date
        )

        if planned_session is None:
            # This is an extra workout not in the plan
            return PlanDeviation(
                plan_id=plan.id,
                week_number=week_number or 0,
                day_of_week=workout.date.weekday(),
                planned_date=workout.date,
                deviation_type=DeviationType.EXTRA,
                planned_workout_type=None,
                actual_workout_id=workout.workout_id,
                actual_workout_type=workout.activity_type,
                severity="minor",
            )

        # Calculate deviation metrics
        metrics = DeviationMetrics(
            planned_duration_min=planned_session.target_duration_min,
            actual_duration_min=workout.duration_min,
            planned_load=planned_session.target_load,
            actual_load=workout.load,
            planned_intensity=planned_session.target_hr_zone,
            actual_avg_hr=workout.avg_hr,
            actual_max_hr=workout.max_hr,
        )

        # Classify the deviation
        deviation_type, severity = self._classify_deviation(metrics)

        return PlanDeviation(
            plan_id=plan.id,
            week_number=week_number,
            day_of_week=day_of_week,
            planned_date=workout.date,
            deviation_type=deviation_type,
            metrics=metrics,
            planned_workout_type=planned_session.workout_type.value,
            actual_workout_id=workout.workout_id,
            actual_workout_type=workout.activity_type,
            severity=severity,
        )

    def detect_skipped_sessions(
        self,
        plan: TrainingPlan,
        workouts: List[WorkoutData],
        check_date: date,
    ) -> List[PlanDeviation]:
        """
        Detect planned sessions that were skipped.

        Args:
            plan: The training plan
            workouts: List of completed workouts
            check_date: Date up to which to check for skipped sessions

        Returns:
            List of PlanDeviation for skipped sessions
        """
        skipped = []
        workout_dates = {w.date for w in workouts}

        # Find the current week
        current_week = plan.get_current_week(check_date)
        if not current_week:
            return skipped

        # Calculate the start date of the plan
        race_date = plan.goal.race_date
        plan_start_date = race_date - timedelta(weeks=plan.total_weeks)

        # Check all weeks up to and including current week
        for week in plan.weeks:
            if week.week_number > current_week.week_number:
                continue

            week_start = plan_start_date + timedelta(weeks=week.week_number - 1)

            for session in week.sessions:
                # Skip rest days
                if session.workout_type == WorkoutType.REST:
                    continue

                session_date = week_start + timedelta(days=session.day_of_week)

                # Only check past dates up to check_date
                if session_date > check_date:
                    continue

                # Check if workout was completed on this date
                if session_date not in workout_dates:
                    skipped.append(PlanDeviation(
                        plan_id=plan.id,
                        week_number=week.week_number,
                        day_of_week=session.day_of_week,
                        planned_date=session_date,
                        deviation_type=DeviationType.SKIPPED,
                        metrics=DeviationMetrics(
                            planned_duration_min=session.target_duration_min,
                            actual_duration_min=0,
                            planned_load=session.target_load,
                            actual_load=0,
                            planned_intensity=session.target_hr_zone,
                        ),
                        planned_workout_type=session.workout_type.value,
                        severity="significant",
                    ))

        return skipped

    def detect_all_deviations(
        self,
        plan: TrainingPlan,
        workouts: List[WorkoutData],
        days_back: int = 7,
    ) -> List[PlanDeviation]:
        """
        Detect all deviations in recent workouts.

        Args:
            plan: The training plan
            workouts: List of completed workouts
            days_back: Number of days to look back

        Returns:
            List of all detected deviations
        """
        deviations = []
        check_date = date.today()
        cutoff_date = check_date - timedelta(days=days_back)

        # Filter workouts to the specified date range
        recent_workouts = [
            w for w in workouts
            if cutoff_date <= w.date <= check_date
        ]

        # Detect deviations for each workout
        for workout in recent_workouts:
            deviation = self.detect_deviation(plan, workout)
            if deviation:
                deviations.append(deviation)

        # Detect skipped sessions
        skipped = self.detect_skipped_sessions(plan, recent_workouts, check_date)
        deviations.extend(skipped)

        # Sort by date
        deviations.sort(key=lambda d: d.planned_date, reverse=True)

        return deviations

    def get_deviation_summary(
        self,
        deviations: List[PlanDeviation],
    ) -> Dict[str, Any]:
        """
        Generate a summary of detected deviations.

        Args:
            deviations: List of detected deviations

        Returns:
            Summary dictionary with counts and analysis
        """
        if not deviations:
            return {
                "total": 0,
                "by_type": {},
                "significant_count": 0,
                "has_significant": False,
                "summary_text": "No deviations detected in the checked period.",
            }

        by_type = {}
        significant_count = 0

        for dev in deviations:
            dev_type = dev.deviation_type.value
            by_type[dev_type] = by_type.get(dev_type, 0) + 1
            if dev.is_significant:
                significant_count += 1

        # Generate summary text
        parts = []
        if by_type.get("skipped", 0) > 0:
            parts.append(f"{by_type['skipped']} skipped session(s)")
        if by_type.get("harder", 0) > 0:
            parts.append(f"{by_type['harder']} harder than planned")
        if by_type.get("easier", 0) > 0:
            parts.append(f"{by_type['easier']} easier than planned")
        if by_type.get("extra", 0) > 0:
            parts.append(f"{by_type['extra']} extra workout(s)")

        summary_text = "; ".join(parts) if parts else "All workouts as planned."

        return {
            "total": len(deviations),
            "by_type": by_type,
            "significant_count": significant_count,
            "has_significant": significant_count > 0,
            "summary_text": summary_text,
        }

    def _find_planned_session(
        self,
        plan: TrainingPlan,
        workout_date: date,
    ) -> Tuple[Optional[PlannedSession], Optional[int], Optional[int]]:
        """
        Find the planned session for a given date.

        Args:
            plan: The training plan
            workout_date: The date to find session for

        Returns:
            Tuple of (PlannedSession, week_number, day_of_week) or (None, None, None)
        """
        # Calculate which week this date falls in
        race_date = plan.goal.race_date
        plan_start_date = race_date - timedelta(weeks=plan.total_weeks)

        days_since_start = (workout_date - plan_start_date).days

        if days_since_start < 0 or days_since_start >= plan.total_weeks * 7:
            return None, None, None

        week_number = (days_since_start // 7) + 1
        day_of_week = workout_date.weekday()

        # Find the week
        week = plan.get_week(week_number)
        if not week:
            return None, week_number, day_of_week

        # Find the session for this day
        for session in week.sessions:
            if session.day_of_week == day_of_week:
                # Skip rest days
                if session.workout_type == WorkoutType.REST:
                    return None, week_number, day_of_week
                return session, week_number, day_of_week

        return None, week_number, day_of_week

    def _classify_deviation(
        self,
        metrics: DeviationMetrics,
    ) -> Tuple[DeviationType, str]:
        """
        Classify the deviation type based on metrics.

        Args:
            metrics: The deviation metrics

        Returns:
            Tuple of (DeviationType, severity)
        """
        load_dev = metrics.load_deviation_pct
        duration_dev = metrics.duration_deviation_pct

        # Combined deviation metric (weighted towards load)
        combined_dev = load_dev * 0.7 + duration_dev * 0.3

        # Classify based on combined deviation
        if abs(combined_dev) <= self.load_tolerance_pct:
            return DeviationType.AS_PLANNED, "none"

        if combined_dev > HARDER_THRESHOLD_PCT:
            severity = "significant" if combined_dev > 50 else "moderate"
            return DeviationType.HARDER, severity

        if combined_dev < EASIER_THRESHOLD_PCT:
            severity = "significant" if combined_dev < -50 else "moderate"
            return DeviationType.EASIER, severity

        # Borderline cases
        if combined_dev > 0:
            return DeviationType.HARDER, "minor"
        else:
            return DeviationType.EASIER, "minor"


# ============================================================================
# Factory function for dependency injection
# ============================================================================

_deviation_service: Optional[DeviationDetectionService] = None


def get_deviation_service() -> DeviationDetectionService:
    """Get or create the deviation detection service singleton."""
    global _deviation_service
    if _deviation_service is None:
        _deviation_service = DeviationDetectionService()
    return _deviation_service


def reset_deviation_service() -> None:
    """Reset the deviation service singleton (for testing)."""
    global _deviation_service
    _deviation_service = None
