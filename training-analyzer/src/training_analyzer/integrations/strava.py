"""
Strava integration for activity sync and segment analysis.

Implements:
- OAuth 2.0 flow for Strava
- Activity listing and download
- Segment effort tracking
- Webhook support for real-time sync
"""

import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .base import (
    AuthenticationError,
    IntegrationClient,
    IntegrationError,
    OAuthCredentials,
    OAuthFlow,
    RateLimitError,
)


class StravaSport(str, Enum):
    """Strava sport types."""
    RUN = "Run"
    RIDE = "Ride"
    SWIM = "Swim"
    WALK = "Walk"
    HIKE = "Hike"
    VIRTUAL_RUN = "VirtualRun"
    VIRTUAL_RIDE = "VirtualRide"
    WEIGHT_TRAINING = "WeightTraining"
    WORKOUT = "Workout"


@dataclass
class StravaActivity:
    """Strava activity data."""
    id: int
    name: str
    sport_type: StravaSport
    start_date: datetime
    elapsed_time_sec: int
    moving_time_sec: int
    distance_m: float
    
    # Performance metrics
    average_speed_mps: Optional[float] = None
    max_speed_mps: Optional[float] = None
    average_heartrate: Optional[float] = None
    max_heartrate: Optional[int] = None
    average_watts: Optional[float] = None
    max_watts: Optional[int] = None
    weighted_average_watts: Optional[float] = None
    
    # Elevation
    total_elevation_gain_m: Optional[float] = None
    elev_high_m: Optional[float] = None
    elev_low_m: Optional[float] = None
    
    # Strava-specific
    kudos_count: int = 0
    suffer_score: Optional[int] = None
    device_name: Optional[str] = None
    external_id: Optional[str] = None  # FIT file ID
    
    # Flags
    trainer: bool = False
    commute: bool = False
    manual: bool = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "sport_type": self.sport_type.value,
            "start_date": self.start_date.isoformat(),
            "elapsed_time_sec": self.elapsed_time_sec,
            "moving_time_sec": self.moving_time_sec,
            "distance_m": self.distance_m,
            "average_speed_mps": self.average_speed_mps,
            "max_speed_mps": self.max_speed_mps,
            "average_heartrate": self.average_heartrate,
            "max_heartrate": self.max_heartrate,
            "average_watts": self.average_watts,
            "max_watts": self.max_watts,
            "weighted_average_watts": self.weighted_average_watts,
            "total_elevation_gain_m": self.total_elevation_gain_m,
            "kudos_count": self.kudos_count,
            "suffer_score": self.suffer_score,
            "trainer": self.trainer,
            "commute": self.commute,
        }
    
    @classmethod
    def from_api_response(cls, data: dict) -> "StravaActivity":
        """Parse from Strava API response."""
        sport_map = {
            "Run": StravaSport.RUN,
            "Ride": StravaSport.RIDE,
            "Swim": StravaSport.SWIM,
            "Walk": StravaSport.WALK,
            "Hike": StravaSport.HIKE,
            "VirtualRun": StravaSport.VIRTUAL_RUN,
            "VirtualRide": StravaSport.VIRTUAL_RIDE,
            "WeightTraining": StravaSport.WEIGHT_TRAINING,
        }
        
        sport_type = sport_map.get(data.get("sport_type", ""), StravaSport.WORKOUT)
        
        return cls(
            id=data["id"],
            name=data["name"],
            sport_type=sport_type,
            start_date=datetime.fromisoformat(data["start_date"].replace("Z", "+00:00")),
            elapsed_time_sec=data["elapsed_time"],
            moving_time_sec=data["moving_time"],
            distance_m=data.get("distance", 0),
            average_speed_mps=data.get("average_speed"),
            max_speed_mps=data.get("max_speed"),
            average_heartrate=data.get("average_heartrate"),
            max_heartrate=data.get("max_heartrate"),
            average_watts=data.get("average_watts"),
            max_watts=data.get("max_watts"),
            weighted_average_watts=data.get("weighted_average_watts"),
            total_elevation_gain_m=data.get("total_elevation_gain"),
            elev_high_m=data.get("elev_high"),
            elev_low_m=data.get("elev_low"),
            kudos_count=data.get("kudos_count", 0),
            suffer_score=data.get("suffer_score"),
            device_name=data.get("device_name"),
            external_id=data.get("external_id"),
            trainer=data.get("trainer", False),
            commute=data.get("commute", False),
            manual=data.get("manual", False),
        )


