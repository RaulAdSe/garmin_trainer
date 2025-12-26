"""AI-powered workout analysis from Garmin data."""

from .db.database import TrainingDatabase, UserProfile, ActivityMetrics, DailyFitnessMetrics
from .metrics import (
    calculate_hrss,
    calculate_trimp,
    FitnessMetrics,
    calculate_fitness_metrics,
    HRZones,
    calculate_hr_zones_karvonen,
    calculate_hr_zones_lthr,
)
from .services.enrichment import EnrichmentService

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Database
    "TrainingDatabase",
    "UserProfile",
    "ActivityMetrics",
    "DailyFitnessMetrics",
    # Metrics - Load
    "calculate_hrss",
    "calculate_trimp",
    # Metrics - Fitness
    "FitnessMetrics",
    "calculate_fitness_metrics",
    # Metrics - Zones
    "HRZones",
    "calculate_hr_zones_karvonen",
    "calculate_hr_zones_lthr",
    # Services
    "EnrichmentService",
]
