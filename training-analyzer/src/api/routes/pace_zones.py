"""
VDOT Pace Zones API Routes

Endpoints for calculating VDOT from race results and managing
user's saved pace zones based on Jack Daniels' Running Formula.
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from ..deps import get_current_user, get_training_db, CurrentUser
from ...metrics.vdot import (
    calculate_vdot,
    get_pace_zones,
    predict_race_times,
    calculate_vdot_from_race,
    parse_race_time,
    pace_km_to_mile,
    format_pace_per_mile,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class CalculateVDOTRequest(BaseModel):
    """Request to calculate VDOT from a race result."""
    distance: str = Field(
        ...,
        description="Race distance: '5K', '10K', 'half', 'marathon', or 'custom'",
        examples=["5K", "10K", "half", "marathon"],
    )
    time: str = Field(
        ...,
        description="Race time in H:MM:SS, MM:SS, or seconds",
        examples=["25:30", "1:45:00", "3600"],
    )
    custom_distance_m: Optional[float] = Field(
        None,
        description="Distance in meters (required if distance is 'custom')",
        ge=100,
        le=100000,
    )

    @field_validator('distance')
    @classmethod
    def validate_distance(cls, v):
        valid_distances = ['5k', '10k', 'half', 'half_marathon', 'marathon', 'custom']
        if v.lower().replace('-', '_').replace(' ', '_') not in valid_distances:
            raise ValueError(
                f"Invalid distance. Must be one of: 5K, 10K, half, marathon, custom"
            )
        return v


class PaceZoneResponse(BaseModel):
    """A single pace zone with all details."""
    name: str
    min_pace_sec_per_km: float
    max_pace_sec_per_km: float
    min_pace_formatted: str
    max_pace_formatted: str
    pace_range_formatted: str
    min_pace_per_mile: str
    max_pace_per_mile: str
    description: str
    hr_range_min: int
    hr_range_max: int
    typical_duration: str


class RacePredictionResponse(BaseModel):
    """Race time prediction for a distance."""
    distance: str
    distance_km: float
    time_sec: int
    time_formatted: str
    pace_sec_per_km: float
    pace_formatted: str
    pace_per_mile: str


class VDOTCalculationResponse(BaseModel):
    """Complete VDOT calculation result."""
    vdot: float
    race_distance: str
    race_time_sec: int
    race_time_formatted: str
    pace_zones: Dict[str, PaceZoneResponse]
    race_predictions: List[RacePredictionResponse]


class SavePaceZonesRequest(BaseModel):
    """Request to save user's pace zones."""
    vdot: float = Field(..., ge=25, le=90, description="VDOT value")
    source_distance: Optional[str] = Field(
        None, description="Race distance used to calculate VDOT"
    )
    source_time_sec: Optional[int] = Field(
        None, ge=0, description="Race time used to calculate VDOT"
    )


class UserPaceZonesResponse(BaseModel):
    """User's saved pace zones."""
    vdot: float
    source_distance: Optional[str]
    source_time_sec: Optional[int]
    source_time_formatted: Optional[str]
    pace_zones: Dict[str, PaceZoneResponse]
    race_predictions: List[RacePredictionResponse]
    saved_at: str


# =============================================================================
# Helper Functions
# =============================================================================

