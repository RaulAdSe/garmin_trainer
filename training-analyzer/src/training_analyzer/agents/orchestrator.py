"""
Multi-Agent Orchestrator for the Reactive Training App.

Coordinates between different agents to handle complex multi-step tasks
that require analysis, planning, and workout design.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END

from .base import BaseAgent, AgentMetrics
from .analysis_agent import AnalysisAgent, AnalysisState
from .plan_agent import PlanAgent, PlanState
from .workout_agent import WorkoutDesignAgent

from ..llm.providers import ModelType
from ..models.athlete_context import AthleteContext
from ..models.plans import TrainingPlan
from ..models.workouts import StructuredWorkout


class TaskType(str, Enum):
    """Types of tasks the orchestrator can handle."""
    ANALYZE_WORKOUT = "analyze_workout"
    GENERATE_PLAN = "generate_plan"
    DESIGN_WORKOUT = "design_workout"
    ANALYZE_AND_SUGGEST = "analyze_and_suggest"
    PLAN_NEXT_WEEK = "plan_next_week"
    FULL_COACHING = "full_coaching"


@dataclass
class OrchestratorRequest:
    """Request for the orchestrator."""
    task_type: TaskType
    athlete_context: Dict[str, Any]
    task_data: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorResponse:
    """Response from the orchestrator."""
    success: bool
    task_type: TaskType
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    metrics: Optional[Dict[str, Any]] = None


class OrchestratorState(TypedDict):
    """State for the orchestrator workflow."""
    # Input
    task_type: str
    athlete_context: Dict[str, Any]
    task_data: Dict[str, Any]
    options: Dict[str, Any]

    # Processing state
    current_step: str
    completed_steps: List[str]
    errors: List[str]

    # Intermediate results
    analysis_result: Optional[Dict[str, Any]]
    plan_result: Optional[Dict[str, Any]]
    workout_result: Optional[Dict[str, Any]]

    # Final output
    final_result: Optional[Dict[str, Any]]


class AgentOrchestrator(BaseAgent[OrchestratorState]):
    """
    Orchestrates multiple agents to complete complex coaching tasks.

    This orchestrator can:
    1. Route simple tasks to the appropriate agent
    2. Chain agents together for multi-step tasks
    3. Aggregate results from multiple agents
    4. Handle errors gracefully
    """

    def __init__(
        self,
        analysis_agent: Optional[AnalysisAgent] = None,
        plan_agent: Optional[PlanAgent] = None,
        workout_agent: Optional[WorkoutDesignAgent] = None,
    ):
        """
        Initialize the orchestrator with optional pre-configured agents.

        Args:
            analysis_agent: Pre-configured analysis agent
            plan_agent: Pre-configured plan agent
            workout_agent: Pre-configured workout design agent
        """
        super().__init__(model_type=ModelType.SMART)

        self._analysis_agent = analysis_agent
        self._plan_agent = plan_agent
        self._workout_agent = workout_agent

    @property
    def analysis_agent(self) -> AnalysisAgent:
        """Lazy-load analysis agent."""
        if self._analysis_agent is None:
            self._analysis_agent = AnalysisAgent(llm_client=self.llm_client)
        return self._analysis_agent

    @property
    def plan_agent(self) -> PlanAgent:
        """Lazy-load plan agent."""
        if self._plan_agent is None:
            self._plan_agent = PlanAgent(llm_client=self.llm_client)
        return self._plan_agent

    @property
    def workout_agent(self) -> WorkoutDesignAgent:
        """Lazy-load workout agent."""
        if self._workout_agent is None:
            self._workout_agent = WorkoutDesignAgent(llm_client=self.llm_client)
        return self._workout_agent

    def _build_graph(self) -> StateGraph:
        """Build the orchestrator workflow graph."""
        workflow = StateGraph(OrchestratorState)

        # Add nodes
        workflow.add_node("route_task", self._route_task)
        workflow.add_node("run_analysis", self._run_analysis)
        workflow.add_node("run_plan_generation", self._run_plan_generation)
        workflow.add_node("run_workout_design", self._run_workout_design)
        workflow.add_node("aggregate_results", self._aggregate_results)

        # Set entry point
        workflow.set_entry_point("route_task")

        # Add conditional edges from router
        workflow.add_conditional_edges(
            "route_task",
            self._determine_next_step,
            {
                "analysis": "run_analysis",
                "plan": "run_plan_generation",
                "workout": "run_workout_design",
                "done": END,
            }
        )

        # Add edges from agent nodes to aggregation
        workflow.add_edge("run_analysis", "aggregate_results")
        workflow.add_edge("run_plan_generation", "aggregate_results")
        workflow.add_edge("run_workout_design", "aggregate_results")

        # Add conditional edge from aggregation (may need more steps)
        workflow.add_conditional_edges(
            "aggregate_results",
            self._check_if_complete,
            {
                "continue": "route_task",
                "done": END,
            }
        )

        return workflow.compile()

    def _route_task(self, state: OrchestratorState) -> OrchestratorState:
        """Route the task to the appropriate agent(s)."""
        task_type = TaskType(state["task_type"])
        completed = state.get("completed_steps", [])

        # Determine next step based on task type and progress
        if task_type == TaskType.ANALYZE_WORKOUT:
            if "analysis" not in completed:
                state["current_step"] = "analysis"
            else:
                state["current_step"] = "done"

        elif task_type == TaskType.GENERATE_PLAN:
            if "plan" not in completed:
                state["current_step"] = "plan"
            else:
                state["current_step"] = "done"

        elif task_type == TaskType.DESIGN_WORKOUT:
            if "workout" not in completed:
                state["current_step"] = "workout"
            else:
                state["current_step"] = "done"

        elif task_type == TaskType.ANALYZE_AND_SUGGEST:
            # First analyze, then suggest workout
            if "analysis" not in completed:
                state["current_step"] = "analysis"
            elif "workout" not in completed:
                state["current_step"] = "workout"
            else:
                state["current_step"] = "done"

        elif task_type == TaskType.PLAN_NEXT_WEEK:
            # Generate a plan for the upcoming week
            if "plan" not in completed:
                state["current_step"] = "plan"
            else:
                state["current_step"] = "done"

        elif task_type == TaskType.FULL_COACHING:
            # Full coaching: analyze recent, generate plan, suggest workout
            if "analysis" not in completed:
                state["current_step"] = "analysis"
            elif "plan" not in completed:
                state["current_step"] = "plan"
            elif "workout" not in completed:
                state["current_step"] = "workout"
            else:
                state["current_step"] = "done"

        else:
            state["current_step"] = "done"
            state["errors"] = state.get("errors", []) + [f"Unknown task type: {task_type}"]

        return state

    def _determine_next_step(self, state: OrchestratorState) -> str:
        """Determine the next step based on current state."""
        current = state.get("current_step", "done")
        if current == "analysis":
            return "analysis"
        elif current == "plan":
            return "plan"
        elif current == "workout":
            return "workout"
        else:
            return "done"

    def _run_analysis(self, state: OrchestratorState) -> OrchestratorState:
        """Run the analysis agent."""
        try:
            workout_data = state.get("task_data", {}).get("workout_data", {})
            athlete_context = state.get("athlete_context", {})
            similar_workouts = state.get("task_data", {}).get("similar_workouts", [])

            # Run analysis
            result = self.analysis_agent.analyze(
                workout_data=workout_data,
                athlete_context=athlete_context,
                similar_workouts=similar_workouts,
            )

            state["analysis_result"] = result
            state["completed_steps"] = state.get("completed_steps", []) + ["analysis"]

        except Exception as e:
            state["errors"] = state.get("errors", []) + [f"Analysis error: {str(e)}"]

        return state

    def _run_plan_generation(self, state: OrchestratorState) -> OrchestratorState:
        """Run the plan generation agent."""
        try:
            goal = state.get("task_data", {}).get("goal", {})
            constraints = state.get("task_data", {}).get("constraints", {})
            athlete_context = state.get("athlete_context", {})

            # Convert to unified AthleteContext format
            plan_context = AthleteContext(
                ctl=athlete_context.get("ctl", 40.0),
                atl=athlete_context.get("atl", 40.0),
                tsb=athlete_context.get("tsb", 0.0),
                max_hr=athlete_context.get("max_hr", 185),
                rest_hr=athlete_context.get("rest_hr", 55),
                threshold_hr=athlete_context.get("lthr", athlete_context.get("threshold_hr", 165)),
            )

            # Run plan generation
            result = self.plan_agent.generate_plan(
                goal=goal,
                context=plan_context,
                constraints=constraints,
            )

            state["plan_result"] = result
            state["completed_steps"] = state.get("completed_steps", []) + ["plan"]

        except Exception as e:
            state["errors"] = state.get("errors", []) + [f"Plan generation error: {str(e)}"]

        return state

    def _run_workout_design(self, state: OrchestratorState) -> OrchestratorState:
        """Run the workout design agent."""
        try:
            workout_request = state.get("task_data", {}).get("workout_request", {})
            athlete_context = state.get("athlete_context", {})

            # Convert to unified AthleteContext format
            workout_context = AthleteContext(
                max_hr=athlete_context.get("max_hr", 185),
                rest_hr=athlete_context.get("rest_hr", 55),
                threshold_hr=athlete_context.get("lthr", athlete_context.get("threshold_hr", 165)),
                ctl=athlete_context.get("ctl", 40.0),
                atl=athlete_context.get("atl", 40.0),
                tsb=athlete_context.get("tsb", 0.0),
            )

            # Run workout design
            result = self.workout_agent.design_workout(
                request=workout_request,
                context=workout_context,
            )

            state["workout_result"] = result
            state["completed_steps"] = state.get("completed_steps", []) + ["workout"]

        except Exception as e:
            state["errors"] = state.get("errors", []) + [f"Workout design error: {str(e)}"]

        return state

    def _aggregate_results(self, state: OrchestratorState) -> OrchestratorState:
        """Aggregate results from all completed steps."""
        final = {}

        if state.get("analysis_result"):
            final["analysis"] = state["analysis_result"]

        if state.get("plan_result"):
            final["plan"] = state["plan_result"]

        if state.get("workout_result"):
            final["workout"] = state["workout_result"]

        state["final_result"] = final
        return state

    def _check_if_complete(self, state: OrchestratorState) -> str:
        """Check if all required steps are complete."""
        task_type = TaskType(state["task_type"])
        completed = set(state.get("completed_steps", []))

        required = {
            TaskType.ANALYZE_WORKOUT: {"analysis"},
            TaskType.GENERATE_PLAN: {"plan"},
            TaskType.DESIGN_WORKOUT: {"workout"},
            TaskType.ANALYZE_AND_SUGGEST: {"analysis", "workout"},
            TaskType.PLAN_NEXT_WEEK: {"plan"},
            TaskType.FULL_COACHING: {"analysis", "plan", "workout"},
        }

        if required.get(task_type, set()).issubset(completed):
            return "done"
        return "continue"

    def execute(self, request: OrchestratorRequest) -> OrchestratorResponse:
        """
        Execute an orchestration request.

        Args:
            request: The orchestration request

        Returns:
            OrchestratorResponse with results
        """
        self.reset_metrics()

        initial_state: OrchestratorState = {
            "task_type": request.task_type.value,
            "athlete_context": request.athlete_context,
            "task_data": request.task_data,
            "options": request.options,
            "current_step": "",
            "completed_steps": [],
            "errors": [],
            "analysis_result": None,
            "plan_result": None,
            "workout_result": None,
            "final_result": None,
        }

        try:
            # Run the workflow
            final_state = self.graph.invoke(initial_state)

            self.metrics.finish()

            return OrchestratorResponse(
                success=len(final_state.get("errors", [])) == 0,
                task_type=request.task_type,
                results=final_state.get("final_result", {}),
                errors=final_state.get("errors", []),
                metrics=self.metrics.to_dict(),
            )

        except Exception as e:
            self.metrics.finish()

            return OrchestratorResponse(
                success=False,
                task_type=request.task_type,
                results={},
                errors=[str(e)],
                metrics=self.metrics.to_dict(),
            )

    async def execute_async(self, request: OrchestratorRequest) -> OrchestratorResponse:
        """
        Execute an orchestration request asynchronously.

        Args:
            request: The orchestration request

        Returns:
            OrchestratorResponse with results
        """
        # For now, just call the sync version
        # In a real implementation, this would use async agents
        return self.execute(request)


def get_orchestrator() -> AgentOrchestrator:
    """Get a configured orchestrator instance."""
    return AgentOrchestrator()
