"""Gamification API routes for achievements and progress tracking.

All gamification routes require authentication since they expose user-specific
achievement data, XP/level progress, and streak information.
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ..deps import get_training_db, get_current_user, CurrentUser
from ...services.achievement_service import AchievementService
from ...models.gamification import (
    AchievementUnlock,
    AchievementWithStatus,
    CheckAchievementsRequest,
    CheckAchievementsResponse,
    UserProgress,
    to_camel,
)


router = APIRouter()


def get_achievement_service(training_db=Depends(get_training_db)) -> AchievementService:
    """Get achievement service instance using the training database path."""
    return AchievementService(str(training_db.db_path))


# =============================================================================
# Response Models
# =============================================================================


class AchievementsListResponse(BaseModel):
    """Response model for listing all achievements."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    achievements: List[AchievementWithStatus] = Field(
        ..., description="All achievements with unlock status"
    )
    total: int = Field(..., description="Total number of achievements")
    unlocked: int = Field(..., description="Number of unlocked achievements")


class RecentAchievementsResponse(BaseModel):
    """Response model for recent achievements."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    achievements: List[AchievementUnlock] = Field(
        ..., description="Recently unlocked achievements"
    )
    count: int = Field(..., description="Number of recent achievements")


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/achievements", response_model=AchievementsListResponse)
async def get_all_achievements(
    current_user: CurrentUser = Depends(get_current_user),
    achievement_service: AchievementService = Depends(get_achievement_service),
):
    """
    Get all achievements with their unlock status.

    Returns all defined achievements in the system, along with whether
    the user has unlocked each one and when.

    Requires authentication.
    """
    try:
        achievements = achievement_service.get_all_achievements()

        unlocked_count = sum(1 for a in achievements if a.unlocked)

        return AchievementsListResponse(
            achievements=achievements,
            total=len(achievements),
            unlocked=unlocked_count,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to get achievements: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get achievements. Please try again later.",
        )


@router.get("/achievements/recent", response_model=RecentAchievementsResponse)
async def get_recent_achievements(
    days: int = 7,
    current_user: CurrentUser = Depends(get_current_user),
    achievement_service: AchievementService = Depends(get_achievement_service),
):
    """
    Get recently unlocked achievements.

    Args:
        days: Number of days to look back (default 7)

    Returns:
        List of achievements unlocked in the specified time period

    Requires authentication.
    """
    try:
        achievements = achievement_service.get_recent_achievements(days=days)

        return RecentAchievementsResponse(
            achievements=achievements,
            count=len(achievements),
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to get recent achievements: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get recent achievements. Please try again later.",
        )


@router.get("/progress", response_model=UserProgress)
async def get_user_progress(
    current_user: CurrentUser = Depends(get_current_user),
    achievement_service: AchievementService = Depends(get_achievement_service),
):
    """
    Get user's gamification progress.

    Returns:
        User progress including XP, level, streak information,
        and achievement count

    Requires authentication.
    """
    try:
        return achievement_service.get_user_progress()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to get user progress: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get user progress. Please try again later.",
        )


@router.post("/check", response_model=CheckAchievementsResponse)
async def check_achievements(
    request: Optional[CheckAchievementsRequest] = None,
    current_user: CurrentUser = Depends(get_current_user),
    achievement_service: AchievementService = Depends(get_achievement_service),
    training_db=Depends(get_training_db),
):
    """
    Manually trigger achievement check.

    This endpoint checks for any newly earned achievements based on
    the current state of the database. It's useful for:
    - Checking after a workout sync
    - Manual verification of achievement status
    - Testing achievement unlock logic

    Args:
        request: Optional check request with workout_id and activity_date

    Returns:
        CheckAchievementsResponse with any new unlocks

    Requires authentication.
    """
    try:
        # Build context for achievement checking
        context = {}

        if request:
            context["workout_id"] = request.workout_id
            context["activity_date"] = request.activity_date or date.today().isoformat()
        else:
            context["activity_date"] = date.today().isoformat()

        # Get CTL from latest fitness metrics
        latest_fitness = training_db.get_latest_fitness_metrics()
        if latest_fitness:
            context["ctl"] = latest_fitness.ctl or 0

            # Get CTL peak from historical data
            # Query all fitness metrics to find the peak
            from datetime import timedelta
            end_date = date.today()
            start_date = end_date - timedelta(days=365)

            fitness_range = training_db.get_fitness_range(
                start_date.isoformat(),
                end_date.isoformat(),
            )

            if fitness_range:
                ctl_values = [f.ctl for f in fitness_range if f.ctl is not None]
                if ctl_values:
                    # Exclude current value to find historical peak
                    historical_values = ctl_values[1:] if len(ctl_values) > 1 else [0]
                    context["ctl_peak"] = max(historical_values) if historical_values else 0

        # Get VO2 Max from latest Garmin fitness data
        latest_garmin = training_db.get_latest_garmin_fitness_data()
        if latest_garmin:
            context["vo2max_running"] = latest_garmin.vo2max_running or 0
            context["vo2max_cycling"] = latest_garmin.vo2max_cycling or 0

        return achievement_service.check_and_unlock_achievements(context)

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to check achievements: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to check achievements. Please try again later.",
        )
