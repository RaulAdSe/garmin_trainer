"""
Workout design and export API routes.

Provides endpoints for:
- AI-powered workout design
- Workout storage and retrieval (using SQLite persistence)
- FIT file export for Garmin devices
- Garmin Connect integration (future)
- Detailed activity data (time series, GPS, splits)
"""

from datetime import date, datetime
from typing import Dict, List, Optional, Tuple, Any
import tempfile
import hashlib
import json
import time
from pathlib import Path
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from ..deps import get_coach_service, get_training_db, get_workout_repository
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
from ...db.repositories.workout_repository import WorkoutRepository


router = APIRouter()


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
# Pydantic models for Activity Details endpoint
# ============================================================================

class TimeSeriesPoint(BaseModel):
    """A single point in a time series."""
    timestamp: int  # seconds from start
    value: float


class HeartRatePoint(BaseModel):
    """Heart rate data point."""
    timestamp: int  # seconds from start
    hr: int  # beats per minute


class PaceSpeedPoint(BaseModel):
    """Pace (for running) or speed (for cycling) data point."""
    timestamp: int  # seconds from start
    value: float  # pace in sec/km for running, speed in km/h for cycling


class ElevationPoint(BaseModel):
    """Elevation data point."""
    timestamp: int  # seconds from start
    elevation: float  # meters


class CadencePoint(BaseModel):
    """Cadence data point."""
    timestamp: int  # seconds from start
    cadence: int  # steps/min for running, rpm for cycling


class GPSCoordinate(BaseModel):
    """GPS coordinate for route mapping."""
    lat: float
    lon: float


class SplitData(BaseModel):
    """Per-km or per-lap split data."""
    split_number: int
    distance_m: float
    duration_sec: float
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    avg_pace_sec_km: Optional[float] = None  # for running
    avg_speed_kmh: Optional[float] = None  # for cycling
    elevation_gain_m: Optional[float] = None
    elevation_loss_m: Optional[float] = None
    avg_cadence: Optional[int] = None


class ActivityTimeSeries(BaseModel):
    """Time series data for an activity."""
    heart_rate: List[HeartRatePoint] = Field(default_factory=list)
    pace_or_speed: List[PaceSpeedPoint] = Field(default_factory=list)
    elevation: List[ElevationPoint] = Field(default_factory=list)
    cadence: List[CadencePoint] = Field(default_factory=list)


class BasicActivityInfo(BaseModel):
    """Basic activity summary info."""
    activity_id: str
    name: str
    activity_type: str
    sport_type: Optional[str] = None
    date: str
    start_time: Optional[str] = None
    duration_sec: int
    distance_m: Optional[float] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    avg_pace_sec_km: Optional[float] = None  # for running
    avg_speed_kmh: Optional[float] = None  # for cycling
    elevation_gain_m: Optional[float] = None
    calories: Optional[int] = None
    training_effect: Optional[float] = None


class ActivityDetailsResponse(BaseModel):
    """Complete detailed activity response."""
    basic_info: BasicActivityInfo
    time_series: ActivityTimeSeries
    gps_coordinates: List[GPSCoordinate] = Field(default_factory=list)
    splits: List[SplitData] = Field(default_factory=list)
    is_running: bool = True  # True for running (pace), False for cycling (speed)
    data_source: str = "garmin"  # garmin, strava, etc.
    cached: bool = False
    cache_timestamp: Optional[str] = None


# ============================================================================
# In-memory cache for activity details
# ============================================================================

# Simple in-memory cache with TTL
_activity_details_cache: Dict[str, Tuple[float, ActivityDetailsResponse]] = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour cache


def _get_cached_details(activity_id: str) -> Optional[ActivityDetailsResponse]:
    """Get cached activity details if available and not expired."""
    if activity_id in _activity_details_cache:
        cache_time, data = _activity_details_cache[activity_id]
        if time.time() - cache_time < _CACHE_TTL_SECONDS:
            # Update cached flag and timestamp
            data.cached = True
            data.cache_timestamp = datetime.fromtimestamp(cache_time).isoformat()
            return data
        else:
            # Expired, remove from cache
            del _activity_details_cache[activity_id]
    return None


def _set_cached_details(activity_id: str, data: ActivityDetailsResponse) -> None:
    """Cache activity details."""
    _activity_details_cache[activity_id] = (time.time(), data)


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


