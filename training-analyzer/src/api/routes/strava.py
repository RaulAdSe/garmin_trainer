"""Strava OAuth and integration API routes.

Uses StravaRepository for credential storage with encryption at rest.
OAuth tokens are automatically encrypted when saved and decrypted when retrieved.
"""

import logging
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import get_training_db
from ...config import get_settings
from ...db.database import TrainingDatabase
from ...db.repositories.strava_repository import StravaRepository, get_strava_repository
from ...integrations.strava import StravaOAuthFlow, StravaClient
from ...integrations.base import OAuthCredentials, AuthenticationError
from ...models.strava import StravaCredentials as StravaCredentialsModel
from ...services.encryption import CredentialEncryptionError

logger = logging.getLogger(__name__)


router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================


class StravaAuthResponse(BaseModel):
    """Response containing Strava OAuth authorization URL."""
    authorization_url: str
    state: str


class StravaCallbackRequest(BaseModel):
    """Request body for OAuth callback (alternative to query params)."""
    code: str
    state: str
    scope: Optional[str] = None


class StravaCallbackResponse(BaseModel):
    """Response from OAuth callback."""
    success: bool
    message: str
    athlete_id: Optional[str] = None
    athlete_name: Optional[str] = None
    scope: Optional[str] = None


class StravaDisconnectResponse(BaseModel):
    """Response from disconnect operation."""
    success: bool
    message: str


class StravaStatusResponse(BaseModel):
    """Response containing Strava connection status."""
    connected: bool
    athlete_id: Optional[str] = None
    athlete_name: Optional[str] = None
    scope: Optional[str] = None
    expires_at: Optional[str] = None
    needs_refresh: bool = False


class StravaPreferences(BaseModel):
    """User preferences for Strava integration."""
    auto_update_description: bool = True
    use_extended_format: bool = False
    custom_footer: Optional[str] = None


class StravaPreferencesResponse(BaseModel):
    """Response containing Strava preferences."""
    success: bool
    preferences: StravaPreferences


# =============================================================================
# OAuth State Storage (database-backed for multi-instance deployments)
# =============================================================================


def _store_oauth_state(state: str, strava_repo: StravaRepository) -> None:
    """Store OAuth state for validation.

    Uses database storage for persistence across restarts and multi-instance support.
    Automatically cleans up expired states (older than 10 minutes).
    """
    strava_repo.store_oauth_state(state)


def _validate_oauth_state(state: str, strava_repo: StravaRepository) -> bool:
    """Validate and consume OAuth state.

    Returns True if state was valid and removes it to prevent replay attacks.
    """
    return strava_repo.validate_oauth_state(state)


# =============================================================================
# Helper Functions
# =============================================================================


def _get_strava_oauth_flow() -> StravaOAuthFlow:
    """Create a Strava OAuth flow instance."""
    settings = get_settings()
    if not settings.strava_client_id or not settings.strava_client_secret:
        raise HTTPException(
            status_code=500,
            detail="Strava OAuth not configured. Set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET."
        )
    return StravaOAuthFlow(
        client_id=settings.strava_client_id,
        client_secret=settings.strava_client_secret,
        redirect_uri=settings.strava_redirect_uri,
        scope="read,activity:read_all,activity:write",
    )


def _get_stored_credentials(
    strava_repo: StravaRepository,
    user_id: str = "default"
) -> Optional[OAuthCredentials]:
    """Get stored Strava credentials from database.

    Uses StravaRepository which handles encryption/decryption internally.

    Args:
        strava_repo: The Strava repository instance
        user_id: User identifier (defaults to 'default')

    Returns:
        OAuthCredentials if found and decryption succeeds, None otherwise

    Raises:
        HTTPException: If encryption key is missing or decryption fails
    """
    try:
        strava_creds = strava_repo.get_strava_credentials(user_id)
        if not strava_creds:
            return None

        # Convert StravaCredentials model to OAuthCredentials
        return OAuthCredentials(
            provider="strava",
            access_token=strava_creds.access_token,
            refresh_token=strava_creds.refresh_token,
            expires_at=datetime.fromisoformat(strava_creds.expires_at.replace('Z', '+00:00')) if strava_creds.expires_at else None,
            user_id=strava_creds.athlete_id,
            user_name=strava_creds.athlete_name,
            scope=strava_creds.scope,
            created_at=strava_creds.created_at if strava_creds.created_at else datetime.now(),
            updated_at=strava_creds.updated_at if strava_creds.updated_at else datetime.now(),
        )
    except CredentialEncryptionError as e:
        logger.error(f"Failed to decrypt Strava credentials: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to decrypt Strava credentials. The encryption key may have changed."
        )


