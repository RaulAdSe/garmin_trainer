"""SQLite-backed repository for Garmin Connect credentials and sync management.

Provides secure storage and retrieval of Garmin credentials (pre-encrypted by service layer),
sync configuration, and sync history tracking for the multi-user platform.

NOTE: Encryption/decryption is handled by the service layer before calling these methods.
This repository stores credentials that are already encrypted.
"""

import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class GarminCredentials:
    """Garmin Connect credentials entity (encrypted values)."""

    user_id: str
    encrypted_email: str
    encrypted_password: str
    encryption_key_id: str = "v1"
    oauth1_token: Optional[str] = None
    oauth1_token_secret: Optional[str] = None
    session_data: Optional[str] = None
    garmin_user_id: Optional[str] = None
    garmin_display_name: Optional[str] = None
    is_valid: bool = True
    last_validation_at: Optional[datetime] = None
    validation_error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class GarminSyncConfig:
    """Garmin sync configuration for a user."""

    user_id: str
    auto_sync_enabled: bool = True
    sync_frequency: str = "daily"
    sync_time: str = "06:00"
    sync_activities: bool = True
    sync_wellness: bool = True
    sync_fitness_metrics: bool = True
    sync_sleep: bool = True
    initial_sync_days: int = 365
    incremental_sync_days: int = 7
    min_sync_interval_minutes: int = 60
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class GarminSyncHistory:
    """Record of a Garmin sync operation."""

    id: int
    user_id: str
    sync_type: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    status: str = "running"
    activities_synced: int = 0
    wellness_days_synced: int = 0
    fitness_days_synced: int = 0
    sync_from_date: Optional[date] = None
    sync_to_date: Optional[date] = None
    error_message: Optional[str] = None
    error_details: Optional[str] = None
    retry_count: int = 0


