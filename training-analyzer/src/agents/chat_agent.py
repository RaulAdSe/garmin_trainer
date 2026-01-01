"""
Chat Agent for conversational AI training coach.

This agent handles natural language queries about training data,
providing intelligent responses contextualized with athlete data.
"""

import json
import uuid
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END

from ..llm.providers import get_llm_client, ModelType
from ..llm.prompts import (
    CHAT_SYSTEM,
    CHAT_USER,
    CHAT_INTENT_SYSTEM,
    CHAT_INTENT_USER,
)
from ..llm.context_builder import build_athlete_context_prompt
from ..analysis.condensation import condense_workout_data


# ============================================================================
# Enums and Types
# ============================================================================

class ChatIntent(str, Enum):
    """Types of questions the chat agent can handle."""
    TRAINING_STATUS = "training_status"
    WORKOUT_COMPARISON = "workout_comparison"
    READINESS = "readiness"
    RACE_READINESS = "race_readiness"
    TREND_ANALYSIS = "trend_analysis"
    WORKOUT_DETAIL = "workout_detail"
    RECOMMENDATION = "recommendation"
    GENERAL = "general"


class ChatState(TypedDict):
    """State for the chat workflow."""
    # Input
    message: str
    conversation_history: List[Dict[str, str]]
    language: str  # Language code for response (en, es)

    # Processing
    chat_id: str
    intent: Optional[str]
    intent_data: Optional[Dict[str, Any]]

    # Context
    athlete_context: Optional[Dict[str, Any]]
    training_data: Optional[Dict[str, Any]]

    # Output
    response: Optional[str]
    data_sources: List[str]
    error: Optional[str]
    status: str


# ============================================================================
# Chat Agent
# ============================================================================

