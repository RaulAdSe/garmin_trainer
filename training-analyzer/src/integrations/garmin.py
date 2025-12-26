"""
Garmin Connect integration for workout sync and push.

Implements:
- OAuth 1.0a flow for Garmin Connect
- Activity download and sync
- Workout push to Garmin devices via Connect
- FIT file upload
"""

import hashlib
import hmac
import json
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import secrets
import base64

from .base import (
    AuthenticationError,
    IntegrationClient,
    IntegrationError,
    OAuthCredentials,
    OAuthFlow,
    RateLimitError,
)


# Garmin uses OAuth 1.0a, so we need different credential handling
@dataclass
class GarminCredentials:
    """
    Garmin Connect OAuth 1.0a credentials.
    """
    consumer_key: str
    consumer_secret: str
    access_token: Optional[str] = None
    access_token_secret: Optional[str] = None
    
    # User info
    user_id: Optional[str] = None
    display_name: Optional[str] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_authenticated(self) -> bool:
        """Check if we have valid tokens."""
        return self.access_token is not None and self.access_token_secret is not None
    
    def to_dict(self) -> dict:
        return {
            "consumer_key": self.consumer_key,
            "consumer_secret": self.consumer_secret,
            "access_token": self.access_token,
            "access_token_secret": self.access_token_secret,
            "user_id": self.user_id,
            "display_name": self.display_name,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "GarminCredentials":
        return cls(
            consumer_key=data["consumer_key"],
            consumer_secret=data["consumer_secret"],
            access_token=data.get("access_token"),
            access_token_secret=data.get("access_token_secret"),
            user_id=data.get("user_id"),
            display_name=data.get("display_name"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )


class GarminOAuthFlow:
    """
    OAuth 1.0a flow for Garmin Connect.
    
    Garmin uses OAuth 1.0a which requires:
    1. Request token
    2. User authorization
    3. Access token exchange
    """
    
    provider = "garmin"
    
    REQUEST_TOKEN_URL = "https://connectapi.garmin.com/oauth-service/oauth/request_token"
    AUTHORIZE_URL = "https://connect.garmin.com/oauthConfirm"
    ACCESS_TOKEN_URL = "https://connectapi.garmin.com/oauth-service/oauth/access_token"
    
    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        callback_url: str,
    ):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.callback_url = callback_url
        
        # Temporary tokens during flow
        self._request_token: Optional[str] = None
        self._request_token_secret: Optional[str] = None
    
    def _generate_nonce(self) -> str:
        """Generate a random nonce."""
        return secrets.token_hex(16)
    
    def _generate_timestamp(self) -> str:
        """Generate OAuth timestamp."""
        return str(int(time.time()))
    
    def _percent_encode(self, s: str) -> str:
        """Percent-encode a string per OAuth spec."""
        return urllib.parse.quote(str(s), safe="")
    
    def _generate_signature_base(
        self,
        method: str,
        url: str,
        params: Dict[str, str],
    ) -> str:
        """Generate the signature base string."""
        # Sort and encode parameters
        sorted_params = sorted(params.items())
        param_string = "&".join(
            f"{self._percent_encode(k)}={self._percent_encode(v)}"
            for k, v in sorted_params
        )
        
        # Construct base string
        base = "&".join([
            method.upper(),
            self._percent_encode(url),
            self._percent_encode(param_string),
        ])
        
        return base
    
    def _generate_signature(
        self,
        method: str,
        url: str,
        params: Dict[str, str],
        token_secret: str = "",
    ) -> str:
        """Generate HMAC-SHA1 signature."""
        base = self._generate_signature_base(method, url, params)
        
        # Signing key
        key = f"{self._percent_encode(self.consumer_secret)}&{self._percent_encode(token_secret)}"
        
        # HMAC-SHA1
        signature = hmac.new(
            key.encode("utf-8"),
            base.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        
        return base64.b64encode(signature).decode("utf-8")
    
    def _build_auth_header(self, params: Dict[str, str]) -> str:
        """Build OAuth Authorization header."""
        header_params = ", ".join(
            f'{self._percent_encode(k)}="{self._percent_encode(v)}"'
            for k, v in sorted(params.items())
        )
        return f"OAuth {header_params}"
    
    async def get_request_token(self) -> Tuple[str, str]:
        """
        Step 1: Get a request token.
        
        Returns:
            Tuple of (request_token, request_token_secret)
        """
        # OAuth parameters
        oauth_params = {
            "oauth_consumer_key": self.consumer_key,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": self._generate_timestamp(),
            "oauth_nonce": self._generate_nonce(),
            "oauth_callback": self.callback_url,
            "oauth_version": "1.0",
        }
        
        # Generate signature
        signature = self._generate_signature(
            "POST",
            self.REQUEST_TOKEN_URL,
            oauth_params,
        )
        oauth_params["oauth_signature"] = signature
        
        # In production, use httpx or aiohttp
        # This is a mock for the structure
        # response = await self._make_request("POST", self.REQUEST_TOKEN_URL, oauth_params)
        
        # Parse response (format: oauth_token=xxx&oauth_token_secret=xxx)
        # For now, return placeholder
        self._request_token = "placeholder_request_token"
        self._request_token_secret = "placeholder_request_secret"
        
        return self._request_token, self._request_token_secret
    
    def get_authorization_url(self, request_token: str) -> str:
        """
        Step 2: Get URL to redirect user for authorization.
        
        Args:
            request_token: Token from get_request_token()
        
        Returns:
            Full authorization URL
        """
        params = urllib.parse.urlencode({"oauth_token": request_token})
        return f"{self.AUTHORIZE_URL}?{params}"
    
    async def get_access_token(
        self,
        request_token: str,
        request_token_secret: str,
        oauth_verifier: str,
    ) -> GarminCredentials:
        """
        Step 3: Exchange request token for access token.
        
        Args:
            request_token: Request token from step 1
            request_token_secret: Request token secret from step 1
            oauth_verifier: Verifier from callback URL
        
        Returns:
            GarminCredentials with access tokens
        """
        # OAuth parameters
        oauth_params = {
            "oauth_consumer_key": self.consumer_key,
            "oauth_token": request_token,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": self._generate_timestamp(),
            "oauth_nonce": self._generate_nonce(),
            "oauth_verifier": oauth_verifier,
            "oauth_version": "1.0",
        }
        
        # Generate signature with request token secret
        signature = self._generate_signature(
            "POST",
            self.ACCESS_TOKEN_URL,
            oauth_params,
            request_token_secret,
        )
        oauth_params["oauth_signature"] = signature
        
        # Make request and parse response
        # In production, actually make the HTTP request
        
        return GarminCredentials(
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            access_token="placeholder_access_token",
            access_token_secret="placeholder_access_secret",
        )


class GarminActivityType(str, Enum):
    """Garmin activity types."""
    RUNNING = "running"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    STRENGTH = "strength_training"
    WALKING = "walking"
    HIKING = "hiking"
    OTHER = "other"


@dataclass
class GarminActivity:
    """Garmin activity data."""
    activity_id: str
    activity_type: GarminActivityType
    name: str
    start_time: datetime
    duration_sec: int
    distance_m: Optional[float] = None
    calories: Optional[int] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    avg_pace_sec_km: Optional[int] = None
    avg_power: Optional[int] = None
    elevation_gain_m: Optional[float] = None
    training_effect: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            "activity_id": self.activity_id,
            "activity_type": self.activity_type.value,
            "name": self.name,
            "start_time": self.start_time.isoformat(),
            "duration_sec": self.duration_sec,
            "distance_m": self.distance_m,
            "calories": self.calories,
            "avg_hr": self.avg_hr,
            "max_hr": self.max_hr,
            "avg_pace_sec_km": self.avg_pace_sec_km,
            "avg_power": self.avg_power,
            "elevation_gain_m": self.elevation_gain_m,
            "training_effect": self.training_effect,
        }


class GarminConnectClient:
    """
    Client for Garmin Connect API.
    
    Features:
    - Activity listing and download
    - Workout push to devices
    - FIT file upload
    """
    
    provider = "garmin"
    BASE_URL = "https://connect.garmin.com"
    API_URL = "https://connectapi.garmin.com"
    
    def __init__(self, credentials: GarminCredentials):
        if not credentials.is_authenticated:
            raise AuthenticationError("Garmin credentials not authenticated", "garmin")
        self.credentials = credentials
    
    def _sign_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Sign a request with OAuth 1.0a."""
        oauth_params = {
            "oauth_consumer_key": self.credentials.consumer_key,
            "oauth_token": self.credentials.access_token,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_nonce": secrets.token_hex(16),
            "oauth_version": "1.0",
        }
        
        all_params = {**oauth_params}
        if params:
            all_params.update(params)
        
        # Generate signature base string
        sorted_params = sorted(all_params.items())
        param_string = "&".join(
            f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='')}"
            for k, v in sorted_params
        )
        
        base = "&".join([
            method.upper(),
            urllib.parse.quote(url, safe=""),
            urllib.parse.quote(param_string, safe=""),
        ])
        
        # Signing key
        key = f"{urllib.parse.quote(self.credentials.consumer_secret, safe='')}&{urllib.parse.quote(self.credentials.access_token_secret or '', safe='')}"
        
        # HMAC-SHA1
        signature = hmac.new(
            key.encode("utf-8"),
            base.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        
        oauth_params["oauth_signature"] = base64.b64encode(signature).decode("utf-8")
        
        # Build header
        header_params = ", ".join(
            f'{k}="{urllib.parse.quote(str(v), safe="")}"'
            for k, v in sorted(oauth_params.items())
        )
        
        return {"Authorization": f"OAuth {header_params}"}
    
    async def get_user_profile(self) -> Dict[str, Any]:
        """Get Garmin user profile."""
        url = f"{self.API_URL}/userprofile-service/socialProfile"
        headers = self._sign_request("GET", url)
        
        # In production, make actual HTTP request
        # response = await httpx.get(url, headers=headers)
        
        return {
            "user_id": self.credentials.user_id,
            "display_name": self.credentials.display_name,
            "profile_image_url": None,
        }
    
    async def get_activities(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[GarminActivity]:
        """
        Get activities from Garmin Connect.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum activities to return
        
        Returns:
            List of GarminActivity objects
        """
        url = f"{self.API_URL}/activitylist-service/activities"
        
        params = {"limit": str(limit)}
        if start_date:
            params["startDate"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["endDate"] = end_date.strftime("%Y-%m-%d")
        
        headers = self._sign_request("GET", url, params)
        
        # In production, make actual HTTP request
        # response = await httpx.get(url, headers=headers, params=params)
        
        return []  # Would return parsed activities
    
    async def get_activity_details(self, activity_id: str) -> Dict[str, Any]:
        """Get detailed activity data including GPS, HR, etc."""
        url = f"{self.API_URL}/activity-service/activity/{activity_id}/details"
        headers = self._sign_request("GET", url)
        
        # Make request and return details
        return {}
    
    async def download_activity_fit(self, activity_id: str) -> bytes:
        """Download original FIT file for an activity."""
        url = f"{self.BASE_URL}/modern/proxy/download-service/files/activity/{activity_id}"
        headers = self._sign_request("GET", url)
        
        # Make request and return FIT file bytes
        return b""


@dataclass
class GarminWorkoutStep:
    """A step in a Garmin workout."""
    step_type: str  # "warmup", "cooldown", "interval", "recovery", "rest"
    duration_type: str  # "time", "distance", "lap_button", "open"
    duration_value: Optional[int] = None  # seconds or meters depending on type
    target_type: str = "open"  # "heart_rate", "pace", "power", "open"
    target_low: Optional[int] = None
    target_high: Optional[int] = None
    notes: Optional[str] = None


@dataclass
class GarminWorkout:
    """Garmin workout definition."""
    name: str
    sport_type: str  # "running", "cycling", "swimming"
    steps: List[GarminWorkoutStep] = field(default_factory=list)
    description: Optional[str] = None
    estimated_duration_sec: Optional[int] = None
    
    def to_garmin_format(self) -> Dict[str, Any]:
        """Convert to Garmin API format."""
        return {
            "workoutName": self.name,
            "sportType": {
                "sportTypeKey": self.sport_type,
            },
            "description": self.description or "",
            "estimatedDurationInSecs": self.estimated_duration_sec,
            "workoutSegments": [
                {
                    "segmentOrder": 0,
                    "sportType": {"sportTypeKey": self.sport_type},
                    "workoutSteps": [
                        {
                            "type": step.step_type,
                            "stepOrder": i,
                            "endCondition": {
                                "conditionTypeKey": step.duration_type,
                                "conditionTypeId": 1 if step.duration_type == "time" else 2,
                            },
                            "endConditionValue": step.duration_value,
                            "targetType": {
                                "workoutTargetTypeKey": step.target_type,
                            },
                            "targetValueOne": step.target_low,
                            "targetValueTwo": step.target_high,
                        }
                        for i, step in enumerate(self.steps)
                    ],
                }
            ],
        }


class GarminWorkoutPush:
    """
    Service for pushing workouts to Garmin Connect.
    
    Allows sending structured workouts to Garmin devices via Connect.
    """
    
    WORKOUT_API_URL = "https://connect.garmin.com/modern/proxy/workout-service/workout"
    
    def __init__(self, client: GarminConnectClient):
        self.client = client
    
    async def push_workout(self, workout: GarminWorkout) -> str:
        """
        Push a workout to Garmin Connect.
        
        Args:
            workout: Workout to push
        
        Returns:
            Workout ID from Garmin
        """
        workout_data = workout.to_garmin_format()
        
        url = self.WORKOUT_API_URL
        headers = self.client._sign_request("POST", url)
        headers["Content-Type"] = "application/json"
        
        # In production:
        # response = await httpx.post(url, headers=headers, json=workout_data)
        # return response.json()["workoutId"]
        
        return "placeholder_workout_id"
    
    async def schedule_workout(
        self,
        workout_id: str,
        schedule_date: datetime,
    ) -> bool:
        """
        Schedule a workout for a specific date.
        
        Args:
            workout_id: ID of workout in Garmin Connect
            schedule_date: Date to schedule workout
        
        Returns:
            True if successful
        """
        url = f"{self.WORKOUT_API_URL}/{workout_id}/schedule/{schedule_date.strftime('%Y-%m-%d')}"
        headers = self.client._sign_request("POST", url)
        
        # Make request
        return True
    
    async def delete_workout(self, workout_id: str) -> bool:
        """Delete a workout from Garmin Connect."""
        url = f"{self.WORKOUT_API_URL}/{workout_id}"
        headers = self.client._sign_request("DELETE", url)
        
        return True
    
    async def list_workouts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List workouts in Garmin Connect."""
        url = f"{self.WORKOUT_API_URL}s"
        params = {"limit": str(limit)}
        headers = self.client._sign_request("GET", url, params)
        
        return []
    
    async def upload_fit_file(
        self,
        fit_data: bytes,
        activity_name: Optional[str] = None,
    ) -> str:
        """
        Upload a FIT file to Garmin Connect.
        
        Args:
            fit_data: Raw FIT file bytes
            activity_name: Optional name for the activity
        
        Returns:
            Activity ID
        """
        url = "https://connect.garmin.com/modern/proxy/upload-service/upload/.fit"
        headers = self.client._sign_request("POST", url)
        headers["Content-Type"] = "application/octet-stream"
        
        # In production, upload the file
        return "placeholder_activity_id"