def _format_time(seconds: int) -> str:
    """Format seconds to H:MM:SS or MM:SS."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _pace_zone_to_response(name: str, zone: dict) -> PaceZoneResponse:
    """Convert a pace zone dict to response model."""
    min_pace = zone['min_pace_sec_per_km']
    max_pace = zone['max_pace_sec_per_km']

    return PaceZoneResponse(
        name=zone['name'],
        min_pace_sec_per_km=min_pace,
        max_pace_sec_per_km=max_pace,
        min_pace_formatted=zone['min_pace_formatted'],
        max_pace_formatted=zone['max_pace_formatted'],
        pace_range_formatted=zone['pace_range_formatted'],
        min_pace_per_mile=format_pace_per_mile(min_pace),
        max_pace_per_mile=format_pace_per_mile(max_pace),
        description=zone['description'],
        hr_range_min=zone['hr_range']['min'],
        hr_range_max=zone['hr_range']['max'],
        typical_duration=zone['typical_duration'],
    )


def _prediction_to_response(name: str, prediction: dict) -> RacePredictionResponse:
    """Convert a race prediction dict to response model."""
    pace = prediction['pace_sec_per_km']

    return RacePredictionResponse(
        distance=name,
        distance_km=prediction['distance_km'],
        time_sec=prediction['time_sec'],
        time_formatted=prediction['time_formatted'],
        pace_sec_per_km=pace,
        pace_formatted=prediction['pace_formatted'],
        pace_per_mile=format_pace_per_mile(pace),
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/calculate-vdot", response_model=VDOTCalculationResponse)
async def calculate_vdot_endpoint(
    request: CalculateVDOTRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Calculate VDOT from a race result.

    This endpoint calculates your VDOT (Jack Daniels' running ability metric)
    from a recent race performance, then returns:

    1. **VDOT Score**: Your current running fitness level (typically 30-85)
    2. **Pace Zones**: Recommended training paces for different workout types
    3. **Race Predictions**: Expected finish times for standard distances

    The calculation uses the exact formulas from Jack Daniels' Running Formula,
    which account for:
    - Oxygen cost of running at various velocities
    - Percentage of VO2max sustainable for different race durations

    **Training Zones Explained:**
    - **Easy**: Recovery runs, conversational pace (65-79% max HR)
    - **Marathon**: Marathon-specific training (80-89% max HR)
    - **Threshold**: Tempo runs, lactate threshold (88-92% max HR)
    - **Interval**: VO2max training, 3-5 min intervals (95-100% max HR)
    - **Repetition**: Speed work, 200-400m repeats (neuromuscular)

    **Requires authentication.**
    """
    try:
        result = calculate_vdot_from_race(
            distance=request.distance,
            time_str=request.time,
            custom_distance_m=request.custom_distance_m,
        )

        # Convert to response format
        result_dict = result.to_dict()

        pace_zones = {
            name: _pace_zone_to_response(name, zone_data)
            for name, zone_data in result_dict['pace_zones'].items()
        }

        race_predictions = [
            _prediction_to_response(name, pred_data)
            for name, pred_data in result_dict['race_predictions'].items()
        ]

        return VDOTCalculationResponse(
            vdot=result_dict['vdot'],
            race_distance=result_dict['race_distance'],
            race_time_sec=result_dict['race_time_sec'],
            race_time_formatted=result_dict['race_time_formatted'],
            pace_zones=pace_zones,
            race_predictions=race_predictions,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating VDOT: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to calculate VDOT. Please check your input and try again."
        )


@router.get("/my-zones", response_model=Optional[UserPaceZonesResponse])
async def get_my_pace_zones(
    current_user: CurrentUser = Depends(get_current_user),
    training_db = Depends(get_training_db),
):
    """
    Get the user's saved pace zones.

    Returns the user's stored VDOT and corresponding pace zones,
    or null if no zones have been saved yet.

    **Requires authentication.**
    """
    try:
        # Try to get saved VDOT from user profile or preferences
        profile = training_db.get_user_profile()

        if not profile or not hasattr(profile, 'vdot') or not profile.vdot:
            # Try to get from user preferences table
            prefs = training_db.get_user_preference(current_user.user_id, 'vdot_zones')
            if not prefs:
                return None

            vdot = prefs.get('vdot')
            if not vdot:
                return None

            source_distance = prefs.get('source_distance')
            source_time_sec = prefs.get('source_time_sec')
            saved_at = prefs.get('saved_at', '')
        else:
            vdot = profile.vdot
            # Check for additional metadata in preferences
            prefs = training_db.get_user_preference(current_user.user_id, 'vdot_zones') or {}
            source_distance = prefs.get('source_distance')
            source_time_sec = prefs.get('source_time_sec')
            saved_at = prefs.get('saved_at', '')

        # Calculate zones from VDOT
        zones = get_pace_zones(vdot)
        predictions = predict_race_times(vdot)

        pace_zones = {
            name: _pace_zone_to_response(name, zone.to_dict())
            for name, zone in zones.items()
        }

        race_predictions = [
            _prediction_to_response(name, pred_data)
            for name, pred_data in predictions.items()
        ]

        return UserPaceZonesResponse(
            vdot=vdot,
            source_distance=source_distance,
            source_time_sec=source_time_sec,
            source_time_formatted=_format_time(source_time_sec) if source_time_sec else None,
            pace_zones=pace_zones,
            race_predictions=race_predictions,
            saved_at=saved_at,
        )

    except Exception as e:
        logger.error(f"Error getting pace zones: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve pace zones."
        )


