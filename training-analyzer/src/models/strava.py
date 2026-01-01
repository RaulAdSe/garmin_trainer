"""Strava integration data models for OAuth credentials and preferences."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class SyncStatus(str, Enum):
    """Status of activity synchronization with Strava."""
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"


class StravaCredentials(BaseModel):
    """Strava OAuth credentials for a user."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    user_id: str = Field(default="default", description="User identifier")
    access_token: str = Field(..., description="OAuth access token")
    refresh_token: str = Field(..., description="OAuth refresh token")
    expires_at: str = Field(..., description="Token expiration timestamp (ISO format)")
    athlete_id: Optional[str] = Field(None, description="Strava athlete ID")
    athlete_name: Optional[str] = Field(None, description="Strava athlete display name")
    scope: Optional[str] = Field(None, description="OAuth scopes granted")
    created_at: Optional[datetime] = Field(None, description="When credentials were created")
    updated_at: Optional[datetime] = Field(None, description="When credentials were last updated")

    def is_expired(self) -> bool:
        """Check if the access token has expired."""
        try:
            expires = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            return datetime.now(expires.tzinfo) >= expires
        except (ValueError, AttributeError):
            return True

    def needs_refresh(self, buffer_seconds: int = 300) -> bool:
        """Check if the token needs refresh (with buffer before expiration)."""
        try:
            expires = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            from datetime import timedelta
            return datetime.now(expires.tzinfo) >= (expires - timedelta(seconds=buffer_seconds))
        except (ValueError, AttributeError):
            return True


class StravaPreferences(BaseModel):
    """User preferences for Strava integration."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    user_id: str = Field(default="default", description="User identifier")
    auto_update_description: bool = Field(
        default=True,
        description="Automatically update Strava activity descriptions"
    )
    include_score: bool = Field(
        default=True,
        description="Include overall workout score in description"
    )
    include_summary: bool = Field(
        default=True,
        description="Include AI-generated summary in description"
    )
    include_link: bool = Field(
        default=True,
        description="Include link to full analysis"
    )
    use_extended_format: bool = Field(
        default=False,
        description="Use extended format with more details"
    )
    custom_footer: Optional[str] = Field(
        None,
        description="Custom text to append to descriptions"
    )
    updated_at: Optional[datetime] = Field(None, description="When preferences were last updated")


class StravaActivitySync(BaseModel):
    """Mapping between local activity and Strava activity."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    local_activity_id: str = Field(..., description="Local activity ID (Garmin)")
    strava_activity_id: int = Field(..., description="Strava activity ID")
    sync_status: SyncStatus = Field(
        default=SyncStatus.PENDING,
        description="Current sync status"
    )
    last_synced_at: Optional[str] = Field(
        None,
        description="When activity was last synced (ISO format)"
    )
    description_updated: bool = Field(
        default=False,
        description="Whether description has been updated"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if sync failed"
    )
    created_at: Optional[datetime] = Field(None, description="When sync record was created")


# =============================================================================
# Request/Response Models for API
# =============================================================================

class StravaConnectRequest(BaseModel):
    """Request to initiate Strava OAuth flow."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    redirect_uri: Optional[str] = Field(
        None,
        description="Custom redirect URI (defaults to configured value)"
    )


class StravaConnectResponse(BaseModel):
    """Response with Strava authorization URL."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    authorization_url: str = Field(..., description="URL to redirect user for OAuth")
    state: str = Field(..., description="State parameter for CSRF protection")


class StravaCallbackRequest(BaseModel):
    """Request from Strava OAuth callback."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    code: str = Field(..., description="Authorization code from Strava")
    state: str = Field(..., description="State parameter for verification")
    scope: Optional[str] = Field(None, description="Granted scopes")


class StravaStatusResponse(BaseModel):
    """Response with Strava connection status."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    connected: bool = Field(..., description="Whether Strava is connected")
    athlete_id: Optional[str] = Field(None, description="Strava athlete ID")
    athlete_name: Optional[str] = Field(None, description="Strava athlete name")
    scope: Optional[str] = Field(None, description="Granted OAuth scopes")
    expires_at: Optional[str] = Field(None, description="Token expiration time")


class StravaPreferencesUpdate(BaseModel):
    """Request to update Strava preferences."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    auto_update_description: Optional[bool] = Field(None)
    include_score: Optional[bool] = Field(None)
    include_summary: Optional[bool] = Field(None)
    include_link: Optional[bool] = Field(None)
    use_extended_format: Optional[bool] = Field(None)
    custom_footer: Optional[str] = Field(None)


class StravaSyncRequest(BaseModel):
    """Request to manually sync an activity to Strava."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    local_activity_id: str = Field(..., description="Local activity ID to sync")
    strava_activity_id: int = Field(..., description="Strava activity ID to update")
    force: bool = Field(
        default=False,
        description="Force sync even if already synced"
    )


class StravaSyncResponse(BaseModel):
    """Response from activity sync operation."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    success: bool = Field(..., description="Whether sync succeeded")
    local_activity_id: str = Field(..., description="Local activity ID")
    strava_activity_id: int = Field(..., description="Strava activity ID")
    description_updated: bool = Field(
        default=False,
        description="Whether description was updated"
    )
    error_message: Optional[str] = Field(None, description="Error if sync failed")
