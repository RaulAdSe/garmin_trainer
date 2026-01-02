"""
Mileage Cap Service for the 10% Rule implementation.

The 10% rule is a widely-accepted guideline in running that suggests
weekly mileage should not increase by more than 10% from week to week.
This helps prevent overuse injuries, especially in beginners.

Based on sports science research supporting gradual training progression:
- Gabbett et al. (2016): Acute:chronic workload ratio and injury risk
- Nielsen et al. (2014): Weekly running volume and injury incidence
- Buist et al. (2008): Training progression and running injuries
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import List, Optional
import logging

from pydantic import BaseModel, ConfigDict, Field


logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================


class CapStatus(str, Enum):
    """Status of the mileage cap."""
    SAFE = "safe"           # Well under the cap (<70%)
    WARNING = "warning"     # Approaching the cap (70-90%)
    NEAR_LIMIT = "near_limit"  # Very close to cap (90-100%)
    EXCEEDED = "exceeded"   # Over the cap (>100%)


# Default values based on sports science recommendations
DEFAULT_CAP_PERCENTAGE = 0.10  # 10% rule
MINIMUM_BASE_KM = 5.0          # Minimum base for calculations (prevents extreme caps)
WARNING_THRESHOLD = 70         # % at which to show warning
NEAR_LIMIT_THRESHOLD = 90      # % at which to show strong warning


# =============================================================================
# Data Models
# =============================================================================


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


@dataclass
class MileageCapResult:
    """
    Result of mileage cap calculation based on the 10% rule.

    The 10% rule recommends not increasing weekly mileage by more than
    10% from one week to the next to prevent injury.
    """
    current_week_km: float
    previous_week_km: float
    weekly_limit_km: float
    remaining_km: float
    is_exceeded: bool
    percentage_used: float
    status: CapStatus
    recommendation: str
    base_km: float  # The base used for calculation (may differ from previous_week)
    allowed_increase_km: float

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "currentWeekKm": round(self.current_week_km, 1),
            "previousWeekKm": round(self.previous_week_km, 1),
            "weeklyLimitKm": round(self.weekly_limit_km, 1),
            "remainingKm": round(self.remaining_km, 1),
            "isExceeded": self.is_exceeded,
            "percentageUsed": round(self.percentage_used, 1),
            "status": self.status.value,
            "recommendation": self.recommendation,
            "baseKm": round(self.base_km, 1),
            "allowedIncreaseKm": round(self.allowed_increase_km, 1),
        }


@dataclass
class PlannedRunCheck:
    """
    Result of checking if a planned run would exceed the weekly cap.
    """
    planned_km: float
    current_week_km: float
    projected_total_km: float
    weekly_limit_km: float
    would_exceed: bool
    excess_km: float
    safe_distance_km: float
    suggestion: str

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "plannedKm": round(self.planned_km, 1),
            "currentWeekKm": round(self.current_week_km, 1),
            "projectedTotalKm": round(self.projected_total_km, 1),
            "weeklyLimitKm": round(self.weekly_limit_km, 1),
            "wouldExceed": self.would_exceed,
            "excessKm": round(self.excess_km, 1),
            "safeDistanceKm": round(self.safe_distance_km, 1),
            "suggestion": self.suggestion,
        }


@dataclass
class WeeklyMileageData:
    """
    Weekly mileage data for tracking and comparison.
    """
    week_start: date
    week_end: date
    total_km: float
    run_count: int
    avg_run_km: float
    longest_run_km: float

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "weekStart": self.week_start.isoformat(),
            "weekEnd": self.week_end.isoformat(),
            "totalKm": round(self.total_km, 1),
            "runCount": self.run_count,
            "avgRunKm": round(self.avg_run_km, 1),
            "longestRunKm": round(self.longest_run_km, 1),
        }


# =============================================================================
# Pydantic Response Models (for API)
# =============================================================================


class MileageCapResponse(BaseModel):
    """API response model for mileage cap status."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    current_week_km: float = Field(..., alias="currentWeekKm")
    previous_week_km: float = Field(..., alias="previousWeekKm")
    weekly_limit_km: float = Field(..., alias="weeklyLimitKm")
    remaining_km: float = Field(..., alias="remainingKm")
    is_exceeded: bool = Field(..., alias="isExceeded")
    percentage_used: float = Field(..., alias="percentageUsed")
    status: str
    recommendation: str
    base_km: float = Field(..., alias="baseKm")
    allowed_increase_km: float = Field(..., alias="allowedIncreaseKm")
    current_week_start: str = Field(..., alias="currentWeekStart")
    previous_week_start: str = Field(..., alias="previousWeekStart")