def _save_credentials(
    strava_repo: StravaRepository,
    credentials: OAuthCredentials,
    user_id: str = "default"
) -> None:
    """Save Strava credentials to database.

    Uses StravaRepository which handles encryption internally.

    Args:
        strava_repo: The Strava repository instance
        credentials: OAuth credentials to save
        user_id: User identifier (defaults to 'default')

    Raises:
        HTTPException: If encryption fails
    """
    try:
        # Convert OAuthCredentials to StravaCredentials model
        strava_creds = StravaCredentialsModel(
            user_id=user_id,
            access_token=credentials.access_token,
            refresh_token=credentials.refresh_token,
            expires_at=credentials.expires_at.isoformat() if credentials.expires_at else "",
            athlete_id=credentials.user_id,
            athlete_name=credentials.user_name,
            scope=credentials.scope,
            created_at=credentials.created_at if credentials.created_at else datetime.now(),
            updated_at=datetime.now(),
        )

        # Repository handles encryption internally
        strava_repo.save_strava_credentials(strava_creds)
        logger.info(f"Saved encrypted Strava credentials for user {user_id}")

    except CredentialEncryptionError as e:
        logger.error(f"Failed to encrypt Strava credentials: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to encrypt Strava credentials. Check CREDENTIAL_ENCRYPTION_KEY configuration."
        )


def _delete_credentials(strava_repo: StravaRepository, user_id: str = "default") -> None:
    """Delete Strava credentials from database.

    Args:
        strava_repo: The Strava repository instance
        user_id: User identifier (defaults to 'default')
    """
    strava_repo.delete_strava_credentials(user_id)
    logger.info(f"Deleted Strava credentials for user {user_id}")


def _get_stored_preferences(strava_repo: StravaRepository, user_id: str = "default") -> StravaPreferences:
    """Get stored Strava preferences from database.

    Args:
        strava_repo: The Strava repository instance
        user_id: User identifier (defaults to 'default')

    Returns:
        StravaPreferences (existing or defaults)
    """
    repo_prefs = strava_repo.get_strava_preferences(user_id)

    return StravaPreferences(
        auto_update_description=repo_prefs.auto_update_description,
        use_extended_format=repo_prefs.use_extended_format,
        custom_footer=repo_prefs.custom_footer,
    )


def _save_preferences(
    strava_repo: StravaRepository,
    preferences: StravaPreferences,
    user_id: str = "default"
) -> None:
    """Save Strava preferences to database.

    Args:
        strava_repo: The Strava repository instance
        preferences: Preferences to save
        user_id: User identifier (defaults to 'default')
    """
    from ...models.strava import StravaPreferences as StravaPreferencesModel

    repo_prefs = StravaPreferencesModel(
        user_id=user_id,
        auto_update_description=preferences.auto_update_description,
        use_extended_format=preferences.use_extended_format,
        custom_footer=preferences.custom_footer,
    )

    strava_repo.save_strava_preferences(repo_prefs)



async def _refresh_token_if_needed(
    strava_repo: StravaRepository,
    credentials: OAuthCredentials,
    user_id: str = "default"
) -> OAuthCredentials:
    """Refresh token if expired or about to expire.

    Args:
        strava_repo: The Strava repository instance
        credentials: Current OAuth credentials
        user_id: User identifier (defaults to 'default')

    Returns:
        Refreshed OAuthCredentials (or original if no refresh needed)

    Raises:
        AuthenticationError: If token refresh fails with Strava
        HTTPException: If encryption fails when saving new tokens
    """
    if not credentials.needs_refresh:
        return credentials

    settings = get_settings()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": settings.strava_client_id,
                "client_secret": settings.strava_client_secret,
                "refresh_token": credentials.refresh_token,
                "grant_type": "refresh_token",
            }
        )

        if response.status_code != 200:
            logger.error(f"Strava token refresh failed: status={response.status_code}, response={response.text}")
            raise AuthenticationError(
                "Failed to refresh Strava token. Please reconnect your account.",
                "strava"
            )

        data = response.json()

        new_credentials = OAuthCredentials(
            provider="strava",
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", credentials.refresh_token),
            expires_at=datetime.fromtimestamp(data["expires_at"]) if data.get("expires_at") else None,
            token_type="Bearer",
            scope=credentials.scope,
            user_id=credentials.user_id,
            user_name=credentials.user_name,
            created_at=credentials.created_at,
        )

        # Save with encryption via repository
        _save_credentials(strava_repo, new_credentials, user_id)
        logger.info(f"Refreshed and saved encrypted Strava token for user {user_id}")
        return new_credentials