@dataclass
class StravaSegment:
    """Strava segment data."""
    id: int
    name: str
    activity_type: str
    distance_m: float
    average_grade: float
    maximum_grade: float
    elevation_high_m: float
    elevation_low_m: float
    
    # Effort stats
    effort_count: int = 0
    athlete_count: int = 0
    star_count: int = 0
    
    # Personal records
    athlete_pr_effort_id: Optional[int] = None
    athlete_pr_time_sec: Optional[int] = None
    
    # Location
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "activity_type": self.activity_type,
            "distance_m": self.distance_m,
            "average_grade": self.average_grade,
            "maximum_grade": self.maximum_grade,
            "elevation_high_m": self.elevation_high_m,
            "elevation_low_m": self.elevation_low_m,
            "effort_count": self.effort_count,
            "athlete_pr_time_sec": self.athlete_pr_time_sec,
            "city": self.city,
            "country": self.country,
        }
    
    @classmethod
    def from_api_response(cls, data: dict) -> "StravaSegment":
        """Parse from Strava API response."""
        return cls(
            id=data["id"],
            name=data["name"],
            activity_type=data.get("activity_type", "Run"),
            distance_m=data["distance"],
            average_grade=data.get("average_grade", 0),
            maximum_grade=data.get("maximum_grade", 0),
            elevation_high_m=data.get("elevation_high", 0),
            elevation_low_m=data.get("elevation_low", 0),
            effort_count=data.get("effort_count", 0),
            athlete_count=data.get("athlete_count", 0),
            star_count=data.get("star_count", 0),
            athlete_pr_effort_id=data.get("athlete_segment_stats", {}).get("pr_activity_id"),
            athlete_pr_time_sec=data.get("athlete_segment_stats", {}).get("pr_elapsed_time"),
            city=data.get("city"),
            state=data.get("state"),
            country=data.get("country"),
        )


@dataclass
class StravaSegmentEffort:
    """A segment effort (attempt at a segment)."""
    id: int
    segment_id: int
    activity_id: int
    elapsed_time_sec: int
    moving_time_sec: int
    start_date: datetime
    
    # Rankings
    pr_rank: Optional[int] = None  # 1, 2, or 3 for PR
    kom_rank: Optional[int] = None  # Position on leaderboard
    
    # Performance
    average_watts: Optional[float] = None
    average_heartrate: Optional[float] = None
    max_heartrate: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "segment_id": self.segment_id,
            "activity_id": self.activity_id,
            "elapsed_time_sec": self.elapsed_time_sec,
            "start_date": self.start_date.isoformat(),
            "pr_rank": self.pr_rank,
            "kom_rank": self.kom_rank,
            "average_watts": self.average_watts,
        }


