"""Running economy API routes.

Running economy measures how efficiently a runner converts oxygen into forward motion.
These endpoints provide running economy tracking and cardiac drift analysis.

All economy routes require authentication since they expose sensitive performance data.
"""

from datetime import date, datetime
from typing import Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import get_training_db, get_current_user, CurrentUser
from ...models.running_economy import (
    CardiacDriftResponse,
    EconomyCurrentResponse,
    EconomyTrendResponse,
    PaceZonesEconomyResponse,
)
from ...services.running_economy_service import (
    RunningEconomyService,
    get_running_economy_service,
)


logger = logging.getLogger(__name__)
router = APIRouter()


def get_economy_service() -> RunningEconomyService:
    """Get the running economy service instance."""
    return get_running_economy_service()


@router.get("/current", response_model=EconomyCurrentResponse)
async def get_current_economy(
    current_user: CurrentUser = Depends(get_current_user),
    training_db = Depends(get_training_db),
    economy_service: RunningEconomyService = Depends(get_economy_service),
):
    """
    Get the most recent running economy metrics.

    Returns the economy ratio from the latest running workout,
    along with comparison to personal best economy.

    Economy is calculated as: pace_seconds_per_km / avg_hr
    Lower values indicate better economy (less cardiac effort for same pace).

    Example:
        At 5:00/km (300 sec) with 150 bpm: economy = 2.0
        At 5:00/km with 145 bpm: economy = 2.07 (3.4% better)

    Requires authentication (contains performance data).
    """
    try:
        # Get recent activities (last 365 days for best economy comparison)
        activities = training_db.get_activities(days=365)

        if not activities:
            return EconomyCurrentResponse(
                has_data=False,
                message="No running workouts found. Complete a run to see economy metrics.",
            )

        # Convert to dicts if needed
        activity_dicts = []
        for act in activities:
            if hasattr(act, "__dict__"):
                activity_dicts.append(act.__dict__)
            elif isinstance(act, dict):
                activity_dicts.append(act)
            else:
                activity_dicts.append(dict(act))

        return economy_service.get_current_economy(activity_dicts)

    except Exception as e:
        logger.error(f"Failed to get current economy: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get running economy. Please try again later."
        )


@router.get("/trend", response_model=EconomyTrendResponse)
async def get_economy_trend(
    days: int = Query(default=90, ge=7, le=365, description="Number of days to analyze"),
    current_user: CurrentUser = Depends(get_current_user),
    training_db = Depends(get_training_db),
    economy_service: RunningEconomyService = Depends(get_economy_service),
):
    """
    Get running economy trend over time.

    Shows how running economy has changed over the specified period,
    including improvement percentage and trend direction.

    Trend analysis:
    - improving: Economy improved >3% (lower ratio)
    - stable: Economy changed <3%
    - declining: Economy worsened >3% (higher ratio)

    Requires authentication (contains performance data).
    """
    try:
        # Get activities for the requested period
        activities = training_db.get_activities(days=days)

        if not activities:
            return EconomyTrendResponse(
                trend=economy_service.get_economy_trend([], days),
                success=True,
                message="No running workouts found in the specified period.",
            )

        # Convert to dicts
        activity_dicts = []
        for act in activities:
            if hasattr(act, "__dict__"):
                activity_dicts.append(act.__dict__)
            elif isinstance(act, dict):
                activity_dicts.append(act)
            else:
                activity_dicts.append(dict(act))

        trend = economy_service.get_economy_trend(activity_dicts, days)

        return EconomyTrendResponse(
            trend=trend,
            success=True,
        )

    except Exception as e:
        logger.error(f"Failed to get economy trend: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get economy trend. Please try again later."
        )


