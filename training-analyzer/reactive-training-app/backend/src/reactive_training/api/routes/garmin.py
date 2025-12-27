"""Garmin Connect sync API routes."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, EmailStr


router = APIRouter()


class GarminSyncRequest(BaseModel):
    """Request to sync activities from Garmin Connect."""

    email: EmailStr = Field(..., description="Garmin Connect email")
    password: str = Field(..., min_length=1, description="Garmin Connect password")
    days: int = Field(
        default=30, ge=1, le=365, description="Number of days to sync (1-365)"
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
    """Map Garmin activity type to our internal type."""
    type_map = {
        "running": "running",
        "trail_running": "running",
        "treadmill_running": "running",
        "cycling": "cycling",
        "indoor_cycling": "cycling",
        "virtual_ride": "cycling",
        "swimming": "swimming",
        "pool_swimming": "swimming",
        "open_water_swimming": "swimming",
        "walking": "walking",
        "hiking": "walking",
        "strength_training": "strength",
        "yoga": "yoga",
        "pilates": "yoga",
        "hiit": "hiit",
        "cardio": "hiit",
    }
    return type_map.get(garmin_type.lower(), "other")


def _calculate_pace(
    distance_m: Optional[float], duration_sec: Optional[float]
) -> Optional[float]:
    """Calculate pace in seconds per km."""
    if not distance_m or not duration_sec or distance_m <= 0:
        return None
    distance_km = distance_m / 1000
    return duration_sec / distance_km


# In-memory storage for now (can be replaced with database)
_activities_store: dict[str, dict] = {}


@router.post("/sync", response_model=GarminSyncDetailedResponse)
async def sync_garmin(request: GarminSyncRequest):
    """
    Sync activities from Garmin Connect.

    This endpoint connects to Garmin Connect using the provided credentials,
    fetches recent activities, and saves them to the local storage.

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
            detail="garminconnect library not installed. Run: pip install garminconnect",
        )

    # Attempt login
    try:
        client = Garmin(request.email, request.password)
        client.login()
    except GarminConnectAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Garmin Connect credentials. Please check your email and password.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to Garmin Connect: {str(e)}"
        )

    # Fetch activities
    try:
        activities = client.get_activities(
            0, request.days * 3
        )  # Fetch extra to ensure coverage
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch activities from Garmin: {str(e)}"
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
                activity_datetime = datetime.fromisoformat(
                    activity_date_str.replace("Z", "+00:00")
                )
            except ValueError:
                # Try alternative format
                try:
                    activity_datetime = datetime.strptime(
                        activity_date_str[:19], "%Y-%m-%d %H:%M:%S"
                    )
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
            existing = _activities_store.get(activity_id)

            # Store activity
            activity_data = {
                "activity_id": activity_id,
                "date": activity_datetime.strftime("%Y-%m-%d"),
                "activity_type": mapped_type,
                "activity_name": activity_name,
                "avg_hr": int(avg_hr) if avg_hr else None,
                "max_hr": int(max_hr) if max_hr else None,
                "duration_min": duration_min,
                "distance_km": distance_km,
                "pace_sec_per_km": pace_sec_per_km,
                "sport_type": activity_type,
                "avg_speed_kmh": avg_speed_kmh,
                "elevation_gain_m": elevation_gain,
                "calories": calories,
            }

            _activities_store[activity_id] = activity_data

            if existing:
                updated_count += 1
            else:
                new_count += 1

            # Add to synced activities list
            synced_activities.append(
                SyncedActivity(
                    id=activity_id,
                    name=activity_name,
                    type=mapped_type,
                    date=activity_datetime.strftime("%Y-%m-%d"),
                    distance_km=round(distance_km, 2) if distance_km else None,
                    duration_min=round(duration_min, 1) if duration_min else None,
                )
            )

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
            "running",
            "cycling",
            "swimming",
            "walking",
            "strength",
            "yoga",
            "hiit",
        ],
        "max_sync_days": 365,
        "synced_activities_count": len(_activities_store),
        "notes": [
            "Credentials are only used for the sync request and are not stored",
            "Use HTTPS in production to protect credentials",
            "Rate limits may apply from Garmin's side",
        ],
    }


@router.get("/activities")
async def get_synced_activities(
    activity_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    Get synced activities.

    Returns activities that have been synced from Garmin Connect.
    """
    activities = list(_activities_store.values())

    # Filter by type if specified
    if activity_type:
        activities = [a for a in activities if a["activity_type"] == activity_type]

    # Sort by date descending
    activities.sort(key=lambda x: x["date"], reverse=True)

    # Paginate
    total = len(activities)
    activities = activities[offset : offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "activities": activities,
    }
