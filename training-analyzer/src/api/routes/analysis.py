"""Workout analysis API routes."""

import asyncio
import logging
from datetime import date, datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from ..deps import get_coach_service, get_training_db, get_workout_repository, get_current_user, CurrentUser, get_consent_service_dep
from ..middleware.rate_limit import limiter, RATE_LIMIT_AI
from ..middleware.quota import require_quota
from ...db.repositories.workout_repository import WorkoutRepository
from ...db.database import TrainingDatabase
from ...llm.providers import get_llm_client, ModelType
from ...llm.context_builder import build_athlete_context_prompt, format_workout_for_prompt
from ...llm.prompts import (
    WORKOUT_ANALYSIS_SYSTEM,
    WORKOUT_ANALYSIS_USER,
    QUICK_SUMMARY_SYSTEM,
    QUICK_SUMMARY_USER,
)
from ...agents.analysis_agent import (
    AnalysisAgent,
    build_athlete_context_from_briefing,
    get_similar_workouts,
)
from ...models.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatus,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    RecentWorkoutsResponse,
    RecentWorkoutWithAnalysis,
    WorkoutAnalysisResult,
    WorkoutExecutionRating,
)


router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# Simple Analysis Storage (Direct DB access)
# ============================================================================

# In-memory cache for session performance (optional optimization)
_memory_cache: Dict[str, WorkoutAnalysisResult] = {}


def get_analysis(db: TrainingDatabase, workout_id: str) -> Optional[WorkoutAnalysisResult]:
    """Get analysis for a workout from DB (with memory cache for speed)."""
    # Check memory first
    if workout_id in _memory_cache:
        return _memory_cache[workout_id]

    # Check database
    data = db.get_workout_analysis(workout_id)
    if data:
        try:
            analysis = WorkoutAnalysisResult(
                workout_id=workout_id,
                analysis_id=f"db_{workout_id}",
                status=AnalysisStatus.COMPLETED,
                summary=data.get("summary", ""),
                what_worked_well=data.get("what_went_well", []),
                observations=data.get("improvements", []),
                training_fit=data.get("training_context", ""),
                execution_rating=data.get("execution_rating", "good"),
                overall_score=data.get("overall_score", 0),
                training_effect_score=data.get("training_effect_score", 0),
                load_score=data.get("load_score", 0),
                recovery_hours=data.get("recovery_hours", 0),
                model_used=data.get("model_used", ""),
                generated_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            )
            _memory_cache[workout_id] = analysis
            return analysis
        except Exception as e:
            logger.warning(f"Failed to parse analysis for {workout_id}: {e}")

    return None


def save_analysis(db: TrainingDatabase, workout_id: str, analysis: WorkoutAnalysisResult) -> None:
    """Save analysis to DB (and memory cache)."""
    try:
        db.save_workout_analysis(
            workout_id=workout_id,
            summary=analysis.summary,
            what_went_well=analysis.what_worked_well,
            improvements=analysis.observations,
            training_context=analysis.training_fit or "",
            execution_rating=analysis.execution_rating,
            overall_score=analysis.overall_score,
            training_effect_score=analysis.training_effect_score,
            load_score=analysis.load_score,
            recovery_hours=analysis.recovery_hours,
            model_used=analysis.model_used or "",
        )
        _memory_cache[workout_id] = analysis
    except Exception as e:
        logger.error(f"Failed to save analysis for {workout_id}: {e}")


def delete_analysis(db: TrainingDatabase, workout_id: str) -> bool:
    """Delete analysis from DB and memory."""
    if workout_id in _memory_cache:
        del _memory_cache[workout_id]
    return db.delete_workout_analysis(workout_id)


# Singleton agent instance
_analysis_agent: Optional[AnalysisAgent] = None


def get_analysis_agent(user_id: Optional[str] = None) -> AnalysisAgent:
    """Get the analysis agent singleton."""
    global _analysis_agent
    if _analysis_agent is None:
        import logging
        logger = logging.getLogger(__name__)
        try:
            logger.info("Initializing AnalysisAgent...")
            _analysis_agent = AnalysisAgent(user_id=user_id)
            logger.info("AnalysisAgent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AnalysisAgent: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize analysis agent. Please try again later."
            )
    # Update user_id on each request (for usage tracking)
    _analysis_agent.user_id = user_id
    return _analysis_agent