@router.get("/drift/{workout_id}", response_model=CardiacDriftResponse)
async def get_cardiac_drift(
    workout_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    training_db = Depends(get_training_db),
    economy_service: RunningEconomyService = Depends(get_economy_service),
):
    """
    Get cardiac drift analysis for a specific workout.

    Cardiac drift is the increase in heart rate during the second half
    of a workout at the same pace. It indicates:
    - Aerobic base fitness
    - Hydration status
    - Heat adaptation
    - Fueling adequacy

    Severity levels:
    - none: <2% drift (excellent aerobic control)
    - minimal: 2-5% drift (normal for longer efforts)
    - concerning: 5-8% drift (indicates room for improvement)
    - significant: >8% drift (needs attention)

    Drift >5% typically indicates aerobic base deficiency.

    Requires authentication (contains performance data).
    """
    try:
        # Get the specific workout
        activity = training_db.get_activity_by_id(workout_id)

        if not activity:
            raise HTTPException(
                status_code=404,
                detail=f"Workout {workout_id} not found."
            )

        # Convert to dict
        if hasattr(activity, "__dict__"):
            activity_dict = activity.__dict__
        elif isinstance(activity, dict):
            activity_dict = activity
        else:
            activity_dict = dict(activity)

        # Try to get time series data for more accurate drift calculation
        time_series = None
        try:
            details = training_db.get_activity_details(workout_id)
            if details and hasattr(details, "time_series"):
                time_series = details.time_series
        except Exception:
            # Time series not available, will use splits or return None
            pass

        analysis = economy_service.detect_cardiac_drift(activity_dict, time_series)

        if not analysis:
            return CardiacDriftResponse(
                success=True,
                message="Unable to calculate cardiac drift. Workout may not have sufficient HR data or be a running workout.",
            )

        return CardiacDriftResponse(
            analysis=analysis,
            success=True,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cardiac drift: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze cardiac drift. Please try again later."
        )


@router.get("/zones", response_model=PaceZonesEconomyResponse)
async def get_pace_zones_economy(
    days: int = Query(default=90, ge=7, le=365, description="Number of days to analyze"),
    current_user: CurrentUser = Depends(get_current_user),
    training_db = Depends(get_training_db),
    economy_service: RunningEconomyService = Depends(get_economy_service),
):
    """
    Get economy breakdown by pace zone.

    Shows running economy metrics for different intensity levels:
    - Easy: Recovery and easy runs
    - Long: Long run pace
    - Tempo: Comfortably hard efforts
    - Threshold: Lactate threshold pace
    - Interval: VO2max and speed work

    This helps identify:
    - Which zones have the best economy
    - Where improvement is needed
    - Optimal training intensities

    Requires authentication (contains performance data).
    """
    try:
        # Get activities for the requested period
        activities = training_db.get_activities(days=days)

        if not activities:
            return PaceZonesEconomyResponse(
                zones_economy=economy_service.get_pace_specific_economy([], days),
                success=True,
                message="No running workouts found in the specified period.",
            )

        # Convert to dicts
        activity_dicts = []
        for act in activities:
            if hasattr(act, "__dict__"):
                activity_dicts.append(act.__dict__)
            elif isinstance(act, dict):
                activity_dicts.append(act)
            else:
                activity_dicts.append(dict(act))

        zones_economy = economy_service.get_pace_specific_economy(activity_dicts, days)

        return PaceZonesEconomyResponse(
            zones_economy=zones_economy,
            success=True,
        )

    except Exception as e:
        logger.error(f"Failed to get pace zones economy: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get zone economy. Please try again later."
        )


@router.get("/drift-trend")
async def get_cardiac_drift_trend(
    days: int = Query(default=90, ge=7, le=365, description="Number of days to analyze"),
    current_user: CurrentUser = Depends(get_current_user),
    training_db = Depends(get_training_db),
    economy_service: RunningEconomyService = Depends(get_economy_service),
):
    """
    Get cardiac drift trends over time.

    Tracks how cardiac drift has changed over the specified period,
    indicating changes in aerobic fitness.

    Improving drift trend suggests:
    - Better aerobic base
    - Improved endurance
    - Better heat adaptation

    Requires authentication (contains performance data).
    """
    try:
        # Get activities for the requested period
        activities = training_db.get_activities(days=days)

        if not activities:
            return {
                "success": True,
                "data": {
                    "startDate": (date.today()).isoformat(),
                    "endDate": date.today().isoformat(),
                    "dataPoints": [],
                    "avgDriftPercent": 0,
                    "concerningCount": 0,
                    "improvementTrend": "stable",
                    "aerobicBaseAssessment": "No running workouts found to assess aerobic base.",
                },
            }

        # Convert to dicts
        activity_dicts = []
        for act in activities:
            if hasattr(act, "__dict__"):
                activity_dicts.append(act.__dict__)
            elif isinstance(act, dict):
                activity_dicts.append(act)
            else:
                activity_dicts.append(dict(act))

        drift_trend = economy_service.get_cardiac_drift_trend(activity_dicts, days=days)

        return {
            "success": True,
            "data": drift_trend.model_dump(by_alias=True),
        }

    except Exception as e:
        logger.error(f"Failed to get cardiac drift trend: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get drift trend. Please try again later."
        )
