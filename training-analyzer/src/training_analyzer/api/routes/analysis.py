"""Workout analysis API routes."""

import asyncio
from datetime import date, datetime
from typing import Dict, Optional
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..deps import get_coach_service, get_training_db
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


# ============================================================================
# In-Memory Cache
# ============================================================================

class AnalysisCache:
    """Simple in-memory cache for workout analyses."""

    def __init__(self, max_size: int = 100):
        self._cache: Dict[str, WorkoutAnalysisResult] = {}
        self._max_size = max_size

    def get(self, workout_id: str) -> Optional[WorkoutAnalysisResult]:
        """Get cached analysis for a workout."""
        return self._cache.get(workout_id)

    def set(self, workout_id: str, analysis: WorkoutAnalysisResult) -> None:
        """Cache an analysis result."""
        # Simple LRU: remove oldest if at capacity
        if len(self._cache) >= self._max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        analysis.cached_at = datetime.utcnow()
        self._cache[workout_id] = analysis

    def invalidate(self, workout_id: str) -> bool:
        """Remove a workout from cache."""
        if workout_id in self._cache:
            del self._cache[workout_id]
            return True
        return False

    def clear(self) -> None:
        """Clear all cached analyses."""
        self._cache.clear()


# Singleton cache instance
_analysis_cache = AnalysisCache()


def get_analysis_cache() -> AnalysisCache:
    """Get the analysis cache singleton."""
    return _analysis_cache


# Singleton agent instance
_analysis_agent: Optional[AnalysisAgent] = None


def get_analysis_agent() -> AnalysisAgent:
    """Get the analysis agent singleton."""
    global _analysis_agent
    if _analysis_agent is None:
        _analysis_agent = AnalysisAgent()
    return _analysis_agent


# ============================================================================
# API Routes
# ============================================================================

@router.post("/workout/{workout_id}", response_model=AnalysisResponse)
async def analyze_workout(
    workout_id: str,
    request: Optional[AnalysisRequest] = None,
    stream: bool = Query(default=False, description="Stream the response"),
    coach_service=Depends(get_coach_service),
    training_db=Depends(get_training_db),
    cache: AnalysisCache = Depends(get_analysis_cache),
    agent: AnalysisAgent = Depends(get_analysis_agent),
):
    """
    Analyze a workout with AI-powered insights.

    Uses the AnalysisAgent (LangGraph) to provide detailed analysis including:
    - Execution summary
    - What went well
    - Areas for improvement
    - How it fits into training

    The analysis is contextualized with the athlete's:
    - Current fitness (CTL/ATL/TSB)
    - HR zones and training paces
    - Race goals
    - Recent training history

    Args:
        workout_id: The ID of the workout to analyze
        request: Optional analysis request with options
        stream: Whether to stream the response (for raw text)

    Returns:
        AnalysisResponse with the analysis result
    """
    try:
        # Check cache first (unless force_refresh)
        force_refresh = request.force_refresh if request else False
        if not force_refresh and not stream:
            cached = cache.get(workout_id)
            if cached:
                return AnalysisResponse(
                    success=True,
                    analysis=cached,
                    cached=True,
                )

        # Get workout data
        workout = training_db.get_activity(workout_id)
        if not workout:
            raise HTTPException(status_code=404, detail=f"Workout {workout_id} not found")

        workout_dict = workout.to_dict()

        # Get athlete context
        briefing = coach_service.get_daily_briefing(date.today())

        # Build context for agent
        athlete_context = build_athlete_context_from_briefing(briefing)

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

        # Get similar workouts for comparison
        include_similar = request.include_similar if request else True
        similar_workouts = []
        if include_similar:
            recent = coach_service.get_recent_activities(days=14)
            similar_workouts = get_similar_workouts(recent, workout_dict, limit=3)

        if stream:
            # Streaming response (raw LLM output)
            return await _stream_analysis(
                workout_dict,
                athlete_context,
                similar_workouts,
                briefing,
                training_db,
            )

        # Use the agent for structured analysis
        analysis = await agent.analyze(
            workout_data=workout_dict,
            athlete_context=athlete_context,
            similar_workouts=similar_workouts,
        )

        # Cache the result
        cache.set(workout_id, analysis)

        return AnalysisResponse(
            success=True,
            analysis=analysis,
            cached=False,
        )

    except HTTPException:
        raise
    except Exception as e:
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
    briefing: dict,
    training_db,
):
    """Stream analysis response from LLM."""
    # Build prompts for streaming
    context_prompt = build_athlete_context_prompt(
        fitness_metrics=briefing.get("training_status"),
        profile=training_db.get_user_profile(),
        goals=training_db.get_race_goals(),
        readiness=briefing.get("readiness"),
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

    async def generate():
        async for chunk in llm.stream_completion(
            system=system_prompt,
            user=user_prompt,
            model=ModelType.SMART,
        ):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )


