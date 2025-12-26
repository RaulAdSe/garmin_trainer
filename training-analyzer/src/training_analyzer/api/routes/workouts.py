"""
Workout design and export API routes.

Provides endpoints for:
- AI-powered workout design
- Workout storage and retrieval
- FIT file export for Garmin devices
- Garmin Connect integration (future)
"""

from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from ..deps import get_coach_service, get_training_db
from ...models.workouts import (
    AthleteContext,
    IntervalType,
    IntensityZone,
    StructuredWorkout,
    WorkoutDesignRequest,
    WorkoutInterval,
    WorkoutSport,
)
from ...agents.workout_agent import WorkoutDesignAgent, get_workout_agent
from ...fit.encoder import FITEncoder, encode_workout_to_fit


router = APIRouter()


# In-memory workout storage (would be database in production)
_workout_store: Dict[str, StructuredWorkout] = {}


# ============================================================================
# Pydantic models for API
# ============================================================================

class WorkoutIntervalResponse(BaseModel):
    """API response model for a workout interval."""
    type: str
    duration_sec: Optional[int] = None
    distance_m: Optional[int] = None
    target_pace_min: Optional[int] = None
    target_pace_max: Optional[int] = None
    target_hr_min: Optional[int] = None
    target_hr_max: Optional[int] = None
    repetitions: int = 1
    notes: Optional[str] = None
    intensity_zone: Optional[str] = None

    @classmethod
    def from_workout_interval(cls, interval: WorkoutInterval) -> "WorkoutIntervalResponse":
        """Convert from WorkoutInterval dataclass."""
        return cls(
            type=interval.type.value if hasattr(interval.type, 'value') else str(interval.type),
            duration_sec=interval.duration_sec,
            distance_m=interval.distance_m,
            target_pace_min=interval.target_pace_range[0] if interval.target_pace_range else None,
            target_pace_max=interval.target_pace_range[1] if interval.target_pace_range else None,
            target_hr_min=interval.target_hr_range[0] if interval.target_hr_range else None,
            target_hr_max=interval.target_hr_range[1] if interval.target_hr_range else None,
            repetitions=interval.repetitions,
            notes=interval.notes,
            intensity_zone=interval.intensity_zone.value if interval.intensity_zone else None,
        )


class StructuredWorkoutResponse(BaseModel):
    """API response model for a structured workout."""
    workout_id: str
    name: str
    description: str
    sport: str = "running"
    intervals: List[WorkoutIntervalResponse]
    estimated_duration_min: int
    estimated_distance_km: Optional[float] = None
    estimated_load: Optional[float] = None
    created_at: Optional[str] = None

    @classmethod
    def from_structured_workout(cls, workout: StructuredWorkout) -> "StructuredWorkoutResponse":
        """Convert from StructuredWorkout dataclass."""
        return cls(
            workout_id=workout.id,
            name=workout.name,
            description=workout.description,
            sport=workout.sport.value if hasattr(workout.sport, 'value') else str(workout.sport),
            intervals=[
                WorkoutIntervalResponse.from_workout_interval(i)
                for i in workout.intervals
            ],
            estimated_duration_min=workout.estimated_duration_min,
            estimated_distance_km=workout.estimated_distance_m / 1000 if workout.estimated_distance_m else None,
            estimated_load=workout.estimated_load,
            created_at=workout.created_at.isoformat() if workout.created_at else None,
        )


class DesignWorkoutRequest(BaseModel):
    """Request to design a workout."""
    workout_type: str = Field(
        ...,
        description="Type of workout: easy, tempo, intervals, threshold, long, fartlek"
    )
    duration_min: Optional[int] = Field(
        None,
        description="Target duration in minutes",
        ge=10,
        le=300
    )
    target_load: Optional[float] = Field(
        None,
        description="Target training load (TSS/HRSS)",
        ge=0,
        le=500
    )
    focus: Optional[str] = Field(
        None,
        description="Training focus: speed, endurance, threshold, recovery"
    )
    use_ai: bool = Field(
        False,
        description="Use AI for more nuanced workout design (requires API key)"
    )


class ExportGarminRequest(BaseModel):
    """Request to export workout to Garmin Connect."""
    garmin_username: Optional[str] = None
    garmin_password: Optional[str] = None
    use_stored_credentials: bool = True


class ExportGarminResponse(BaseModel):
    """Response from Garmin Connect export."""
    success: bool
    message: str
    garmin_workout_id: Optional[str] = None


# ============================================================================
# Helper functions
# ============================================================================

