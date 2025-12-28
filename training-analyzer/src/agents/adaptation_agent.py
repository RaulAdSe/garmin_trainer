"""
Plan Adaptation Agent using LangGraph for intelligent plan adjustments.

This agent:
- Analyzes detected deviations from the training plan
- Proposes adaptive changes to upcoming sessions
- Uses LLM to generate natural language explanations
- Applies rule-based logic with LLM enhancement
"""

import json
import logging
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END

from ..llm.providers import LLMClient, ModelType, get_llm_client
from ..models.deviation import (
    DeviationType,
    AdaptationAction,
    PlanDeviation,
    AdaptationSuggestion,
    SessionAdjustment,
)
from ..models.plans import (
    TrainingPlan,
    TrainingWeek,
    PlannedSession,
    TrainingPhase,
    WorkoutType,
)


logger = logging.getLogger(__name__)


# ============================================================================
# Prompts for Adaptation
# ============================================================================

ADAPTATION_ANALYSIS_SYSTEM = """You are an expert running coach analyzing training plan deviations and suggesting adaptations.

ATHLETE CONTEXT:
{athlete_context}

ADAPTATION PRINCIPLES:
1. If a workout was HARDER than planned:
   - The athlete may be fatigued; suggest easier next session or recovery
   - Monitor for signs of overreaching
   - Reduce intensity or volume of next quality session

2. If a workout was EASIER than planned:
   - Could be fatigue, motivation, or life circumstances
   - Maintain planned intensity but possibly extend duration slightly
   - Don't overcompensate - trust the plan

3. If a workout was SKIPPED:
   - Don't try to "make up" the session
   - Redistribute key elements (not full load) to upcoming days
   - Consider extending the plan if close to race date
   - Protect quality sessions - skip easy runs before skipping quality

4. If there are EXTRA workouts:
   - Athlete is motivated but watch for overload
   - Reduce planned session durations to compensate
   - Monitor recovery indicators

LOAD MANAGEMENT:
- Weekly load changes should stay within 10% of original plan
- Don't add more than 2 quality sessions per week
- Maintain at least 48 hours between hard efforts
- Recovery is as important as training

OUTPUT FORMAT: JSON
{{
    "analysis": "Brief analysis of the deviation and its impact",
    "recommended_actions": ["action1", "action2"],
    "session_adjustments": [
        {{
            "day_of_week": 0-6,
            "original_type": "workout type",
            "suggested_type": "new workout type",
            "original_duration_min": number,
            "suggested_duration_min": number,
            "original_load": number,
            "suggested_load": number,
            "rationale": "Why this change"
        }}
    ],
    "explanation": "Natural language explanation for the athlete (2-3 sentences)",
    "expected_load_change_pct": number,
    "confidence": 0.0-1.0,
    "monitoring_notes": "What to watch for"
}}
"""

ADAPTATION_ANALYSIS_USER = """Analyze this training deviation and suggest adaptations:

DEVIATION DETAILS:
{deviation}

PLAN CONTEXT:
- Current week: {current_week}
- Current phase: {current_phase}
- Weeks remaining: {weeks_remaining}
- Race date: {race_date}

UPCOMING SESSIONS (next 7 days):
{upcoming_sessions}

RECENT PERFORMANCE:
{recent_performance}

Provide adaptation recommendations as JSON. Focus on practical adjustments that maintain training continuity while respecting the athlete's current state."""


class AdaptationState(TypedDict):
    """State for the adaptation agent workflow."""
    # Input
    plan_id: str
    deviation: Dict[str, Any]
    plan_context: Dict[str, Any]
    upcoming_sessions: List[Dict[str, Any]]
    athlete_context: Dict[str, Any]

    # Processing
    actions: List[str]
    session_adjustments: List[Dict[str, Any]]
    explanation: str

    # Output
    suggestion: Optional[Dict[str, Any]]
    errors: List[str]
    status: str


