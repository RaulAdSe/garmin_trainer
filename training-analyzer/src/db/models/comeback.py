"""Comeback Challenge database model.

The Comeback Challenge system helps users recover from broken streaks
by providing a 3-day challenge with bonus XP multipliers.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class ComebackChallengeStatus(str, Enum):
    """Status of a comeback challenge."""

    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class ComebackChallenge:
    """
    Represents a Comeback Challenge for streak recovery.

    When a user breaks a streak of 3+ days, they get a chance to
    restore momentum through a 3-day comeback challenge with 1.5x XP bonus.

    Attributes:
        id: Unique identifier for the challenge
        user_id: ID of the user this challenge belongs to
        triggered_at: When the challenge was triggered (streak broke)
        previous_streak: The streak count before it was broken
        status: Current status of the challenge
        day1_completed_at: Timestamp when day 1 workout was completed
        day2_completed_at: Timestamp when day 2 workout was completed
        day3_completed_at: Timestamp when day 3 workout was completed
        xp_multiplier: XP bonus multiplier (default 1.5x)
        bonus_xp_earned: Total bonus XP earned during the challenge
        expires_at: When the challenge expires (7 days from trigger)
        created_at: When the record was created
    """

    id: str
    user_id: str
    triggered_at: datetime
    previous_streak: int
    status: ComebackChallengeStatus
    day1_completed_at: Optional[datetime] = None
    day2_completed_at: Optional[datetime] = None
    day3_completed_at: Optional[datetime] = None
    xp_multiplier: float = 1.5
    bonus_xp_earned: int = 0
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    @property
    def days_completed(self) -> int:
        """Get the number of days completed in the challenge."""
        count = 0
        if self.day1_completed_at:
            count += 1
        if self.day2_completed_at:
            count += 1
        if self.day3_completed_at:
            count += 1
        return count

    @property
    def is_complete(self) -> bool:
        """Check if all 3 days are completed."""
        return self.days_completed == 3

    @property
    def is_expired(self) -> bool:
        """Check if the challenge has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def is_active(self) -> bool:
        """Check if the challenge is currently active."""
        return (
            self.status == ComebackChallengeStatus.ACTIVE
            and not self.is_expired
            and not self.is_complete
        )

    def get_next_day_to_complete(self) -> Optional[int]:
        """Get the next day number that needs to be completed (1, 2, or 3)."""
        if not self.day1_completed_at:
            return 1
        if not self.day2_completed_at:
            return 2
        if not self.day3_completed_at:
            return 3
        return None  # All days completed


# SQL schema for comeback_challenges table
COMEBACK_CHALLENGE_SCHEMA = """
-- Comeback Challenge table for streak recovery
CREATE TABLE IF NOT EXISTS comeback_challenges (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    triggered_at TEXT NOT NULL,
    previous_streak INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    day1_completed_at TEXT,
    day2_completed_at TEXT,
    day3_completed_at TEXT,
    xp_multiplier REAL DEFAULT 1.5,
    bonus_xp_earned INTEGER DEFAULT 0,
    expires_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_comeback_user ON comeback_challenges(user_id);
CREATE INDEX IF NOT EXISTS idx_comeback_status ON comeback_challenges(status);
CREATE INDEX IF NOT EXISTS idx_comeback_user_status ON comeback_challenges(user_id, status);
CREATE INDEX IF NOT EXISTS idx_comeback_expires ON comeback_challenges(expires_at);
"""