# =============================================================================
# API Routes
# =============================================================================


@router.get("/auth", response_model=StravaAuthResponse)
async def get_strava_auth_url(
    strava_repo: StravaRepository = Depends(get_strava_repository),
):
    """
    Get Strava OAuth authorization URL.

    Returns the URL to redirect the user to for Strava OAuth authorization.
    The state parameter is stored in the database for validation on callback.
    """
    oauth_flow = _get_strava_oauth_flow()
    auth_url = oauth_flow.get_authorization_url()
    state = oauth_flow._state

    # Store state for validation (database-backed)
    _store_oauth_state(state, strava_repo)

    return StravaAuthResponse(
        authorization_url=auth_url,
        state=state,
    )


@router.post("/callback", response_model=StravaCallbackResponse)
async def handle_strava_callback(
    request: StravaCallbackRequest,
    strava_repo: StravaRepository = Depends(get_strava_repository),
):
    """
    Handle Strava OAuth callback.

    Validates the state parameter, exchanges the authorization code for
    access tokens, and stores them with encryption via StravaRepository.
    Called by the frontend after the user authorizes the app.
    """
    code = request.code
    state = request.state
    scope = request.scope

    # Validate OAuth state to prevent CSRF attacks
    if not _validate_oauth_state(state, strava_repo):
        logger.warning(f"Invalid or expired OAuth state: {state[:8]}...")
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OAuth state. Please try connecting again."
        )

    settings = get_settings()

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": settings.strava_client_id,
                "client_secret": settings.strava_client_secret,
                "code": code,
                "grant_type": "authorization_code",
            }
        )

        if response.status_code != 200:
            logger.error(f"Strava token exchange failed: status={response.status_code}, response={response.text}")
            raise HTTPException(
                status_code=400,
                detail="Failed to connect to Strava. Please try again."
            )

        data = response.json()

    # Extract athlete info
    athlete = data.get("athlete", {})
    athlete_id = str(athlete.get("id", ""))
    athlete_name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()

    # Create credentials
    credentials = OAuthCredentials(
        provider="strava",
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_at=datetime.fromtimestamp(data["expires_at"]) if data.get("expires_at") else None,
        token_type="Bearer",
        scope=scope or "read,activity:read_all,activity:write",
        user_id=athlete_id,
        user_name=athlete_name,
    )

    # Store credentials with encryption
    _save_credentials(strava_repo, credentials)

    return StravaCallbackResponse(
        success=True,
        message=f"Successfully connected to Strava as {athlete_name}",
        athlete_id=athlete_id,
        athlete_name=athlete_name,
        scope=scope,
    )


@router.post("/disconnect", response_model=StravaDisconnectResponse)
async def disconnect_strava(
    strava_repo: StravaRepository = Depends(get_strava_repository),
):
    """
    Disconnect from Strava.

    Revokes the access token with Strava and removes stored credentials.
    """
    credentials = _get_stored_credentials(strava_repo)

    if not credentials:
        return StravaDisconnectResponse(
            success=True,
            message="No Strava connection found"
        )

    # Attempt to deauthorize with Strava
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.strava.com/oauth/deauthorize",
                headers={"Authorization": f"Bearer {credentials.access_token}"}
            )
            # We don't fail if deauthorization fails - just log and continue
            if response.status_code != 200:
                logger.warning(f"Strava deauthorization returned {response.status_code}: {response.text}")
    except Exception as e:
        logger.warning(f"Error deauthorizing with Strava: {e}")

    # Delete stored credentials regardless
    _delete_credentials(strava_repo)

    return StravaDisconnectResponse(
        success=True,
        message="Successfully disconnected from Strava"
    )


@router.get("/status", response_model=StravaStatusResponse)
async def get_strava_status(
    strava_repo: StravaRepository = Depends(get_strava_repository),
):
    """
    Get Strava connection status.

    Returns whether Strava is connected and athlete information.
    Credentials are decrypted internally by the repository.

    Gracefully handles cases where:
    - No credentials are stored (returns connected=False)
    - Encryption key is missing or invalid (returns connected=False)
    - Any other error occurs (returns connected=False)
    """
    try:
        credentials = _get_stored_credentials(strava_repo)

        if not credentials:
            return StravaStatusResponse(connected=False)

        return StravaStatusResponse(
            connected=True,
            athlete_id=credentials.user_id,
            athlete_name=credentials.user_name,
            scope=credentials.scope,
            expires_at=credentials.expires_at.isoformat() if credentials.expires_at else None,
            needs_refresh=credentials.needs_refresh,
        )
    except CredentialEncryptionError as e:
        # Encryption key missing or invalid - treat as not connected
        logger.warning(f"Strava status check failed due to encryption error: {e}")
        return StravaStatusResponse(connected=False)
    except HTTPException:
        # Re-raise HTTP exceptions (like 500 from _get_stored_credentials)
        # but for status endpoint, we want to return not connected instead
        return StravaStatusResponse(connected=False)
    except Exception as e:
        # Any other unexpected error - log and return not connected
        logger.error(f"Unexpected error checking Strava status: {e}")
        return StravaStatusResponse(connected=False)


