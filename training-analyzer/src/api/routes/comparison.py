"""
Workout Comparison API Routes.

Provides endpoints for comparing workouts and getting normalized time series data
for overlay comparison in charts.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import get_training_db, get_current_user, CurrentUser
from ...services.comparison_service import (
    ComparisonService,
    NormalizationMode,
    ComparisonTarget,
    NormalizedTimeSeries,
    ComparisonStats,
    WorkoutComparison,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic models for API
# ============================================================================

class ComparisonTargetResponse(BaseModel):
    """A workout available for comparison."""
    activity_id: str
    name: str
    activity_type: str
    date: str
    duration_min: float
    distance_km: Optional[float] = None
    avg_hr: Optional[int] = None
    avg_pace_sec_km: Optional[float] = None
    similarity_score: float = 0.0
    is_pr: bool = False
    quick_selection_type: Optional[str] = None

    @classmethod
    def from_target(cls, target: ComparisonTarget) -> "ComparisonTargetResponse":
        return cls(
            activity_id=target.activity_id,
            name=target.name,
            activity_type=target.activity_type,
            date=target.date,
            duration_min=target.duration_min,
            distance_km=target.distance_km,
            avg_hr=target.avg_hr,
            avg_pace_sec_km=target.avg_pace_sec_km,
            similarity_score=target.similarity_score,
            is_pr=target.is_pr,
            quick_selection_type=target.quick_selection_type,
        )


class ComparableWorkoutsResponse(BaseModel):
    """Response containing comparable workouts."""
    targets: List[ComparisonTargetResponse]
    quick_selections: List[ComparisonTargetResponse]
    total: int


class NormalizedTimeSeriesResponse(BaseModel):
    """Normalized time series data for comparison."""
    timestamps: List[float]
    heart_rate: List[Optional[float]] = Field(default_factory=list)
    pace: List[Optional[float]] = Field(default_factory=list)
    power: List[Optional[float]] = Field(default_factory=list)
    cadence: List[Optional[float]] = Field(default_factory=list)
    elevation: List[Optional[float]] = Field(default_factory=list)

    @classmethod
    def from_series(cls, series: NormalizedTimeSeries) -> "NormalizedTimeSeriesResponse":
        return cls(
            timestamps=series.timestamps,
            heart_rate=series.heart_rate,
            pace=series.pace,
            power=series.power,
            cadence=series.cadence,
            elevation=series.elevation,
        )


class ComparisonStatsResponse(BaseModel):
    """Statistics comparing two workouts."""
    hr_avg_diff: Optional[float] = None
    hr_max_diff: Optional[float] = None
    pace_avg_diff: Optional[float] = None
    power_avg_diff: Optional[float] = None
    duration_diff: float = 0.0
    distance_diff: Optional[float] = None
    improvement_metrics: Dict[str, float] = Field(default_factory=dict)

    @classmethod
    def from_stats(cls, stats: ComparisonStats) -> "ComparisonStatsResponse":
        return cls(
            hr_avg_diff=stats.hr_avg_diff,
            hr_max_diff=stats.hr_max_diff,
            pace_avg_diff=stats.pace_avg_diff,
            power_avg_diff=stats.power_avg_diff,
            duration_diff=stats.duration_diff,
            distance_diff=stats.distance_diff,
            improvement_metrics=stats.improvement_metrics,
        )


class WorkoutComparisonResponse(BaseModel):
    """Complete comparison response."""
    primary_id: str
    comparison_id: str
    normalization_mode: str
    primary_series: NormalizedTimeSeriesResponse
    comparison_series: NormalizedTimeSeriesResponse
    stats: ComparisonStatsResponse
    sample_count: int


class CompareWorkoutsRequest(BaseModel):
    """Request to compare two workouts."""
    comparison_id: str = Field(..., description="ID of the workout to compare against")
    normalization_mode: str = Field(
        default="percentage",
        description="How to normalize data: time, distance, or percentage"
    )
    sample_count: int = Field(
        default=100,
        ge=10,
        le=500,
        description="Number of normalized sample points"
    )


class ComparableWorkoutsFilters(BaseModel):
    """Filters for finding comparable workouts."""
    workout_type: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    min_distance: Optional[float] = None
    max_distance: Optional[float] = None


# ============================================================================
# Helper functions
# ============================================================================

def get_comparison_service(training_db=Depends(get_training_db)) -> ComparisonService:
    """Get comparison service instance."""
    return ComparisonService(training_db)


# ============================================================================
# API Routes
# ============================================================================

@router.get("/{activity_id}/comparable", response_model=ComparableWorkoutsResponse)
async def get_comparable_workouts(
    activity_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    workout_type: Optional[str] = None,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    min_distance: Optional[float] = None,
    max_distance: Optional[float] = None,
    current_user: CurrentUser = Depends(get_current_user),
    comparison_service: ComparisonService = Depends(get_comparison_service),
):
    """
    Get workouts comparable to the specified activity.

    Returns a list of similar workouts that can be used for comparison,
    including quick selection options like "Best 10K" or "Last Similar".

    **Similarity Scoring:**
    - Activity type match (40% weight)
    - Distance similarity within 20% (30% weight)
    - Duration similarity within 30% (30% weight)

    **Quick Selections:**
    - `last_similar`: Most recent workout with high similarity
    - `best_pace`: Best pace for the same activity type
    - `best_5k`, `best_10k`, etc.: Best performance for specific distances
    """
    # Build filters
    filters = {}
    if workout_type:
        filters["workout_type"] = workout_type
    if date_start:
        filters["date_start"] = date_start
    if date_end:
        filters["date_end"] = date_end
    if min_distance is not None:
        filters["min_distance"] = min_distance
    if max_distance is not None:
        filters["max_distance"] = max_distance

    try:
        targets = comparison_service.find_comparable_workouts(
            activity_id=activity_id,
            user_id=current_user.id,
            limit=limit,
            filters=filters if filters else None,
        )

        # Separate quick selections from regular targets
        quick_selections = [t for t in targets if t.quick_selection_type]
        regular_targets = [t for t in targets if not t.quick_selection_type]

        return ComparableWorkoutsResponse(
            targets=[ComparisonTargetResponse.from_target(t) for t in regular_targets],
            quick_selections=[ComparisonTargetResponse.from_target(t) for t in quick_selections],
            total=len(targets),
        )

    except Exception as e:
        logger.error(f"Error finding comparable workouts: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to find comparable workouts"
        )


@router.get("/{activity_id}/normalized", response_model=NormalizedTimeSeriesResponse)
async def get_normalized_data(
    activity_id: str,
    mode: str = Query(default="percentage", regex="^(time|distance|percentage)$"),
    sample_count: int = Query(default=100, ge=10, le=500),
    current_user: CurrentUser = Depends(get_current_user),
    comparison_service: ComparisonService = Depends(get_comparison_service),
    training_db=Depends(get_training_db),
):
    """
    Get time/distance normalized data for an activity.

    Normalizes the activity's time series data to a fixed number of samples,
    allowing direct comparison between workouts of different durations.

    **Normalization Modes:**
    - `time`: Normalize by elapsed time
    - `distance`: Normalize by distance covered
    - `percentage`: Normalize by percentage of workout completion (default)

    **Returns:**
    Time series arrays for heart_rate, pace, power, cadence, and elevation,
    all resampled to the specified sample_count.
    """
    try:
        # Get the activity details first
        from .workouts import _fetch_garmin_activity_details, _is_running_activity

        # Try to fetch from Garmin
        details = await _fetch_garmin_activity_details(activity_id)

        if not details:
            # Fall back to local data
            local_activity = training_db.get_activity_metrics(activity_id)
            if not local_activity:
                raise HTTPException(
                    status_code=404,
                    detail=f"Activity {activity_id} not found"
                )

            # Return empty normalized series for local data without time series
            return NormalizedTimeSeriesResponse(
                timestamps=list(range(sample_count)),
                heart_rate=[None] * sample_count,
                pace=[None] * sample_count,
                power=[None] * sample_count,
                cadence=[None] * sample_count,
                elevation=[None] * sample_count,
            )

        # Convert time series to dict format for normalization
        time_series_dict = {
            "heart_rate": [{"timestamp": p.timestamp, "hr": p.hr} for p in details.time_series.heart_rate],
            "pace_or_speed": [{"timestamp": p.timestamp, "value": p.value} for p in details.time_series.pace_or_speed],
            "elevation": [{"timestamp": p.timestamp, "elevation": p.elevation} for p in details.time_series.elevation],
            "cadence": [{"timestamp": p.timestamp, "cadence": p.cadence} for p in details.time_series.cadence],
            "power": [{"timestamp": p.timestamp, "power": p.power} for p in details.time_series.power],
        }

        # Normalize the time series
        norm_mode = NormalizationMode(mode)
        normalized = comparison_service.normalize_time_series(
            time_series_dict,
            norm_mode,
            sample_count,
        )

        return NormalizedTimeSeriesResponse.from_series(normalized)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error normalizing activity data: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to normalize activity data"
        )


@router.post("/{activity_id}/compare", response_model=WorkoutComparisonResponse)
async def compare_workouts(
    activity_id: str,
    request: CompareWorkoutsRequest,
    current_user: CurrentUser = Depends(get_current_user),
    comparison_service: ComparisonService = Depends(get_comparison_service),
    training_db=Depends(get_training_db),
):
    """
    Compare two workouts and get normalized overlay data.

    Returns normalized time series data for both workouts, allowing them
    to be overlaid in a chart for visual comparison.

    **Comparison Features:**
    - Normalized time series for all metrics (HR, pace, power, cadence, elevation)
    - Statistical comparison (average differences, improvement percentages)
    - Difference highlighting data for visualization

    **Usage:**
    1. Get comparable workouts using `GET /comparison/{id}/comparable`
    2. Call this endpoint with the chosen comparison workout ID
    3. Use the normalized series data for chart overlay
    """
    try:
        from .workouts import _fetch_garmin_activity_details

        # Fetch both activities
        primary_details = await _fetch_garmin_activity_details(activity_id)
        comparison_details = await _fetch_garmin_activity_details(request.comparison_id)

        if not primary_details:
            raise HTTPException(
                status_code=404,
                detail=f"Primary activity {activity_id} not found"
            )

        if not comparison_details:
            raise HTTPException(
                status_code=404,
                detail=f"Comparison activity {request.comparison_id} not found"
            )

        # Convert to dict format
        primary_ts = {
            "heart_rate": [{"timestamp": p.timestamp, "hr": p.hr} for p in primary_details.time_series.heart_rate],
            "pace_or_speed": [{"timestamp": p.timestamp, "value": p.value} for p in primary_details.time_series.pace_or_speed],
            "elevation": [{"timestamp": p.timestamp, "elevation": p.elevation} for p in primary_details.time_series.elevation],
            "cadence": [{"timestamp": p.timestamp, "cadence": p.cadence} for p in primary_details.time_series.cadence],
            "power": [{"timestamp": p.timestamp, "power": p.power} for p in primary_details.time_series.power],
        }

        comparison_ts = {
            "heart_rate": [{"timestamp": p.timestamp, "hr": p.hr} for p in comparison_details.time_series.heart_rate],
            "pace_or_speed": [{"timestamp": p.timestamp, "value": p.value} for p in comparison_details.time_series.pace_or_speed],
            "elevation": [{"timestamp": p.timestamp, "elevation": p.elevation} for p in comparison_details.time_series.elevation],
            "cadence": [{"timestamp": p.timestamp, "cadence": p.cadence} for p in comparison_details.time_series.cadence],
            "power": [{"timestamp": p.timestamp, "power": p.power} for p in comparison_details.time_series.power],
        }

        # Normalize both
        norm_mode = NormalizationMode(request.normalization_mode)
        primary_normalized = comparison_service.normalize_time_series(
            primary_ts, norm_mode, request.sample_count
        )
        comparison_normalized = comparison_service.normalize_time_series(
            comparison_ts, norm_mode, request.sample_count
        )

        # Calculate stats
        primary_info = {
            "duration_sec": primary_details.basic_info.duration_sec,
            "distance_m": primary_details.basic_info.distance_m,
        }
        comparison_info = {
            "duration_sec": comparison_details.basic_info.duration_sec,
            "distance_m": comparison_details.basic_info.distance_m,
        }

        stats = comparison_service.calculate_comparison_stats(
            primary_normalized,
            comparison_normalized,
            primary_info,
            comparison_info,
        )

        return WorkoutComparisonResponse(
            primary_id=activity_id,
            comparison_id=request.comparison_id,
            normalization_mode=request.normalization_mode,
            primary_series=NormalizedTimeSeriesResponse.from_series(primary_normalized),
            comparison_series=NormalizedTimeSeriesResponse.from_series(comparison_normalized),
            stats=ComparisonStatsResponse.from_stats(stats),
            sample_count=request.sample_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing workouts: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to compare workouts"
        )
