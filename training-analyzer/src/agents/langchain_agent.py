"""LangChain-based agentic AI coach.

This agent can:
- Query athlete data on-demand using tools
- Reason about the athlete's situation
- Take actions (create plans, design workouts)
- Never ask for information available in the database

This agent uses LangChain with Anthropic Claude for:
- Dynamic tool calling (fetch data on-demand)
- Multi-step reasoning
- Full Langfuse tracing for observability
- Token-based usage tracking

See docs/ai-agentic-architecture.md for architecture details.
"""

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional, Union
from collections import Counter

from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

# LLM imports - support both Anthropic and OpenAI
try:
    from langchain_anthropic import ChatAnthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    from langchain_openai import ChatOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


def get_available_llm(
    model: Optional[str] = None,
    temperature: float = 0,
    max_tokens: int = 4096,
):
    """Get the best available LLM based on API keys and packages.

    Priority: Anthropic > OpenAI

    Returns:
        Tuple of (llm_instance, model_id, provider)
    """
    from ..config import get_settings
    settings = get_settings()

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")

    # Try Anthropic first
    if HAS_ANTHROPIC and anthropic_key:
        model_id = model or "claude-sonnet-4-20250514"
        return ChatAnthropic(
            model=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
        ), model_id, "anthropic"

    # Fall back to OpenAI (default to gpt-5-mini for cost efficiency)
    if HAS_OPENAI and openai_key:
        model_id = model if model and "gpt" in model else "gpt-5-mini"
        return ChatOpenAI(
            model=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=openai_key,
        ), model_id, "openai"

    # No LLM available
    raise RuntimeError(
        "No LLM available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in environment. "
        f"Packages: anthropic={HAS_ANTHROPIC}, openai={HAS_OPENAI}"
    )

from ..observability.langfuse_config import get_langfuse_callback, is_langfuse_enabled
from ..utils.token_counter import count_tokens, count_message_tokens

# Try to import external tools (may not exist yet)
try:
    from ..tools.query_tools import (
        query_workouts as external_query_workouts,
        query_wellness as external_query_wellness,
        get_athlete_profile as external_get_athlete_profile,
        get_training_patterns as external_get_training_patterns,
        get_fitness_metrics as external_get_fitness_metrics,
        get_garmin_data as external_get_garmin_data,
        compare_workouts as external_compare_workouts,
        get_workout_details as external_get_workout_details,
    )
    EXTERNAL_QUERY_TOOLS = True
except ImportError:
    EXTERNAL_QUERY_TOOLS = False

try:
    from ..tools.action_tools import (
        create_training_plan,
        design_workout,
        log_note,
        set_goal,
    )
    EXTERNAL_ACTION_TOOLS = True
except ImportError:
    EXTERNAL_ACTION_TOOLS = False

logger = logging.getLogger(__name__)


# ============================================================================
# Streaming Event Types
# ============================================================================

StreamEventType = Literal["status", "tool_start", "tool_end", "token", "done", "error"]


@dataclass
class StreamEvent:
    """Event emitted during streaming chat."""

    type: StreamEventType
    content: Optional[str] = None
    tool: Optional[str] = None
    message: Optional[str] = None
    tools_used: Optional[List[str]] = None
    token_usage: Optional[Dict[str, int]] = None
    trace_id: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: Dict[str, Any] = {"type": self.type}
        if self.content is not None:
            result["content"] = self.content
        if self.tool is not None:
            result["tool"] = self.tool
        if self.message is not None:
            result["message"] = self.message
        if self.tools_used is not None:
            result["tools_used"] = self.tools_used
        if self.token_usage is not None:
            result["token_usage"] = self.token_usage
        if self.trace_id is not None:
            result["trace_id"] = self.trace_id
        if self.error is not None:
            result["error"] = self.error
        return result


# Tool name to human-readable message mapping
TOOL_MESSAGES = {
    "query_workouts": "Searching your workout history...",
    "get_athlete_profile": "Fetching your athlete profile...",
    "get_training_patterns": "Analyzing your training patterns...",
    "query_wellness": "Checking your wellness data...",
    "get_fitness_metrics": "Loading your fitness metrics...",
    "get_garmin_data": "Fetching Garmin data...",
    "compare_workouts": "Comparing workouts...",
    "get_workout_details": "Analyzing workout time-series data...",
    "create_training_plan": "Creating training plan...",
    "design_workout": "Designing workout...",
    "log_note": "Logging note...",
    "set_goal": "Setting goal...",
}