def _is_running_activity(activity_type: str) -> bool:
    """Check if activity is running-based (uses pace) vs cycling (uses speed)."""
    running_types = {
        "running", "trail_running", "treadmill_running", "track_running",
        "ultra_run", "walking", "hiking"
    }
    return activity_type.lower() in running_types


def _parse_garmin_time_series(
    details_data: Dict[str, Any],
    is_running: bool
) -> ActivityTimeSeries:
    """
    Parse Garmin activity details into time series data.

    Garmin returns data in 'metricsDescriptors' and 'activityDetailMetrics' format.
    """
    time_series = ActivityTimeSeries()

    if not details_data:
        return time_series

    # Get metrics descriptors to understand data positions
    descriptors = details_data.get("metricDescriptors", [])
    metrics_data = details_data.get("activityDetailMetrics", [])

    if not descriptors or not metrics_data:
        return time_series

    # Build index map for metric positions
    metric_indices = {}
    for i, desc in enumerate(descriptors):
        key = desc.get("key", "")
        metric_indices[key] = i

    # Process each data point
    for point in metrics_data:
        metrics = point.get("metrics", [])
        if not metrics:
            continue

        # Get timestamp (usually first metric or from 'startTimeGMT')
        timestamp_sec = 0
        if "startTimeGMT" in metric_indices and metric_indices["startTimeGMT"] < len(metrics):
            # Convert to relative seconds from start
            timestamp_sec = int(metrics[metric_indices["startTimeGMT"]] or 0)
        elif "sumElapsedDuration" in metric_indices and metric_indices["sumElapsedDuration"] < len(metrics):
            timestamp_sec = int(metrics[metric_indices["sumElapsedDuration"]] or 0)

        # Heart rate
        if "directHeartRate" in metric_indices:
            idx = metric_indices["directHeartRate"]
            if idx < len(metrics) and metrics[idx] is not None:
                hr_val = int(metrics[idx])
                if 30 < hr_val < 250:  # Sanity check
                    time_series.heart_rate.append(
                        HeartRatePoint(timestamp=timestamp_sec, hr=hr_val)
                    )

        # Speed (m/s from Garmin, convert appropriately)
        if "directSpeed" in metric_indices:
            idx = metric_indices["directSpeed"]
            if idx < len(metrics) and metrics[idx] is not None:
                speed_ms = float(metrics[idx])
                if speed_ms > 0:
                    if is_running:
                        # Convert m/s to sec/km (pace)
                        pace_sec_km = 1000 / speed_ms if speed_ms > 0 else 0
                        time_series.pace_or_speed.append(
                            PaceSpeedPoint(timestamp=timestamp_sec, value=round(pace_sec_km, 1))
                        )
                    else:
                        # Convert m/s to km/h (speed)
                        speed_kmh = speed_ms * 3.6
                        time_series.pace_or_speed.append(
                            PaceSpeedPoint(timestamp=timestamp_sec, value=round(speed_kmh, 2))
                        )

        # Elevation
        if "directElevation" in metric_indices:
            idx = metric_indices["directElevation"]
            if idx < len(metrics) and metrics[idx] is not None:
                elevation = float(metrics[idx])
                time_series.elevation.append(
                    ElevationPoint(timestamp=timestamp_sec, elevation=round(elevation, 1))
                )

        # Cadence
        cadence_key = "directRunCadence" if is_running else "directBikeCadence"
        if cadence_key in metric_indices:
            idx = metric_indices[cadence_key]
            if idx < len(metrics) and metrics[idx] is not None:
                cadence = int(metrics[idx])
                # For running, Garmin reports half cadence (one foot), double it
                if is_running:
                    cadence *= 2
                if cadence > 0:
                    time_series.cadence.append(
                        CadencePoint(timestamp=timestamp_sec, cadence=cadence)
                    )

    return time_series


