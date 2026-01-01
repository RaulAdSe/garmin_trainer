"""
Achievement service for gamification features.

Handles:
- Achievement tracking and unlocking
- XP and level progression
- Streak tracking and management
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..db.schema import SCHEMA
from ..models.gamification import (
    Achievement,
    AchievementCategory,
    AchievementRarity,
    AchievementUnlock,
    AchievementWithStatus,
    CheckAchievementsResponse,
    LevelInfo,
    LevelReward,
    StreakInfo,
    UserProgress,
    calculate_level,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Default Achievement Definitions
# =============================================================================

DEFAULT_ACHIEVEMENTS: List[Dict[str, Any]] = [
    # Streak achievements
    {
        "id": "first_workout",
        "name": "First Steps",
        "description": "Complete your first workout",
        "category": "consistency",
        "icon": "🎯",
        "xp_value": 10,
        "rarity": "common",
        "condition_type": "workout_count",
        "condition_value": "1",
        "display_order": 1,
    },
    {
        "id": "streak_3",
        "name": "Getting Started",
        "description": "Maintain a 3-day workout streak",
        "category": "consistency",
        "icon": "🔥",
        "xp_value": 25,
        "rarity": "common",
        "condition_type": "streak",
        "condition_value": "3",
        "display_order": 2,
    },
    {
        "id": "streak_7",
        "name": "Week Warrior",
        "description": "Maintain a 7-day workout streak",
        "category": "consistency",
        "icon": "⚡",
        "xp_value": 50,
        "rarity": "common",
        "condition_type": "streak",
        "condition_value": "7",
        "display_order": 3,
    },
    {
        "id": "streak_14",
        "name": "Fortnight Fighter",
        "description": "Maintain a 14-day workout streak",
        "category": "consistency",
        "icon": "💪",
        "xp_value": 75,
        "rarity": "common",
        "condition_type": "streak",
        "condition_value": "14",
        "display_order": 4,
    },
    {
        "id": "streak_30",
        "name": "Monthly Master",
        "description": "Maintain a 30-day workout streak",
        "category": "consistency",
        "icon": "🏆",
        "xp_value": 100,
        "rarity": "rare",
        "condition_type": "streak",
        "condition_value": "30",
        "display_order": 5,
    },
    # VO2 Max achievements - Sports science based (relative improvements, not absolute)
    # Relative improvement achievements (achievable by anyone)
    {
        "id": "vo2max_first",
        "name": "Baseline Set",
        "description": "Record your first VO2 Max measurement",
        "category": "milestone",
        "icon": "📊",
        "xp_value": 25,
        "rarity": "common",
        "condition_type": "vo2max_baseline",
        "condition_value": "1",
        "display_order": 6,
    },
    {
        "id": "vo2max_up_3",
        "name": "Oxygen Rising",
        "description": "Improve your VO2 Max by 3% from baseline",
        "category": "performance",
        "icon": "📈",
        "xp_value": 50,
        "rarity": "common",
        "condition_type": "vo2max_improvement",
        "condition_value": "3",
        "display_order": 7,
    },
    {
        "id": "vo2max_up_5",
        "name": "Aerobic Gains",
        "description": "Improve your VO2 Max by 5% from baseline",
        "category": "performance",
        "icon": "💨",
        "xp_value": 75,
        "rarity": "rare",
        "condition_type": "vo2max_improvement",
        "condition_value": "5",
        "display_order": 8,
    },
    {
        "id": "vo2max_up_10",
        "name": "Cardio Transformer",
        "description": "Improve your VO2 Max by 10% from baseline",
        "category": "performance",
        "icon": "🫀",
        "xp_value": 100,
        "rarity": "epic",
        "condition_type": "vo2max_improvement",
        "condition_value": "10",
        "display_order": 9,
    },
    {
        "id": "vo2max_up_15",
        "name": "Aerobic Legend",
        "description": "Improve your VO2 Max by 15% from baseline",
        "category": "performance",
        "icon": "🚀",
        "xp_value": 150,
        "rarity": "legendary",
        "condition_type": "vo2max_improvement",
        "condition_value": "15",
        "display_order": 10,
    },
    # Trend-based achievements (consistency rewards)
    {
        "id": "vo2max_trend_4w",
        "name": "Rising Tide",
        "description": "VO2 Max trending upward for 4 consecutive weeks",
        "category": "consistency",
        "icon": "🌊",
        "xp_value": 50,
        "rarity": "common",
        "condition_type": "vo2max_trend",
        "condition_value": "4",
        "display_order": 11,
    },
    {
        "id": "vo2max_trend_8w",
        "name": "Steady Climber",
        "description": "VO2 Max trending upward for 8 consecutive weeks",
        "category": "consistency",
        "icon": "⛰️",
        "xp_value": 100,
        "rarity": "rare",
        "condition_type": "vo2max_trend",
        "condition_value": "8",
        "display_order": 12,
    },
    # Process-based achievements (reward the right behaviors)
    {
        "id": "interval_starter",
        "name": "Interval Initiate",
        "description": "Complete 5 high-intensity interval workouts",
        "category": "execution",
        "icon": "⚡",
        "xp_value": 40,
        "rarity": "common",
        "condition_type": "interval_workouts",
        "condition_value": "5",
        "display_order": 13,
    },
    {
        "id": "interval_master",
        "name": "HIIT Hero",
        "description": "Complete 20 high-intensity interval workouts",
        "category": "execution",
        "icon": "🔥",
        "xp_value": 75,
        "rarity": "rare",
        "condition_type": "interval_workouts",
        "condition_value": "20",
        "display_order": 14,
    },
    {
        "id": "zone5_warrior",
        "name": "Zone 5 Warrior",
        "description": "Accumulate 60 minutes in heart rate Zone 5",
        "category": "execution",
        "icon": "💪",
        "xp_value": 75,
        "rarity": "rare",
        "condition_type": "zone5_minutes",
        "condition_value": "60",
        "display_order": 15,
    },
    # Personal record achievement (always achievable)
    {
        "id": "vo2max_pr",
        "name": "New Personal Best!",
        "description": "Set a new personal VO2 Max record",
        "category": "performance",
        "icon": "🌟",
        "xp_value": 50,
        "rarity": "common",
        "condition_type": "vo2max_pr",
        "condition_value": "personal_best",
        "display_order": 16,
    },
    # CTL/Fitness achievements
    {
        "id": "ctl_30",
        "name": "Base Builder",
        "description": "Build your fitness base - CTL reaches 30",
        "category": "performance",
        "icon": "🏃",
        "xp_value": 50,
        "rarity": "common",
        "condition_type": "ctl",
        "condition_value": "30",
        "display_order": 20,
    },
    {
        "id": "ctl_50",
        "name": "Fitness Foundation",
        "description": "Establish a solid fitness foundation - CTL reaches 50",
        "category": "performance",
        "icon": "🏗️",
        "xp_value": 75,
        "rarity": "rare",
        "condition_type": "ctl",
        "condition_value": "50",
        "display_order": 21,
    },
    {
        "id": "ctl_70",
        "name": "Peak Performer",
        "description": "Reach peak fitness - CTL reaches 70",
        "category": "performance",
        "icon": "🏔️",
        "xp_value": 100,
        "rarity": "epic",
        "condition_type": "ctl",
        "condition_value": "70",
        "display_order": 22,
    },
    {
        "id": "ctl_peak",
        "name": "New Peak!",
        "description": "Set a new personal CTL record",
        "category": "performance",
        "icon": "⭐",
        "xp_value": 50,
        "rarity": "common",
        "condition_type": "ctl_peak",
        "condition_value": "personal_best",
        "display_order": 23,
    },
]


# =============================================================================
# Level Rewards System - Features unlock as users level up
# =============================================================================

# Features always available (never locked) - core value proposition
ALWAYS_AVAILABLE_FEATURES = [
    "basic_dashboard",
    "workout_history",
    "ai_workout_analysis",
    "garmin_sync",
]

LEVEL_REWARDS: Dict[int, Dict[str, Any]] = {
    1: {
        "name": "Rookie",
        "title": "Training Rookie",
        "unlocks": [],  # Core features always available, no unlocks needed
        "description": "Welcome! Start your training journey.",
    },
    3: {
        "name": "Learner",
        "title": "Eager Learner",
        "unlocks": ["trend_analysis"],
        "description": "Trend analysis (7/30/90 day views) unlocked!",
    },
    5: {
        "name": "Dedicated",
        "title": "Dedicated Athlete",
        "unlocks": ["advanced_metrics"],
        "description": "Advanced metrics and fatigue modeling unlocked!",
    },
    8: {
        "name": "Committed",
        "title": "Committed Trainer",
        "unlocks": ["ai_coach_chat", "personalized_tips"],
        "description": "AI Coach chat and personalized tips unlocked!",
    },
    10: {
        "name": "Athlete",
        "title": "Serious Athlete",
        "unlocks": ["training_plan_generation", "race_predictions"],
        "description": "Training plan generation and race predictions unlocked!",
    },
    15: {
        "name": "Advanced",
        "title": "Advanced Performer",
        "unlocks": ["custom_workout_design", "garmin_fit_export"],
        "description": "Custom workout design with Garmin FIT export unlocked!",
    },
    20: {
        "name": "Expert",
        "title": "Training Expert",
        "unlocks": ["periodization_planner", "peak_optimization"],
        "description": "Periodization planner and peak optimization unlocked!",
    },
    25: {
        "name": "Elite",
        "title": "Elite Performer",
        "unlocks": ["coach_mode", "athlete_management"],
        "description": "Coach mode unlocked - help others train!",
    },
    30: {
        "name": "Master",
        "title": "Training Master",
        "unlocks": ["beta_access"],
        "description": "All features unlocked + early access to new features!",
    },
}


class AchievementService:
    """
    Service for managing achievements and gamification features.

    Handles:
    - Achievement definitions and seeding
    - Achievement unlock checking and tracking
    - XP progression and level calculation
    - Streak tracking and updates
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the achievement service.

        Args:
            db_path: Path to SQLite database. Uses default if not provided.
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            from ..db.database import get_default_db_path
            self.db_path = get_default_db_path()

        self._init_db()
        self._seed_achievements()

    def _init_db(self) -> None:
        """Initialize database tables if they don't exist."""
        with self._get_connection() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _seed_achievements(self) -> None:
        """Seed default achievements if not present."""
        with self._get_connection() as conn:
            # Check if achievements already exist
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM achievements"
            ).fetchone()["cnt"]

            if count > 0:
                return

            # Insert default achievements
            for achievement in DEFAULT_ACHIEVEMENTS:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO achievements
                    (id, name, description, category, icon, xp_value,
                     rarity, condition_type, condition_value, display_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        achievement["id"],
                        achievement["name"],
                        achievement["description"],
                        achievement["category"],
                        achievement["icon"],
                        achievement["xp_value"],
                        achievement["rarity"],
                        achievement["condition_type"],
                        achievement["condition_value"],
                        achievement["display_order"],
                    ),
                )

            logger.info(f"Seeded {len(DEFAULT_ACHIEVEMENTS)} achievements")

    # =========================================================================
    # Achievement Methods
    # =========================================================================

    def get_all_achievements(self) -> List[AchievementWithStatus]:
        """
        Get all achievements with unlock status for the user.

        Returns:
            List of achievements with their unlock status
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    a.*,
                    ua.unlocked_at
                FROM achievements a
                LEFT JOIN user_achievements ua ON a.id = ua.achievement_id
                ORDER BY a.display_order, a.id
                """
            ).fetchall()

            result = []
            for row in rows:
                achievement = Achievement(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    category=AchievementCategory(row["category"]),
                    icon=row["icon"],
                    xp_value=row["xp_value"],
                    rarity=AchievementRarity(row["rarity"]),
                    condition_type=row["condition_type"],
                    condition_value=row["condition_value"],
                    display_order=row["display_order"],
                )

                unlocked_at = None
                if row["unlocked_at"]:
                    unlocked_at = datetime.fromisoformat(row["unlocked_at"])

                result.append(AchievementWithStatus(
                    achievement=achievement,
                    unlocked=row["unlocked_at"] is not None,
                    unlocked_at=unlocked_at,
                ))

            return result

    def get_user_achievements(self) -> List[AchievementUnlock]:
        """
        Get all achievements unlocked by the user.

        Returns:
            List of unlocked achievements with unlock details
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    a.*,
                    ua.unlocked_at
                FROM user_achievements ua
                JOIN achievements a ON a.id = ua.achievement_id
                ORDER BY ua.unlocked_at DESC
                """
            ).fetchall()

            result = []
            for row in rows:
                achievement = Achievement(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    category=AchievementCategory(row["category"]),
                    icon=row["icon"],
                    xp_value=row["xp_value"],
                    rarity=AchievementRarity(row["rarity"]),
                    condition_type=row["condition_type"],
                    condition_value=row["condition_value"],
                    display_order=row["display_order"],
                )

                result.append(AchievementUnlock(
                    achievement=achievement,
                    unlocked_at=datetime.fromisoformat(row["unlocked_at"]),
                    is_new=False,
                ))

            return result

    def get_recent_achievements(self, days: int = 7) -> List[AchievementUnlock]:
        """
        Get recently unlocked achievements.

        Args:
            days: Number of days to look back

        Returns:
            List of recently unlocked achievements
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    a.*,
                    ua.unlocked_at
                FROM user_achievements ua
                JOIN achievements a ON a.id = ua.achievement_id
                WHERE ua.unlocked_at >= ?
                ORDER BY ua.unlocked_at DESC
                """,
                (cutoff,),
            ).fetchall()

            result = []
            for row in rows:
                achievement = Achievement(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    category=AchievementCategory(row["category"]),
                    icon=row["icon"],
                    xp_value=row["xp_value"],
                    rarity=AchievementRarity(row["rarity"]),
                    condition_type=row["condition_type"],
                    condition_value=row["condition_value"],
                    display_order=row["display_order"],
                )

                result.append(AchievementUnlock(
                    achievement=achievement,
                    unlocked_at=datetime.fromisoformat(row["unlocked_at"]),
                    is_new=False,
                ))

            return result

    def _is_achievement_unlocked(self, achievement_id: str) -> bool:
        """Check if an achievement is already unlocked."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM user_achievements WHERE achievement_id = ?",
                (achievement_id,),
            ).fetchone()
            return row is not None

    def _unlock_achievement(
        self,
        achievement_id: str,
        workout_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AchievementUnlock]:
        """
        Unlock an achievement for the user.

        Args:
            achievement_id: ID of the achievement to unlock
            workout_id: Optional workout that triggered the unlock
            metadata: Optional additional metadata

        Returns:
            AchievementUnlock if newly unlocked, None if already unlocked
        """
        if self._is_achievement_unlocked(achievement_id):
            return None

        with self._get_connection() as conn:
            # Get achievement details
            row = conn.execute(
                "SELECT * FROM achievements WHERE id = ?",
                (achievement_id,),
            ).fetchone()

            if not row:
                logger.warning(f"Achievement not found: {achievement_id}")
                return None

            # Insert unlock record
            unlocked_at = datetime.now().isoformat()
            metadata_json = json.dumps(metadata) if metadata else None

            conn.execute(
                """
                INSERT INTO user_achievements
                (achievement_id, unlocked_at, workout_id, metadata_json)
                VALUES (?, ?, ?, ?)
                """,
                (achievement_id, unlocked_at, workout_id, metadata_json),
            )

            achievement = Achievement(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                category=AchievementCategory(row["category"]),
                icon=row["icon"],
                xp_value=row["xp_value"],
                rarity=AchievementRarity(row["rarity"]),
                condition_type=row["condition_type"],
                condition_value=row["condition_value"],
                display_order=row["display_order"],
            )

            logger.info(f"Achievement unlocked: {achievement.name}")

            return AchievementUnlock(
                achievement=achievement,
                unlocked_at=datetime.fromisoformat(unlocked_at),
                is_new=True,
            )

    # =========================================================================
    # Progress Methods
    # =========================================================================

    def get_user_progress(self) -> UserProgress:
        """
        Get the user's overall gamification progress.

        Returns:
            UserProgress with XP, level, and streak info
        """
        with self._get_connection() as conn:
            # Get or create user progress
            row = conn.execute(
                "SELECT * FROM user_progress WHERE user_id = 'default'"
            ).fetchone()

            if not row:
                # Create default progress
                conn.execute(
                    """
                    INSERT INTO user_progress (user_id, total_xp, current_level,
                        current_streak, longest_streak, streak_freeze_tokens)
                    VALUES ('default', 0, 1, 0, 0, 0)
                    """
                )
                row = conn.execute(
                    "SELECT * FROM user_progress WHERE user_id = 'default'"
                ).fetchone()

            # Count unlocked achievements
            achievement_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM user_achievements"
            ).fetchone()["cnt"]

            total_xp = row["total_xp"] or 0
            level_info = calculate_level(total_xp)

            streak_info = StreakInfo(
                current=row["current_streak"] or 0,
                longest=row["longest_streak"] or 0,
                freeze_tokens=row["streak_freeze_tokens"] or 0,
                is_protected=False,
                last_activity_date=row["last_activity_date"],
            )

            updated_at = None
            if row["updated_at"]:
                updated_at = datetime.fromisoformat(row["updated_at"])

            # Get level rewards info
            current_level = level_info.level
            title = self.get_user_title(current_level)
            unlocked_features = self.get_unlocked_features(current_level)

            # Get next reward
            next_reward_data = self.get_next_level_reward(current_level)
            next_reward = None
            if next_reward_data:
                next_reward = LevelReward(
                    level=next_reward_data["level"],
                    name=next_reward_data["name"],
                    title=next_reward_data["title"],
                    unlocks=next_reward_data["unlocks"],
                    description=next_reward_data["description"],
                )

            return UserProgress(
                user_id="default",
                total_xp=total_xp,
                level=level_info,
                streak=streak_info,
                achievements_unlocked=achievement_count,
                updated_at=updated_at,
                title=title,
                unlocked_features=unlocked_features,
                next_reward=next_reward,
            )

    def add_xp(self, amount: int, source: str) -> Tuple[int, bool, Optional[int]]:
        """
        Add XP to the user's progress.

        Args:
            amount: Amount of XP to add
            source: Description of XP source

        Returns:
            Tuple of (new_total_xp, level_up_occurred, new_level)
        """
        with self._get_connection() as conn:
            # Get current progress
            row = conn.execute(
                "SELECT total_xp, current_level FROM user_progress WHERE user_id = 'default'"
            ).fetchone()

            if not row:
                old_xp = 0
                old_level = 1
            else:
                old_xp = row["total_xp"] or 0
                old_level = row["current_level"] or 1

            new_xp = old_xp + amount
            new_level_info = calculate_level(new_xp)
            new_level = new_level_info.level

            level_up = new_level > old_level

            # Update progress
            conn.execute(
                """
                INSERT OR REPLACE INTO user_progress
                (user_id, total_xp, current_level, current_streak, longest_streak,
                 streak_freeze_tokens, last_activity_date, updated_at)
                VALUES (
                    'default', ?, ?,
                    COALESCE((SELECT current_streak FROM user_progress WHERE user_id = 'default'), 0),
                    COALESCE((SELECT longest_streak FROM user_progress WHERE user_id = 'default'), 0),
                    COALESCE((SELECT streak_freeze_tokens FROM user_progress WHERE user_id = 'default'), 0),
                    (SELECT last_activity_date FROM user_progress WHERE user_id = 'default'),
                    CURRENT_TIMESTAMP
                )
                """,
                (new_xp, new_level),
            )

            logger.info(f"Added {amount} XP from {source}. Total: {new_xp}")

            if level_up:
                logger.info(f"Level up! {old_level} -> {new_level}")

            return new_xp, level_up, new_level if level_up else None

    # =========================================================================
    # Streak Methods
    # =========================================================================

    def update_streak(self, activity_date: str) -> Tuple[int, bool]:
        """
        Update the user's workout streak based on activity date.

        Args:
            activity_date: Date of the activity (YYYY-MM-DD)

        Returns:
            Tuple of (current_streak, streak_updated)
        """
        with self._get_connection() as conn:
            # Get current progress
            row = conn.execute(
                "SELECT * FROM user_progress WHERE user_id = 'default'"
            ).fetchone()

            if not row:
                # Create new progress
                conn.execute(
                    """
                    INSERT INTO user_progress (user_id, total_xp, current_level,
                        current_streak, longest_streak, streak_freeze_tokens,
                        last_activity_date, updated_at)
                    VALUES ('default', 0, 1, 1, 1, 0, ?, CURRENT_TIMESTAMP)
                    """,
                    (activity_date,),
                )
                return 1, True

            last_activity = row["last_activity_date"]
            current_streak = row["current_streak"] or 0
            longest_streak = row["longest_streak"] or 0

            # Parse dates
            activity_dt = datetime.strptime(activity_date, "%Y-%m-%d").date()

            if last_activity:
                last_dt = datetime.strptime(last_activity, "%Y-%m-%d").date()
                days_diff = (activity_dt - last_dt).days
            else:
                days_diff = None

            streak_updated = False

            if days_diff is None:
                # First activity ever
                new_streak = 1
                streak_updated = True
            elif days_diff == 0:
                # Same day activity, no change
                new_streak = current_streak
            elif days_diff == 1:
                # Consecutive day, increment streak
                new_streak = current_streak + 1
                streak_updated = True
            elif days_diff > 1:
                # Streak broken, start new
                new_streak = 1
                streak_updated = True
            else:
                # Activity in the past, don't update streak
                new_streak = current_streak

            # Update longest streak
            new_longest = max(longest_streak, new_streak)

            # Only update last_activity_date if this is a new or future date
            update_last = days_diff is None or days_diff >= 0

            if update_last:
                conn.execute(
                    """
                    UPDATE user_progress
                    SET current_streak = ?,
                        longest_streak = ?,
                        last_activity_date = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = 'default'
                    """,
                    (new_streak, new_longest, activity_date),
                )
            else:
                conn.execute(
                    """
                    UPDATE user_progress
                    SET current_streak = ?,
                        longest_streak = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = 'default'
                    """,
                    (new_streak, new_longest),
                )

            return new_streak, streak_updated

    # =========================================================================
    # Achievement Checking
    # =========================================================================

    def check_and_unlock_achievements(
        self,
        context: Dict[str, Any],
    ) -> CheckAchievementsResponse:
        """
        Check conditions and unlock any newly earned achievements.

        Args:
            context: Dictionary with context data:
                - workout_id: Optional workout ID
                - activity_date: Activity date (YYYY-MM-DD)
                - ctl: Current CTL value
                - ctl_peak: Historical peak CTL

        Returns:
            CheckAchievementsResponse with new unlocks and XP earned
        """
        new_achievements: List[AchievementUnlock] = []
        total_xp = 0

        workout_id = context.get("workout_id")
        activity_date = context.get("activity_date", date.today().isoformat())

        # Update streak
        current_streak, streak_updated = self.update_streak(activity_date)

        # Get current progress for context
        progress = self.get_user_progress()
        workout_count = self._get_workout_count()

        # Check first workout
        if workout_count >= 1:
            unlock = self._unlock_achievement("first_workout", workout_id)
            if unlock:
                new_achievements.append(unlock)
                total_xp += unlock.achievement.xp_value

        # Check streak achievements
        streak_thresholds = [
            ("streak_3", 3),
            ("streak_7", 7),
            ("streak_14", 14),
            ("streak_30", 30),
        ]

        for achievement_id, threshold in streak_thresholds:
            if current_streak >= threshold:
                unlock = self._unlock_achievement(achievement_id, workout_id)
                if unlock:
                    new_achievements.append(unlock)
                    total_xp += unlock.achievement.xp_value

        # Check VO2 Max achievements (sports science based - relative improvements)
        vo2max_running = context.get("vo2max_running", 0) or 0
        vo2max_baseline = context.get("vo2max_baseline", 0) or 0
        vo2max_peak = context.get("vo2max_peak", 0) or 0
        vo2max_trend_weeks = context.get("vo2max_trend_weeks", 0) or 0
        interval_workout_count = context.get("interval_workout_count", 0) or 0
        zone5_total_minutes = context.get("zone5_total_minutes", 0) or 0

        # First VO2 Max measurement (baseline)
        if vo2max_running > 0:
            unlock = self._unlock_achievement(
                "vo2max_first",
                workout_id,
                metadata={"vo2max_running": vo2max_running},
            )
            if unlock:
                new_achievements.append(unlock)
                total_xp += unlock.achievement.xp_value

        # Relative improvement achievements (percentage based)
        if vo2max_baseline > 0 and vo2max_running > 0:
            improvement_pct = ((vo2max_running - vo2max_baseline) / vo2max_baseline) * 100

            vo2max_improvement_thresholds = [
                ("vo2max_up_3", 3),
                ("vo2max_up_5", 5),
                ("vo2max_up_10", 10),
                ("vo2max_up_15", 15),
            ]

            for achievement_id, threshold in vo2max_improvement_thresholds:
                if improvement_pct >= threshold:
                    unlock = self._unlock_achievement(
                        achievement_id,
                        workout_id,
                        metadata={
                            "vo2max_running": vo2max_running,
                            "vo2max_baseline": vo2max_baseline,
                            "improvement_pct": round(improvement_pct, 1),
                        },
                    )
                    if unlock:
                        new_achievements.append(unlock)
                        total_xp += unlock.achievement.xp_value

        # Trend-based achievements (consistency)
        vo2max_trend_thresholds = [
            ("vo2max_trend_4w", 4),
            ("vo2max_trend_8w", 8),
        ]

        for achievement_id, threshold in vo2max_trend_thresholds:
            if vo2max_trend_weeks >= threshold:
                unlock = self._unlock_achievement(
                    achievement_id,
                    workout_id,
                    metadata={"trend_weeks": vo2max_trend_weeks},
                )
                if unlock:
                    new_achievements.append(unlock)
                    total_xp += unlock.achievement.xp_value

        # Process-based achievements (interval workouts)
        interval_thresholds = [
            ("interval_starter", 5),
            ("interval_master", 20),
        ]

        for achievement_id, threshold in interval_thresholds:
            if interval_workout_count >= threshold:
                unlock = self._unlock_achievement(
                    achievement_id,
                    workout_id,
                    metadata={"interval_workouts": interval_workout_count},
                )
                if unlock:
                    new_achievements.append(unlock)
                    total_xp += unlock.achievement.xp_value

        # Zone 5 time achievement
        if zone5_total_minutes >= 60:
            unlock = self._unlock_achievement(
                "zone5_warrior",
                workout_id,
                metadata={"zone5_minutes": zone5_total_minutes},
            )
            if unlock:
                new_achievements.append(unlock)
                total_xp += unlock.achievement.xp_value

        # VO2 Max personal record
        if vo2max_running > 0 and vo2max_peak > 0 and vo2max_running > vo2max_peak:
            unlock = self._unlock_achievement(
                "vo2max_pr",
                workout_id,
                metadata={"new_pr": vo2max_running, "old_pr": vo2max_peak},
            )
            if unlock:
                new_achievements.append(unlock)
                total_xp += unlock.achievement.xp_value

        # Check CTL achievements
        current_ctl = context.get("ctl", 0)
        ctl_peak = context.get("ctl_peak", 0)

        ctl_thresholds = [
            ("ctl_30", 30),
            ("ctl_50", 50),
            ("ctl_70", 70),
        ]

        for achievement_id, threshold in ctl_thresholds:
            if current_ctl >= threshold:
                unlock = self._unlock_achievement(
                    achievement_id,
                    workout_id,
                    metadata={"ctl": current_ctl},
                )
                if unlock:
                    new_achievements.append(unlock)
                    total_xp += unlock.achievement.xp_value

        # Check CTL peak achievement
        if current_ctl > 0 and current_ctl >= ctl_peak:
            # Only unlock if this is a new peak (not first CTL value)
            if ctl_peak > 0 and current_ctl > ctl_peak:
                unlock = self._unlock_achievement(
                    "ctl_peak",
                    workout_id,
                    metadata={"new_peak": current_ctl, "old_peak": ctl_peak},
                )
                if unlock:
                    new_achievements.append(unlock)
                    total_xp += unlock.achievement.xp_value

        # Add XP and check for level up
        level_up = False
        new_level = None

        if total_xp > 0:
            _, level_up, new_level = self.add_xp(total_xp, "achievements")

        return CheckAchievementsResponse(
            new_achievements=new_achievements,
            xp_earned=total_xp,
            level_up=level_up,
            new_level=new_level,
            streak_updated=streak_updated,
            current_streak=current_streak,
        )

    def _get_workout_count(self) -> int:
        """Get total number of workouts (activities) in the database."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM activity_metrics"
            ).fetchone()
            return row["cnt"] if row else 0

    # =========================================================================
    # Level Rewards Methods
    # =========================================================================

    def get_level_reward(self, level: int) -> Optional[Dict[str, Any]]:
        """
        Get the reward for a specific level.

        Args:
            level: The level to check

        Returns:
            Reward dict if level has a reward, None otherwise
        """
        return LEVEL_REWARDS.get(level)

    def get_unlocked_features(self, level: int) -> List[str]:
        """
        Get all features unlocked at or below a given level.

        Always includes core features (dashboard, workout history, AI analysis)
        that are never locked.

        Args:
            level: Current user level

        Returns:
            List of unlocked feature identifiers
        """
        # Start with always-available core features
        features = list(ALWAYS_AVAILABLE_FEATURES)

        # Add level-gated features
        for reward_level, reward in LEVEL_REWARDS.items():
            if reward_level <= level:
                features.extend(reward.get("unlocks", []))
        return features

    def get_next_level_reward(self, current_level: int) -> Optional[Dict[str, Any]]:
        """
        Get the next upcoming level reward.

        Args:
            current_level: User's current level

        Returns:
            Next reward dict with 'level' key added, or None if no more rewards
        """
        for level in sorted(LEVEL_REWARDS.keys()):
            if level > current_level:
                reward = LEVEL_REWARDS[level].copy()
                reward["level"] = level
                return reward
        return None

    def get_all_level_rewards(self) -> List[Dict[str, Any]]:
        """
        Get all level rewards with their levels.

        Returns:
            List of reward dicts with 'level' key added
        """
        rewards = []
        for level in sorted(LEVEL_REWARDS.keys()):
            reward = LEVEL_REWARDS[level].copy()
            reward["level"] = level
            rewards.append(reward)
        return rewards

    def is_feature_unlocked(self, feature: str, level: int) -> bool:
        """
        Check if a specific feature is unlocked at a given level.

        Args:
            feature: Feature identifier to check
            level: User's current level

        Returns:
            True if feature is unlocked, False otherwise
        """
        return feature in self.get_unlocked_features(level)

    def get_user_title(self, level: int) -> str:
        """
        Get the user's title based on their level.

        Args:
            level: User's current level

        Returns:
            Title string for the user's level
        """
        title = "Training Rookie"
        for reward_level in sorted(LEVEL_REWARDS.keys(), reverse=True):
            if level >= reward_level:
                title = LEVEL_REWARDS[reward_level].get("title", title)
                break
        return title
