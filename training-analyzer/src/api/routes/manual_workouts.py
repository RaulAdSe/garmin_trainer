"""
Manual Workout API routes.

Provides endpoints for logging workouts manually without a device,
using Rate of Perceived Exertion (RPE) to estimate training load.
"""

import logging
from typing import List, Optional
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import get_current_user, CurrentUser
from ...services.manual_workout_service import (
    ManualWorkoutService,
    ManualWorkoutCreate,
    ManualWorkoutResponse,
    get_manual_workout_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ManualWorkoutCreateRequest(BaseModel):
    """Request model for creating a manual workout."""
    name: Optional[str] = Field(None, max_length=200, description="Workout name (auto-generated if not provided)")
    activity_type: str = Field(default="running", max_length=50, description="Type of activity")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    duration_min: int = Field(..., ge=1, le=720, description="Duration in minutes (1-720)")
    distance_km: Optional[float] = Field(None, ge=0, le=500, description="Distance in km (optional)")
    rpe: int = Field(..., ge=1, le=10, description="Rate of Perceived Exertion (1-10)")
    avg_hr: Optional[int] = Field(None, ge=30, le=250, description="Average heart rate (optional)")
    max_hr: Optional[int] = Field(None, ge=30, le=250, description="Maximum heart rate (optional)")
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes")


class PaginatedManualWorkoutsResponse(BaseModel):
    """Paginated response for manual workouts."""
    items: List[ManualWorkoutResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class WeeklyLoadSummary(BaseModel):
    """Weekly training load summary."""
    week: str
    total_load: float
    workout_count: int
    total_duration_min: int
    total_distance_km: float
    avg_rpe: float


class LoadEstimateRequest(BaseModel):
    """Request model for estimating training load."""
    duration_min: int = Field(..., ge=1, le=720, description="Duration in minutes")
    rpe: int = Field(..., ge=1, le=10, description="Rate of Perceived Exertion (1-10)")


class LoadEstimateResponse(BaseModel):
    """Response model for training load estimate."""
    duration_min: int
    rpe: int
    estimated_load: float
    load_category: str
    description: str


# =============================================================================
# Dependencies
# =============================================================================

def get_service() -> ManualWorkoutService:
    """Get the manual workout service instance."""
    return get_manual_workout_service()


# =============================================================================
# API Routes
# =============================================================================

@router.post("/", response_model=ManualWorkoutResponse, status_code=201)
async def log_manual_workout(
    request: ManualWorkoutCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: ManualWorkoutService = Depends(get_service),
):
    """
    Log a manual workout using RPE.

    This endpoint allows users to log workouts without device data.
    Training load is estimated using the session-RPE method:
    Load = Duration (minutes) x RPE x 0.8

    The 0.8 factor normalizes session-RPE to approximately match
    heart rate-based TRIMP scores for comparison.

    **RPE Scale (1-10):**
    - 1-2: Very Light (barely moving, normal breathing)
    - 3-4: Light (easy effort, can speak in sentences)
    - 5-6: Moderate (comfortable, can speak in phrases)
    - 7-8: Hard (challenging, can only say a few words)
    - 9-10: Maximum (all-out, can't talk)

    **Activity Types:**
    running, cycling, swimming, walking, hiking, strength, yoga, other
    """
    try:
        workout_data = ManualWorkoutCreate(
            name=request.name,
            activity_type=request.activity_type,
            date=request.date,
            duration_min=request.duration_min,
            distance_km=request.distance_km,
            rpe=request.rpe,
            avg_hr=request.avg_hr,
            max_hr=request.max_hr,
            notes=request.notes,
        )

        workout = service.log_manual_workout(
            user_id=current_user.id,
            workout_data=workout_data,
        )

        return ManualWorkoutResponse(
            activity_id=workout.activity_id,
            user_id=workout.user_id,
            name=workout.name,
            activity_type=workout.activity_type,
            date=workout.date,
            duration_min=workout.duration_min,
            distance_km=workout.distance_km,
            rpe=workout.rpe,
            avg_hr=workout.avg_hr,
            max_hr=workout.max_hr,
            estimated_load=workout.estimated_load,
            notes=workout.notes,
            created_at=workout.created_at,
            source="manual",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error logging manual workout: {e}")
        raise HTTPException(status_code=500, detail="Failed to log workout")


@router.get("/", response_model=PaginatedManualWorkoutsResponse)
async def list_manual_workouts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    current_user: CurrentUser = Depends(get_current_user),
    service: ManualWorkoutService = Depends(get_service),
):
    """
    List manual workouts with pagination.

    Returns workouts ordered by date (newest first).
    """
    offset = (page - 1) * page_size

    workouts, total = service.get_manual_workouts(
        user_id=current_user.id,
        limit=page_size,
        offset=offset,
        start_date=start_date,
        end_date=end_date,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedManualWorkoutsResponse(
        items=[
            ManualWorkoutResponse(
                activity_id=w.activity_id,
                user_id=w.user_id,
                name=w.name,
                activity_type=w.activity_type,
                date=w.date,
                duration_min=w.duration_min,
                distance_km=w.distance_km,
                rpe=w.rpe,
                avg_hr=w.avg_hr,
                max_hr=w.max_hr,
                estimated_load=w.estimated_load,
                notes=w.notes,
                created_at=w.created_at,
                source="manual",
            )
            for w in workouts
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/weekly-summary", response_model=List[WeeklyLoadSummary])
async def get_weekly_load_summary(
    weeks: int = Query(4, ge=1, le=52, description="Number of weeks to include"),
    current_user: CurrentUser = Depends(get_current_user),
    service: ManualWorkoutService = Depends(get_service),
):
    """
    Get weekly training load summary from manual workouts.

    Returns aggregated data for the specified number of weeks,
    including total load, workout count, duration, and average RPE.
    """
    summaries = service.get_weekly_load_summary(
        user_id=current_user.id,
        weeks=weeks,
    )

    return [
        WeeklyLoadSummary(**summary)
        for summary in summaries
    ]


@router.get("/{workout_id}", response_model=ManualWorkoutResponse)
async def get_manual_workout(
    workout_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: ManualWorkoutService = Depends(get_service),
):
    """
    Get a specific manual workout by ID.
    """
    workout = service.get_manual_workout(
        user_id=current_user.id,
        workout_id=workout_id,
    )

    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    return ManualWorkoutResponse(
        activity_id=workout.activity_id,
        user_id=workout.user_id,
        name=workout.name,
        activity_type=workout.activity_type,
        date=workout.date,
        duration_min=workout.duration_min,
        distance_km=workout.distance_km,
        rpe=workout.rpe,
        avg_hr=workout.avg_hr,
        max_hr=workout.max_hr,
        estimated_load=workout.estimated_load,
        notes=workout.notes,
        created_at=workout.created_at,
        source="manual",
    )


@router.delete("/{workout_id}", status_code=204)
async def delete_manual_workout(
    workout_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: ManualWorkoutService = Depends(get_service),
):
    """
    Delete a manual workout.
    """
    deleted = service.delete_manual_workout(
        user_id=current_user.id,
        workout_id=workout_id,
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Workout not found")

    return None


@router.post("/estimate-load", response_model=LoadEstimateResponse)
async def estimate_training_load(
    request: LoadEstimateRequest,
):
    """
    Estimate training load from duration and RPE.

    This is a utility endpoint that doesn't require authentication,
    allowing users to preview estimated load before logging a workout.

    Uses the session-RPE method: Load = Duration x RPE x 0.8
    """
    estimated_load = ManualWorkoutService.estimate_load_from_rpe(
        duration_min=request.duration_min,
        rpe=request.rpe,
    )

    # Categorize the load
    if estimated_load < 50:
        category = "light"
        description = "Recovery or easy workout. Good for active recovery days."
    elif estimated_load < 100:
        category = "moderate"
        description = "Moderate training stimulus. Suitable for regular training days."
    elif estimated_load < 150:
        category = "hard"
        description = "Significant training load. Allow adequate recovery."
    elif estimated_load < 200:
        category = "very_hard"
        description = "High training load. Consider rest or easy training the next day."
    else:
        category = "extreme"
        description = "Extreme training load. Extended recovery recommended."

    return LoadEstimateResponse(
        duration_min=request.duration_min,
        rpe=request.rpe,
        estimated_load=estimated_load,
        load_category=category,
        description=description,
    )


@router.get("/rpe-guide", response_model=dict)
async def get_rpe_guide():
    """
    Get the RPE scale guide with descriptions.

    Returns information about each RPE level to help users
    accurately rate their perceived exertion.
    """
    return {
        "scale": "borg_modified",
        "range": {"min": 1, "max": 10},
        "levels": [
            {
                "value": 1,
                "label": "Very Light",
                "description": "Barely moving",
                "breathing": "Normal",
                "talk_test": "Full conversation",
                "color": "green",
            },
            {
                "value": 2,
                "label": "Very Light",
                "description": "Barely moving",
                "breathing": "Normal",
                "talk_test": "Full conversation",
                "color": "green",
            },
            {
                "value": 3,
                "label": "Light",
                "description": "Easy effort",
                "breathing": "Slightly elevated",
                "talk_test": "Sentences",
                "color": "green",
            },
            {
                "value": 4,
                "label": "Light",
                "description": "Easy effort",
                "breathing": "Slightly elevated",
                "talk_test": "Sentences",
                "color": "lime",
            },
            {
                "value": 5,
                "label": "Moderate",
                "description": "Comfortable",
                "breathing": "Noticeable",
                "talk_test": "Phrases",
                "color": "yellow",
            },
            {
                "value": 6,
                "label": "Moderate",
                "description": "Comfortable",
                "breathing": "Noticeable",
                "talk_test": "Phrases",
                "color": "yellow",
            },
            {
                "value": 7,
                "label": "Hard",
                "description": "Challenging",
                "breathing": "Heavy",
                "talk_test": "Few words",
                "color": "orange",
            },
            {
                "value": 8,
                "label": "Hard",
                "description": "Challenging",
                "breathing": "Heavy",
                "talk_test": "Few words",
                "color": "orange",
            },
            {
                "value": 9,
                "label": "Maximum",
                "description": "All-out",
                "breathing": "Gasping",
                "talk_test": "Can't talk",
                "color": "red",
            },
            {
                "value": 10,
                "label": "Maximum",
                "description": "All-out",
                "breathing": "Gasping",
                "talk_test": "Can't talk",
                "color": "red",
            },
        ],
        "reference": {
            "title": "Session-RPE Method",
            "authors": "Foster et al.",
            "year": 2001,
            "journal": "Journal of Strength and Conditioning Research",
            "description": "Training load is calculated as Duration (minutes) x RPE, providing a simple but validated method for quantifying internal training load without heart rate monitoring.",
        },
    }
