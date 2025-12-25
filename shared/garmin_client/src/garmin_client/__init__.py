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
]