# ============================================================================
# Historical Context Helper
# ============================================================================

def _build_athlete_context_from_historical(historical_context: Dict) -> Dict:
    """
    Build athlete context dictionary from historical context.

    This is similar to build_athlete_context_from_briefing but uses
    the historical context structure returned by get_historical_athlete_context.

    Args:
        historical_context: Dictionary from coach_service.get_historical_athlete_context()

    Returns:
        Dictionary suitable for AnalysisAgent
    """
    fitness_metrics = historical_context.get("fitness_metrics", {}) or {}
    readiness = historical_context.get("readiness", {}) or {}
    physiology = historical_context.get("physiology", {}) or {}
    daily_activity = historical_context.get("daily_activity", {}) or {}
    prev_day_activity = historical_context.get("prev_day_activity", {}) or {}

    # Calculate risk zone from ACWR if not provided
    acwr = fitness_metrics.get("acwr", 1.0)
    if acwr < 0.8:
        risk_zone = "undertrained"
    elif acwr <= 1.3:
        risk_zone = "optimal"
    elif acwr <= 1.5:
        risk_zone = "caution"
    else:
        risk_zone = "danger"

    return {
        "ctl": fitness_metrics.get("ctl", 0.0),
        "atl": fitness_metrics.get("atl", 0.0),
        "tsb": fitness_metrics.get("tsb", 0.0),
        "acwr": acwr,
        "risk_zone": fitness_metrics.get("risk_zone", risk_zone),
        "readiness_score": readiness.get("score", 50.0),
        "readiness_zone": readiness.get("zone", "yellow"),
        "max_hr": physiology.get("max_hr", 185),
        "rest_hr": physiology.get("rest_hr", 55),
        "threshold_hr": physiology.get("lthr", 165),
        # Daily activity (7-day averages)
        "avg_daily_steps": daily_activity.get("avg_steps"),
        "avg_active_minutes": daily_activity.get("avg_active_minutes"),
        # Previous day activity (day before workout)
        "prev_day_steps": prev_day_activity.get("steps"),
        "prev_day_active_minutes": prev_day_activity.get("active_minutes"),
        "prev_day_date": prev_day_activity.get("date"),
        # Flag to indicate historical context was used
        "context_date": historical_context.get("date"),
        "is_historical": True,
    }


# ============================================================================
# API Routes
# ============================================================================