@router.put("/my-zones", response_model=UserPaceZonesResponse)
async def save_my_pace_zones(
    request: SavePaceZonesRequest,
    current_user: CurrentUser = Depends(get_current_user),
    training_db = Depends(get_training_db),
):
    """
    Save the user's pace zones.

    Stores the user's VDOT value and optionally the source race
    that was used to calculate it. The zones can then be retrieved
    via GET /my-zones.

    **Requires authentication.**
    """
    try:
        from datetime import datetime

        # Store VDOT in user preferences
        vdot_data = {
            'vdot': request.vdot,
            'source_distance': request.source_distance,
            'source_time_sec': request.source_time_sec,
            'saved_at': datetime.now().isoformat(),
        }

        training_db.set_user_preference(
            current_user.user_id,
            'vdot_zones',
            vdot_data,
        )

        # Also try to update the user profile if it has a vdot field
        try:
            training_db.update_user_profile_vdot(current_user.user_id, request.vdot)
        except Exception:
            pass  # Profile might not have vdot field

        # Calculate and return the full response
        zones = get_pace_zones(request.vdot)
        predictions = predict_race_times(request.vdot)

        pace_zones = {
            name: _pace_zone_to_response(name, zone.to_dict())
            for name, zone in zones.items()
        }

        race_predictions = [
            _prediction_to_response(name, pred_data)
            for name, pred_data in predictions.items()
        ]

        return UserPaceZonesResponse(
            vdot=request.vdot,
            source_distance=request.source_distance,
            source_time_sec=request.source_time_sec,
            source_time_formatted=_format_time(request.source_time_sec) if request.source_time_sec else None,
            pace_zones=pace_zones,
            race_predictions=race_predictions,
            saved_at=vdot_data['saved_at'],
        )

    except Exception as e:
        logger.error(f"Error saving pace zones: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to save pace zones."
        )


@router.get("/zones-from-vdot")
async def get_zones_from_vdot(
    vdot: float = Query(..., ge=25, le=90, description="VDOT value"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get pace zones for a specific VDOT value without saving.

    This is useful for previewing zones before saving, or for
    comparing different VDOT values.

    **Requires authentication.**
    """
    try:
        zones = get_pace_zones(vdot)
        predictions = predict_race_times(vdot)

        pace_zones = {
            name: _pace_zone_to_response(name, zone.to_dict())
            for name, zone in zones.items()
        }

        race_predictions = [
            _prediction_to_response(name, pred_data)
            for name, pred_data in predictions.items()
        ]

        return {
            "vdot": vdot,
            "pace_zones": pace_zones,
            "race_predictions": race_predictions,
        }

    except Exception as e:
        logger.error(f"Error calculating zones from VDOT: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to calculate pace zones."
        )


@router.get("/race-equivalents")
async def get_race_equivalents(
    distance: str = Query(..., description="Race distance (5K, 10K, half, marathon)"),
    time: str = Query(..., description="Race time (H:MM:SS or MM:SS)"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Calculate equivalent race times for other distances.

    Given a race result, calculates what you should be able to run
    at other distances assuming equal fitness and preparation.

    This is based on the relationship between VDOT and race performance
    established by Jack Daniels.

    **Requires authentication.**
    """
    try:
        result = calculate_vdot_from_race(distance, time)
        result_dict = result.to_dict()

        return {
            "input_race": {
                "distance": result_dict['race_distance'],
                "time": result_dict['race_time_formatted'],
                "vdot": result_dict['vdot'],
            },
            "equivalent_races": [
                _prediction_to_response(name, pred_data)
                for name, pred_data in result_dict['race_predictions'].items()
            ],
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating race equivalents: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to calculate race equivalents."
        )
