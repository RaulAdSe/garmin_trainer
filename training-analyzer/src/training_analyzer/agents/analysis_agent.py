"""
Workout Analysis Agent using LangGraph.

This agent analyzes workout data with AI, providing structured feedback
that is contextualized with the athlete's current training state.
"""

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END

from ..llm.providers import get_llm_client, ModelType
from ..llm.prompts import (
    WORKOUT_ANALYSIS_SYSTEM,
    WORKOUT_ANALYSIS_USER,
    WORKOUT_ANALYSIS_PARSER_SYSTEM,
    WORKOUT_ANALYSIS_PARSER_USER,
)
from ..models.analysis import (
    AnalysisContext,
    AnalysisStatus,
    AthleteContext,
    WorkoutAnalysisResult,
    WorkoutData,
    WorkoutExecutionRating,
    WorkoutInsight,
)


# ============================================================================
# State Definition
# ============================================================================

class AnalysisState(TypedDict):
    """State for the analysis workflow."""
    # Input
    workout_data: Dict[str, Any]
    athlete_context: Dict[str, Any]
    similar_workouts: List[Dict[str, Any]]

    # Processing state
    analysis_id: str
    status: str
    error: Optional[str]

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

    def __init__(self, llm_client=None):
        """
        Initialize the analysis agent.

        Args:
            llm_client: Optional LLM client (uses default if not provided)
        """
        self._llm_client = llm_client
        self._graph = self._build_graph()

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
                race_goal=ctx_data.get("race_goal"),
                race_date=ctx_data.get("race_date"),
                target_time=ctx_data.get("target_time"),
                readiness_score=ctx_data.get("readiness_score", 50.0),
                readiness_zone=ctx_data.get("readiness_zone", "yellow"),
                training_paces=ctx_data.get("training_paces", {}),
            )

            # Create WorkoutData from dict
            workout = WorkoutData.from_dict(state.get("workout_data", {}))

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
        """Generate analysis using LLM."""
        try:
            # Build prompts
            system_prompt = WORKOUT_ANALYSIS_SYSTEM.format(
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

            user_prompt = WORKOUT_ANALYSIS_USER.format(
                workout_data=state.get("formatted_workout", "No workout data"),
                similar_workouts=similar_text,
            )

            # Get completion
            response = await self.llm_client.completion(
                system=system_prompt,
                user=user_prompt,
                model=ModelType.SMART,
                max_tokens=1500,
                temperature=0.7,
            )

            return {
                **state,
                "raw_analysis": response,
                "status": "generated",
            }

        except Exception as e:
            return {
                **state,
                "error": f"Failed to generate analysis: {str(e)}",
                "status": "failed",
            }

    async def _parse_response(self, state: AnalysisState) -> Dict[str, Any]:
        """Parse LLM response into structured format."""
        try:
            raw_response = state.get("raw_analysis", "")

            # Try to parse the structured response
            parsed = self._extract_sections(raw_response)

            # If parsing failed, use LLM to help parse
            if not parsed.get("summary"):
                parsed = await self._llm_assisted_parse(raw_response)

            return {
                **state,
                "parsed_analysis": parsed,
                "status": "parsed",
            }

        except Exception as e:
            # If parsing fails, try to extract what we can
            return {
                **state,
                "parsed_analysis": {
                    "summary": state.get("raw_analysis", "")[:500],
                    "what_worked_well": [],
                    "observations": [],
                    "recommendations": [],
                },
                "status": "parsed_with_fallback",
            }

    def _extract_sections(self, text: str) -> Dict[str, Any]:
        """Extract structured sections from LLM response."""
        result = {
            "summary": "",
            "what_worked_well": [],
            "observations": [],
            "recommendations": [],
            "execution_rating": None,
            "training_fit": "",
        }

        # Extract summary
        summary_match = re.search(
            r"\*\*Summary\*\*:?\s*(.+?)(?=\n\n|\*\*|$)",
            text,
            re.DOTALL | re.IGNORECASE
        )
        if summary_match:
            result["summary"] = summary_match.group(1).strip()

        # Extract what worked well
        worked_match = re.search(
            r"\*\*What Worked Well\*\*:?\s*(.+?)(?=\*\*|$)",
            text,
            re.DOTALL | re.IGNORECASE
        )
        if worked_match:
            items = self._extract_list_items(worked_match.group(1))
            result["what_worked_well"] = items

        # Extract observations
        obs_match = re.search(
            r"\*\*Observations?\*\*:?\s*(.+?)(?=\*\*|$)",
            text,
            re.DOTALL | re.IGNORECASE
        )
        if obs_match:
            items = self._extract_list_items(obs_match.group(1))
            result["observations"] = items

        # Extract recommendations
        rec_match = re.search(
            r"\*\*Recommendations?\*\*:?\s*(.+?)(?=\*\*|$)",
            text,
            re.DOTALL | re.IGNORECASE
        )
        if rec_match:
            items = self._extract_list_items(rec_match.group(1))
            result["recommendations"] = items

        # Try to infer execution rating from text
        text_lower = text.lower()
        if any(word in text_lower for word in ["excellent", "outstanding", "perfect"]):
            result["execution_rating"] = "excellent"
        elif any(word in text_lower for word in ["good", "solid", "well done", "well executed"]):
            result["execution_rating"] = "good"
        elif any(word in text_lower for word in ["fair", "adequate", "ok"]):
            result["execution_rating"] = "fair"
        elif any(word in text_lower for word in ["needs improvement", "concern", "struggling"]):
            result["execution_rating"] = "needs_improvement"

        return result

    def _extract_list_items(self, text: str) -> List[str]:
        """Extract bullet points or list items from text."""
        items = []

        # Match various list formats
        patterns = [
            r"^[-*]\s*(.+)$",  # Markdown bullets
            r"^\d+\.\s*(.+)$",  # Numbered list
            r"^[>•]\s*(.+)$",  # Other bullets
        ]

        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            matched = False
            for pattern in patterns:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    items.append(match.group(1).strip())
                    matched = True
                    break

            # If no pattern matched but line has content, try to use it
            if not matched and line and not line.startswith("**"):
                items.append(line)

        return items[:5]  # Limit to 5 items

    async def _llm_assisted_parse(self, raw_response: str) -> Dict[str, Any]:
        """Use LLM to help parse a poorly formatted response."""
        try:
            system_prompt = WORKOUT_ANALYSIS_PARSER_SYSTEM
            user_prompt = WORKOUT_ANALYSIS_PARSER_USER.format(
                raw_response=raw_response
            )

            response = await self.llm_client.completion(
                system=system_prompt,
                user=user_prompt,
                model=ModelType.FAST,
                max_tokens=800,
                temperature=0.2,
            )

            # Try to parse JSON from response
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            # Fallback
            return {
                "summary": raw_response[:500],
                "what_worked_well": [],
                "observations": [],
                "recommendations": [],
            }

        except Exception:
            return {
                "summary": raw_response[:500],
                "what_worked_well": [],
                "observations": [],
                "recommendations": [],
            }

    async def _build_result(self, state: AnalysisState) -> Dict[str, Any]:
        """Build the final WorkoutAnalysisResult."""
        try:
            parsed = state.get("parsed_analysis", {})
            workout = state.get("workout_data", {})
            ctx = state.get("athlete_context", {})

            # Determine execution rating
            execution_rating = None
            if parsed.get("execution_rating"):
                try:
                    execution_rating = WorkoutExecutionRating(parsed["execution_rating"])
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

            # Build insights from observations
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

            result = WorkoutAnalysisResult(
                workout_id=workout.get("activity_id", "unknown"),
                analysis_id=state.get("analysis_id", str(uuid.uuid4())),
                status=AnalysisStatus.COMPLETED,
                summary=parsed.get("summary", ""),
                what_worked_well=parsed.get("what_worked_well", []),
                observations=parsed.get("observations", []),
                recommendations=parsed.get("recommendations", []),
                insights=insights,
                execution_rating=execution_rating,
                training_fit=parsed.get("training_fit"),
                context=analysis_context,
                model_used="gpt-5-mini",
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
            model_used="gpt-5-mini",
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
    ) -> WorkoutAnalysisResult:
        """
        Analyze a workout.

        Args:
            workout_data: Dictionary with workout metrics
            athlete_context: Dictionary with athlete context (CTL, TSB, goals, etc.)
            similar_workouts: Optional list of similar workouts for comparison

        Returns:
            WorkoutAnalysisResult with the analysis
        """
        # Initialize state
        initial_state: AnalysisState = {
            "workout_data": workout_data,
            "athlete_context": athlete_context,
            "similar_workouts": similar_workouts or [],
            "analysis_id": str(uuid.uuid4()),
            "status": "initialized",
            "error": None,
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

    return {
        "ctl": training_status.get("ctl", 0.0),
        "atl": training_status.get("atl", 0.0),
        "tsb": training_status.get("tsb", 0.0),
        "acwr": training_status.get("acwr", 1.0),
        "risk_zone": training_status.get("risk_zone", "unknown"),
        "readiness_score": readiness.get("score", 50.0),
        "readiness_zone": readiness.get("zone", "yellow"),
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