class PlannedRunCheckResponse(BaseModel):
    """API response model for planned run check."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    planned_km: float = Field(..., alias="plannedKm")
    current_week_km: float = Field(..., alias="currentWeekKm")
    projected_total_km: float = Field(..., alias="projectedTotalKm")
    weekly_limit_km: float = Field(..., alias="weeklyLimitKm")
    would_exceed: bool = Field(..., alias="wouldExceed")
    excess_km: float = Field(..., alias="excessKm")
    safe_distance_km: float = Field(..., alias="safeDistanceKm")
    suggestion: str


class PlannedRunCheckRequest(BaseModel):
    """Request model for checking a planned run."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    planned_km: float = Field(..., alias="plannedKm", gt=0, description="Planned run distance in km")


# =============================================================================
# Core Functions
# =============================================================================


def calculate_mileage_cap(
    previous_week_km: float,
    current_week_km: float,
    cap_percentage: float = DEFAULT_CAP_PERCENTAGE,
    minimum_base_km: float = MINIMUM_BASE_KM,
) -> MileageCapResult:
    """
    Calculate weekly mileage cap based on the 10% rule.

    The 10% rule states that you should not increase your weekly running
    mileage by more than 10% from one week to the next. This gradual
    progression helps prevent overuse injuries.

    Args:
        previous_week_km: Total kilometers run in the previous week
        current_week_km: Total kilometers run so far in the current week
        cap_percentage: Maximum allowed increase (default 10% = 0.10)
        minimum_base_km: Minimum base for calculations (prevents extreme caps)

    Returns:
        MileageCapResult with cap status and recommendations

    Example:
        If you ran 30km last week, your cap this week is:
        30km + (30km * 0.10) = 33km
    """
    # Use minimum base if previous week was very low
    # This prevents unrealistic caps for returning runners
    base_km = max(previous_week_km, minimum_base_km)

    # Calculate allowed increase and weekly limit
    allowed_increase = base_km * cap_percentage
    weekly_limit = base_km + allowed_increase

    # Calculate remaining and percentage used
    remaining_km = max(0, weekly_limit - current_week_km)
    percentage_used = (current_week_km / weekly_limit) * 100 if weekly_limit > 0 else 0

    # Determine status
    if current_week_km > weekly_limit:
        status = CapStatus.EXCEEDED
    elif percentage_used >= NEAR_LIMIT_THRESHOLD:
        status = CapStatus.NEAR_LIMIT
    elif percentage_used >= WARNING_THRESHOLD:
        status = CapStatus.WARNING
    else:
        status = CapStatus.SAFE

    # Generate recommendation based on status
    recommendation = _generate_recommendation(
        status=status,
        remaining_km=remaining_km,
        percentage_used=percentage_used,
        weekly_limit=weekly_limit,
        current_week_km=current_week_km,
    )

    return MileageCapResult(
        current_week_km=current_week_km,
        previous_week_km=previous_week_km,
        weekly_limit_km=weekly_limit,
        remaining_km=remaining_km,
        is_exceeded=current_week_km > weekly_limit,
        percentage_used=percentage_used,
        status=status,
        recommendation=recommendation,
        base_km=base_km,
        allowed_increase_km=allowed_increase,
    )


def _generate_recommendation(
    status: CapStatus,
    remaining_km: float,
    percentage_used: float,
    weekly_limit: float,
    current_week_km: float,
) -> str:
    """Generate a recommendation based on the current cap status."""

    if status == CapStatus.EXCEEDED:
        excess = current_week_km - weekly_limit
        return (
            f"You've exceeded your weekly cap by {excess:.1f}km. "
            "Consider rest or cross-training (swimming, cycling) for the remaining days "
            "to allow recovery and reduce injury risk."
        )

    elif status == CapStatus.NEAR_LIMIT:
        return (
            f"You're at {percentage_used:.0f}% of your weekly cap with only {remaining_km:.1f}km remaining. "
            "Consider shorter, easy runs or take a rest day to stay within safe limits."
        )

    elif status == CapStatus.WARNING:
        return (
            f"You're at {percentage_used:.0f}% of your weekly cap. "
            f"You can safely run up to {remaining_km:.1f}km more this week. "
            "Keep your remaining runs at easy effort."
        )

    else:  # SAFE
        return (
            f"You're well within your weekly cap at {percentage_used:.0f}%. "
            f"You can safely run up to {remaining_km:.1f}km more this week."
        )


