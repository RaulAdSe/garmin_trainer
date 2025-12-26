"""Garmin Connect sync API routes."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr

from ..deps import get_training_db
from ...db.database import TrainingDatabase, ActivityMetrics


router = APIRouter()


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
    except GarminConnectAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Garmin Connect credentials. Please check your email and password."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to Garmin Connect: {str(e)}"
        )

    # Fetch activities
    try:
        activities = client.get_activities(0, request.days * 3)  # Fetch extra to ensure coverage
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch activities from Garmin: {str(e)}"
        )

    # Filter activities to the requested date range
    cutoff_date = datetime.now() - timedelta(days=request.days)

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

            # Create activity metrics object
            metrics = ActivityMetrics(
                activity_id=activity_id,
                date=activity_datetime.strftime("%Y-%m-%d"),
                activity_type=mapped_type,
                activity_name=activity_name,
                hrss=None,  # Will be calculated by enrichment service
                trimp=None,
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
            print(f"Error processing activity: {e}")
            continue

    total_synced = new_count + updated_count

    return GarminSyncDetailedResponse(
        success=True,
        synced_count=total_synced,
        new_activities=new_count,
        updated_activities=updated_count,
        message=f"Successfully synced {total_synced} activities ({new_count} new, {updated_count} updated)",
        activities=synced_activities[:50],  # Limit to 50 most recent
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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect: {str(e)}"
        )

    # Get wellness.db path
    import sqlite3
    from pathlib import Path
    from ...config import PROJECT_ROOT

    wellness_db_path = PROJECT_ROOT / "whoop-dashboard" / "wellness.db"

    if not wellness_db_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Wellness database not found at {wellness_db_path}"
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
        "notes": [
            "Credentials are only used for the sync request and are not stored",
            "Use HTTPS in production to protect credentials",
            "Rate limits may apply from Garmin's side",
        ],
    }
