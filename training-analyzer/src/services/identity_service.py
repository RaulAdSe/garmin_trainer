"""Identity commitment service for emotional design features.

This service handles the Identity Commitment feature based on sports science
research showing that athletes who identify as "someone who trains consistently"
are more likely to maintain long-term training adherence.

Features:
- Identity statement creation at Level 3
- Periodic reinforcement to strengthen commitment
- Template-based and custom statement support
"""

import logging
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, List

from ..db.database import TrainingDatabase

logger = logging.getLogger(__name__)


# Identity statement templates
IDENTITY_TEMPLATES = [
    {
        "id": "trains_consistently",
        "statement": "trains consistently, no matter what",
        "description": "Commit to showing up for your training every day",
    },
    {
        "id": "prioritizes_health",
        "statement": "prioritizes their health every day",
        "description": "Make health your daily non-negotiable",
    },
    {
        "id": "shows_up",
        "statement": "shows up even when it's hard",
        "description": "Embrace the challenge and never give up",
    },
    {
        "id": "values_discipline",
        "statement": "values discipline over motivation",
        "description": "Build habits that don't depend on feeling motivated",
    },
    {
        "id": "never_quits",
        "statement": "never gives up on their goals",
        "description": "Persistence is your superpower",
    },
    {
        "id": "embraces_process",
        "statement": "loves the process, not just the results",
        "description": "Find joy in the journey itself",
    },
]


@dataclass
class IdentityStatement:
    """User identity statement data model."""

    id: int
    user_id: str
    statement: str
    created_at: str
    last_reinforced_at: str
    reinforcement_count: int

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "userId": self.user_id,
            "statement": self.statement,
            "createdAt": self.created_at,
            "lastReinforcedAt": self.last_reinforced_at,
            "reinforcementCount": self.reinforcement_count,
        }

    @classmethod
    def from_row(cls, row: dict) -> "IdentityStatement":
        """Create IdentityStatement from database row."""
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            statement=row["statement"],
            created_at=row["created_at"],
            last_reinforced_at=row["last_reinforced_at"],
            reinforcement_count=row["reinforcement_count"],
        )


@dataclass
class IdentityTemplate:
    """Identity statement template."""

    id: str
    statement: str
    description: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "statement": self.statement,
            "description": self.description,
        }


