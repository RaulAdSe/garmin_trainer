"""SQLite-backed repository for Strava integration data.

Provides persistent storage for Strava OAuth credentials, user preferences,
and activity synchronization tracking.

OAuth tokens (access_token, refresh_token) are encrypted at rest using the
CredentialEncryption service. Encryption is handled internally by this repository.
The repository automatically:
- Encrypts tokens when saving credentials
- Decrypts tokens when retrieving credentials
- Supports migration from legacy unencrypted storage
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from contextlib import contextmanager
import os

from .base import Repository
from ...models.strava import (
    StravaCredentials,
    StravaPreferences,
    StravaActivitySync,
    SyncStatus,
)
from ...services.encryption import CredentialEncryption, CredentialEncryptionError

logger = logging.getLogger(__name__)


class StravaCredentialEncryptionError(Exception):
    """Raised when Strava credential encryption/decryption fails.

    This error indicates that the CREDENTIAL_ENCRYPTION_KEY is missing,
    invalid, or different from the key used to encrypt stored credentials.
    """
    pass


class StravaRepository:
    """
    SQLite-backed repository for Strava integration data.

    Handles:
    - OAuth credentials storage and retrieval
    - User preferences for Strava integration
    - Activity synchronization tracking
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the Strava repository.

        Args:
            db_path: Path to SQLite database file. If None, uses the default
                    training.db in the training-analyzer directory.
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            # Use the same default path as TrainingDatabase
            env_path = os.environ.get("TRAINING_DB_PATH")
            if env_path:
                self.db_path = Path(env_path)
            else:
                self.db_path = Path(__file__).parent.parent.parent.parent / "training.db"

        self._encryption: Optional[CredentialEncryption] = None
        self._ensure_tables_exist()

    def _get_encryption(self) -> CredentialEncryption:
        """Get or create the encryption service."""
        if self._encryption is None:
            self._encryption = CredentialEncryption()
        return self._encryption

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_tables_exist(self):
        """Ensure the Strava tables exist."""
        with self._get_connection() as conn:
            # Strava credentials table with encrypted token columns
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strava_credentials (
                    user_id TEXT PRIMARY KEY DEFAULT 'default',
                    encrypted_access_token TEXT,
                    encrypted_refresh_token TEXT,
                    encryption_key_id TEXT DEFAULT 'v1',
                    access_token TEXT,
                    refresh_token TEXT,
                    expires_at TEXT NOT NULL,
                    athlete_id TEXT,
                    athlete_name TEXT,
                    scope TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Check if we need to add encrypted columns to existing table
            cursor = conn.execute("PRAGMA table_info(strava_credentials)")
            columns = {row[1] for row in cursor.fetchall()}

            if "encrypted_access_token" not in columns:
                conn.execute(
                    "ALTER TABLE strava_credentials ADD COLUMN encrypted_access_token TEXT"
                )
            if "encrypted_refresh_token" not in columns:
                conn.execute(
                    "ALTER TABLE strava_credentials ADD COLUMN encrypted_refresh_token TEXT"
                )
            if "encryption_key_id" not in columns:
                conn.execute(
                    "ALTER TABLE strava_credentials ADD COLUMN encryption_key_id TEXT DEFAULT 'v1'"
                )

            # Strava preferences table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strava_preferences (
                    user_id TEXT PRIMARY KEY DEFAULT 'default',
                    auto_update_description BOOLEAN DEFAULT TRUE,
                    include_score BOOLEAN DEFAULT TRUE,
                    include_summary BOOLEAN DEFAULT TRUE,
                    include_link BOOLEAN DEFAULT TRUE,
                    use_extended_format BOOLEAN DEFAULT FALSE,
                    custom_footer TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Activity sync table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strava_activity_sync (
                    local_activity_id TEXT PRIMARY KEY,
                    strava_activity_id INTEGER NOT NULL,
                    sync_status TEXT DEFAULT 'pending',
                    last_synced_at TEXT,
                    description_updated BOOLEAN DEFAULT FALSE,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_strava_sync_status
                ON strava_activity_sync(sync_status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_strava_activity
                ON strava_activity_sync(strava_activity_id)
            """)

            # OAuth state table for CSRF protection
            conn.execute("""
                CREATE TABLE IF NOT EXISTS oauth_states (
                    state TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_oauth_states_created
                ON oauth_states(created_at)
            """)

    # =========================================================================
    # OAuth State Methods
    # =========================================================================

    def store_oauth_state(self, state: str) -> None:
        """
        Store an OAuth state token for CSRF validation.

        Also cleans up expired states (older than 10 minutes) during storage.

        Args:
            state: The OAuth state token to store
        """
        with self._get_connection() as conn:
            # Store the new state
            conn.execute(
                "INSERT OR REPLACE INTO oauth_states (state, created_at) VALUES (?, ?)",
                (state, datetime.now().isoformat())
            )

            # Clean up expired states (older than 10 minutes)
            self._cleanup_expired_states(conn)

    def validate_oauth_state(self, state: str) -> bool:
        """
        Validate and consume an OAuth state token.

        The state is deleted after validation to prevent replay attacks.

        Args:
            state: The OAuth state token to validate

        Returns:
            True if state was valid, False otherwise
        """
        with self._get_connection() as conn:
            # Check if state exists
            row = conn.execute(
                "SELECT created_at FROM oauth_states WHERE state = ?",
                (state,)
            ).fetchone()

            if not row:
                return False

            # Check if state is not expired (10 minute validity)
            created_at = datetime.fromisoformat(row["created_at"])
            if (datetime.now() - created_at).total_seconds() > 600:
                # State expired, delete it and return False
                conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
                return False

            # Valid state - delete it to prevent reuse (consume the token)
            conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
            return True

    def _cleanup_expired_states(self, conn=None) -> int:
        """
        Remove OAuth states older than 10 minutes.

        Args:
            conn: Optional database connection to reuse

        Returns:
            Number of expired states removed
        """
        cutoff = (datetime.now() - timedelta(minutes=10)).isoformat()

        if conn is not None:
            cursor = conn.execute(
                "DELETE FROM oauth_states WHERE created_at < ?",
                (cutoff,)
            )
            return cursor.rowcount

        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM oauth_states WHERE created_at < ?",
                (cutoff,)
            )
            return cursor.rowcount

    def cleanup_expired_oauth_states(self) -> int:
        """
        Public method to clean up expired OAuth states.

        Can be called periodically by a background task.

        Returns:
            Number of expired states removed
        """
        return self._cleanup_expired_states()

    # =========================================================================
    # Credentials Methods
    # =========================================================================

    def save_strava_credentials(self, credentials: StravaCredentials) -> StravaCredentials:
        """
        Save or update Strava OAuth credentials.

        Tokens are encrypted before storage for security.

        Args:
            credentials: The credentials to save

        Returns:
            The saved credentials
        """
        # Encrypt the tokens
        encryption = self._get_encryption()
        encrypted_access_token = encryption.encrypt(credentials.access_token)
        encrypted_refresh_token = encryption.encrypt(credentials.refresh_token)

        with self._get_connection() as conn:
            # Check if record exists to preserve created_at
            existing = conn.execute(
                "SELECT created_at FROM strava_credentials WHERE user_id = ?",
                (credentials.user_id,)
            ).fetchone()

            if existing:
                # Update existing record with encrypted tokens
                # Clear plaintext columns during update
                conn.execute("""
                    UPDATE strava_credentials
                    SET encrypted_access_token = ?,
                        encrypted_refresh_token = ?,
                        encryption_key_id = 'v1',
                        access_token = NULL,
                        refresh_token = NULL,
                        expires_at = ?,
                        athlete_id = ?,
                        athlete_name = ?,
                        scope = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (
                    encrypted_access_token,
                    encrypted_refresh_token,
                    credentials.expires_at,
                    credentials.athlete_id,
                    credentials.athlete_name,
                    credentials.scope,
                    credentials.user_id,
                ))
            else:
                # Insert new record with encrypted tokens
                conn.execute("""
                    INSERT INTO strava_credentials
                    (user_id, encrypted_access_token, encrypted_refresh_token,
                     encryption_key_id, expires_at, athlete_id, athlete_name,
                     scope, created_at, updated_at)
                    VALUES (?, ?, ?, 'v1', ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    credentials.user_id,
                    encrypted_access_token,
                    encrypted_refresh_token,
                    credentials.expires_at,
                    credentials.athlete_id,
                    credentials.athlete_name,
                    credentials.scope,
                ))

        return credentials

    def get_strava_credentials(self, user_id: str = "default") -> Optional[StravaCredentials]:
        """
        Retrieve Strava credentials for a user.

        Tokens are decrypted after retrieval. Supports migration from
        unencrypted storage by checking for plaintext tokens and
        encrypting them on first access.

        Args:
            user_id: The user identifier (defaults to 'default')

        Returns:
            StravaCredentials if found, None otherwise
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM strava_credentials WHERE user_id = ?",
                (user_id,)
            ).fetchone()

            if not row:
                return None

            # Check for encrypted tokens first
            encrypted_access = row["encrypted_access_token"] if "encrypted_access_token" in row.keys() else None
            encrypted_refresh = row["encrypted_refresh_token"] if "encrypted_refresh_token" in row.keys() else None

            # Check for legacy plaintext tokens
            plaintext_access = row["access_token"] if "access_token" in row.keys() else None
            plaintext_refresh = row["refresh_token"] if "refresh_token" in row.keys() else None

            access_token = None
            refresh_token = None

            if encrypted_access and encrypted_refresh:
                # Use encrypted tokens
                try:
                    encryption = self._get_encryption()
                    access_token = encryption.decrypt(encrypted_access)
                    refresh_token = encryption.decrypt(encrypted_refresh)
                except CredentialEncryptionError as e:
                    logger.error(f"Failed to decrypt Strava tokens for user {user_id}: {e}")
                    return None
            elif plaintext_access and plaintext_refresh:
                # Migration case: plaintext tokens exist but no encrypted ones
                # Use them and migrate to encrypted storage
                access_token = plaintext_access
                refresh_token = plaintext_refresh

                # Migrate to encrypted storage
                try:
                    credentials = StravaCredentials(
                        user_id=row["user_id"],
                        access_token=access_token,
                        refresh_token=refresh_token,
                        expires_at=row["expires_at"],
                        athlete_id=row["athlete_id"],
                        athlete_name=row["athlete_name"],
                        scope=row["scope"],
                        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                        updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
                    )
                    # Re-save with encryption (this will encrypt and clear plaintext)
                    self.save_strava_credentials(credentials)
                    logger.info(f"Migrated Strava credentials to encrypted storage for user {user_id}")
                except CredentialEncryptionError as e:
                    logger.warning(f"Could not migrate Strava credentials for user {user_id}: {e}")
                    # Still return credentials even if migration failed
            else:
                # No valid tokens found
                logger.warning(f"No valid Strava tokens found for user {user_id}")
                return None

            return StravaCredentials(
                user_id=row["user_id"],
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=row["expires_at"],
                athlete_id=row["athlete_id"],
                athlete_name=row["athlete_name"],
                scope=row["scope"],
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
            )

    def delete_strava_credentials(self, user_id: str = "default") -> bool:
        """
        Delete Strava credentials for a user.

        Args:
            user_id: The user identifier (defaults to 'default')

        Returns:
            True if credentials were deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM strava_credentials WHERE user_id = ?",
                (user_id,)
            )
            return cursor.rowcount > 0

    # =========================================================================
    # Preferences Methods
    # =========================================================================

    def save_strava_preferences(self, preferences: StravaPreferences) -> StravaPreferences:
        """
        Save or update Strava preferences for a user.

        Args:
            preferences: The preferences to save

        Returns:
            The saved preferences
        """
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO strava_preferences
                (user_id, auto_update_description, include_score, include_summary,
                 include_link, use_extended_format, custom_footer, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                preferences.user_id,
                preferences.auto_update_description,
                preferences.include_score,
                preferences.include_summary,
                preferences.include_link,
                preferences.use_extended_format,
                preferences.custom_footer,
            ))

        return preferences

    def get_strava_preferences(self, user_id: str = "default") -> StravaPreferences:
        """
        Retrieve Strava preferences for a user.

        If no preferences exist, returns default preferences.

        Args:
            user_id: The user identifier (defaults to 'default')

        Returns:
            StravaPreferences (existing or defaults)
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM strava_preferences WHERE user_id = ?",
                (user_id,)
            ).fetchone()

            if row:
                # Use .get() with defaults for backwards compatibility with older DB schemas
                row_dict = dict(row)
                return StravaPreferences(
                    user_id=row_dict.get("user_id", user_id),
                    auto_update_description=bool(row_dict.get("auto_update_description", True)),
                    include_score=bool(row_dict.get("include_score", True)),
                    include_summary=bool(row_dict.get("include_summary", True)),
                    include_link=bool(row_dict.get("include_link", True)),
                    use_extended_format=bool(row_dict.get("use_extended_format", False)),
                    custom_footer=row_dict.get("custom_footer"),
                    updated_at=datetime.fromisoformat(row_dict["updated_at"]) if row_dict.get("updated_at") else None,
                )

            # Return default preferences
            return StravaPreferences(user_id=user_id)

    def update_strava_preferences(
        self,
        user_id: str = "default",
        auto_update_description: Optional[bool] = None,
        include_score: Optional[bool] = None,
        include_summary: Optional[bool] = None,
        include_link: Optional[bool] = None,
        use_extended_format: Optional[bool] = None,
        custom_footer: Optional[str] = None,
    ) -> StravaPreferences:
        """
        Update specific preference fields for a user.

        Only updates fields that are provided (not None).

        Args:
            user_id: The user identifier
            auto_update_description: Auto-update Strava descriptions
            include_score: Include score in description
            include_summary: Include summary in description
            include_link: Include analysis link in description
            use_extended_format: Use extended description format
            custom_footer: Custom footer text

        Returns:
            Updated StravaPreferences
        """
        current = self.get_strava_preferences(user_id)

        # Update only provided fields
        updated = StravaPreferences(
            user_id=user_id,
            auto_update_description=auto_update_description if auto_update_description is not None else current.auto_update_description,
            include_score=include_score if include_score is not None else current.include_score,
            include_summary=include_summary if include_summary is not None else current.include_summary,
            include_link=include_link if include_link is not None else current.include_link,
            use_extended_format=use_extended_format if use_extended_format is not None else current.use_extended_format,
            custom_footer=custom_footer if custom_footer is not None else current.custom_footer,
        )

        return self.save_strava_preferences(updated)

    # =========================================================================
    # Activity Sync Methods
    # =========================================================================

    def save_activity_sync(
        self,
        local_activity_id: str,
        strava_activity_id: int,
        sync_status: SyncStatus = SyncStatus.PENDING,
    ) -> StravaActivitySync:
        """
        Save or update an activity sync record.

        Args:
            local_activity_id: Local (Garmin) activity ID
            strava_activity_id: Strava activity ID
            sync_status: Current sync status

        Returns:
            The saved StravaActivitySync record
        """
        with self._get_connection() as conn:
            # Check if record exists
            existing = conn.execute(
                "SELECT created_at FROM strava_activity_sync WHERE local_activity_id = ?",
                (local_activity_id,)
            ).fetchone()

            now = datetime.now().isoformat()

            if existing:
                conn.execute("""
                    UPDATE strava_activity_sync
                    SET strava_activity_id = ?,
                        sync_status = ?,
                        last_synced_at = ?
                    WHERE local_activity_id = ?
                """, (
                    strava_activity_id,
                    sync_status.value,
                    now if sync_status == SyncStatus.SYNCED else None,
                    local_activity_id,
                ))
            else:
                conn.execute("""
                    INSERT INTO strava_activity_sync
                    (local_activity_id, strava_activity_id, sync_status,
                     last_synced_at, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    local_activity_id,
                    strava_activity_id,
                    sync_status.value,
                    now if sync_status == SyncStatus.SYNCED else None,
                ))

        return StravaActivitySync(
            local_activity_id=local_activity_id,
            strava_activity_id=strava_activity_id,
            sync_status=sync_status,
            last_synced_at=now if sync_status == SyncStatus.SYNCED else None,
        )

    def get_activity_sync(self, local_activity_id: str) -> Optional[StravaActivitySync]:
        """
        Retrieve an activity sync record by local activity ID.

        Args:
            local_activity_id: The local (Garmin) activity ID

        Returns:
            StravaActivitySync if found, None otherwise
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM strava_activity_sync WHERE local_activity_id = ?",
                (local_activity_id,)
            ).fetchone()

            if row:
                return StravaActivitySync(
                    local_activity_id=row["local_activity_id"],
                    strava_activity_id=row["strava_activity_id"],
                    sync_status=SyncStatus(row["sync_status"]),
                    last_synced_at=row["last_synced_at"],
                    description_updated=bool(row["description_updated"]),
                    error_message=row["error_message"],
                    created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                )
            return None

    def get_activity_sync_by_strava_id(self, strava_activity_id: int) -> Optional[StravaActivitySync]:
        """
        Retrieve an activity sync record by Strava activity ID.

        Args:
            strava_activity_id: The Strava activity ID

        Returns:
            StravaActivitySync if found, None otherwise
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM strava_activity_sync WHERE strava_activity_id = ?",
                (strava_activity_id,)
            ).fetchone()

            if row:
                return StravaActivitySync(
                    local_activity_id=row["local_activity_id"],
                    strava_activity_id=row["strava_activity_id"],
                    sync_status=SyncStatus(row["sync_status"]),
                    last_synced_at=row["last_synced_at"],
                    description_updated=bool(row["description_updated"]),
                    error_message=row["error_message"],
                    created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                )
            return None

    def update_activity_sync_status(
        self,
        local_activity_id: str,
        sync_status: SyncStatus,
        error_message: Optional[str] = None,
        description_updated: Optional[bool] = None,
    ) -> Optional[StravaActivitySync]:
        """
        Update the sync status for an activity.

        Args:
            local_activity_id: The local activity ID
            sync_status: New sync status
            error_message: Error message if status is FAILED
            description_updated: Whether description was updated

        Returns:
            Updated StravaActivitySync if found, None otherwise
        """
        with self._get_connection() as conn:
            now = datetime.now().isoformat()

            # Build update query dynamically
            updates = ["sync_status = ?"]
            params = [sync_status.value]

            if sync_status == SyncStatus.SYNCED:
                updates.append("last_synced_at = ?")
                params.append(now)

            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)

            if description_updated is not None:
                updates.append("description_updated = ?")
                params.append(description_updated)

            params.append(local_activity_id)

            cursor = conn.execute(
                f"UPDATE strava_activity_sync SET {', '.join(updates)} WHERE local_activity_id = ?",
                params
            )

            row_updated = cursor.rowcount > 0

        # Return the updated record after commit
        if row_updated:
            return self.get_activity_sync(local_activity_id)
        return None

    def get_pending_syncs(self, limit: int = 100) -> List[StravaActivitySync]:
        """
        Get all activities pending synchronization.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of pending StravaActivitySync records
        """
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM strava_activity_sync
                WHERE sync_status = ?
                ORDER BY created_at ASC
                LIMIT ?
            """, (SyncStatus.PENDING.value, limit)).fetchall()

            return [
                StravaActivitySync(
                    local_activity_id=row["local_activity_id"],
                    strava_activity_id=row["strava_activity_id"],
                    sync_status=SyncStatus(row["sync_status"]),
                    last_synced_at=row["last_synced_at"],
                    description_updated=bool(row["description_updated"]),
                    error_message=row["error_message"],
                    created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                )
                for row in rows
            ]

    def get_failed_syncs(self, limit: int = 100) -> List[StravaActivitySync]:
        """
        Get all activities that failed synchronization.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of failed StravaActivitySync records
        """
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM strava_activity_sync
                WHERE sync_status = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (SyncStatus.FAILED.value, limit)).fetchall()

            return [
                StravaActivitySync(
                    local_activity_id=row["local_activity_id"],
                    strava_activity_id=row["strava_activity_id"],
                    sync_status=SyncStatus(row["sync_status"]),
                    last_synced_at=row["last_synced_at"],
                    description_updated=bool(row["description_updated"]),
                    error_message=row["error_message"],
                    created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                )
                for row in rows
            ]

    def delete_activity_sync(self, local_activity_id: str) -> bool:
        """
        Delete an activity sync record.

        Args:
            local_activity_id: The local activity ID

        Returns:
            True if record was deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM strava_activity_sync WHERE local_activity_id = ?",
                (local_activity_id,)
            )
            return cursor.rowcount > 0

    def get_sync_stats(self) -> dict:
        """
        Get statistics about activity synchronization.

        Returns:
            Dictionary with sync statistics
        """
        with self._get_connection() as conn:
            # Count by status
            status_counts = conn.execute("""
                SELECT sync_status, COUNT(*) as count
                FROM strava_activity_sync
                GROUP BY sync_status
            """).fetchall()

            stats = {status.value: 0 for status in SyncStatus}
            for row in status_counts:
                stats[row["sync_status"]] = row["count"]

            # Get total count
            total = conn.execute(
                "SELECT COUNT(*) as count FROM strava_activity_sync"
            ).fetchone()["count"]

            # Get last sync time
            last_sync = conn.execute("""
                SELECT MAX(last_synced_at) as last_sync
                FROM strava_activity_sync
                WHERE sync_status = ?
            """, (SyncStatus.SYNCED.value,)).fetchone()["last_sync"]

            return {
                "total": total,
                "pending": stats.get("pending", 0),
                "synced": stats.get("synced", 0),
                "failed": stats.get("failed", 0),
                "last_synced_at": last_sync,
            }


# Singleton instance for dependency injection
_strava_repository: Optional[StravaRepository] = None


def get_strava_repository() -> StravaRepository:
    """Get or create the singleton StravaRepository instance."""
    global _strava_repository
    if _strava_repository is None:
        _strava_repository = StravaRepository()
    return _strava_repository
