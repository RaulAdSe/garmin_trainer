"""Mileage Cap API routes for the 10% rule implementation.

Provides endpoints for tracking weekly mileage limits to help
prevent overuse injuries, especially important for beginners.

All routes require authentication since they expose user-specific
training data and personalized injury prevention recommendations.
"""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from ..deps import get_coach_service, get_current_user, CurrentUser
from ...services.mileage_cap_service import (
    MileageCapService,
    get_mileage_cap_service,
    MileageCapResponse,
    PlannedRunCheckResponse,
    PlannedRunCheckRequest,
)


router = APIRouter()


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


# =============================================================================
# Dependencies
# =============================================================================


def get_mileage_cap_service_dep() -> MileageCapService:
    """Get mileage cap service instance."""
    return get_mileage_cap_service()


# =============================================================================
# Response Models
# =============================================================================


class WeeklyMileageResponse(BaseModel):
    """Response model for weekly mileage data."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    week_start: str = Field(..., alias="weekStart")
    week_end: str = Field(..., alias="weekEnd")
    total_km: float = Field(..., alias="totalKm")
    run_count: int = Field(..., alias="runCount")
    avg_run_km: float = Field(..., alias="avgRunKm")
    longest_run_km: float = Field(..., alias="longestRunKm")


class WeeklyComparisonResponse(BaseModel):
    """Response model for week-over-week comparison."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    current_week: WeeklyMileageResponse = Field(..., alias="currentWeek")
    previous_week: WeeklyMileageResponse = Field(..., alias="previousWeek")
    change_pct: float = Field(..., alias="changePct")
    change_km: float = Field(..., alias="changeKm")