def _parse_garmin_gps(details_data: Dict[str, Any]) -> List[GPSCoordinate]:
    """Extract GPS coordinates from Garmin activity details."""
    coordinates = []

    if not details_data:
        return coordinates

    # GPS data can be in different places depending on Garmin API version
    # Check geoPolylineDTO first
    geo_polyline = details_data.get("geoPolylineDTO", {})
    if geo_polyline:
        polyline = geo_polyline.get("polyline", [])
        for point in polyline:
            if not point:
                continue
            # Point can be a dict with lat/lon keys or a list/tuple
            if isinstance(point, dict):
                lat = point.get("lat")
                lon = point.get("lon")
            elif isinstance(point, (list, tuple)) and len(point) >= 2:
                lat, lon = point[0], point[1]
            else:
                continue
            if lat is not None and lon is not None:
                coordinates.append(GPSCoordinate(lat=lat, lon=lon))
        return coordinates

    # Alternative: look in activityDetailMetrics
    descriptors = details_data.get("metricDescriptors", [])
    metrics_data = details_data.get("activityDetailMetrics", [])

    lat_idx = None
    lon_idx = None
    for i, desc in enumerate(descriptors):
        key = desc.get("key", "")
        if key == "directLatitude":
            lat_idx = i
        elif key == "directLongitude":
            lon_idx = i

    if lat_idx is not None and lon_idx is not None:
        for point in metrics_data:
            metrics = point.get("metrics", [])
            if lat_idx < len(metrics) and lon_idx < len(metrics):
                lat = metrics[lat_idx]
                lon = metrics[lon_idx]
                if lat is not None and lon is not None:
                    coordinates.append(GPSCoordinate(lat=lat, lon=lon))

    return coordinates


def _parse_garmin_splits(
    splits_data: Dict[str, Any],
    is_running: bool
) -> List[SplitData]:
    """Parse Garmin splits data."""
    splits = []

    if not splits_data:
        return splits

    # Get lap splits
    lap_splits = splits_data.get("lapDTOs", [])
    if not lap_splits:
        # Try alternative key
        lap_splits = splits_data.get("splits", [])

    for i, lap in enumerate(lap_splits):
        distance = lap.get("distance", 0) or 0  # meters
        duration = lap.get("duration", 0) or 0  # seconds (can be float)

        split = SplitData(
            split_number=i + 1,
            distance_m=distance,
            duration_sec=duration,
            avg_hr=lap.get("averageHR"),
            max_hr=lap.get("maxHR"),
            elevation_gain_m=lap.get("elevationGain"),
            elevation_loss_m=lap.get("elevationLoss"),
            avg_cadence=lap.get("averageRunningCadenceInStepsPerMinute") if is_running
                        else lap.get("averageBikingCadenceInRevPerMinute"),
        )

        # Calculate pace or speed
        if distance > 0 and duration > 0:
            if is_running:
                # Pace in sec/km
                pace_sec_km = (duration / distance) * 1000
                split.avg_pace_sec_km = round(pace_sec_km, 1)
            else:
                # Speed in km/h
                speed_kmh = (distance / 1000) / (duration / 3600)
                split.avg_speed_kmh = round(speed_kmh, 2)

        splits.append(split)

    return splits


