"""Workout analysis API routes."""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..deps import get_coach_service, get_training_db
from ...llm.providers import get_llm_client, ModelType
from ...llm.context_builder import build_athlete_context_prompt
from ...llm.prompts import WORKOUT_ANALYSIS_SYSTEM, WORKOUT_ANALYSIS_USER


router = APIRouter()


class WorkoutAnalysisResponse(BaseModel):
    """Response from workout analysis."""
    workout_id: str
    summary: str
    what_worked: str
    observations: str
    recommendations: str
    context_used: dict
    model_used: str


class BatchAnalysisRequest(BaseModel):
    """Request for batch analysis."""
    workout_ids: list[str]


@router.post("/workout/{workout_id}")
async def analyze_workout(
    workout_id: str,
    stream: bool = False,
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
):
    """
    Analyze a workout with AI-powered insights.

    Uses GPT-5-mini to provide detailed analysis including:
    - Execution summary
    - What went well
    - Areas for improvement
    - How it fits into training

    The analysis is contextualized with the athlete's:
    - Current fitness (CTL/ATL/TSB)
    - HR zones and training paces
    - Race goals
    - Recent training history
    """
    try:
        # Get workout data
        workout = training_db.get_activity(workout_id)
        if not workout:
            raise HTTPException(status_code=404, detail=f"Workout {workout_id} not found")

        workout_dict = workout.to_dict()

        # Get athlete context
        briefing = coach_service.get_daily_briefing(date.today())

        # Build context for LLM
        athlete_context = build_athlete_context_prompt(
            fitness_metrics=briefing.get("training_status"),
            profile=training_db.get_user_profile(),
            goals=training_db.get_race_goals(),
            readiness=briefing.get("readiness"),
        )

        # Get recent activities for comparison
        recent = coach_service.get_recent_activities(days=14)
        similar_workouts = [
            a for a in recent
            if a.get("activity_type") == workout_dict.get("activity_type")
            and a.get("activity_id") != workout_id
        ][:3]  # Last 3 similar workouts

        # Build prompt
        system_prompt = WORKOUT_ANALYSIS_SYSTEM.format(
            athlete_context=athlete_context,
        )

        user_prompt = WORKOUT_ANALYSIS_USER.format(
            workout_data=str(workout_dict),
            similar_workouts=str(similar_workouts) if similar_workouts else "No recent similar workouts",
        )

        # Get LLM client
        llm = get_llm_client()

        if stream:
            # Streaming response
            async def generate():
                async for chunk in llm.stream_completion(
                    system=system_prompt,
                    user=user_prompt,
                    model=ModelType.SMART,  # GPT-5-mini for complex analysis
                ):
                    yield chunk

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
            )
        else:
            # Regular response
            response = await llm.completion(
                system=system_prompt,
                user=user_prompt,
                model=ModelType.SMART,
            )

            return {
                "workout_id": workout_id,
                "analysis": response,
                "context_used": {
                    "ctl": briefing.get("training_status", {}).get("ctl"),
                    "tsb": briefing.get("training_status", {}).get("tsb"),
                    "readiness": briefing.get("readiness", {}).get("score"),
                },
                "model_used": "gpt-5-mini",
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze workout: {str(e)}")


@router.get("/recent")
async def get_recent_with_analysis(
    limit: int = 10,
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
):
    """
    Get recent workouts with quick AI summaries.

    Uses GPT-5-nano for fast, cost-effective summaries.
    """
    try:
        # Get recent activities
        activities = coach_service.get_recent_activities(days=30)[:limit]

        if not activities:
            return {"workouts": [], "count": 0}

        # Get athlete context once
        briefing = coach_service.get_daily_briefing(date.today())
        athlete_context = build_athlete_context_prompt(
            fitness_metrics=briefing.get("training_status"),
            profile=training_db.get_user_profile(),
            goals=training_db.get_race_goals(),
        )

        # Get LLM for quick summaries
        llm = get_llm_client()

        workouts_with_summaries = []
        for activity in activities:
            # Quick summary using nano model
            summary_prompt = f"""
            Provide a 1-2 sentence summary of this workout:
            {activity}

            Focus on the key achievement or notable aspect.
            """

            try:
                summary = await llm.completion(
                    system=f"You are a running coach. Athlete context: {athlete_context}",
                    user=summary_prompt,
                    model=ModelType.FAST,  # GPT-5-nano
                    max_tokens=100,
                )
            except Exception:
                summary = "Analysis pending..."

            workouts_with_summaries.append({
                **activity,
                "ai_summary": summary,
            })

        return {
            "workouts": workouts_with_summaries,
            "count": len(workouts_with_summaries),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent workouts: {str(e)}")


@router.post("/batch")
async def batch_analyze(
    request: BatchAnalysisRequest,
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
):
    """
    Batch analyze multiple workouts.

    Efficient for analyzing a week or training block.
    """
    try:
        results = []

        for workout_id in request.workout_ids:
            try:
                # Reuse the single workout analysis
                result = await analyze_workout(
                    workout_id=workout_id,
                    stream=False,
                    coach_service=coach_service,
                    training_db=training_db,
                )
                results.append(result)
            except HTTPException as e:
                results.append({
                    "workout_id": workout_id,
                    "error": str(e.detail),
                })

        return {
            "analyses": results,
            "count": len(results),
            "success_count": len([r for r in results if "error" not in r]),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed batch analysis: {str(e)}")
