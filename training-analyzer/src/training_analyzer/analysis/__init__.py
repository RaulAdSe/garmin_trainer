"""
Analysis module for training data.

Provides trend analysis, weekly summaries, and race goal tracking.
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
]
