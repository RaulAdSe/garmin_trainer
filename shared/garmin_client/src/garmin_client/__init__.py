"""Shared Garmin Connect client for data extraction."""

from garmin_client.api.client import GarminClient
from garmin_client.db.database import Database
from garmin_client.db.models import (
    DailyWellness,
    SleepData,
    HRVData,
    StressData,
    ActivityData,
    TrainingReadiness,
    PersonalBaselines,
)
from garmin_client.baselines import (
    calculate_rolling_average,
    calculate_direction,
    get_personal_baselines,
    calculate_recovery_with_baselines,
    save_baselines,
    get_saved_baselines,
    DirectionIndicator,
)
from garmin_client.causality import (
    Correlation,
    Streak,
    TrendAlert,
    WeeklySummary,
    detect_workout_timing_correlation,
    detect_sleep_consistency_impact,
    detect_step_count_correlation,
    detect_alcohol_nights,
    get_all_correlations,
    calculate_green_day_streak,
    calculate_sleep_consistency_streak,
    calculate_step_goal_streak,
    get_all_streaks,
    detect_hrv_trend,
    detect_sleep_trend,
    detect_recovery_trend,
    get_all_trend_alerts,
    generate_weekly_summary,
)

__version__ = "0.1.0"

__all__ = [
    "GarminClient",
    "Database",
    "DailyWellness",
    "SleepData",
    "HRVData",
    "StressData",
    "ActivityData",
    "TrainingReadiness",
    "PersonalBaselines",
    "calculate_rolling_average",
    "calculate_direction",
    "get_personal_baselines",
    "calculate_recovery_with_baselines",
    "save_baselines",
    "get_saved_baselines",
    "DirectionIndicator",
    # Phase 4: Causality engine
    "Correlation",
    "Streak",
    "TrendAlert",
    "WeeklySummary",
    "detect_workout_timing_correlation",
    "detect_sleep_consistency_impact",
    "detect_step_count_correlation",
    "detect_alcohol_nights",
    "get_all_correlations",
    "calculate_green_day_streak",
    "calculate_sleep_consistency_streak",
    "calculate_step_goal_streak",
    "get_all_streaks",
    "detect_hrv_trend",
    "detect_sleep_trend",
    "detect_recovery_trend",
    "get_all_trend_alerts",
    "generate_weekly_summary",
]