def _build_athlete_context(
    coach_service,
    training_db,
) -> AthleteContext:
    """Build athlete context from available data."""
    try:
        # Get athlete profile
        profile = training_db.get_user_profile()

        # Get fitness metrics
        briefing = coach_service.get_daily_briefing(date.today())

        # Get race goals for training paces
        goals = training_db.get_race_goals()

        # Build context
        context = AthleteContext(
            max_hr=profile.max_hr if profile else 185,
            rest_hr=profile.rest_hr if profile else 55,
            lthr=profile.threshold_hr if profile else 165,
        )

        # Add fitness metrics if available
        if briefing:
            context.ctl = briefing.get("fitness", {}).get("ctl", 40.0)
            context.atl = briefing.get("fitness", {}).get("atl", 40.0)
            context.tsb = briefing.get("fitness", {}).get("tsb", 0.0)
            context.readiness_score = briefing.get("readiness", {}).get("score", 75)

        # Calculate training paces from goals if available
        if goals:
            try:
                from ...analysis.goals import calculate_training_paces, RaceGoal, RaceDistance

                first_goal = goals[0]
                distance = RaceDistance.from_string(str(first_goal.get("distance", "10k"))) or RaceDistance.TEN_K
                target_time = first_goal.get("target_time_sec", 3000)
                race_date_str = first_goal.get("race_date", date.today().isoformat())

                if isinstance(race_date_str, str):
                    race_date = datetime.strptime(race_date_str, "%Y-%m-%d").date()
                else:
                    race_date = race_date_str

                goal = RaceGoal(
                    race_date=race_date,
                    distance=distance,
                    target_time_sec=target_time,
                )
                paces = calculate_training_paces(goal)

                # Update context with calculated paces
                context.easy_pace = paces.get("easy", {}).get("pace_sec", 360)
                context.long_pace = paces.get("long", {}).get("pace_sec", 345)
                context.tempo_pace = paces.get("tempo", {}).get("pace_sec", 300)
                context.threshold_pace = paces.get("threshold", {}).get("pace_sec", 285)
                context.interval_pace = paces.get("interval", {}).get("pace_sec", 270)

            except Exception as e:
                # Use default paces if calculation fails
                print(f"Could not calculate training paces: {e}")

        return context

    except Exception as e:
        print(f"Error building athlete context: {e}")
        # Return default context
        return AthleteContext()


def _cleanup_temp_file(path: str):
    """Background task to cleanup temporary files."""
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass


# ============================================================================
# API Routes
# ============================================================================

@router.post("/design", response_model=StructuredWorkoutResponse)
async def design_workout(
    request: DesignWorkoutRequest,
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
):
    """
    AI-powered workout design.

    Creates structured workouts based on:
    - Workout type requested (easy, tempo, intervals, threshold, long, fartlek)
    - Current fitness level and readiness
    - Training paces calculated from race goals
    - Athlete's HR zones

    The designed workout can be exported to Garmin FIT format for device sync.

    **Workout Types:**
    - `easy`: Recovery/base building run at conversational pace
    - `tempo`: Sustained threshold effort (20-40 min at tempo pace)
    - `intervals`: High-intensity VO2max intervals with recovery
    - `threshold`: Cruise intervals at lactate threshold
    - `long`: Extended aerobic endurance run
    - `fartlek`: Speed play with varied intensity surges
    """
    try:
        # Build athlete context
        context = _build_athlete_context(coach_service, training_db)

        # Create workout design request
        design_request = WorkoutDesignRequest(
            workout_type=request.workout_type,
            duration_min=request.duration_min,
            target_load=request.target_load,
            focus=request.focus,
        )

        # Get workout agent
        agent = get_workout_agent()

        # Design the workout
        if request.use_ai:
            # Use async AI-powered design
            workout = await agent.design_workout_async(design_request, context)
        else:
            # Use rule-based design
            workout = agent.design_workout(design_request, context)

        # Store the workout
        _workout_store[workout.id] = workout

        # Return response
        return StructuredWorkoutResponse.from_structured_workout(workout)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to design workout: {str(e)}")


@router.get("/{workout_id}", response_model=StructuredWorkoutResponse)
async def get_workout(workout_id: str):
    """
    Get a specific designed workout by ID.

    Returns the full workout structure including all intervals
    with their target paces and HR zones.
    """
    workout = _workout_store.get(workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail=f"Workout {workout_id} not found")

    return StructuredWorkoutResponse.from_structured_workout(workout)


@router.get("/", response_model=List[StructuredWorkoutResponse])
async def list_workouts(
    limit: int = 20,
    offset: int = 0,
):
    """
    List all designed workouts.

    Returns workouts ordered by creation time (newest first).
    """
    workouts = list(_workout_store.values())
    workouts.sort(key=lambda w: w.created_at or datetime.min, reverse=True)

    paginated = workouts[offset:offset + limit]
    return [StructuredWorkoutResponse.from_structured_workout(w) for w in paginated]


@router.delete("/{workout_id}")
async def delete_workout(workout_id: str):
    """Delete a workout from storage."""
    if workout_id not in _workout_store:
        raise HTTPException(status_code=404, detail=f"Workout {workout_id} not found")

    del _workout_store[workout_id]
    return {"message": f"Workout {workout_id} deleted"}