class GarminCredentialsRepository:
    """
    SQLite-backed repository for Garmin credentials and sync management.

    Provides secure storage of pre-encrypted Garmin credentials, sync configuration,
    and sync history tracking. Credentials are encrypted by the service layer
    before being passed to this repository.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the Garmin credentials repository.

        Args:
            db_path: Path to SQLite database file. If None, uses the default
                    training.db in the training-analyzer directory.
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            import os
            env_path = os.environ.get("TRAINING_DB_PATH")
            if env_path:
                self.db_path = Path(env_path)
            else:
                self.db_path = Path(__file__).parent.parent.parent.parent.parent / "training.db"

        self._ensure_tables_exist()

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
        """Ensure Garmin-related tables exist."""
        with self._get_connection() as conn:
            # Garmin credentials table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS garmin_credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL UNIQUE,
                    encrypted_email TEXT NOT NULL,
                    encrypted_password TEXT NOT NULL,
                    encryption_key_id TEXT NOT NULL DEFAULT 'v1',
                    oauth1_token TEXT,
                    oauth1_token_secret TEXT,
                    session_data TEXT,
                    garmin_user_id TEXT,
                    garmin_display_name TEXT,
                    is_valid INTEGER DEFAULT 1,
                    last_validation_at TEXT,
                    validation_error TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Garmin sync configuration table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS garmin_sync_config (
                    user_id TEXT PRIMARY KEY,
                    auto_sync_enabled INTEGER DEFAULT 1,
                    sync_frequency TEXT DEFAULT 'daily',
                    sync_time TEXT DEFAULT '06:00',
                    sync_activities INTEGER DEFAULT 1,
                    sync_wellness INTEGER DEFAULT 1,
                    sync_fitness_metrics INTEGER DEFAULT 1,
                    sync_sleep INTEGER DEFAULT 1,
                    initial_sync_days INTEGER DEFAULT 365,
                    incremental_sync_days INTEGER DEFAULT 7,
                    min_sync_interval_minutes INTEGER DEFAULT 60,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Garmin sync history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS garmin_sync_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    sync_type TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    duration_seconds INTEGER,
                    status TEXT DEFAULT 'running',
                    activities_synced INTEGER DEFAULT 0,
                    wellness_days_synced INTEGER DEFAULT 0,
                    fitness_days_synced INTEGER DEFAULT 0,
                    sync_from_date TEXT,
                    sync_to_date TEXT,
                    error_message TEXT,
                    error_details TEXT,
                    retry_count INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_garmin_creds_user
                ON garmin_credentials(user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_history_user
                ON garmin_sync_history(user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_history_started
                ON garmin_sync_history(started_at DESC)
            """)

    def _row_to_credentials(self, row: sqlite3.Row) -> GarminCredentials:
        """Convert a database row to a GarminCredentials entity."""
        def parse_datetime(val):
            if isinstance(val, str) and val:
                return datetime.fromisoformat(val)
            return val

        return GarminCredentials(
            user_id=row["user_id"],
            encrypted_email=row["encrypted_email"],
            encrypted_password=row["encrypted_password"],
            encryption_key_id=row["encryption_key_id"] or "v1",
            oauth1_token=row["oauth1_token"],
            oauth1_token_secret=row["oauth1_token_secret"],
            session_data=row["session_data"],
            garmin_user_id=row["garmin_user_id"],
            garmin_display_name=row["garmin_display_name"],
            is_valid=bool(row["is_valid"]),
            last_validation_at=parse_datetime(row["last_validation_at"]),
            validation_error=row["validation_error"],
            created_at=parse_datetime(row["created_at"]),
            updated_at=parse_datetime(row["updated_at"]),
        )

    def _row_to_sync_config(self, row: sqlite3.Row) -> GarminSyncConfig:
        """Convert a database row to a GarminSyncConfig entity."""
        def parse_datetime(val):
            if isinstance(val, str) and val:
                return datetime.fromisoformat(val)
            return val

        return GarminSyncConfig(
            user_id=row["user_id"],
            auto_sync_enabled=bool(row["auto_sync_enabled"]),
            sync_frequency=row["sync_frequency"] or "daily",
            sync_time=row["sync_time"] or "06:00",
            sync_activities=bool(row["sync_activities"]),
            sync_wellness=bool(row["sync_wellness"]),
            sync_fitness_metrics=bool(row["sync_fitness_metrics"]),
            sync_sleep=bool(row["sync_sleep"]),
            initial_sync_days=row["initial_sync_days"] or 365,
            incremental_sync_days=row["incremental_sync_days"] or 7,
            min_sync_interval_minutes=row["min_sync_interval_minutes"] or 60,
            created_at=parse_datetime(row["created_at"]),
            updated_at=parse_datetime(row["updated_at"]),
        )

    def _row_to_sync_history(self, row: sqlite3.Row) -> GarminSyncHistory:
        """Convert a database row to a GarminSyncHistory entity."""
        def parse_datetime(val):
            if isinstance(val, str) and val:
                return datetime.fromisoformat(val)
            return val

        def parse_date(val):
            if isinstance(val, str) and val:
                return date.fromisoformat(val)
            return val

        return GarminSyncHistory(
            id=row["id"],
            user_id=row["user_id"],
            sync_type=row["sync_type"],
            started_at=parse_datetime(row["started_at"]),
            completed_at=parse_datetime(row["completed_at"]),
            duration_seconds=row["duration_seconds"],
            status=row["status"] or "running",
            activities_synced=row["activities_synced"] or 0,
            wellness_days_synced=row["wellness_days_synced"] or 0,
            fitness_days_synced=row["fitness_days_synced"] or 0,
            sync_from_date=parse_date(row["sync_from_date"]),
            sync_to_date=parse_date(row["sync_to_date"]),
            error_message=row["error_message"],
            error_details=row["error_details"],
            retry_count=row["retry_count"] or 0,
        )

    # ==================== Credential Methods ====================

    def save_credentials(
        self,
        user_id: str,
        encrypted_email: str,
        encrypted_password: str,
        encryption_key_id: str = "v1",
        garmin_user_id: Optional[str] = None,
        garmin_display_name: Optional[str] = None,
    ) -> GarminCredentials:
        """
        Save encrypted Garmin credentials for a user.

        NOTE: Encryption must be performed by the service layer before calling this method.

        Args:
            user_id: The user's unique identifier
            encrypted_email: Pre-encrypted Garmin email
            encrypted_password: Pre-encrypted Garmin password
            encryption_key_id: ID of the encryption key used
            garmin_user_id: Garmin Connect user ID (optional)
            garmin_display_name: Garmin Connect display name (optional)

        Returns:
            The saved GarminCredentials entity
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO garmin_credentials
                (user_id, encrypted_email, encrypted_password, encryption_key_id,
                 garmin_user_id, garmin_display_name, is_valid, last_validation_at,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    encrypted_email = excluded.encrypted_email,
                    encrypted_password = excluded.encrypted_password,
                    encryption_key_id = excluded.encryption_key_id,
                    garmin_user_id = COALESCE(excluded.garmin_user_id, garmin_credentials.garmin_user_id),
                    garmin_display_name = COALESCE(excluded.garmin_display_name, garmin_credentials.garmin_display_name),
                    is_valid = 1,
                    validation_error = NULL,
                    last_validation_at = excluded.last_validation_at,
                    updated_at = excluded.updated_at
            """, (
                user_id,
                encrypted_email,
                encrypted_password,
                encryption_key_id,
                garmin_user_id,
                garmin_display_name,
                now,
                now,
                now,
            ))

        return GarminCredentials(
            user_id=user_id,
            encrypted_email=encrypted_email,
            encrypted_password=encrypted_password,
            encryption_key_id=encryption_key_id,
            garmin_user_id=garmin_user_id,
            garmin_display_name=garmin_display_name,
            is_valid=True,
            last_validation_at=datetime.fromisoformat(now),
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )

    def get_credentials(self, user_id: str) -> Optional[GarminCredentials]:
        """
        Retrieve encrypted Garmin credentials for a user.

        NOTE: Decryption must be performed by the service layer after retrieval.

        Args:
            user_id: The user's unique identifier

        Returns:
            The GarminCredentials if found, None otherwise
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM garmin_credentials WHERE user_id = ?",
                (user_id,)
            ).fetchone()

            if row:
                return self._row_to_credentials(row)
            return None

    def delete_credentials(self, user_id: str) -> bool:
        """
        Delete Garmin credentials for a user.

        Also deletes associated sync config and history.

        Args:
            user_id: The user's unique identifier

        Returns:
            True if credentials were deleted, False if not found
        """
        with self._get_connection() as conn:
            # Delete credentials
            cursor = conn.execute(
                "DELETE FROM garmin_credentials WHERE user_id = ?",
                (user_id,)
            )
            deleted = cursor.rowcount > 0

            # Also delete sync config
            conn.execute(
                "DELETE FROM garmin_sync_config WHERE user_id = ?",
                (user_id,)
            )

            return deleted

    def update_validation_status(
        self,
        user_id: str,
        is_valid: bool,
        validation_error: Optional[str] = None,
    ) -> bool:
        """
        Update the validation status of stored credentials.

        Args:
            user_id: The user's unique identifier
            is_valid: Whether the credentials are valid
            validation_error: Error message if validation failed

        Returns:
            True if update was successful, False if no credentials found
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE garmin_credentials
                SET is_valid = ?,
                    validation_error = ?,
                    last_validation_at = ?,
                    updated_at = ?
                WHERE user_id = ?
            """, (
                1 if is_valid else 0,
                validation_error,
                now,
                now,
                user_id,
            ))
            return cursor.rowcount > 0

    # ==================== Sync Config Methods ====================

    def get_sync_config(self, user_id: str) -> Optional[GarminSyncConfig]:
        """
        Retrieve sync configuration for a user.

        Args:
            user_id: The user's unique identifier

        Returns:
            The GarminSyncConfig if found, None otherwise
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM garmin_sync_config WHERE user_id = ?",
                (user_id,)
            ).fetchone()

            if row:
                return self._row_to_sync_config(row)
            return None

    def update_sync_config(
        self,
        user_id: str,
        auto_sync_enabled: Optional[bool] = None,
        sync_frequency: Optional[str] = None,
        sync_time: Optional[str] = None,
        sync_activities: Optional[bool] = None,
        sync_wellness: Optional[bool] = None,
        sync_fitness_metrics: Optional[bool] = None,
        sync_sleep: Optional[bool] = None,
        initial_sync_days: Optional[int] = None,
        incremental_sync_days: Optional[int] = None,
        min_sync_interval_minutes: Optional[int] = None,
    ) -> GarminSyncConfig:
        """
        Update or create sync configuration for a user.

        Args:
            user_id: The user's unique identifier
            auto_sync_enabled: Whether auto-sync is enabled
            sync_frequency: Sync frequency ('hourly', 'daily', 'weekly')
            sync_time: Preferred sync time (HH:MM format, UTC)
            sync_activities: Whether to sync activities
            sync_wellness: Whether to sync wellness data
            sync_fitness_metrics: Whether to sync fitness metrics
            sync_sleep: Whether to sync sleep data
            initial_sync_days: Days to sync on first sync
            incremental_sync_days: Days to sync on incremental syncs
            min_sync_interval_minutes: Minimum interval between syncs

        Returns:
            The updated GarminSyncConfig entity
        """
        now = datetime.now().isoformat()

        # Build update values, using defaults for None
        values = {
            "auto_sync_enabled": 1 if auto_sync_enabled is True else (0 if auto_sync_enabled is False else None),
            "sync_frequency": sync_frequency,
            "sync_time": sync_time,
            "sync_activities": 1 if sync_activities is True else (0 if sync_activities is False else None),
            "sync_wellness": 1 if sync_wellness is True else (0 if sync_wellness is False else None),
            "sync_fitness_metrics": 1 if sync_fitness_metrics is True else (0 if sync_fitness_metrics is False else None),
            "sync_sleep": 1 if sync_sleep is True else (0 if sync_sleep is False else None),
            "initial_sync_days": initial_sync_days,
            "incremental_sync_days": incremental_sync_days,
            "min_sync_interval_minutes": min_sync_interval_minutes,
        }

        with self._get_connection() as conn:
            # Check if config exists
            existing = conn.execute(
                "SELECT user_id FROM garmin_sync_config WHERE user_id = ?",
                (user_id,)
            ).fetchone()

            if existing:
                # Update existing config
                updates = []
                params = []
                for key, value in values.items():
                    if value is not None:
                        updates.append(f"{key} = ?")
                        params.append(value)

                if updates:
                    updates.append("updated_at = ?")
                    params.append(now)
                    params.append(user_id)

                    query = f"UPDATE garmin_sync_config SET {', '.join(updates)} WHERE user_id = ?"
                    conn.execute(query, params)
            else:
                # Create new config with defaults
                conn.execute("""
                    INSERT INTO garmin_sync_config
                    (user_id, auto_sync_enabled, sync_frequency, sync_time,
                     sync_activities, sync_wellness, sync_fitness_metrics, sync_sleep,
                     initial_sync_days, incremental_sync_days, min_sync_interval_minutes,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    values.get("auto_sync_enabled", 1),
                    values.get("sync_frequency", "daily"),
                    values.get("sync_time", "06:00"),
                    values.get("sync_activities", 1),
                    values.get("sync_wellness", 1),
                    values.get("sync_fitness_metrics", 1),
                    values.get("sync_sleep", 1),
                    values.get("initial_sync_days", 365),
                    values.get("incremental_sync_days", 7),
                    values.get("min_sync_interval_minutes", 60),
                    now,
                    now,
                ))

        return self.get_sync_config(user_id)

    # ==================== Sync History Methods ====================

    def get_sync_history(
        self,
        user_id: str,
        limit: int = 10,
    ) -> List[GarminSyncHistory]:
        """
        Retrieve sync history for a user.

        Args:
            user_id: The user's unique identifier
            limit: Maximum number of records to return

        Returns:
            List of GarminSyncHistory entities, most recent first
        """
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM garmin_sync_history
                WHERE user_id = ?
                ORDER BY started_at DESC
                LIMIT ?
            """, (user_id, limit)).fetchall()

            return [self._row_to_sync_history(row) for row in rows]

    def start_sync(
        self,
        user_id: str,
        sync_type: str,
        sync_from_date: Optional[date] = None,
        sync_to_date: Optional[date] = None,
    ) -> int:
        """
        Record the start of a sync operation.

        Args:
            user_id: The user's unique identifier
            sync_type: Type of sync ('manual', 'scheduled', 'webhook')
            sync_from_date: Start date for sync range
            sync_to_date: End date for sync range

        Returns:
            The ID of the created sync history record
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO garmin_sync_history
                (user_id, sync_type, started_at, status, sync_from_date, sync_to_date)
                VALUES (?, ?, ?, 'running', ?, ?)
            """, (
                user_id,
                sync_type,
                now,
                sync_from_date.isoformat() if sync_from_date else None,
                sync_to_date.isoformat() if sync_to_date else None,
            ))
            return cursor.lastrowid

    def complete_sync(
        self,
        sync_id: int,
        status: str,
        activities_synced: int = 0,
        wellness_days_synced: int = 0,
        fitness_days_synced: int = 0,
        error_message: Optional[str] = None,
        error_details: Optional[str] = None,
    ) -> bool:
        """
        Record the completion of a sync operation.

        Args:
            sync_id: The sync history record ID
            status: Final status ('completed', 'failed', 'partial')
            activities_synced: Number of activities synced
            wellness_days_synced: Number of wellness days synced
            fitness_days_synced: Number of fitness metric days synced
            error_message: Error message if sync failed
            error_details: Detailed error information (JSON)

        Returns:
            True if update was successful, False if record not found
        """
        now = datetime.now()

        with self._get_connection() as conn:
            # Get start time to calculate duration
            row = conn.execute(
                "SELECT started_at FROM garmin_sync_history WHERE id = ?",
                (sync_id,)
            ).fetchone()

            if not row:
                return False

            started_at = datetime.fromisoformat(row["started_at"])
            duration_seconds = int((now - started_at).total_seconds())

            cursor = conn.execute("""
                UPDATE garmin_sync_history
                SET completed_at = ?,
                    duration_seconds = ?,
                    status = ?,
                    activities_synced = ?,
                    wellness_days_synced = ?,
                    fitness_days_synced = ?,
                    error_message = ?,
                    error_details = ?
                WHERE id = ?
            """, (
                now.isoformat(),
                duration_seconds,
                status,
                activities_synced,
                wellness_days_synced,
                fitness_days_synced,
                error_message,
                error_details,
                sync_id,
            ))
            return cursor.rowcount > 0

    def get_all_auto_sync_users(self) -> List[str]:
        """
        Get all user IDs with valid credentials and auto-sync enabled.

        Returns:
            List of user IDs eligible for auto-sync
        """
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT gc.user_id
                FROM garmin_credentials gc
                JOIN garmin_sync_config gsc ON gc.user_id = gsc.user_id
                WHERE gc.is_valid = 1 AND gsc.auto_sync_enabled = 1
            """).fetchall()
            return [row["user_id"] for row in rows]

    def get_last_successful_sync(self, user_id: str) -> Optional[GarminSyncHistory]:
        """
        Get the most recent successful sync for a user.

        Args:
            user_id: The user's unique identifier

        Returns:
            The most recent successful GarminSyncHistory, or None
        """
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM garmin_sync_history
                WHERE user_id = ? AND status = 'completed'
                ORDER BY started_at DESC
                LIMIT 1
            """, (user_id,)).fetchone()

            if row:
                return self._row_to_sync_history(row)
            return None


# Singleton instance for dependency injection
_garmin_credentials_repository: Optional[GarminCredentialsRepository] = None


def get_garmin_credentials_repository() -> GarminCredentialsRepository:
    """Get or create the singleton GarminCredentialsRepository instance."""
    global _garmin_credentials_repository
    if _garmin_credentials_repository is None:
        _garmin_credentials_repository = GarminCredentialsRepository()
    return _garmin_credentials_repository
