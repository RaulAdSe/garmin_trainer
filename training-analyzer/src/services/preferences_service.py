"""User preferences service for managing beginner mode and other settings.

This service handles CRUD operations for user preferences including:
- Beginner mode toggle
- Intensity scale preferences
- Metric visibility settings
"""

import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional, Literal

from ..db.database import TrainingDatabase

logger = logging.getLogger(__name__)

IntensityScale = Literal["hr", "rpe", "pace"]


@dataclass
class UserPreferences:
    """User preferences data model."""

    user_id: str
    beginner_mode_enabled: bool = False
    beginner_mode_start_date: Optional[str] = None
    show_hr_metrics: bool = True
    show_advanced_metrics: bool = True
    preferred_intensity_scale: IntensityScale = "hr"
    weekly_mileage_cap_enabled: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "beginner_mode_enabled": self.beginner_mode_enabled,
            "beginner_mode_start_date": self.beginner_mode_start_date,
            "show_hr_metrics": self.show_hr_metrics,
            "show_advanced_metrics": self.show_advanced_metrics,
            "preferred_intensity_scale": self.preferred_intensity_scale,
            "weekly_mileage_cap_enabled": self.weekly_mileage_cap_enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row: dict) -> "UserPreferences":
        """Create UserPreferences from database row."""
        return cls(
            user_id=row["user_id"],
            beginner_mode_enabled=bool(row.get("beginner_mode_enabled", 0)),
            beginner_mode_start_date=row.get("beginner_mode_start_date"),
            show_hr_metrics=bool(row.get("show_hr_metrics", 1)),
            show_advanced_metrics=bool(row.get("show_advanced_metrics", 1)),
            preferred_intensity_scale=row.get("preferred_intensity_scale", "hr"),
            weekly_mileage_cap_enabled=bool(row.get("weekly_mileage_cap_enabled", 0)),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )


