"""Services for training analysis."""

from .enrichment import EnrichmentService, get_n8n_db_path
from .coach import CoachService, find_wellness_db
from .base import BaseService, CacheProtocol, PaginationParams, PaginatedResult
from .analysis_service import AnalysisService
from .plan_service import PlanService
from .workout_service import WorkoutService

__all__ = [
    # Core services
    "EnrichmentService",
    "get_n8n_db_path",
    "CoachService",
    "find_wellness_db",
    # Base classes
    "BaseService",
    "CacheProtocol",
    "PaginationParams",
    "PaginatedResult",
    # API services
    "AnalysisService",
    "PlanService",
    "WorkoutService",
]
