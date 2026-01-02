"""
Social Proof service for community engagement features.

Provides aggregated statistics and percentile rankings to create
a sense of community and social validation for users.

For demo/development, uses simulated data that looks realistic.
In production, this would use cached/aggregated data from the database.
"""

import logging
import random
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


# =============================================================================
# Models
# =============================================================================


class PercentileRanking(BaseModel):
    """User's percentile ranking in a category."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    category: str = Field(..., description="Category name (pace, streak, level)")
    percentile: int = Field(
        ..., ge=0, le=100, description="Percentile ranking (0-100)"
    )
    label: str = Field(..., description="Human-readable label")
    value: Optional[float] = Field(
        None, description="User's actual value for this category"
    )
    unit: Optional[str] = Field(None, description="Unit for the value")


class CommunityActivity(BaseModel):
    """Recent community activity item."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    activity_type: str = Field(..., description="Type of activity")
    count: int = Field(..., description="Number of occurrences")
    time_ago: str = Field(..., description="Human-readable time ago")


class SocialProofStats(BaseModel):
    """Aggregated social proof statistics."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    athletes_trained_today: int = Field(
        ..., description="Count of athletes who trained today"
    )
    workouts_completed_today: int = Field(
        ..., description="Total workouts completed today"
    )
    athletes_training_now: int = Field(
        ..., description="Athletes currently training (approximate)"
    )

    # Optional percentile rankings (if user has data)
    pace_percentile: Optional[PercentileRanking] = Field(
        None, description="User's pace percentile"
    )
    streak_percentile: Optional[PercentileRanking] = Field(
        None, description="User's streak percentile"
    )
    level_percentile: Optional[PercentileRanking] = Field(
        None, description="User's level percentile"
    )

    # Community activity feed
    recent_activity: List[CommunityActivity] = Field(
        default_factory=list, description="Recent community activity"
    )

    # Timestamps
    generated_at: datetime = Field(
        default_factory=datetime.now, description="When stats were generated"
    )
    cache_ttl_seconds: int = Field(
        default=300, description="How long these stats are valid"
    )


# =============================================================================
# Service
# =============================================================================


class SocialProofService:
    """
    Service for social proof and community engagement features.

    For demo/development, generates realistic simulated data.
    In production, would use cached aggregates from the database.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the social proof service.

        Args:
            db_path: Path to SQLite database (for future production use)
        """
        self.db_path = db_path
        self._cache: Dict[str, Any] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(seconds=60)  # Cache for 60 seconds

    def get_social_proof_stats(
        self,
        user_level: Optional[int] = None,
        user_streak: Optional[int] = None,
        user_avg_pace: Optional[float] = None,
    ) -> SocialProofStats:
        """
        Get social proof statistics.

        Uses cached/aggregated data for performance.
        For demo purposes, generates realistic simulated data.

        Args:
            user_level: User's current level (for percentile calculation)
            user_streak: User's current streak (for percentile calculation)
            user_avg_pace: User's average pace in min/km (for percentile calculation)

        Returns:
            SocialProofStats with community data and optional percentiles
        """
        now = datetime.now()

        # Check cache
        if self._cache_time and now - self._cache_time < self._cache_ttl:
            stats = self._cache.get("stats")
            if stats:
                # Recalculate percentiles for this user
                return self._add_user_percentiles(
                    stats, user_level, user_streak, user_avg_pace
                )

        # Generate base community stats (simulated for demo)
        base_stats = self._generate_community_stats()

        # Cache the base stats
        self._cache["stats"] = base_stats
        self._cache_time = now

        # Add user-specific percentiles
        return self._add_user_percentiles(
            base_stats, user_level, user_streak, user_avg_pace
        )

    def _generate_community_stats(self) -> SocialProofStats:
        """
        Generate realistic community statistics.

        In production, this would query cached aggregates.
        For demo, generates believable numbers based on time of day.
        """
        now = datetime.now()
        hour = now.hour

        # Base athlete counts vary by time of day
        # Morning (5-9am) and evening (5-8pm) are peak times
        if 5 <= hour < 9:
            base_athletes = random.randint(180, 280)
            training_now = random.randint(25, 50)
        elif 17 <= hour < 21:
            base_athletes = random.randint(250, 400)
            training_now = random.randint(40, 80)
        elif 9 <= hour < 17:
            base_athletes = random.randint(120, 200)
            training_now = random.randint(15, 35)
        else:
            base_athletes = random.randint(50, 120)
            training_now = random.randint(5, 20)

        # Workouts completed is typically 1.2-1.5x athletes (some do multiple)
        workout_multiplier = random.uniform(1.2, 1.5)
        workouts_today = int(base_athletes * workout_multiplier)

        # Generate recent activity feed
        recent_activity = self._generate_recent_activity()

        return SocialProofStats(
            athletes_trained_today=base_athletes,
            workouts_completed_today=workouts_today,
            athletes_training_now=training_now,
            recent_activity=recent_activity,
            generated_at=now,
            cache_ttl_seconds=60,
        )

    def _generate_recent_activity(self) -> List[CommunityActivity]:
        """Generate recent community activity items."""
        activities = [
            CommunityActivity(
                activity_type="workout_completed",
                count=random.randint(5, 15),
                time_ago="just now",
            ),
            CommunityActivity(
                activity_type="achievement_unlocked",
                count=random.randint(2, 8),
                time_ago="in the last minute",
            ),
            CommunityActivity(
                activity_type="streak_continued",
                count=random.randint(8, 20),
                time_ago="in the last 5 minutes",
            ),
            CommunityActivity(
                activity_type="level_up",
                count=random.randint(1, 5),
                time_ago="in the last hour",
            ),
        ]
        return activities

    def _add_user_percentiles(
        self,
        stats: SocialProofStats,
        user_level: Optional[int],
        user_streak: Optional[int],
        user_avg_pace: Optional[float],
    ) -> SocialProofStats:
        """
        Add user-specific percentile rankings to stats.

        For demo, calculates approximate percentiles.
        In production, would use pre-computed percentile tables.
        """
        percentiles: Dict[str, Optional[PercentileRanking]] = {
            "pace_percentile": None,
            "streak_percentile": None,
            "level_percentile": None,
        }

        # Calculate pace percentile if user has pace data
        if user_avg_pace is not None and user_avg_pace > 0:
            # Pace: lower is better
            # Assume distribution: 4:00 = 99th, 5:00 = 80th, 6:00 = 50th, 7:00 = 25th
            if user_avg_pace <= 4.0:
                pace_pct = random.randint(95, 99)
            elif user_avg_pace <= 5.0:
                pace_pct = random.randint(75, 90)
            elif user_avg_pace <= 6.0:
                pace_pct = random.randint(45, 65)
            elif user_avg_pace <= 7.0:
                pace_pct = random.randint(20, 40)
            else:
                pace_pct = random.randint(5, 25)

            percentiles["pace_percentile"] = PercentileRanking(
                category="pace",
                percentile=pace_pct,
                label=f"faster than {pace_pct}% of athletes",
                value=user_avg_pace,
                unit="min/km",
            )

        # Calculate streak percentile
        if user_streak is not None and user_streak > 0:
            # Streak distribution: 30+ = 95th, 14+ = 80th, 7+ = 60th, 3+ = 40th
            if user_streak >= 30:
                streak_pct = random.randint(92, 99)
            elif user_streak >= 14:
                streak_pct = random.randint(75, 88)
            elif user_streak >= 7:
                streak_pct = random.randint(55, 72)
            elif user_streak >= 3:
                streak_pct = random.randint(35, 52)
            else:
                streak_pct = random.randint(15, 35)

            percentiles["streak_percentile"] = PercentileRanking(
                category="streak",
                percentile=streak_pct,
                label=f"longer streak than {streak_pct}% of athletes",
                value=float(user_streak),
                unit="days",
            )

        # Calculate level percentile
        if user_level is not None and user_level > 0:
            # Level distribution: 20+ = 95th, 10+ = 70th, 5+ = 45th, 3+ = 25th
            if user_level >= 20:
                level_pct = random.randint(92, 99)
            elif user_level >= 10:
                level_pct = random.randint(65, 82)
            elif user_level >= 5:
                level_pct = random.randint(40, 58)
            elif user_level >= 3:
                level_pct = random.randint(20, 38)
            else:
                level_pct = random.randint(5, 20)

            percentiles["level_percentile"] = PercentileRanking(
                category="level",
                percentile=level_pct,
                label=f"top {100 - level_pct}% by level",
                value=float(user_level),
                unit=None,
            )

        # Create new stats with percentiles
        return SocialProofStats(
            athletes_trained_today=stats.athletes_trained_today,
            workouts_completed_today=stats.workouts_completed_today,
            athletes_training_now=stats.athletes_training_now,
            pace_percentile=percentiles["pace_percentile"],
            streak_percentile=percentiles["streak_percentile"],
            level_percentile=percentiles["level_percentile"],
            recent_activity=stats.recent_activity,
            generated_at=stats.generated_at,
            cache_ttl_seconds=stats.cache_ttl_seconds,
        )
