"""
Plan Agent using LangGraph for training plan generation.

This agent generates periodized training plans using a multi-step approach:
1. Analyze athlete context and goal
2. Determine periodization structure
3. Generate week-by-week plan
4. Optimize session distribution
5. Validate and refine
"""

import json
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from dataclasses import dataclass
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from ..models.plans import (
    TrainingPlan,
    TrainingWeek,
    PlannedSession,
    RaceGoal,
    PlanConstraints,
    AthleteContext,
    PeriodizationType,
    TrainingPhase,
    WorkoutType,
)
from ..llm.providers import LLMClient, ModelType, get_llm_client
from ..llm.prompts import (
    PLAN_STRUCTURE_SYSTEM,
    PLAN_STRUCTURE_USER,
    PLAN_WEEK_GENERATION_SYSTEM,
    PLAN_WEEK_GENERATION_USER,
    PLAN_ADAPTATION_SYSTEM,
    PLAN_ADAPTATION_USER,
)


class PlanState(TypedDict):
    """State for the plan generation agent."""
    # Input
    goal: Dict[str, Any]
    constraints: Dict[str, Any]
    athlete_context: Dict[str, Any]

    # Processing state
    periodization_type: str
    phase_distribution: List[Dict[str, Any]]
    weeks: List[Dict[str, Any]]
    current_week_index: int

    # Output
    plan: Optional[Dict[str, Any]]
    errors: List[str]
    status: str