# System prompt for the agentic coach
SYSTEM_PROMPT = """You are an expert running coach AI assistant.

You have access to the athlete's complete training database through tools.
ALWAYS use tools to get data - never guess or ask for information you can look up.

Guidelines:
- Use get_athlete_profile() first to understand current fitness state
- Use query_workouts() to find specific workouts or analyze history
- Use get_training_patterns() to understand training habits
- Use get_fitness_metrics() for CTL/ATL/TSB trends over time
- Use query_wellness() for sleep, HRV, stress, and body battery data
- Use get_garmin_data() for real-time Garmin metrics (VO2max, race predictions, training status)
- Never ask for: fitness level, weekly mileage, HR zones, training days (use tools)
- Only ask for: race goals, race dates, preferences, injuries

Be concise and data-driven in responses.

Language: {language}"""

# Alias for backwards compatibility
AGENTIC_COACH_SYSTEM = SYSTEM_PROMPT


class LangChainCoachAgent:
    """
    LangChain-based agentic coach that queries data on-demand.

    Unlike the static ChatAgent, this agent:
    1. Uses tools to fetch only the data it needs
    2. Never asks for information available in the database
    3. Can take actions (create plans, design workouts)

    This agent:
    1. Uses LangChain AgentExecutor for tool-calling workflows
    2. Integrates with Langfuse for full observability
    3. Tracks token usage for quota management
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        temperature: float = 0,
        max_tokens: int = 4096,
        user_id: Optional[str] = None,
        coach_service=None,
        training_db=None,
    ):
        """Initialize the LangChain coach agent.

        Args:
            model: Anthropic model ID to use
            temperature: Sampling temperature (0 = deterministic)
            max_tokens: Maximum tokens in response
            user_id: User ID for tracking and Langfuse
            coach_service: CoachService for athlete context
            training_db: TrainingDatabase for data queries
        """
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._user_id = user_id
        self._coach_service = coach_service
        self._training_db = training_db

        # Initialize LLM (auto-detect provider based on available API keys)
        self._llm, self._model_id, self._provider = get_available_llm(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self._model = self._model_id  # For backwards compatibility

        # Build tools and agent
        self._tools = self._build_tools()
        self._agent_executor = self._build_agent()

        logger.info(f"LangChainCoachAgent initialized with {self._provider}:{self._model_id}")

    @property
    def user_id(self) -> Optional[str]:
        """Get the user ID for usage tracking."""
        return self._user_id

    @user_id.setter
    def user_id(self, value: Optional[str]) -> None:
        """Set the user ID for usage tracking."""
        self._user_id = value

    def _build_tools(self) -> List:
        """Build the LangChain tools for the agent."""
        from langchain_core.tools import tool

        tools = []

        # Query workouts tool
        @tool
        def query_workouts(
            sport_type: Optional[str] = None,
            days: int = 7,
            workout_type: Optional[str] = None,
            limit: int = 10,
        ) -> str:
            """Query workout history with flexible filters.

            Args:
                sport_type: Filter by sport (running, cycling, swimming, strength)
                days: Number of days to look back (default 7)
                workout_type: Filter by workout type (easy, tempo, long, intervals)
                limit: Maximum number of workouts to return (default 10)

            Returns:
                Formatted string with workout summaries
            """
            if not self._coach_service:
                return "No training data available."

            try:
                activities = self._coach_service.get_recent_activities(days=days)

                # Apply filters
                filtered = activities
                if sport_type:
                    filtered = [a for a in filtered if a.get("activity_type", "").lower() == sport_type.lower()]
                if workout_type:
                    filtered = [a for a in filtered if a.get("workout_type", "").lower() == workout_type.lower()]

                filtered = filtered[:limit]

                if not filtered:
                    return f"No workouts found matching criteria in the last {days} days."

                lines = [f"Found {len(filtered)} workout(s):"]
                for w in filtered:
                    date_str = w.get("date", "")
                    w_type = w.get("activity_type", "workout")
                    dist = w.get("distance_km", 0) or 0
                    dur = w.get("duration_min", 0) or 0
                    hr = w.get("avg_hr", "N/A")
                    load = w.get("hrss") or w.get("trimp", 0) or 0
                    lines.append(f"- {date_str}: {w_type} | {dist:.1f}km | {dur:.0f}min | HR {hr} | Load {load:.0f}")

                return "\n".join(lines)

            except Exception as e:
                logger.error(f"Error querying workouts: {e}")
                return f"Error querying workouts: {str(e)}"

        tools.append(query_workouts)

        # Get athlete profile tool
        @tool
        def get_athlete_profile() -> str:
            """Get current athlete profile with fitness metrics, HR zones, and training paces.

            Returns:
                Formatted string with CTL, ATL, TSB, ACWR, readiness, HR zones, paces, and goals
            """
            if not self._coach_service:
                return "No athlete profile available."

            try:
                context = self._coach_service.get_llm_context()
                briefing = self._coach_service.get_daily_briefing()

                lines = ["=== ATHLETE PROFILE ==="]

                # Fitness metrics
                ts = briefing.get("training_status", {})
                lines.append("")
                lines.append("Fitness Metrics:")
                lines.append(f"- CTL (Chronic Training Load): {ts.get('ctl', 0):.1f}")
                lines.append(f"- ATL (Acute Training Load): {ts.get('atl', 0):.1f}")
                lines.append(f"- TSB (Training Stress Balance): {ts.get('tsb', 0):.1f}")
                lines.append(f"- ACWR (Acute:Chronic Ratio): {ts.get('acwr', 1.0):.2f}")
                lines.append(f"- Risk Zone: {ts.get('risk_zone', 'unknown')}")

                # Readiness
                r = briefing.get("readiness", {})
                lines.append("")
                lines.append("Readiness:")
                lines.append(f"- Score: {r.get('score', 0)}/100")
                lines.append(f"- Zone: {r.get('zone', 'unknown')}")

                # Weekly load
                wl = briefing.get("weekly_load", {})
                lines.append("")
                lines.append("This Week:")
                lines.append(f"- Current Load: {wl.get('current', 0):.0f}")
                lines.append(f"- Target Load: {wl.get('target', 0):.0f}")
                lines.append(f"- Workouts: {wl.get('workout_count', 0)}")

                # Goals
                if self._training_db:
                    goals = self._training_db.get_race_goals()
                    if goals:
                        lines.append("")
                        lines.append("Race Goals:")
                        for g in goals[:3]:
                            lines.append(f"- {g.get('distance', 'Race')}: {g.get('target_time_formatted', 'N/A')} on {g.get('race_date', 'TBD')}")

                return "\n".join(lines)

            except Exception as e:
                logger.error(f"Error getting athlete profile: {e}")
                return f"Error getting athlete profile: {str(e)}"

        tools.append(get_athlete_profile)

        # Get training patterns tool
        @tool
        def get_training_patterns() -> str:
            """Get detected training patterns from workout history.

            Returns:
                Formatted string with training frequency, typical days, cross-training info
            """
            if not self._coach_service:
                return "No training pattern data available."

            try:
                # Get recent activities for pattern detection
                activities = self._coach_service.get_recent_activities(days=56)  # 8 weeks

                if not activities:
                    return "Not enough training history to detect patterns."

                # Analyze patterns
                from datetime import datetime
                from collections import Counter

                days_with_workouts = set()
                sport_types = Counter()
                workout_types = Counter()

                for a in activities:
                    date_str = a.get("date", "")
                    if date_str:
                        try:
                            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            days_with_workouts.add(dt.strftime("%Y-%m-%d"))
                        except:
                            pass
                    sport_types[a.get("activity_type", "unknown")] += 1
                    if a.get("workout_type"):
                        workout_types[a.get("workout_type", "unknown")] += 1

                weeks = max(1, len(activities) // 7 + 1)
                avg_days_per_week = len(days_with_workouts) / (weeks * 8) * 7

                lines = ["=== TRAINING PATTERNS ==="]
                lines.append("")
                lines.append(f"Training Frequency: ~{avg_days_per_week:.1f} days/week")
                lines.append(f"Total workouts analyzed: {len(activities)} (last 8 weeks)")

                lines.append("")
                lines.append("Sport Distribution:")
                for sport, count in sport_types.most_common(5):
                    pct = count / len(activities) * 100
                    lines.append(f"- {sport}: {count} ({pct:.0f}%)")

                if workout_types:
                    lines.append("")
                    lines.append("Workout Types:")
                    for wtype, count in workout_types.most_common(5):
                        lines.append(f"- {wtype}: {count}")

                # Check for cross-training
                has_strength = "strength" in sport_types or "gym" in sport_types
                has_cycling = "cycling" in sport_types or "biking" in sport_types
                has_swimming = "swimming" in sport_types or "pool" in sport_types

                lines.append("")
                lines.append("Cross-Training:")
                lines.append(f"- Strength Training: {'Yes' if has_strength else 'No'}")
                lines.append(f"- Cycling: {'Yes' if has_cycling else 'No'}")
                lines.append(f"- Swimming: {'Yes' if has_swimming else 'No'}")

                return "\n".join(lines)

            except Exception as e:
                logger.error(f"Error getting training patterns: {e}")
                return f"Error getting training patterns: {str(e)}"

        tools.append(get_training_patterns)

        # Query wellness tool
        @tool
        def query_wellness(days: int = 7) -> str:
            """Query wellness/recovery data including sleep, HRV, stress, and body battery.

            Args:
                days: Number of days to look back (default 7)

            Returns:
                Formatted string with wellness metrics
            """
            if not self._coach_service:
                return "No wellness data available."

            try:
                briefing = self._coach_service.get_daily_briefing()
                readiness = briefing.get("readiness", {})

                lines = ["=== WELLNESS DATA ==="]
                lines.append("")
                lines.append("Current Readiness:")
                lines.append(f"- Score: {readiness.get('score', 0)}/100")
                lines.append(f"- Zone: {readiness.get('zone', 'unknown')}")

                if readiness.get("recommendation"):
                    lines.append(f"- Recommendation: {readiness.get('recommendation')}")

                # Add Garmin fitness data if available
                garmin = briefing.get("garmin_fitness", {})
                if garmin:
                    lines.append("")
                    lines.append("Garmin Metrics:")
                    if garmin.get("vo2max"):
                        lines.append(f"- VO2max: {garmin.get('vo2max')}")
                    if garmin.get("training_status"):
                        lines.append(f"- Training Status: {garmin.get('training_status')}")

                return "\n".join(lines)

            except Exception as e:
                logger.error(f"Error querying wellness: {e}")
                return f"Error querying wellness: {str(e)}"

        tools.append(query_wellness)

        # Get fitness metrics tool
        @tool
        def get_fitness_metrics(
            date_from: Optional[str] = None,
            date_to: Optional[str] = None,
        ) -> str:
            """Get fitness metrics over time (CTL, ATL, TSB).

            Use this to understand fitness trends and training load history.

            Args:
                date_from: Start date (ISO format: YYYY-MM-DD)
                date_to: End date (ISO format: YYYY-MM-DD), defaults to today

            Returns:
                Formatted string with fitness metrics including CTL, ATL, TSB, ACWR
            """
            if not self._coach_service:
                return "No fitness metrics available."

            try:
                target_date = date_to or date.today().isoformat()
                metrics = self._coach_service.get_fitness_metrics(target_date)

                if not metrics:
                    return f"No fitness metrics available for {target_date}."

                lines = ["=== FITNESS METRICS ==="]
                lines.append(f"Date: {target_date}")
                lines.append("")
                lines.append(f"CTL (Chronic Training Load): {metrics.get('ctl', 0):.1f}")
                lines.append(f"ATL (Acute Training Load): {metrics.get('atl', 0):.1f}")
                lines.append(f"TSB (Training Stress Balance): {metrics.get('tsb', 0):.1f}")
                lines.append(f"ACWR (Acute:Chronic Ratio): {metrics.get('acwr', 1.0):.2f}")
                lines.append(f"Risk Zone: {metrics.get('risk_zone', 'unknown')}")

                if metrics.get('ramped_load'):
                    lines.append(f"Ramped Load: {metrics.get('ramped_load'):.0f}")

                return "\n".join(lines)

            except Exception as e:
                logger.error(f"Error getting fitness metrics: {e}")
                return f"Error getting fitness metrics: {str(e)}"

        tools.append(get_fitness_metrics)

        # Get Garmin data tool
        @tool
        def get_garmin_data() -> str:
            """Get latest data from Garmin Connect.

            Returns real-time Garmin metrics including:
            - VO2max: Current VO2max estimate
            - Race predictions: Predicted times for various distances
            - Training status: "Productive", "Maintaining", "Detraining", etc.
            - Training readiness: Score 0-100
            - HRV status: "Balanced", "Low", "High"
            """
            if not self._coach_service:
                return "No Garmin data available."

            try:
                briefing = self._coach_service.get_daily_briefing()

                lines = ["=== GARMIN DATA ==="]

                # Garmin fitness metrics
                garmin = briefing.get("garmin_fitness", {})
                if garmin:
                    lines.append("")
                    lines.append("Garmin Metrics:")
                    if garmin.get("vo2max"):
                        lines.append(f"- VO2max: {garmin.get('vo2max')}")
                    if garmin.get("training_status"):
                        lines.append(f"- Training Status: {garmin.get('training_status')}")
                    if garmin.get("training_readiness"):
                        lines.append(f"- Training Readiness: {garmin.get('training_readiness')}")
                    if garmin.get("hrv_status"):
                        lines.append(f"- HRV Status: {garmin.get('hrv_status')}")

                # Race predictions
                predictions = briefing.get("race_predictions", {})
                if predictions:
                    lines.append("")
                    lines.append("Race Predictions:")
                    if predictions.get("5k"):
                        lines.append(f"- 5K: {predictions.get('5k')}")
                    if predictions.get("10k"):
                        lines.append(f"- 10K: {predictions.get('10k')}")
                    if predictions.get("half_marathon"):
                        lines.append(f"- Half Marathon: {predictions.get('half_marathon')}")
                    if predictions.get("marathon"):
                        lines.append(f"- Marathon: {predictions.get('marathon')}")

                # Readiness
                readiness = briefing.get("readiness", {})
                if readiness:
                    lines.append("")
                    lines.append("Current Readiness:")
                    lines.append(f"- Score: {readiness.get('score', 0)}/100")
                    lines.append(f"- Zone: {readiness.get('zone', 'unknown')}")

                if len(lines) == 1:
                    return "No Garmin data available at this time."

                return "\n".join(lines)

            except Exception as e:
                logger.error(f"Error getting Garmin data: {e}")
                return f"Error getting Garmin data: {str(e)}"

        tools.append(get_garmin_data)

        # Compare workouts tool
        @tool
        def compare_workouts(
            workout_ids: Optional[List[str]] = None,
            days: int = 14,
            workout_type: Optional[str] = None,
        ) -> str:
            """Compare multiple workouts side-by-side.

            Compares recent workouts of the same type to show progression.

            Args:
                workout_ids: Optional list of specific workout IDs to compare
                days: Number of days to look back for workouts (default 14)
                workout_type: Filter to compare only this workout type (e.g., "tempo", "long")

            Returns:
                Comparison of key metrics across workouts
            """
            if not self._coach_service:
                return "No workout data available for comparison."

            try:
                activities = self._coach_service.get_recent_activities(days=days)

                if workout_type:
                    activities = [
                        a for a in activities
                        if a.get("workout_type", "").lower() == workout_type.lower()
                    ]

                if len(activities) < 2:
                    return f"Need at least 2 workouts to compare. Found {len(activities)} in the last {days} days."

                # Compare the workouts
                lines = ["=== WORKOUT COMPARISON ==="]
                lines.append(f"Comparing {len(activities)} workouts:")
                lines.append("")

                for i, w in enumerate(activities[:5], 1):
                    lines.append(f"Workout {i}: {w.get('date', 'N/A')}")
                    lines.append(f"  Type: {w.get('activity_type', 'unknown')}")
                    lines.append(f"  Distance: {w.get('distance_km', 0):.2f} km")
                    lines.append(f"  Duration: {w.get('duration_min', 0):.0f} min")
                    if w.get('pace_sec_per_km'):
                        pace_min = int(w['pace_sec_per_km'] // 60)
                        pace_sec = int(w['pace_sec_per_km'] % 60)
                        lines.append(f"  Pace: {pace_min}:{pace_sec:02d}/km")
                    lines.append(f"  Avg HR: {w.get('avg_hr', 'N/A')} bpm")
                    lines.append(f"  Load: {w.get('hrss') or w.get('trimp', 0):.0f}")
                    lines.append("")

                # Summary comparison
                if len(activities) >= 2:
                    latest = activities[0]
                    previous = activities[1]
                    lines.append("Comparison (Latest vs Previous):")

                    if latest.get('pace_sec_per_km') and previous.get('pace_sec_per_km'):
                        pace_diff = latest['pace_sec_per_km'] - previous['pace_sec_per_km']
                        if pace_diff < 0:
                            lines.append(f"  Pace: {abs(pace_diff):.0f}s/km FASTER")
                        elif pace_diff > 0:
                            lines.append(f"  Pace: {pace_diff:.0f}s/km slower")
                        else:
                            lines.append("  Pace: Same")

                    if latest.get('avg_hr') and previous.get('avg_hr'):
                        hr_diff = latest['avg_hr'] - previous['avg_hr']
                        lines.append(f"  HR: {hr_diff:+.0f} bpm")

                return "\n".join(lines)

            except Exception as e:
                logger.error(f"Error comparing workouts: {e}")
                return f"Error comparing workouts: {str(e)}"

        tools.append(compare_workouts)

        # Get workout details with condensed time-series analysis
        @tool
        def get_workout_details(workout_id: str) -> str:
            """Get deep analysis of a single workout with condensed time-series statistics.

            Use this for detailed analysis beyond basic metrics. Fetches and analyzes
            full time-series data (HR, pace, elevation, cadence, splits) and returns
            condensed statistical summaries.

            Provides:
            - HR analysis: drift, variability, zone transitions, interval detection
            - Pace analysis: consistency score, fade index, negative splits, trend
            - Elevation analysis: terrain type, climb count
            - Splits analysis: even split score, fastest/slowest km
            - Cadence analysis: consistency, fatigue indicators
            - Coaching insights: Pre-computed observations

            Args:
                workout_id: The activity ID from query_workouts results

            Returns:
                Detailed workout analysis with condensed stats
            """
            if EXTERNAL_QUERY_TOOLS:
                try:
                    result = external_get_workout_details(workout_id)
                    if isinstance(result, dict):
                        lines = [f"=== WORKOUT DETAILS: {result.get('name', 'Workout')} ==="]
                        lines.append(f"Date: {result.get('date')} | {result.get('sport_type')}")
                        lines.append(f"Duration: {result.get('duration_min', 0):.0f}min | Distance: {result.get('distance_km', 0):.1f}km")
                        lines.append("")

                        # HR analysis
                        if "hr_analysis" in result:
                            hr = result["hr_analysis"]
                            lines.append("Heart Rate Analysis:")
                            lines.append(f"  {hr.get('summary', '')}")
                            lines.append("")

                        # Pace analysis
                        if "pace_analysis" in result:
                            pace = result["pace_analysis"]
                            lines.append("Pace Analysis:")
                            lines.append(f"  {pace.get('summary', '')}")
                            lines.append(f"  Consistency: {pace.get('consistency_score', 0)}/100")
                            lines.append(f"  Fade Index: {pace.get('fade_index', 1.0):.2f}")
                            if pace.get('negative_split'):
                                lines.append("  ✓ Negative split achieved")
                            lines.append("")

                        # Splits analysis
                        if "splits_analysis" in result:
                            sp = result["splits_analysis"]
                            lines.append("Splits Analysis:")
                            lines.append(f"  {sp.get('summary', '')}")
                            lines.append("")

                        # Elevation analysis
                        if "elevation_analysis" in result:
                            elev = result["elevation_analysis"]
                            lines.append("Elevation:")
                            lines.append(f"  {elev.get('summary', '')}")
                            lines.append("")

                        # Cadence analysis
                        if "cadence_analysis" in result:
                            cad = result["cadence_analysis"]
                            lines.append("Cadence:")
                            lines.append(f"  {cad.get('summary', '')}")
                            lines.append("")

                        # Coaching insights
                        if "coaching_insights" in result:
                            lines.append("Coaching Insights:")
                            for insight in result["coaching_insights"]:
                                lines.append(f"  • {insight}")

                        return "\n".join(lines)
                    return str(result)
                except Exception as e:
                    logger.error(f"Error getting workout details: {e}")
                    return f"Error getting workout details: {str(e)}"
            else:
                return "Workout details analysis not available - external tools not loaded."

        tools.append(get_workout_details)

        # Add action tools if available
        if EXTERNAL_ACTION_TOOLS:
            try:
                tools.extend([create_training_plan, design_workout, log_note, set_goal])
                logger.debug("Action tools loaded from external module")
            except Exception as e:
                logger.warning(f"Failed to load action tools: {e}")

        return tools

    def _build_agent(self):
        """Build the LangGraph react agent."""
        # Create agent with tools using langgraph
        agent = create_react_agent(
            self._llm,
            self._tools,
        )

        return agent

    def _convert_chat_history(self, history: List[Dict[str, str]]) -> List:
        """Convert chat history dict to LangChain messages."""
        messages = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        return messages

    async def chat(
        self,
        message: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        """Process a chat message through the LangChain agent.

        Args:
            message: The user's message
            chat_history: Optional list of previous messages
            session_id: Optional session ID for Langfuse tracing
            language: Language for the response (en, es, fr, de, etc.)

        Returns:
            Dict with:
                - response: The agent's response text
                - status: "completed" or "error"
                - tools_used: List of tools that were called
                - token_usage: Dict with input/output tokens (optional)
                - trace_id: Langfuse trace ID (if enabled)
                - error: Error message if status is "error"
        """
        start_time = datetime.utcnow()
        trace_id = None
        langfuse_trace = None

        # Set up Langfuse tracing if configured
        langfuse_trace = get_langfuse_callback(
            session_id=session_id or str(uuid.uuid4()),
            user_id=self._user_id,
            trace_name="langchain_coach_chat",
            metadata={
                "language": language,
                "model": self._model_id,
            },
        )
        if langfuse_trace:
            try:
                trace_id = langfuse_trace.id
            except:
                pass

        # Convert chat history
        history_messages = self._convert_chat_history(chat_history or [])

        # Language name for prompt - extended language support
        language_names = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "nl": "Dutch",
            "pl": "Polish",
            "ru": "Russian",
            "ja": "Japanese",
            "zh": "Chinese",
            "ko": "Korean",
        }
        language_name = language_names.get(language, "English")

        try:
            # Build messages for the agent
            system_prompt = AGENTIC_COACH_SYSTEM.format(language=language_name)
            messages = [SystemMessage(content=system_prompt)]
            messages.extend(history_messages)
            messages.append(HumanMessage(content=message))

            # Invoke the agent using langgraph
            result = await self._agent_executor.ainvoke(
                {"messages": messages},
            )

            # Extract response from langgraph result
            final_messages = result.get("messages", [])
            response_text = ""
            tools_used = []

            for msg in final_messages:
                if hasattr(msg, "content") and isinstance(msg, AIMessage):
                    if msg.content:
                        response_text = msg.content
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        if isinstance(tc, dict):
                            tools_used.append(tc.get("name", "unknown"))
                        elif hasattr(tc, "name"):
                            tools_used.append(tc.name)

            if not response_text:
                response_text = "I'm sorry, I couldn't process that request."

            # Calculate duration
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Record generation in Langfuse trace
            if langfuse_trace:
                try:
                    from ..observability.langfuse_config import record_generation

                    input_token_count = count_tokens(message)
                    output_token_count = count_tokens(response_text)
                    record_generation(
                        trace=langfuse_trace,
                        name="coach_response",
                        model=self._model_id,
                        input_messages=[{"role": "user", "content": message}],
                        output=response_text,
                        usage={
                            "input": input_token_count,
                            "output": output_token_count,
                            "total": input_token_count + output_token_count,
                        },
                        metadata={"tools_used": tools_used},
                    )
                except Exception as e:
                    logger.warning(f"Failed to record Langfuse generation: {e}")

            # Estimate token usage using tiktoken for accuracy
            input_tokens = count_tokens(message) + sum(
                count_tokens(str(h)) for h in history_messages
            )
            output_tokens = count_tokens(response_text)

            return {
                "response": response_text,
                "status": "completed",
                "tools_used": list(set(tools_used)),
                "token_usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                },
                "trace_id": trace_id,
                "duration_ms": duration_ms,
                "model": self._model_id,
            }

        except Exception as e:
            logger.error(f"Error in LangChain agent chat: {e}", exc_info=True)
            return {
                "response": "I encountered an error processing your request. Please try again.",
                "status": "error",
                "tools_used": [],
                "error": str(e),
            }

    async def chat_stream(
        self,
        message: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None,
        language: str = "en",
    ) -> AsyncGenerator[StreamEvent, None]:
        """Process a chat message and stream the response.

        Uses langgraph's astream_events() to yield events as they occur:
        - status: Initial thinking status
        - tool_start: When a tool call begins
        - tool_end: When a tool call completes
        - token: Each token of the response
        - done: Final event with metadata
        - error: If an error occurs

        Args:
            message: The user's message
            chat_history: Optional list of previous messages
            session_id: Optional session ID for Langfuse tracing
            language: Language for the response (en, es, fr, de, etc.)

        Yields:
            StreamEvent objects containing event data
        """
        start_time = datetime.utcnow()
        trace_id = None
        tools_used: List[str] = []
        response_text = ""
        input_tokens = 0
        output_tokens = 0

        # Set up Langfuse tracing if configured
        langfuse_trace = get_langfuse_callback(
            session_id=session_id or str(uuid.uuid4()),
            user_id=self._user_id,
            trace_name="langchain_coach_chat_stream",
            metadata={
                "language": language,
                "model": self._model_id,
                "streaming": True,
            },
        )
        if langfuse_trace:
            try:
                trace_id = langfuse_trace.id
            except:
                pass

        # Convert chat history
        history_messages = self._convert_chat_history(chat_history or [])

        # Language name for prompt
        language_names = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "nl": "Dutch",
            "pl": "Polish",
            "ru": "Russian",
            "ja": "Japanese",
            "zh": "Chinese",
            "ko": "Korean",
        }
        language_name = language_names.get(language, "English")

        try:
            # Yield initial status
            yield StreamEvent(type="status", message="Thinking...")

            # Build messages for the agent
            system_prompt = AGENTIC_COACH_SYSTEM.format(language=language_name)
            messages = [SystemMessage(content=system_prompt)]
            messages.extend(history_messages)
            messages.append(HumanMessage(content=message))

            # Track active tool calls to handle start/end events
            active_tool_calls: Dict[str, str] = {}  # call_id -> tool_name

            # Stream events from langgraph
            async for event in self._agent_executor.astream_events(
                {"messages": messages},
                version="v2",
            ):
                event_type = event.get("event", "")
                event_data = event.get("data", {})

                # Handle tool call start
                if event_type == "on_tool_start":
                    tool_name = event.get("name", "unknown_tool")
                    run_id = event.get("run_id", "")
                    active_tool_calls[run_id] = tool_name
                    tools_used.append(tool_name)

                    # Get human-readable message for this tool
                    tool_message = TOOL_MESSAGES.get(
                        tool_name, f"Running {tool_name}..."
                    )

                    yield StreamEvent(
                        type="tool_start",
                        tool=tool_name,
                        message=tool_message,
                    )

                # Handle tool call end
                elif event_type == "on_tool_end":
                    run_id = event.get("run_id", "")
                    tool_name = active_tool_calls.pop(run_id, "unknown_tool")

                    yield StreamEvent(
                        type="tool_end",
                        tool=tool_name,
                    )

                # Handle streaming tokens from the LLM
                elif event_type == "on_chat_model_stream":
                    chunk = event_data.get("chunk")
                    if chunk and hasattr(chunk, "content"):
                        content = chunk.content
                        if content and isinstance(content, str):
                            response_text += content
                            output_tokens += 1  # Rough approximation

                            yield StreamEvent(
                                type="token",
                                content=content,
                            )

                # Track input/output from chat model end
                elif event_type == "on_chat_model_end":
                    output = event_data.get("output")
                    if output and hasattr(output, "usage_metadata"):
                        usage = output.usage_metadata
                        if usage:
                            input_tokens = getattr(usage, "input_tokens", 0)
                            output_tokens = getattr(usage, "output_tokens", 0)

            # Calculate duration
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Estimate token usage if not captured (using tiktoken for accuracy)
            if input_tokens == 0:
                input_tokens = count_tokens(message) + sum(
                    count_tokens(str(h)) for h in history_messages
                )
            if output_tokens == 0:
                output_tokens = count_tokens(response_text)

            token_usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            }

            # Record generation in Langfuse trace
            if langfuse_trace:
                try:
                    from ..observability.langfuse_config import record_generation

                    record_generation(
                        trace=langfuse_trace,
                        name="coach_response_stream",
                        model=self._model_id,
                        input_messages=[{"role": "user", "content": message}],
                        output=response_text,
                        usage={
                            "input": input_tokens,
                            "output": output_tokens,
                            "total": input_tokens + output_tokens,
                        },
                        metadata={"tools_used": list(set(tools_used)), "streaming": True},
                    )
                except Exception as e:
                    logger.warning(f"Failed to record Langfuse generation: {e}")

            # Yield final done event
            yield StreamEvent(
                type="done",
                tools_used=list(set(tools_used)),
                token_usage=token_usage,
                trace_id=trace_id,
            )

        except Exception as e:
            logger.error(f"Error in LangChain agent streaming chat: {e}", exc_info=True)
            yield StreamEvent(
                type="error",
                error=str(e),
                message="I encountered an error processing your request. Please try again.",
            )


# Singleton instance
_langchain_agent: Optional[LangChainCoachAgent] = None


def get_langchain_agent(
    user_id: Optional[str] = None,
    coach_service=None,
    training_db=None,
) -> LangChainCoachAgent:
    """Get or create the LangChain agent instance.

    Args:
        user_id: User ID for tracking (updates existing instance)
        coach_service: CoachService for data access
        training_db: TrainingDatabase for direct queries

    Returns:
        The LangChainCoachAgent singleton
    """
    global _langchain_agent

    if _langchain_agent is None:
        _langchain_agent = LangChainCoachAgent(
            coach_service=coach_service,
            training_db=training_db,
            user_id=user_id,
        )
    else:
        # Update user_id and services if provided
        if user_id:
            _langchain_agent.user_id = user_id
        if coach_service:
            _langchain_agent._coach_service = coach_service
            # Rebuild tools with new service
            _langchain_agent._tools = _langchain_agent._build_tools()
            _langchain_agent._agent_executor = _langchain_agent._build_agent()
        if training_db:
            _langchain_agent._training_db = training_db

    return _langchain_agent


def reset_langchain_agent() -> None:
    """Reset the LangChain agent singleton (for testing)."""
    global _langchain_agent
    _langchain_agent = None
