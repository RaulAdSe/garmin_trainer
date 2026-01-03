"""
Emotional engagement API routes for social proof, comeback challenges, and personal records.

Provides:
- Community statistics and social validation to increase user engagement
- Comeback challenge system for streak recovery with bonus XP
- Personal record (PR) detection, tracking, and celebration
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from ..deps import get_training_db, get_current_user, CurrentUser
from ...services.social_proof_service import SocialProofService, SocialProofStats
from ...services.achievement_service import AchievementService
from ...services.comeback_service import ComebackService, get_comeback_service
from ...services.pr_detection_service import PRDetectionService
from ...db.models.comeback import ComebackChallengeStatus
from ...models.personal_records import (
    PersonalRecord,
    PRType,
    ActivityType,
    PRDetectionResult,
    PRSummary,
    PRComparisonResult,
    PRListResponse,
    RecentPRsResponse,
    to_camel,
)


logger = logging.getLogger(__name__)

router = APIRouter()


def get_social_proof_service(
    training_db=Depends(get_training_db),
) -> SocialProofService:
    """Get social proof service instance."""
    return SocialProofService(str(training_db.db_path))


def get_achievement_service(
    training_db=Depends(get_training_db),
) -> AchievementService:
    """Get achievement service instance."""
    return AchievementService(str(training_db.db_path))


@router.get("/social-proof", response_model=SocialProofStats)
async def get_social_proof(
    current_user: CurrentUser = Depends(get_current_user),
    social_proof_service: SocialProofService = Depends(get_social_proof_service),
    achievement_service: AchievementService = Depends(get_achievement_service),
    training_db=Depends(get_training_db),
) -> SocialProofStats:
    """
    Get social proof statistics for the community.

    Returns:
    - Number of athletes who trained today
    - Total workouts completed today
    - Athletes currently training (live-ish indicator)
    - User's percentile rankings (if they have data):
        - Pace percentile
        - Streak percentile
        - Level percentile
    - Recent community activity feed

    These stats are cached for performance and refreshed periodically.
    """
    try:
        # Get user's progress for percentile calculations
        user_progress = achievement_service.get_user_progress()

        # Get user's level and streak
        user_level: Optional[int] = None
        user_streak: Optional[int] = None

        if user_progress:
            user_level = user_progress.level.level if user_progress.level else None
            user_streak = user_progress.streak.current if user_progress.streak else None

        # Get user's average pace (from recent workouts)
        user_avg_pace: Optional[float] = None
        try:
            # Try to get average pace from recent running workouts
            recent_activities = training_db.get_recent_activities(limit=10)
            running_paces = []

            for activity in recent_activities:
                if (
                    activity.type
                    and "run" in activity.type.lower()
                    and activity.distance
                    and activity.duration
                    and activity.distance > 0
                    and activity.duration > 0
                ):
                    # Calculate pace in min/km
                    distance_km = activity.distance / 1000  # Assuming meters
                    duration_min = activity.duration / 60  # Assuming seconds
                    if distance_km > 0:
                        pace = duration_min / distance_km
                        if 3.0 < pace < 15.0:  # Reasonable running pace
                            running_paces.append(pace)

            if running_paces:
                user_avg_pace = sum(running_paces) / len(running_paces)

        except Exception as e:
            logger.debug(f"Could not calculate user average pace: {e}")

        # Get social proof stats with user context
        stats = social_proof_service.get_social_proof_stats(
            user_level=user_level,
            user_streak=user_streak,
            user_avg_pace=user_avg_pace,
        )

        return stats

    except Exception as e:
        logger.error(f"Failed to get social proof stats: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get social proof statistics. Please try again later.",
        )


# =============================================================================
# Emotional Support Messaging Service Import
# =============================================================================

from ...services.emotional_messaging_service import (
    EmotionalMessagingService,
    EmotionalContext,
    EmotionalMessage,
    MessageTone,
    get_emotional_messaging_service,
)


# =============================================================================
# Emotional Support Messaging Response Models
# =============================================================================


class EmotionalMessageResponse(BaseModel):
    """Response model for a single emotional message."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    context: str = Field(..., description="The context that triggered this message")
    message: str = Field(..., description="The main supportive message")
    tone: str = Field(..., description="The emotional tone of the message")
    action_suggestion: Optional[str] = Field(None, description="Optional suggested action")
    recovery_tips: Optional[List[str]] = Field(
        None, description="Recovery tips for red zone/recovery contexts"
    )
    alternative_activities: Optional[List[str]] = Field(
        None, description="Alternative activity suggestions"
    )