@router.get("/{workout_id}/fit")
async def download_fit(
    workout_id: str,
    background_tasks: BackgroundTasks,
):
    """
    Download workout as Garmin FIT file.

    The FIT file can be:
    1. Transferred to Garmin device via USB (copy to /Garmin/NewFiles/)
    2. Imported to Garmin Connect web/app
    3. Synced via Garmin Express

    Returns a downloadable .fit file.
    """
    workout = _workout_store.get(workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail=f"Workout {workout_id} not found")

    try:
        # Encode to FIT
        encoder = FITEncoder()
        temp_path = encoder.encode_to_temp_file(workout)

        # Schedule cleanup
        background_tasks.add_task(_cleanup_temp_file, str(temp_path))

        # Generate filename
        safe_name = workout.name.replace(" ", "_").lower()[:30]
        filename = f"{safe_name}_{workout_id[-8:]}.fit"

        return FileResponse(
            path=str(temp_path),
            filename=filename,
            media_type="application/vnd.ant.fit",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate FIT file: {str(e)}")


@router.get("/{workout_id}/fit/bytes")
async def get_fit_bytes(workout_id: str):
    """
    Get workout as FIT file bytes (base64 encoded).

    Useful for programmatic access without file download.
    """
    import base64

    workout = _workout_store.get(workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail=f"Workout {workout_id} not found")

    try:
        fit_bytes = encode_workout_to_fit(workout)
        encoded = base64.b64encode(fit_bytes).decode('ascii')

        return {
            "workout_id": workout_id,
            "filename": f"{workout.name.replace(' ', '_').lower()}.fit",
            "content_type": "application/vnd.ant.fit",
            "data_base64": encoded,
            "size_bytes": len(fit_bytes),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate FIT bytes: {str(e)}")


@router.post("/{workout_id}/export-garmin", response_model=ExportGarminResponse)
async def export_to_garmin(
    workout_id: str,
    request: ExportGarminRequest,
):
    """
    Push workout directly to Garmin Connect.

    This endpoint uploads the workout to Garmin Connect so it can be
    synced to your Garmin device automatically.

    **Authentication:**
    - Provide Garmin Connect credentials, or
    - Use stored credentials (from previous authentication)

    **Note:** This feature requires valid Garmin Connect authentication.
    Direct API access may require Garmin Connect IQ developer access.
    """
    workout = _workout_store.get(workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail=f"Workout {workout_id} not found")

    # TODO: Implement Garmin Connect OAuth flow and workout upload
    # This would typically use:
    # 1. OAuth authentication with Garmin Connect
    # 2. Garmin Connect API to upload workout
    # 3. Or use garminconnect library: https://github.com/cyberjunky/python-garminconnect

    return ExportGarminResponse(
        success=False,
        message="Garmin Connect export not yet implemented. Please download the FIT file and manually import to Garmin Connect or transfer to your device.",
        garmin_workout_id=None,
    )


@router.post("/import-fit")
async def import_fit_workout(
    # Would accept file upload
):
    """
    Import a workout from a FIT file.

    Parse an existing FIT workout file and create a StructuredWorkout.
    Useful for editing existing workouts or importing from other sources.
    """
    # TODO: Implement FIT file parsing
    raise HTTPException(status_code=501, detail="FIT import not yet implemented")


# ============================================================================
# Convenience endpoints for quick workout generation
# ============================================================================

@router.post("/quick/easy", response_model=StructuredWorkoutResponse)
async def quick_easy_run(
    duration_min: int = 45,
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
):
    """Quick endpoint to generate an easy run workout."""
    request = DesignWorkoutRequest(workout_type="easy", duration_min=duration_min)
    return await design_workout(request, coach_service, training_db)


@router.post("/quick/tempo", response_model=StructuredWorkoutResponse)
async def quick_tempo_run(
    duration_min: int = 50,
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
):
    """Quick endpoint to generate a tempo run workout."""
    request = DesignWorkoutRequest(workout_type="tempo", duration_min=duration_min)
    return await design_workout(request, coach_service, training_db)


@router.post("/quick/intervals", response_model=StructuredWorkoutResponse)
async def quick_intervals(
    duration_min: int = 55,
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
):
    """Quick endpoint to generate an interval workout."""
    request = DesignWorkoutRequest(workout_type="intervals", duration_min=duration_min)
    return await design_workout(request, coach_service, training_db)


@router.post("/quick/long", response_model=StructuredWorkoutResponse)
async def quick_long_run(
    duration_min: int = 90,
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
):
    """Quick endpoint to generate a long run workout."""
    request = DesignWorkoutRequest(workout_type="long", duration_min=duration_min)
    return await design_workout(request, coach_service, training_db)
