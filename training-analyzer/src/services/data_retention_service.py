"""Data retention service for cleaning up old data.

Handles automatic cleanup of:
- Expired user sessions (older than 30 days by default)
- Old AI usage logs (older than 90 days by default)
- Historical sync logs (older than 90 days by default)
- Old activity data (configurable, disabled by default)

Addresses SECURITY.md finding #17 - No Data Retention Policy.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..config import get_settings
from ..db.database import TrainingDatabase

logger = logging.getLogger(__name__)


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""

    category: str
    records_deleted: int
    cutoff_date: str
    success: bool
    error: Optional[str] = None


@dataclass
class DataRetentionReport:
    """Complete report of all cleanup operations."""

    timestamp: str
    results: list[CleanupResult]
    total_deleted: int
    duration_seconds: float

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "results": [
                {
                    "category": r.category,
                    "records_deleted": r.records_deleted,
                    "cutoff_date": r.cutoff_date,
                    "success": r.success,
                    "error": r.error,
                }
                for r in self.results
            ],
            "total_deleted": self.total_deleted,
            "duration_seconds": self.duration_seconds,
        }


class DataRetentionService:
    """Service for managing data retention and cleanup.

    Provides methods to clean up various types of old data based on
    configurable retention periods.
    """

    def __init__(self, db: TrainingDatabase) -> None:
        """Initialize the data retention service.

        Args:
            db: Training database instance.
        """
        self._db = db
        self._settings = get_settings()

    def cleanup_expired_sessions(
        self, retention_days: Optional[int] = None
    ) -> CleanupResult:
        """Delete user sessions that have expired or are older than retention period.

        Args:
            retention_days: Override for retention period. Defaults to config value.

        Returns:
            CleanupResult with details of the cleanup operation.
        """
        days = retention_days or self._settings.retention_sessions_days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()

        try:
            # Delete sessions that are:
            # 1. Expired (expires_at < now), OR
            # 2. Created more than retention_days ago
            query = """
                DELETE FROM user_sessions
                WHERE expires_at < ? OR created_at < ?
            """
            cursor = self._db.conn.execute(query, (cutoff_str, cutoff_str))
            deleted_count = cursor.rowcount
            self._db.conn.commit()

            logger.info(
                f"Cleaned up {deleted_count} expired sessions "
                f"(cutoff: {cutoff_str})"
            )

            return CleanupResult(
                category="user_sessions",
                records_deleted=deleted_count,
                cutoff_date=cutoff_str,
                success=True,
            )
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return CleanupResult(
                category="user_sessions",
                records_deleted=0,
                cutoff_date=cutoff_str,
                success=False,
                error=str(e),
            )

    def cleanup_ai_usage_logs(
        self, retention_days: Optional[int] = None
    ) -> CleanupResult:
        """Delete old AI usage tracking records.

        Args:
            retention_days: Override for retention period. Defaults to config value.

        Returns:
            CleanupResult with details of the cleanup operation.
        """
        days = retention_days or self._settings.retention_ai_usage_logs_days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()

        try:
            # Delete user_usage records older than retention period
            # Keep at least the current period for each user
            query = """
                DELETE FROM user_usage
                WHERE period_end < ?
                AND id NOT IN (
                    SELECT id FROM user_usage
                    WHERE user_id IN (SELECT DISTINCT user_id FROM user_usage)
                    GROUP BY user_id
                    HAVING period_start = MAX(period_start)
                )
            """
            cursor = self._db.conn.execute(query, (cutoff_str,))
            deleted_count = cursor.rowcount
            self._db.conn.commit()

            logger.info(
                f"Cleaned up {deleted_count} old AI usage records "
                f"(cutoff: {cutoff_str})"
            )

            return CleanupResult(
                category="ai_usage_logs",
                records_deleted=deleted_count,
                cutoff_date=cutoff_str,
                success=True,
            )
        except Exception as e:
            logger.error(f"Failed to cleanup AI usage logs: {e}")
            return CleanupResult(
                category="ai_usage_logs",
                records_deleted=0,
                cutoff_date=cutoff_str,
                success=False,
                error=str(e),
            )

    def cleanup_sync_history(
        self, retention_days: Optional[int] = None
    ) -> CleanupResult:
        """Delete old Garmin sync history records.

        Args:
            retention_days: Override for retention period. Defaults to config value.

        Returns:
            CleanupResult with details of the cleanup operation.
        """
        days = retention_days or self._settings.retention_sync_history_days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()

        try:
            # Delete old sync history records
            query = """
                DELETE FROM garmin_sync_history
                WHERE started_at < ?
            """
            cursor = self._db.conn.execute(query, (cutoff_str,))
            deleted_count = cursor.rowcount
            self._db.conn.commit()

            logger.info(
                f"Cleaned up {deleted_count} old sync history records "
                f"(cutoff: {cutoff_str})"
            )

            return CleanupResult(
                category="sync_history",
                records_deleted=deleted_count,
                cutoff_date=cutoff_str,
                success=True,
            )
        except Exception as e:
            logger.error(f"Failed to cleanup sync history: {e}")
            return CleanupResult(
                category="sync_history",
                records_deleted=0,
                cutoff_date=cutoff_str,
                success=False,
                error=str(e),
            )

    def cleanup_old_activity_data(
        self, retention_days: Optional[int] = None
    ) -> CleanupResult:
        """Delete old activity data beyond retention period.

        Note: This is disabled by default (retention_days=0 or very large value).
        Activity data is valuable for long-term training analysis.

        Args:
            retention_days: Override for retention period. Defaults to config value.
                           Set to 0 to disable cleanup.

        Returns:
            CleanupResult with details of the cleanup operation.
        """
        days = retention_days or self._settings.retention_activity_data_days

        # If days is 0, skip cleanup (keep forever)
        if days == 0:
            return CleanupResult(
                category="activity_data",
                records_deleted=0,
                cutoff_date="N/A (disabled)",
                success=True,
            )

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        try:
            total_deleted = 0

            # Delete from activity_metrics
            query1 = "DELETE FROM activity_metrics WHERE date < ?"
            cursor1 = self._db.conn.execute(query1, (cutoff_str,))
            total_deleted += cursor1.rowcount

            # Delete from fitness_metrics
            query2 = "DELETE FROM fitness_metrics WHERE date < ?"
            cursor2 = self._db.conn.execute(query2, (cutoff_str,))
            total_deleted += cursor2.rowcount

            # Delete from garmin_fitness_data
            query3 = "DELETE FROM garmin_fitness_data WHERE date < ?"
            cursor3 = self._db.conn.execute(query3, (cutoff_str,))
            total_deleted += cursor3.rowcount

            # Delete from weekly_summaries
            query4 = "DELETE FROM weekly_summaries WHERE week_start < ?"
            cursor4 = self._db.conn.execute(query4, (cutoff_str,))
            total_deleted += cursor4.rowcount

            self._db.conn.commit()

            logger.info(
                f"Cleaned up {total_deleted} old activity data records "
                f"(cutoff: {cutoff_str})"
            )

            return CleanupResult(
                category="activity_data",
                records_deleted=total_deleted,
                cutoff_date=cutoff_str,
                success=True,
            )
        except Exception as e:
            logger.error(f"Failed to cleanup old activity data: {e}")
            return CleanupResult(
                category="activity_data",
                records_deleted=0,
                cutoff_date=cutoff_str,
                success=False,
                error=str(e),
            )

    def cleanup_strava_sync_records(
        self, retention_days: Optional[int] = None
    ) -> CleanupResult:
        """Delete old Strava sync records for activities no longer present.

        Args:
            retention_days: Override for retention period. Defaults to sync history days.

        Returns:
            CleanupResult with details of the cleanup operation.
        """
        days = retention_days or self._settings.retention_sync_history_days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()

        try:
            # Delete orphaned sync records (where local activity no longer exists)
            # and old completed syncs
            query = """
                DELETE FROM strava_activity_sync
                WHERE created_at < ?
                AND sync_status = 'completed'
            """
            cursor = self._db.conn.execute(query, (cutoff_str,))
            deleted_count = cursor.rowcount
            self._db.conn.commit()

            logger.info(
                f"Cleaned up {deleted_count} old Strava sync records "
                f"(cutoff: {cutoff_str})"
            )

            return CleanupResult(
                category="strava_sync_records",
                records_deleted=deleted_count,
                cutoff_date=cutoff_str,
                success=True,
            )
        except Exception as e:
            logger.error(f"Failed to cleanup Strava sync records: {e}")
            return CleanupResult(
                category="strava_sync_records",
                records_deleted=0,
                cutoff_date=cutoff_str,
                success=False,
                error=str(e),
            )

    def cleanup_old_workout_analyses(
        self, retention_days: Optional[int] = None
    ) -> CleanupResult:
        """Delete workout analyses for activities that no longer exist.

        Args:
            retention_days: Override for retention period. Defaults to activity data days.

        Returns:
            CleanupResult with details of the cleanup operation.
        """
        days = retention_days or self._settings.retention_activity_data_days

        # If days is 0, skip cleanup (keep forever)
        if days == 0:
            return CleanupResult(
                category="workout_analyses",
                records_deleted=0,
                cutoff_date="N/A (disabled)",
                success=True,
            )

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()

        try:
            # Delete analyses for workouts that no longer exist in activity_metrics
            # or analyses older than retention period
            query = """
                DELETE FROM workout_analyses
                WHERE created_at < ?
                OR workout_id NOT IN (SELECT activity_id FROM activity_metrics)
            """
            cursor = self._db.conn.execute(query, (cutoff_str,))
            deleted_count = cursor.rowcount
            self._db.conn.commit()

            logger.info(
                f"Cleaned up {deleted_count} old/orphaned workout analyses "
                f"(cutoff: {cutoff_str})"
            )

            return CleanupResult(
                category="workout_analyses",
                records_deleted=deleted_count,
                cutoff_date=cutoff_str,
                success=True,
            )
        except Exception as e:
            logger.error(f"Failed to cleanup workout analyses: {e}")
            return CleanupResult(
                category="workout_analyses",
                records_deleted=0,
                cutoff_date=cutoff_str,
                success=False,
                error=str(e),
            )

    def run_full_cleanup(self, dry_run: bool = False) -> DataRetentionReport:
        """Run all cleanup operations.

        Args:
            dry_run: If True, only report what would be deleted without
                    actually deleting. (Currently not fully implemented)

        Returns:
            DataRetentionReport with results from all cleanup operations.
        """
        start_time = datetime.now(timezone.utc)
        results: list[CleanupResult] = []

        if dry_run:
            logger.info("Running data retention cleanup (DRY RUN - no actual deletions)")
        else:
            logger.info("Running data retention cleanup")

        # Run all cleanup operations
        results.append(self.cleanup_expired_sessions())
        results.append(self.cleanup_ai_usage_logs())
        results.append(self.cleanup_sync_history())
        results.append(self.cleanup_strava_sync_records())
        results.append(self.cleanup_old_workout_analyses())

        # Only run activity data cleanup if explicitly enabled (non-zero retention)
        if self._settings.retention_activity_data_days > 0:
            results.append(self.cleanup_old_activity_data())

        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        total_deleted = sum(r.records_deleted for r in results if r.success)

        report = DataRetentionReport(
            timestamp=start_time.isoformat(),
            results=results,
            total_deleted=total_deleted,
            duration_seconds=duration,
        )

        logger.info(
            f"Data retention cleanup complete: "
            f"{total_deleted} records deleted in {duration:.2f}s"
        )

        return report

    def get_retention_stats(self) -> dict:
        """Get statistics about data eligible for cleanup.

        Returns:
            Dictionary with counts of records that would be cleaned up.
        """
        stats = {}
        now = datetime.now(timezone.utc)

        # Sessions
        cutoff = (now - timedelta(days=self._settings.retention_sessions_days)).isoformat()
        try:
            cursor = self._db.conn.execute(
                "SELECT COUNT(*) FROM user_sessions WHERE expires_at < ? OR created_at < ?",
                (cutoff, cutoff),
            )
            stats["expired_sessions"] = cursor.fetchone()[0]
        except Exception:
            stats["expired_sessions"] = "N/A"

        # AI usage logs
        cutoff = (now - timedelta(days=self._settings.retention_ai_usage_logs_days)).isoformat()
        try:
            cursor = self._db.conn.execute(
                "SELECT COUNT(*) FROM user_usage WHERE period_end < ?",
                (cutoff,),
            )
            stats["old_ai_usage_logs"] = cursor.fetchone()[0]
        except Exception:
            stats["old_ai_usage_logs"] = "N/A"

        # Sync history
        cutoff = (now - timedelta(days=self._settings.retention_sync_history_days)).isoformat()
        try:
            cursor = self._db.conn.execute(
                "SELECT COUNT(*) FROM garmin_sync_history WHERE started_at < ?",
                (cutoff,),
            )
            stats["old_sync_history"] = cursor.fetchone()[0]
        except Exception:
            stats["old_sync_history"] = "N/A"

        # Strava sync records
        try:
            cursor = self._db.conn.execute(
                "SELECT COUNT(*) FROM strava_activity_sync WHERE created_at < ? AND sync_status = 'completed'",
                (cutoff,),
            )
            stats["old_strava_sync_records"] = cursor.fetchone()[0]
        except Exception:
            stats["old_strava_sync_records"] = "N/A"

        # Activity data (only if retention is enabled)
        if self._settings.retention_activity_data_days > 0:
            cutoff = (now - timedelta(days=self._settings.retention_activity_data_days)).strftime("%Y-%m-%d")
            try:
                cursor = self._db.conn.execute(
                    "SELECT COUNT(*) FROM activity_metrics WHERE date < ?",
                    (cutoff,),
                )
                stats["old_activity_metrics"] = cursor.fetchone()[0]
            except Exception:
                stats["old_activity_metrics"] = "N/A"
        else:
            stats["old_activity_metrics"] = "N/A (disabled)"

        return stats


# Module-level instance for easy access
_retention_service: Optional[DataRetentionService] = None


def get_data_retention_service(db: Optional[TrainingDatabase] = None) -> DataRetentionService:
    """Get or create the data retention service instance.

    Args:
        db: Training database instance. Required on first call.

    Returns:
        DataRetentionService instance.

    Raises:
        ValueError: If db is not provided on first call.
    """
    global _retention_service

    if _retention_service is None:
        if db is None:
            # Try to create with default database
            settings = get_settings()
            db = TrainingDatabase(str(settings.training_db_path))
        _retention_service = DataRetentionService(db)

    return _retention_service
