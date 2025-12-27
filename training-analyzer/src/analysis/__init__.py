"""
Analysis module for training data.

Provides trend analysis, weekly summaries, race goal tracking,
and time-series data condensation for LLM analysis.
"""

from .trends import (
    FitnessTrend,
    PerformanceTrend,
    calculate_fitness_trend,
    calculate_pace_at_hr_trend,
    detect_overtraining_signals,
)
from .weekly import (
    WeeklyAnalysis,
    analyze_week,
    generate_weekly_insights,
)
from .goals import (
    RaceDistance,
    RaceGoal,
    GoalProgress,
    predict_race_time,
    calculate_training_paces,
    assess_goal_progress,
)
from .condensation import (
    CondensedWorkoutData,
    HRSummary,
    PaceSummary,
    ElevationSummary,
    SplitsSummary,
    TrendDirection,
    TerrainType,
    condense_workout_data,
    calculate_hr_summary,
    calculate_pace_summary,
    calculate_elevation_summary,
    calculate_splits_summary,
    extract_insights,
)

__all__ = [
    # Trends
    "FitnessTrend",
    "PerformanceTrend",
    "calculate_fitness_trend",
    "calculate_pace_at_hr_trend",
    "detect_overtraining_signals",
    # Weekly
    "WeeklyAnalysis",
    "analyze_week",
    "generate_weekly_insights",
    # Goals
    "RaceDistance",
    "RaceGoal",
    "GoalProgress",
    "predict_race_time",
    "calculate_training_paces",
    "assess_goal_progress",
    # Condensation (time-series to LLM summary)
    "CondensedWorkoutData",
    "HRSummary",
    "PaceSummary",
    "ElevationSummary",
    "SplitsSummary",
    "TrendDirection",
    "TerrainType",
    "condense_workout_data",
    "calculate_hr_summary",
    "calculate_pace_summary",
    "calculate_elevation_summary",
    "calculate_splits_summary",
    "extract_insights",
]
