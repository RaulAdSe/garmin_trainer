"""Garmin Connect sync API routes."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum
import uuid
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr

from ..deps import get_training_db
from ...db.database import TrainingDatabase, ActivityMetrics, GarminFitnessData
from ...metrics.load import calculate_hrss, calculate_trimp


router = APIRouter()


# ============ Async Job Infrastructure ============

class SyncJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SyncJob:
    """In-memory sync job tracker."""
    def __init__(self, job_id: str, days: int):
        self.job_id = job_id
        self.status = SyncJobStatus.PENDING
        self.days = days
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.progress_percent = 0
        self.current_step = "Starting..."
        self.activities_synced = 0
        self.fitness_days_synced = 0
        self.error: Optional[str] = None
        self.result: Optional[Dict[str, Any]] = None


# In-memory job store (jobs expire after 1 hour)
_sync_jobs: Dict[str, SyncJob] = {}


def _cleanup_old_jobs():
    """Remove jobs older than 1 hour."""
    cutoff = datetime.now() - timedelta(hours=1)
    expired = [jid for jid, job in _sync_jobs.items() if job.created_at < cutoff]
    for jid in expired:
        del _sync_jobs[jid]


class SyncJobResponse(BaseModel):
    """Response for sync job status."""
    job_id: str
    status: str
    progress_percent: int = 0
    current_step: str = ""
    activities_synced: int = 0
    fitness_days_synced: int = 0
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class AsyncSyncResponse(BaseModel):
    """Response when starting async sync."""
    job_id: str
    status: str
    message: str


class GarminSyncRequest(BaseModel):
    """Request to sync activities from Garmin Connect."""
    email: EmailStr = Field(..., description="Garmin Connect email")
    password: str = Field(..., min_length=1, description="Garmin Connect password")
    days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Number of days to sync (1-365)"
    )


class GarminSyncResponse(BaseModel):
    """Response from Garmin sync operation."""
    success: bool
    synced_count: int
    message: str
    new_activities: int = 0
    updated_activities: int = 0


class SyncedActivity(BaseModel):
    """Brief summary of a synced activity."""
    id: str
    name: str
    type: str
    date: str
    distance_km: Optional[float] = None
    duration_min: Optional[float] = None


class GarminSyncDetailedResponse(GarminSyncResponse):
    """Detailed response including synced activities."""
    activities: list[SyncedActivity] = []


def _map_garmin_activity_type(garmin_type: str) -> str:
    """Map Garmin activity type to our internal type.

    We preserve specific sport types for better icon/emoji display,
    while mapping variations to a canonical form.
    """
    type_map = {
        # Running variants
        "running": "running",
        "treadmill_running": "running",
        "track_running": "running",
        "trail_running": "trail_running",
        "ultra_run": "trail_running",

        # Cycling variants
        "cycling": "cycling",
        "indoor_cycling": "cycling",
        "virtual_ride": "cycling",
        "mountain_biking": "cycling",
        "gravel_cycling": "cycling",
        "road_biking": "cycling",
        "e_bike": "cycling",

        # Swimming variants
        "swimming": "swimming",
        "pool_swimming": "swimming",
        "open_water_swimming": "swimming",
        "lap_swimming": "swimming",

        # Walking/Hiking
        "walking": "walking",
        "hiking": "hiking",
        "casual_walking": "walking",

        # Strength/Gym
        "strength_training": "strength",
        "fitness_equipment": "strength",
        "weightlifting": "strength",

        # Mind/Body
        "yoga": "yoga",
        "pilates": "yoga",
        "breathwork": "yoga",
        "meditation": "yoga",

        # High Intensity
        "hiit": "hiit",
        "cardio": "hiit",
        "circuit_training": "hiit",
        "bootcamp": "hiit",

        # Winter Sports
        "resort_skiing": "skiing",
        "resort_snowboarding": "skiing",
        "backcountry_skiing": "skiing",
        "backcountry_snowboarding": "skiing",
        "cross_country_skiing": "skiing",
        "skate_skiing": "skiing",
        "alpine_skiing": "skiing",
        "snowboarding": "skiing",
        "skiing": "skiing",
        "snowshoeing": "skiing",

        # Ball Sports
        "soccer": "football",
        "football": "football",
        "american_football": "football",
        "tennis": "tennis",
        "padel": "tennis",
        "pickleball": "tennis",
        "badminton": "tennis",
        "squash": "tennis",
        "racquetball": "tennis",
        "basketball": "basketball",
        "volleyball": "basketball",
        "handball": "basketball",
        "golf": "golf",

        # Water Sports
        "rowing": "rowing",
        "indoor_rowing": "rowing",
        "kayaking": "rowing",
        "stand_up_paddleboarding": "rowing",
        "paddling": "rowing",
        "surfing": "surfing",
        "kiteboarding": "surfing",
        "windsurfing": "surfing",

        # Other Sports
        "elliptical": "elliptical",
        "stair_climbing": "elliptical",
        "climbing": "climbing",
        "bouldering": "climbing",
        "ice_climbing": "climbing",
        "martial_arts": "martial_arts",
        "boxing": "martial_arts",
        "kickboxing": "martial_arts",
        "skating": "skating",
        "ice_skating": "skating",
        "inline_skating": "skating",
        "skateboarding": "skating",
        "dance": "dance",
        "triathlon": "triathlon",
        "duathlon": "triathlon",
        "multisport": "triathlon",
    }
    return type_map.get(garmin_type.lower(), "other")


def _calculate_pace(distance_m: Optional[float], duration_sec: Optional[float]) -> Optional[float]:
    """Calculate pace in seconds per km."""
    if not distance_m or not duration_sec or distance_m <= 0:
        return None
    distance_km = distance_m / 1000
    return duration_sec / distance_km


@router.post("/sync", response_model=GarminSyncDetailedResponse)
async def sync_garmin(
    request: GarminSyncRequest,
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Sync activities from Garmin Connect.

    This endpoint connects to Garmin Connect using the provided credentials,
    fetches recent activities, and saves them to the local database.

    **Security Note:**
    - Credentials are only used for this request and are not stored
    - Use HTTPS in production to protect credentials in transit

    **Parameters:**
    - email: Your Garmin Connect email
    - password: Your Garmin Connect password
    - days: Number of days to sync (default: 30, max: 365)
    """
    import logging
    import traceback
    logger = logging.getLogger(__name__)

    try:
        return await _do_garmin_sync(request, training_db, logger)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unhandled error in sync_garmin: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Sync failed. Please try again later.")