@router.get("/workout/{workout_id}", response_model=AnalysisResponse)
async def get_cached_analysis(
    workout_id: str,
    cache: AnalysisCache = Depends(get_analysis_cache),
):
    """
    Get cached analysis for a workout.

    Returns the cached analysis if available, otherwise indicates it needs
    to be generated using the POST endpoint.

    Args:
        workout_id: The ID of the workout

    Returns:
        AnalysisResponse with cached analysis or indication that none exists
    """
    cached = cache.get(workout_id)

    if cached:
        return AnalysisResponse(
            success=True,
            analysis=cached,
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
    coach_service=Depends(get_coach_service),
    training_db=Depends(get_training_db),
    cache: AnalysisCache = Depends(get_analysis_cache),
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
    try:
        # Get recent activities
        activities = coach_service.get_recent_activities(days=30)[:limit]

        if not activities:
            return RecentWorkoutsResponse(workouts=[], count=0)

        workouts = []

        if include_summaries:
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
                    # Check if we have a cached full analysis
                    workout_id = activity.get("activity_id")
                    cached = cache.get(workout_id)
                    if cached and cached.summary:
                        return cached.summary

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
                cached = cache.get(workout_id)

                workouts.append(RecentWorkoutWithAnalysis(
                    workout_id=workout_id,
                    date=activity.get("date", ""),
                    activity_type=activity.get("activity_type", "running"),
                    duration_min=activity.get("duration_min", 0.0) or 0.0,
                    distance_km=activity.get("distance_km"),
                    avg_hr=activity.get("avg_hr"),
                    hrss=activity.get("hrss"),
                    ai_summary=summary,
                    execution_rating=cached.execution_rating if cached else None,
                    has_full_analysis=cached is not None,
                ))
        else:
            # Just return workout data without summaries
            for activity in activities:
                workout_id = activity.get("activity_id")
                cached = cache.get(workout_id)

                workouts.append(RecentWorkoutWithAnalysis(
                    workout_id=workout_id,
                    date=activity.get("date", ""),
                    activity_type=activity.get("activity_type", "running"),
                    duration_min=activity.get("duration_min", 0.0) or 0.0,
                    distance_km=activity.get("distance_km"),
                    avg_hr=activity.get("avg_hr"),
                    hrss=activity.get("hrss"),
                    ai_summary=None,
                    execution_rating=cached.execution_rating if cached else None,
                    has_full_analysis=cached is not None,
                ))

        return RecentWorkoutsResponse(
            workouts=workouts,
            count=len(workouts),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recent workouts: {str(e)}"
        )


@router.post("/batch", response_model=BatchAnalysisResponse)
async def batch_analyze(
    request: BatchAnalysisRequest,
    coach_service=Depends(get_coach_service),
    training_db=Depends(get_training_db),
    cache: AnalysisCache = Depends(get_analysis_cache),
    agent: AnalysisAgent = Depends(get_analysis_agent),
):
    """
    Batch analyze multiple workouts.

    Efficient for analyzing a week or training block.
    Uses caching to avoid re-analyzing already processed workouts.

    Args:
        request: BatchAnalysisRequest with list of workout IDs

    Returns:
        BatchAnalysisResponse with all analysis results
    """
    try:
        results = []
        cached_count = 0

        # Get context once for all workouts
        briefing = coach_service.get_daily_briefing(date.today())
        athlete_context = build_athlete_context_from_briefing(briefing)

        # Add profile info
        profile = training_db.get_user_profile()
        if profile:
            athlete_context["max_hr"] = getattr(profile, "max_hr", 185)
            athlete_context["rest_hr"] = getattr(profile, "rest_hr", 55)
            athlete_context["threshold_hr"] = getattr(profile, "threshold_hr", 165)

        # Process each workout
        for workout_id in request.workout_ids:
            try:
                # Check cache first
                if not request.force_refresh:
                    cached = cache.get(workout_id)
                    if cached:
                        results.append(AnalysisResponse(
                            success=True,
                            analysis=cached,
                            cached=True,
                        ))
                        cached_count += 1
                        continue

                # Get workout data
                workout = training_db.get_activity(workout_id)
                if not workout:
                    results.append(AnalysisResponse(
                        success=False,
                        analysis=None,
                        error=f"Workout {workout_id} not found",
                    ))
                    continue

                workout_dict = workout.to_dict()

                # Get similar workouts
                recent = coach_service.get_recent_activities(days=14)
                similar_workouts = get_similar_workouts(recent, workout_dict, limit=3)

                # Analyze
                analysis = await agent.analyze(
                    workout_data=workout_dict,
                    athlete_context=athlete_context,
                    similar_workouts=similar_workouts,
                )

                # Cache the result
                cache.set(workout_id, analysis)

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
        raise HTTPException(
            status_code=500,
            detail=f"Failed batch analysis: {str(e)}"
        )


@router.delete("/cache/{workout_id}")
async def invalidate_cache(
    workout_id: str,
    cache: AnalysisCache = Depends(get_analysis_cache),
):
    """
    Invalidate cached analysis for a workout.

    Args:
        workout_id: The ID of the workout to invalidate

    Returns:
        Success status
    """
    removed = cache.invalidate(workout_id)
    return {
        "workout_id": workout_id,
        "removed": removed,
    }


@router.delete("/cache")
async def clear_cache(
    cache: AnalysisCache = Depends(get_analysis_cache),
):
    """
    Clear all cached analyses.

    Returns:
        Success status
    """
    cache.clear()
    return {"status": "cache cleared"}