@router.get("/preferences", response_model=StravaPreferencesResponse)
async def get_strava_preferences(
    strava_repo: StravaRepository = Depends(get_strava_repository),
):
    """
    Get Strava sharing preferences.

    Returns the user's preferences for what to include in Strava activity updates.
    """
    try:
        preferences = _get_stored_preferences(strava_repo)
    except Exception as e:
        logger.warning(f"Error fetching Strava preferences, returning defaults: {e}")
        # Return default preferences on error
        preferences = StravaPreferences(user_id="default")

    return StravaPreferencesResponse(
        success=True,
        preferences=preferences,
    )


@router.put("/preferences", response_model=StravaPreferencesResponse)
async def update_strava_preferences(
    preferences: StravaPreferences,
    strava_repo: StravaRepository = Depends(get_strava_repository),
):
    """
    Update Strava sharing preferences.

    Updates the user's preferences for what to include in Strava activity updates.
    """
    # Check if connected first
    credentials = _get_stored_credentials(strava_repo)
    if not credentials:
        raise HTTPException(
            status_code=400,
            detail="Not connected to Strava. Please connect first."
        )

    _save_preferences(strava_repo, preferences)

    return StravaPreferencesResponse(
        success=True,
        preferences=preferences,
    )


# =============================================================================
# Strava Sync Status Storage
# =============================================================================


class StravaSyncStatus(BaseModel):
    """Sync status for a workout."""
    workout_id: str
    synced: bool = False
    strava_activity_id: Optional[int] = None
    strava_url: Optional[str] = None
    synced_at: Optional[str] = None


def _ensure_sync_status_table(training_db: TrainingDatabase) -> None:
    """Ensure the strava_sync_status table exists."""
    with training_db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strava_sync_status (
                workout_id TEXT PRIMARY KEY,
                strava_activity_id INTEGER NOT NULL,
                strava_url TEXT NOT NULL,
                synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def _get_sync_status(training_db: TrainingDatabase, workout_id: str) -> Optional[StravaSyncStatus]:
    """Get sync status for a workout."""
    _ensure_sync_status_table(training_db)

    with training_db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT workout_id, strava_activity_id, strava_url, synced_at
            FROM strava_sync_status
            WHERE workout_id = ?
        """, (workout_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return StravaSyncStatus(
            workout_id=row[0],
            synced=True,
            strava_activity_id=row[1],
            strava_url=row[2],
            synced_at=row[3],
        )


def _save_sync_status(
    training_db: TrainingDatabase,
    workout_id: str,
    strava_activity_id: int,
    strava_url: str,
) -> None:
    """Save sync status for a workout."""
    _ensure_sync_status_table(training_db)

    with training_db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO strava_sync_status
            (workout_id, strava_activity_id, strava_url, synced_at)
            VALUES (?, ?, ?, ?)
        """, (workout_id, strava_activity_id, strava_url, datetime.now().isoformat()))


# =============================================================================
# Strava Sync Endpoint
# =============================================================================


class StravaSyncResponse(BaseModel):
    """Response from syncing workout to Strava."""
    success: bool
    message: str
    strava_activity_id: Optional[int] = None
    strava_url: Optional[str] = None


@router.get("/sync/{workout_id}/status", response_model=StravaSyncStatus)
async def get_strava_sync_status(
    workout_id: str,
    training_db: TrainingDatabase = Depends(get_training_db),
):
    """
    Get sync status for a workout.

    Returns whether the workout has been synced to Strava and the Strava URL.
    Note: Sync status uses training_db since it's not sensitive data.
    """
    status = _get_sync_status(training_db, workout_id)
    if status:
        return status
    return StravaSyncStatus(workout_id=workout_id, synced=False)


