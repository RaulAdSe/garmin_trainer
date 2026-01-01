"""Garmin credentials management API routes.

Provides endpoints for managing encrypted Garmin Connect credentials,
sync configuration, and manual sync triggers.

Security Features:
- Rate limiting on sensitive operations (credentials save/delete, sync trigger)
- Audit logging for all credential operations (without logging actual credentials)
- Failed validation tracking with automatic credential invalidation
- HTTPS required in production for credential transmission
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from ..deps import get_training_db, get_current_user, CurrentUser
from ..middleware.rate_limit import limiter
from ...db.database import TrainingDatabase
from ...services.garmin_sync_service import (
    GarminSyncService,
    GarminCredentialsRepository,
)
from ...services.garmin_scheduler import get_scheduler


router = APIRouter()
logger = logging.getLogger(__name__)


# ============ Rate Limit Constants ============

RATE_LIMIT_CREDENTIALS_SAVE = "5/minute"  # Prevent brute force attempts
RATE_LIMIT_CREDENTIALS_DELETE = "3/minute"  # Prevent abuse
RATE_LIMIT_CREDENTIALS_STATUS = "30/minute"  # Read-only, less restrictive
RATE_LIMIT_SYNC_TRIGGER = "5/minute"  # Prevent API abuse

# Failed validation threshold before marking credentials invalid
MAX_FAILED_VALIDATIONS = 3


# ============ Request/Response Models ============


class SaveCredentialsRequest(BaseModel):
    """Request to save Garmin Connect credentials."""
    email: EmailStr = Field(..., description="Garmin Connect email")
    password: str = Field(..., min_length=1, description="Garmin Connect password")


class SaveCredentialsResponse(BaseModel):
    """Response after saving credentials."""
    status: str
    garmin_user: Optional[str] = None
    message: str


class CredentialsStatusResponse(BaseModel):
    """Response for credentials status check."""
    connected: bool
    garmin_user: Optional[str] = None
    is_valid: bool = False
    last_validated: Optional[str] = None


class SyncConfigRequest(BaseModel):
    """Request to update sync configuration."""
    auto_sync_enabled: bool = True
    sync_frequency: str = Field(default="daily", pattern="^(hourly|daily|weekly)$")
    sync_time: str = Field(default="06:00", pattern="^\\d{2}:\\d{2}$")
    sync_activities: bool = True
    sync_wellness: bool = True
    sync_fitness_metrics: bool = True
    sync_sleep: bool = True
    initial_sync_days: int = Field(default=365, ge=1, le=730)
    incremental_sync_days: int = Field(default=7, ge=1, le=30)


class SyncConfigResponse(BaseModel):
    """Response with sync configuration."""
    user_id: str
    auto_sync_enabled: bool
    sync_frequency: str
    sync_time: str
    sync_activities: bool
    sync_wellness: bool
    sync_fitness_metrics: bool
    sync_sleep: bool
    initial_sync_days: int
    incremental_sync_days: int


class SyncHistoryItem(BaseModel):
    """A single sync history record."""
    id: int
    sync_type: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    activities_synced: int = 0
    wellness_days_synced: int = 0
    fitness_days_synced: int = 0
    error_message: Optional[str] = None


class SyncHistoryResponse(BaseModel):
    """Response with sync history."""
    history: list[SyncHistoryItem]


class TriggerSyncRequest(BaseModel):
    """Request to trigger a manual sync."""
    days: Optional[int] = Field(default=None, ge=1, le=365)


class TriggerSyncResponse(BaseModel):
    """Response after triggering sync."""
    status: str
    message: str
    activities_synced: int = 0
    wellness_days_synced: int = 0
    fitness_days_synced: int = 0


class SchedulerStatusResponse(BaseModel):
    """Response with scheduler status."""
    is_running: bool
    auto_sync_enabled: bool
    sync_hour_utc: int
    next_sync_time: Optional[str] = None


# ============ API Endpoints ============


@router.post("/credentials", response_model=SaveCredentialsResponse)
@limiter.limit(RATE_LIMIT_CREDENTIALS_SAVE)
async def save_garmin_credentials(
    request_obj: Request,
    request: SaveCredentialsRequest,
    current_user: CurrentUser = Depends(get_current_user),
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Save Garmin Connect credentials (encrypted).

    Validates the credentials by attempting a login to Garmin Connect,
    then stores them encrypted in the database.

    **Security:**
    - Rate limited to 5 requests/minute to prevent brute force attacks
    - Credentials are encrypted at rest using Fernet (AES-128-CBC)
    - Password is never logged or returned in responses
    - HTTPS required in production to protect credentials in transit
    - All operations are audit logged (without logging credentials)
    """
    user_id = current_user.id
    sync_service = GarminSyncService(training_db)
    repo = GarminCredentialsRepository(training_db)

    # Audit log: credential save attempt (no credentials in log)
    logger.info(
        f"AUDIT: Credential save attempt | user_id={user_id} | "
        f"timestamp={datetime.utcnow().isoformat()}"
    )

    # Validate credentials by attempting login
    is_valid, display_name, error = sync_service.validate_credentials(
        request.email, request.password
    )

    if not is_valid:
        # Audit log: validation failure
        logger.warning(
            f"AUDIT: Credential validation failed | user_id={user_id} | "
            f"timestamp={datetime.utcnow().isoformat()} | error_type=validation_failed"
        )

        # Track failed validation attempt
        _track_failed_validation(training_db, user_id)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error or "Invalid Garmin Connect credentials",
        )

    # Save encrypted credentials
    try:
        repo.save_credentials(
            user_id=user_id,
            email=request.email,
            password=request.password,
            garmin_display_name=display_name,
        )

        # Reset failed validation counter on successful save
        _reset_failed_validations(training_db, user_id)

        # Audit log: successful save
        logger.info(
            f"AUDIT: Credentials saved successfully | user_id={user_id} | "
            f"timestamp={datetime.utcnow().isoformat()} | "
            f"garmin_display_name={display_name}"
        )

    except Exception as e:
        # Audit log: save failure (error details go to error log, not audit)
        logger.error(f"Failed to save credentials for user {user_id}: {e}")
        logger.warning(
            f"AUDIT: Credential save failed | user_id={user_id} | "
            f"timestamp={datetime.utcnow().isoformat()} | error_type=storage_error"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save credentials. Please try again later.",
        )

    return SaveCredentialsResponse(
        status="saved",
        garmin_user=display_name,
        message="Garmin Connect credentials saved successfully",
    )