def check_planned_run(
    planned_km: float,
    current_week_km: float,
    weekly_limit_km: float,
) -> PlannedRunCheck:
    """
    Check if a planned run would exceed the weekly mileage cap.

    Args:
        planned_km: Distance of the planned run in kilometers
        current_week_km: Total kilometers already run this week
        weekly_limit_km: Maximum allowed kilometers for this week

    Returns:
        PlannedRunCheck with analysis and suggestions
    """
    projected_total = current_week_km + planned_km
    would_exceed = projected_total > weekly_limit_km
    excess_km = max(0, projected_total - weekly_limit_km)
    safe_distance = max(0, weekly_limit_km - current_week_km)

    # Generate suggestion
    if would_exceed:
        if safe_distance > 0:
            suggestion = (
                f"This run would exceed your cap by {excess_km:.1f}km. "
                f"Consider running {safe_distance:.1f}km instead to stay within safe limits."
            )
        else:
            suggestion = (
                "You've already reached your weekly cap. "
                "Consider rest or cross-training (swimming, cycling, yoga) today."
            )
    else:
        remaining_after = weekly_limit_km - projected_total
        if remaining_after < 2:
            suggestion = (
                f"Safe to run! This will bring you very close to your weekly cap "
                f"({remaining_after:.1f}km remaining after)."
            )
        else:
            suggestion = (
                f"Safe to run! You'll have {remaining_after:.1f}km remaining "
                "in your weekly cap after this run."
            )

    return PlannedRunCheck(
        planned_km=planned_km,
        current_week_km=current_week_km,
        projected_total_km=projected_total,
        weekly_limit_km=weekly_limit_km,
        would_exceed=would_exceed,
        excess_km=excess_km,
        safe_distance_km=safe_distance,
        suggestion=suggestion,
    )


def extract_weekly_mileage(
    activities: List[dict],
    week_start: date,
) -> WeeklyMileageData:
    """
    Extract weekly mileage data from activities.

    Args:
        activities: List of activity dictionaries
        week_start: Start date of the week (Monday)

    Returns:
        WeeklyMileageData with aggregated weekly stats
    """
    week_end = week_start + timedelta(days=6)

    run_distances: List[float] = []

    for activity in activities:
        # Only count running activities
        activity_type = activity.get("type", "").lower()
        if activity_type not in ("running", "run", "trail_running", "treadmill_running"):
            continue

        # Parse activity date
        activity_date_str = activity.get("date")
        if not activity_date_str:
            continue

        try:
            if isinstance(activity_date_str, str):
                activity_date = date.fromisoformat(activity_date_str.split("T")[0])
            elif isinstance(activity_date_str, datetime):
                activity_date = activity_date_str.date()
            elif isinstance(activity_date_str, date):
                activity_date = activity_date_str
            else:
                continue
        except (ValueError, TypeError):
            continue

        # Check if activity is in the target week
        if week_start <= activity_date <= week_end:
            # Get distance in km
            distance_km = activity.get("distance_km")
            if distance_km is None:
                # Try meters and convert
                distance_m = activity.get("distance")
                if distance_m is not None:
                    distance_km = distance_m / 1000
                else:
                    continue

            if distance_km and distance_km > 0:
                run_distances.append(float(distance_km))

    total_km = sum(run_distances)
    run_count = len(run_distances)
    avg_run_km = total_km / run_count if run_count > 0 else 0
    longest_run_km = max(run_distances) if run_distances else 0

    return WeeklyMileageData(
        week_start=week_start,
        week_end=week_end,
        total_km=total_km,
        run_count=run_count,
        avg_run_km=avg_run_km,
        longest_run_km=longest_run_km,
    )


