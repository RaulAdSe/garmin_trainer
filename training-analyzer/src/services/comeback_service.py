"""
Comeback Challenge service for streak recovery.

Provides functionality to:
- Trigger comeback challenges when streaks break
- Record workout progress during challenges
- Apply XP multipliers and bonus rewards
- Track and manage active challenges
"""

import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..db.models.comeback import (
    ComebackChallenge,
    ComebackChallengeStatus,
    COMEBACK_CHALLENGE_SCHEMA,
)


logger = logging.getLogger(__name__)


# Constants
DEFAULT_XP_MULTIPLIER = 1.5
CHALLENGE_DURATION_DAYS = 7
MIN_STREAK_FOR_COMEBACK = 3
COMPLETION_BONUS_XP = 100


class ComebackService:
    """
    Service for managing Comeback Challenges.

    The comeback challenge system encourages users who have broken their
    workout streak to get back on track. When a streak of 3+ days breaks,
    the user is offered a 3-day challenge with 1.5x XP bonus for each workout.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the comeback service.

        Args:
            db_path: Path to SQLite database. Uses default if not provided.
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            from ..db.database import get_default_db_path
            self.db_path = get_default_db_path()

        self._init_db()

    def _init_db(self) -> None:
        """Initialize database tables if they don't exist."""
        with self._get_connection() as conn:
            conn.executescript(COMEBACK_CHALLENGE_SCHEMA)

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

    def _row_to_challenge(self, row: sqlite3.Row) -> ComebackChallenge:
        """Convert a database row to a ComebackChallenge object."""
        return ComebackChallenge(
            id=row["id"],
            user_id=row["user_id"],
            triggered_at=datetime.fromisoformat(row["triggered_at"]),
            previous_streak=row["previous_streak"],
            status=ComebackChallengeStatus(row["status"]),
            day1_completed_at=(
                datetime.fromisoformat(row["day1_completed_at"])
                if row["day1_completed_at"]
                else None
            ),
            day2_completed_at=(
                datetime.fromisoformat(row["day2_completed_at"])
                if row["day2_completed_at"]
                else None
            ),
            day3_completed_at=(
                datetime.fromisoformat(row["day3_completed_at"])
                if row["day3_completed_at"]
                else None
            ),
            xp_multiplier=row["xp_multiplier"] or DEFAULT_XP_MULTIPLIER,
            bonus_xp_earned=row["bonus_xp_earned"] or 0,
            expires_at=(
                datetime.fromisoformat(row["expires_at"])
                if row["expires_at"]
                else None
            ),
            created_at=(
                datetime.fromisoformat(row["created_at"])
                if row["created_at"]
                else None
            ),
        )

    # =========================================================================
    # Public API
    # =========================================================================

    def check_and_trigger_comeback(
        self,
        user_id: str,
        previous_streak: int,
        last_activity_date: Optional[str] = None,
    ) -> Optional[ComebackChallenge]:
        """
        Check if a comeback challenge should be triggered and create one if so.

        A comeback challenge is triggered when:
        1. The user had a streak of MIN_STREAK_FOR_COMEBACK or more days
        2. The streak was broken (gap in workout dates)
        3. No active comeback challenge exists for this user

        Args:
            user_id: The user's ID
            previous_streak: The streak count before it was broken
            last_activity_date: The date of the last activity (YYYY-MM-DD)

        Returns:
            The created ComebackChallenge if triggered, None otherwise
        """
        # Check minimum streak requirement
        if previous_streak < MIN_STREAK_FOR_COMEBACK:
            logger.debug(
                f"Streak {previous_streak} below minimum {MIN_STREAK_FOR_COMEBACK} "
                "for comeback challenge"
            )
            return None

        # Check for existing active challenge
        existing = self.get_active_challenge(user_id)
        if existing:
            logger.debug(f"User {user_id} already has an active comeback challenge")
            return None

        # Create new comeback challenge
        challenge_id = str(uuid.uuid4())
        now = datetime.now()
        expires_at = now + timedelta(days=CHALLENGE_DURATION_DAYS)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO comeback_challenges (
                    id, user_id, triggered_at, previous_streak, status,
                    xp_multiplier, expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    challenge_id,
                    user_id,
                    now.isoformat(),
                    previous_streak,
                    ComebackChallengeStatus.ACTIVE.value,
                    DEFAULT_XP_MULTIPLIER,
                    expires_at.isoformat(),
                    now.isoformat(),
                ),
            )

        logger.info(
            f"Created comeback challenge {challenge_id} for user {user_id} "
            f"(previous streak: {previous_streak})"
        )

        return self.get_challenge(challenge_id)

    def record_comeback_workout(
        self,
        user_id: str,
        workout_id: str,
        base_xp: int = 25,
    ) -> Tuple[Optional[ComebackChallenge], int, bool]:
        """
        Record a workout during an active comeback challenge.

        Applies the XP multiplier and updates the challenge progress.

        Args:
            user_id: The user's ID
            workout_id: The ID of the completed workout
            base_xp: The base XP for the workout (before multiplier)

        Returns:
            Tuple of (updated challenge, bonus XP earned, challenge completed)
        """
        challenge = self.get_active_challenge(user_id)

        if not challenge:
            return None, 0, False

        # Check if challenge is expired
        if challenge.is_expired:
            self._expire_challenge(challenge.id)
            return None, 0, False

        # Get next day to complete
        next_day = challenge.get_next_day_to_complete()
        if next_day is None:
            # Challenge already complete
            return challenge, 0, True

        # Calculate bonus XP
        bonus_xp = int(base_xp * (challenge.xp_multiplier - 1))
        now = datetime.now()

        # Update the appropriate day
        day_column = f"day{next_day}_completed_at"
        total_bonus = challenge.bonus_xp_earned + bonus_xp

        with self._get_connection() as conn:
            conn.execute(
                f"""
                UPDATE comeback_challenges
                SET {day_column} = ?,
                    bonus_xp_earned = ?
                WHERE id = ?
                """,
                (now.isoformat(), total_bonus, challenge.id),
            )

        # Check if challenge is now complete
        updated_challenge = self.get_challenge(challenge.id)
        challenge_completed = False

        if updated_challenge and updated_challenge.is_complete:
            # Mark as completed and add completion bonus
            self._complete_challenge(challenge.id)
            bonus_xp += COMPLETION_BONUS_XP
            challenge_completed = True
            logger.info(
                f"Comeback challenge {challenge.id} completed! "
                f"Bonus XP: {bonus_xp} (including {COMPLETION_BONUS_XP} completion bonus)"
            )
        else:
            logger.info(
                f"Comeback challenge day {next_day} recorded for user {user_id}. "
                f"Bonus XP: {bonus_xp}"
            )

        return self.get_challenge(challenge.id), bonus_xp, challenge_completed

    def get_active_challenge(self, user_id: str) -> Optional[ComebackChallenge]:
        """
        Get the active comeback challenge for a user.

        Args:
            user_id: The user's ID

        Returns:
            The active ComebackChallenge if one exists, None otherwise
        """
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM comeback_challenges
                WHERE user_id = ?
                AND status = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id, ComebackChallengeStatus.ACTIVE.value),
            ).fetchone()

            if not row:
                return None

            challenge = self._row_to_challenge(row)

            # Check if expired
            if challenge.is_expired:
                self._expire_challenge(challenge.id)
                return None

            return challenge

    def get_challenge(self, challenge_id: str) -> Optional[ComebackChallenge]:
        """
        Get a comeback challenge by ID.

        Args:
            challenge_id: The challenge ID

        Returns:
            The ComebackChallenge if found, None otherwise
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM comeback_challenges WHERE id = ?",
                (challenge_id,),
            ).fetchone()

            if not row:
                return None

            return self._row_to_challenge(row)

    def get_user_challenges(
        self,
        user_id: str,
        limit: int = 10,
    ) -> List[ComebackChallenge]:
        """
        Get comeback challenge history for a user.

        Args:
            user_id: The user's ID
            limit: Maximum number of challenges to return

        Returns:
            List of ComebackChallenge objects, newest first
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM comeback_challenges
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

            return [self._row_to_challenge(row) for row in rows]

    def complete_challenge(
        self,
        challenge_id: str,
    ) -> Optional[ComebackChallenge]:
        """
        Manually complete a comeback challenge.

        Typically called automatically when all 3 days are completed,
        but can be called manually for administrative purposes.

        Args:
            challenge_id: The challenge ID

        Returns:
            The updated ComebackChallenge if found, None otherwise
        """
        return self._complete_challenge(challenge_id)

    def cancel_challenge(
        self,
        challenge_id: str,
    ) -> Optional[ComebackChallenge]:
        """
        Cancel an active comeback challenge.

        Args:
            challenge_id: The challenge ID

        Returns:
            The updated ComebackChallenge if found, None otherwise
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE comeback_challenges
                SET status = ?
                WHERE id = ?
                AND status = ?
                """,
                (
                    ComebackChallengeStatus.CANCELLED.value,
                    challenge_id,
                    ComebackChallengeStatus.ACTIVE.value,
                ),
            )

        return self.get_challenge(challenge_id)

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _complete_challenge(
        self,
        challenge_id: str,
    ) -> Optional[ComebackChallenge]:
        """Mark a challenge as completed."""
        challenge = self.get_challenge(challenge_id)
        if not challenge:
            return None

        # Add completion bonus to total
        total_bonus = challenge.bonus_xp_earned + COMPLETION_BONUS_XP

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE comeback_challenges
                SET status = ?,
                    bonus_xp_earned = ?
                WHERE id = ?
                """,
                (
                    ComebackChallengeStatus.COMPLETED.value,
                    total_bonus,
                    challenge_id,
                ),
            )

        logger.info(f"Comeback challenge {challenge_id} marked as completed")
        return self.get_challenge(challenge_id)

    def _expire_challenge(self, challenge_id: str) -> None:
        """Mark a challenge as expired."""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE comeback_challenges
                SET status = ?
                WHERE id = ?
                AND status = ?
                """,
                (
                    ComebackChallengeStatus.EXPIRED.value,
                    challenge_id,
                    ComebackChallengeStatus.ACTIVE.value,
                ),
            )

        logger.info(f"Comeback challenge {challenge_id} marked as expired")


# Module-level singleton for convenience
_comeback_service: Optional[ComebackService] = None


def get_comeback_service(db_path: Optional[str] = None) -> ComebackService:
    """
    Get or create the comeback service singleton.

    Args:
        db_path: Optional path to the database

    Returns:
        ComebackService instance
    """
    global _comeback_service

    if _comeback_service is None or db_path is not None:
        _comeback_service = ComebackService(db_path)

    return _comeback_service