@router.delete("/credentials")
@limiter.limit(RATE_LIMIT_CREDENTIALS_DELETE)
async def delete_garmin_credentials(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Delete stored Garmin credentials.

    Removes all stored credentials and sync configuration for the user.
    This effectively disconnects the Garmin Connect integration.

    **Security:**
    - Rate limited to 3 requests/minute to prevent abuse
    - Audit logged for security monitoring
    """
    user_id = current_user.id
    repo = GarminCredentialsRepository(training_db)

    # Audit log: deletion attempt
    logger.info(
        f"AUDIT: Credential deletion attempt | user_id={user_id} | "
        f"timestamp={datetime.utcnow().isoformat()}"
    )

    deleted = repo.delete_credentials(user_id)

    if not deleted:
        # Audit log: nothing to delete
        logger.info(
            f"AUDIT: Credential deletion - no credentials found | user_id={user_id} | "
            f"timestamp={datetime.utcnow().isoformat()}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No credentials found to delete",
        )

    # Audit log: successful deletion
    logger.info(
        f"AUDIT: Credentials deleted successfully | user_id={user_id} | "
        f"timestamp={datetime.utcnow().isoformat()}"
    )

    return {"status": "deleted", "message": "Garmin credentials removed"}


@router.get("/credentials/status", response_model=CredentialsStatusResponse)
@limiter.limit(RATE_LIMIT_CREDENTIALS_STATUS)
async def get_credentials_status(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Check if Garmin credentials are stored and valid.

    Returns the connection status without exposing any credential details.

    **Security:**
    - Rate limited to 30 requests/minute (read-only, less restrictive)
    - Access is audit logged
    """
    user_id = current_user.id
    repo = GarminCredentialsRepository(training_db)

    # Audit log: status check (less verbose than write operations)
    logger.debug(
        f"AUDIT: Credential status check | user_id={user_id} | "
        f"timestamp={datetime.utcnow().isoformat()}"
    )

    creds = repo.get_credentials(user_id)

    if not creds:
        return CredentialsStatusResponse(connected=False)

    # Get last validation time and failed validation count from database
    with training_db._get_connection() as conn:
        row = conn.execute(
            """SELECT last_validation_at, validation_error, failed_validation_count
               FROM garmin_credentials WHERE user_id = ?""",
            (user_id,),
        ).fetchone()
        last_validated = row["last_validation_at"] if row else None
        failed_count = row["failed_validation_count"] if row and row["failed_validation_count"] else 0

    # Check if credentials have been marked invalid due to too many failures
    credentials_invalid_due_to_failures = failed_count >= MAX_FAILED_VALIDATIONS

    return CredentialsStatusResponse(
        connected=True,
        garmin_user=creds.garmin_display_name,
        is_valid=creds.is_valid and not credentials_invalid_due_to_failures,
        last_validated=last_validated,
    )


@router.get("/sync-config", response_model=SyncConfigResponse)
async def get_sync_config(
    current_user: CurrentUser = Depends(get_current_user),
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Get the current sync configuration.

    Returns the user's sync settings including auto-sync preferences,
    frequency, and data types to sync.
    """
    user_id = current_user.id
    repo = GarminCredentialsRepository(training_db)

    config = repo.get_sync_config(user_id)

    return SyncConfigResponse(
        user_id=user_id,
        auto_sync_enabled=config.get("auto_sync_enabled", True),
        sync_frequency=config.get("sync_frequency", "daily"),
        sync_time=config.get("sync_time", "06:00"),
        sync_activities=config.get("sync_activities", True),
        sync_wellness=config.get("sync_wellness", True),
        sync_fitness_metrics=config.get("sync_fitness_metrics", True),
        sync_sleep=config.get("sync_sleep", True),
        initial_sync_days=config.get("initial_sync_days", 365),
        incremental_sync_days=config.get("incremental_sync_days", 7),
    )


@router.put("/sync-config")
async def update_sync_config(
    request: SyncConfigRequest,
    current_user: CurrentUser = Depends(get_current_user),
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Update Garmin sync configuration.

    Allows customization of sync behavior including:
    - Auto-sync enable/disable
    - Sync frequency and preferred time
    - Data types to sync (activities, wellness, fitness metrics)
    - Lookback periods for initial and incremental syncs
    """
    user_id = current_user.id
    repo = GarminCredentialsRepository(training_db)

    repo.update_sync_config(
        user_id=user_id,
        auto_sync_enabled=request.auto_sync_enabled,
        sync_frequency=request.sync_frequency,
        sync_time=request.sync_time,
        sync_activities=request.sync_activities,
        sync_wellness=request.sync_wellness,
        sync_fitness_metrics=request.sync_fitness_metrics,
        sync_sleep=request.sync_sleep,
        initial_sync_days=request.initial_sync_days,
        incremental_sync_days=request.incremental_sync_days,
    )

    return {"status": "updated", "message": "Sync configuration updated"}


@router.get("/sync-history", response_model=SyncHistoryResponse)
async def get_sync_history(
    limit: int = 10,
    current_user: CurrentUser = Depends(get_current_user),
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Get recent sync history.

    Returns a list of recent sync operations including their status,
    duration, and counts of synced items.
    """
    user_id = current_user.id
    repo = GarminCredentialsRepository(training_db)

    history = repo.get_sync_history(user_id, limit)

    return SyncHistoryResponse(
        history=[
            SyncHistoryItem(
                id=h.get("id", 0),
                sync_type=h.get("sync_type", "unknown"),
                status=h.get("status", "unknown"),
                started_at=h.get("started_at", ""),
                completed_at=h.get("completed_at"),
                duration_seconds=h.get("duration_seconds"),
                activities_synced=h.get("activities_synced", 0),
                wellness_days_synced=h.get("wellness_days_synced", 0),
                fitness_days_synced=h.get("fitness_days_synced", 0),
                error_message=h.get("error_message"),
            )
            for h in history
        ]
    )


@router.post("/sync/trigger", response_model=TriggerSyncResponse)
@limiter.limit(RATE_LIMIT_SYNC_TRIGGER)
async def trigger_manual_sync(
    request_obj: Request,
    request: TriggerSyncRequest = None,
    current_user: CurrentUser = Depends(get_current_user),
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Manually trigger a Garmin sync.

    Immediately starts a sync operation for the current user.
    Note: There is a minimum interval between syncs (default 60 minutes)
    to prevent excessive API calls to Garmin.

    **Security:**
    - Rate limited to 5 requests/minute to prevent API abuse
    - Sync operations are audit logged
    """
    user_id = current_user.id
    scheduler = get_scheduler(training_db)

    days = request.days if request else None

    # Audit log: sync trigger attempt
    logger.info(
        f"AUDIT: Sync triggered | user_id={user_id} | "
        f"timestamp={datetime.utcnow().isoformat()} | days={days}"
    )

    result = await scheduler.trigger_sync(user_id, days)

    if not result.success:
        # Audit log: sync failure
        logger.warning(
            f"AUDIT: Sync failed | user_id={user_id} | "
            f"timestamp={datetime.utcnow().isoformat()} | "
            f"error_type=sync_failed"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error_message or "Sync failed",
        )

    # Audit log: sync success
    logger.info(
        f"AUDIT: Sync completed | user_id={user_id} | "
        f"timestamp={datetime.utcnow().isoformat()} | "
        f"activities={result.activities_synced} | "
        f"wellness_days={result.wellness_days_synced} | "
        f"fitness_days={result.fitness_days_synced}"
    )

    return TriggerSyncResponse(
        status="completed",
        message="Sync completed successfully",
        activities_synced=result.activities_synced,
        wellness_days_synced=result.wellness_days_synced,
        fitness_days_synced=result.fitness_days_synced,
    )


@router.get("/scheduler/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status(
    current_user: CurrentUser = Depends(get_current_user),
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Get the scheduler status.

    Returns information about the background sync scheduler including
    whether it's running and when the next scheduled sync will occur.
    """
    scheduler = get_scheduler(training_db)
    status = scheduler.get_scheduler_status()

    return SchedulerStatusResponse(
        is_running=status["is_running"],
        auto_sync_enabled=status["auto_sync_enabled"],
        sync_hour_utc=status["sync_hour_utc"],
        next_sync_time=status["next_sync_time"],
    )


# ============ Helper Functions for Failed Validation Tracking ============


def _track_failed_validation(training_db: TrainingDatabase, user_id: str) -> None:
    """Track a failed credential validation attempt.

    Increments the failed_validation_count in the database.
    After MAX_FAILED_VALIDATIONS attempts, credentials are marked as invalid.

    Args:
        training_db: Database connection.
        user_id: The user ID.
    """
    try:
        with training_db._get_connection() as conn:
            # First, check if credentials exist and get current count
            row = conn.execute(
                """SELECT failed_validation_count FROM garmin_credentials
                   WHERE user_id = ?""",
                (user_id,),
            ).fetchone()

            if row:
                current_count = (row["failed_validation_count"] or 0) + 1

                # Update the count
                conn.execute(
                    """UPDATE garmin_credentials
                       SET failed_validation_count = ?,
                           last_validation_at = CURRENT_TIMESTAMP,
                           updated_at = CURRENT_TIMESTAMP
                       WHERE user_id = ?""",
                    (current_count, user_id),
                )

                # If threshold reached, mark as invalid
                if current_count >= MAX_FAILED_VALIDATIONS:
                    conn.execute(
                        """UPDATE garmin_credentials
                           SET is_valid = 0,
                               validation_error = 'Credentials marked invalid after multiple failed validation attempts',
                               updated_at = CURRENT_TIMESTAMP
                           WHERE user_id = ?""",
                        (user_id,),
                    )
                    logger.warning(
                        f"AUDIT: Credentials invalidated due to failed validations | "
                        f"user_id={user_id} | failed_count={current_count} | "
                        f"timestamp={datetime.utcnow().isoformat()}"
                    )
    except Exception as e:
        # Log but don't fail the request - this is a tracking mechanism
        logger.error(f"Failed to track validation failure for user {user_id}: {e}")


def _reset_failed_validations(training_db: TrainingDatabase, user_id: str) -> None:
    """Reset the failed validation counter after successful credential save.

    Args:
        training_db: Database connection.
        user_id: The user ID.
    """
    try:
        with training_db._get_connection() as conn:
            conn.execute(
                """UPDATE garmin_credentials
                   SET failed_validation_count = 0,
                       validation_error = NULL,
                       is_valid = 1,
                       last_validation_at = CURRENT_TIMESTAMP,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = ?""",
                (user_id,),
            )
    except Exception as e:
        # Log but don't fail the request
        logger.error(f"Failed to reset validation counter for user {user_id}: {e}")
