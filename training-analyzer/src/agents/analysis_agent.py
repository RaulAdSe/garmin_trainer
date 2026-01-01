"""
Workout Analysis Agent using LangGraph.

This agent analyzes workout data with AI, providing structured feedback
that is contextualized with the athlete's current training state.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END

from ..llm.providers import get_llm_client, ModelType
from ..llm.prompts import (
    WORKOUT_ANALYSIS_SYSTEM_JSON,
    WORKOUT_ANALYSIS_USER_JSON,
)
from ..models.analysis import (
    AnalysisContext,
    AnalysisStatus,
    AthleteContext,
    CategorizedInsight,
    InsightCategory,
    ScoreCard,
    WorkoutAnalysisResult,
    WorkoutData,
    WorkoutExecutionRating,
    WorkoutInsight,
    # Score calculation functions
    calculate_training_effect,
    calculate_load_score,
    calculate_recovery_hours,
    calculate_overall_score,
    build_default_score_cards,
)
from ..analysis.condensation import condense_workout_data


# ============================================================================
# State Definition
# ============================================================================

class AnalysisState(TypedDict):
    """State for the analysis workflow."""
    # Input
    workout_data: Dict[str, Any]
    athlete_context: Dict[str, Any]
    similar_workouts: List[Dict[str, Any]]

    # Optional detailed data for condensation
    time_series: Optional[Dict[str, Any]]  # {heart_rate, pace_or_speed, elevation, cadence}
    splits: Optional[List[Dict[str, Any]]]  # Per-km split data

    # Processing state
    analysis_id: str
    status: str
    error: Optional[str]

    # Formatted prompts (set by prepare_context)
    formatted_context: Optional[str]
    formatted_workout: Optional[str]

    # LLM outputs
    raw_analysis: Optional[str]
    parsed_analysis: Optional[Dict[str, Any]]

    # Final result
    result: Optional[Dict[str, Any]]


# ============================================================================
# Analysis Agent
# ============================================================================

class AnalysisAgent:
    """
    LangGraph-based workout analysis agent.

    This agent:
    1. Builds context from athlete data
    2. Generates analysis using GPT
    3. Parses the response into structured format
    4. Returns a WorkoutAnalysisResult
    """

    def __init__(self, llm_client=None, user_id: Optional[str] = None):
        """
        Initialize the analysis agent.

        Args:
            llm_client: Optional LLM client (uses default if not provided)
            user_id: Optional user ID for usage tracking and billing
        """
        self._llm_client = llm_client
        self._user_id = user_id
        self._graph = self._build_graph()

    @property
    def user_id(self) -> Optional[str]:
        """Get the user ID for usage tracking."""
        return self._user_id

    @user_id.setter
    def user_id(self, value: Optional[str]) -> None:
        """Set the user ID for usage tracking."""
        self._user_id = value

    @property
    def llm_client(self):
        """Lazy-load LLM client."""
        if self._llm_client is None:
            self._llm_client = get_llm_client()
        return self._llm_client

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        # Create the graph
        workflow = StateGraph(AnalysisState)

        # Add nodes
        workflow.add_node("prepare_context", self._prepare_context)
        workflow.add_node("generate_analysis", self._generate_analysis)
        workflow.add_node("parse_response", self._parse_response)
        workflow.add_node("build_result", self._build_result)
        workflow.add_node("handle_error", self._handle_error)

        # Add edges
        workflow.set_entry_point("prepare_context")
        workflow.add_edge("prepare_context", "generate_analysis")
        workflow.add_conditional_edges(
            "generate_analysis",
            self._check_generation_success,
            {
                "success": "parse_response",
                "error": "handle_error",
            }
        )
        workflow.add_conditional_edges(
            "parse_response",
            self._check_parse_success,
            {
                "success": "build_result",
                "error": "handle_error",
            }
        )
        workflow.add_edge("build_result", END)
        workflow.add_edge("handle_error", END)

        return workflow.compile()

    def _check_generation_success(self, state: AnalysisState) -> str:
        """Check if analysis generation succeeded."""
        return "error" if state.get("error") else "success"

    def _check_parse_success(self, state: AnalysisState) -> str:
        """Check if response parsing succeeded."""
        return "error" if state.get("error") else "success"

    async def _prepare_context(self, state: AnalysisState) -> Dict[str, Any]:
        """Prepare context for analysis."""
        try:
            # Create AthleteContext from dict
            ctx_data = state.get("athlete_context", {})
            athlete_ctx = AthleteContext(
                ctl=ctx_data.get("ctl", 0.0),
                atl=ctx_data.get("atl", 0.0),
                tsb=ctx_data.get("tsb", 0.0),
                acwr=ctx_data.get("acwr", 1.0),
                risk_zone=ctx_data.get("risk_zone", "unknown"),
                max_hr=ctx_data.get("max_hr", 185),
                rest_hr=ctx_data.get("rest_hr", 55),
                threshold_hr=ctx_data.get("threshold_hr", 165),
                vdot=ctx_data.get("vdot"),
                # VO2max and fitness level
                vo2max_running=ctx_data.get("vo2max_running"),
                vo2max_cycling=ctx_data.get("vo2max_cycling"),
                training_status=ctx_data.get("training_status"),
                # Race predictions
                race_prediction_5k=ctx_data.get("race_prediction_5k"),
                race_prediction_10k=ctx_data.get("race_prediction_10k"),
                race_prediction_half=ctx_data.get("race_prediction_half"),
                race_prediction_marathon=ctx_data.get("race_prediction_marathon"),
                # Daily activity (7-day averages)
                avg_daily_steps=ctx_data.get("avg_daily_steps"),
                avg_active_minutes=ctx_data.get("avg_active_minutes"),
                # Previous day activity (day before workout)
                prev_day_steps=ctx_data.get("prev_day_steps"),
                prev_day_active_minutes=ctx_data.get("prev_day_active_minutes"),
                prev_day_date=ctx_data.get("prev_day_date"),
                # Goals
                race_goal=ctx_data.get("race_goal"),
                race_date=ctx_data.get("race_date"),
                target_time=ctx_data.get("target_time"),
                readiness_score=ctx_data.get("readiness_score", 50.0),
                readiness_zone=ctx_data.get("readiness_zone", "yellow"),
                training_paces=ctx_data.get("training_paces", {}),
            )

            # Create WorkoutData from dict
            workout_data = state.get("workout_data", {})
            workout = WorkoutData.from_dict(workout_data)

            # Condense time-series data if available
            time_series = state.get("time_series")
            splits = state.get("splits")

            if time_series or splits:
                # Get HR zones for zone transition detection
                hr_zones = athlete_ctx.hr_zones

                # Condense the detailed data
                condensed = condense_workout_data(
                    time_series=time_series,
                    splits=splits,
                    hr_zones=hr_zones,
                    duration_sec=int((workout_data.get("duration_min") or 0) * 60),
                    distance_km=workout_data.get("distance_km") or 0.0,
                    activity_type=workout_data.get("activity_type"),
                )

                # Attach condensed data to workout
                workout.condensed_data = condensed

            # Store formatted context in state
            return {
                **state,
                "formatted_context": athlete_ctx.to_prompt_context(),
                "formatted_workout": workout.to_prompt_data(),
                "status": "preparing",
            }

        except Exception as e:
            return {
                **state,
                "error": f"Failed to prepare context: {str(e)}",
                "status": "failed",
            }

    async def _generate_analysis(self, state: AnalysisState) -> Dict[str, Any]:
        """Generate analysis using LLM with JSON mode."""
        try:
            # Build prompts
            system_prompt = WORKOUT_ANALYSIS_SYSTEM_JSON.format(
                athlete_context=state.get("formatted_context", "No context available"),
            )

            # Format similar workouts
            similar = state.get("similar_workouts", [])
            if similar:
                similar_text = "\n".join([
                    f"- {w.get('date')}: {w.get('activity_type')} "
                    f"{w.get('distance_km', 0):.1f}km in {w.get('duration_min', 0):.0f}min, "
                    f"HR {w.get('avg_hr', 'N/A')} bpm"
                    for w in similar[:3]
                ])
            else:
                similar_text = "No similar recent workouts available for comparison"

            user_prompt = WORKOUT_ANALYSIS_USER_JSON.format(
                workout_data=state.get("formatted_workout", "No workout data"),
                similar_workouts=similar_text,
            )

            # Get JSON completion using JSON mode
            workout_id = state.get("workout_data", {}).get("activity_id")
            parsed_response = await self.llm_client.completion_json(
                system=system_prompt,
                user=user_prompt,
                model=ModelType.SMART,
                max_tokens=4000,
                temperature=0.7,
                user_id=self._user_id,
                analysis_type="workout_analysis",
                entity_type="workout",
                entity_id=workout_id,
            )

            return {
                **state,
                "raw_analysis": json.dumps(parsed_response),
                "parsed_analysis": parsed_response,
                "status": "generated",
            }

        except Exception as e:
            return {
                **state,
                "error": f"Failed to generate analysis: {str(e)}",
                "status": "failed",
            }

    async def _parse_response(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Parse LLM response into structured format.

        Since we use JSON mode in _generate_analysis, the parsed_analysis
        is already available. This method validates the structure and
        parses the new score and insight fields.
        """
        try:
            # parsed_analysis is already set by _generate_analysis when using JSON mode
            parsed = state.get("parsed_analysis", {})

            # Ensure all required fields have defaults (backward compatible)
            validated = {
                "summary": parsed.get("summary", ""),
                "what_worked_well": parsed.get("what_worked_well", []),
                "observations": parsed.get("observations", []),
                "recommendations": parsed.get("recommendations", []),
                "execution_rating": parsed.get("execution_rating"),
                "training_fit": parsed.get("training_fit", ""),
            }

            # Parse new score fields from LLM response
            validated["overall_score"] = parsed.get("overall_score")
            validated["training_effect_score"] = parsed.get("training_effect_score")
            validated["recovery_hours"] = parsed.get("recovery_hours")

            # Parse categorized insights
            raw_insights = parsed.get("categorized_insights", [])
            categorized_insights = []
            for insight in raw_insights:
                if isinstance(insight, dict):
                    try:
                        # Map category string to enum
                        category_str = insight.get("category", "recommendation")
                        category = InsightCategory(category_str) if category_str in [e.value for e in InsightCategory] else InsightCategory.RECOMMENDATION

                        categorized_insights.append({
                            "category": category.value,
                            "icon": insight.get("icon", ""),
                            "text": insight.get("text", ""),
                            "detail": insight.get("detail", ""),
                        })
                    except (ValueError, KeyError):
                        continue

            validated["categorized_insights"] = categorized_insights

            # Store score reasoning for potential use
            validated["score_reasoning"] = parsed.get("score_reasoning", {})

            return {
                **state,
                "parsed_analysis": validated,
                "status": "parsed",
            }

        except Exception as e:
            # If validation fails, return empty structure
            return {
                **state,
                "parsed_analysis": {
                    "summary": "",
                    "what_worked_well": [],
                    "observations": [],
                    "recommendations": [],
                    "categorized_insights": [],
                },
                "status": "parsed_with_fallback",
            }

    async def _build_result(self, state: AnalysisState) -> Dict[str, Any]:
        """Build the final WorkoutAnalysisResult."""
        try:
            parsed = state.get("parsed_analysis", {})
            workout = state.get("workout_data", {})
            ctx = state.get("athlete_context", {})

            # Determine execution rating
            execution_rating = None
            execution_rating_str = None
            if parsed.get("execution_rating"):
                try:
                    execution_rating = WorkoutExecutionRating(parsed["execution_rating"])
                    execution_rating_str = parsed["execution_rating"]
                except ValueError:
                    pass

            # Build context object
            analysis_context = AnalysisContext(
                ctl=ctx.get("ctl"),
                atl=ctx.get("atl"),
                tsb=ctx.get("tsb"),
                acwr=ctx.get("acwr"),
                readiness_score=ctx.get("readiness_score"),
                readiness_zone=ctx.get("readiness_zone"),
                similar_workouts_count=len(state.get("similar_workouts", [])),
            )

            # Build insights from observations (legacy format)
            insights = []
            for obs in parsed.get("what_worked_well", []):
                insights.append(WorkoutInsight(
                    category="execution",
                    observation=obs,
                    is_positive=True,
                    importance="medium",
                ))
            for obs in parsed.get("observations", []):
                insights.append(WorkoutInsight(
                    category="observation",
                    observation=obs,
                    is_positive=False,
                    importance="medium",
                ))

            # ================================================================
            # Calculate scores with LLM values as primary, fallback to calculated
            # ================================================================

            # Get athlete physiology for calculations
            max_hr = ctx.get("max_hr", 185)
            rest_hr = ctx.get("rest_hr", 55)

            # Calculate training effect (use LLM value if provided, else calculate)
            llm_training_effect = parsed.get("training_effect_score")
            if llm_training_effect is not None:
                training_effect_score = float(llm_training_effect)
            else:
                training_effect_score = calculate_training_effect(
                    duration_min=workout.get("duration_min", 0) or 0,
                    avg_hr=workout.get("avg_hr"),
                    max_hr=max_hr,
                    rest_hr=rest_hr,
                    zone3_pct=workout.get("zone3_pct", 0) or 0,
                    zone4_pct=workout.get("zone4_pct", 0) or 0,
                    zone5_pct=workout.get("zone5_pct", 0) or 0,
                )

            # Calculate load score from HRSS/TRIMP (always calculated from data)
            load_score = calculate_load_score(
                hrss=workout.get("hrss"),
                trimp=workout.get("trimp"),
                tss=workout.get("tss"),
                duration_min=workout.get("duration_min", 0) or 0,
                avg_hr=workout.get("avg_hr"),
                max_hr=max_hr,
            )

            # Calculate recovery hours (use LLM value if provided, else calculate)
            llm_recovery_hours = parsed.get("recovery_hours")
            if llm_recovery_hours is not None:
                recovery_hours = int(llm_recovery_hours)
            else:
                recovery_hours = calculate_recovery_hours(
                    training_effect=training_effect_score,
                    load_score=load_score,
                    tsb=ctx.get("tsb"),
                    execution_rating=execution_rating_str,
                )

            # Calculate overall score (use LLM value if provided, else calculate)
            llm_overall_score = parsed.get("overall_score")
            zone2_pct = workout.get("zone2_pct", 0) or 0
            zone3_pct = workout.get("zone3_pct", 0) or 0
            zone_quality = min(1.0, (zone2_pct + zone3_pct) / 80)  # 80% aerobic = 1.0

            if llm_overall_score is not None:
                overall_score = int(llm_overall_score)
            else:
                overall_score = calculate_overall_score(
                    execution_rating=execution_rating_str,
                    training_effect=training_effect_score,
                    load_score=load_score,
                    zone_distribution_quality=zone_quality,
                )

            # Build score cards for visualization
            score_cards = build_default_score_cards(
                workout_data=workout,
                training_effect=training_effect_score,
                load_score=load_score,
                recovery_hours=recovery_hours,
                execution_rating=execution_rating_str,
            )

            # Build categorized insights from LLM response
            categorized_insights = []
            for insight_data in parsed.get("categorized_insights", []):
                try:
                    category = InsightCategory(insight_data.get("category", "recommendation"))
                    categorized_insights.append(CategorizedInsight(
                        category=category,
                        icon=insight_data.get("icon", ""),
                        text=insight_data.get("text", ""),
                        detail=insight_data.get("detail", ""),
                    ))
                except (ValueError, KeyError):
                    continue

            result = WorkoutAnalysisResult(
                workout_id=workout.get("activity_id", "unknown"),
                analysis_id=state.get("analysis_id", str(uuid.uuid4())),
                status=AnalysisStatus.COMPLETED,
                summary=parsed.get("summary", ""),
                what_worked_well=parsed.get("what_worked_well", []),
                observations=parsed.get("observations", []),
                recommendations=parsed.get("recommendations", []),
                insights=insights,
                # New structured scores
                overall_score=overall_score,
                training_effect_score=training_effect_score,
                load_score=load_score,
                recovery_hours=recovery_hours,
                scores=score_cards,
                categorized_insights=categorized_insights,
                # Existing fields
                execution_rating=execution_rating,
                training_fit=parsed.get("training_fit"),
                context=analysis_context,
                model_used=self.llm_client.get_model_name(ModelType.SMART),
                raw_response=state.get("raw_analysis"),
                created_at=datetime.utcnow(),
            )

            return {
                **state,
                "result": result.model_dump(),
                "status": "completed",
            }

        except Exception as e:
            return {
                **state,
                "error": f"Failed to build result: {str(e)}",
                "status": "failed",
            }

    async def _handle_error(self, state: AnalysisState) -> Dict[str, Any]:
        """Handle errors in the workflow."""
        workout = state.get("workout_data", {})

        result = WorkoutAnalysisResult(
            workout_id=workout.get("activity_id", "unknown"),
            analysis_id=state.get("analysis_id", str(uuid.uuid4())),
            status=AnalysisStatus.FAILED,
            summary=f"Analysis failed: {state.get('error', 'Unknown error')}",
            model_used=self.llm_client.get_model_name(ModelType.SMART),
            created_at=datetime.utcnow(),
        )

        return {
            **state,
            "result": result.model_dump(),
            "status": "failed",
        }

    async def analyze(
        self,
        workout_data: Dict[str, Any],
        athlete_context: Dict[str, Any],
        similar_workouts: Optional[List[Dict[str, Any]]] = None,
        time_series: Optional[Dict[str, Any]] = None,
        splits: Optional[List[Dict[str, Any]]] = None,
    ) -> WorkoutAnalysisResult:
        """
        Analyze a workout.

        Args:
            workout_data: Dictionary with workout metrics
            athlete_context: Dictionary with athlete context (CTL, TSB, goals, etc.)
            similar_workouts: Optional list of similar workouts for comparison
            time_series: Optional dict with detailed time-series data
                        {heart_rate: [{timestamp, hr}], pace_or_speed: [...], elevation: [...]}
            splits: Optional list of per-km split data
                   [{pace, avg_hr, elevation_gain, ...}]

        Returns:
            WorkoutAnalysisResult with the analysis
        """
        # Initialize state
        initial_state: AnalysisState = {
            "workout_data": workout_data,
            "athlete_context": athlete_context,
            "similar_workouts": similar_workouts or [],
            "time_series": time_series,
            "splits": splits,
            "analysis_id": str(uuid.uuid4()),
            "status": "initialized",
            "error": None,
            "formatted_context": None,
            "formatted_workout": None,
            "raw_analysis": None,
            "parsed_analysis": None,
            "result": None,
        }

        # Run the graph
        final_state = await self._graph.ainvoke(initial_state)

        # Return the result
        result_dict = final_state.get("result", {})
        return WorkoutAnalysisResult(**result_dict)