async def _fetch_garmin_activity_details(
    activity_id: str,
) -> Optional[ActivityDetailsResponse]:
    """
    Fetch detailed activity data from Garmin Connect.

    Uses garminconnect library to fetch:
    - Activity summary
    - Activity details (time series data)
    - Activity splits
    """
    try:
        from garminconnect import Garmin
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="garminconnect library not installed. Run: pip install garminconnect"
        )

    # Get Garmin credentials from settings
    from ...config import get_settings
    settings = get_settings()
    email = settings.garmin_email
    password = settings.garmin_password

    if not email or not password:
        raise HTTPException(
            status_code=400,
            detail="Garmin credentials not configured. Set GARMIN_EMAIL and GARMIN_PASSWORD in .env file."
        )

    try:
        import garth
        from pathlib import Path
        import logging
        logger = logging.getLogger(__name__)

        # Try to use existing garth session
        token_dir = Path.home() / ".garmin_tokens"
        garth_error = None
        use_garth = False

        try:
            if token_dir.exists():
                logger.info(f"Found token dir: {token_dir}")
                garth.resume(token_dir)
                logger.info("Garth session resumed")
                # Verify session is still valid
                profile = garth.connectapi("/userprofile-service/socialProfile")
                logger.info(f"Garth session valid: {profile.get('displayName', 'OK')}")
                use_garth = True
            else:
                garth_error = "No token directory found"
                logger.warning(garth_error)
        except Exception as e:
            garth_error = f"{type(e).__name__}: {str(e)}"
            logger.warning(f"Garth session failed: {garth_error}")

        if use_garth:
            # Fetch activity summary
            summary = garth.connectapi(f"/activity-service/activity/{activity_id}")

            # Fetch activity details (time series)
            details = garth.connectapi(
                f"/activity-service/activity/{activity_id}/details",
                params={"maxChartSize": 2000, "maxPolylineSize": 4000}
            )

            # Fetch splits
            try:
                splits = garth.connectapi(f"/activity-service/activity/{activity_id}/splits")
            except Exception:
                splits = {}  # Splits not available for all activities

        else:
            # Fall back to garminconnect library
            try:
                client = Garmin(email, password)
                client.login()

                # Fetch activity summary
                summary = client.get_activity(activity_id)

                # Fetch activity details
                details = client.get_activity_details(activity_id, maxchart=2000, maxpoly=4000)

                # Fetch splits
                try:
                    splits = client.get_activity_splits(activity_id)
                except Exception:
                    splits = {}
            except Exception as login_error:
                raise HTTPException(
                    status_code=401,
                    detail=f"Garmin authentication failed. Garth error: {garth_error}. Login error: {str(login_error)}"
                )

        if not summary:
            return None

        # Determine activity type (Garmin uses activityTypeDTO or activityType)
        activity_type_dto = summary.get("activityTypeDTO") or summary.get("activityType") or {}
        activity_type = activity_type_dto.get("typeKey", "running") if isinstance(activity_type_dto, dict) else "running"
        is_running = _is_running_activity(activity_type)

        # Get summary data (Garmin API returns data in summaryDTO)
        summary_dto = summary.get("summaryDTO", {})

        # Build basic info - prefer summaryDTO values, fall back to top-level
        duration_sec = int(summary_dto.get("duration") or summary.get("duration") or 0)
        distance_m = summary_dto.get("distance") or summary.get("distance")
        start_time = summary_dto.get("startTimeLocal") or summary.get("startTimeLocal")

        # Get sport type
        sport_type_dto = summary.get("sportTypeDTO") or summary.get("sportType")
        sport_type = sport_type_dto.get("typeKey") if isinstance(sport_type_dto, dict) else None

        basic_info = BasicActivityInfo(
            activity_id=str(activity_id),
            name=summary.get("activityName", "Unnamed Activity"),
            activity_type=activity_type,
            sport_type=sport_type,
            date=start_time[:10] if start_time else "",
            start_time=start_time,
            duration_sec=duration_sec,
            distance_m=distance_m,
            avg_hr=summary_dto.get("averageHR") or summary.get("averageHR"),
            max_hr=summary_dto.get("maxHR") or summary.get("maxHR"),
            elevation_gain_m=summary_dto.get("elevationGain") or summary.get("elevationGain"),
            calories=summary_dto.get("calories") or summary.get("calories"),
            training_effect=summary.get("aerobicTrainingEffect"),
        )

        # Calculate pace/speed
        if distance_m and duration_sec > 0:
            if is_running:
                pace_sec_km = (duration_sec / distance_m) * 1000
                basic_info.avg_pace_sec_km = round(pace_sec_km, 1)
            else:
                speed_kmh = (distance_m / 1000) / (duration_sec / 3600)
                basic_info.avg_speed_kmh = round(speed_kmh, 2)

        # Parse time series
        time_series = _parse_garmin_time_series(details, is_running)

        # Parse GPS coordinates
        gps_coordinates = _parse_garmin_gps(details)

        # Parse splits
        split_data = _parse_garmin_splits(splits, is_running)

        return ActivityDetailsResponse(
            basic_info=basic_info,
            time_series=time_series,
            gps_coordinates=gps_coordinates,
            splits=split_data,
            is_running=is_running,
            data_source="garmin",
            cached=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Garmin fetch error: {type(e).__name__}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch activity details from Garmin: {type(e).__name__}: {str(e)}"
        )


# ============================================================================
# API Routes
# ============================================================================