class StravaOAuthFlow(OAuthFlow):
    """
    OAuth 2.0 flow for Strava.
    """
    
    provider = "strava"
    authorize_url = "https://www.strava.com/oauth/authorize"
    token_url = "https://www.strava.com/oauth/token"
    
    # Strava scopes
    SCOPE_READ = "read"
    SCOPE_READ_ALL = "read_all"
    SCOPE_PROFILE_READ_ALL = "profile:read_all"
    SCOPE_ACTIVITY_READ = "activity:read"
    SCOPE_ACTIVITY_READ_ALL = "activity:read_all"
    SCOPE_ACTIVITY_WRITE = "activity:write"
    
    DEFAULT_SCOPE = "read_all,activity:read_all,profile:read_all"
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scope: Optional[str] = None,
    ):
        super().__init__(client_id, client_secret, redirect_uri, scope or self.DEFAULT_SCOPE)
    
    def get_authorization_url(self) -> str:
        """Get the Strava authorization URL."""
        state = self.generate_state()
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.scope,
            "state": state,
            "approval_prompt": "auto",
        }
        
        query = urllib.parse.urlencode(params)
        return f"{self.authorize_url}?{query}"
    
    async def exchange_code(self, code: str) -> OAuthCredentials:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from callback
        
        Returns:
            OAuth credentials
        """
        # In production, use httpx:
        # response = await httpx.post(self.token_url, data={
        #     "client_id": self.client_id,
        #     "client_secret": self.client_secret,
        #     "code": code,
        #     "grant_type": "authorization_code",
        # })
        # data = response.json()
        
        # Placeholder for structure
        data = {
            "access_token": "placeholder_access_token",
            "refresh_token": "placeholder_refresh_token",
            "expires_at": int((datetime.now() + timedelta(hours=6)).timestamp()),
            "athlete": {
                "id": 12345,
                "firstname": "Test",
                "lastname": "Athlete",
            },
        }
        
        return OAuthCredentials(
            provider=self.provider,
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=datetime.fromtimestamp(data["expires_at"]) if data.get("expires_at") else None,
            token_type="Bearer",
            scope=self.scope,
            user_id=str(data.get("athlete", {}).get("id")),
            user_name=f"{data.get('athlete', {}).get('firstname', '')} {data.get('athlete', {}).get('lastname', '')}".strip(),
        )
    
    async def refresh_token(self, credentials: OAuthCredentials) -> OAuthCredentials:
        """Refresh an expired access token."""
        if not credentials.refresh_token:
            raise AuthenticationError("No refresh token available", "strava")
        
        # In production, use httpx:
        # response = await httpx.post(self.token_url, data={
        #     "client_id": self.client_id,
        #     "client_secret": self.client_secret,
        #     "refresh_token": credentials.refresh_token,
        #     "grant_type": "refresh_token",
        # })
        
        # Return updated credentials
        return OAuthCredentials(
            provider=self.provider,
            access_token="refreshed_access_token",
            refresh_token=credentials.refresh_token,
            expires_at=datetime.now() + timedelta(hours=6),
            token_type="Bearer",
            scope=credentials.scope,
            user_id=credentials.user_id,
            user_name=credentials.user_name,
        )


class StravaClient(IntegrationClient):
    """
    Client for Strava API v3.
    
    Features:
    - Activity listing and details
    - Segment exploration
    - Athlete stats
    - Route downloads
    """
    
    provider = "strava"
    base_url = "https://www.strava.com/api/v3"
    
    def __init__(self, credentials: OAuthCredentials):
        if credentials.provider != "strava":
            raise ValueError("Credentials must be for Strava")
        super().__init__(credentials)
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an API request."""
        url = f"{self.base_url}{endpoint}"
        headers = self.get_auth_headers()
        
        # In production, use httpx:
        # response = await httpx.request(
        #     method, url, headers=headers, params=params, json=json_data
        # )
        # 
        # if response.status_code == 401:
        #     raise AuthenticationError("Token expired", "strava")
        # if response.status_code == 429:
        #     retry_after = int(response.headers.get("X-RateLimit-Reset", 900))
        #     raise RateLimitError("Rate limit exceeded", "strava", retry_after)
        # 
        # return response.json()
        
        return {}  # Placeholder
    
    async def get_user_profile(self) -> Dict[str, Any]:
        """Get authenticated athlete profile."""
        return await self._request("GET", "/athlete")
    
    async def get_athlete_stats(self) -> Dict[str, Any]:
        """Get athlete's aggregate stats."""
        athlete_id = self.credentials.user_id
        return await self._request("GET", f"/athletes/{athlete_id}/stats")
    
    async def get_activities(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        page: int = 1,
    ) -> List[StravaActivity]:
        """
        Get athlete's activities.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            limit: Activities per page (max 200)
            page: Page number
        
        Returns:
            List of StravaActivity objects
        """
        params = {
            "per_page": min(limit, 200),
            "page": page,
        }
        
        if start_date:
            params["after"] = int(start_date.timestamp())
        if end_date:
            params["before"] = int(end_date.timestamp())
        
        response = await self._request("GET", "/athlete/activities", params)
        
        # Parse activities
        activities = []
        if isinstance(response, list):
            for data in response:
                try:
                    activities.append(StravaActivity.from_api_response(data))
                except (KeyError, ValueError):
                    continue
        
        return activities
    
    async def get_activity(self, activity_id: int) -> StravaActivity:
        """Get detailed activity data."""
        response = await self._request("GET", f"/activities/{activity_id}")
        return StravaActivity.from_api_response(response)
    
    async def get_activity_streams(
        self,
        activity_id: int,
        stream_types: Optional[List[str]] = None,
    ) -> Dict[str, List[Any]]:
        """
        Get activity streams (time series data).
        
        Args:
            activity_id: Activity ID
            stream_types: Types to fetch (time, latlng, heartrate, watts, etc.)
        
        Returns:
            Dictionary of stream data
        """
        if stream_types is None:
            stream_types = ["time", "latlng", "distance", "altitude", "heartrate", "cadence", "watts"]
        
        keys = ",".join(stream_types)
        response = await self._request(
            "GET",
            f"/activities/{activity_id}/streams",
            params={"keys": keys, "key_by_type": "true"},
        )
        
        return response
    
    async def get_segment(self, segment_id: int) -> StravaSegment:
        """Get segment details."""
        response = await self._request("GET", f"/segments/{segment_id}")
        return StravaSegment.from_api_response(response)
    
    async def get_segment_efforts(
        self,
        segment_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[StravaSegmentEffort]:
        """
        Get segment efforts for the authenticated athlete.
        
        Args:
            segment_id: Segment ID
            start_date: Start of date range
            end_date: End of date range
            limit: Max efforts to return
        
        Returns:
            List of segment efforts
        """
        params = {"per_page": limit}
        
        if start_date:
            params["start_date_local"] = start_date.isoformat()
        if end_date:
            params["end_date_local"] = end_date.isoformat()
        
        response = await self._request(
            "GET",
            f"/segment_efforts",
            params={"segment_id": segment_id, **params},
        )
        
        efforts = []
        if isinstance(response, list):
            for data in response:
                efforts.append(StravaSegmentEffort(
                    id=data["id"],
                    segment_id=data["segment"]["id"],
                    activity_id=data["activity"]["id"],
                    elapsed_time_sec=data["elapsed_time"],
                    moving_time_sec=data["moving_time"],
                    start_date=datetime.fromisoformat(data["start_date"].replace("Z", "+00:00")),
                    pr_rank=data.get("pr_rank"),
                    kom_rank=data.get("kom_rank"),
                    average_watts=data.get("average_watts"),
                    average_heartrate=data.get("average_heartrate"),
                    max_heartrate=data.get("max_heartrate"),
                ))
        
        return efforts
    
    async def star_segment(self, segment_id: int, starred: bool = True) -> StravaSegment:
        """Star or unstar a segment."""
        response = await self._request(
            "PUT",
            f"/segments/{segment_id}/starred",
            json_data={"starred": starred},
        )
        return StravaSegment.from_api_response(response)
    
    async def explore_segments(
        self,
        bounds: Tuple[float, float, float, float],  # (sw_lat, sw_lng, ne_lat, ne_lng)
        activity_type: str = "running",
        min_cat: Optional[int] = None,
        max_cat: Optional[int] = None,
    ) -> List[StravaSegment]:
        """
        Explore segments in a geographic area.
        
        Args:
            bounds: Bounding box (sw_lat, sw_lng, ne_lat, ne_lng)
            activity_type: "running" or "riding"
            min_cat: Min climb category
            max_cat: Max climb category
        
        Returns:
            List of segments in area
        """
        params = {
            "bounds": f"{bounds[0]},{bounds[1]},{bounds[2]},{bounds[3]}",
            "activity_type": activity_type,
        }
        
        if min_cat is not None:
            params["min_cat"] = min_cat
        if max_cat is not None:
            params["max_cat"] = max_cat
        
        response = await self._request("GET", "/segments/explore", params)
        
        segments = []
        for seg_data in response.get("segments", []):
            try:
                segments.append(StravaSegment.from_api_response(seg_data))
            except (KeyError, ValueError):
                continue
        
        return segments


# Tuple is already imported at the top

