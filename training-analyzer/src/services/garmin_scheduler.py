"""Garmin sync scheduler using APScheduler.

Manages scheduled background sync jobs for all users with auto-sync enabled.
Runs daily at a configurable time (default 6 AM UTC).
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from ..db.database import TrainingDatabase
from ..config import get_settings
from .garmin_sync_service import GarminSyncService, GarminCredentialsRepository, SyncResult

logger = logging.getLogger(__name__)


class GarminSyncScheduler:
    """Manages scheduled Garmin sync jobs for all users.

    Uses APScheduler for background job execution with:
    - Daily scheduled sync at configurable time (default 6 AM UTC)
    - Optional startup sync to catch up on missed syncs
    - Manual trigger support for immediate sync

    Usage:
        scheduler = GarminSyncScheduler(training_db)
        scheduler.start()
        # ... app runs ...
        scheduler.stop()
    """

    def __init__(self, training_db: TrainingDatabase):
        """Initialize the scheduler.

        Args:
            training_db: The training database instance.
        """
        self.db = training_db
        self.repo = GarminCredentialsRepository(training_db)
        self.sync_service = GarminSyncService(training_db)
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self._is_running and self.scheduler is not None

    def start(self, run_startup_sync: bool = False) -> None:
        """Start the scheduler with daily sync job.

        Args:
            run_startup_sync: If True, run a sync shortly after startup
                             to catch up on any missed syncs.
        """
        if self._is_running:
            logger.warning("Scheduler is already running")
            return

        settings = get_settings()

        if not settings.garmin_sync_enabled:
            logger.info("Garmin auto-sync is disabled in configuration")
            return

        self.scheduler = AsyncIOScheduler()

        # Add daily sync job at configured hour (default 6 AM UTC)
        sync_hour = settings.garmin_sync_hour
        self.scheduler.add_job(
            self._run_all_syncs,
            CronTrigger(hour=sync_hour, minute=0),
            id="daily_garmin_sync",
            name="Daily Garmin Sync",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping runs
        )

        # Optionally run a startup sync after a short delay
        if run_startup_sync:
            startup_time = datetime.now() + timedelta(seconds=30)
            self.scheduler.add_job(
                self._run_all_syncs,
                DateTrigger(run_date=startup_time),
                id="startup_sync",
                name="Startup Sync",
            )
            logger.info(f"Startup sync scheduled for {startup_time}")

        self.scheduler.start()
        self._is_running = True
        logger.info(f"Garmin sync scheduler started (daily sync at {sync_hour}:00 UTC)")

    def stop(self) -> None:
        """Gracefully shutdown the scheduler."""
        if not self._is_running or self.scheduler is None:
            return

        logger.info("Shutting down Garmin sync scheduler...")
        self.scheduler.shutdown(wait=True)
        self._is_running = False
        self.scheduler = None
        logger.info("Garmin sync scheduler stopped")

    async def _run_all_syncs(self) -> None:
        """Execute sync for all users with auto-sync enabled.

        This is the main scheduled job that runs daily.
        """
        user_ids = self.repo.get_all_auto_sync_users()
        logger.info(f"Starting scheduled sync for {len(user_ids)} users")

        successful = 0
        failed = 0

        for user_id in user_ids:
            try:
                result = await self._sync_user(user_id)
                if result.success:
                    successful += 1
                    logger.info(
                        f"Sync completed for user {user_id}: "
                        f"{result.activities_synced} activities, "
                        f"{result.fitness_days_synced} fitness days"
                    )
                else:
                    failed += 1
                    logger.warning(
                        f"Sync failed for user {user_id}: {result.error_message}"
                    )
            except Exception as e:
                failed += 1
                logger.error(f"Unexpected error syncing user {user_id}: {e}")

        logger.info(
            f"Scheduled sync complete: {successful} successful, {failed} failed"
        )

    async def _sync_user(self, user_id: str) -> SyncResult:
        """Sync a single user's Garmin data.

        Args:
            user_id: The user ID to sync.

        Returns:
            SyncResult with sync details.
        """
        credentials = self.repo.get_credentials(user_id)
        if not credentials:
            return SyncResult(
                success=False,
                error_message="No valid credentials found",
            )

        config = self.repo.get_sync_config(user_id)

        # Determine sync date range based on last successful sync
        last_sync = self.repo.get_last_successful_sync(user_id)
        if last_sync and last_sync.get("sync_to_date"):
            # Incremental sync from last sync date
            days = config.get("incremental_sync_days", 7)
        else:
            # Initial sync with longer lookback
            days = config.get("initial_sync_days", 365)

        # Record sync start
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        sync_id = self.repo.start_sync(
            user_id=user_id,
            sync_type="scheduled",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        try:
            # Perform the sync
            result = self.sync_service.full_sync(user_id, days)

            # Record completion
            self.repo.complete_sync(
                sync_id=sync_id,
                status="completed" if result.success else "failed",
                activities_synced=result.activities_synced,
                wellness_days=result.wellness_days_synced,
                fitness_days=result.fitness_days_synced,
                error_message=result.error_message,
            )

            return result

        except Exception as e:
            self.repo.complete_sync(
                sync_id=sync_id,
                status="failed",
                error_message=str(e),
            )
            raise

    async def trigger_sync(self, user_id: str, days: Optional[int] = None) -> SyncResult:
        """Manually trigger a sync for a specific user.

        Args:
            user_id: The user ID to sync.
            days: Optional number of days to sync (overrides config).

        Returns:
            SyncResult with sync details.
        """
        credentials = self.repo.get_credentials(user_id)
        if not credentials:
            return SyncResult(
                success=False,
                error_message="No valid credentials found",
            )

        config = self.repo.get_sync_config(user_id)

        # Check minimum sync interval to prevent abuse
        last_sync = self.repo.get_last_successful_sync(user_id)
        if last_sync:
            min_interval = config.get("min_sync_interval_minutes", 60)
            last_sync_time = datetime.fromisoformat(last_sync["started_at"])
            time_since_last = datetime.now() - last_sync_time

            if time_since_last < timedelta(minutes=min_interval):
                minutes_remaining = min_interval - int(time_since_last.total_seconds() / 60)
                return SyncResult(
                    success=False,
                    error_message=f"Please wait {minutes_remaining} minutes before syncing again",
                )

        # Use provided days or default from config
        sync_days = days or config.get("incremental_sync_days", 7)

        # Record sync start
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=sync_days)
        sync_id = self.repo.start_sync(
            user_id=user_id,
            sync_type="manual",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        try:
            result = self.sync_service.full_sync(user_id, sync_days)

            self.repo.complete_sync(
                sync_id=sync_id,
                status="completed" if result.success else "failed",
                activities_synced=result.activities_synced,
                wellness_days=result.wellness_days_synced,
                fitness_days=result.fitness_days_synced,
                error_message=result.error_message,
            )

            return result

        except Exception as e:
            self.repo.complete_sync(
                sync_id=sync_id,
                status="failed",
                error_message=str(e),
            )
            return SyncResult(
                success=False,
                error_message=str(e),
            )

    def get_next_sync_time(self) -> Optional[datetime]:
        """Get the next scheduled sync time.

        Returns:
            The next scheduled run time, or None if scheduler is not running.
        """
        if not self.is_running or self.scheduler is None:
            return None

        job = self.scheduler.get_job("daily_garmin_sync")
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
            "auto_sync_enabled": settings.garmin_sync_enabled,
            "sync_hour_utc": settings.garmin_sync_hour,
            "next_sync_time": None,
            "jobs": [],
        }

        if self.is_running and self.scheduler is not None:
            next_time = self.get_next_sync_time()
            if next_time:
                status["next_sync_time"] = next_time.isoformat()

            for job in self.scheduler.get_jobs():
                status["jobs"].append({
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                })

        return status


# Global scheduler instance for the application
_scheduler_instance: Optional[GarminSyncScheduler] = None


def get_scheduler(training_db: TrainingDatabase) -> GarminSyncScheduler:
    """Get or create the global scheduler instance.

    Args:
        training_db: The training database instance.

    Returns:
        The global GarminSyncScheduler instance.
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = GarminSyncScheduler(training_db)
    return _scheduler_instance


def shutdown_scheduler() -> None:
    """Shutdown the global scheduler instance if running."""
    global _scheduler_instance
    if _scheduler_instance is not None:
        _scheduler_instance.stop()
        _scheduler_instance = None
