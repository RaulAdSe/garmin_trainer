"""Gamification data models for achievements and progress tracking."""

from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class AchievementCategory(str, Enum):
    """Categories for achievements."""
    CONSISTENCY = "consistency"
    PERFORMANCE = "performance"
    EXECUTION = "execution"
    MILESTONE = "milestone"
    EARLY_WIN = "early_win"  # Guaranteed early achievements for new users


class AchievementRarity(str, Enum):
    """Rarity levels for achievements."""
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class Achievement(BaseModel):
    """Achievement definition model."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str = Field(..., description="Unique achievement identifier")
    name: str = Field(..., description="Display name of the achievement")
    description: str = Field(..., description="Description of how to unlock")
    category: AchievementCategory = Field(..., description="Achievement category")
    icon: str = Field(..., description="Icon/emoji for the achievement")
    xp_value: int = Field(default=25, description="XP awarded when unlocked")
    rarity: AchievementRarity = Field(default=AchievementRarity.COMMON, description="Rarity level")
    condition_type: Optional[str] = Field(None, description="Type of condition to check")
    condition_value: Optional[str] = Field(None, description="Value for the condition")
    display_order: int = Field(default=0, description="Order for display")
    created_at: Optional[datetime] = Field(None, description="When achievement was defined")


class UserAchievement(BaseModel):
    """User's unlocked achievement record."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: int = Field(..., description="Record ID")
    achievement_id: str = Field(..., description="Reference to achievement")
    unlocked_at: datetime = Field(..., description="When the achievement was unlocked")
    workout_id: Optional[str] = Field(None, description="Workout that triggered unlock")
    metadata_json: Optional[str] = Field(None, description="Additional unlock metadata")


class AchievementUnlock(BaseModel):
    """Response model for achievement unlock event."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    achievement: Achievement = Field(..., description="The achievement that was unlocked")
    unlocked_at: datetime = Field(..., description="When it was unlocked")
    is_new: bool = Field(default=True, description="Whether this is a new unlock")


class AchievementWithStatus(BaseModel):
    """Achievement with its unlock status for the user."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    achievement: Achievement = Field(..., description="The achievement")
    unlocked: bool = Field(default=False, description="Whether user has unlocked it")
    unlocked_at: Optional[datetime] = Field(None, description="When it was unlocked")


class LevelInfo(BaseModel):
    """Information about a user's level."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    level: int = Field(..., description="Current level")
    xp_required: int = Field(..., description="Total XP required for this level")
    xp_for_next: int = Field(..., description="XP needed to reach next level")
    xp_in_level: int = Field(..., description="XP earned within current level")
    progress_percent: float = Field(..., description="Progress to next level (0-100)")


class StreakInfo(BaseModel):
    """Information about user's workout streak."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    current: int = Field(default=0, description="Current streak in days")
    longest: int = Field(default=0, description="Longest streak achieved")
    freeze_tokens: int = Field(default=0, description="Streak freeze tokens available")
    is_protected: bool = Field(default=False, description="Whether streak is currently protected")
    last_activity_date: Optional[str] = Field(None, description="Date of last activity")


class LevelReward(BaseModel):
    """Reward unlocked at a specific level."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    level: int = Field(..., description="Level that unlocks this reward")
    name: str = Field(..., description="Short name for the level tier")
    title: str = Field(..., description="User title at this level")
    unlocks: List[str] = Field(default_factory=list, description="Features unlocked")
    description: str = Field(..., description="Description of what's unlocked")


class UserProgress(BaseModel):
    """User's overall gamification progress."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    user_id: str = Field(default="default", description="User identifier")
    total_xp: int = Field(default=0, description="Total XP earned")
    level: LevelInfo = Field(..., description="Current level information")
    streak: StreakInfo = Field(..., description="Streak information")
    achievements_unlocked: int = Field(default=0, description="Number of achievements unlocked")
    updated_at: Optional[datetime] = Field(None, description="Last update time")
    title: str = Field(default="Training Rookie", description="User's current title")
    unlocked_features: List[str] = Field(default_factory=list, description="Features unlocked")
    next_reward: Optional[LevelReward] = Field(None, description="Next level reward to unlock")


