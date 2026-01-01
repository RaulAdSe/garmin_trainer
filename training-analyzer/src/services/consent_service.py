"""
Consent service for managing user privacy preferences.

Handles LLM data sharing consent tracking and verification.
"""

import logging
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from .base import BaseService


class ConsentStatus(BaseModel):
    """Model representing user consent status."""

    user_id: str
    llm_data_sharing_consent: bool
    consent_date: Optional[str] = None
    consent_version: str = "v1"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConsentService(BaseService):
    """
    Service for managing user consent for LLM data sharing.

    Provides methods to check, record, and retrieve consent status
    for users regarding their training data being shared with LLMs.
    """

    CURRENT_CONSENT_VERSION = "v1"

    def __init__(
        self,
        db_path: str,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialize the consent service.

        Args:
            db_path: Path to the SQLite database
            logger: Optional logger instance
        """
        super().__init__(logger=logger)
        self._db_path = db_path

    def _get_connection(self):
        """Get a database connection."""
        import sqlite3

        return sqlite3.connect(self._db_path)

    def check_llm_consent(self, user_id: str) -> bool:
        """
        Check if a user has consented to LLM data sharing.

        Args:
            user_id: The user ID to check consent for

        Returns:
            True if the user has active consent, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT llm_data_sharing_consent
                FROM user_consent
                WHERE user_id = ?
                """,
                (user_id,),
            )

            row = cursor.fetchone()
            conn.close()

            if row is None:
                self.logger.debug(f"No consent record found for user {user_id}")
                return False

            return bool(row[0])

        except Exception as e:
            self.logger.error(f"Error checking consent for user {user_id}: {e}")
            return False

    def record_consent(self, user_id: str, consented: bool) -> bool:
        """
        Record a user's consent decision for LLM data sharing.

        Args:
            user_id: The user ID to record consent for
            consented: True if user consents, False if they decline/withdraw

        Returns:
            True if the consent was recorded successfully, False otherwise
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            now = datetime.utcnow().isoformat()

            # Use INSERT OR REPLACE to handle both new and existing records
            cursor.execute(
                """
                INSERT INTO user_consent (
                    user_id,
                    llm_data_sharing_consent,
                    consent_date,
                    consent_version,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    llm_data_sharing_consent = excluded.llm_data_sharing_consent,
                    consent_date = excluded.consent_date,
                    consent_version = excluded.consent_version,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    1 if consented else 0,
                    now if consented else None,
                    self.CURRENT_CONSENT_VERSION,
                    now,
                    now,
                ),
            )

            conn.commit()
            conn.close()

            action = "granted" if consented else "withdrawn"
            self.logger.info(f"Consent {action} for user {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error recording consent for user {user_id}: {e}")
            return False

    def get_consent_status(self, user_id: str) -> dict:
        """
        Get the full consent status for a user.

        Args:
            user_id: The user ID to get consent status for

        Returns:
            Dictionary containing consent status details:
            - user_id: The user ID
            - llm_data_sharing_consent: Boolean consent status
            - consent_date: When consent was given/updated (if any)
            - consent_version: Version of consent terms
            - exists: Whether a consent record exists
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    user_id,
                    llm_data_sharing_consent,
                    consent_date,
                    consent_version,
                    created_at,
                    updated_at
                FROM user_consent
                WHERE user_id = ?
                """,
                (user_id,),
            )

            row = cursor.fetchone()
            conn.close()

            if row is None:
                return {
                    "user_id": user_id,
                    "llm_data_sharing_consent": False,
                    "consent_date": None,
                    "consent_version": None,
                    "exists": False,
                }

            return {
                "user_id": row[0],
                "llm_data_sharing_consent": bool(row[1]),
                "consent_date": row[2],
                "consent_version": row[3],
                "created_at": row[4],
                "updated_at": row[5],
                "exists": True,
            }

        except Exception as e:
            self.logger.error(f"Error getting consent status for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "llm_data_sharing_consent": False,
                "consent_date": None,
                "consent_version": None,
                "exists": False,
                "error": str(e),
            }


# Singleton instance
_consent_service: Optional[ConsentService] = None


def get_consent_service(db_path: Optional[str] = None) -> ConsentService:
    """
    Get or create the singleton consent service instance.

    Args:
        db_path: Path to the SQLite database. Required on first call.

    Returns:
        The ConsentService singleton instance
    """
    global _consent_service

    if _consent_service is None:
        if db_path is None:
            raise ValueError("db_path is required when creating ConsentService")
        _consent_service = ConsentService(db_path=db_path)

    return _consent_service


def reset_consent_service() -> None:
    """Reset the singleton consent service instance (useful for testing)."""
    global _consent_service
    _consent_service = None