class TenPercentRuleInfo(BaseModel):
    """Information about the 10% rule."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    title: str
    description: str
    benefits: list[str]
    tips: list[str]


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=MileageCapResponse)
async def get_mileage_cap(
    target_date: Optional[str] = Query(
        None,
        description="Target date (YYYY-MM-DD). Defaults to today."
    ),
    current_user: CurrentUser = Depends(get_current_user),
    coach_service=Depends(get_coach_service),
    mileage_service: MileageCapService = Depends(get_mileage_cap_service_dep),
):
    """
    Get the current weekly mileage cap status based on the 10% rule.

    The 10% rule recommends not increasing weekly running mileage by more
    than 10% from one week to the next. This helps prevent overuse injuries,
    especially important for beginners.

    Returns:
        - Current week's mileage
        - Previous week's mileage (used as baseline)
        - Weekly limit based on 10% rule
        - Remaining safe kilometers
        - Status (safe, warning, near_limit, exceeded)
        - Personalized recommendation

    Requires authentication.
    """
    try:
        # Parse target date
        if target_date:
            try:
                parsed_date = date.fromisoformat(target_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use YYYY-MM-DD."
                )
        else:
            parsed_date = date.today()

        # Calculate week boundaries for current and previous week
        current_week_start = parsed_date - timedelta(days=parsed_date.weekday())
        previous_week_start = current_week_start - timedelta(days=7)

        # Need 14 days of activities
        activities = coach_service.get_recent_activities(days=14)

        # Get mileage cap
        cap_result = mileage_service.get_mileage_cap(activities, parsed_date)

        return MileageCapResponse(
            current_week_km=round(cap_result.current_week_km, 1),
            previous_week_km=round(cap_result.previous_week_km, 1),
            weekly_limit_km=round(cap_result.weekly_limit_km, 1),
            remaining_km=round(cap_result.remaining_km, 1),
            is_exceeded=cap_result.is_exceeded,
            percentage_used=round(cap_result.percentage_used, 1),
            status=cap_result.status.value,
            recommendation=cap_result.recommendation,
            base_km=round(cap_result.base_km, 1),
            allowed_increase_km=round(cap_result.allowed_increase_km, 1),
            current_week_start=current_week_start.isoformat(),
            previous_week_start=previous_week_start.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to get mileage cap: {e}")
        import traceback
        logging.getLogger(__name__).error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail="Failed to calculate mileage cap. Please try again later.",
        )


@router.post("/check", response_model=PlannedRunCheckResponse)
async def check_planned_run(
    request: PlannedRunCheckRequest,
    target_date: Optional[str] = Query(
        None,
        description="Date for the planned run (YYYY-MM-DD). Defaults to today."
    ),
    current_user: CurrentUser = Depends(get_current_user),
    coach_service=Depends(get_coach_service),
    mileage_service: MileageCapService = Depends(get_mileage_cap_service_dep),
):
    """
    Check if a planned run would exceed the weekly mileage cap.

    Use this endpoint to verify if a planned run distance is safe
    before heading out. If the run would exceed your cap, you'll
    get a suggestion for a safer distance.

    Args:
        planned_km: Distance of the planned run in kilometers

    Returns:
        - Whether the run would exceed the cap
        - Projected total after the run
        - Excess kilometers if over limit
        - Safe distance suggestion

    Requires authentication.
    """
    try:
        # Parse target date
        if target_date:
            try:
                parsed_date = date.fromisoformat(target_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use YYYY-MM-DD."
                )
        else:
            parsed_date = date.today()

        # Get activities
        activities = coach_service.get_recent_activities(days=14)

        # Check planned run
        check_result = mileage_service.check_planned_run(
            planned_km=request.planned_km,
            activities=activities,
            target_date=parsed_date,
        )

        return PlannedRunCheckResponse(
            planned_km=round(check_result.planned_km, 1),
            current_week_km=round(check_result.current_week_km, 1),
            projected_total_km=round(check_result.projected_total_km, 1),
            weekly_limit_km=round(check_result.weekly_limit_km, 1),
            would_exceed=check_result.would_exceed,
            excess_km=round(check_result.excess_km, 1),
            safe_distance_km=round(check_result.safe_distance_km, 1),
            suggestion=check_result.suggestion,
        )

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to check planned run: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to check planned run. Please try again later.",
        )


@router.get("/comparison", response_model=WeeklyComparisonResponse)
async def get_weekly_comparison(
    target_date: Optional[str] = Query(
        None,
        description="Target date (YYYY-MM-DD). Defaults to today."
    ),
    current_user: CurrentUser = Depends(get_current_user),
    coach_service=Depends(get_coach_service),
    mileage_service: MileageCapService = Depends(get_mileage_cap_service_dep),
):
    """
    Get week-over-week mileage comparison.

    Shows how the current week compares to the previous week,
    including the percentage change and detailed breakdown.

    Requires authentication.
    """
    try:
        # Parse target date
        if target_date:
            try:
                parsed_date = date.fromisoformat(target_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use YYYY-MM-DD."
                )
        else:
            parsed_date = date.today()

        # Get activities
        activities = coach_service.get_recent_activities(days=14)

        # Get comparison
        comparison = mileage_service.get_weekly_comparison(activities, parsed_date)

        return WeeklyComparisonResponse(
            current_week=WeeklyMileageResponse(**comparison["currentWeek"]),
            previous_week=WeeklyMileageResponse(**comparison["previousWeek"]),
            change_pct=comparison["changePct"],
            change_km=comparison["changeKm"],
        )

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to get weekly comparison: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get weekly comparison. Please try again later.",
        )


@router.get("/info", response_model=TenPercentRuleInfo)
async def get_ten_percent_rule_info():
    """
    Get information about the 10% rule.

    This endpoint provides educational content about the 10% rule
    for injury prevention. No authentication required.
    """
    return TenPercentRuleInfo(
        title="The 10% Rule",
        description=(
            "The 10% rule is a widely-accepted guideline in running that suggests "
            "your weekly mileage should not increase by more than 10% from week to week. "
            "This gradual progression helps your body adapt to increasing training loads "
            "and reduces the risk of overuse injuries like shin splints, stress fractures, "
            "and tendinitis."
        ),
        benefits=[
            "Reduces risk of overuse injuries",
            "Allows muscles, tendons, and bones to adapt gradually",
            "Helps prevent burnout and overtraining",
            "Builds a sustainable training habit",
            "Especially important for beginners and returning runners",
        ],
        tips=[
            "Track your weekly mileage consistently",
            "Include rest days in your training schedule",
            "Listen to your body - it's okay to increase less than 10%",
            "Consider cross-training (swimming, cycling) to stay active without adding mileage",
            "If you miss a week, don't try to make up the lost mileage",
            "Quality over quantity - better to run fewer miles well than more miles injured",
        ],
    )