@router.post("/design", response_model=StructuredWorkoutResponse)
async def design_workout(
    request: DesignWorkoutRequest,
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
    workout_repo: WorkoutRepository = Depends(get_workout_repository),
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

        # Store the workout in the database
        workout_repo.save(workout)

        # Return response
        return StructuredWorkoutResponse.from_structured_workout(workout)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to design workout: {str(e)}")


# IMPORTANT: More specific routes must come BEFORE catch-all routes
# The /{activity_id}/details route must be defined before /{workout_id}

@router.get("/{activity_id}/details", response_model=ActivityDetailsResponse)
async def get_activity_details(
    activity_id: str,
    force_refresh: bool = False,
    training_db = Depends(get_training_db),
):
    """
    Get detailed activity data including time series, GPS, and splits.

    Fetches comprehensive activity data from Garmin Connect:

    **Returns:**
    - **basic_info**: Activity summary (name, type, duration, distance, avg HR, etc.)
    - **time_series**: Time-based data streams:
      - heart_rate: Heart rate over time [(timestamp, hr), ...]
      - pace_or_speed: Pace (sec/km for running) or speed (km/h for cycling)
      - elevation: Elevation profile [(timestamp, elevation), ...]
      - cadence: Steps/min (running) or RPM (cycling)
    - **gps_coordinates**: Route data for mapping [(lat, lon), ...]
    - **splits**: Per-km or per-lap metrics with avg HR, pace/speed, elevation

    **Sport-specific handling:**
    - Running activities: Returns pace in sec/km
    - Cycling activities: Returns speed in km/h

    **Caching:**
    - Results are cached for 1 hour to reduce Garmin API calls
    - Use `force_refresh=true` to bypass cache

    **Requirements:**
    - GARMIN_EMAIL and GARMIN_PASSWORD environment variables must be set
    - Or existing Garmin session tokens in ~/.garmin_tokens
    """
    # Check cache first (unless force refresh)
    if not force_refresh:
        cached = _get_cached_details(activity_id)
        if cached:
            return cached

    # First, check if we have basic info in our database
    local_activity = training_db.get_activity_metrics(activity_id)

    # Fetch detailed data from Garmin
    details = await _fetch_garmin_activity_details(activity_id)

    if not details:
        # If we have local data, return minimal response
        if local_activity:
            is_running = _is_running_activity(local_activity.activity_type or "running")
            duration_sec = int((local_activity.duration_min or 0) * 60)
            distance_m = (local_activity.distance_km or 0) * 1000

            basic_info = BasicActivityInfo(
                activity_id=activity_id,
                name=local_activity.activity_name or "Unknown Activity",
                activity_type=local_activity.activity_type or "running",
                sport_type=local_activity.sport_type,
                date=local_activity.date,
                duration_sec=duration_sec,
                distance_m=distance_m,
                avg_hr=local_activity.avg_hr,
                max_hr=local_activity.max_hr,
                avg_pace_sec_km=local_activity.pace_sec_per_km if is_running else None,
                avg_speed_kmh=local_activity.avg_speed_kmh if not is_running else None,
                elevation_gain_m=local_activity.elevation_gain_m,
            )

            return ActivityDetailsResponse(
                basic_info=basic_info,
                time_series=ActivityTimeSeries(),
                gps_coordinates=[],
                splits=[],
                is_running=is_running,
                data_source="local_cache",
                cached=False,
            )

        raise HTTPException(
            status_code=404,
            detail=f"Activity {activity_id} not found"
        )

    # Cache the result
    _set_cached_details(activity_id, details)

    return details


@router.get("/{workout_id}")
async def get_workout(
    workout_id: str,
    workout_repo: WorkoutRepository = Depends(get_workout_repository),
    training_db = Depends(get_training_db),
):
    """
    Get a specific workout by ID.

    This endpoint handles both:
    1. Designed workouts (from the workouts table)
    2. Synced activities from Garmin (from the activity_metrics table)

    Returns the appropriate response format based on the workout type found.
    """
    # First, try to find it as a designed workout
    workout = workout_repo.get(workout_id)
    if workout:
        return StructuredWorkoutResponse.from_structured_workout(workout)

    # If not found, try to find it as a synced activity
    activity = training_db.get_activity_metrics(workout_id)
    if activity:
        duration_sec = int((activity.duration_min or 0) * 60)
        distance_m = (activity.distance_km or 0) * 1000

        return ActivityResponse(
            id=activity.activity_id,
            type=activity.activity_type or "other",
            name=activity.activity_name or f"{activity.activity_type} workout",
            date=activity.date,
            startTime=f"{activity.date}T08:00:00",
            endTime=f"{activity.date}T09:00:00",
            duration=duration_sec,
            distance=distance_m,
            metrics={
                "avgHeartRate": activity.avg_hr,
                "maxHeartRate": activity.max_hr,
                "avgPace": activity.pace_sec_per_km,
            },
            source="garmin",
        )

    # Neither found
    raise HTTPException(status_code=404, detail=f"Workout {workout_id} not found")


class ActivityResponse(BaseModel):
    """API response model for a synced activity."""
    id: str
    userId: str = "default"
    type: str
    name: str
    date: str
    startTime: str
    endTime: str
    duration: int  # seconds
    distance: Optional[float] = None  # meters
    metrics: Dict = Field(default_factory=dict)
    source: str = "garmin"


@router.get("/", response_model=List[ActivityResponse])
async def list_workouts(
    limit: int = 20,
    offset: int = 0,
    training_db = Depends(get_training_db),
):
    """
    List synced activities from Garmin.

    Returns activities ordered by date (newest first).
    """
    from datetime import timedelta
    # Get activities from the last 90 days
    end_date = date.today()
    start_date = end_date - timedelta(days=90)
    activities = training_db.get_activities_range(
        start_date.isoformat(),
        end_date.isoformat()
    )

    result = []
    for act in activities[:limit]:
        duration_sec = int((act.duration_min or 0) * 60)
        distance_m = (act.distance_km or 0) * 1000

        result.append(ActivityResponse(
            id=act.activity_id,
            type=act.activity_type or "other",
            name=act.activity_name or f"{act.activity_type} workout",
            date=act.date,
            startTime=f"{act.date}T08:00:00",
            endTime=f"{act.date}T09:00:00",
            duration=duration_sec,
            distance=distance_m,
            metrics={
                "avgHeartRate": act.avg_hr,
                "maxHeartRate": act.max_hr,
                "avgPace": act.pace_sec_per_km,
            },
            source="garmin",
        ))

    return result


@router.delete("/{workout_id}")
async def delete_workout(
    workout_id: str,
    workout_repo: WorkoutRepository = Depends(get_workout_repository),
):
    """Delete a workout from storage."""
    if not workout_repo.exists(workout_id):
        raise HTTPException(status_code=404, detail=f"Workout {workout_id} not found")

    workout_repo.delete(workout_id)
    return {"message": f"Workout {workout_id} deleted"}


@router.get("/{workout_id}/fit")
async def download_fit(
    workout_id: str,
    background_tasks: BackgroundTasks,
    workout_repo: WorkoutRepository = Depends(get_workout_repository),
):
    """
    Download workout as Garmin FIT file.

    The FIT file can be:
    1. Transferred to Garmin device via USB (copy to /Garmin/NewFiles/)
    2. Imported to Garmin Connect web/app
    3. Synced via Garmin Express

    Returns a downloadable .fit file.
    """
    workout = workout_repo.get(workout_id)
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
async def get_fit_bytes(
    workout_id: str,
    workout_repo: WorkoutRepository = Depends(get_workout_repository),
):
    """
    Get workout as FIT file bytes (base64 encoded).

    Useful for programmatic access without file download.
    """
    import base64

    workout = workout_repo.get(workout_id)
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
    workout_repo: WorkoutRepository = Depends(get_workout_repository),
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
    workout = workout_repo.get(workout_id)
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
    workout_repo: WorkoutRepository = Depends(get_workout_repository),
):
    """Quick endpoint to generate an easy run workout."""
    request = DesignWorkoutRequest(workout_type="easy", duration_min=duration_min)
    return await design_workout(request, coach_service, training_db, workout_repo)


@router.post("/quick/tempo", response_model=StructuredWorkoutResponse)
async def quick_tempo_run(
    duration_min: int = 50,
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
    workout_repo: WorkoutRepository = Depends(get_workout_repository),
):
    """Quick endpoint to generate a tempo run workout."""
    request = DesignWorkoutRequest(workout_type="tempo", duration_min=duration_min)
    return await design_workout(request, coach_service, training_db, workout_repo)


@router.post("/quick/intervals", response_model=StructuredWorkoutResponse)
async def quick_intervals(
    duration_min: int = 55,
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
    workout_repo: WorkoutRepository = Depends(get_workout_repository),
):
    """Quick endpoint to generate an interval workout."""
    request = DesignWorkoutRequest(workout_type="intervals", duration_min=duration_min)
    return await design_workout(request, coach_service, training_db, workout_repo)


@router.post("/quick/long", response_model=StructuredWorkoutResponse)
async def quick_long_run(
    duration_min: int = 90,
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
    workout_repo: WorkoutRepository = Depends(get_workout_repository),
):
    """Quick endpoint to generate a long run workout."""
    request = DesignWorkoutRequest(workout_type="long", duration_min=duration_min)
    return await design_workout(request, coach_service, training_db, workout_repo)