async def _do_garmin_sync(request, training_db, logger):
    """Internal sync implementation."""
    import traceback

    try:
        from garminconnect import Garmin, GarminConnectAuthenticationError
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="garminconnect library not installed. Run: pip install garminconnect"
        )

    # Attempt login
    try:
        client = Garmin(request.email, request.password)
        client.login()
    except GarminConnectAuthenticationError as e:
        raise HTTPException(
            status_code=401,
            detail="Invalid Garmin Connect credentials. Please check your email and password."
        )
    except Exception as e:
        error_msg = str(e).lower()
        # Check if it's an auth error that wasn't caught as GarminConnectAuthenticationError
        if "401" in error_msg or "unauthorized" in error_msg or "login failed" in error_msg:
            raise HTTPException(
                status_code=401,
                detail="Garmin Connect authentication failed. Please check your credentials or try again later."
            )
        logger.error(f"Failed to connect to Garmin Connect: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to connect to Garmin Connect. Please try again later."
        )

    # Fetch activities with pagination (Garmin API limit is 1000 per request)
    BATCH_SIZE = 200  # Safe batch size well under the 1000 limit
    cutoff_date = datetime.now() - timedelta(days=request.days)
    activities = []
    start_index = 0

    try:
        while True:
            batch = client.get_activities(start_index, BATCH_SIZE)

            if not batch:
                # No more activities
                break

            # Check if we've gone past our date range
            last_activity = batch[-1]
            last_date_str = last_activity.get("startTimeLocal", "")
            if last_date_str:
                try:
                    last_date = datetime.fromisoformat(last_date_str.replace("Z", "+00:00"))
                    if last_date.replace(tzinfo=None) < cutoff_date:
                        # Add remaining activities that might be in range
                        activities.extend(batch)
                        break
                except ValueError:
                    pass

            activities.extend(batch)

            if len(batch) < BATCH_SIZE:
                # Got fewer than requested, no more activities
                break

            start_index += BATCH_SIZE

    except Exception as e:
        logger.error(f"Failed to fetch activities from Garmin: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch activities from Garmin. Please try again later."
        )

    new_count = 0
    updated_count = 0
    synced_activities = []

    for activity in activities:
        try:
            # Parse activity date
            activity_date_str = activity.get("startTimeLocal", "")
            if not activity_date_str:
                continue

            # Parse the datetime
            try:
                activity_datetime = datetime.fromisoformat(activity_date_str.replace("Z", "+00:00"))
            except ValueError:
                # Try alternative format
                try:
                    activity_datetime = datetime.strptime(activity_date_str[:19], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue

            # Skip if outside date range
            if activity_datetime.replace(tzinfo=None) < cutoff_date:
                continue

            # Extract activity data
            activity_id = str(activity.get("activityId", ""))
            if not activity_id:
                continue

            activity_name = activity.get("activityName", "Unnamed Activity")
            activity_type = activity.get("activityType", {}).get("typeKey", "other")
            mapped_type = _map_garmin_activity_type(activity_type)

            # Extract metrics
            distance_m = activity.get("distance")  # in meters
            duration_sec = activity.get("duration")  # in seconds
            avg_hr = activity.get("averageHR")
            max_hr = activity.get("maxHR")
            calories = activity.get("calories")
            elevation_gain = activity.get("elevationGain")
            avg_speed = activity.get("averageSpeed")  # m/s

            # Convert units
            distance_km = distance_m / 1000 if distance_m else None
            duration_min = duration_sec / 60 if duration_sec else None
            pace_sec_per_km = _calculate_pace(distance_m, duration_sec)
            avg_speed_kmh = avg_speed * 3.6 if avg_speed else None

            # Check if activity already exists
            existing = training_db.get_activity_metrics(activity_id)

            # Calculate HRSS and TRIMP if we have required data
            hrss = None
            trimp = None
            profile = training_db.get_user_profile()
            if avg_hr and duration_min and profile and profile.max_hr and profile.rest_hr:
                max_hr_for_calc = max_hr or profile.max_hr
                if profile.threshold_hr:
                    hrss = calculate_hrss(
                        duration_min=duration_min,
                        avg_hr=int(avg_hr),
                        threshold_hr=profile.threshold_hr,
                        max_hr=max_hr_for_calc,
                        rest_hr=profile.rest_hr,
                    )
                trimp = calculate_trimp(
                    duration_min=duration_min,
                    avg_hr=int(avg_hr),
                    rest_hr=profile.rest_hr,
                    max_hr=max_hr_for_calc,
                    gender=profile.gender or "male",
                )

            # Create activity metrics object
            metrics = ActivityMetrics(
                activity_id=activity_id,
                date=activity_datetime.strftime("%Y-%m-%d"),
                start_time=activity_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
                activity_type=mapped_type,
                activity_name=activity_name,
                hrss=hrss,
                trimp=trimp,
                avg_hr=int(avg_hr) if avg_hr else None,
                max_hr=int(max_hr) if max_hr else None,
                duration_min=duration_min,
                distance_km=distance_km,
                pace_sec_per_km=pace_sec_per_km,
                zone1_pct=None,
                zone2_pct=None,
                zone3_pct=None,
                zone4_pct=None,
                zone5_pct=None,
                sport_type=activity_type,
                avg_speed_kmh=avg_speed_kmh,
                elevation_gain_m=elevation_gain,
            )

            # Save to database
            training_db.save_activity_metrics(metrics)

            if existing:
                updated_count += 1
            else:
                new_count += 1

            # Add to synced activities list
            synced_activities.append(SyncedActivity(
                id=activity_id,
                name=activity_name,
                type=mapped_type,
                date=activity_datetime.strftime("%Y-%m-%d"),
                distance_km=round(distance_km, 2) if distance_km else None,
                duration_min=round(duration_min, 1) if duration_min else None,
            ))

        except Exception as e:
            # Log but don't fail on individual activity errors
            logger.warning(f"Error processing activity: {e}")
            continue

    total_synced = new_count + updated_count

    # Also sync fitness data (VO2max, etc.) using the same client session
    fitness_new = 0
    fitness_updated = 0
    try:
        logger.info(f"Starting fitness data sync for {request.days} days...")
        fitness_new, fitness_updated, _ = _sync_fitness_data_internal(
            client, training_db, request.days
        )
        logger.info(f"Fitness sync complete: {fitness_new} new, {fitness_updated} updated")
    except Exception as e:
        logger.warning(f"Failed to sync fitness data: {e}", exc_info=True)
        # Don't fail the whole sync if fitness sync fails

    try:
        fitness_msg = ""
        if fitness_new + fitness_updated > 0:
            fitness_msg = f", fitness data for {fitness_new + fitness_updated} days"

        return GarminSyncDetailedResponse(
            success=True,
            synced_count=total_synced,
            new_activities=new_count,
            updated_activities=updated_count,
            message=f"Successfully synced {total_synced} activities ({new_count} new, {updated_count} updated){fitness_msg}",
            activities=synced_activities[:50],  # Limit to 50 most recent
        )
    except Exception as e:
        logger.error(f"Error building sync response: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error building response. Please try again later.")


class RecalculateMetricsResponse(BaseModel):
    """Response from metrics recalculation."""
    success: bool
    activities_updated: int
    fitness_days_calculated: int
    message: str


@router.post("/recalculate-metrics", response_model=RecalculateMetricsResponse)
async def recalculate_metrics(
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Recalculate HRSS/TRIMP for all existing activities and update fitness metrics.

    This endpoint:
    1. Recalculates HRSS and TRIMP for all activities using current user profile
    2. Recalculates CTL, ATL, TSB, and ACWR from the updated load data
    """
    from ...services.enrichment import EnrichmentService

    profile = training_db.get_user_profile()
    if not profile or not profile.max_hr or not profile.rest_hr or not profile.threshold_hr:
        raise HTTPException(
            status_code=400,
            detail="User profile incomplete. Please set max_hr, rest_hr, and threshold_hr first."
        )

    # Get all activities
    activities = training_db.get_all_activity_metrics()
    updated_count = 0

    for activity in activities:
        if not activity.avg_hr or not activity.duration_min:
            continue

        max_hr_for_calc = activity.max_hr or profile.max_hr

        # Calculate HRSS
        hrss = calculate_hrss(
            duration_min=activity.duration_min,
            avg_hr=activity.avg_hr,
            threshold_hr=profile.threshold_hr,
            max_hr=max_hr_for_calc,
            rest_hr=profile.rest_hr,
        )

        # Calculate TRIMP
        trimp = calculate_trimp(
            duration_min=activity.duration_min,
            avg_hr=activity.avg_hr,
            rest_hr=profile.rest_hr,
            max_hr=max_hr_for_calc,
            gender=profile.gender or "male",
        )

        # Update the activity
        activity.hrss = hrss
        activity.trimp = trimp
        training_db.save_activity_metrics(activity)
        updated_count += 1

    # Recalculate fitness metrics
    enrichment_service = EnrichmentService(training_db=training_db)
    fitness_days = enrichment_service.calculate_fitness_from_activities(
        days=365,  # Calculate for full year
        load_metric="hrss",
    )

    return RecalculateMetricsResponse(
        success=True,
        activities_updated=updated_count,
        fitness_days_calculated=fitness_days,
        message=f"Updated {updated_count} activities with HRSS/TRIMP, recalculated {fitness_days} days of fitness metrics",
    )


# ============ Async Sync Endpoints ============

@router.post("/sync-async", response_model=AsyncSyncResponse)
async def sync_garmin_async(
    request: GarminSyncRequest,
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Start an async Garmin sync and return a job ID for polling.

    Use /sync-status/{job_id} to poll for progress and completion.
    This prevents frontend timeouts on long syncs.
    """
    _cleanup_old_jobs()

    job_id = str(uuid.uuid4())
    job = SyncJob(job_id=job_id, days=request.days)
    _sync_jobs[job_id] = job

    # Start the sync in background
    asyncio.create_task(
        _do_garmin_sync_async(job, request, training_db)
    )

    return AsyncSyncResponse(
        job_id=job_id,
        status="pending",
        message=f"Sync started for {request.days} days. Poll /sync-status/{job_id} for progress.",
    )


@router.get("/sync-status/{job_id}", response_model=SyncJobResponse)
async def get_sync_status(job_id: str):
    """
    Get the status of an async sync job.

    Poll this endpoint every 1-2 seconds to track progress.
    """
    job = _sync_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    return SyncJobResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress_percent=job.progress_percent,
        current_step=job.current_step,
        activities_synced=job.activities_synced,
        fitness_days_synced=job.fitness_days_synced,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        error=job.error,
        result=job.result,
    )


async def _do_garmin_sync_async(job: SyncJob, request: GarminSyncRequest, training_db: TrainingDatabase):
    """Background task to perform the actual Garmin sync."""
    import logging
    import traceback
    logger = logging.getLogger(__name__)

    job.status = SyncJobStatus.RUNNING
    job.started_at = datetime.now()
    job.current_step = "Connecting to Garmin..."

    try:
        from garminconnect import Garmin, GarminConnectAuthenticationError
    except ImportError:
        job.status = SyncJobStatus.FAILED
        job.error = "garminconnect library not installed"
        job.completed_at = datetime.now()
        return

    try:
        # Login (blocking call - run in thread)
        job.current_step = "Connecting to Garmin..."
        job.progress_percent = 2
        await asyncio.sleep(0)  # Yield to allow polling to see progress

        client = Garmin(request.email, request.password)

        job.current_step = "Authenticating..."
        job.progress_percent = 5
        await asyncio.sleep(0)

        await asyncio.to_thread(client.login)

        job.current_step = "Logged in successfully"
        job.progress_percent = 10
        await asyncio.sleep(0)

        # Fetch activities (blocking call - run in thread)
        job.current_step = "Fetching activity list..."
        job.progress_percent = 12
        await asyncio.sleep(0)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=request.days)

        activities = await asyncio.to_thread(
            client.get_activities_by_date,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        )

        total_activities = len(activities) if activities else 0
        job.current_step = f"Found {total_activities} activities"
        job.progress_percent = 15
        await asyncio.sleep(0)

        # Process activities (15-75% range = 60% for activities)
        new_count = 0
        updated_count = 0
        profile = training_db.get_user_profile()

        for i, activity in enumerate(activities or []):
            # Update progress more smoothly (15-75% for activities)
            # Use (i+1) so progress updates after processing, not before
            progress = 15 + int(((i + 1) / max(total_activities, 1)) * 60)
            job.progress_percent = min(progress, 75)  # Cap at 75%
            job.current_step = f"Processing activity {i+1}/{total_activities}..."
            job.activities_synced = new_count + updated_count
            await asyncio.sleep(0)  # Yield to allow polling to see progress

            try:
                activity_id = str(activity.get("activityId"))
                activity_type = activity.get("activityType", {}).get("typeKey", "unknown")
                mapped_type = _map_garmin_activity_type(activity_type)

                # Get activity details
                start_time = activity.get("startTimeLocal")
                activity_datetime = datetime.fromisoformat(start_time.replace("Z", "+00:00")) if start_time else datetime.now()
                activity_name = activity.get("activityName", mapped_type.title())

                # Metrics
                avg_hr = activity.get("averageHR")
                max_hr = activity.get("maxHR")
                duration_sec = activity.get("duration")
                distance_m = activity.get("distance")
                elevation_gain = activity.get("elevationGain")
                avg_speed = activity.get("averageSpeed")

                # Convert units
                distance_km = distance_m / 1000 if distance_m else None
                duration_min = duration_sec / 60 if duration_sec else None
                pace_sec_per_km = _calculate_pace(distance_m, duration_sec)
                avg_speed_kmh = avg_speed * 3.6 if avg_speed else None

                # Check existing
                existing = training_db.get_activity_metrics(activity_id)

                # Calculate HRSS/TRIMP
                hrss = None
                trimp = None
                if avg_hr and duration_min and profile and profile.max_hr and profile.rest_hr:
                    max_hr_for_calc = max_hr or profile.max_hr
                    if profile.threshold_hr:
                        hrss = calculate_hrss(
                            duration_min=duration_min,
                            avg_hr=int(avg_hr),
                            threshold_hr=profile.threshold_hr,
                            max_hr=max_hr_for_calc,
                            rest_hr=profile.rest_hr,
                        )
                    trimp = calculate_trimp(
                        duration_min=duration_min,
                        avg_hr=int(avg_hr),
                        rest_hr=profile.rest_hr,
                        max_hr=max_hr_for_calc,
                        gender=profile.gender or "male",
                    )

                # Save
                metrics = ActivityMetrics(
                    activity_id=activity_id,
                    date=activity_datetime.strftime("%Y-%m-%d"),
                    activity_type=mapped_type,
                    activity_name=activity_name,
                    hrss=hrss,
                    trimp=trimp,
                    avg_hr=int(avg_hr) if avg_hr else None,
                    max_hr=int(max_hr) if max_hr else None,
                    duration_min=duration_min,
                    distance_km=distance_km,
                    pace_sec_per_km=pace_sec_per_km,
                    zone1_pct=None,  # Zone data not available from simple API
                    zone2_pct=None,
                    zone3_pct=None,
                    zone4_pct=None,
                    zone5_pct=None,
                    start_time=activity_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
                    sport_type=activity_type,
                    avg_speed_kmh=avg_speed_kmh,
                    elevation_gain_m=elevation_gain,
                )
                await asyncio.to_thread(training_db.save_activity_metrics, metrics)

                if existing:
                    updated_count += 1
                else:
                    new_count += 1

            except Exception as e:
                logger.warning(f"Error processing activity: {e}")
                continue

        job.activities_synced = new_count + updated_count

        # Sync fitness data (75-95%)
        job.current_step = "Fetching fitness metrics..."
        job.progress_percent = 78
        await asyncio.sleep(0)  # Yield to allow polling to see progress

        try:
            job.current_step = "Syncing VO2 Max data..."
            job.progress_percent = 82
            await asyncio.sleep(0)

            # Run fitness sync in thread (it uses blocking Garmin API calls)
            fitness_new, fitness_updated, _ = await asyncio.to_thread(
                _sync_fitness_data_internal,
                client, training_db, request.days
            )
            job.fitness_days_synced = fitness_new + fitness_updated

            job.current_step = "Fitness data synced"
            job.progress_percent = 95
            await asyncio.sleep(0)
        except Exception as e:
            logger.warning(f"Failed to sync fitness data: {e}")

        # Complete
        job.current_step = "Finishing up..."
        job.progress_percent = 98
        await asyncio.sleep(0)

        job.progress_percent = 100
        job.current_step = "Sync complete!"
        job.status = SyncJobStatus.COMPLETED
        job.completed_at = datetime.now()
        job.result = {
            "synced_count": new_count + updated_count,
            "new_activities": new_count,
            "updated_activities": updated_count,
            "fitness_days": job.fitness_days_synced,
        }

    except GarminConnectAuthenticationError:
        job.status = SyncJobStatus.FAILED
        job.error = "Invalid Garmin Connect credentials"
        job.completed_at = datetime.now()
    except Exception as e:
        logger.error(f"Async sync failed: {e}")
        logger.error(traceback.format_exc())
        job.status = SyncJobStatus.FAILED
        job.error = str(e)
        job.completed_at = datetime.now()


