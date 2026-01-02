"""Personal Records (PR) data models for tracking athletic achievements."""

from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class PRType(str, Enum):
    """Types of personal records that can be tracked."""
    PACE = "pace"              # Fastest pace (min/km) for a given distance
    DISTANCE = "distance"       # Longest distance run
    DURATION = "duration"       # Longest workout duration
    ELEVATION = "elevation"     # Most elevation gain in a single workout
    POWER = "power"            # Highest average power (cycling/running power)


class ActivityType(str, Enum):
    """Activity types for PR categorization."""
    RUNNING = "running"
    TRAIL_RUNNING = "trail_running"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    WALKING = "walking"
    HIKING = "hiking"
    OTHER = "other"


class PersonalRecord(BaseModel):
    """Personal record model representing a user's best performance."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str = Field(..., description="Unique PR identifier")
    user_id: str = Field(default="default", description="User identifier")
    pr_type: PRType = Field(..., description="Type of personal record")
    activity_type: ActivityType = Field(..., description="Type of activity")
    value: float = Field(..., description="PR value (pace in sec/km, distance in m, etc.)")
    unit: str = Field(..., description="Unit of measurement")
    workout_id: str = Field(..., description="ID of the workout where PR was achieved")
    achieved_at: datetime = Field(..., description="When the PR was achieved")
    previous_value: Optional[float] = Field(None, description="Previous best value")
    improvement: Optional[float] = Field(None, description="Improvement amount")
    improvement_percent: Optional[float] = Field(None, description="Improvement percentage")
    workout_name: Optional[str] = Field(None, description="Name of the workout")
    workout_date: Optional[str] = Field(None, description="Date of the workout")


class PRDetectionResult(BaseModel):
    """Result of PR detection for a single workout."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    new_prs: List[PersonalRecord] = Field(
        default_factory=list,
        description="List of new PRs achieved in this workout"
    )
    near_prs: List[dict] = Field(
        default_factory=list,
        description="Near PRs (within threshold of beating current PR)"
    )
    workout_id: str = Field(..., description="ID of the analyzed workout")
    has_new_pr: bool = Field(default=False, description="Whether any new PR was achieved")


class PRSummary(BaseModel):
    """Summary of a user's personal records."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    total_prs: int = Field(default=0, description="Total number of PRs")
    recent_prs: int = Field(default=0, description="PRs in the last 30 days")
    prs_by_type: dict = Field(
        default_factory=dict,
        description="Count of PRs by type"
    )
    latest_pr: Optional[PersonalRecord] = Field(
        None,
        description="Most recently achieved PR"
    )


class PRComparisonResult(BaseModel):
    """Result of comparing a workout to existing PRs."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    workout_id: str = Field(..., description="ID of the workout being compared")
    comparisons: List[dict] = Field(
        default_factory=list,
        description="Comparisons to existing PRs"
    )
    potential_prs: List[dict] = Field(
        default_factory=list,
        description="Potential PRs if certain thresholds are met"
    )


# =============================================================================
# PR Thresholds Configuration (from DEEP_ANALYSIS.md)
# =============================================================================

class PRThresholds:
    """Threshold configuration for PR detection."""

    # Running pace PRs: minimum distance required
    PACE_MIN_DISTANCE_M = 1000  # 1km minimum

    # Running distance PRs: minimum duration required
    DISTANCE_MIN_DURATION_MIN = 10  # 10 minutes minimum

    # Elevation PRs: minimum distance required
    ELEVATION_MIN_DISTANCE_M = 3000  # 3km minimum

    # Near-PR threshold (percentage within current PR)
    NEAR_PR_THRESHOLD_PERCENT = 5.0

    # Standard distances for pace PRs (in meters)
    PACE_DISTANCES = {
        "1km": 1000,
        "5km": 5000,
        "10km": 10000,
        "half_marathon": 21097,
        "marathon": 42195,
    }


class PRListRequest(BaseModel):
    """Request model for listing PRs."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    pr_type: Optional[PRType] = Field(None, description="Filter by PR type")
    activity_type: Optional[ActivityType] = Field(None, description="Filter by activity type")
    limit: int = Field(default=50, description="Maximum number of results")
    offset: int = Field(default=0, description="Offset for pagination")


class PRListResponse(BaseModel):
    """Response model for listing PRs."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    personal_records: List[PersonalRecord] = Field(
        ..., description="List of personal records"
    )
    total: int = Field(..., description="Total number of PRs")
    summary: PRSummary = Field(..., description="Summary of PRs")


class RecentPRsResponse(BaseModel):
    """Response model for recent PRs."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    personal_records: List[PersonalRecord] = Field(
        ..., description="List of recent personal records"
    )
    count: int = Field(..., description="Number of recent PRs")
    days: int = Field(default=30, description="Number of days looked back")
