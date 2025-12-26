"""
FIT Export API routes.

Provides dedicated endpoints for FIT file generation and Garmin export.
This module extends the basic export functionality in workouts.py
with additional features.
"""

import base64
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from ...models.workouts import (
    IntervalType,
    IntensityZone,
    StructuredWorkout,
    WorkoutInterval,
    WorkoutSport,
)
from ...fit.encoder import FITEncoder, encode_workout_to_fit


router = APIRouter()


# ============================================================================
# Pydantic models for API
# ============================================================================

class IntervalInput(BaseModel):
    """Input model for a workout interval."""
    type: str = Field(..., description="Interval type: warmup, work, recovery, cooldown, rest")
    duration_sec: Optional[int] = Field(None, description="Duration in seconds")
    distance_m: Optional[int] = Field(None, description="Distance in meters")
    target_pace_min: Optional[int] = Field(None, description="Target pace min (sec/km)")
    target_pace_max: Optional[int] = Field(None, description="Target pace max (sec/km)")
    target_hr_min: Optional[int] = Field(None, description="Target HR min (bpm)")
    target_hr_max: Optional[int] = Field(None, description="Target HR max (bpm)")
    repetitions: int = Field(1, description="Number of repetitions")
    notes: Optional[str] = Field(None, description="Step notes/name")

    def to_workout_interval(self) -> WorkoutInterval:
        """Convert to WorkoutInterval dataclass."""
        interval_type_map = {
            "warmup": IntervalType.WARMUP,
            "work": IntervalType.WORK,
            "recovery": IntervalType.RECOVERY,
            "cooldown": IntervalType.COOLDOWN,
            "rest": IntervalType.REST,
            "active_recovery": IntervalType.ACTIVE_RECOVERY,
        }

        return WorkoutInterval(
            type=interval_type_map.get(self.type.lower(), IntervalType.WORK),
            duration_sec=self.duration_sec,
            distance_m=self.distance_m,
            target_pace_range=(self.target_pace_min, self.target_pace_max) if self.target_pace_min and self.target_pace_max else None,
            target_hr_range=(self.target_hr_min, self.target_hr_max) if self.target_hr_min and self.target_hr_max else None,
            repetitions=self.repetitions,
            notes=self.notes,
        )


class ExportWorkoutRequest(BaseModel):
    """Request to export a workout to FIT format."""
    name: str = Field(..., description="Workout name", max_length=64)
    description: str = Field("", description="Workout description")
    sport: str = Field("running", description="Sport type: running, cycling, swimming")
    intervals: List[IntervalInput] = Field(..., description="Workout intervals")


class ExportFITResponse(BaseModel):
    """Response containing FIT file data."""
    filename: str
    content_type: str = "application/vnd.ant.fit"
    data_base64: str
    size_bytes: int


class BatchExportRequest(BaseModel):
    """Request to export multiple workouts."""
    workouts: List[ExportWorkoutRequest]


class BatchExportResponse(BaseModel):
    """Response containing multiple FIT files."""
    files: List[ExportFITResponse]
    total_count: int


# ============================================================================
# Helper functions
# ============================================================================

def _build_structured_workout(request: ExportWorkoutRequest) -> StructuredWorkout:
    """Build a StructuredWorkout from the API request."""
    sport_map = {
        "running": WorkoutSport.RUNNING,
        "cycling": WorkoutSport.CYCLING,
        "swimming": WorkoutSport.SWIMMING,
    }

    intervals = [i.to_workout_interval() for i in request.intervals]

    # Calculate estimated duration
    total_duration = sum(
        (i.duration_sec or 0) * i.repetitions
        for i in intervals
    )

    # Calculate estimated distance
    total_distance = sum(
        (i.distance_m or 0) * i.repetitions
        for i in intervals
    )

    return StructuredWorkout(
        name=request.name,
        description=request.description,
        sport=sport_map.get(request.sport.lower(), WorkoutSport.RUNNING),
        intervals=intervals,
        estimated_duration_min=total_duration // 60 if total_duration else 60,
        estimated_distance_m=total_distance if total_distance else None,
    )


def _cleanup_temp_file(path: str):
    """Background task to cleanup temporary files."""
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass


# ============================================================================
# API Routes
# ============================================================================