# =============================================================================
# Mileage Cap Service Class
# =============================================================================


class MileageCapService:
    """
    Service for managing weekly mileage caps based on the 10% rule.

    The 10% rule is a widely-recommended guideline for increasing running
    volume safely. It suggests not increasing weekly mileage by more than
    10% from one week to the next.

    Benefits:
    - Reduces risk of overuse injuries
    - Allows body to adapt gradually
    - Especially important for beginners
    """

    def __init__(
        self,
        cap_percentage: float = DEFAULT_CAP_PERCENTAGE,
        minimum_base_km: float = MINIMUM_BASE_KM,
    ):
        """
        Initialize the mileage cap service.

        Args:
            cap_percentage: Maximum allowed weekly increase (default 10%)
            minimum_base_km: Minimum base for calculations
        """
        self._cap_percentage = cap_percentage
        self._minimum_base_km = minimum_base_km
        self._logger = logging.getLogger(__name__)

    def get_mileage_cap(
        self,
        activities: List[dict],
        target_date: Optional[date] = None,
    ) -> MileageCapResult:
        """
        Calculate the mileage cap for the current/target week.

        Args:
            activities: List of recent activities (at least 14 days)
            target_date: Date to calculate cap for (default: today)

        Returns:
            MileageCapResult with current cap status
        """
        if target_date is None:
            target_date = date.today()

        # Calculate week boundaries (Monday-Sunday)
        # weekday() returns 0 for Monday, 6 for Sunday
        current_week_start = target_date - timedelta(days=target_date.weekday())
        previous_week_start = current_week_start - timedelta(days=7)

        # Extract weekly mileage
        current_week_data = extract_weekly_mileage(activities, current_week_start)
        previous_week_data = extract_weekly_mileage(activities, previous_week_start)

        # Calculate cap
        return calculate_mileage_cap(
            previous_week_km=previous_week_data.total_km,
            current_week_km=current_week_data.total_km,
            cap_percentage=self._cap_percentage,
            minimum_base_km=self._minimum_base_km,
        )

    def check_planned_run(
        self,
        planned_km: float,
        activities: List[dict],
        target_date: Optional[date] = None,
    ) -> PlannedRunCheck:
        """
        Check if a planned run would exceed the weekly cap.

        Args:
            planned_km: Distance of the planned run in km
            activities: List of recent activities
            target_date: Date for the planned run (default: today)

        Returns:
            PlannedRunCheck with analysis
        """
        # First get the current cap status
        cap_result = self.get_mileage_cap(activities, target_date)

        # Check the planned run against the cap
        return check_planned_run(
            planned_km=planned_km,
            current_week_km=cap_result.current_week_km,
            weekly_limit_km=cap_result.weekly_limit_km,
        )

    def get_weekly_comparison(
        self,
        activities: List[dict],
        target_date: Optional[date] = None,
    ) -> dict:
        """
        Get week-over-week mileage comparison.

        Args:
            activities: List of recent activities
            target_date: Reference date (default: today)

        Returns:
            Dict with current and previous week data
        """
        if target_date is None:
            target_date = date.today()

        current_week_start = target_date - timedelta(days=target_date.weekday())
        previous_week_start = current_week_start - timedelta(days=7)

        current_week = extract_weekly_mileage(activities, current_week_start)
        previous_week = extract_weekly_mileage(activities, previous_week_start)

        # Calculate change
        if previous_week.total_km > 0:
            change_pct = ((current_week.total_km - previous_week.total_km) / previous_week.total_km) * 100
        else:
            change_pct = 0 if current_week.total_km == 0 else 100

        return {
            "currentWeek": current_week.to_dict(),
            "previousWeek": previous_week.to_dict(),
            "changePct": round(change_pct, 1),
            "changeKm": round(current_week.total_km - previous_week.total_km, 1),
        }


# =============================================================================
# Singleton Instance
# =============================================================================


_mileage_cap_service: Optional[MileageCapService] = None


def get_mileage_cap_service() -> MileageCapService:
    """
    Get the mileage cap service singleton.

    Returns:
        MileageCapService instance
    """
    global _mileage_cap_service
    if _mileage_cap_service is None:
        _mileage_cap_service = MileageCapService()
    return _mileage_cap_service
