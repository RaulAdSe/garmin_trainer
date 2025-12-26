"""LangGraph agents for the Reactive Training App."""

from .base import (
    BaseAgent,
    AgentMetrics,
)

from .analysis_agent import (
    AnalysisAgent,
    AnalysisState,
    build_athlete_context_from_briefing,
    get_similar_workouts,
)

from .plan_agent import (
    PlanAgent,
    PlanState,
    PlanGenerationError,
    generate_plan_sync,
)

from .workout_agent import (
    WorkoutDesignAgent,
    get_workout_agent,
)

from .cycling_agent import (
    CyclingWorkoutAgent,
    CyclingAthleteContext,
    CyclingWorkoutInterval,
    get_cycling_agent,
)

from .swim_agent import (
    SwimWorkoutAgent,
    get_swim_agent,
)

from .triathlon_agent import (
    TriathlonAgent,
    TriathlonAthleteContext,
    BrickWorkout,
    MultiSportDay,
    RaceDistance,
    FatigueCarryoverModel,
    get_triathlon_agent,
)

from .orchestrator import (
    AgentOrchestrator,
    OrchestratorRequest,
    OrchestratorResponse,
    TaskType,
    get_orchestrator,
)

__all__ = [
    # Base Agent
    "BaseAgent",
    "AgentMetrics",
    # Analysis Agent
    "AnalysisAgent",
    "AnalysisState",
    "build_athlete_context_from_briefing",
    "get_similar_workouts",
    # Plan Agent
    "PlanAgent",
    "PlanState",
    "PlanGenerationError",
    "generate_plan_sync",
    # Workout Agent
    "WorkoutDesignAgent",
    "get_workout_agent",
    # Cycling Agent (Phase 3)
    "CyclingWorkoutAgent",
    "CyclingAthleteContext",
    "CyclingWorkoutInterval",
    "get_cycling_agent",
    # Swim Agent (Phase 3)
    "SwimWorkoutAgent",
    "get_swim_agent",
    # Triathlon Agent (Phase 3)
    "TriathlonAgent",
    "TriathlonAthleteContext",
    "BrickWorkout",
    "MultiSportDay",
    "RaceDistance",
    "FatigueCarryoverModel",
    "get_triathlon_agent",
    # Orchestrator
    "AgentOrchestrator",
    "OrchestratorRequest",
    "OrchestratorResponse",
    "TaskType",
    "get_orchestrator",
]