@router.post("/fit", response_model=ExportFITResponse)
async def export_to_fit(request: ExportWorkoutRequest):
    """
    Export a workout definition to Garmin FIT format.

    Returns the FIT file as base64-encoded data.
    Use this for programmatic access to FIT files.
    """
    try:
        # Build workout
        workout = _build_structured_workout(request)

        # Encode to FIT
        fit_bytes = encode_workout_to_fit(workout)
        encoded = base64.b64encode(fit_bytes).decode('ascii')

        # Generate filename
        safe_name = request.name.replace(" ", "_").lower()[:30]
        filename = f"{safe_name}.fit"

        return ExportFITResponse(
            filename=filename,
            data_base64=encoded,
            size_bytes=len(fit_bytes),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate FIT file: {str(e)}")


@router.post("/fit/download")
async def export_to_fit_download(
    request: ExportWorkoutRequest,
    background_tasks: BackgroundTasks,
):
    """
    Export a workout to FIT format and download as a file.

    Returns the FIT file as a downloadable attachment.
    """
    try:
        # Build workout
        workout = _build_structured_workout(request)

        # Encode to FIT and write to temp file
        encoder = FITEncoder()
        temp_path = encoder.encode_to_temp_file(workout)

        # Schedule cleanup
        background_tasks.add_task(_cleanup_temp_file, str(temp_path))

        # Generate filename
        safe_name = request.name.replace(" ", "_").lower()[:30]
        filename = f"{safe_name}.fit"

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


@router.post("/fit/batch", response_model=BatchExportResponse)
async def export_batch_to_fit(request: BatchExportRequest):
    """
    Export multiple workouts to FIT format.

    Returns all FIT files as base64-encoded data.
    Useful for batch export of training plans.
    """
    try:
        files = []

        for workout_request in request.workouts:
            # Build workout
            workout = _build_structured_workout(workout_request)

            # Encode to FIT
            fit_bytes = encode_workout_to_fit(workout)
            encoded = base64.b64encode(fit_bytes).decode('ascii')

            # Generate filename
            safe_name = workout_request.name.replace(" ", "_").lower()[:30]
            filename = f"{safe_name}.fit"

            files.append(ExportFITResponse(
                filename=filename,
                data_base64=encoded,
                size_bytes=len(fit_bytes),
            ))

        return BatchExportResponse(
            files=files,
            total_count=len(files),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate FIT files: {str(e)}")


@router.post("/validate")
async def validate_workout(request: ExportWorkoutRequest):
    """
    Validate a workout structure without generating FIT.

    Returns validation results including any warnings.
    """
    warnings = []
    errors = []

    # Check name length
    if len(request.name) > 64:
        errors.append("Workout name exceeds 64 characters")

    if not request.intervals:
        errors.append("Workout must have at least one interval")

    # Check intervals
    for i, interval in enumerate(request.intervals):
        if not interval.duration_sec and not interval.distance_m:
            warnings.append(f"Interval {i+1}: No duration or distance specified (will use open duration)")

        if interval.target_pace_min and interval.target_pace_max:
            if interval.target_pace_min > interval.target_pace_max:
                errors.append(f"Interval {i+1}: Pace min > max (remember slower pace = higher seconds)")

        if interval.target_hr_min and interval.target_hr_max:
            if interval.target_hr_min > interval.target_hr_max:
                errors.append(f"Interval {i+1}: HR min > max")

    # Calculate totals
    total_duration = sum(
        (i.duration_sec or 0) * i.repetitions
        for i in request.intervals
    )
    total_distance = sum(
        (i.distance_m or 0) * i.repetitions
        for i in request.intervals
    )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "name": request.name,
            "sport": request.sport,
            "interval_count": len(request.intervals),
            "total_steps": sum(i.repetitions for i in request.intervals),
            "estimated_duration_min": total_duration // 60 if total_duration else None,
            "estimated_distance_km": total_distance / 1000 if total_distance else None,
        }
    }


@router.get("/sports")
async def list_supported_sports():
    """List supported sports for FIT export."""
    return {
        "sports": [
            {"id": "running", "name": "Running", "fit_sport_id": 1},
            {"id": "cycling", "name": "Cycling", "fit_sport_id": 2},
            {"id": "swimming", "name": "Swimming", "fit_sport_id": 5},
        ]
    }


@router.get("/interval-types")
async def list_interval_types():
    """List supported interval types."""
    return {
        "interval_types": [
            {"id": "warmup", "name": "Warm Up", "description": "Low intensity warm-up"},
            {"id": "work", "name": "Work Interval", "description": "Main effort interval"},
            {"id": "recovery", "name": "Recovery", "description": "Recovery between intervals"},
            {"id": "cooldown", "name": "Cool Down", "description": "Low intensity cool-down"},
            {"id": "rest", "name": "Rest", "description": "Complete rest (standing)"},
            {"id": "active_recovery", "name": "Active Recovery", "description": "Easy movement recovery"},
        ]
    }
