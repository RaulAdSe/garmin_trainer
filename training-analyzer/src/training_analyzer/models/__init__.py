"""Data models for the Reactive Training App."""

# Import the unified AthleteContext from the dedicated module
from .athlete_context import (
    AthleteContext,
    # Backward compatibility aliases
    AnalysisAthleteContext,
    PlanAthleteContext,
    WorkoutAthleteContext,
)

from .analysis import (
    # Enums
    AnalysisStatus,
    WorkoutExecutionRating,
    # Request/Response models
    AnalysisRequest,
    AnalysisResponse,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    RecentWorkoutsResponse,
    RecentWorkoutWithAnalysis,
    # Result models
    WorkoutAnalysisResult,
    WorkoutInsight,
    AnalysisContext,
    # Dataclasses
    WorkoutData,
)

from .plans import (
    # Enums
    PeriodizationType,
    TrainingPhase,
    WorkoutType,
    RaceDistance,
    # Core dataclasses
    RaceGoal,
    PlannedSession,
    TrainingWeek,
    PlanConstraints,
    TrainingPlan,
    PlanAdaptation,
    # Pydantic schemas for API
    GoalInputSchema,
    ConstraintsInputSchema,
    GeneratePlanRequestSchema,
    PlanResponseSchema,
    AdaptPlanRequestSchema,
    # Utility functions
    parse_time_string,
    day_name_to_number,
    parse_goal_input,
    parse_constraints_input,
)

from .workouts import (
    # Enums
    IntensityZone,
    IntervalType,
    WorkoutSport,
    # Core dataclasses
    WorkoutInterval,
    StructuredWorkout,
    WorkoutDesignRequest,
)

__all__ = [
    # Unified AthleteContext (and backward compatibility aliases)
    "AthleteContext",
    "AnalysisAthleteContext",
    "PlanAthleteContext",
    "WorkoutAthleteContext",
    # Analysis Enums
    "AnalysisStatus",
    "WorkoutExecutionRating",
    # Analysis Request/Response models
    "AnalysisRequest",
    "AnalysisResponse",
    "BatchAnalysisRequest",
    "BatchAnalysisResponse",
    "RecentWorkoutsResponse",
    "RecentWorkoutWithAnalysis",
    # Analysis Result models
    "WorkoutAnalysisResult",
    "WorkoutInsight",
    "AnalysisContext",
    # Analysis Dataclasses
    "WorkoutData",
    # Plan Enums
    "PeriodizationType",
    "TrainingPhase",
    "WorkoutType",
    "RaceDistance",
    # Plan Core dataclasses
    "RaceGoal",
    "PlannedSession",
    "TrainingWeek",
    "PlanConstraints",
    "TrainingPlan",
    "PlanAdaptation",
    # Plan Pydantic schemas for API
    "GoalInputSchema",
    "ConstraintsInputSchema",
    "GeneratePlanRequestSchema",
    "PlanResponseSchema",
    "AdaptPlanRequestSchema",
    # Plan Utility functions
    "parse_time_string",
    "day_name_to_number",
    "parse_goal_input",
    "parse_constraints_input",
    # Workout Enums
    "IntensityZone",
    "IntervalType",
    "WorkoutSport",
    # Workout Core dataclasses
    "WorkoutInterval",
    "StructuredWorkout",
    "WorkoutDesignRequest",
]