class PlanAgent:
    """
    LangGraph-based agent for generating periodized training plans.

    The agent uses a multi-step workflow:
    1. analyze_goal: Understand the race goal and athlete context
    2. determine_structure: Decide periodization type and phase distribution
    3. generate_weeks: Create detailed sessions for each week
    4. validate_plan: Check constraints and optimize
    5. finalize: Create the final TrainingPlan object
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize the plan agent.

        Args:
            llm_client: LLM client for AI-powered generation. If None, uses default.
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
        workflow = StateGraph(PlanState)

        # Add nodes
        workflow.add_node("analyze_goal", self._analyze_goal)
        workflow.add_node("determine_structure", self._determine_structure)
        workflow.add_node("generate_weeks", self._generate_weeks)
        workflow.add_node("validate_plan", self._validate_plan)
        workflow.add_node("finalize", self._finalize)

        # Add edges
        workflow.set_entry_point("analyze_goal")
        workflow.add_edge("analyze_goal", "determine_structure")
        workflow.add_edge("determine_structure", "generate_weeks")
        workflow.add_edge("generate_weeks", "validate_plan")
        workflow.add_edge("validate_plan", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def generate_plan(
        self,
        goal: RaceGoal,
        athlete_context: AthleteContext,
        constraints: Optional[PlanConstraints] = None,
    ) -> TrainingPlan:
        """
        Generate a complete training plan.

        Args:
            goal: The race goal
            athlete_context: Current athlete fitness/training context
            constraints: Training constraints (days, time limits, etc.)

        Returns:
            A complete TrainingPlan object
        """
        if constraints is None:
            constraints = PlanConstraints()

        initial_state: PlanState = {
            "goal": goal.to_dict(),
            "constraints": constraints.to_dict(),
            "athlete_context": athlete_context.to_dict(),
            "periodization_type": "",
            "phase_distribution": [],
            "weeks": [],
            "current_week_index": 0,
            "plan": None,
            "errors": [],
            "status": "initialized",
        }

        # Run the graph
        final_state = await self._graph.ainvoke(initial_state)

        if final_state["errors"]:
            raise PlanGenerationError(
                f"Plan generation failed: {'; '.join(final_state['errors'])}"
            )

        if final_state["plan"] is None:
            raise PlanGenerationError("Plan generation completed but no plan was created")

        return self._state_to_plan(final_state, goal, athlete_context, constraints)

    async def adapt_plan(
        self,
        plan: TrainingPlan,
        performance_data: Dict[str, Any],
        weeks_to_adapt: Optional[List[int]] = None,
    ) -> TrainingPlan:
        """
        Adapt an existing plan based on performance data.

        Args:
            plan: The existing training plan
            performance_data: Recent performance metrics
            weeks_to_adapt: Specific weeks to adapt (None = all remaining)

        Returns:
            Updated TrainingPlan
        """
        # Get remaining weeks
        current_week = plan.get_current_week()
        if current_week is None:
            raise PlanGenerationError("Cannot adapt plan: no remaining weeks")

        remaining_weeks = [
            w for w in plan.weeks
            if w.week_number >= current_week.week_number
        ]

        if weeks_to_adapt:
            remaining_weeks = [
                w for w in remaining_weeks
                if w.week_number in weeks_to_adapt
            ]

        # Build adaptation prompt
        athlete_context_str = self._format_athlete_context(
            plan.athlete_context.to_dict() if plan.athlete_context else {}
        )

        system_prompt = PLAN_ADAPTATION_SYSTEM.format(
            athlete_context=athlete_context_str,
        )

        user_prompt = PLAN_ADAPTATION_USER.format(
            goal=json.dumps(plan.goal.to_dict(), indent=2),
            current_week=current_week.week_number,
            remaining_weeks=len(remaining_weeks),
            performance_data=json.dumps(performance_data, indent=2),
            original_weeks=json.dumps(
                [w.to_dict() for w in remaining_weeks], indent=2
            ),
        )

        # Get LLM response
        response = await self.llm_client.completion(
            system=system_prompt,
            user=user_prompt,
            model=ModelType.SMART,
            max_tokens=3000,
            temperature=0.5,
        )

        # Parse response
        adapted_weeks_data = self._parse_json_response(response)

        # Update the plan with adapted weeks
        adapted_weeks = self._parse_weeks(adapted_weeks_data.get("weeks", []))

        # Replace adapted weeks in the plan
        for adapted_week in adapted_weeks:
            for i, original_week in enumerate(plan.weeks):
                if original_week.week_number == adapted_week.week_number:
                    plan.weeks[i] = adapted_week
                    break

        # Record adaptation
        plan.adaptation_history.append({
            "timestamp": datetime.now().isoformat(),
            "reason": adapted_weeks_data.get("adaptation_reason", "Performance-based adjustment"),
            "changes": adapted_weeks_data.get("changes_summary", {}),
            "weeks_affected": [w.week_number for w in adapted_weeks],
            "triggered_by": "performance",
        })
        plan.updated_at = datetime.now()

        return plan

    async def _analyze_goal(self, state: PlanState) -> PlanState:
        """Analyze the goal and determine feasibility."""
        goal = state["goal"]
        athlete = state["athlete_context"]

        # Calculate weeks until race
        race_date = datetime.strptime(goal["race_date"], "%Y-%m-%d").date()
        weeks_available = (race_date - date.today()).days // 7

        if weeks_available < 1:
            state["errors"].append("Race date is too soon (less than 1 week)")
            state["status"] = "error"
            return state

        if weeks_available > 52:
            # Cap at 52 weeks - longer plans can be done in phases
            weeks_available = 52

        # Estimate fitness gap
        current_ctl = athlete.get("current_ctl", 30)
        target_ctl = self._estimate_target_ctl(goal["distance"])

        state["athlete_context"]["weeks_available"] = weeks_available
        state["athlete_context"]["target_ctl"] = target_ctl
        state["athlete_context"]["fitness_gap"] = target_ctl - current_ctl
        state["status"] = "analyzed"

        return state

    async def _determine_structure(self, state: PlanState) -> PlanState:
        """Determine periodization type and phase distribution."""
        goal = state["goal"]
        athlete = state["athlete_context"]
        constraints = state["constraints"]

        weeks_available = athlete.get("weeks_available", 12)
        current_ctl = athlete.get("current_ctl", 30)
        fitness_gap = athlete.get("fitness_gap", 20)

        # Decide periodization type
        periodization = self._select_periodization(
            weeks_available=weeks_available,
            fitness_gap=fitness_gap,
            distance=goal["distance"],
        )
        state["periodization_type"] = periodization.value

        # Distribute phases
        phases = self._distribute_phases(
            weeks_available=weeks_available,
            periodization=periodization,
            current_ctl=current_ctl,
        )
        state["phase_distribution"] = phases
        state["status"] = "structured"

        return state

    async def _generate_weeks(self, state: PlanState) -> PlanState:
        """Generate detailed sessions for each week."""
        goal = state["goal"]
        athlete = state["athlete_context"]
        constraints = state["constraints"]
        phases = state["phase_distribution"]

        weeks = []
        week_number = 1
        current_ctl = athlete.get("current_ctl", 30)

        for phase_info in phases:
            phase_name = phase_info["phase"]
            phase_weeks = phase_info["weeks"]
            phase = TrainingPhase(phase_name)

            for week_in_phase in range(phase_weeks):
                is_cutback = self._is_cutback_week(
                    week_number, phase, week_in_phase, phase_weeks
                )

                # Calculate target load for this week
                target_load = self._calculate_week_target_load(
                    phase=phase,
                    week_in_phase=week_in_phase + 1,
                    total_phase_weeks=phase_weeks,
                    current_ctl=current_ctl,
                    is_cutback=is_cutback,
                )

                # Generate sessions
                sessions = self._generate_week_sessions(
                    phase=phase,
                    week_in_phase=week_in_phase + 1,
                    target_load=target_load,
                    constraints=constraints,
                    is_cutback=is_cutback,
                )

                weeks.append({
                    "week_number": week_number,
                    "phase": phase_name,
                    "target_load": target_load,
                    "sessions": sessions,
                    "focus": self._get_phase_focus(phase, week_in_phase + 1, phase_weeks),
                    "notes": self._get_week_notes(phase, week_in_phase + 1, phase_weeks),
                    "is_cutback": is_cutback,
                })

                week_number += 1
                # Simulate CTL progression
                current_ctl += target_load / 7 * 0.1

        state["weeks"] = weeks
        state["status"] = "generated"
        return state

    async def _validate_plan(self, state: PlanState) -> PlanState:
        """Validate the plan against constraints and optimize if needed."""
        weeks = state["weeks"]
        constraints = state["constraints"]
        errors = []

        max_weekly_hours = constraints.get("max_weekly_hours", 8.0)
        max_session_duration = constraints.get("max_session_duration_min", 150)

        for week in weeks:
            total_duration = sum(s["target_duration_min"] for s in week["sessions"])

            # Check weekly hours
            if total_duration > max_weekly_hours * 60:
                # Scale down sessions proportionally
                scale_factor = (max_weekly_hours * 60) / total_duration
                for session in week["sessions"]:
                    session["target_duration_min"] = int(
                        session["target_duration_min"] * scale_factor
                    )

            # Check individual session duration
            for session in week["sessions"]:
                if session["target_duration_min"] > max_session_duration:
                    session["target_duration_min"] = max_session_duration

        state["weeks"] = weeks
        state["status"] = "validated"
        return state

    async def _finalize(self, state: PlanState) -> PlanState:
        """Create the final plan object."""
        weeks = state["weeks"]

        # Find peak week
        peak_week = max(weeks, key=lambda w: w["target_load"])["week_number"]

        state["plan"] = {
            "periodization": state["periodization_type"],
            "total_weeks": len(weeks),
            "peak_week": peak_week,
            "weeks": weeks,
        }
        state["status"] = "completed"

        return state

    def _state_to_plan(
        self,
        state: PlanState,
        goal: RaceGoal,
        athlete_context: AthleteContext,
        constraints: PlanConstraints,
    ) -> TrainingPlan:
        """Convert final state to a TrainingPlan object."""
        plan_data = state["plan"]

        weeks = self._parse_weeks(plan_data["weeks"])

        return TrainingPlan(
            id=TrainingPlan.generate_id(),
            goal=goal,
            weeks=weeks,
            periodization=PeriodizationType(plan_data["periodization"]),
            peak_week=plan_data["peak_week"],
            created_at=datetime.now(),
            athlete_context=athlete_context,
            constraints=constraints,
            name=f"{goal.distance.value.upper()} Plan - {goal.race_date.isoformat()}",
            description=f"Periodized plan for {goal.target_time_formatted} {goal.distance.value}",
        )

    def _parse_weeks(self, weeks_data: List[Dict[str, Any]]) -> List[TrainingWeek]:
        """Parse week dictionaries into TrainingWeek objects."""
        weeks = []
        for week_data in weeks_data:
            sessions = []
            for session_data in week_data.get("sessions", []):
                workout_type = WorkoutType(session_data.get("workout_type", "easy"))
                sessions.append(PlannedSession(
                    day_of_week=session_data.get("day_of_week", 0),
                    workout_type=workout_type,
                    description=session_data.get("description", ""),
                    target_duration_min=session_data.get("target_duration_min", 30),
                    target_load=session_data.get("target_load", 30.0),
                    target_pace=session_data.get("target_pace"),
                    target_hr_zone=session_data.get("target_hr_zone"),
                    intervals=session_data.get("intervals"),
                    notes=session_data.get("notes"),
                ))

            weeks.append(TrainingWeek(
                week_number=week_data["week_number"],
                phase=TrainingPhase(week_data["phase"]),
                target_load=week_data["target_load"],
                sessions=sessions,
                focus=week_data.get("focus"),
                notes=week_data.get("notes"),
                is_cutback=week_data.get("is_cutback", False),
            ))

        return weeks

    def _select_periodization(
        self,
        weeks_available: int,
        fitness_gap: float,
        distance: str,
    ) -> PeriodizationType:
        """Select the best periodization type based on context."""
        # Linear is best for longer preparations with significant fitness gaps
        if weeks_available >= 16 and fitness_gap > 15:
            return PeriodizationType.LINEAR

        # Block periodization for shorter preps or experienced athletes
        if weeks_available >= 8 and fitness_gap < 10:
            return PeriodizationType.BLOCK

        # Reverse linear for very short preps
        if weeks_available < 8:
            return PeriodizationType.REVERSE

        # Default to linear
        return PeriodizationType.LINEAR

    def _distribute_phases(
        self,
        weeks_available: int,
        periodization: PeriodizationType,
        current_ctl: float,
    ) -> List[Dict[str, Any]]:
        """Distribute training phases across available weeks."""
        if weeks_available >= 16:
            # Long preparation
            return [
                {"phase": "base", "weeks": max(4, weeks_available // 4)},
                {"phase": "build", "weeks": weeks_available - 8},
                {"phase": "peak", "weeks": 3},
                {"phase": "taper", "weeks": 1},
            ]
        elif weeks_available >= 12:
            return [
                {"phase": "base", "weeks": 3},
                {"phase": "build", "weeks": weeks_available - 6},
                {"phase": "peak", "weeks": 2},
                {"phase": "taper", "weeks": 1},
            ]
        elif weeks_available >= 8:
            return [
                {"phase": "base", "weeks": 2},
                {"phase": "build", "weeks": weeks_available - 4},
                {"phase": "peak", "weeks": 1},
                {"phase": "taper", "weeks": 1},
            ]
        else:
            # Short preparation
            return [
                {"phase": "build", "weeks": max(1, weeks_available - 2)},
                {"phase": "peak", "weeks": 1},
                {"phase": "taper", "weeks": 1},
            ]

    def _is_cutback_week(
        self,
        week_number: int,
        phase: TrainingPhase,
        week_in_phase: int,
        total_phase_weeks: int,
    ) -> bool:
        """Determine if this should be a cutback (recovery) week."""
        # No cutbacks in taper phase
        if phase == TrainingPhase.TAPER:
            return False

        # Every 4th week is typically a cutback
        if week_number % 4 == 0:
            return True

        # Last week of base phase is a cutback
        if phase == TrainingPhase.BASE and week_in_phase == total_phase_weeks:
            return True

        return False

    def _calculate_week_target_load(
        self,
        phase: TrainingPhase,
        week_in_phase: int,
        total_phase_weeks: int,
        current_ctl: float,
        is_cutback: bool,
    ) -> float:
        """Calculate target weekly load based on phase and progression."""
        # Base load on current fitness
        base_load = current_ctl * 7

        # Phase multipliers
        phase_multipliers = {
            TrainingPhase.BASE: 0.85,
            TrainingPhase.BUILD: 1.0,
            TrainingPhase.PEAK: 1.1,
            TrainingPhase.TAPER: 0.5,
            TrainingPhase.RECOVERY: 0.4,
        }

        multiplier = phase_multipliers.get(phase, 1.0)

        # Progressive overload within phase (except taper)
        if phase not in (TrainingPhase.TAPER, TrainingPhase.RECOVERY):
            progression = 1.0 + (week_in_phase - 1) * 0.05
            multiplier *= min(progression, 1.2)  # Cap at 20% increase

        # Cutback weeks reduce load by 30%
        if is_cutback:
            multiplier *= 0.7

        return round(base_load * multiplier, 1)

    def _generate_week_sessions(
        self,
        phase: TrainingPhase,
        week_in_phase: int,
        target_load: float,
        constraints: Dict[str, Any],
        is_cutback: bool,
    ) -> List[Dict[str, Any]]:
        """Generate session distribution for a week."""
        days_per_week = constraints.get("days_per_week", 5)
        long_run_day = constraints.get("long_run_day", 6)  # Sunday
        rest_days = constraints.get("rest_days", [])

        sessions = []
        load_per_session = target_load / days_per_week

        # Determine which days to train
        all_days = list(range(7))
        train_days = [d for d in all_days if d not in rest_days][:days_per_week]

        # Assign session types based on phase
        for day in range(7):
            if day in rest_days or day not in train_days:
                sessions.append({
                    "day_of_week": day,
                    "workout_type": "rest",
                    "description": "Rest day",
                    "target_duration_min": 0,
                    "target_load": 0.0,
                    "target_hr_zone": None,
                })
            elif day == long_run_day and day in train_days:
                # Long run
                duration = self._get_long_run_duration(phase, week_in_phase, is_cutback)
                sessions.append({
                    "day_of_week": day,
                    "workout_type": "long",
                    "description": "Long run - build aerobic endurance",
                    "target_duration_min": duration,
                    "target_load": load_per_session * 1.5,
                    "target_hr_zone": "Zone 2",
                    "target_pace": "Easy pace",
                })
            elif self._should_be_quality_session(day, phase, train_days, is_cutback):
                # Quality session
                session_type, description, hr_zone = self._get_quality_session(
                    phase, week_in_phase
                )
                sessions.append({
                    "day_of_week": day,
                    "workout_type": session_type,
                    "description": description,
                    "target_duration_min": 45 if not is_cutback else 35,
                    "target_load": load_per_session * 1.2,
                    "target_hr_zone": hr_zone,
                })
            else:
                # Easy run
                sessions.append({
                    "day_of_week": day,
                    "workout_type": "easy",
                    "description": "Easy recovery run",
                    "target_duration_min": 40 if not is_cutback else 30,
                    "target_load": load_per_session * 0.7,
                    "target_hr_zone": "Zone 1-2",
                    "target_pace": "Easy pace",
                })

        return sessions

    def _should_be_quality_session(
        self,
        day: int,
        phase: TrainingPhase,
        train_days: List[int],
        is_cutback: bool,
    ) -> bool:
        """Determine if a day should have a quality session."""
        if is_cutback:
            return False

        if phase == TrainingPhase.BASE:
            return False  # No quality sessions in base phase

        if phase == TrainingPhase.TAPER:
            # One quality session mid-week in taper
            return day == 2 and day in train_days

        # Build and peak: typically Tuesday and Thursday
        quality_days = [1, 3]  # Tuesday, Thursday
        return day in quality_days and day in train_days

    def _get_quality_session(
        self,
        phase: TrainingPhase,
        week_in_phase: int,
    ) -> tuple:
        """Get quality session type based on phase and progression."""
        if phase == TrainingPhase.BUILD:
            if week_in_phase <= 2:
                return ("tempo", "Tempo run: 20-25 min at tempo pace", "Zone 3-4")
            else:
                return ("threshold", "Threshold intervals: 4x6 min at threshold", "Zone 4")

        elif phase == TrainingPhase.PEAK:
            return ("intervals", "Race-pace intervals: 6x1000m at goal pace", "Zone 4-5")

        elif phase == TrainingPhase.TAPER:
            return ("tempo", "Short tempo: 15 min at tempo pace", "Zone 3-4")

        return ("tempo", "Tempo run", "Zone 3-4")

    def _get_long_run_duration(
        self,
        phase: TrainingPhase,
        week_in_phase: int,
        is_cutback: bool,
    ) -> int:
        """Calculate long run duration."""
        base_duration = 60

        if phase == TrainingPhase.BASE:
            duration = base_duration + (week_in_phase * 5)
        elif phase == TrainingPhase.BUILD:
            duration = base_duration + 15 + (week_in_phase * 5)
        elif phase == TrainingPhase.PEAK:
            duration = base_duration + 30
        else:  # Taper
            duration = base_duration

        if is_cutback:
            duration = int(duration * 0.7)

        # Cap at 2.5 hours
        return min(duration, 150)

    def _get_phase_focus(
        self,
        phase: TrainingPhase,
        week_in_phase: int,
        total_weeks: int,
    ) -> str:
        """Get the focus description for a training phase."""
        focuses = {
            TrainingPhase.BASE: "Aerobic endurance and running economy",
            TrainingPhase.BUILD: "Progressive load increase and lactate threshold",
            TrainingPhase.PEAK: "Race-specific fitness and neuromuscular power",
            TrainingPhase.TAPER: "Recovery and freshness for race day",
            TrainingPhase.RECOVERY: "Active recovery and regeneration",
        }
        return focuses.get(phase, "General fitness")

    def _get_week_notes(
        self,
        phase: TrainingPhase,
        week_in_phase: int,
        total_weeks: int,
    ) -> str:
        """Generate notes for the training week."""
        notes = {
            TrainingPhase.BASE: "Focus on easy, conversational pace. Build your aerobic base.",
            TrainingPhase.BUILD: "Listen to your body. Quality over quantity.",
            TrainingPhase.PEAK: "Race-specific work. Stay confident and focused.",
            TrainingPhase.TAPER: "Trust your training. Stay rested and fresh.",
        }

        base_note = notes.get(phase, "")

        if week_in_phase == 1:
            return f"{base_note} First week of {phase.value} phase - ease into it."
        elif week_in_phase == total_weeks:
            return f"{base_note} Last week of {phase.value} - transition coming."

        return base_note

    def _estimate_target_ctl(self, distance: str) -> float:
        """Estimate target CTL for a race distance."""
        targets = {
            "5k": 40,
            "10k": 50,
            "half": 60,
            "marathon": 70,
            "ultra": 80,
        }
        return targets.get(distance, 50)

    def _format_athlete_context(self, context: Dict[str, Any]) -> str:
        """Format athlete context for prompt injection."""
        parts = []

        if context.get("current_ctl"):
            parts.append(f"Current CTL (fitness): {context['current_ctl']}")
        if context.get("current_atl"):
            parts.append(f"Current ATL (fatigue): {context['current_atl']}")
        if context.get("recent_weekly_load"):
            parts.append(f"Recent weekly load: {context['recent_weekly_load']}")
        if context.get("max_hr"):
            parts.append(f"Max HR: {context['max_hr']} bpm")
        if context.get("threshold_hr"):
            parts.append(f"Threshold HR: {context['threshold_hr']} bpm")

        return "\n".join(parts) if parts else "No athlete context available"

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        # Try to find JSON in the response
        try:
            # First try direct parse
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        import re
        json_pattern = r'```(?:json)?\s*\n?([\s\S]*?)\n?```'
        matches = re.findall(json_pattern, response)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # Try to find JSON object in text
        start_idx = response.find('{')
        end_idx = response.rfind('}')

        if start_idx != -1 and end_idx != -1:
            try:
                return json.loads(response[start_idx:end_idx + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse JSON from response: {response[:200]}...")


class PlanGenerationError(Exception):
    """Exception raised when plan generation fails."""
    pass


# Synchronous wrapper for non-async contexts
def generate_plan_sync(
    goal: RaceGoal,
    athlete_context: AthleteContext,
    constraints: Optional[PlanConstraints] = None,
) -> TrainingPlan:
    """
    Synchronous wrapper for plan generation.

    Uses asyncio to run the async plan generation.
    """
    import asyncio

    agent = PlanAgent()

    # Get or create event loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        # If we're already in an async context, create a new loop in a thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                agent.generate_plan(goal, athlete_context, constraints)
            )
            return future.result()
    else:
        return asyncio.run(agent.generate_plan(goal, athlete_context, constraints))