class EmotionalMessagesListResponse(BaseModel):
    """Response model for listing all messages for a context."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    messages: List[EmotionalMessageResponse] = Field(
        ..., description="All messages for the given context"
    )
    count: int = Field(..., description="Number of messages")


class DetectedContextResponse(BaseModel):
    """Response model for detected emotional context."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    detected_context: Optional[str] = Field(
        None, description="The detected context, or null if none"
    )
    message: Optional[EmotionalMessageResponse] = Field(
        None, description="A suggested message for the context"
    )


class AvailableContextsResponse(BaseModel):
    """Response model for available emotional contexts."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    contexts: List[str] = Field(..., description="Available emotional contexts")


# =============================================================================
# Emotional Messaging Helper Functions
# =============================================================================


def _message_to_response(message: EmotionalMessage) -> EmotionalMessageResponse:
    """Convert EmotionalMessage to response model."""
    return EmotionalMessageResponse(
        context=message.context.value,
        message=message.message,
        tone=message.tone.value,
        action_suggestion=message.action_suggestion,
        recovery_tips=message.recovery_tips,
        alternative_activities=message.alternative_activities,
    )


# =============================================================================
# Emotional Support Messaging Endpoints
# =============================================================================


@router.get("/message", response_model=EmotionalMessageResponse)
async def get_contextual_message(
    context: str = Query(..., description="Emotional context (e.g., 'red_zone_readiness', 'streak_break')"),
    include_tips: bool = Query(True, description="Include recovery tips and alternatives"),
    tone: Optional[str] = Query(None, description="Preferred message tone (empathetic, supportive, encouraging)"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get a contextual supportive message.

    Returns an appropriate emotional support message based on the specified context.
    Multiple calls with the same context may return different messages for variety.

    Available contexts:
    - red_zone_readiness: When readiness score indicates need for rest
    - streak_break: When a training streak is broken
    - plateau: When progress has stalled
    - bad_workout: After a difficult or underperforming workout
    - comeback: When returning after a break
    - consistency_milestone: When achieving a consistency goal
    - recovery_day: On planned recovery days

    Requires authentication.
    """
    try:
        # Validate context
        try:
            emotional_context = EmotionalContext(context)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid context: {context}. Valid contexts: {[c.value for c in EmotionalContext]}"
            )

        # Validate tone if provided
        preferred_tone = None
        if tone:
            try:
                preferred_tone = MessageTone(tone)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid tone: {tone}. Valid tones: {[t.value for t in MessageTone]}"
                )

        service = get_emotional_messaging_service()
        message = service.get_contextual_message(
            context=emotional_context,
            include_tips=include_tips,
            preferred_tone=preferred_tone,
        )

        return _message_to_response(message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get emotional message: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get emotional message. Please try again later.",
        )