class ChatAgent:
    """
    LangGraph-based conversational AI agent for training queries.

    This agent:
    1. Classifies the user's intent
    2. Fetches relevant training data
    3. Builds athlete context
    4. Generates a conversational response
    """

    def __init__(
        self,
        llm_client=None,
        coach_service=None,
        training_db=None,
        user_id: Optional[str] = None,
    ):
        """
        Initialize the chat agent.

        Args:
            llm_client: Optional LLM client (uses default if not provided)
            coach_service: Optional CoachService for athlete context
            training_db: Optional TrainingDatabase for data queries
            user_id: Optional user ID for usage tracking and billing
        """
        self._llm_client = llm_client
        self._coach_service = coach_service
        self._training_db = training_db
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
        workflow = StateGraph(ChatState)

        # Add nodes
        workflow.add_node("classify_intent", self._classify_intent)
        workflow.add_node("gather_context", self._gather_context)
        workflow.add_node("fetch_training_data", self._fetch_training_data)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("handle_error", self._handle_error)

        # Add edges
        workflow.set_entry_point("classify_intent")
        workflow.add_edge("classify_intent", "gather_context")
        workflow.add_edge("gather_context", "fetch_training_data")
        workflow.add_conditional_edges(
            "fetch_training_data",
            self._check_data_success,
            {
                "success": "generate_response",
                "error": "handle_error",
            }
        )
        workflow.add_edge("generate_response", END)
        workflow.add_edge("handle_error", END)

        return workflow.compile()

    def _check_data_success(self, state: ChatState) -> str:
        """Check if data fetching succeeded."""
        return "error" if state.get("error") else "success"

    async def _classify_intent(self, state: ChatState) -> Dict[str, Any]:
        """Classify the user's intent from their message."""
        try:
            message = state.get("message", "")

            # Use LLM to classify intent
            intent_response = await self.llm_client.completion_json(
                system=CHAT_INTENT_SYSTEM,
                user=CHAT_INTENT_USER.format(question=message),
                model=ModelType.FAST,
                max_tokens=500,
                user_id=self._user_id,
                analysis_type="intent_classification",
            )

            intent = intent_response.get("intent", "general")

            return {
                **state,
                "intent": intent,
                "intent_data": intent_response,
                "status": "intent_classified",
            }

        except Exception as e:
            # Default to general intent on classification failure
            return {
                **state,
                "intent": "general",
                "intent_data": {"intent": "general", "confidence": 0.5},
                "status": "intent_defaulted",
            }

    async def _gather_context(self, state: ChatState) -> Dict[str, Any]:
        """Gather athlete context for the response."""
        try:
            athlete_context = {}

            if self._coach_service:
                # Get comprehensive athlete context
                context = self._coach_service.get_llm_context()
                athlete_context = context

            return {
                **state,
                "athlete_context": athlete_context,
                "status": "context_gathered",
            }

        except Exception as e:
            return {
                **state,
                "athlete_context": {},
                "status": "context_failed",
            }

    async def _fetch_training_data(self, state: ChatState) -> Dict[str, Any]:
        """Fetch relevant training data based on intent."""
        try:
            intent = state.get("intent", "general")
            intent_data = state.get("intent_data", {})
            training_data = {}
            data_sources = []

            if not self._coach_service and not self._training_db:
                return {
                    **state,
                    "training_data": {},
                    "data_sources": [],
                    "status": "no_data_source",
                }

            # Determine time period from intent
            time_period = intent_data.get("time_period", "last week")
            days = self._parse_time_period(time_period)

            # Fetch data based on intent
            if intent in ["training_status", "readiness"]:
                training_data = await self._fetch_status_data(days)
                data_sources.extend(["fitness_metrics", "readiness"])

            elif intent == "workout_comparison":
                training_data = await self._fetch_comparison_data(intent_data, days)
                data_sources.extend(["workouts", "metrics"])

            elif intent == "trend_analysis":
                training_data = await self._fetch_trend_data(days)
                data_sources.extend(["fitness_metrics", "workouts"])

            elif intent == "race_readiness":
                training_data = await self._fetch_race_readiness_data()
                data_sources.extend(["fitness_metrics", "goals", "readiness"])

            elif intent == "workout_detail":
                training_data = await self._fetch_workout_details(intent_data)
                data_sources.extend(["workouts", "workout_analysis"])

            elif intent == "recommendation":
                training_data = await self._fetch_recommendation_data()
                data_sources.extend(["readiness", "fitness_metrics"])

            else:
                # General - fetch basic context
                training_data = await self._fetch_general_data(days)
                data_sources.extend(["workouts", "metrics"])

            return {
                **state,
                "training_data": training_data,
                "data_sources": data_sources,
                "status": "data_fetched",
            }

        except Exception as e:
            return {
                **state,
                "error": f"Failed to fetch training data: {str(e)}",
                "training_data": {},
                "data_sources": [],
                "status": "data_fetch_failed",
            }

    async def _generate_response(self, state: ChatState) -> Dict[str, Any]:
        """Generate the conversational response."""
        try:
            message = state.get("message", "")
            athlete_context = state.get("athlete_context", {})
            training_data = state.get("training_data", {})
            conversation_history = state.get("conversation_history", [])
            language = state.get("language", "en")

            # Build context prompt
            context_prompt = build_athlete_context_prompt(
                fitness_metrics=athlete_context.get("fitness_metrics"),
                goals=athlete_context.get("race_goals"),
                readiness=athlete_context.get("readiness"),
                recent_activities=training_data.get("recent_activities"),
            )

            # Format training data for prompt
            training_data_str = self._format_training_data(training_data)

            # Build additional context from conversation history
            history_context = ""
            if conversation_history:
                history_lines = []
                for msg in conversation_history[-3:]:  # Last 3 exchanges
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    history_lines.append(f"{role.upper()}: {content[:200]}")
                history_context = "\n".join(history_lines)

            # Get language name for prompt
            language_names = {"en": "English", "es": "Spanish"}
            language_name = language_names.get(language, "English")

            # Build system prompt with language instruction
            base_system = CHAT_SYSTEM.format(
                athlete_context=context_prompt,
            )

            # Add language instruction
            system_prompt = f"""{base_system}

LANGUAGE INSTRUCTION:
You MUST respond entirely in {language_name}. All responses, explanations, recommendations, and metric descriptions must be in {language_name}."""

            user_prompt = CHAT_USER.format(
                question=message,
                training_data=training_data_str,
                additional_context=history_context or "No previous conversation",
            )

            # Generate response
            response = await self.llm_client.completion(
                system=system_prompt,
                user=user_prompt,
                model=ModelType.SMART,
                max_tokens=1500,
                temperature=0.7,
                user_id=self._user_id,
                analysis_type="chat",
            )

            return {
                **state,
                "response": response,
                "status": "completed",
            }

        except Exception as e:
            return {
                **state,
                "error": f"Failed to generate response: {str(e)}",
                "status": "generation_failed",
            }

    async def _handle_error(self, state: ChatState) -> Dict[str, Any]:
        """Handle errors in the workflow."""
        error = state.get("error", "Unknown error occurred")

        # Generate a helpful error response
        response = (
            f"I apologize, but I encountered an issue while processing your question. "
            f"This might be because some training data is not available. "
            f"Could you try rephrasing your question or asking about something else?"
        )

        return {
            **state,
            "response": response,
            "status": "error_handled",
        }

    # ========================================================================
    # Data Fetching Helpers
    # ========================================================================

    def _parse_time_period(self, period: Optional[str]) -> int:
        """Parse a time period string into number of days."""
        if not period:
            return 7

        period = period.lower()

        if "today" in period or "yesterday" in period:
            return 1
        elif "week" in period:
            if "last" in period or "past" in period:
                return 7
            elif "this" in period:
                return date.today().weekday() + 1
            else:
                return 7
        elif "month" in period:
            if "last" in period or "past" in period:
                return 30
            elif "this" in period:
                return date.today().day
            else:
                return 30
        elif "days" in period:
            # Try to extract number
            import re
            match = re.search(r"(\d+)\s*days?", period)
            if match:
                return int(match.group(1))

        return 7  # Default to week

    async def _fetch_status_data(self, days: int) -> Dict[str, Any]:
        """Fetch current training status data."""
        data = {}

        if self._coach_service:
            briefing = self._coach_service.get_daily_briefing()
            data["training_status"] = briefing.get("training_status", {})
            data["readiness"] = briefing.get("readiness", {})
            data["weekly_load"] = briefing.get("weekly_load", {})
            data["recommendation"] = briefing.get("recommendation", {})
            data["recent_activities"] = self._coach_service.get_recent_activities(days=days)

        return data

    async def _fetch_comparison_data(
        self,
        intent_data: Dict[str, Any],
        days: int,
    ) -> Dict[str, Any]:
        """Fetch data for comparing periods or workouts."""
        data = {}

        if self._coach_service:
            # Get current period
            data["current_period"] = self._coach_service.get_recent_activities(days=days)

            # Get previous period for comparison
            end_date = date.today() - timedelta(days=days)
            data["previous_period"] = self._coach_service.get_recent_activities(
                days=days,
                end_date=end_date,
            )

            # Weekly summaries if comparing weeks
            if "week" in str(intent_data.get("comparison_type", "")):
                data["this_week"] = self._coach_service.get_weekly_summary(weeks_back=0)
                data["last_week"] = self._coach_service.get_weekly_summary(weeks_back=1)

        return data

    async def _fetch_trend_data(self, days: int) -> Dict[str, Any]:
        """Fetch trend and progress data."""
        data = {}

        if self._coach_service:
            # Get activities for trend analysis
            data["activities"] = self._coach_service.get_recent_activities(days=days)

            # Get multiple weekly summaries
            weeks = min(days // 7, 4)
            data["weekly_summaries"] = []
            for w in range(weeks):
                summary = self._coach_service.get_weekly_summary(weeks_back=w)
                data["weekly_summaries"].append(summary)

            # Current fitness metrics
            data["fitness_metrics"] = self._coach_service.get_fitness_metrics()

        return data

    async def _fetch_race_readiness_data(self) -> Dict[str, Any]:
        """Fetch data for race readiness assessment."""
        data = {}

        if self._coach_service:
            briefing = self._coach_service.get_daily_briefing()
            data["readiness"] = briefing.get("readiness", {})
            data["training_status"] = briefing.get("training_status", {})
            data["garmin_fitness"] = briefing.get("garmin_fitness", {})
            data["race_predictions"] = briefing.get("race_predictions", {})
            data["goal_feasibility"] = briefing.get("goal_feasibility", {})

            # Recent training summary
            data["recent_activities"] = self._coach_service.get_recent_activities(days=14)

        if self._training_db:
            data["race_goals"] = self._training_db.get_race_goals()

        return data

    async def _fetch_workout_details(
        self,
        intent_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fetch details about specific workouts with rich analysis context."""
        data = {}

        specific_date = intent_data.get("specific_date")

        if self._coach_service:
            if specific_date:
                # Get activities for that specific date
                target_date = datetime.strptime(specific_date, "%Y-%m-%d").date()
                activities = self._coach_service.get_recent_activities(
                    days=1,
                    end_date=target_date,
                )
                data["workouts"] = activities
            else:
                # Get most recent activities
                data["workouts"] = self._coach_service.get_recent_activities(days=7)

            # Enrich workouts with stored analysis data
            if data.get("workouts") and self._training_db:
                enriched_workouts = []
                for workout in data["workouts"]:
                    workout_id = workout.get("activity_id")
                    if workout_id:
                        # Try to get stored workout analysis from DB
                        analysis = self._training_db.get_workout_analysis(workout_id)
                        if analysis:
                            workout["analysis"] = {
                                "summary": analysis.get("summary"),
                                "what_went_well": analysis.get("what_went_well", []),
                                "improvements": analysis.get("improvements", []),
                                "training_context": analysis.get("training_context"),
                                "execution_rating": analysis.get("execution_rating"),
                                "overall_score": analysis.get("overall_score"),
                                "training_effect_score": analysis.get("training_effect_score"),
                                "load_score": analysis.get("load_score"),
                                "recovery_hours": analysis.get("recovery_hours"),
                            }
                    enriched_workouts.append(workout)
                data["workouts"] = enriched_workouts

        return data

    async def _fetch_recommendation_data(self) -> Dict[str, Any]:
        """Fetch data for generating recommendations."""
        data = {}

        if self._coach_service:
            briefing = self._coach_service.get_daily_briefing()
            data["readiness"] = briefing.get("readiness", {})
            data["recommendation"] = briefing.get("recommendation", {})
            data["training_status"] = briefing.get("training_status", {})
            data["weekly_load"] = briefing.get("weekly_load", {})
            data["training_paces"] = briefing.get("training_paces", {})

        return data

    async def _fetch_general_data(self, days: int) -> Dict[str, Any]:
        """Fetch general training data."""
        data = {}

        if self._coach_service:
            data["recent_activities"] = self._coach_service.get_recent_activities(days=days)
            data["fitness_metrics"] = self._coach_service.get_fitness_metrics()

            briefing = self._coach_service.get_daily_briefing()
            data["readiness"] = briefing.get("readiness", {})

        return data

    def _format_training_data(self, data: Dict[str, Any]) -> str:
        """Format training data for inclusion in the prompt."""
        if not data:
            return "No training data available."

        parts = []

        # Format training status
        if "training_status" in data and data["training_status"]:
            ts = data["training_status"]
            parts.append("CURRENT TRAINING STATUS:")
            parts.append(f"  CTL (Fitness): {ts.get('ctl', 0):.1f}")
            parts.append(f"  ATL (Fatigue): {ts.get('atl', 0):.1f}")
            parts.append(f"  TSB (Form): {ts.get('tsb', 0):.1f}")
            parts.append(f"  ACWR: {ts.get('acwr', 1.0):.2f}")
            parts.append(f"  Risk Zone: {ts.get('risk_zone', 'unknown')}")
            parts.append("")

        # Format readiness
        if "readiness" in data and data["readiness"]:
            r = data["readiness"]
            parts.append("READINESS:")
            parts.append(f"  Score: {r.get('score', 0)}/100")
            parts.append(f"  Zone: {r.get('zone', 'unknown')}")
            if r.get("recommendation"):
                parts.append(f"  Recommendation: {r.get('recommendation')}")
            parts.append("")

        # Format weekly load
        if "weekly_load" in data and data["weekly_load"]:
            wl = data["weekly_load"]
            parts.append("WEEKLY LOAD:")
            parts.append(f"  Current: {wl.get('current', 0):.0f}")
            parts.append(f"  Target: {wl.get('target', 0):.0f}")
            parts.append(f"  Workouts: {wl.get('workout_count', 0)}")
            parts.append("")

        # Format recent activities
        activities = data.get("recent_activities") or data.get("activities", [])
        if activities:
            parts.append("RECENT ACTIVITIES:")
            for a in activities[:5]:  # Limit to 5
                a_type = a.get("activity_type", "workout")
                a_date = a.get("date", "")
                a_dist = a.get("distance_km", 0) or 0
                a_dur = a.get("duration_min", 0) or 0
                a_hr = a.get("avg_hr", "N/A")
                a_load = a.get("hrss") or a.get("trimp", 0) or 0
                parts.append(
                    f"  - {a_date}: {a_type} | "
                    f"{a_dist:.1f}km | {a_dur:.0f}min | "
                    f"HR {a_hr} | Load {a_load:.0f}"
                )
            parts.append("")

        # Format weekly summaries if available
        if "weekly_summaries" in data:
            parts.append("WEEKLY TRENDS:")
            for ws in data["weekly_summaries"]:
                week_start = ws.get("week_start", "")
                total_load = ws.get("total_load", 0)
                total_dist = ws.get("total_distance_km", 0)
                ctl_change = ws.get("ctl_change", 0)
                parts.append(
                    f"  Week of {week_start}: "
                    f"Load {total_load:.0f} | "
                    f"{total_dist:.1f}km | "
                    f"CTL change {ctl_change:+.1f}"
                )
            parts.append("")

        # Format recommendation
        if "recommendation" in data and data["recommendation"]:
            rec = data["recommendation"]
            parts.append("TODAY'S RECOMMENDATION:")
            parts.append(f"  Workout Type: {rec.get('workout_type', 'unknown')}")
            parts.append(f"  Duration: {rec.get('duration_min', 0)} minutes")
            parts.append(f"  Reason: {rec.get('reason', '')}")
            parts.append("")

        # Format race goals
        if "race_goals" in data and data["race_goals"]:
            parts.append("RACE GOALS:")
            for goal in data["race_goals"][:2]:
                parts.append(
                    f"  - {goal.get('distance', 'Race')}: "
                    f"{goal.get('target_time_formatted', 'N/A')} on "
                    f"{goal.get('race_date', 'TBD')}"
                )
            parts.append("")

        # Format race predictions
        if "race_predictions" in data and data["race_predictions"]:
            rp = data["race_predictions"]
            parts.append("RACE PREDICTIONS:")
            if rp.get("5k"):
                parts.append(f"  5K: {rp.get('5k')}")
            if rp.get("10k"):
                parts.append(f"  10K: {rp.get('10k')}")
            if rp.get("half_marathon"):
                parts.append(f"  Half Marathon: {rp.get('half_marathon')}")
            if rp.get("marathon"):
                parts.append(f"  Marathon: {rp.get('marathon')}")
            parts.append("")

        # Format comparison data
        if "this_week" in data and "last_week" in data:
            tw = data["this_week"]
            lw = data["last_week"]
            parts.append("WEEK COMPARISON:")
            parts.append(f"  This Week: Load {tw.get('total_load', 0):.0f}, "
                        f"{tw.get('workout_count', 0)} workouts")
            parts.append(f"  Last Week: Load {lw.get('total_load', 0):.0f}, "
                        f"{lw.get('workout_count', 0)} workouts")
            parts.append("")

        # Format detailed workouts with analysis (for workout_detail intent)
        workouts = data.get("workouts", [])
        if workouts:
            parts.append("WORKOUT DETAILS:")
            for w in workouts[:5]:  # Limit to 5 workouts
                w_type = w.get("activity_type", "workout")
                w_name = w.get("activity_name", "")
                w_date = w.get("date", "")
                w_dist = w.get("distance_km", 0) or 0
                w_dur = w.get("duration_min", 0) or 0
                w_hr = w.get("avg_hr", "N/A")
                w_max_hr = w.get("max_hr", "N/A")
                w_load = w.get("hrss") or w.get("trimp", 0) or 0
                w_pace = w.get("pace_sec_per_km")

                parts.append(f"  --- {w_date}: {w_name or w_type} ---")
                parts.append(f"    Type: {w_type}")
                parts.append(f"    Distance: {w_dist:.2f} km | Duration: {w_dur:.0f} min")

                if w_pace:
                    pace_min = int(w_pace // 60)
                    pace_sec = int(w_pace % 60)
                    parts.append(f"    Pace: {pace_min}:{pace_sec:02d}/km")

                parts.append(f"    HR: Avg {w_hr} bpm, Max {w_max_hr} bpm")
                parts.append(f"    Training Load: {w_load:.0f}")

                # Zone distribution
                z1 = w.get("zone1_pct", 0) or 0
                z2 = w.get("zone2_pct", 0) or 0
                z3 = w.get("zone3_pct", 0) or 0
                z4 = w.get("zone4_pct", 0) or 0
                z5 = w.get("zone5_pct", 0) or 0
                if any([z1, z2, z3, z4, z5]):
                    parts.append(f"    Zone Distribution: Z1:{z1:.0f}% Z2:{z2:.0f}% Z3:{z3:.0f}% Z4:{z4:.0f}% Z5:{z5:.0f}%")

                # Include AI analysis if available
                analysis = w.get("analysis")
                if analysis:
                    parts.append("    AI ANALYSIS:")
                    if analysis.get("summary"):
                        parts.append(f"      Summary: {analysis['summary']}")
                    if analysis.get("execution_rating"):
                        parts.append(f"      Execution: {analysis['execution_rating']}")
                    if analysis.get("overall_score"):
                        parts.append(f"      Overall Score: {analysis['overall_score']}/100")
                    if analysis.get("training_effect_score"):
                        parts.append(f"      Training Effect: {analysis['training_effect_score']:.1f}/5.0")
                    if analysis.get("recovery_hours"):
                        parts.append(f"      Recovery Time: {analysis['recovery_hours']} hours")

                    # What went well
                    went_well = analysis.get("what_went_well", [])
                    if went_well:
                        parts.append("      What Went Well:")
                        for item in went_well[:3]:  # Limit to 3
                            parts.append(f"        - {item}")

                    # Areas for improvement
                    improvements = analysis.get("improvements", [])
                    if improvements:
                        parts.append("      Areas to Improve:")
                        for item in improvements[:3]:  # Limit to 3
                            parts.append(f"        - {item}")

                    if analysis.get("training_context"):
                        parts.append(f"      Context: {analysis['training_context']}")

                parts.append("")

        return "\n".join(parts) if parts else "Limited training data available."

    # ========================================================================
    # Public Interface
    # ========================================================================

    async def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Process a chat message and return a response.

        Args:
            message: The user's message/question
            conversation_history: Optional list of previous messages
                [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            language: Language code for the response (en=English, es=Spanish)

        Returns:
            Dictionary with:
                - response: The AI's response text
                - data_sources: List of data sources used
                - intent: The classified intent
                - chat_id: Unique ID for this chat turn
        """
        initial_state: ChatState = {
            "message": message,
            "conversation_history": conversation_history or [],
            "language": language,
            "chat_id": str(uuid.uuid4()),
            "intent": None,
            "intent_data": None,
            "athlete_context": None,
            "training_data": None,
            "response": None,
            "data_sources": [],
            "error": None,
            "status": "initialized",
        }

        # Run the graph
        final_state = await self._graph.ainvoke(initial_state)

        return {
            "response": final_state.get("response", "I'm sorry, I couldn't process that request."),
            "data_sources": final_state.get("data_sources", []),
            "intent": final_state.get("intent", "unknown"),
            "chat_id": final_state.get("chat_id"),
            "status": final_state.get("status"),
        }
