"""Garmin Connect sync API routes."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr

from ..deps import get_training_db
from ...db.database import TrainingDatabase, ActivityMetrics, GarminFitnessData


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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to Garmin Connect: {str(e)}"
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
            print(f"Error fetching max metrics for {date}: {e}")

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
            print(f"Error fetching race predictions for {date}: {e}")

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
            print(f"Error fetching training status for {date}: {e}")

        # Fetch training readiness
        try:
            readiness = client.get_training_readiness(date)
            if readiness:
                fitness_data.training_readiness_score = readiness.get('score')
                fitness_data.training_readiness_level = readiness.get('level')
        except Exception as e:
            print(f"Error fetching training readiness for {date}: {e}")

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
