"""Race pacing API routes.

Endpoints for generating race pacing plans, calculating weather adjustments,
and retrieving available pacing strategies.
"""

import logging
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import get_current_user, CurrentUser
from ...models.race_pacing import (
    PacingPlan,
    PacingStrategy,
    RaceDistance,
    RACE_DISTANCES_KM,
    WeatherAdjustment,
    GeneratePacingPlanRequest,
    WeatherAdjustmentRequest,
    AvailableStrategiesResponse,
)
from ...services.race_pacing_service import get_race_pacing_service


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/pacing-plan", response_model=PacingPlan)
async def generate_pacing_plan(
    request: GeneratePacingPlanRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Generate a race pacing plan based on target time and conditions.

    This endpoint creates a detailed pacing plan with per-km splits,
    accounting for:
    - Course elevation profile (if provided)
    - Weather conditions (if provided)
    - Chosen or recommended pacing strategy

    Args:
        request: Pacing plan generation request with target time,
                distance, and optional conditions

    Returns:
        PacingPlan with all splits, strategy, and tips
    """
    logger.info(
        f"[generate_pacing_plan] User {current_user.id} requesting pacing plan: "
        f"distance={request.race_distance.value}, target_time={request.target_time_sec}s"
    )

    service = get_race_pacing_service()

    try:
        # Determine distance
        if request.race_distance == RaceDistance.CUSTOM:
            distance_km = request.distance_km
            if not distance_km:
                raise HTTPException(
                    status_code=400,
                    detail="distance_km is required for custom race distances"
                )
        else:
            distance_km = RACE_DISTANCES_KM.get(request.race_distance)
            if not distance_km:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown race distance: {request.race_distance}"
                )

        # Generate the pacing plan
        plan = service.generate_pacing_plan(
            target_time_sec=request.target_time_sec,
            distance_km=distance_km,
            race_distance=request.race_distance,
            race_name=request.race_name,
            course_profile=request.course_profile,
            weather_conditions=request.weather_conditions,
            strategy=request.strategy,
            split_unit=request.split_unit,
        )

        logger.info(
            f"[generate_pacing_plan] Generated plan with {len(plan.splits)} splits, "
            f"strategy={plan.strategy.value}"
        )

        return plan

    except ValueError as e:
        logger.warning(f"[generate_pacing_plan] Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[generate_pacing_plan] Error generating plan: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate pacing plan. Please try again."
        )


@router.post("/weather-adjustment", response_model=WeatherAdjustment)
async def calculate_weather_adjustment(
    request: WeatherAdjustmentRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Calculate the impact of weather conditions on race pace.

    This endpoint calculates pace adjustments for:
    - Temperature (above optimal 12C)
    - Humidity (above optimal 60%)
    - Wind (headwind, tailwind, crosswind)
    - Altitude

    Args:
        request: Weather adjustment request with base pace and conditions

    Returns:
        WeatherAdjustment with individual and total adjustments
    """
    logger.info(
        f"[calculate_weather_adjustment] User {current_user.id} calculating weather impact: "
        f"temp={request.weather_conditions.temperature_c}C"
    )

    service = get_race_pacing_service()

    try:
        adjustment = service.calculate_weather_adjustment(
            base_pace_sec_km=request.base_pace_sec_km,
            conditions=request.weather_conditions,
        )

        logger.info(
            f"[calculate_weather_adjustment] Total adjustment: "
            f"{adjustment.total_adjustment_pct:.1f}%"
        )

        return adjustment

    except Exception as e:
        logger.error(f"[calculate_weather_adjustment] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to calculate weather adjustment. Please try again."
        )


@router.get("/strategies", response_model=AvailableStrategiesResponse)
async def get_available_strategies(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get available pacing strategies and race distances.

    Returns descriptions and use cases for each pacing strategy,
    plus the list of supported standard race distances.

    Returns:
        AvailableStrategiesResponse with strategies and distances
    """
    strategies = [
        {
            "id": PacingStrategy.EVEN.value,
            "name": "Even Pacing",
            "description": "Maintain consistent pace throughout the race",
            "best_for": "Most efficient for flat courses and shorter distances",
            "pros": [
                "Predictable and efficient",
                "Easy to execute",
                "Good for beginners"
            ],
            "cons": [
                "Doesn't account for course variations",
                "May feel harder at the end"
            ]
        },
        {
            "id": PacingStrategy.NEGATIVE_SPLIT.value,
            "name": "Negative Split",
            "description": "Start conservatively and increase pace in the second half",
            "best_for": "Experienced runners in longer races (half marathon+)",
            "pros": [
                "Strong finish when others are fading",
                "Reduces risk of hitting the wall",
                "Mentally easier in the second half"
            ],
            "cons": [
                "Requires discipline to hold back early",
                "Hard to execute in competitive races"
            ]
        },
        {
            "id": PacingStrategy.POSITIVE_SPLIT.value,
            "name": "Positive Split",
            "description": "Start faster and slow down in the second half",
            "best_for": "Aggressive racing or courses with difficult finishes",
            "pros": [
                "Build a time buffer early",
                "Good for downhill-start courses"
            ],
            "cons": [
                "Risk of hitting the wall",
                "Often results in slower overall time"
            ]
        },
        {
            "id": PacingStrategy.COURSE_SPECIFIC.value,
            "name": "Course-Specific",
            "description": "Adjust pace based on course elevation and features",
            "best_for": "Hilly courses or courses with significant elevation changes",
            "pros": [
                "Optimizes effort over terrain",
                "Preserves energy on climbs",
                "Takes advantage of downhills"
            ],
            "cons": [
                "Requires knowledge of the course",
                "More complex to execute"
            ]
        },
    ]

    race_distances = [
        {
            "id": RaceDistance.FIVE_K.value,
            "name": "5K",
            "distance_km": RACE_DISTANCES_KM[RaceDistance.FIVE_K],
            "distance_miles": round(RACE_DISTANCES_KM[RaceDistance.FIVE_K] / 1.60934, 2),
        },
        {
            "id": RaceDistance.TEN_K.value,
            "name": "10K",
            "distance_km": RACE_DISTANCES_KM[RaceDistance.TEN_K],
            "distance_miles": round(RACE_DISTANCES_KM[RaceDistance.TEN_K] / 1.60934, 2),
        },
        {
            "id": RaceDistance.HALF_MARATHON.value,
            "name": "Half Marathon",
            "distance_km": RACE_DISTANCES_KM[RaceDistance.HALF_MARATHON],
            "distance_miles": round(RACE_DISTANCES_KM[RaceDistance.HALF_MARATHON] / 1.60934, 2),
        },
        {
            "id": RaceDistance.MARATHON.value,
            "name": "Marathon",
            "distance_km": RACE_DISTANCES_KM[RaceDistance.MARATHON],
            "distance_miles": round(RACE_DISTANCES_KM[RaceDistance.MARATHON] / 1.60934, 2),
        },
        {
            "id": RaceDistance.CUSTOM.value,
            "name": "Custom Distance",
            "distance_km": None,
            "distance_miles": None,
        },
    ]

    return AvailableStrategiesResponse(
        strategies=strategies,
        race_distances=race_distances,
    )


@router.get("/quick-plan")
async def get_quick_plan(
    race_distance: RaceDistance = Query(..., description="Race distance"),
    target_time_hours: float = Query(0, ge=0, description="Target hours"),
    target_time_minutes: float = Query(..., ge=0, lt=60, description="Target minutes"),
    target_time_seconds: float = Query(0, ge=0, lt=60, description="Target seconds"),
    custom_distance_km: float = Query(None, gt=0, description="Custom distance in km"),
    current_user: CurrentUser = Depends(get_current_user),
) -> PacingPlan:
    """
    Quick endpoint to generate a basic pacing plan with minimal input.

    This is a simplified version of the main pacing plan endpoint,
    taking time as separate components for easier use.

    Args:
        race_distance: Race distance category
        target_time_hours: Target hours component
        target_time_minutes: Target minutes component
        target_time_seconds: Target seconds component
        custom_distance_km: Distance in km (required for custom)

    Returns:
        PacingPlan with basic even pacing
    """
    # Calculate total seconds
    target_time_sec = (
        target_time_hours * 3600 +
        target_time_minutes * 60 +
        target_time_seconds
    )

    if target_time_sec <= 0:
        raise HTTPException(
            status_code=400,
            detail="Target time must be greater than zero"
        )

    # Determine distance
    if race_distance == RaceDistance.CUSTOM:
        if not custom_distance_km:
            raise HTTPException(
                status_code=400,
                detail="custom_distance_km is required for custom race distances"
            )
        distance_km = custom_distance_km
    else:
        distance_km = RACE_DISTANCES_KM.get(race_distance)
        if not distance_km:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown race distance: {race_distance}"
            )

    service = get_race_pacing_service()

    plan = service.generate_pacing_plan(
        target_time_sec=target_time_sec,
        distance_km=distance_km,
        race_distance=race_distance,
    )

    return plan
