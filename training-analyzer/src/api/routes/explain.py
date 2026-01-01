"""
Explanation API Routes

Provides transparency endpoints that show the mathematical reasoning
and data behind every recommendation, differentiating from "black box" competitors.
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import get_coach_service, get_training_db
from ...recommendations.readiness import calculate_explained_readiness
from ...recommendations.workout import recommend_explained_workout


router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================

class DataSourceResponse(BaseModel):
    """Data source information."""
    source_type: str
    source_name: str
    last_updated: Optional[str] = None
    confidence: float


class ExplanationFactorResponse(BaseModel):
    """A single contributing factor to a recommendation."""
    name: str
    value: Any
    display_value: str
    impact: str  # "positive", "negative", "neutral"
    weight: float
    contribution_points: float
    explanation: str
    threshold: Optional[str] = None
    baseline: Optional[Any] = None
    data_sources: List[DataSourceResponse] = Field(default_factory=list)


class ExplainedRecommendationResponse(BaseModel):
    """Recommendation with full transparency."""
    recommendation: str
    confidence: float
    confidence_explanation: str
    factors: List[ExplanationFactorResponse]
    data_points: Dict[str, Any]
    calculation_summary: str
    alternatives_considered: List[str]
    key_driver: Optional[str] = None


class ExplainedReadinessResponse(BaseModel):
    """Complete explained readiness assessment."""
    date: str
    overall_score: float
    zone: str
    recommendation: ExplainedRecommendationResponse
    factor_breakdown: List[ExplanationFactorResponse]
    score_calculation: str
    comparison_to_baseline: Optional[str] = None
    trend: Optional[str] = None


class ExplainedWorkoutResponse(BaseModel):
    """Workout recommendation with full explanation."""
    workout_type: str
    duration_min: int
    intensity_description: str
    hr_zone_target: Optional[str]
    recommendation: ExplainedRecommendationResponse
    decision_tree: List[str]
    readiness_influence: float
    load_influence: float
    pattern_influence: float


class SessionExplanationResponse(BaseModel):
    """Explanation for a specific training plan session."""
    session_id: str
    session_name: str
    session_type: str
    scheduled_date: str
    rationale: ExplainedRecommendationResponse
    periodization_context: str
    weekly_context: str
    progression_note: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/readiness", response_model=ExplainedReadinessResponse)
async def get_explained_readiness(
    target_date: Optional[str] = Query(None, description="Date for assessment (YYYY-MM-DD)"),
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
):
    """
    Get explained readiness breakdown.

    Shows exactly how the readiness score was calculated, including:
    - Each factor's contribution (HRV, sleep, Body Battery, etc.)
    - The weight applied to each factor
    - The raw data used in calculations
    - Human-readable explanations for each component

    This transparency allows users to understand exactly why they received
    a particular readiness score and recommendation.
    """
    try:
        # Parse date
        if target_date:
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            parsed_date = date.today()

        # Get the daily briefing data
        briefing = coach_service.get_daily_briefing(parsed_date)

        # Extract wellness and fitness data
        wellness_data = briefing.get("wellness", {})
        training_status = briefing.get("training_status", {})

        # Build fitness metrics dict
        fitness_metrics = {
            "tsb": training_status.get("tsb"),
            "acwr": training_status.get("acwr"),
            "ctl": training_status.get("ctl"),
            "atl": training_status.get("atl"),
        }

        # Get recent activities
        recent_activities = briefing.get("recent_activities", [])

        # Calculate explained readiness
        explained = calculate_explained_readiness(
            wellness_data=wellness_data,
            fitness_metrics=fitness_metrics,
            recent_activities=recent_activities,
            target_date=parsed_date,
        )

        # Convert to response format
        return ExplainedReadinessResponse(
            date=explained.date,
            overall_score=explained.overall_score,
            zone=explained.zone,
            recommendation=_to_recommendation_response(explained.recommendation),
            factor_breakdown=[_to_factor_response(f) for f in explained.factor_breakdown],
            score_calculation=explained.score_calculation,
            comparison_to_baseline=explained.comparison_to_baseline,
            trend=explained.trend,
        )

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to get explained readiness: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get explained readiness. Please try again later."
        )


@router.get("/workout-recommendation", response_model=ExplainedWorkoutResponse)
async def get_explained_workout_recommendation(
    target_date: Optional[str] = Query(None, description="Date for recommendation (YYYY-MM-DD)"),
    coach_service = Depends(get_coach_service),
    training_db = Depends(get_training_db),
):
    """
    Get explained workout recommendation.

    Shows the complete decision tree that led to the workout recommendation:
    - Each rule that was evaluated
    - How readiness, training load, and patterns influenced the decision
    - The exact data values used
    - Why alternatives were not chosen

    This transparency helps users understand the logic behind every
    workout suggestion.
    """
    try:
        # Parse date
        if target_date:
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            parsed_date = date.today()

        # Get the daily briefing data
        briefing = coach_service.get_daily_briefing(parsed_date)

        # Extract readiness score
        readiness_data = briefing.get("readiness", {})
        readiness_score = readiness_data.get("score", 50)

        # Extract training status
        training_status = briefing.get("training_status", {})
        acwr = training_status.get("acwr", 1.0) or 1.0
        tsb = training_status.get("tsb", 0) or 0

        # Calculate days since hard/long workouts
        recent_activities = briefing.get("recent_activities", [])
        days_since_hard = _calculate_days_since_hard(recent_activities, parsed_date)
        days_since_long = _calculate_days_since_long(recent_activities, parsed_date)

        # Get weekly load info
        weekly_load = briefing.get("weekly_load", {})
        weekly_load_so_far = weekly_load.get("current", 0) or 0
        target_weekly_load = weekly_load.get("target", 300) or 300

        # Check if race week
        is_race_week = briefing.get("is_race_week", False)

        # Get day of week
        day_of_week = parsed_date.weekday()

        # Calculate explained workout recommendation
        explained = recommend_explained_workout(
            readiness_score=readiness_score,
            acwr=acwr,
            tsb=tsb,
            days_since_hard=days_since_hard,
            days_since_long=days_since_long,
            weekly_load_so_far=weekly_load_so_far,
            target_weekly_load=target_weekly_load,
            is_race_week=is_race_week,
            day_of_week=day_of_week,
        )

        # Convert to response format
        return ExplainedWorkoutResponse(
            workout_type=explained.workout_type,
            duration_min=explained.duration_min,
            intensity_description=explained.intensity_description,
            hr_zone_target=explained.hr_zone_target,
            recommendation=_to_recommendation_response(explained.recommendation),
            decision_tree=explained.decision_tree,
            readiness_influence=explained.readiness_influence,
            load_influence=explained.load_influence,
            pattern_influence=explained.pattern_influence,
        )

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to get explained workout recommendation: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get explained workout recommendation. Please try again later."
        )


@router.get("/plan-session/{session_id}", response_model=SessionExplanationResponse)
async def get_explained_plan_session(
    session_id: str,
    training_db = Depends(get_training_db),
):
    """
    Explain why a specific training plan session was scheduled.

    Shows:
    - The periodization context (what phase, what week)
    - Why this type of session was chosen for this day
    - How it fits into the weekly structure
    - Progression from previous similar sessions

    This helps users understand the thought process behind each
    planned workout in their training plan.
    """
    try:
        # Get the session from the database
        session = training_db.get_planned_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Get the plan for context
        plan = training_db.get_plan_by_session(session_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found for session")

        # Build the explanation
        week_number = session.get("week_number", 1)
        phase = session.get("phase", "base")
        session_type = session.get("session_type", "easy")
        day_of_week = session.get("day_of_week", 0)

        # Get week context
        week_sessions = training_db.get_week_sessions(plan.get("id"), week_number)
        hard_sessions_this_week = sum(
            1 for s in week_sessions
            if s.get("session_type") in ["interval", "tempo", "threshold", "long_run"]
        )

        # Determine weekly context
        session_index = sum(
            1 for s in week_sessions
            if s.get("session_type") == session_type
            and s.get("day_of_week", 0) < day_of_week
        ) + 1

        weekly_context = f"Session {session_index} of {session_type} workouts this week"
        if hard_sessions_this_week > 0:
            weekly_context += f" ({hard_sessions_this_week} quality sessions planned)"

        # Build periodization context
        total_weeks = plan.get("total_weeks", 12)
        periodization_context = f"Week {week_number} of {total_weeks} - {phase.title()} Phase"

        # Check for progression
        previous_similar = training_db.get_previous_similar_session(
            plan.get("id"), session_type, week_number
        )
        progression_note = None
        if previous_similar:
            prev_load = previous_similar.get("target_load", 0)
            curr_load = session.get("target_load", 0)
            if prev_load > 0 and curr_load > 0:
                pct_change = ((curr_load - prev_load) / prev_load) * 100
                if abs(pct_change) > 5:
                    progression_note = f"{pct_change:+.0f}% load from previous {session_type} session"

        # Build the rationale
        factors = [
            _build_session_factor("Periodization Phase", phase, _get_phase_explanation(phase)),
            _build_session_factor("Week Number", week_number, f"Week {week_number} of {total_weeks} in plan"),
            _build_session_factor("Day of Week", day_of_week, _get_day_explanation(day_of_week, session_type)),
        ]

        rationale = ExplainedRecommendationResponse(
            recommendation=f"{session_type.replace('_', ' ').title()} session as part of {phase} phase training",
            confidence=0.90,
            confidence_explanation="Plan-based recommendation with full training context",
            factors=factors,
            data_points={
                "session_id": session_id,
                "week_number": week_number,
                "phase": phase,
                "session_type": session_type,
            },
            calculation_summary=f"Scheduled based on {phase} phase periodization, day {day_of_week} placement, and weekly load distribution",
            alternatives_considered=[],
            key_driver="Periodization Plan",
        )

        return SessionExplanationResponse(
            session_id=session_id,
            session_name=session.get("name", session_type.title()),
            session_type=session_type,
            scheduled_date=session.get("date", ""),
            rationale=rationale,
            periodization_context=periodization_context,
            weekly_context=weekly_context,
            progression_note=progression_note,
        )

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to explain session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to explain session. Please try again later."
        )


# ============================================================================
# Helper Functions
# ============================================================================

def _to_recommendation_response(rec) -> ExplainedRecommendationResponse:
    """Convert ExplainedRecommendation to response model."""
    return ExplainedRecommendationResponse(
        recommendation=rec.recommendation,
        confidence=rec.confidence,
        confidence_explanation=rec.confidence_explanation,
        factors=[_to_factor_response(f) for f in rec.factors],
        data_points=rec.data_points,
        calculation_summary=rec.calculation_summary,
        alternatives_considered=rec.alternatives_considered,
        key_driver=rec.key_driver,
    )


def _to_factor_response(factor) -> ExplanationFactorResponse:
    """Convert ExplanationFactor to response model."""
    return ExplanationFactorResponse(
        name=factor.name,
        value=factor.value,
        display_value=factor.display_value,
        impact=factor.impact.value if hasattr(factor.impact, 'value') else str(factor.impact),
        weight=factor.weight,
        contribution_points=factor.contribution_points,
        explanation=factor.explanation,
        threshold=factor.threshold,
        baseline=factor.baseline,
        data_sources=[
            DataSourceResponse(
                source_type=ds.source_type.value if hasattr(ds.source_type, 'value') else str(ds.source_type),
                source_name=ds.source_name,
                last_updated=ds.last_updated,
                confidence=ds.confidence,
            )
            for ds in factor.data_sources
        ],
    )


def _calculate_days_since_hard(activities: list, target_date: date) -> int:
    """Calculate days since last hard workout."""
    if not activities:
        return 3

    hard_threshold_hrss = 75.0
    last_hard = None

    for activity in activities:
        activity_date_str = activity.get("date")
        if not activity_date_str:
            continue

        try:
            if isinstance(activity_date_str, str):
                activity_date = datetime.strptime(activity_date_str, "%Y-%m-%d").date()
            else:
                activity_date = activity_date_str
        except (ValueError, TypeError):
            continue

        hrss = activity.get("hrss", 0) or 0
        if hrss >= hard_threshold_hrss:
            if last_hard is None or activity_date > last_hard:
                last_hard = activity_date

    if last_hard is None:
        return 3

    return max(0, (target_date - last_hard).days)


def _calculate_days_since_long(activities: list, target_date: date) -> int:
    """Calculate days since last long workout."""
    if not activities:
        return 7

    long_threshold_duration = 75 * 60  # 75 minutes in seconds
    last_long = None

    for activity in activities:
        activity_date_str = activity.get("date")
        if not activity_date_str:
            continue

        try:
            if isinstance(activity_date_str, str):
                activity_date = datetime.strptime(activity_date_str, "%Y-%m-%d").date()
            else:
                activity_date = activity_date_str
        except (ValueError, TypeError):
            continue

        duration = activity.get("duration", 0) or 0
        if duration >= long_threshold_duration:
            if last_long is None or activity_date > last_long:
                last_long = activity_date

    if last_long is None:
        return 7

    return max(0, (target_date - last_long).days)


def _build_session_factor(name: str, value: Any, explanation: str) -> ExplanationFactorResponse:
    """Build a simple explanation factor for session."""
    return ExplanationFactorResponse(
        name=name,
        value=value,
        display_value=str(value),
        impact="neutral",
        weight=0.33,
        contribution_points=33,
        explanation=explanation,
        threshold=None,
        baseline=None,
        data_sources=[
            DataSourceResponse(
                source_type="training_plan",
                source_name="Training Plan",
                confidence=1.0,
            )
        ],
    )


def _get_phase_explanation(phase: str) -> str:
    """Get explanation for training phase."""
    explanations = {
        "base": "Building aerobic foundation with mostly easy running and gradually increasing volume.",
        "build": "Introducing harder workouts while maintaining base. Focus on tempo and threshold work.",
        "peak": "Race-specific intensity with reduced volume. Quality over quantity.",
        "taper": "Reduced training to arrive fresh at race day. Maintain intensity, cut volume.",
        "recovery": "Active recovery phase. Low intensity and volume to allow adaptation.",
    }
    return explanations.get(phase, "Training phase determining workout distribution.")


def _get_day_explanation(day: int, session_type: str) -> str:
    """Get explanation for day placement."""
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_name = day_names[day] if 0 <= day < 7 else f"Day {day}"

    if session_type in ["long_run"]:
        return f"{day_name} scheduled for long run - typical weekend placement for time availability."
    elif session_type in ["interval", "tempo", "threshold"]:
        return f"{day_name} quality session - placed mid-week with recovery days before and after."
    elif session_type in ["rest"]:
        return f"{day_name} rest day - strategically placed after hard effort or before quality session."
    else:
        return f"{day_name} {session_type} session."