@router.get("/messages/{context}", response_model=EmotionalMessagesListResponse)
async def get_all_messages_for_context(
    context: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get all available messages for a specific context.

    Useful for UI to show message rotation or let user choose.

    Requires authentication.
    """
    try:
        # Validate context
        try:
            emotional_context = EmotionalContext(context)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid context: {context}. Valid contexts: {[c.value for c in EmotionalContext]}"
            )

        service = get_emotional_messaging_service()
        messages = service.get_all_messages_for_context(emotional_context)

        return EmotionalMessagesListResponse(
            messages=[_message_to_response(m) for m in messages],
            count=len(messages),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get messages for context: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get messages. Please try again later.",
        )


@router.get("/detect", response_model=DetectedContextResponse)
async def detect_emotional_context(
    current_user: CurrentUser = Depends(get_current_user),
    training_db=Depends(get_training_db),
):
    """
    Automatically detect appropriate emotional context from athlete data.

    Analyzes current athlete state to determine if any emotional support
    message would be appropriate.

    Returns detected context and suggested message, or null if no special
    context is detected.

    Requires authentication.
    """
    from datetime import date, timedelta
    
    try:
        service = get_emotional_messaging_service()

        # Get athlete data for context detection
        readiness_score: Optional[float] = None
        current_streak: Optional[int] = None
        previous_streak: Optional[int] = None
        days_since_last_workout: Optional[int] = None
        weeks_without_improvement: Optional[int] = None
        last_workout_score: Optional[float] = None
        consecutive_training_days: Optional[int] = None

        # Get readiness from latest fitness metrics
        latest_fitness = training_db.get_latest_fitness_metrics()
        if latest_fitness:
            # Estimate readiness from TSB (Training Stress Balance)
            tsb = latest_fitness.tsb
            if tsb is not None:
                # Convert TSB to readiness score (TSB of 0 = ~50 readiness)
                # TSB of +20 = ~80 readiness, TSB of -20 = ~20 readiness
                readiness_score = max(0, min(100, 50 + (tsb * 1.5)))

        # Get user progress for streak info
        try:
            achievement_service = AchievementService(str(training_db.db_path))
            progress = achievement_service.get_user_progress()
            current_streak = progress.current_streak
            consecutive_training_days = progress.current_streak
        except Exception:
            pass

        # Try to get days since last workout
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            workouts = training_db.get_activities_range(
                start_date.isoformat(),
                end_date.isoformat()
            )
            if workouts:
                last_workout_date = date.fromisoformat(workouts[0].date[:10])
                days_since_last_workout = (end_date - last_workout_date).days
        except Exception:
            pass

        # Detect context
        detected = service.detect_context_from_data(
            readiness_score=readiness_score,
            current_streak=current_streak,
            previous_streak=previous_streak,
            days_since_last_workout=days_since_last_workout,
            weeks_without_improvement=weeks_without_improvement,
            last_workout_score=last_workout_score,
            consecutive_training_days=consecutive_training_days,
        )

        if detected:
            message = service.get_contextual_message(detected)
            return DetectedContextResponse(
                detected_context=detected.value,
                message=_message_to_response(message),
            )

        return DetectedContextResponse(
            detected_context=None,
            message=None,
        )

    except Exception as e:
        logger.error(f"Failed to detect emotional context: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to detect emotional context. Please try again later.",
        )


@router.get("/contexts", response_model=AvailableContextsResponse)
async def get_available_contexts():
    """
    Get list of available emotional contexts.

    This endpoint does not require authentication.
    """
    return AvailableContextsResponse(
        contexts=[c.value for c in EmotionalContext]
    )


@router.get("/recovery", response_model=Optional[EmotionalMessageResponse])
async def get_recovery_message(
    readiness_score: float = Query(..., ge=0, le=100, description="Current readiness score (0-100)"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get a recovery-focused message based on readiness score.

    Returns a message if readiness is in yellow or red zone, null otherwise.

    Requires authentication.
    """
    try:
        service = get_emotional_messaging_service()
        message = service.get_recovery_message(readiness_score)

        if message:
            return _message_to_response(message)
        return None

    except Exception as e:
        logger.error(f"Failed to get recovery message: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get recovery message. Please try again later.",
        )


# =============================================================================
# Personal Records (PR) Endpoints
# =============================================================================


def get_pr_service(training_db=Depends(get_training_db)) -> PRDetectionService:
    """Get PR detection service instance."""
    return PRDetectionService(str(training_db.db_path))


class DetectPRsRequest(BaseModel):
    """Request model for detecting PRs in a workout."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    workout_id: str = Field(..., description="ID of the workout to analyze for PRs")


class DetectPRsResponse(BaseModel):
    """Response model for PR detection."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    result: PRDetectionResult = Field(..., description="PR detection results")
    celebration_data: Optional[dict] = Field(
        None, description="Data for celebration UI if new PR detected"
    )


class BestPRsResponse(BaseModel):
    """Response model for getting best PRs."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    best_prs: dict = Field(..., description="Best PR for each type/activity combination")
    total: int = Field(..., description="Total number of unique best PRs")


@router.get("/prs", response_model=PRListResponse)
async def get_personal_records(
    pr_type: Optional[PRType] = Query(None, description="Filter by PR type"),
    activity_type: Optional[ActivityType] = Query(None, description="Filter by activity type"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: CurrentUser = Depends(get_current_user),
    pr_service: PRDetectionService = Depends(get_pr_service),
):
    """
    Get all personal records for the current user.

    Returns a paginated list of personal records with optional filtering
    by PR type and activity type.

    Requires authentication.
    """
    try:
        prs = pr_service.get_user_prs(
            user_id=current_user.id if current_user else "default",
            pr_type=pr_type,
            activity_type=activity_type,
            limit=limit,
            offset=offset
        )

        summary = pr_service.get_pr_summary(
            user_id=current_user.id if current_user else "default"
        )

        return PRListResponse(
            personal_records=prs,
            total=summary.total_prs,
            summary=summary
        )

    except Exception as e:
        logger.error(f"Failed to get personal records: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get personal records. Please try again later."
        )


@router.get("/prs/recent", response_model=RecentPRsResponse)
async def get_recent_prs(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: CurrentUser = Depends(get_current_user),
    pr_service: PRDetectionService = Depends(get_pr_service),
):
    """
    Get recently achieved personal records.

    Returns personal records achieved in the specified time period (default 30 days).

    Requires authentication.
    """
    try:
        prs = pr_service.get_recent_prs(
            user_id=current_user.id if current_user else "default",
            days=days
        )

        return RecentPRsResponse(
            personal_records=prs,
            count=len(prs),
            days=days
        )

    except Exception as e:
        logger.error(f"Failed to get recent PRs: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get recent personal records. Please try again later."
        )


@router.get("/prs/best", response_model=BestPRsResponse)
async def get_best_prs(
    current_user: CurrentUser = Depends(get_current_user),
    pr_service: PRDetectionService = Depends(get_pr_service),
):
    """
    Get the current best PR for each type/activity combination.

    Returns a dictionary mapping each PR type and activity type combination
    to the user's best performance in that category.

    Requires authentication.
    """
    try:
        best_prs = pr_service.get_best_prs(
            user_id=current_user.id if current_user else "default"
        )

        # Convert PersonalRecord objects to dicts for JSON serialization
        serializable_prs = {}
        for key, pr in best_prs.items():
            serializable_prs[key] = pr.model_dump(by_alias=True)

        return BestPRsResponse(
            best_prs=serializable_prs,
            total=len(best_prs)
        )

    except Exception as e:
        logger.error(f"Failed to get best PRs: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get best personal records. Please try again later."
        )


@router.post("/prs/detect", response_model=DetectPRsResponse)
async def detect_prs(
    request: DetectPRsRequest,
    current_user: CurrentUser = Depends(get_current_user),
    pr_service: PRDetectionService = Depends(get_pr_service),
):
    """
    Detect personal records in a workout.

    Analyzes the specified workout for any new personal records based on
    configured thresholds:
    - Pace PRs: minimum 1km distance
    - Distance PRs: minimum 10 minute duration
    - Elevation PRs: minimum 3km distance

    Returns detection results and celebration data if new PRs are found.

    Requires authentication.
    """
    try:
        result = pr_service.detect_prs(
            workout_id=request.workout_id,
            user_id=current_user.id if current_user else "default"
        )

        # Prepare celebration data if new PR detected
        celebration_data = None
        if result.has_new_pr and result.new_prs:
            # Get the most significant PR for celebration
            primary_pr = result.new_prs[0]
            celebration_data = {
                "prType": primary_pr.pr_type.value,
                "activityType": primary_pr.activity_type.value,
                "value": primary_pr.value,
                "unit": primary_pr.unit,
                "improvement": primary_pr.improvement,
                "improvementPercent": primary_pr.improvement_percent,
                "previousValue": primary_pr.previous_value,
                "workoutName": primary_pr.workout_name,
                "workoutDate": primary_pr.workout_date,
                "allPRs": [
                    {
                        "prType": pr.pr_type.value,
                        "value": pr.value,
                        "unit": pr.unit,
                        "improvement": pr.improvement,
                    }
                    for pr in result.new_prs
                ]
            }

        return DetectPRsResponse(
            result=result,
            celebration_data=celebration_data
        )

    except Exception as e:
        logger.error(f"Failed to detect PRs: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to detect personal records. Please try again later."
        )


@router.get("/prs/compare/{workout_id}", response_model=PRComparisonResult)
async def compare_workout_to_prs(
    workout_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    pr_service: PRDetectionService = Depends(get_pr_service),
):
    """
    Compare a workout to existing personal records.

    Shows how the workout compares to the user's best performances
    in each relevant category.

    Requires authentication.
    """
    try:
        result = pr_service.compare_to_best(
            workout_id=workout_id,
            user_id=current_user.id if current_user else "default"
        )

        return result

    except Exception as e:
        logger.error(f"Failed to compare workout to PRs: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to compare workout to personal records. Please try again later."
        )


@router.get("/prs/summary", response_model=PRSummary)
async def get_pr_summary_endpoint(
    current_user: CurrentUser = Depends(get_current_user),
    pr_service: PRDetectionService = Depends(get_pr_service),
):
    """
    Get summary of user's personal records.

    Returns aggregate information about the user's PRs including
    total count, recent count, and breakdown by type.

    Requires authentication.
    """
    try:
        summary = pr_service.get_pr_summary(
            user_id=current_user.id if current_user else "default"
        )

        return summary

    except Exception as e:
        logger.error(f"Failed to get PR summary: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get personal record summary. Please try again later."
        )


# =============================================================================
# Comeback Challenge Response Models
# =============================================================================


class ComebackChallengeResponse(BaseModel):
    """Response model for a comeback challenge."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str
    user_id: str = Field(..., alias="userId")
    triggered_at: str = Field(..., alias="triggeredAt")
    previous_streak: int = Field(..., alias="previousStreak")
    status: str
    day1_completed_at: Optional[str] = Field(None, alias="day1CompletedAt")
    day2_completed_at: Optional[str] = Field(None, alias="day2CompletedAt")
    day3_completed_at: Optional[str] = Field(None, alias="day3CompletedAt")
    xp_multiplier: float = Field(..., alias="xpMultiplier")
    bonus_xp_earned: int = Field(..., alias="bonusXpEarned")
    expires_at: Optional[str] = Field(None, alias="expiresAt")
    created_at: Optional[str] = Field(None, alias="createdAt")
    days_completed: int = Field(..., alias="daysCompleted")
    is_complete: bool = Field(..., alias="isComplete")
    is_active: bool = Field(..., alias="isActive")
    next_day_to_complete: Optional[int] = Field(None, alias="nextDayToComplete")


class RecordComebackWorkoutRequest(BaseModel):
    """Request model for recording a comeback workout."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    workout_id: str = Field(..., alias="workoutId")
    base_xp: int = Field(default=25, alias="baseXp")


class RecordComebackWorkoutResponse(BaseModel):
    """Response model for recording a comeback workout."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    success: bool
    challenge: Optional[ComebackChallengeResponse] = None
    bonus_xp_earned: int = Field(..., alias="bonusXpEarned")
    total_xp_earned: int = Field(..., alias="totalXpEarned")
    challenge_completed: bool = Field(..., alias="challengeCompleted")
    message: str


class TriggerComebackChallengeRequest(BaseModel):
    """Request model for triggering a comeback challenge."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    previous_streak: int = Field(..., alias="previousStreak", ge=3)


class ComebackChallengeHistoryResponse(BaseModel):
    """Response model for challenge history."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    challenges: List[ComebackChallengeResponse]
    total: int


# =============================================================================
# Comeback Challenge Dependencies
# =============================================================================


def get_comeback_service_dep(training_db=Depends(get_training_db)) -> ComebackService:
    """Get comeback service instance using the training database path."""
    return get_comeback_service(str(training_db.db_path))


def challenge_to_response(challenge) -> ComebackChallengeResponse:
    """Convert a ComebackChallenge to a response model."""
    return ComebackChallengeResponse(
        id=challenge.id,
        user_id=challenge.user_id,
        triggered_at=challenge.triggered_at.isoformat(),
        previous_streak=challenge.previous_streak,
        status=challenge.status.value,
        day1_completed_at=(
            challenge.day1_completed_at.isoformat()
            if challenge.day1_completed_at
            else None
        ),
        day2_completed_at=(
            challenge.day2_completed_at.isoformat()
            if challenge.day2_completed_at
            else None
        ),
        day3_completed_at=(
            challenge.day3_completed_at.isoformat()
            if challenge.day3_completed_at
            else None
        ),
        xp_multiplier=challenge.xp_multiplier,
        bonus_xp_earned=challenge.bonus_xp_earned,
        expires_at=(
            challenge.expires_at.isoformat() if challenge.expires_at else None
        ),
        created_at=(
            challenge.created_at.isoformat() if challenge.created_at else None
        ),
        days_completed=challenge.days_completed,
        is_complete=challenge.is_complete,
        is_active=challenge.is_active,
        next_day_to_complete=challenge.get_next_day_to_complete(),
    )


# =============================================================================
# Comeback Challenge Endpoints
# =============================================================================


@router.get("/comeback-challenge", response_model=Optional[ComebackChallengeResponse])
async def get_active_comeback_challenge(
    current_user: CurrentUser = Depends(get_current_user),
    comeback_service: ComebackService = Depends(get_comeback_service_dep),
):
    """
    Get the active comeback challenge for the current user.

    Returns the current active comeback challenge if one exists,
    or null if no active challenge.

    Requires authentication.
    """
    try:
        challenge = comeback_service.get_active_challenge(current_user.id)

        if not challenge:
            return None

        return challenge_to_response(challenge)

    except Exception as e:
        logger.error(f"Failed to get comeback challenge: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get comeback challenge. Please try again later.",
        )


@router.post("/comeback-challenge/record", response_model=RecordComebackWorkoutResponse)
async def record_comeback_workout(
    request: RecordComebackWorkoutRequest,
    current_user: CurrentUser = Depends(get_current_user),
    comeback_service: ComebackService = Depends(get_comeback_service_dep),
):
    """
    Record a workout during an active comeback challenge.

    Applies the XP multiplier (1.5x) and updates challenge progress.
    When all 3 days are completed, awards a completion bonus.

    Requires authentication.
    """
    try:
        challenge, bonus_xp, completed = comeback_service.record_comeback_workout(
            user_id=current_user.id,
            workout_id=request.workout_id,
            base_xp=request.base_xp,
        )

        if not challenge:
            return RecordComebackWorkoutResponse(
                success=False,
                challenge=None,
                bonus_xp_earned=0,
                total_xp_earned=request.base_xp,
                challenge_completed=False,
                message="No active comeback challenge found",
            )

        total_xp = request.base_xp + bonus_xp

        if completed:
            message = (
                f"Amazing comeback! Challenge completed! "
                f"You earned {total_xp} XP (including 100 XP completion bonus)!"
            )
        else:
            day = challenge.days_completed
            message = (
                f"Day {day} of 3 complete! "
                f"You earned {total_xp} XP with your 1.5x bonus!"
            )

        return RecordComebackWorkoutResponse(
            success=True,
            challenge=challenge_to_response(challenge),
            bonus_xp_earned=bonus_xp,
            total_xp_earned=total_xp,
            challenge_completed=completed,
            message=message,
        )

    except Exception as e:
        logger.error(f"Failed to record comeback workout: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to record comeback workout. Please try again later.",
        )


@router.post("/comeback-challenge/trigger", response_model=Optional[ComebackChallengeResponse])
async def trigger_comeback_challenge(
    request: TriggerComebackChallengeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    comeback_service: ComebackService = Depends(get_comeback_service_dep),
):
    """
    Trigger a new comeback challenge.

    This endpoint is typically called automatically when a streak breaks,
    but can be called manually for testing or administrative purposes.

    The previous streak must be at least 3 days to qualify for a comeback challenge.

    Requires authentication.
    """
    try:
        challenge = comeback_service.check_and_trigger_comeback(
            user_id=current_user.id,
            previous_streak=request.previous_streak,
        )

        if not challenge:
            return None

        return challenge_to_response(challenge)

    except Exception as e:
        logger.error(f"Failed to trigger comeback challenge: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to trigger comeback challenge. Please try again later.",
        )


@router.get("/comeback-challenge/history", response_model=ComebackChallengeHistoryResponse)
async def get_comeback_history(
    limit: int = 10,
    current_user: CurrentUser = Depends(get_current_user),
    comeback_service: ComebackService = Depends(get_comeback_service_dep),
):
    """
    Get comeback challenge history for the current user.

    Returns past comeback challenges, newest first.

    Requires authentication.
    """
    try:
        challenges = comeback_service.get_user_challenges(
            user_id=current_user.id,
            limit=limit,
        )

        return ComebackChallengeHistoryResponse(
            challenges=[challenge_to_response(c) for c in challenges],
            total=len(challenges),
        )

    except Exception as e:
        logger.error(f"Failed to get comeback history: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get comeback history. Please try again later.",
        )


@router.post("/comeback-challenge/{challenge_id}/cancel", response_model=Optional[ComebackChallengeResponse])
async def cancel_comeback_challenge(
    challenge_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    comeback_service: ComebackService = Depends(get_comeback_service_dep),
):
    """
    Cancel an active comeback challenge.

    Requires authentication.
    """
    try:
        # First verify the challenge belongs to this user
        challenge = comeback_service.get_challenge(challenge_id)

        if not challenge:
            raise HTTPException(
                status_code=404,
                detail="Challenge not found",
            )

        if challenge.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only cancel your own challenges",
            )

        updated = comeback_service.cancel_challenge(challenge_id)

        if not updated:
            raise HTTPException(
                status_code=400,
                detail="Could not cancel challenge. It may already be completed or expired.",
            )

        return challenge_to_response(updated)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel comeback challenge: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to cancel comeback challenge. Please try again later.",
        )


