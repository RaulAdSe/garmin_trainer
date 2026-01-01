"""
Strava sync service for workout analysis sharing.

Handles:
- Formatting workout analysis for Strava descriptions
- Syncing analysis to Strava activities
- Managing share URLs
- User preferences for Strava sharing
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Protocol
import logging

from pydantic import BaseModel, Field

from .base import BaseService, CacheProtocol
from ..models.analysis import WorkoutAnalysisResult
from ..integrations.strava import StravaClient
from ..integrations.base import OAuthCredentials


# =============================================================================
# Data Models
# =============================================================================


class StravaPreferences(BaseModel):
    """User preferences for Strava integration."""

    user_id: str = "default"
    auto_update_description: bool = True
    use_extended_format: bool = False
    include_score: bool = True
    include_training_effect: bool = True
    include_recovery: bool = True
    include_summary: bool = True
    custom_footer: Optional[str] = None
    updated_at: Optional[datetime] = None


class StravaSyncStatus(BaseModel):
    """Status of activity sync to Strava."""

    local_activity_id: str
    strava_activity_id: Optional[int] = None
    sync_status: str = "pending"  # pending, synced, failed
    last_synced_at: Optional[datetime] = None
    description_updated: bool = False
    error_message: Optional[str] = None


# =============================================================================
# Database Protocol
# =============================================================================


class StravaDatabase(Protocol):
    """Protocol for Strava-related database operations."""

    async def get_strava_credentials(self, user_id: str = "default") -> Optional[OAuthCredentials]:
        """Get stored Strava OAuth credentials."""
        ...

    async def save_strava_credentials(self, credentials: OAuthCredentials, user_id: str = "default") -> None:
        """Save Strava OAuth credentials."""
        ...

    async def get_strava_preferences(self, user_id: str = "default") -> Optional[StravaPreferences]:
        """Get user's Strava preferences."""
        ...

    async def save_strava_preferences(self, preferences: StravaPreferences) -> None:
        """Save user's Strava preferences."""
        ...

    async def get_activity_sync_status(self, local_activity_id: str) -> Optional[StravaSyncStatus]:
        """Get sync status for an activity."""
        ...

    async def update_activity_sync_status(
        self,
        local_activity_id: str,
        status: str,
        strava_activity_id: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update sync status for an activity."""
        ...


# =============================================================================
# Config Protocol
# =============================================================================


class StravaConfig(Protocol):
    """Protocol for Strava configuration."""

    @property
    def app_base_url(self) -> str:
        """Base URL for the application."""
        ...

    @property
    def strava_client_id(self) -> str:
        """Strava OAuth client ID."""
        ...

    @property
    def strava_client_secret(self) -> str:
        """Strava OAuth client secret."""
        ...


# =============================================================================
# Description Formatters
# =============================================================================


def format_strava_description_simple(
    analysis: WorkoutAnalysisResult,
    share_url: str,
) -> str:
    """
    Format workout analysis for Strava - simple, attractive preset.

    This is the default format that prioritizes simplicity and elegance.
    Less is more on Strava - a clean message invites curiosity without
    overwhelming the feed.

    Args:
        analysis: The workout analysis result
        share_url: URL to the full analysis page

    Returns:
        Formatted description string ready for Strava
    """
    # Score with color emoji
    score = analysis.overall_score or 0
    if score >= 80:
        score_emoji = "🟢"
    elif score >= 60:
        score_emoji = "🟡"
    else:
        score_emoji = "🔴"

    # One clean summary line (max 100 chars)
    summary = ""
    if analysis.summary:
        summary = analysis.summary[:100].rstrip('.')
    else:
        summary = "Great session"

    return f"""{score_emoji} {score}/100 · {summary}

---
📊 Analyzed by Training Analyzer
🔗 {share_url}"""


def format_strava_description_extended(
    analysis: WorkoutAnalysisResult,
    share_url: str,
) -> str:
    """
    Extended format with more details for users who enable it.

    This format includes additional metrics like training effect and
    recovery time when available.

    Args:
        analysis: The workout analysis result
        share_url: URL to the full analysis page

    Returns:
        Formatted description string with extended details
    """
    lines = []

    # Score line
    score = analysis.overall_score or 0
    if score >= 80:
        score_emoji = "🟢"
    elif score >= 60:
        score_emoji = "🟡"
    else:
        score_emoji = "🔴"

    # Truncate summary if needed
    if analysis.summary and len(analysis.summary) > 80:
        summary = analysis.summary[:80] + "..."
    elif analysis.summary:
        summary = analysis.summary
    else:
        summary = "Great session"

    lines.append(f"{score_emoji} {score}/100 · {summary}")

    # Training effect if available
    if analysis.training_effect_score is not None:
        lines.append(f"\n📈 Training Effect: {analysis.training_effect_score:.1f}")

    # Recovery if available
    if analysis.recovery_hours is not None:
        lines.append(f"⏱️ Recovery: {analysis.recovery_hours}h")

    # Footer
    lines.append("\n---")
    lines.append("📊 Analyzed by Training Analyzer")
    lines.append(f"🔗 {share_url}")

    return "\n".join(lines)


def format_strava_description_custom(
    analysis: WorkoutAnalysisResult,
    share_url: str,
    preferences: StravaPreferences,
) -> str:
    """
    Custom format based on user preferences.

    Allows granular control over what's included in the description.

    Args:
        analysis: The workout analysis result
        share_url: URL to the full analysis page
        preferences: User's Strava preferences

    Returns:
        Formatted description based on preferences
    """
    lines = []

    # Score line (always included if include_score)
    if preferences.include_score:
        score = analysis.overall_score or 0
        if score >= 80:
            score_emoji = "🟢"
        elif score >= 60:
            score_emoji = "🟡"
        else:
            score_emoji = "🔴"

        if preferences.include_summary and analysis.summary:
            summary = analysis.summary[:80] + "..." if len(analysis.summary) > 80 else analysis.summary
            lines.append(f"{score_emoji} {score}/100 · {summary}")
        else:
            lines.append(f"{score_emoji} {score}/100")
    elif preferences.include_summary and analysis.summary:
        summary = analysis.summary[:100] if len(analysis.summary) > 100 else analysis.summary
        lines.append(summary)

    # Training effect if enabled and available
    if preferences.include_training_effect and analysis.training_effect_score is not None:
        if lines:
            lines.append("")
        lines.append(f"📈 Training Effect: {analysis.training_effect_score:.1f}")

    # Recovery if enabled and available
    if preferences.include_recovery and analysis.recovery_hours is not None:
        lines.append(f"⏱️ Recovery: {analysis.recovery_hours}h")

    # Footer
    if lines:
        lines.append("\n---")

    # Custom footer or default
    if preferences.custom_footer:
        lines.append(preferences.custom_footer)
    else:
        lines.append("📊 Analyzed by Training Analyzer")

    lines.append(f"🔗 {share_url}")

    return "\n".join(lines)


# =============================================================================
# Strava Sync Service
# =============================================================================


class StravaService(BaseService):
    """
    Service for syncing workout analysis to Strava.

    This service orchestrates:
    - Formatting analysis for Strava descriptions
    - Syncing to Strava via API
    - Managing sync status
    - Handling user preferences
    """

    DEFAULT_BASE_URL = "https://training-analyzer.app"

    def __init__(
        self,
        db: StravaDatabase,
        config: Optional[StravaConfig] = None,
        cache: Optional[CacheProtocol] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialize the Strava service.

        Args:
            db: Database for storing credentials and sync status
            config: Application configuration
            cache: Optional cache for performance
            logger: Optional logger instance
        """
        super().__init__(cache=cache, logger=logger)
        self._db = db
        self._config = config

    @property
    def db(self) -> StravaDatabase:
        """Get the database instance."""
        return self._db

    @property
    def config(self) -> Optional[StravaConfig]:
        """Get the config instance."""
        return self._config

    def _generate_share_url(self, activity_id: str) -> str:
        """
        Generate shareable URL for workout analysis.

        Args:
            activity_id: Local activity ID

        Returns:
            Full URL to the shareable analysis page
        """
        base_url = self.DEFAULT_BASE_URL
        if self._config and hasattr(self._config, 'app_base_url') and self._config.app_base_url:
            base_url = self._config.app_base_url.rstrip('/')
        return f"{base_url}/s/{activity_id}"

    async def get_strava_client(self, user_id: str = "default") -> Optional[StravaClient]:
        """
        Get an authenticated Strava client.

        Args:
            user_id: User ID for credentials lookup

        Returns:
            Authenticated StravaClient or None if not connected
        """
        credentials = await self._db.get_strava_credentials(user_id)
        if not credentials:
            self.logger.warning(f"No Strava credentials found for user {user_id}")
            return None

        # Check if token needs refresh
        if credentials.needs_refresh:
            self.logger.info(f"Refreshing Strava token for user {user_id}")
            # Token refresh would be handled by StravaOAuthFlow
            # For now, we just log and return the client
            # In production, integrate with OAuth flow for refresh

        return StravaClient(credentials)

    async def format_description(
        self,
        analysis: WorkoutAnalysisResult,
        local_activity_id: str,
        user_id: str = "default",
    ) -> str:
        """
        Format workout analysis for Strava description.

        Args:
            analysis: The workout analysis result
            local_activity_id: Local activity ID for share URL
            user_id: User ID for preferences lookup

        Returns:
            Formatted description string
        """
        share_url = self._generate_share_url(local_activity_id)
        preferences = await self._db.get_strava_preferences(user_id)

        if preferences is None:
            # Use simple format as default
            return format_strava_description_simple(analysis, share_url)

        if preferences.use_extended_format:
            return format_strava_description_extended(analysis, share_url)

        # Use custom format based on preferences
        return format_strava_description_custom(analysis, share_url, preferences)

    async def sync_activity_to_strava(
        self,
        local_activity_id: str,
        strava_activity_id: int,
        analysis: WorkoutAnalysisResult,
        user_id: str = "default",
    ) -> bool:
        """
        Sync workout analysis to Strava activity.

        This method:
        1. Generates a share URL
        2. Formats the description based on user preferences
        3. Updates the Strava activity description
        4. Updates the local sync status

        Note: The Strava API APPENDS to existing descriptions when using
        the update endpoint, so our content will be added below any
        existing description.

        Args:
            local_activity_id: Local activity ID
            strava_activity_id: Strava activity ID to update
            analysis: The workout analysis result
            user_id: User ID for credentials/preferences

        Returns:
            True if sync was successful, False otherwise
        """
        try:
            # 1. Get preferences
            preferences = await self._db.get_strava_preferences(user_id)
            if preferences and not preferences.auto_update_description:
                self.logger.info(
                    f"Auto-update disabled for user {user_id}, skipping sync for {local_activity_id}"
                )
                return False

            # 2. Generate share URL
            share_url = self._generate_share_url(local_activity_id)

            # 3. Format description based on preferences
            if preferences is None:
                content = format_strava_description_simple(analysis, share_url)
            elif preferences.use_extended_format:
                content = format_strava_description_extended(analysis, share_url)
            else:
                content = format_strava_description_custom(analysis, share_url, preferences)

            # 4. Get Strava client with credentials
            client = await self.get_strava_client(user_id)
            if not client:
                self.logger.error(f"No Strava client available for user {user_id}")
                await self._db.update_activity_sync_status(
                    local_activity_id,
                    "failed",
                    strava_activity_id=strava_activity_id,
                    error_message="No Strava credentials available",
                )
                return False

            # 5. Update activity description
            await client._request(
                "PUT",
                f"/activities/{strava_activity_id}",
                json_data={"description": content},
            )
            self.logger.info(
                f"Successfully updated Strava activity {strava_activity_id} "
                f"with analysis for {local_activity_id}"
            )

            # 6. Update sync status
            await self._db.update_activity_sync_status(
                local_activity_id,
                "synced",
                strava_activity_id=strava_activity_id,
            )

            return True

        except Exception as e:
            self.logger.error(
                f"Failed to sync activity {local_activity_id} to Strava: {e}"
            )
            await self._db.update_activity_sync_status(
                local_activity_id,
                "failed",
                strava_activity_id=strava_activity_id,
                error_message=str(e),
            )
            return False

    async def get_sync_status(self, local_activity_id: str) -> Optional[StravaSyncStatus]:
        """
        Get the sync status for an activity.

        Args:
            local_activity_id: Local activity ID

        Returns:
            Sync status or None if not found
        """
        return await self._db.get_activity_sync_status(local_activity_id)

    async def get_preferences(self, user_id: str = "default") -> StravaPreferences:
        """
        Get Strava preferences for a user.

        Args:
            user_id: User ID

        Returns:
            User's preferences or defaults
        """
        preferences = await self._db.get_strava_preferences(user_id)
        if preferences is None:
            return StravaPreferences(user_id=user_id)
        return preferences

    async def update_preferences(
        self,
        preferences: StravaPreferences,
    ) -> StravaPreferences:
        """
        Update Strava preferences for a user.

        Args:
            preferences: New preferences to save

        Returns:
            Updated preferences
        """
        preferences.updated_at = datetime.utcnow()
        await self._db.save_strava_preferences(preferences)
        return preferences

    async def is_connected(self, user_id: str = "default") -> bool:
        """
        Check if user has connected Strava.

        Args:
            user_id: User ID

        Returns:
            True if Strava is connected with valid credentials
        """
        credentials = await self._db.get_strava_credentials(user_id)
        return credentials is not None and not credentials.is_expired