@router.post("/workout/{workout_id}", response_model=AnalysisResponse)
@limiter.limit(RATE_LIMIT_AI)
async def analyze_workout(
    request: Request,
    workout_id: str,
    analysis_request: Optional[AnalysisRequest] = None,
    stream: bool = Query(default=False, description="Stream the response"),
    include_details: bool = Query(default=True, description="Include detailed time-series analysis (HR dynamics, pace patterns, etc.)"),
    current_user: CurrentUser = Depends(require_quota("workout_analysis")),
    coach_service=Depends(get_coach_service),
    training_db=Depends(get_training_db),
):
    """
    Analyze a workout with AI-powered insights.

    Uses the AnalysisAgent (LangGraph) to provide detailed analysis including:
    - Execution summary
    - What went well
    - Areas for improvement
    - How it fits into training

    IMPORTANT: The analysis uses HISTORICAL athlete context (CTL/ATL/TSB) from
    the workout date, not current values. This ensures accurate context when
    analyzing workouts from days or weeks ago.

    The analysis is contextualized with the athlete's:
    - Historical fitness (CTL/ATL/TSB AS OF workout date)
    - HR zones and training paces
    - Race goals
    - Recent training history (before the workout)

    Args:
        workout_id: The ID of the workout to analyze
        request: Optional analysis request with options
        stream: Whether to stream the response (for raw text)

    Returns:
        AnalysisResponse with the analysis result
    """
    logger.info(f"[analyze_workout] Starting analysis for workout_id={workout_id}")

    # Get user_id for usage tracking
    user_id = current_user.id

    try:
        # Check DB first (unless force_refresh)
        force_refresh = analysis_request.force_refresh if analysis_request else False
        if not force_refresh and not stream:
            existing = get_analysis(training_db, workout_id)
            if existing:
                return AnalysisResponse(
                    success=True,
                    analysis=existing,
                    cached=True,
                )

        # =========================================================================
        # CONSENT CHECK: Verify user has consented to LLM data sharing
        # (Only checked when we need to generate new analysis via LLM)
        # =========================================================================
        consent_service = get_consent_service_dep()
        if not consent_service.check_llm_consent(user_id):
            raise HTTPException(
                status_code=403,
                detail="LLM data sharing consent required. Please accept the data sharing agreement to use AI features."
            )

        # Initialize agent after consent check
        agent = get_analysis_agent(user_id=user_id)

        # Get workout data from activity metrics
        workout = training_db.get_activity_metrics(workout_id)
        if not workout:
            raise HTTPException(status_code=404, detail=f"Workout {workout_id} not found")

        workout_dict = workout.to_dict()

        # Extract the workout date for historical context
        workout_date = workout_dict.get("date")
        if not workout_date:
            # Fallback to today if no date available
            workout_date = date.today().isoformat()
            logger.warning(f"[analyze_workout] No date found for workout {workout_id}, using today")

        logger.info(f"[analyze_workout] Using historical context for workout date: {workout_date}")

        # Get HISTORICAL athlete context (CTL/ATL/TSB as of the workout date)
        # This is critical for accurate analysis - we need the fitness state
        # that existed WHEN the workout was performed, not today's values
        historical_context = coach_service.get_historical_athlete_context(workout_date)

        # Build context for agent from historical data
        athlete_context = _build_athlete_context_from_historical(historical_context)

        # Add additional context from profile and goals
        profile = training_db.get_user_profile()
        if profile:
            athlete_context["max_hr"] = getattr(profile, "max_hr", 185)
            athlete_context["rest_hr"] = getattr(profile, "rest_hr", 55)
            athlete_context["threshold_hr"] = getattr(profile, "threshold_hr", 165)

        goals = training_db.get_race_goals()
        if goals:
            first_goal = goals[0]
            athlete_context["race_goal"] = first_goal.get("distance")
            athlete_context["race_date"] = first_goal.get("race_date")
            athlete_context["target_time"] = first_goal.get("target_time_formatted")

        # Get similar workouts for comparison (from before the workout date)
        include_similar = analysis_request.include_similar if analysis_request else True
        similar_workouts = []
        if include_similar:
            # Get activities from before the workout for fair comparison
            from datetime import datetime as dt
            if isinstance(workout_date, str):
                workout_date_obj = dt.strptime(workout_date, "%Y-%m-%d").date()
            else:
                workout_date_obj = workout_date
            recent = coach_service.get_recent_activities(days=14, end_date=workout_date_obj)
            similar_workouts = get_similar_workouts(recent, workout_dict, limit=3)

        if stream:
            # Streaming response (raw LLM output)
            # Note: streaming uses athlete_context which now contains historical data
            return await _stream_analysis(
                workout_dict,
                athlete_context,
                similar_workouts,
                historical_context,
                training_db,
                user_id=user_id,
            )

        # Fetch detailed time-series data if requested
        time_series = None
        splits = None

        if include_details:
            try:
                # Import the details fetching function
                from .workouts import _fetch_garmin_activity_details

                details = await _fetch_garmin_activity_details(workout_id)
                if details:
                    # Extract time_series as dict for the agent
                    time_series = {
                        "heart_rate": [{"timestamp": p.timestamp, "hr": p.hr} for p in details.time_series.heart_rate],
                        "pace_or_speed": [{"timestamp": p.timestamp, "value": p.value} for p in details.time_series.pace_or_speed],
                        "elevation": [{"timestamp": p.timestamp, "elevation": p.elevation} for p in details.time_series.elevation],
                        "cadence": [{"timestamp": p.timestamp, "cadence": p.cadence} for p in details.time_series.cadence],
                    }
                    # Extract splits as list of dicts
                    splits = [
                        {
                            "split_number": s.split_number,
                            "distance_m": s.distance_m,
                            "duration_sec": s.duration_sec,
                            "pace": s.avg_pace_sec_km,
                            "avg_hr": s.avg_hr,
                            "max_hr": s.max_hr,
                            "elevation_gain": s.elevation_gain_m,
                            "elevation_loss": s.elevation_loss_m,
                        }
                        for s in details.splits
                    ]
            except Exception as detail_error:
                # Log but don't fail - detailed data is optional enhancement
                import logging
                logging.getLogger(__name__).warning(
                    f"Could not fetch detailed data for {workout_id}: {detail_error}"
                )

        # Use the agent for structured analysis
        analysis = await agent.analyze(
            workout_data=workout_dict,
            athlete_context=athlete_context,
            similar_workouts=similar_workouts,
            time_series=time_series,
            splits=splits,
        )

        # Save to database
        save_analysis(training_db, workout_id, analysis)

        return AnalysisResponse(
            success=True,
            analysis=analysis,
            cached=False,
        )

    except HTTPException as http_exc:
        logger.warning(f"[analyze_workout] HTTPException for workout_id={workout_id}: {http_exc.status_code} - {http_exc.detail}")
        raise
    except Exception as e:
        logger.error(f"[analyze_workout] Exception for workout_id={workout_id}: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"[analyze_workout] Traceback: {traceback.format_exc()}")
        return AnalysisResponse(
            success=False,
            analysis=None,
            error=f"Failed to analyze workout: {str(e)}",
            cached=False,
        )


async def _stream_analysis(
    workout_dict: dict,
    athlete_context: dict,
    similar_workouts: list,
    historical_context: dict,
    training_db: TrainingDatabase,
    user_id: Optional[str] = None,
):
    """Stream analysis response from LLM.

    Uses historical context for accurate analysis of past workouts.
    Persists the analysis to database after streaming completes.
    """
    from ...models.analysis import (
        calculate_training_effect,
        calculate_load_score,
        calculate_recovery_hours,
        calculate_overall_score,
    )

    # Build prompts for streaming using HISTORICAL context
    # This ensures streaming analysis also uses the correct historical metrics
    context_prompt = build_athlete_context_prompt(
        fitness_metrics=historical_context.get("fitness_metrics"),
        profile=training_db.get_user_profile(),
        goals=training_db.get_race_goals(),
        readiness=historical_context.get("readiness"),
    )

    system_prompt = WORKOUT_ANALYSIS_SYSTEM.format(
        athlete_context=context_prompt,
    )

    similar_text = "\n".join([
        f"- {w.get('date')}: {w.get('activity_type')} "
        f"{w.get('distance_km', 0):.1f}km in {w.get('duration_min', 0):.0f}min"
        for w in similar_workouts
    ]) if similar_workouts else "No recent similar workouts"

    user_prompt = WORKOUT_ANALYSIS_USER.format(
        workout_data=format_workout_for_prompt(workout_dict),
        similar_workouts=similar_text,
    )

    llm = get_llm_client()

    import json as json_lib

    # Pre-calculate scores from workout data
    max_hr = athlete_context.get("max_hr", 185)
    rest_hr = athlete_context.get("rest_hr", 55)

    training_effect = calculate_training_effect(
        duration_min=workout_dict.get("duration_min", 0) or 0,
        avg_hr=workout_dict.get("avg_hr"),
        max_hr=max_hr,
        rest_hr=rest_hr,
        zone3_pct=workout_dict.get("zone3_pct", 0) or 0,
        zone4_pct=workout_dict.get("zone4_pct", 0) or 0,
        zone5_pct=workout_dict.get("zone5_pct", 0) or 0,
    )

    load_score = calculate_load_score(
        hrss=workout_dict.get("hrss"),
        trimp=workout_dict.get("trimp"),
        duration_min=workout_dict.get("duration_min", 0) or 0,
        avg_hr=workout_dict.get("avg_hr"),
        max_hr=max_hr,
    )

    recovery_hours = calculate_recovery_hours(
        training_effect=training_effect,
        load_score=load_score,
    )

    # Derive execution rating from training effect
    if training_effect >= 3.5:
        execution_rating = "excellent"
    elif training_effect >= 2.5:
        execution_rating = "good"
    elif training_effect >= 1.5:
        execution_rating = "fair"
    else:
        execution_rating = "needs_improvement"

    overall_score = calculate_overall_score(
        execution_rating=execution_rating,
        training_effect=training_effect,
        load_score=load_score,
    )

    async def generate():
        full_content = ""
        workout_id = workout_dict.get("activity_id", "")
        async for chunk in llm.stream_completion(
            system=system_prompt,
            user=user_prompt,
            model=ModelType.SMART,
            user_id=user_id,
            analysis_type="workout_analysis",
            entity_type="workout",
            entity_id=workout_id,
        ):
            full_content += chunk
            # Send SSE format that frontend expects
            yield f"data: {json_lib.dumps({'type': 'content', 'content': chunk})}\n\n"

        # Send done event with analysis including scores
        workout_id = workout_dict.get("activity_id", "")
        generated_at = datetime.now()
        analysis = {
            "id": workout_id,
            "workoutId": workout_id,
            "summary": full_content,
            "whatWentWell": [],
            "improvements": [],
            "trainingContext": "",
            "sections": [],
            "executionRating": execution_rating,
            "overallScore": overall_score,
            "trainingEffectScore": training_effect,
            "loadScore": load_score,
            "recoveryHours": recovery_hours,
            "generatedAt": generated_at.isoformat(),
            "modelUsed": "gpt-5-mini",
        }

        # Save to database
        if workout_id:
            try:
                from ...models.analysis import WorkoutAnalysisResult, AnalysisStatus
                import uuid
                analysis_result = WorkoutAnalysisResult(
                    workout_id=workout_id,
                    analysis_id=f"stream_{uuid.uuid4().hex[:8]}",
                    status=AnalysisStatus.COMPLETED,
                    summary=full_content,
                    what_worked_well=[],
                    observations=[],
                    training_context="",
                    execution_rating=execution_rating,
                    overall_score=overall_score,
                    training_effect_score=training_effect,
                    load_score=load_score,
                    recovery_hours=recovery_hours,
                    generated_at=generated_at,
                    model_used="gpt-5-mini",
                )
                save_analysis(training_db, workout_id, analysis_result)
            except Exception as e:
                logger.error(f"Failed to save streaming analysis for {workout_id}: {e}")

        yield f"data: {json_lib.dumps({'type': 'done', 'analysis': analysis})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable proxy buffering
        },
    )