@router.post("/sync/{workout_id}", response_model=StravaSyncResponse)
async def sync_workout_to_strava(
    workout_id: str,
    training_db: TrainingDatabase = Depends(get_training_db),
    strava_repo: StravaRepository = Depends(get_strava_repository),
):
    """
    Sync a workout analysis to the matching Strava activity.

    Uses encrypted credentials from StravaRepository.

    This endpoint:
    1. Gets the workout's date and analysis
    2. Finds the matching Strava activity (by date and type)
    3. Updates the Strava activity description with the analysis
    """
    # 1. Check if connected to Strava (uses encrypted credentials)
    credentials = _get_stored_credentials(strava_repo)
    if not credentials:
        raise HTTPException(
            status_code=400,
            detail="Not connected to Strava. Please connect first."
        )

    # 2. Refresh token if needed (saves with encryption)
    credentials = await _refresh_token_if_needed(strava_repo, credentials)

    # 3. Get the workout/activity from database
    activity = training_db.get_activity_metrics(workout_id)
    if not activity:
        raise HTTPException(
            status_code=404,
            detail=f"Workout {workout_id} not found"
        )

    # 4. Get the analysis for this workout
    analysis_data = training_db.get_workout_analysis(workout_id)
    if not analysis_data:
        raise HTTPException(
            status_code=400,
            detail="No analysis found for this workout. Generate analysis first."
        )

    # 5. Get user preferences
    preferences = _get_stored_preferences(strava_repo)

    # 6. Format the description
    score = analysis_data.get("overall_score", 0)
    if score >= 80:
        score_emoji = "🟢"
    elif score >= 60:
        score_emoji = "🟡"
    else:
        score_emoji = "🔴"

    summary = analysis_data.get("summary", "Great session")[:100].rstrip('.')
    share_url = f"http://localhost:3000/workouts/{workout_id}"  # TODO: Use real base URL

    if preferences.use_extended_format:
        # Extended format
        lines = [f"{score_emoji} {score}/100 · {summary}"]
        training_effect = analysis_data.get("training_effect_score")
        if training_effect:
            lines.append(f"\n📈 Training Effect: {training_effect:.1f}")
        recovery = analysis_data.get("recovery_hours")
        if recovery:
            lines.append(f"⏱️ Recovery: {recovery}h")
        lines.append("\n---")
        lines.append("📊 Analyzed by Training Analyzer")
        lines.append(f"🔗 {share_url}")
        description_content = "\n".join(lines)
    else:
        # Simple format
        description_content = f"""{score_emoji} {score}/100 · {summary}

---
📊 Analyzed by Training Analyzer
🔗 {share_url}"""

    # 7. Find matching Strava activity by date
    from ...integrations.strava import StravaClient
    from datetime import timedelta

    client = StravaClient(credentials)

    try:
        # Parse the workout date
        workout_date = datetime.fromisoformat(activity.date.replace("Z", "+00:00")) if "T" in activity.date else datetime.strptime(activity.date, "%Y-%m-%d")

        # Search for activities on that day (±1 day to handle timezone differences)
        start_date = workout_date - timedelta(days=1)
        end_date = workout_date + timedelta(days=1)

        strava_activities = await client.get_activities(
            start_date=start_date,
            end_date=end_date,
            limit=20,
        )

        if not strava_activities:
            await client.close()
            raise HTTPException(
                status_code=404,
                detail=f"No Strava activities found around {activity.date}. Make sure your activity is on Strava."
            )

        # Find the best match based on date and duration
        # For now, pick the closest one by start time
        workout_duration_min = activity.duration_min or 0

        best_match = None
        best_time_diff = float("inf")

        for sa in strava_activities:
            # Compare dates
            time_diff = abs((sa.start_date.replace(tzinfo=None) - workout_date.replace(tzinfo=None)).total_seconds())

            # Also consider duration match
            strava_duration_min = sa.elapsed_time_sec / 60.0
            duration_diff = abs(strava_duration_min - workout_duration_min)

            # Score: prefer closer time and similar duration
            match_score = time_diff + (duration_diff * 60)  # Duration diff weighted less

            if match_score < best_time_diff:
                best_time_diff = match_score
                best_match = sa

        if not best_match:
            await client.close()
            raise HTTPException(
                status_code=404,
                detail="Could not find a matching Strava activity."
            )

        # 8. Update the Strava activity description
        updated = await client.update_activity_description(
            activity_id=best_match.id,
            analysis_content=description_content,
        )

        await client.close()

        strava_url = f"https://www.strava.com/activities/{best_match.id}"

        # 9. Save sync status to database
        _save_sync_status(training_db, workout_id, best_match.id, strava_url)

        return StravaSyncResponse(
            success=True,
            message=f"Successfully synced analysis to '{best_match.name}' on Strava!",
            strava_activity_id=best_match.id,
            strava_url=strava_url,
        )

    except HTTPException:
        await client.close()
        raise
    except Exception as e:
        await client.close()
        logger.error(f"Strava sync failed for workout {workout_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to sync to Strava. Please try again."
        )