class CheckAchievementsRequest(BaseModel):
    """Request model for checking achievements."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    workout_id: Optional[str] = Field(None, description="Optional workout ID for context")
    activity_date: Optional[str] = Field(None, description="Date of activity (YYYY-MM-DD)")


class EarlyAchievementContext(BaseModel):
    """Context for checking early win achievements."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # Login context
    is_first_login: bool = Field(default=False, description="First login after device connection")
    login_hour: Optional[int] = Field(None, description="Hour of login (0-23)")

    # Profile context
    profile_complete: bool = Field(default=False, description="User has completed profile/preferences")

    # Workout context
    has_first_workout: bool = Field(default=False, description="User has logged first workout")

    # Navigation context
    pages_visited: List[str] = Field(default_factory=list, description="List of pages visited")
    viewed_workout_details: bool = Field(default=False, description="Has viewed workout details")


class CheckEarlyAchievementsRequest(BaseModel):
    """Request model for checking early win achievements."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    context: EarlyAchievementContext = Field(..., description="Context for early achievement checking")


class CheckAchievementsResponse(BaseModel):
    """Response model for achievement check."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    new_achievements: List[AchievementUnlock] = Field(
        default_factory=list,
        description="Newly unlocked achievements"
    )
    xp_earned: int = Field(default=0, description="Total XP earned from new achievements")
    level_up: bool = Field(default=False, description="Whether user leveled up")
    new_level: Optional[int] = Field(None, description="New level if leveled up")
    streak_updated: bool = Field(default=False, description="Whether streak was updated")
    current_streak: int = Field(default=0, description="Current streak value")


class CheckEarlyAchievementsResponse(BaseModel):
    """Response model for early win achievement check."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    new_achievements: List[AchievementUnlock] = Field(
        default_factory=list,
        description="Newly unlocked early achievements"
    )
    xp_earned: int = Field(default=0, description="Total XP earned from new achievements")
    level_up: bool = Field(default=False, description="Whether user leveled up")
    new_level: Optional[int] = Field(None, description="New level if leveled up")
    is_first_achievement: bool = Field(
        default=False,
        description="Whether any of these is the user's very first achievement (triggers extra celebration)"
    )
    total_achievements_unlocked: int = Field(
        default=0,
        description="Total number of achievements now unlocked"
    )


# =============================================================================
# Helper Functions
# =============================================================================

def get_xp_for_level(level: int) -> int:
    """
    Calculate XP required to reach a given level.

    Uses a quadratic formula: XP = 100 * level^1.5
    Level 1: 0 XP (starting point)
    Level 2: 100 XP
    Level 3: ~245 XP
    Level 5: ~559 XP
    Level 10: ~1000 XP

    Args:
        level: The target level

    Returns:
        Total XP required to reach that level
    """
    if level <= 1:
        return 0
    return int(100 * (level ** 1.5))


def calculate_level(xp: int) -> LevelInfo:
    """
    Calculate level information from total XP.

    Args:
        xp: Total XP earned

    Returns:
        LevelInfo with current level and progress
    """
    if xp <= 0:
        return LevelInfo(
            level=1,
            xp_required=0,
            xp_for_next=100,
            xp_in_level=0,
            progress_percent=0.0,
        )

    # Find current level
    level = 1
    while get_xp_for_level(level + 1) <= xp:
        level += 1

    xp_required = get_xp_for_level(level)
    xp_for_next_level = get_xp_for_level(level + 1)
    xp_needed = xp_for_next_level - xp_required
    xp_in_level = xp - xp_required

    progress = (xp_in_level / xp_needed * 100) if xp_needed > 0 else 100.0

    return LevelInfo(
        level=level,
        xp_required=xp_required,
        xp_for_next=xp_for_next_level - xp,
        xp_in_level=xp_in_level,
        progress_percent=round(progress, 1),
    )