@router.get("/workout/{workout_id}", response_model=AnalysisResponse)
async def get_existing_analysis(
    workout_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    training_db=Depends(get_training_db),
):
    """
    Get existing analysis for a workout.

    Returns the analysis if available, otherwise indicates it needs
    to be generated using the POST endpoint.

    Args:
        workout_id: The ID of the workout

    Returns:
        AnalysisResponse with analysis or indication that none exists
    """
    existing = get_analysis(training_db, workout_id)

    if existing:
        return AnalysisResponse(
            success=True,
            analysis=existing,
            cached=True,
        )

    return AnalysisResponse(
        success=False,
        analysis=None,
        error="No cached analysis available. Use POST to generate analysis.",
        cached=False,
    )


@router.get("/recent", response_model=RecentWorkoutsResponse)
async def get_recent_with_analysis(
    limit: int = Query(default=10, ge=1, le=50, description="Number of workouts to return"),
    include_summaries: bool = Query(default=True, description="Include AI summaries"),
    current_user: CurrentUser = Depends(get_current_user),
    coach_service=Depends(get_coach_service),
    training_db=Depends(get_training_db),
):
    """
    Get recent workouts with quick AI summaries.

    Uses GPT-5-nano for fast, cost-effective summaries.

    Args:
        limit: Number of workouts to return (1-50)
        include_summaries: Whether to include AI summaries

    Returns:
        RecentWorkoutsResponse with workouts and their summaries
    """
    user_id = current_user.id

    try:
        # Get recent activities
        activities = coach_service.get_recent_activities(days=30)[:limit]

        if not activities:
            return RecentWorkoutsResponse(workouts=[], count=0)

        workouts = []

        if include_summaries:
            # =========================================================================
            # CONSENT CHECK: Verify user has consented to LLM data sharing
            # (Only checked when generating AI summaries)
            # =========================================================================
            consent_service = get_consent_service_dep()
            if not consent_service.check_llm_consent(user_id):
                raise HTTPException(
                    status_code=403,
                    detail="LLM data sharing consent required. Please accept the data sharing agreement to use AI features."
                )
            # Get athlete context once
            briefing = coach_service.get_daily_briefing(date.today())
            athlete_context = build_athlete_context_prompt(
                fitness_metrics=briefing.get("training_status"),
                profile=training_db.get_user_profile(),
                goals=training_db.get_race_goals(),
            )

            llm = get_llm_client()

            # Generate summaries concurrently
            async def get_summary(activity: dict) -> str:
                try:
                    # Check if we have an existing full analysis
                    workout_id = activity.get("activity_id")
                    existing = get_analysis(training_db, workout_id)
                    if existing and existing.summary:
                        return existing.summary

                    # Generate quick summary
                    system_prompt = QUICK_SUMMARY_SYSTEM.format(
                        athlete_context=athlete_context
                    )
                    user_prompt = QUICK_SUMMARY_USER.format(
                        workout_data=format_workout_for_prompt(activity)
                    )

                    return await llm.completion(
                        system=system_prompt,
                        user=user_prompt,
                        model=ModelType.FAST,
                        max_tokens=100,
                    )
                except Exception:
                    return "Summary pending..."

            # Run summary generation concurrently
            summaries = await asyncio.gather(*[
                get_summary(a) for a in activities
            ])

            for activity, summary in zip(activities, summaries):
                workout_id = activity.get("activity_id")
                existing = get_analysis(training_db, workout_id)

                workouts.append(RecentWorkoutWithAnalysis(
                    workout_id=workout_id,
                    date=activity.get("date", ""),
                    activity_type=activity.get("activity_type", "running"),
                    duration_min=activity.get("duration_min", 0.0) or 0.0,
                    distance_km=activity.get("distance_km"),
                    avg_hr=activity.get("avg_hr"),
                    hrss=activity.get("hrss"),
                    ai_summary=summary,
                    execution_rating=existing.execution_rating if existing else None,
                    has_full_analysis=existing is not None,
                ))
        else:
            # Just return workout data without summaries
            for activity in activities:
                workout_id = activity.get("activity_id")
                existing = get_analysis(training_db, workout_id)

                workouts.append(RecentWorkoutWithAnalysis(
                    workout_id=workout_id,
                    date=activity.get("date", ""),
                    activity_type=activity.get("activity_type", "running"),
                    duration_min=activity.get("duration_min", 0.0) or 0.0,
                    distance_km=activity.get("distance_km"),
                    avg_hr=activity.get("avg_hr"),
                    hrss=activity.get("hrss"),
                    ai_summary=None,
                    execution_rating=existing.execution_rating if existing else None,
                    has_full_analysis=existing is not None,
                ))

        return RecentWorkoutsResponse(
            workouts=workouts,
            count=len(workouts),
        )

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to get recent workouts: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get recent workouts. Please try again later."
        )