# =============================================================================
# Identity Commitment Feature
# =============================================================================

from ...services.identity_service import (
    IdentityService,
    IdentityStatement,
    get_identity_service,
)


# Identity Response Models

class IdentityStatementResponse(BaseModel):
    """Response model for identity statement."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: int = Field(..., description="Statement ID")
    user_id: str = Field(..., description="User ID", alias="userId")
    statement: str = Field(..., description="The identity statement")
    created_at: str = Field(..., description="Creation timestamp", alias="createdAt")
    last_reinforced_at: str = Field(
        ..., description="Last reinforcement timestamp", alias="lastReinforcedAt"
    )
    reinforcement_count: int = Field(
        ..., description="Number of reinforcements", alias="reinforcementCount"
    )


class IdentityTemplateResponse(BaseModel):
    """Response model for identity template."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str = Field(..., description="Template ID")
    statement: str = Field(..., description="Template statement")
    description: str = Field(..., description="Template description")


class IdentityTemplatesResponse(BaseModel):
    """Response model for list of templates."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    templates: List[IdentityTemplateResponse] = Field(
        ..., description="List of available templates"
    )


class CreateIdentityRequest(BaseModel):
    """Request model for creating identity statement."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    statement: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="The identity statement (without 'I am someone who')",
    )


class ReinforcementCheckResponse(BaseModel):
    """Response model for reinforcement check."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    should_show_reinforcement: bool = Field(
        ...,
        description="Whether to show reinforcement modal",
        alias="shouldShowReinforcement",
    )
    statement: Optional[IdentityStatementResponse] = Field(
        None, description="Current identity statement if exists"
    )


# Identity Service Dependency

def get_identity_service_dep(
    training_db=Depends(get_training_db),
) -> IdentityService:
    """Get identity service instance using the training database."""
    return get_identity_service(training_db)


def statement_to_response(
    statement: IdentityStatement,
) -> IdentityStatementResponse:
    """Convert IdentityStatement to response model."""
    return IdentityStatementResponse(
        id=statement.id,
        user_id=statement.user_id,
        statement=statement.statement,
        created_at=statement.created_at,
        last_reinforced_at=statement.last_reinforced_at,
        reinforcement_count=statement.reinforcement_count,
    )


# Identity Endpoints

@router.get("/identity/templates", response_model=IdentityTemplatesResponse)
async def get_identity_templates(
    current_user: CurrentUser = Depends(get_current_user),
    identity_service: IdentityService = Depends(get_identity_service_dep),
):
    """
    Get available identity statement templates.

    Returns a list of pre-defined identity statement templates that users
    can choose from when creating their identity commitment.

    Requires authentication.
    """
    try:
        templates = identity_service.get_templates()
        return IdentityTemplatesResponse(
            templates=[
                IdentityTemplateResponse(
                    id=t.id,
                    statement=t.statement,
                    description=t.description,
                )
                for t in templates
            ]
        )
    except Exception as e:
        logger.error(f"Failed to get identity templates: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get identity templates. Please try again later.",
        )


@router.get("/identity", response_model=Optional[IdentityStatementResponse])
async def get_identity_statement(
    current_user: CurrentUser = Depends(get_current_user),
    identity_service: IdentityService = Depends(get_identity_service_dep),
):
    """
    Get the current user's identity statement.

    Returns the user's identity commitment statement if one exists,
    or null if the user hasn't created one yet.

    Requires authentication.
    """
    try:
        statement = identity_service.get_statement(current_user.user_id)
        if statement:
            return statement_to_response(statement)
        return None
    except Exception as e:
        logger.error(f"Failed to get identity statement: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get identity statement. Please try again later.",
        )


@router.post("/identity", response_model=IdentityStatementResponse)
async def create_identity_statement(
    request: CreateIdentityRequest,
    current_user: CurrentUser = Depends(get_current_user),
    identity_service: IdentityService = Depends(get_identity_service_dep),
):
    """
    Create or update the user's identity statement.

    Creates a new identity commitment statement or updates the existing one.
    The statement should complete "I am someone who..." (don't include this prefix).

    Requires authentication.
    """
    try:
        statement = identity_service.create_statement(
            user_id=current_user.user_id,
            statement=request.statement,
        )
        return statement_to_response(statement)
    except Exception as e:
        logger.error(f"Failed to create identity statement: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create identity statement. Please try again later.",
        )


@router.post("/identity/reinforce", response_model=IdentityStatementResponse)
async def reinforce_identity_statement(
    current_user: CurrentUser = Depends(get_current_user),
    identity_service: IdentityService = Depends(get_identity_service_dep),
):
    """
    Reinforce the user's identity statement.

    Called when the user acknowledges their identity statement (e.g., in
    the weekly reinforcement modal). This strengthens the psychological
    commitment over time.

    Requires authentication.
    """
    try:
        statement = identity_service.reinforce_statement(current_user.user_id)
        if not statement:
            raise HTTPException(
                status_code=404,
                detail="No identity statement found. Create one first.",
            )
        return statement_to_response(statement)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reinforce identity statement: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to reinforce identity statement. Please try again later.",
        )


@router.get("/identity/check-reinforcement", response_model=ReinforcementCheckResponse)
async def check_reinforcement(
    days_threshold: int = 7,
    current_user: CurrentUser = Depends(get_current_user),
    identity_service: IdentityService = Depends(get_identity_service_dep),
):
    """
    Check if it's time to show a reinforcement reminder.

    Returns whether the user should be shown the identity reinforcement
    modal based on the time since their last reinforcement.

    Args:
        days_threshold: Number of days between reinforcements (default 7)

    Requires authentication.
    """
    try:
        should_show = identity_service.should_show_reinforcement(
            current_user.user_id,
            days_threshold=days_threshold,
        )
        statement = identity_service.get_statement(current_user.user_id)

        return ReinforcementCheckResponse(
            should_show_reinforcement=should_show,
            statement=statement_to_response(statement) if statement else None,
        )
    except Exception as e:
        logger.error(f"Failed to check reinforcement: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to check reinforcement status. Please try again later.",
        )


@router.delete("/identity", status_code=204)
async def delete_identity_statement(
    current_user: CurrentUser = Depends(get_current_user),
    identity_service: IdentityService = Depends(get_identity_service_dep),
):
    """
    Delete the user's identity statement.

    Permanently removes the user's identity commitment statement.

    Requires authentication.
    """
    try:
        deleted = identity_service.delete_statement(current_user.user_id)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail="No identity statement found to delete.",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete identity statement: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete identity statement. Please try again later.",
        )
