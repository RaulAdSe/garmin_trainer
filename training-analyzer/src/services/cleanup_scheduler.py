"""Data retention cleanup scheduler using APScheduler.

Manages scheduled background cleanup jobs for data retention.
Runs daily at a configurable time (default 3 AM UTC).
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..db.database import TrainingDatabase
from ..config import get_settings
from .data_retention_service import DataRetentionService, DataRetentionReport

logger = logging.getLogger(__name__)


class CleanupScheduler:
    """Manages scheduled data retention cleanup jobs.

    Uses APScheduler for background job execution with:
    - Daily scheduled cleanup at configurable time (default 3 AM UTC)
    - Manual trigger support for immediate cleanup

    Usage:
        scheduler = CleanupScheduler(training_db)
        scheduler.start()
        # ... app runs ...
        scheduler.stop()
    """

    def __init__(self, training_db: TrainingDatabase):
        """Initialize the cleanup scheduler.

        Args:
            training_db: The training database instance.
        """
        self.db = training_db
        self.retention_service = DataRetentionService(training_db)
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._is_running = False
        self._last_cleanup_report: Optional[DataRetentionReport] = None

    @property
    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self._is_running and self.scheduler is not None

    @property
    def last_cleanup_report(self) -> Optional[DataRetentionReport]:
        """Get the last cleanup report."""
        return self._last_cleanup_report

    def start(self) -> None:
        """Start the scheduler with daily cleanup job."""
        if self._is_running:
            logger.warning("Cleanup scheduler is already running")
            return

        settings = get_settings()

        if not settings.retention_cleanup_enabled:
            logger.info("Data retention cleanup is disabled in configuration")
            return

        self.scheduler = AsyncIOScheduler()

        # Add daily cleanup job at configured hour (default 3 AM UTC)
        cleanup_hour = settings.retention_cleanup_hour
        self.scheduler.add_job(
            self._run_cleanup,
            CronTrigger(hour=cleanup_hour, minute=0),
            id="daily_data_cleanup",
            name="Daily Data Retention Cleanup",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping runs
        )

        self.scheduler.start()
        self._is_running = True
        logger.info(f"Cleanup scheduler started (daily cleanup at {cleanup_hour}:00 UTC)")

    def stop(self) -> None:
        """Gracefully shutdown the scheduler."""
        if not self._is_running or self.scheduler is None:
            return

        logger.info("Shutting down cleanup scheduler...")
        self.scheduler.shutdown(wait=True)
        self._is_running = False
        self.scheduler = None
        logger.info("Cleanup scheduler stopped")

    async def _run_cleanup(self) -> None:
        """Execute the scheduled cleanup.

        This is the main scheduled job that runs daily.
        """
        logger.info("Starting scheduled data retention cleanup")

        try:
            report = self.retention_service.run_full_cleanup()
            self._last_cleanup_report = report

            # Log results
            successful_categories = [r.category for r in report.results if r.success]
            failed_categories = [r.category for r in report.results if not r.success]

            if failed_categories:
                logger.warning(
                    f"Cleanup completed with errors: "
                    f"{report.total_deleted} records deleted, "
                    f"failed categories: {failed_categories}"
                )
            else:
                logger.info(
                    f"Cleanup completed successfully: "
                    f"{report.total_deleted} records deleted from {successful_categories}"
                )

        except Exception as e:
            logger.error(f"Unexpected error during scheduled cleanup: {e}")

    async def trigger_cleanup(self) -> DataRetentionReport:
        """Manually trigger a cleanup.

        Returns:
            DataRetentionReport with cleanup details.
        """
        logger.info("Manual cleanup triggered")
        report = self.retention_service.run_full_cleanup()
        self._last_cleanup_report = report
        return report

    def get_next_cleanup_time(self) -> Optional[datetime]:
        """Get the next scheduled cleanup time.

        Returns:
            The next scheduled run time, or None if scheduler is not running.
        """
        if not self.is_running or self.scheduler is None:
            return None

        job = self.scheduler.get_job("daily_data_cleanup")
        if job and job.next_run_time:
            return job.next_run_time

        return None

    def get_scheduler_status(self) -> dict:
        """Get the current scheduler status.

        Returns:
            Dictionary with scheduler status information.
        """
        settings = get_settings()

        status = {
            "is_running": self.is_running,
            "cleanup_enabled": settings.retention_cleanup_enabled,
            "cleanup_hour_utc": settings.retention_cleanup_hour,
            "next_cleanup_time": None,
            "last_cleanup": None,
            "retention_settings": {
                "sessions_days": settings.retention_sessions_days,
                "ai_usage_logs_days": settings.retention_ai_usage_logs_days,
                "sync_history_days": settings.retention_sync_history_days,
                "activity_data_days": settings.retention_activity_data_days,
            },
        }

        if self.is_running and self.scheduler is not None:
            next_time = self.get_next_cleanup_time()
            if next_time:
                status["next_cleanup_time"] = next_time.isoformat()

        if self._last_cleanup_report:
            status["last_cleanup"] = {
                "timestamp": self._last_cleanup_report.timestamp,
                "total_deleted": self._last_cleanup_report.total_deleted,
                "duration_seconds": self._last_cleanup_report.duration_seconds,
            }

        return status


# Global scheduler instance for the application
_cleanup_scheduler_instance: Optional[CleanupScheduler] = None


def get_cleanup_scheduler(training_db: TrainingDatabase) -> CleanupScheduler:
    """Get or create the global cleanup scheduler instance.

    Args:
        training_db: The training database instance.

    Returns:
        The global CleanupScheduler instance.
    """
    global _cleanup_scheduler_instance
    if _cleanup_scheduler_instance is None:
        _cleanup_scheduler_instance = CleanupScheduler(training_db)
    return _cleanup_scheduler_instance


def shutdown_cleanup_scheduler() -> None:
    """Shutdown the global cleanup scheduler instance if running."""
    global _cleanup_scheduler_instance
    if _cleanup_scheduler_instance is not None:
        _cleanup_scheduler_instance.stop()
        _cleanup_scheduler_instance = None
