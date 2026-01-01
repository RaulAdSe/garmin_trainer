"""Services for training analysis."""

from .enrichment import EnrichmentService, get_n8n_db_path
from .coach import CoachService, find_wellness_db
from .base import BaseService, CacheProtocol, PaginationParams, PaginatedResult
from .analysis_service import AnalysisService
from .plan_service import PlanService
from .workout_service import WorkoutService

# Phase 4: Adaptive Training Intelligence
from .adaptation import (
    WorkoutAdaptationEngine,
    WorkoutCompletion,
    PerformanceTrend,
    AdaptationRecommendation,
    WorkoutPrediction,
    AdaptationTrigger,
    AdaptationType,
    get_adaptation_engine,
)
from .fatigue_prediction import (
    FatiguePredictionService,
    DailyReadiness,
    FatiguePrediction,
    ACWRAlert,
    RecoveryEstimate,
    FatigueLevel,
    RecoveryState,
    RiskLevel,
    get_fatigue_service,
)

# Strava integration
from .strava_service import (
    StravaService,
    StravaPreferences,
    StravaSyncStatus,
    format_strava_description_simple,
    format_strava_description_extended,
    format_strava_description_custom,
)

# AI Agentic - Training Pattern Detection
from .training_pattern_service import (
    TrainingPatternService,
    TrainingPatterns,
    get_training_pattern_service,
    reset_training_pattern_service,
)

# AI Agentic - Workout Query Service
from .workout_query_service import (
    WorkoutQueryService,
    WorkoutSummary,
    get_workout_query_service,
    reset_workout_query_service,
)

# Consent service for LLM data sharing
from .consent_service import (
    ConsentService,
    ConsentStatus,
    get_consent_service,
    reset_consent_service,
)

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
    # Phase 4: Adaptation Engine
    "WorkoutAdaptationEngine",
    "WorkoutCompletion",
    "PerformanceTrend",
    "AdaptationRecommendation",
    "WorkoutPrediction",
    "AdaptationTrigger",
    "AdaptationType",
    "get_adaptation_engine",
    # Phase 4: Fatigue Prediction
    "FatiguePredictionService",
    "DailyReadiness",
    "FatiguePrediction",
    "ACWRAlert",
    "RecoveryEstimate",
    "FatigueLevel",
    "RecoveryState",
    "RiskLevel",
    "get_fatigue_service",
    # Strava integration
    "StravaService",
    "StravaPreferences",
    "StravaSyncStatus",
    "format_strava_description_simple",
    "format_strava_description_extended",
    "format_strava_description_custom",
    # AI Agentic - Training Pattern Detection
    "TrainingPatternService",
    "TrainingPatterns",
    "get_training_pattern_service",
    "reset_training_pattern_service",
    # AI Agentic - Workout Query Service
    "WorkoutQueryService",
    "WorkoutSummary",
    "get_workout_query_service",
    "reset_workout_query_service",
    # Consent service for LLM data sharing
    "ConsentService",
    "ConsentStatus",
    "get_consent_service",
    "reset_consent_service",
]