class PreferencesService:
    """Service for managing user preferences.

    Handles persistence and retrieval of user preference settings
    including beginner mode, metric visibility, and intensity scales.
    """

    def __init__(self, db: Optional[TrainingDatabase] = None):
        """Initialize the preferences service.

        Args:
            db: Optional TrainingDatabase instance. If not provided,
                a new instance will be created.
        """
        self._db = db or TrainingDatabase(use_pool=True)

    def get_preferences(self, user_id: str) -> UserPreferences:
        """Get user preferences, creating defaults if not exists.

        Args:
            user_id: The user's unique identifier.

        Returns:
            UserPreferences object with current settings.
        """
        with self._db._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM user_preferences WHERE user_id = ?",
                (user_id,),
            ).fetchone()

            if row:
                return UserPreferences.from_row(dict(row))

            # Create default preferences for new user
            return self._create_default_preferences(user_id)

    def _create_default_preferences(self, user_id: str) -> UserPreferences:
        """Create default preferences for a new user.

        Args:
            user_id: The user's unique identifier.

        Returns:
            Newly created UserPreferences with defaults.
        """
        now = datetime.now(timezone.utc).isoformat()
        prefs = UserPreferences(
            user_id=user_id,
            beginner_mode_enabled=False,
            beginner_mode_start_date=None,
            show_hr_metrics=True,
            show_advanced_metrics=True,
            preferred_intensity_scale="hr",
            weekly_mileage_cap_enabled=False,
            created_at=now,
            updated_at=now,
        )

        with self._db._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO user_preferences (
                    user_id, beginner_mode_enabled, beginner_mode_start_date,
                    show_hr_metrics, show_advanced_metrics, preferred_intensity_scale,
                    weekly_mileage_cap_enabled, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prefs.user_id,
                    int(prefs.beginner_mode_enabled),
                    prefs.beginner_mode_start_date,
                    int(prefs.show_hr_metrics),
                    int(prefs.show_advanced_metrics),
                    prefs.preferred_intensity_scale,
                    int(prefs.weekly_mileage_cap_enabled),
                    prefs.created_at,
                    prefs.updated_at,
                ),
            )

        logger.info(f"Created default preferences for user {user_id}")
        return prefs

    def update_preferences(
        self,
        user_id: str,
        beginner_mode_enabled: Optional[bool] = None,
        show_hr_metrics: Optional[bool] = None,
        show_advanced_metrics: Optional[bool] = None,
        preferred_intensity_scale: Optional[IntensityScale] = None,
        weekly_mileage_cap_enabled: Optional[bool] = None,
    ) -> UserPreferences:
        """Update user preferences with provided values.

        Only updates fields that are explicitly provided (not None).
        Automatically manages beginner_mode_start_date when toggling beginner mode.

        Args:
            user_id: The user's unique identifier.
            beginner_mode_enabled: Enable/disable beginner mode.
            show_hr_metrics: Show/hide heart rate metrics.
            show_advanced_metrics: Show/hide advanced metrics.
            preferred_intensity_scale: Preferred intensity scale (hr, rpe, pace).
            weekly_mileage_cap_enabled: Enable/disable weekly mileage cap.

        Returns:
            Updated UserPreferences object.
        """
        # Get current preferences
        current = self.get_preferences(user_id)
        now = datetime.now(timezone.utc).isoformat()

        # Apply updates
        new_beginner_mode = (
            beginner_mode_enabled
            if beginner_mode_enabled is not None
            else current.beginner_mode_enabled
        )
        new_show_hr = (
            show_hr_metrics
            if show_hr_metrics is not None
            else current.show_hr_metrics
        )
        new_show_advanced = (
            show_advanced_metrics
            if show_advanced_metrics is not None
            else current.show_advanced_metrics
        )
        new_intensity_scale = (
            preferred_intensity_scale
            if preferred_intensity_scale is not None
            else current.preferred_intensity_scale
        )
        new_mileage_cap = (
            weekly_mileage_cap_enabled
            if weekly_mileage_cap_enabled is not None
            else current.weekly_mileage_cap_enabled
        )

        # Handle beginner mode start date
        beginner_mode_start_date = current.beginner_mode_start_date
        if beginner_mode_enabled is not None:
            if beginner_mode_enabled and not current.beginner_mode_enabled:
                # Turning on beginner mode - set start date
                beginner_mode_start_date = now
                logger.info(f"User {user_id} enabled beginner mode")
            elif not beginner_mode_enabled and current.beginner_mode_enabled:
                # Turning off beginner mode - clear start date
                beginner_mode_start_date = None
                logger.info(f"User {user_id} disabled beginner mode")

        with self._db._get_connection() as conn:
            conn.execute(
                """
                UPDATE user_preferences SET
                    beginner_mode_enabled = ?,
                    beginner_mode_start_date = ?,
                    show_hr_metrics = ?,
                    show_advanced_metrics = ?,
                    preferred_intensity_scale = ?,
                    weekly_mileage_cap_enabled = ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (
                    int(new_beginner_mode),
                    beginner_mode_start_date,
                    int(new_show_hr),
                    int(new_show_advanced),
                    new_intensity_scale,
                    int(new_mileage_cap),
                    now,
                    user_id,
                ),
            )

        return UserPreferences(
            user_id=user_id,
            beginner_mode_enabled=new_beginner_mode,
            beginner_mode_start_date=beginner_mode_start_date,
            show_hr_metrics=new_show_hr,
            show_advanced_metrics=new_show_advanced,
            preferred_intensity_scale=new_intensity_scale,
            weekly_mileage_cap_enabled=new_mileage_cap,
            created_at=current.created_at,
            updated_at=now,
        )

    def toggle_beginner_mode(self, user_id: str) -> bool:
        """Toggle beginner mode on/off for a user.

        Args:
            user_id: The user's unique identifier.

        Returns:
            New state of beginner mode (True = enabled).
        """
        current = self.get_preferences(user_id)
        new_state = not current.beginner_mode_enabled

        self.update_preferences(user_id, beginner_mode_enabled=new_state)

        logger.info(
            f"Toggled beginner mode for user {user_id}: "
            f"{'enabled' if new_state else 'disabled'}"
        )

        return new_state

    def is_beginner_mode_enabled(self, user_id: str) -> bool:
        """Check if beginner mode is enabled for a user.

        Args:
            user_id: The user's unique identifier.

        Returns:
            True if beginner mode is enabled.
        """
        prefs = self.get_preferences(user_id)
        return prefs.beginner_mode_enabled

    def get_beginner_mode_days(self, user_id: str) -> Optional[int]:
        """Get the number of days user has been in beginner mode.

        Args:
            user_id: The user's unique identifier.

        Returns:
            Number of days in beginner mode, or None if not enabled.
        """
        prefs = self.get_preferences(user_id)
        if not prefs.beginner_mode_enabled or not prefs.beginner_mode_start_date:
            return None

        try:
            start = datetime.fromisoformat(
                prefs.beginner_mode_start_date.replace("Z", "+00:00")
            )
            now = datetime.now(timezone.utc)
            return (now - start).days
        except (ValueError, TypeError):
            return None


# Module-level singleton
_preferences_service: Optional[PreferencesService] = None


def get_preferences_service() -> PreferencesService:
    """Get or create the preferences service singleton."""
    global _preferences_service
    if _preferences_service is None:
        _preferences_service = PreferencesService()
    return _preferences_service