# ============================================================================
# Helper Functions
# ============================================================================

def build_athlete_context_from_briefing(briefing: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build athlete context dictionary from a coach service briefing.

    Args:
        briefing: Daily briefing from CoachService

    Returns:
        Dictionary suitable for AnalysisAgent
    """
    training_status = briefing.get("training_status", {}) or {}
    readiness = briefing.get("readiness", {}) or {}
    fitness_level = briefing.get("fitness_level", {}) or {}
    race_predictions = briefing.get("race_predictions", {}) or {}
    daily_activity = briefing.get("daily_activity", {}) or {}
    prev_day_activity = briefing.get("prev_day_activity", {}) or {}

    return {
        "ctl": training_status.get("ctl", 0.0),
        "atl": training_status.get("atl", 0.0),
        "tsb": training_status.get("tsb", 0.0),
        "acwr": training_status.get("acwr", 1.0),
        "risk_zone": training_status.get("risk_zone", "unknown"),
        "readiness_score": readiness.get("score", 50.0),
        "readiness_zone": readiness.get("zone", "yellow"),
        # VO2max and fitness level
        "vo2max_running": fitness_level.get("vo2max_running"),
        "vo2max_cycling": fitness_level.get("vo2max_cycling"),
        "training_status": fitness_level.get("training_status"),
        # Race predictions (in seconds)
        "race_prediction_5k": race_predictions.get("5k"),
        "race_prediction_10k": race_predictions.get("10k"),
        "race_prediction_half": race_predictions.get("half_marathon"),
        "race_prediction_marathon": race_predictions.get("marathon"),
        # Daily activity (7-day averages)
        "avg_daily_steps": daily_activity.get("avg_steps"),
        "avg_active_minutes": daily_activity.get("avg_active_minutes"),
        # Previous day activity (day before workout)
        "prev_day_steps": prev_day_activity.get("steps"),
        "prev_day_active_minutes": prev_day_activity.get("active_minutes"),
        "prev_day_date": prev_day_activity.get("date"),
    }


def get_similar_workouts(
    recent_activities: List[Dict[str, Any]],
    target_workout: Dict[str, Any],
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """
    Find similar workouts from recent activities.

    Args:
        recent_activities: List of recent workout dictionaries
        target_workout: The workout being analyzed
        limit: Maximum number of similar workouts to return

    Returns:
        List of similar workout dictionaries
    """
    target_type = target_workout.get("activity_type", "running")
    target_id = target_workout.get("activity_id")

    similar = [
        a for a in recent_activities
        if a.get("activity_type") == target_type
        and a.get("activity_id") != target_id
    ]

    return similar[:limit]