class BackfillStartTimeResponse(BaseModel):
    """Response from start_time backfill operation."""
    success: bool
    updated_count: int
    message: str


@router.post("/backfill-start-time", response_model=BackfillStartTimeResponse)
async def backfill_start_time(
    request: GarminSyncRequest,
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Backfill start_time for existing activities by re-fetching from Garmin.

    This endpoint fetches activities from Garmin and updates the start_time
    field for activities that already exist in the database.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from garminconnect import Garmin, GarminConnectAuthenticationError
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="garminconnect library not installed"
        )

    # Authenticate with Garmin
    try:
        client = Garmin(request.email, request.password)
        client.login()
    except GarminConnectAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Garmin Connect credentials"
        )
    except Exception as e:
        logger.error(f"Failed to connect to Garmin: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to connect to Garmin. Please try again later."
        )

    # Fetch activities
    BATCH_SIZE = 100
    cutoff_date = datetime.now() - timedelta(days=request.days)
    activities = []
    start_index = 0

    try:
        while True:
            batch = client.get_activities(start_index, BATCH_SIZE)
            if not batch:
                break

            last_activity = batch[-1]
            last_date_str = last_activity.get("startTimeLocal", "")
            if last_date_str:
                try:
                    last_date = datetime.fromisoformat(last_date_str.replace("Z", "+00:00"))
                    if last_date.replace(tzinfo=None) < cutoff_date:
                        activities.extend(batch)
                        break
                except ValueError:
                    pass

            activities.extend(batch)

            if len(batch) < BATCH_SIZE:
                break

            start_index += BATCH_SIZE
    except Exception as e:
        logger.error(f"Failed to fetch activities from Garmin: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch activities from Garmin. Please try again later."
        )

    # Update start_time for existing activities
    updated_count = 0

    with training_db._get_connection() as conn:
        for activity in activities:
            try:
                activity_id = str(activity.get("activityId", ""))
                activity_date_str = activity.get("startTimeLocal", "")

                if not activity_id or not activity_date_str:
                    continue

                # Parse the datetime
                try:
                    activity_datetime = datetime.fromisoformat(activity_date_str.replace("Z", "+00:00"))
                except ValueError:
                    try:
                        activity_datetime = datetime.strptime(activity_date_str[:19], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        continue

                start_time = activity_datetime.strftime("%Y-%m-%dT%H:%M:%S")

                # Update only the start_time field
                cursor = conn.execute(
                    "UPDATE activity_metrics SET start_time = ? WHERE activity_id = ?",
                    (start_time, activity_id)
                )

                if cursor.rowcount > 0:
                    updated_count += 1

            except Exception as e:
                logger.warning(f"Error updating activity {activity.get('activityId')}: {e}")
                continue

        conn.commit()

    return BackfillStartTimeResponse(
        success=True,
        updated_count=updated_count,
        message=f"Updated start_time for {updated_count} activities"
    )


class SyncedWellnessDay(BaseModel):
    """Summary of a synced wellness day."""
    date: str
    has_sleep: bool = False
    has_hrv: bool = False
    has_stress: bool = False
    has_activity: bool = False


class WellnessSyncResponse(BaseModel):
    """Response from wellness sync operation."""
    success: bool
    synced_count: int
    message: str
    new_days: int = 0
    updated_days: int = 0
    synced_days: list[SyncedWellnessDay] = []


@router.post("/sync-wellness", response_model=WellnessSyncResponse)
async def sync_wellness(request: GarminSyncRequest):
    """
    Sync wellness data from Garmin Connect.

    Syncs sleep, HRV, stress/body battery, and daily activity data
    to the wellness.db database for the whoop-dashboard.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from garminconnect import Garmin, GarminConnectAuthenticationError
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="garminconnect library not installed"
        )

    # Login
    try:
        client = Garmin(request.email, request.password)
        client.login()
    except GarminConnectAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Garmin Connect credentials"
        )
    except Exception as e:
        logger.error(f"Failed to connect to Garmin: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to connect. Please try again later."
        )

    # Get wellness.db path
    import sqlite3
    from pathlib import Path
    from ...config import PROJECT_ROOT

    wellness_db_path = PROJECT_ROOT / "whoop-dashboard" / "wellness.db"

    if not wellness_db_path.exists():
        raise HTTPException(
            status_code=500,
            detail="Wellness database not found. Please contact support."
        )

    conn = sqlite3.connect(str(wellness_db_path))
    cursor = conn.cursor()

    end_date = datetime.now().date()
    synced_days = []
    new_days = 0
    updated_days = 0
    processed_dates = set()

    # Sync sleep data
    for i in range(request.days):
        date = (end_date - timedelta(days=i)).isoformat()
        try:
            sleep = client.get_sleep_data(date)
            if sleep and sleep.get('dailySleepDTO'):
                dto = sleep['dailySleepDTO']

                # Check if exists
                cursor.execute('SELECT 1 FROM sleep_data WHERE date = ?', (date,))
                exists = cursor.fetchone()

                cursor.execute('''
                    INSERT OR REPLACE INTO sleep_data
                    (date, total_sleep_seconds, deep_sleep_seconds, light_sleep_seconds,
                     rem_sleep_seconds, awake_seconds, sleep_score, sleep_efficiency)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    date,
                    dto.get('sleepTimeSeconds'),
                    dto.get('deepSleepSeconds'),
                    dto.get('lightSleepSeconds'),
                    dto.get('remSleepSeconds'),
                    dto.get('awakeSleepSeconds'),
                    dto.get('sleepScores', {}).get('overall', {}).get('value'),
                    dto.get('sleepScores', {}).get('sleepEfficiency', {}).get('value'),
                ))

                if date not in processed_dates:
                    processed_dates.add(date)
                    if exists:
                        updated_days += 1
                    else:
                        new_days += 1
        except Exception:
            pass

    # Sync HRV data for all requested days
    for i in range(request.days):
        date = (end_date - timedelta(days=i)).isoformat()
        try:
            hrv = client.get_hrv_data(date)
            if hrv and hrv.get('hrvSummary'):
                summary = hrv['hrvSummary']
                cursor.execute('''
                    INSERT OR REPLACE INTO hrv_data
                    (date, hrv_last_night_avg, hrv_weekly_avg, hrv_status)
                    VALUES (?, ?, ?, ?)
                ''', (
                    date,
                    summary.get('lastNightAvg'),
                    summary.get('weeklyAvg'),
                    summary.get('status'),
                ))
        except Exception:
            pass

    # Sync stress/body battery data
    for i in range(min(request.days, 7)):
        date = (end_date - timedelta(days=i)).isoformat()
        try:
            stress = client.get_stress_data(date)
            if stress:
                cursor.execute('''
                    INSERT OR REPLACE INTO stress_data
                    (date, avg_stress_level, max_stress_level,
                     body_battery_charged, body_battery_drained)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    date,
                    stress.get('avgStressLevel'),
                    stress.get('maxStressLevel'),
                    stress.get('bodyBatteryChargedValue'),
                    stress.get('bodyBatteryDrainedValue'),
                ))
        except Exception:
            pass

    # Sync daily activity stats and RHR
    for i in range(request.days):
        date = (end_date - timedelta(days=i)).isoformat()
        fetched_at = datetime.now().isoformat()
        resting_hr = None

        # First try to get RHR from heart rate data (more reliable)
        try:
            hr_data = client.get_heart_rates(date)
            if hr_data:
                resting_hr = hr_data.get('restingHeartRate')
        except Exception:
            pass

        try:
            stats = client.get_stats(date)
            if stats:
                cursor.execute('''
                    INSERT OR REPLACE INTO activity_data
                    (date, steps, steps_goal, intensity_minutes, floors_climbed, active_calories, total_calories)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    date,
                    stats.get('totalSteps'),
                    stats.get('dailyStepGoal'),
                    (stats.get('moderateIntensityMinutes') or 0) + (stats.get('vigorousIntensityMinutes') or 0),
                    stats.get('floorsAscended'),
                    stats.get('activeKilocalories'),
                    stats.get('totalKilocalories'),
                ))

                # Fallback to stats RHR if heart rate API didn't provide it
                if resting_hr is None:
                    resting_hr = stats.get('restingHeartRate')
        except Exception:
            pass

        # Save daily_wellness OUTSIDE the if stats: block
        # This ensures RHR from get_heart_rates() is saved even if get_stats() fails
        if resting_hr is not None:
            try:
                cursor.execute('''
                    INSERT INTO daily_wellness (date, fetched_at, resting_heart_rate)
                    VALUES (?, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET
                        fetched_at = excluded.fetched_at,
                        resting_heart_rate = COALESCE(excluded.resting_heart_rate, resting_heart_rate)
                ''', (
                    date,
                    fetched_at,
                    resting_hr,
                ))
            except Exception:
                pass

    conn.commit()
    conn.close()

    # Build synced days list
    for date in list(processed_dates)[:10]:
        synced_days.append(SyncedWellnessDay(
            date=date,
            has_sleep=True,
            has_hrv=True,
            has_stress=True,
            has_activity=True,
        ))

    total = new_days + updated_days
    return WellnessSyncResponse(
        success=True,
        synced_count=total,
        message=f"Successfully synced {total} days ({new_days} new, {updated_days} updated)",
        new_days=new_days,
        updated_days=updated_days,
        synced_days=synced_days,
    )


@router.get("/status")
async def garmin_sync_status():
    """
    Get Garmin sync status and information.

    Returns information about the Garmin sync capability and requirements.
    """
    try:
        from garminconnect import Garmin
        library_available = True
    except ImportError:
        library_available = False

    return {
        "garmin_connect_available": library_available,
        "supported_activity_types": [
            "running", "cycling", "swimming", "walking", "strength", "yoga", "hiit"
        ],
        "max_sync_days": 365,
        "sync_endpoints": {
            "/sync": "Sync activities (workouts) from Garmin Connect",
            "/sync-wellness": "Sync wellness data (sleep, HRV, stress, body battery)",
            "/sync-fitness": "Sync fitness data (VO2max, race predictions, training status)",
        },
        "fitness_data_available": [
            "VO2max (running and cycling)",
            "Race predictions (5K, 10K, half marathon, marathon)",
            "Training status (productive, unproductive, peaking, etc.)",
            "Training readiness score and level",
            "Acute:Chronic Workload Ratio (ACWR)",
            "Fitness age",
        ],
        "notes": [
            "Credentials are only used for the sync request and are not stored",
            "Use HTTPS in production to protect credentials",
            "Rate limits may apply from Garmin's side",
            "Fitness data is stored historically (one record per day)",
        ],
    }


class WellnessDay(BaseModel):
    """Wellness data for a single day."""
    date: str
    resting_heart_rate: Optional[int] = None
    sleep_hours: Optional[float] = None
    sleep_score: Optional[int] = None
    deep_sleep_pct: Optional[float] = None
    rem_sleep_pct: Optional[float] = None
    hrv: Optional[int] = None
    hrv_status: Optional[str] = None
    body_battery_high: Optional[int] = None
    body_battery_low: Optional[int] = None
    body_battery_charged: Optional[int] = None
    body_battery_drained: Optional[int] = None
    avg_stress: Optional[int] = None
    steps: Optional[int] = None
    steps_goal: Optional[int] = None
    active_calories: Optional[int] = None
    intensity_minutes: Optional[int] = None


class WellnessHistoryResponse(BaseModel):
    """Response containing wellness history."""
    success: bool
    days: list[WellnessDay]
    total_days: int


@router.get("/wellness-history", response_model=WellnessHistoryResponse)
async def get_wellness_history(days: int = 14):
    """
    Get wellness history from the local database.

    Returns sleep, HRV, stress, and activity data for the requested number of days.
    """
    import sqlite3
    from pathlib import Path
    from ...config import PROJECT_ROOT

    wellness_db_path = PROJECT_ROOT / "whoop-dashboard" / "wellness.db"

    if not wellness_db_path.exists():
        return WellnessHistoryResponse(success=False, days=[], total_days=0)

    conn = sqlite3.connect(str(wellness_db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get combined wellness data
    cursor.execute('''
        SELECT
            dw.date,
            dw.resting_heart_rate,
            s.total_sleep_seconds,
            s.deep_sleep_seconds,
            s.light_sleep_seconds,
            s.rem_sleep_seconds,
            s.sleep_score,
            h.hrv_last_night_avg,
            h.hrv_status,
            st.avg_stress_level,
            st.body_battery_charged,
            st.body_battery_drained,
            st.body_battery_high,
            st.body_battery_low,
            a.steps,
            a.steps_goal,
            a.active_calories,
            a.intensity_minutes
        FROM daily_wellness dw
        LEFT JOIN sleep_data s ON dw.date = s.date
        LEFT JOIN hrv_data h ON dw.date = h.date
        LEFT JOIN stress_data st ON dw.date = st.date
        LEFT JOIN activity_data a ON dw.date = a.date
        ORDER BY dw.date DESC
        LIMIT ?
    ''', (days,))

    rows = cursor.fetchall()
    conn.close()

    wellness_days = []
    for row in rows:
        total_sleep = row['total_sleep_seconds'] or 0
        deep_sleep = row['deep_sleep_seconds'] or 0
        rem_sleep = row['rem_sleep_seconds'] or 0

        wellness_days.append(WellnessDay(
            date=row['date'],
            resting_heart_rate=row['resting_heart_rate'],
            sleep_hours=round(total_sleep / 3600, 2) if total_sleep else None,
            sleep_score=row['sleep_score'],
            deep_sleep_pct=round(deep_sleep / total_sleep * 100, 1) if total_sleep > 0 else None,
            rem_sleep_pct=round(rem_sleep / total_sleep * 100, 1) if total_sleep > 0 else None,
            hrv=row['hrv_last_night_avg'],
            hrv_status=row['hrv_status'],
            body_battery_high=row['body_battery_high'],
            body_battery_low=row['body_battery_low'],
            body_battery_charged=row['body_battery_charged'],
            body_battery_drained=row['body_battery_drained'],
            avg_stress=row['avg_stress_level'],
            steps=row['steps'],
            steps_goal=row['steps_goal'],
            active_calories=row['active_calories'],
            intensity_minutes=row['intensity_minutes'],
        ))

    return WellnessHistoryResponse(
        success=True,
        days=wellness_days,
        total_days=len(wellness_days),
    )


# === Fitness Data Sync (VO2max, Race Predictions, Training Status) ===


class SyncedFitnessDay(BaseModel):
    """Summary of synced fitness data for a day."""
    date: str
    vo2max_running: Optional[float] = None
    vo2max_cycling: Optional[float] = None
    fitness_age: Optional[int] = None
    training_status: Optional[str] = None
    training_readiness_score: Optional[int] = None
    has_race_predictions: bool = False


class FitnessSyncResponse(BaseModel):
    """Response from fitness data sync operation."""
    success: bool
    synced_count: int
    message: str
    new_days: int = 0
    updated_days: int = 0
    synced_days: list[SyncedFitnessDay] = []


def _sync_fitness_data_internal(client, training_db: TrainingDatabase, days: int) -> tuple:
    """
    Internal helper to sync fitness data from Garmin.
    Returns (new_days, updated_days, synced_days_list).
    """
    import logging
    logger = logging.getLogger(__name__)

    end_date = datetime.now().date()
    synced_days = []
    new_days = 0
    updated_days = 0

    for i in range(days):
        date = (end_date - timedelta(days=i)).isoformat()

        # Check if we already have data for this date
        existing = training_db.get_garmin_fitness_data(date)

        # Initialize data with defaults
        fitness_data = GarminFitnessData(date=date)

        # Fetch VO2max and fitness age from max metrics
        try:
            max_metrics = client.get_max_metrics(date)
            logger.debug(f"Fetched max_metrics for {date}")
            if max_metrics:
                if isinstance(max_metrics, list) and len(max_metrics) > 0:
                    metric = max_metrics[0]
                elif isinstance(max_metrics, dict):
                    metric = max_metrics
                else:
                    metric = None

                if metric:
                    # VO2 Max data is nested inside 'generic' key
                    generic = metric.get('generic') or {}
                    vo2_precise = generic.get('vo2MaxPreciseValue')
                    vo2_value = generic.get('vo2MaxValue')
                    fitness_data.vo2max_running = vo2_precise or vo2_value
                    logger.debug(f"Extracted VO2max for {date}: {fitness_data.vo2max_running}")

                    # Cycling VO2 max is in separate 'cycling' key
                    cycling = metric.get('cycling') or {}
                    cycling_vo2 = cycling.get('vo2MaxPreciseValue') or cycling.get('vo2MaxValue')
                    if cycling_vo2:
                        fitness_data.vo2max_cycling = cycling_vo2

                    fitness_data.fitness_age = generic.get('fitnessAge')
        except Exception as e:
            logger.warning(f"Error fetching max metrics for {date}: {e}")

        # Only save if we got at least some data
        has_data = fitness_data.vo2max_running is not None

        if has_data:
            training_db.save_garmin_fitness_data(fitness_data)

            if existing:
                updated_days += 1
            else:
                new_days += 1

            synced_days.append(SyncedFitnessDay(
                date=date,
                vo2max_running=fitness_data.vo2max_running,
                vo2max_cycling=fitness_data.vo2max_cycling,
                fitness_age=fitness_data.fitness_age,
                training_status=fitness_data.training_status,
                training_readiness_score=fitness_data.training_readiness_score,
                has_race_predictions=fitness_data.race_time_5k is not None,
            ))

    return new_days, updated_days, synced_days


class RacePrediction(BaseModel):
    """Race prediction times."""
    distance: str
    time_seconds: Optional[int] = None
    time_formatted: Optional[str] = None


class FitnessDataResponse(BaseModel):
    """Response containing fitness data for a date."""
    success: bool
    date: str
    vo2max_running: Optional[float] = None
    vo2max_cycling: Optional[float] = None
    fitness_age: Optional[int] = None
    race_predictions: list[RacePrediction] = []
    training_status: Optional[str] = None
    training_status_description: Optional[str] = None
    fitness_trend: Optional[str] = None
    training_readiness_score: Optional[int] = None
    training_readiness_level: Optional[str] = None
    acwr_percent: Optional[float] = None
    acwr_status: Optional[str] = None


def _format_race_time(seconds: Optional[int]) -> Optional[str]:
    """Format race time in seconds to HH:MM:SS or MM:SS."""
    if seconds is None:
        return None
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


@router.post("/sync-fitness", response_model=FitnessSyncResponse)
async def sync_fitness(
    request: GarminSyncRequest,
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Sync fitness data from Garmin Connect.

    Syncs VO2max, race predictions, training status, and training readiness
    to the training database for historical tracking.

    **Data synced:**
    - VO2max (running and cycling if available)
    - Race predictions (5K, 10K, half marathon, marathon)
    - Training status (productive, unproductive, peaking, recovery, etc.)
    - Training readiness score and level
    - Acute:Chronic Workload Ratio (ACWR)

    **Note:** This stores one record per day to track how these metrics
    change over time.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from garminconnect import Garmin, GarminConnectAuthenticationError
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="garminconnect library not installed. Run: pip install garminconnect"
        )

    # Login
    try:
        client = Garmin(request.email, request.password)
        client.login()
    except GarminConnectAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Garmin Connect credentials"
        )
    except Exception as e:
        logger.error(f"Failed to connect to Garmin Connect: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to connect to Garmin Connect. Please try again later."
        )

    end_date = datetime.now().date()
    synced_days = []
    new_days = 0
    updated_days = 0

    for i in range(request.days):
        date = (end_date - timedelta(days=i)).isoformat()

        # Check if we already have data for this date
        existing = training_db.get_garmin_fitness_data(date)

        # Initialize data with defaults
        fitness_data = GarminFitnessData(date=date)

        # Fetch VO2max and fitness age from max metrics
        try:
            max_metrics = client.get_max_metrics(date)
            if max_metrics:
                # The API returns a list of metrics, find the most recent
                if isinstance(max_metrics, list) and len(max_metrics) > 0:
                    metric = max_metrics[0]
                elif isinstance(max_metrics, dict):
                    metric = max_metrics
                else:
                    metric = None

                if metric:
                    # Running VO2max - try precise value first
                    vo2_precise = metric.get('vo2MaxPreciseValue')
                    vo2_value = metric.get('vo2MaxValue')
                    fitness_data.vo2max_running = vo2_precise or vo2_value

                    # Cycling VO2max if available
                    cycling_vo2 = metric.get('cyclingVo2MaxPreciseValue') or metric.get('cyclingVo2MaxValue')
                    if cycling_vo2:
                        fitness_data.vo2max_cycling = cycling_vo2

                    # Fitness age
                    fitness_data.fitness_age = metric.get('fitnessAge')
        except Exception as e:
            logger.warning(f"Error fetching max metrics for {date}: {e}")

        # Fetch race predictions
        try:
            race_preds = client.get_race_predictions()
            if race_preds:
                # Race predictions might be returned as a list or dict
                if isinstance(race_preds, list) and len(race_preds) > 0:
                    # Find the prediction for this date or the most recent
                    pred = None
                    for p in race_preds:
                        if p.get('calendarDate') == date:
                            pred = p
                            break
                    if pred is None and len(race_preds) > 0:
                        # Use the most recent prediction for today only
                        if i == 0:
                            pred = race_preds[0]
                elif isinstance(race_preds, dict):
                    pred = race_preds
                else:
                    pred = None

                if pred:
                    fitness_data.race_time_5k = pred.get('time5K')
                    fitness_data.race_time_10k = pred.get('time10K')
                    fitness_data.race_time_half = pred.get('timeHalfMarathon')
                    fitness_data.race_time_marathon = pred.get('timeMarathon')
        except Exception as e:
            logger.warning(f"Error fetching race predictions for {date}: {e}")

        # Fetch training status
        try:
            training_status = client.get_training_status(date)
            if training_status:
                # Extract training status info
                most_recent = training_status.get('mostRecentTrainingStatus', {})
                if most_recent:
                    fitness_data.training_status = most_recent.get('trainingStatus')
                    fitness_data.training_status_description = most_recent.get('trainingStatusDescription')
                    fitness_data.fitness_trend = most_recent.get('fitnessTrend')

                # Extract ACWR from acute training load
                acute_load = training_status.get('acuteTrainingLoadDTO', {})
                if acute_load:
                    fitness_data.acwr_percent = acute_load.get('acwrPercent')
                    fitness_data.acwr_status = acute_load.get('acwrStatus')
        except Exception as e:
            logger.warning(f"Error fetching training status for {date}: {e}")

        # Fetch training readiness
        try:
            readiness = client.get_training_readiness(date)
            if readiness:
                fitness_data.training_readiness_score = readiness.get('score')
                fitness_data.training_readiness_level = readiness.get('level')
        except Exception as e:
            logger.warning(f"Error fetching training readiness for {date}: {e}")

        # Only save if we got at least some data
        has_data = (
            fitness_data.vo2max_running is not None or
            fitness_data.training_status is not None or
            fitness_data.training_readiness_score is not None or
            fitness_data.race_time_5k is not None
        )

        if has_data:
            training_db.save_garmin_fitness_data(fitness_data)

            if existing:
                updated_days += 1
            else:
                new_days += 1

            synced_days.append(SyncedFitnessDay(
                date=date,
                vo2max_running=fitness_data.vo2max_running,
                vo2max_cycling=fitness_data.vo2max_cycling,
                fitness_age=fitness_data.fitness_age,
                training_status=fitness_data.training_status,
                training_readiness_score=fitness_data.training_readiness_score,
                has_race_predictions=fitness_data.race_time_5k is not None,
            ))

    total = new_days + updated_days
    return FitnessSyncResponse(
        success=True,
        synced_count=total,
        message=f"Successfully synced fitness data for {total} days ({new_days} new, {updated_days} updated)",
        new_days=new_days,
        updated_days=updated_days,
        synced_days=synced_days[:30],  # Limit response size
    )


@router.get("/fitness-data/{date}", response_model=FitnessDataResponse)
async def get_fitness_data(
    date: str,
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Get fitness data for a specific date.

    Returns VO2max, race predictions, training status, and readiness for the
    specified date. If no data exists for that exact date, returns the most
    recent data available before that date.

    **Parameters:**
    - date: Date in YYYY-MM-DD format
    """
    # First try exact date match
    fitness_data = training_db.get_garmin_fitness_data(date)

    # If no exact match, get the most recent data before this date
    if fitness_data is None:
        fitness_data = training_db.get_garmin_fitness_for_workout(date)

    if fitness_data is None:
        return FitnessDataResponse(
            success=False,
            date=date,
        )

    # Build race predictions list
    race_predictions = []
    if fitness_data.race_time_5k is not None:
        race_predictions.append(RacePrediction(
            distance="5K",
            time_seconds=fitness_data.race_time_5k,
            time_formatted=_format_race_time(fitness_data.race_time_5k),
        ))
    if fitness_data.race_time_10k is not None:
        race_predictions.append(RacePrediction(
            distance="10K",
            time_seconds=fitness_data.race_time_10k,
            time_formatted=_format_race_time(fitness_data.race_time_10k),
        ))
    if fitness_data.race_time_half is not None:
        race_predictions.append(RacePrediction(
            distance="Half Marathon",
            time_seconds=fitness_data.race_time_half,
            time_formatted=_format_race_time(fitness_data.race_time_half),
        ))
    if fitness_data.race_time_marathon is not None:
        race_predictions.append(RacePrediction(
            distance="Marathon",
            time_seconds=fitness_data.race_time_marathon,
            time_formatted=_format_race_time(fitness_data.race_time_marathon),
        ))

    return FitnessDataResponse(
        success=True,
        date=fitness_data.date,
        vo2max_running=fitness_data.vo2max_running,
        vo2max_cycling=fitness_data.vo2max_cycling,
        fitness_age=fitness_data.fitness_age,
        race_predictions=race_predictions,
        training_status=fitness_data.training_status,
        training_status_description=fitness_data.training_status_description,
        fitness_trend=fitness_data.fitness_trend,
        training_readiness_score=fitness_data.training_readiness_score,
        training_readiness_level=fitness_data.training_readiness_level,
        acwr_percent=fitness_data.acwr_percent,
        acwr_status=fitness_data.acwr_status,
    )


@router.get("/fitness-history", response_model=list[FitnessDataResponse])
async def get_fitness_history(
    days: int = 30,
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Get fitness data history.

    Returns historical VO2max, race predictions, and training status for
    the specified number of days.

    **Parameters:**
    - days: Number of days of history to return (default: 30, max: 365)
    """
    if days > 365:
        days = 365

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    fitness_records = training_db.get_garmin_fitness_range(
        start_date.isoformat(),
        end_date.isoformat()
    )

    results = []
    for data in fitness_records:
        # Build race predictions list
        race_predictions = []
        if data.race_time_5k is not None:
            race_predictions.append(RacePrediction(
                distance="5K",
                time_seconds=data.race_time_5k,
                time_formatted=_format_race_time(data.race_time_5k),
            ))
        if data.race_time_10k is not None:
            race_predictions.append(RacePrediction(
                distance="10K",
                time_seconds=data.race_time_10k,
                time_formatted=_format_race_time(data.race_time_10k),
            ))
        if data.race_time_half is not None:
            race_predictions.append(RacePrediction(
                distance="Half Marathon",
                time_seconds=data.race_time_half,
                time_formatted=_format_race_time(data.race_time_half),
            ))
        if data.race_time_marathon is not None:
            race_predictions.append(RacePrediction(
                distance="Marathon",
                time_seconds=data.race_time_marathon,
                time_formatted=_format_race_time(data.race_time_marathon),
            ))

        results.append(FitnessDataResponse(
            success=True,
            date=data.date,
            vo2max_running=data.vo2max_running,
            vo2max_cycling=data.vo2max_cycling,
            fitness_age=data.fitness_age,
            race_predictions=race_predictions,
            training_status=data.training_status,
            training_status_description=data.training_status_description,
            fitness_trend=data.fitness_trend,
            training_readiness_score=data.training_readiness_score,
            training_readiness_level=data.training_readiness_level,
            acwr_percent=data.acwr_percent,
            acwr_status=data.acwr_status,
        ))

    return results
