"""Admin API routes for system maintenance tasks.

Provides endpoints for data retention cleanup and system health monitoring.
These endpoints require admin authentication.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..middleware.auth import CurrentUser, get_current_user
from ...config import get_settings
from ...db.database import TrainingDatabase
from ...services.data_retention_service import (
    DataRetentionService,
    get_data_retention_service,
)
from ...services.cleanup_scheduler import get_cleanup_scheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# Request/Response Models
class RetentionStatsResponse(BaseModel):
    """Response model for data retention statistics."""

    expired_sessions: int | str
    old_ai_usage_logs: int | str
    old_sync_history: int | str
    old_strava_sync_records: int | str
    old_activity_metrics: int | str
    retention_settings: dict


class CleanupResultResponse(BaseModel):
    """Response model for a single cleanup result."""

    category: str
    records_deleted: int
    cutoff_date: str
    success: bool
    error: Optional[str] = None


class CleanupReportResponse(BaseModel):
    """Response model for full cleanup report."""

    timestamp: str
    results: list[CleanupResultResponse]
    total_deleted: int
    duration_seconds: float


class RetentionSettingsResponse(BaseModel):
    """Response model for current retention settings."""

    retention_sessions_days: int
    retention_ai_usage_logs_days: int
    retention_sync_history_days: int
    retention_activity_data_days: int
    retention_cleanup_enabled: bool
    retention_cleanup_hour: int


class CleanupSchedulerStatusResponse(BaseModel):
    """Response model for cleanup scheduler status."""

    is_running: bool
    cleanup_enabled: bool
    cleanup_hour_utc: int
    next_cleanup_time: Optional[str] = None
    last_cleanup: Optional[dict] = None
    retention_settings: dict


def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency that requires admin privileges."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this operation",
        )
    return current_user


def get_retention_service() -> DataRetentionService:
    """Get the data retention service instance."""
    settings = get_settings()
    db = TrainingDatabase(str(settings.training_db_path))
    return DataRetentionService(db)


@router.get("/retention/settings", response_model=RetentionSettingsResponse)
async def get_retention_settings(
    current_user: CurrentUser = Depends(require_admin),
) -> RetentionSettingsResponse:
    """Get current data retention settings.

    Returns the configured retention periods for different data types.
    Requires admin privileges.
    """
    settings = get_settings()

    return RetentionSettingsResponse(
        retention_sessions_days=settings.retention_sessions_days,
        retention_ai_usage_logs_days=settings.retention_ai_usage_logs_days,
        retention_sync_history_days=settings.retention_sync_history_days,
        retention_activity_data_days=settings.retention_activity_data_days,
        retention_cleanup_enabled=settings.retention_cleanup_enabled,
        retention_cleanup_hour=settings.retention_cleanup_hour,
    )


@router.get("/retention/stats", response_model=RetentionStatsResponse)
async def get_retention_stats(
    current_user: CurrentUser = Depends(require_admin),
    retention_service: DataRetentionService = Depends(get_retention_service),
) -> RetentionStatsResponse:
    """Get statistics about data eligible for cleanup.

    Returns counts of records that would be deleted based on current
    retention settings. Requires admin privileges.
    """
    stats = retention_service.get_retention_stats()
    settings = get_settings()

    return RetentionStatsResponse(
        expired_sessions=stats.get("expired_sessions", "N/A"),
        old_ai_usage_logs=stats.get("old_ai_usage_logs", "N/A"),
        old_sync_history=stats.get("old_sync_history", "N/A"),
        old_strava_sync_records=stats.get("old_strava_sync_records", "N/A"),
        old_activity_metrics=stats.get("old_activity_metrics", "N/A"),
        retention_settings={
            "sessions_days": settings.retention_sessions_days,
            "ai_usage_logs_days": settings.retention_ai_usage_logs_days,
            "sync_history_days": settings.retention_sync_history_days,
            "activity_data_days": settings.retention_activity_data_days,
        },
    )


@router.post("/retention/cleanup", response_model=CleanupReportResponse)
async def run_cleanup(
    current_user: CurrentUser = Depends(require_admin),
    retention_service: DataRetentionService = Depends(get_retention_service),
    include_activity_data: bool = Query(
        default=False,
        description="Include activity data cleanup (use with caution)",
    ),
) -> CleanupReportResponse:
    """Run data retention cleanup.

    Deletes old data based on configured retention periods.
    Requires admin privileges.

    Args:
        include_activity_data: Whether to include activity data in cleanup.
                              Default is False to prevent accidental data loss.
    """
    logger.info(
        f"Admin {current_user.email} initiated data retention cleanup "
        f"(include_activity_data={include_activity_data})"
    )

    # Run the cleanup
    report = retention_service.run_full_cleanup()

    # Convert to response model
    results = [
        CleanupResultResponse(
            category=r.category,
            records_deleted=r.records_deleted,
            cutoff_date=r.cutoff_date,
            success=r.success,
            error=r.error,
        )
        for r in report.results
        # Filter out activity data if not included
        if include_activity_data or r.category != "activity_data"
    ]

    return CleanupReportResponse(
        timestamp=report.timestamp,
        results=results,
        total_deleted=sum(r.records_deleted for r in results if r.success),
        duration_seconds=report.duration_seconds,
    )


@router.post("/retention/cleanup/sessions", response_model=CleanupResultResponse)
async def cleanup_sessions(
    current_user: CurrentUser = Depends(require_admin),
    retention_service: DataRetentionService = Depends(get_retention_service),
    retention_days: Optional[int] = Query(
        default=None,
        description="Override retention period (days)",
        ge=1,
    ),
) -> CleanupResultResponse:
    """Clean up expired user sessions.

    Deletes sessions that have expired or are older than the retention period.
    Requires admin privileges.
    """
    logger.info(
        f"Admin {current_user.email} initiated session cleanup "
        f"(retention_days={retention_days})"
    )

    result = retention_service.cleanup_expired_sessions(retention_days)

    return CleanupResultResponse(
        category=result.category,
        records_deleted=result.records_deleted,
        cutoff_date=result.cutoff_date,
        success=result.success,
        error=result.error,
    )


@router.post("/retention/cleanup/ai-usage", response_model=CleanupResultResponse)
async def cleanup_ai_usage(
    current_user: CurrentUser = Depends(require_admin),
    retention_service: DataRetentionService = Depends(get_retention_service),
    retention_days: Optional[int] = Query(
        default=None,
        description="Override retention period (days)",
        ge=1,
    ),
) -> CleanupResultResponse:
    """Clean up old AI usage logs.

    Deletes AI usage tracking records older than the retention period.
    Requires admin privileges.
    """
    logger.info(
        f"Admin {current_user.email} initiated AI usage cleanup "
        f"(retention_days={retention_days})"
    )

    result = retention_service.cleanup_ai_usage_logs(retention_days)

    return CleanupResultResponse(
        category=result.category,
        records_deleted=result.records_deleted,
        cutoff_date=result.cutoff_date,
        success=result.success,
        error=result.error,
    )


@router.post("/retention/cleanup/sync-history", response_model=CleanupResultResponse)
async def cleanup_sync_history(
    current_user: CurrentUser = Depends(require_admin),
    retention_service: DataRetentionService = Depends(get_retention_service),
    retention_days: Optional[int] = Query(
        default=None,
        description="Override retention period (days)",
        ge=1,
    ),
) -> CleanupResultResponse:
    """Clean up old Garmin sync history.

    Deletes sync history records older than the retention period.
    Requires admin privileges.
    """
    logger.info(
        f"Admin {current_user.email} initiated sync history cleanup "
        f"(retention_days={retention_days})"
    )

    result = retention_service.cleanup_sync_history(retention_days)

    return CleanupResultResponse(
        category=result.category,
        records_deleted=result.records_deleted,
        cutoff_date=result.cutoff_date,
        success=result.success,
        error=result.error,
    )


@router.get("/retention/scheduler", response_model=CleanupSchedulerStatusResponse)
async def get_scheduler_status(
    current_user: CurrentUser = Depends(require_admin),
) -> CleanupSchedulerStatusResponse:
    """Get the cleanup scheduler status.

    Returns information about the scheduled cleanup task including
    next run time and last cleanup results. Requires admin privileges.
    """
    settings = get_settings()
    db = TrainingDatabase(str(settings.training_db_path))
    scheduler = get_cleanup_scheduler(db)
    status = scheduler.get_scheduler_status()

    return CleanupSchedulerStatusResponse(
        is_running=status["is_running"],
        cleanup_enabled=status["cleanup_enabled"],
        cleanup_hour_utc=status["cleanup_hour_utc"],
        next_cleanup_time=status.get("next_cleanup_time"),
        last_cleanup=status.get("last_cleanup"),
        retention_settings=status["retention_settings"],
    )
