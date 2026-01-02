"""User preferences API routes.

Provides endpoints for managing user preferences including:
- GET /preferences - Get current user preferences
- PUT /preferences - Update user preferences
- POST /preferences/toggle-beginner-mode - Toggle beginner mode
"""

import logging
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..middleware.auth import CurrentUser, get_current_user
from ...services.preferences_service import (
    PreferencesService,
    UserPreferences,
    get_preferences_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/preferences", tags=["preferences"])


# Type aliases
IntensityScale = Literal["hr", "rpe", "pace"]


# Request/Response Models
class UserPreferencesResponse(BaseModel):
    """Response model for user preferences."""

    user_id: str
    beginner_mode_enabled: bool
    beginner_mode_start_date: Optional[str] = None
    show_hr_metrics: bool
    show_advanced_metrics: bool
    preferred_intensity_scale: IntensityScale
    weekly_mileage_cap_enabled: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_preferences(cls, prefs: UserPreferences) -> "UserPreferencesResponse":
        """Create response from UserPreferences model."""
        return cls(
            user_id=prefs.user_id,
            beginner_mode_enabled=prefs.beginner_mode_enabled,
            beginner_mode_start_date=prefs.beginner_mode_start_date,
            show_hr_metrics=prefs.show_hr_metrics,
            show_advanced_metrics=prefs.show_advanced_metrics,
            preferred_intensity_scale=prefs.preferred_intensity_scale,
            weekly_mileage_cap_enabled=prefs.weekly_mileage_cap_enabled,
            created_at=prefs.created_at,
            updated_at=prefs.updated_at,
        )


class UpdatePreferencesRequest(BaseModel):
    """Request model for updating user preferences."""

    beginner_mode_enabled: Optional[bool] = Field(
        default=None,
        description="Enable beginner mode for simplified UI",
    )
    show_hr_metrics: Optional[bool] = Field(
        default=None,
        description="Show heart rate metrics in the dashboard",
    )
    show_advanced_metrics: Optional[bool] = Field(
        default=None,
        description="Show advanced training metrics (CTL, ATL, TSB)",
    )
    preferred_intensity_scale: Optional[IntensityScale] = Field(
        default=None,
        description="Preferred intensity scale: hr (heart rate), rpe (perceived effort), or pace",
    )
    weekly_mileage_cap_enabled: Optional[bool] = Field(
        default=None,
        description="Enable weekly mileage cap warnings",
    )


class ToggleBeginnerModeResponse(BaseModel):
    """Response model for toggling beginner mode."""

    beginner_mode_enabled: bool
    message: str


class BeginnerModeStatusResponse(BaseModel):
    """Response model for beginner mode status."""

    enabled: bool
    days_in_beginner_mode: Optional[int] = None
    start_date: Optional[str] = None


@router.get("", response_model=UserPreferencesResponse)
async def get_preferences(
    current_user: CurrentUser = Depends(get_current_user),
    preferences_service: PreferencesService = Depends(get_preferences_service),
) -> UserPreferencesResponse:
    """Get current user preferences.

    Returns the user's preferences, creating defaults if they don't exist.
    """
    try:
        prefs = preferences_service.get_preferences(current_user.user_id)
        return UserPreferencesResponse.from_preferences(prefs)
    except Exception as e:
        logger.error(f"Error getting preferences for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve preferences",
        )


@router.put("", response_model=UserPreferencesResponse)
async def update_preferences(
    request: UpdatePreferencesRequest,
    current_user: CurrentUser = Depends(get_current_user),
    preferences_service: PreferencesService = Depends(get_preferences_service),
) -> UserPreferencesResponse:
    """Update user preferences.

    Updates only the fields that are provided in the request.
    """
    try:
        prefs = preferences_service.update_preferences(
            user_id=current_user.user_id,
            beginner_mode_enabled=request.beginner_mode_enabled,
            show_hr_metrics=request.show_hr_metrics,
            show_advanced_metrics=request.show_advanced_metrics,
            preferred_intensity_scale=request.preferred_intensity_scale,
            weekly_mileage_cap_enabled=request.weekly_mileage_cap_enabled,
        )
        return UserPreferencesResponse.from_preferences(prefs)
    except Exception as e:
        logger.error(f"Error updating preferences for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences",
        )


@router.post("/toggle-beginner-mode", response_model=ToggleBeginnerModeResponse)
async def toggle_beginner_mode(
    current_user: CurrentUser = Depends(get_current_user),
    preferences_service: PreferencesService = Depends(get_preferences_service),
) -> ToggleBeginnerModeResponse:
    """Toggle beginner mode on/off.

    Returns the new state of beginner mode after toggling.
    """
    try:
        new_state = preferences_service.toggle_beginner_mode(current_user.user_id)

        if new_state:
            message = "Beginner mode enabled. The interface has been simplified."
        else:
            message = "Beginner mode disabled. Full metrics are now visible."

        return ToggleBeginnerModeResponse(
            beginner_mode_enabled=new_state,
            message=message,
        )
    except Exception as e:
        logger.error(
            f"Error toggling beginner mode for user {current_user.user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle beginner mode",
        )


@router.get("/beginner-mode-status", response_model=BeginnerModeStatusResponse)
async def get_beginner_mode_status(
    current_user: CurrentUser = Depends(get_current_user),
    preferences_service: PreferencesService = Depends(get_preferences_service),
) -> BeginnerModeStatusResponse:
    """Get beginner mode status for the current user.

    Returns whether beginner mode is enabled and how long it's been active.
    """
    try:
        prefs = preferences_service.get_preferences(current_user.user_id)
        days = preferences_service.get_beginner_mode_days(current_user.user_id)

        return BeginnerModeStatusResponse(
            enabled=prefs.beginner_mode_enabled,
            days_in_beginner_mode=days,
            start_date=prefs.beginner_mode_start_date,
        )
    except Exception as e:
        logger.error(
            f"Error getting beginner mode status for user {current_user.user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve beginner mode status",
        )