class AdaptationAgent:
    """
    LangGraph-based agent for adapting training plans based on deviations.

    The agent uses a workflow:
    1. analyze_deviation: Understand the deviation impact
    2. determine_actions: Select appropriate adaptation actions
    3. generate_adjustments: Create specific session changes
    4. generate_explanation: Create athlete-friendly explanation
    5. finalize: Build the AdaptationSuggestion
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize the adaptation agent.

        Args:
            llm_client: LLM client for AI-powered suggestions. If None, uses default.
        """
        self._llm_client = llm_client
        self._graph = self._build_graph()

    @property
    def llm_client(self) -> LLMClient:
        """Get or create the LLM client."""
        if self._llm_client is None:
            self._llm_client = get_llm_client()
        return self._llm_client

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AdaptationState)

        # Add nodes
        workflow.add_node("analyze_deviation", self._analyze_deviation)
        workflow.add_node("determine_actions", self._determine_actions)
        workflow.add_node("generate_adjustments", self._generate_adjustments)
        workflow.add_node("generate_explanation", self._generate_explanation)
        workflow.add_node("finalize", self._finalize)

        # Add edges
        workflow.set_entry_point("analyze_deviation")
        workflow.add_edge("analyze_deviation", "determine_actions")
        workflow.add_edge("determine_actions", "generate_adjustments")
        workflow.add_edge("generate_adjustments", "generate_explanation")
        workflow.add_edge("generate_explanation", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def suggest_adaptation(
        self,
        plan: TrainingPlan,
        deviation: PlanDeviation,
        athlete_context: Optional[Dict[str, Any]] = None,
        recent_performance: Optional[Dict[str, Any]] = None,
    ) -> AdaptationSuggestion:
        """
        Generate an adaptation suggestion for a detected deviation.

        Args:
            plan: The training plan
            deviation: The detected deviation
            athlete_context: Current athlete context (fitness, fatigue, etc.)
            recent_performance: Recent performance data

        Returns:
            AdaptationSuggestion with recommended changes
        """
        # Get upcoming sessions
        upcoming = self._get_upcoming_sessions(plan, deviation.planned_date)

        # Prepare plan context
        current_week = plan.get_current_week(deviation.planned_date)
        plan_context = {
            "current_week": current_week.week_number if current_week else 1,
            "current_phase": current_week.phase.value if current_week else "build",
            "weeks_remaining": plan.goal.weeks_until_race(deviation.planned_date),
            "race_date": plan.goal.race_date.isoformat(),
            "total_weeks": plan.total_weeks,
        }

        initial_state: AdaptationState = {
            "plan_id": plan.id,
            "deviation": deviation.to_dict(),
            "plan_context": plan_context,
            "upcoming_sessions": [self._session_to_dict(s) for s in upcoming],
            "athlete_context": athlete_context or {},
            "actions": [],
            "session_adjustments": [],
            "explanation": "",
            "suggestion": None,
            "errors": [],
            "status": "initialized",
        }

        # Run the graph
        final_state = await self._graph.ainvoke(initial_state)

        if final_state["errors"]:
            logger.warning(f"Adaptation had errors: {final_state['errors']}")

        if final_state["suggestion"] is None:
            # Create a minimal suggestion if workflow failed
            return self._create_fallback_suggestion(plan.id, deviation)

        return self._state_to_suggestion(final_state, deviation)

    async def _analyze_deviation(self, state: AdaptationState) -> AdaptationState:
        """Analyze the deviation to understand its impact."""
        deviation = state["deviation"]
        deviation_type = deviation["deviation_type"]

        # Calculate severity and impact
        metrics = deviation.get("metrics", {})
        load_dev = metrics.get("load_deviation_pct", 0)
        duration_dev = metrics.get("duration_deviation_pct", 0)

        # Determine if this needs adaptation
        needs_adaptation = (
            deviation_type in ("skipped", "harder", "easier") and
            (abs(load_dev) > 15 or abs(duration_dev) > 15 or deviation_type == "skipped")
        )

        if not needs_adaptation:
            state["status"] = "no_adaptation_needed"
            state["explanation"] = "Deviation is within acceptable range. No adaptation needed."
            state["actions"] = [AdaptationAction.MAINTAIN.value]
        else:
            state["status"] = "analyzed"

        return state

    async def _determine_actions(self, state: AdaptationState) -> AdaptationState:
        """Determine which adaptation actions to take."""
        if state["status"] == "no_adaptation_needed":
            return state

        deviation = state["deviation"]
        deviation_type = deviation["deviation_type"]
        metrics = deviation.get("metrics", {})
        plan_context = state["plan_context"]

        actions = []

        if deviation_type == "harder":
            # Workout was harder than planned
            load_dev = metrics.get("load_deviation_pct", 0)
            if load_dev > 30:
                actions.append(AdaptationAction.ADD_RECOVERY)
                actions.append(AdaptationAction.REDUCE_INTENSITY)
            else:
                actions.append(AdaptationAction.REDUCE_INTENSITY)

        elif deviation_type == "easier":
            # Workout was easier than planned
            load_dev = metrics.get("load_deviation_pct", 0)
            if abs(load_dev) > 30:
                # Significant underperformance - might need investigation
                actions.append(AdaptationAction.MAINTAIN)
            else:
                # Slight underperformance - can adjust slightly
                actions.append(AdaptationAction.INCREASE_INTENSITY)

        elif deviation_type == "skipped":
            # Workout was skipped
            weeks_remaining = plan_context.get("weeks_remaining", 4)

            if weeks_remaining <= 2:
                # Close to race - just maintain
                actions.append(AdaptationAction.MAINTAIN)
            else:
                # Redistribute load
                actions.append(AdaptationAction.REDISTRIBUTE_LOAD)

                # If multiple skips, consider extending
                if deviation.get("severity") == "significant":
                    actions.append(AdaptationAction.EXTEND_PLAN)

        elif deviation_type == "extra":
            # Extra workout not in plan
            actions.append(AdaptationAction.REDUCE_VOLUME)

        # Default if no actions
        if not actions:
            actions.append(AdaptationAction.MAINTAIN)

        state["actions"] = [a.value for a in actions]
        state["status"] = "actions_determined"

        return state

    async def _generate_adjustments(self, state: AdaptationState) -> AdaptationState:
        """Generate specific session adjustments."""
        if state["status"] == "no_adaptation_needed":
            return state

        deviation = state["deviation"]
        actions = state["actions"]
        upcoming = state["upcoming_sessions"]

        adjustments = []

        if not upcoming:
            state["session_adjustments"] = []
            state["status"] = "adjustments_generated"
            return state

        # Get the next non-rest session
        next_session = None
        for session in upcoming:
            if session.get("workout_type") != "rest":
                next_session = session
                break

        if not next_session:
            state["session_adjustments"] = []
            state["status"] = "adjustments_generated"
            return state

        # Apply adjustments based on actions
        if AdaptationAction.ADD_RECOVERY.value in actions:
            # Convert next session to recovery
            adjustments.append({
                "day_of_week": next_session["day_of_week"],
                "original_type": next_session["workout_type"],
                "suggested_type": "recovery",
                "original_duration_min": next_session.get("target_duration_min", 45),
                "suggested_duration_min": 30,
                "original_load": next_session.get("target_load", 40),
                "suggested_load": 20,
                "rationale": "Adding recovery session after harder-than-planned workout",
            })

        elif AdaptationAction.REDUCE_INTENSITY.value in actions:
            # Reduce intensity of next session
            original_duration = next_session.get("target_duration_min", 45)
            original_load = next_session.get("target_load", 40)

            adjustments.append({
                "day_of_week": next_session["day_of_week"],
                "original_type": next_session["workout_type"],
                "suggested_type": "easy" if next_session["workout_type"] in ("tempo", "threshold", "intervals") else next_session["workout_type"],
                "original_duration_min": original_duration,
                "suggested_duration_min": int(original_duration * 0.85),
                "original_load": original_load,
                "suggested_load": round(original_load * 0.75, 1),
                "rationale": "Reducing intensity after harder effort to prevent overreaching",
            })

        elif AdaptationAction.INCREASE_INTENSITY.value in actions:
            # Slightly increase next session
            original_duration = next_session.get("target_duration_min", 45)
            original_load = next_session.get("target_load", 40)

            adjustments.append({
                "day_of_week": next_session["day_of_week"],
                "original_type": next_session["workout_type"],
                "suggested_type": next_session["workout_type"],
                "original_duration_min": original_duration,
                "suggested_duration_min": int(original_duration * 1.1),
                "original_load": original_load,
                "suggested_load": round(original_load * 1.1, 1),
                "rationale": "Slightly increasing load to compensate for easier session",
            })

        elif AdaptationAction.REDISTRIBUTE_LOAD.value in actions:
            # Redistribute skipped load across next few sessions
            skipped_load = deviation.get("metrics", {}).get("planned_load", 40)
            redistribute_per_session = skipped_load / min(3, len(upcoming))

            for i, session in enumerate(upcoming[:3]):
                if session.get("workout_type") == "rest":
                    continue

                original_load = session.get("target_load", 40)
                original_duration = session.get("target_duration_min", 45)

                adjustments.append({
                    "day_of_week": session["day_of_week"],
                    "original_type": session["workout_type"],
                    "suggested_type": session["workout_type"],
                    "original_duration_min": original_duration,
                    "suggested_duration_min": int(original_duration * 1.05),
                    "original_load": original_load,
                    "suggested_load": round(original_load + redistribute_per_session * 0.3, 1),
                    "rationale": f"Partially redistributing load from skipped session",
                })

        elif AdaptationAction.REDUCE_VOLUME.value in actions:
            # Reduce next session due to extra workout
            original_duration = next_session.get("target_duration_min", 45)
            original_load = next_session.get("target_load", 40)

            adjustments.append({
                "day_of_week": next_session["day_of_week"],
                "original_type": next_session["workout_type"],
                "suggested_type": next_session["workout_type"],
                "original_duration_min": original_duration,
                "suggested_duration_min": int(original_duration * 0.85),
                "original_load": original_load,
                "suggested_load": round(original_load * 0.85, 1),
                "rationale": "Reducing volume to account for extra unplanned workout",
            })

        state["session_adjustments"] = adjustments
        state["status"] = "adjustments_generated"

        return state

    async def _generate_explanation(self, state: AdaptationState) -> AdaptationState:
        """Generate a natural language explanation using LLM."""
        if state["status"] == "no_adaptation_needed":
            return state

        deviation = state["deviation"]
        actions = state["actions"]
        adjustments = state["session_adjustments"]

        # Try to get LLM explanation
        try:
            athlete_context_str = self._format_context(state["athlete_context"])

            system_prompt = ADAPTATION_ANALYSIS_SYSTEM.format(
                athlete_context=athlete_context_str,
            )

            user_prompt = ADAPTATION_ANALYSIS_USER.format(
                deviation=json.dumps(deviation, indent=2),
                current_week=state["plan_context"].get("current_week", 1),
                current_phase=state["plan_context"].get("current_phase", "build"),
                weeks_remaining=state["plan_context"].get("weeks_remaining", 8),
                race_date=state["plan_context"].get("race_date", "N/A"),
                upcoming_sessions=json.dumps(state["upcoming_sessions"][:3], indent=2),
                recent_performance=json.dumps(state["athlete_context"].get("recent_performance", {}), indent=2),
            )

            response = await self.llm_client.completion_json(
                system=system_prompt,
                user=user_prompt,
                model=ModelType.FAST,
                max_tokens=800,
            )

            state["explanation"] = response.get("explanation", "")

            # Update adjustments if LLM provided better ones
            if response.get("session_adjustments") and not adjustments:
                state["session_adjustments"] = response["session_adjustments"]

        except Exception as e:
            logger.warning(f"LLM explanation failed: {e}")
            # Generate fallback explanation
            state["explanation"] = self._generate_fallback_explanation(
                deviation, actions, adjustments
            )

        state["status"] = "explanation_generated"
        return state

    async def _finalize(self, state: AdaptationState) -> AdaptationState:
        """Create the final suggestion object."""
        deviation = state["deviation"]
        actions = state["actions"]
        adjustments = state["session_adjustments"]

        # Calculate expected load change
        if adjustments:
            original_load = sum(a.get("original_load", 0) for a in adjustments)
            suggested_load = sum(a.get("suggested_load", 0) for a in adjustments)
            if original_load > 0:
                expected_change = ((suggested_load - original_load) / original_load) * 100
            else:
                expected_change = 0
        else:
            expected_change = 0

        # Determine affected weeks
        current_week = state["plan_context"].get("current_week", 1)
        affected_weeks = [current_week]
        if adjustments:
            affected_weeks = list(set([current_week, current_week + 1]))

        state["suggestion"] = {
            "plan_id": state["plan_id"],
            "actions": actions,
            "affected_weeks": affected_weeks,
            "session_adjustments": adjustments,
            "explanation": state["explanation"],
            "expected_load_change_pct": round(expected_change, 1),
            "confidence": 0.8 if state["explanation"] else 0.6,
        }

        state["status"] = "completed"
        return state

    def _get_upcoming_sessions(
        self,
        plan: TrainingPlan,
        from_date: date,
    ) -> List[PlannedSession]:
        """Get upcoming sessions for the next 7 days."""
        sessions = []

        # Calculate plan start date
        race_date = plan.goal.race_date
        plan_start = race_date - timedelta(weeks=plan.total_weeks)

        for day_offset in range(1, 8):  # Next 7 days
            check_date = from_date + timedelta(days=day_offset)
            days_since_start = (check_date - plan_start).days

            if days_since_start < 0 or days_since_start >= plan.total_weeks * 7:
                continue

            week_number = (days_since_start // 7) + 1
            day_of_week = check_date.weekday()

            week = plan.get_week(week_number)
            if week:
                for session in week.sessions:
                    if session.day_of_week == day_of_week:
                        sessions.append(session)
                        break

        return sessions

    def _session_to_dict(self, session: PlannedSession) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "day_of_week": session.day_of_week,
            "day_name": session.day_name,
            "workout_type": session.workout_type.value,
            "target_duration_min": session.target_duration_min,
            "target_load": session.target_load,
            "description": session.description,
        }

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format athlete context for prompts."""
        if not context:
            return "No athlete context available"

        parts = []
        if context.get("current_ctl"):
            parts.append(f"CTL (fitness): {context['current_ctl']}")
        if context.get("current_atl"):
            parts.append(f"ATL (fatigue): {context['current_atl']}")
        if context.get("tsb"):
            parts.append(f"TSB (form): {context['tsb']}")
        if context.get("readiness"):
            parts.append(f"Readiness: {context['readiness']}")

        return "\n".join(parts) if parts else "No athlete context available"

    def _generate_fallback_explanation(
        self,
        deviation: Dict[str, Any],
        actions: List[str],
        adjustments: List[Dict[str, Any]],
    ) -> str:
        """Generate a fallback explanation without LLM."""
        deviation_type = deviation.get("deviation_type", "unknown")

        if deviation_type == "harder":
            return ("Your recent workout was harder than planned. "
                    "To prevent overreaching, we recommend reducing the intensity "
                    "of your next session and focusing on recovery.")

        elif deviation_type == "easier":
            return ("Your recent workout was easier than planned. "
                    "We'll make a small adjustment to maintain your training progression "
                    "while respecting your current energy levels.")

        elif deviation_type == "skipped":
            return ("A planned workout was missed. "
                    "We've redistributed a portion of that training load "
                    "across your upcoming sessions to keep you on track.")

        elif deviation_type == "extra":
            return ("You completed an extra workout not in the plan. "
                    "To balance your weekly load and prevent overtraining, "
                    "we recommend reducing the volume of your next planned session.")

        return ("Based on your recent training, we recommend "
                "some minor adjustments to optimize your progress.")

    def _create_fallback_suggestion(
        self,
        plan_id: str,
        deviation: PlanDeviation,
    ) -> AdaptationSuggestion:
        """Create a fallback suggestion when workflow fails."""
        return AdaptationSuggestion(
            plan_id=plan_id,
            deviation=deviation,
            actions=[AdaptationAction.MAINTAIN],
            affected_weeks=[deviation.week_number],
            session_adjustments=[],
            explanation="Unable to generate specific adaptations. Recommend continuing with current plan.",
            expected_load_change_pct=0.0,
            confidence=0.5,
        )

    def _state_to_suggestion(
        self,
        state: AdaptationState,
        deviation: PlanDeviation,
    ) -> AdaptationSuggestion:
        """Convert state to AdaptationSuggestion."""
        suggestion_data = state["suggestion"]

        # Convert action strings to enum
        actions = [
            AdaptationAction(a) for a in suggestion_data.get("actions", ["maintain"])
        ]

        # Convert adjustment dicts to dataclass
        session_adjustments = [
            SessionAdjustment(
                day_of_week=adj["day_of_week"],
                original_type=adj["original_type"],
                suggested_type=adj["suggested_type"],
                original_duration_min=adj["original_duration_min"],
                suggested_duration_min=adj["suggested_duration_min"],
                original_load=adj["original_load"],
                suggested_load=adj["suggested_load"],
                rationale=adj["rationale"],
            )
            for adj in suggestion_data.get("session_adjustments", [])
        ]

        return AdaptationSuggestion(
            plan_id=suggestion_data["plan_id"],
            deviation=deviation,
            actions=actions,
            affected_weeks=suggestion_data.get("affected_weeks", [deviation.week_number]),
            session_adjustments=session_adjustments,
            explanation=suggestion_data.get("explanation", ""),
            expected_load_change_pct=suggestion_data.get("expected_load_change_pct", 0.0),
            confidence=suggestion_data.get("confidence", 0.8),
        )


# ============================================================================
# Factory function for dependency injection
# ============================================================================

_adaptation_agent: Optional[AdaptationAgent] = None


def get_adaptation_agent() -> AdaptationAgent:
    """Get or create the adaptation agent singleton."""
    global _adaptation_agent
    if _adaptation_agent is None:
        _adaptation_agent = AdaptationAgent()
    return _adaptation_agent


def reset_adaptation_agent() -> None:
    """Reset the adaptation agent singleton (for testing)."""
    global _adaptation_agent
    _adaptation_agent = None