# NOTE: batch_analyze is internal-only, not exposed via public API
# Use for background jobs or admin tasks only
async def batch_analyze_internal(
    request: BatchAnalysisRequest,
    user_id: str,
    coach_service,
    training_db,
):
    """
    Batch analyze multiple workouts (internal use only).

    Efficient for analyzing a week or training block.
    Skips already-analyzed workouts unless force_refresh is set.

    IMPORTANT: Each workout is analyzed with its HISTORICAL context (CTL/ATL/TSB)
    from the workout date, not today's values. This ensures accurate analysis
    even when batch-processing workouts from different dates.

    Args:
        request: BatchAnalysisRequest with list of workout IDs

    Returns:
        BatchAnalysisResponse with all analysis results
    """
    import logging
    from datetime import datetime as dt

    logger = logging.getLogger(__name__)

    # =========================================================================
    # CONSENT CHECK: Verify user has consented to LLM data sharing
    # =========================================================================
    consent_service = get_consent_service_dep()
    if not consent_service.check_llm_consent(user_id):
        raise HTTPException(
            status_code=403,
            detail="LLM data sharing consent required. Please accept the data sharing agreement to use AI features."
        )

    # user_id passed directly for internal use
    agent = get_analysis_agent(user_id=user_id)

    try:
        results = []
        cached_count = 0

        # Get profile info once (this doesn't change per workout)
        profile = training_db.get_user_profile()

        # Process each workout with its OWN historical context
        for workout_id in request.workout_ids:
            try:
                # Check if already analyzed
                if not request.force_refresh:
                    existing = get_analysis(training_db, workout_id)
                    if existing:
                        results.append(AnalysisResponse(
                            success=True,
                            analysis=existing,
                            cached=True,
                        ))
                        cached_count += 1
                        continue

                # Get workout data
                workout = training_db.get_activity_metrics(workout_id)
                if not workout:
                    results.append(AnalysisResponse(
                        success=False,
                        analysis=None,
                        error=f"Workout {workout_id} not found",
                    ))
                    continue

                workout_dict = workout.to_dict()

                # Extract workout date for HISTORICAL context
                workout_date = workout_dict.get("date")
                if not workout_date:
                    workout_date = date.today().isoformat()
                    logger.warning(f"[batch_analyze] No date for workout {workout_id}, using today")

                # Get HISTORICAL context for THIS specific workout's date
                # This is critical: each workout needs context from when it was performed
                historical_context = coach_service.get_historical_athlete_context(workout_date)
                athlete_context = _build_athlete_context_from_historical(historical_context)

                # Add profile info
                if profile:
                    athlete_context["max_hr"] = getattr(profile, "max_hr", 185)
                    athlete_context["rest_hr"] = getattr(profile, "rest_hr", 55)
                    athlete_context["threshold_hr"] = getattr(profile, "threshold_hr", 165)

                # Get similar workouts from BEFORE the workout date
                if isinstance(workout_date, str):
                    workout_date_obj = dt.strptime(workout_date, "%Y-%m-%d").date()
                else:
                    workout_date_obj = workout_date
                recent = coach_service.get_recent_activities(days=14, end_date=workout_date_obj)
                similar_workouts = get_similar_workouts(recent, workout_dict, limit=3)

                # Analyze with historical context
                analysis = await agent.analyze(
                    workout_data=workout_dict,
                    athlete_context=athlete_context,
                    similar_workouts=similar_workouts,
                )

                # Save to database
                save_analysis(training_db, workout_id, analysis)

                results.append(AnalysisResponse(
                    success=True,
                    analysis=analysis,
                    cached=False,
                ))

            except Exception as e:
                results.append(AnalysisResponse(
                    success=False,
                    analysis=None,
                    error=str(e),
                ))

        success_count = sum(1 for r in results if r.success)
        failed_count = len(results) - success_count

        return BatchAnalysisResponse(
            analyses=results,
            total_count=len(request.workout_ids),
            success_count=success_count,
            cached_count=cached_count,
            failed_count=failed_count,
        )

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed batch analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed batch analysis. Please try again later."
        )


@router.delete("/workout/{workout_id}/analysis")
async def delete_workout_analysis(
    workout_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    training_db=Depends(get_training_db),
):
    """
    Delete analysis for a workout.

    Args:
        workout_id: The ID of the workout

    Returns:
        Success status
    """
    removed = delete_analysis(training_db, workout_id)
    return {
        "workout_id": workout_id,
        "removed": removed,
    }