class IdentityService:
    """Service for managing identity commitment statements.

    Handles creation, retrieval, and reinforcement of identity statements
    as part of the emotional design system.
    """

    def __init__(self, db: Optional[TrainingDatabase] = None):
        """Initialize the identity service.

        Args:
            db: Optional TrainingDatabase instance. If not provided,
                a new instance will be created.
        """
        self._db = db or TrainingDatabase(use_pool=True)

    def get_templates(self) -> List[IdentityTemplate]:
        """Get available identity statement templates.

        Returns:
            List of IdentityTemplate objects.
        """
        return [
            IdentityTemplate(
                id=t["id"],
                statement=t["statement"],
                description=t["description"],
            )
            for t in IDENTITY_TEMPLATES
        ]

    def get_statement(self, user_id: str) -> Optional[IdentityStatement]:
        """Get the identity statement for a user.

        Args:
            user_id: The user's unique identifier.

        Returns:
            IdentityStatement if found, None otherwise.
        """
        with self._db._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM identity_statements WHERE user_id = ?",
                (user_id,),
            ).fetchone()

            if row:
                return IdentityStatement.from_row(dict(row))
            return None

    def create_statement(
        self,
        user_id: str,
        statement: str,
    ) -> IdentityStatement:
        """Create or update an identity statement for a user.

        Args:
            user_id: The user's unique identifier.
            statement: The identity statement (without "I am someone who").

        Returns:
            Created or updated IdentityStatement.
        """
        now = datetime.now(timezone.utc).isoformat()
        statement = statement.strip()

        # Check if user already has a statement
        existing = self.get_statement(user_id)

        with self._db._get_connection() as conn:
            if existing:
                # Update existing statement
                conn.execute(
                    """
                    UPDATE identity_statements
                    SET statement = ?, last_reinforced_at = ?, updated_at = ?
                    WHERE user_id = ?
                    """,
                    (statement, now, now, user_id),
                )
                logger.info(f"Updated identity statement for user {user_id}")

                return IdentityStatement(
                    id=existing.id,
                    user_id=user_id,
                    statement=statement,
                    created_at=existing.created_at,
                    last_reinforced_at=now,
                    reinforcement_count=existing.reinforcement_count,
                )
            else:
                # Create new statement
                cursor = conn.execute(
                    """
                    INSERT INTO identity_statements (
                        user_id, statement, created_at, last_reinforced_at, reinforcement_count
                    ) VALUES (?, ?, ?, ?, 0)
                    """,
                    (user_id, statement, now, now),
                )
                statement_id = cursor.lastrowid
                logger.info(f"Created identity statement for user {user_id}")

                return IdentityStatement(
                    id=statement_id,
                    user_id=user_id,
                    statement=statement,
                    created_at=now,
                    last_reinforced_at=now,
                    reinforcement_count=0,
                )

    def reinforce_statement(self, user_id: str) -> Optional[IdentityStatement]:
        """Reinforce the identity statement for a user.

        Called when user views/acknowledges their identity statement,
        strengthening the psychological commitment.

        Args:
            user_id: The user's unique identifier.

        Returns:
            Updated IdentityStatement if found, None otherwise.
        """
        existing = self.get_statement(user_id)
        if not existing:
            logger.warning(f"No identity statement found for user {user_id}")
            return None

        now = datetime.now(timezone.utc).isoformat()
        new_count = existing.reinforcement_count + 1

        with self._db._get_connection() as conn:
            conn.execute(
                """
                UPDATE identity_statements
                SET last_reinforced_at = ?, reinforcement_count = ?
                WHERE user_id = ?
                """,
                (now, new_count, user_id),
            )

        logger.info(
            f"Reinforced identity statement for user {user_id} "
            f"(count: {new_count})"
        )

        return IdentityStatement(
            id=existing.id,
            user_id=user_id,
            statement=existing.statement,
            created_at=existing.created_at,
            last_reinforced_at=now,
            reinforcement_count=new_count,
        )

    def delete_statement(self, user_id: str) -> bool:
        """Delete the identity statement for a user.

        Args:
            user_id: The user's unique identifier.

        Returns:
            True if deleted, False if not found.
        """
        with self._db._get_connection() as conn:
            result = conn.execute(
                "DELETE FROM identity_statements WHERE user_id = ?",
                (user_id,),
            )
            deleted = result.rowcount > 0

        if deleted:
            logger.info(f"Deleted identity statement for user {user_id}")
        return deleted

    def should_show_reinforcement(
        self,
        user_id: str,
        days_threshold: int = 7,
    ) -> bool:
        """Check if it's time to show a reinforcement reminder.

        Args:
            user_id: The user's unique identifier.
            days_threshold: Number of days between reinforcements (default 7).

        Returns:
            True if reinforcement should be shown.
        """
        statement = self.get_statement(user_id)
        if not statement:
            return False

        try:
            last_reinforced = datetime.fromisoformat(
                statement.last_reinforced_at.replace("Z", "+00:00")
            )
            now = datetime.now(timezone.utc)
            days_since = (now - last_reinforced).days

            return days_since >= days_threshold
        except (ValueError, TypeError):
            # If date parsing fails, show reinforcement
            return True


# Module-level singleton
_identity_service: Optional[IdentityService] = None


def get_identity_service(db: Optional[TrainingDatabase] = None) -> IdentityService:
    """Get or create the identity service singleton.

    Args:
        db: Optional database instance for initialization.

    Returns:
        IdentityService instance.
    """
    global _identity_service
    if _identity_service is None:
        _identity_service = IdentityService(db)
    return _identity_service
