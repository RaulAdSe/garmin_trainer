"""Dependency injection for API routes."""

from functools import lru_cache

from ..config import get_settings
from ..services.coach import CoachService
from ..services.auth_service import AuthService, get_auth_service
from ..services.feature_gate import FeatureGateService, get_feature_gate_service
from ..db.database import TrainingDatabase
from ..db.repositories.workout_repository import WorkoutRepository
from ..db.repositories.plan_repository import PlanRepository
from ..db.repositories.analysis_cache_repository import AnalysisCacheRepository
from ..services.consent_service import ConsentService, get_consent_service

# Re-export auth dependencies for convenient imports
from .middleware.auth import (
    CurrentUser,
    get_current_user,
    get_optional_user,
    require_admin,
    get_require_subscription,
)


@lru_cache
def get_training_db() -> TrainingDatabase:
    """Get the training database instance."""
    settings = get_settings()
    db_path = settings.training_db_path
    if db_path and db_path.exists():
        return TrainingDatabase(str(db_path))
    return TrainingDatabase()


@lru_cache
def get_coach_service() -> CoachService:
    """Get the coach service instance."""
    settings = get_settings()
    training_db = get_training_db()
    wellness_db = str(settings.wellness_db_path) if settings.wellness_db_path else None
    return CoachService(training_db=training_db, wellness_db_path=wellness_db)


@lru_cache
def get_workout_repository() -> WorkoutRepository:
    """Get the workout repository instance."""
    settings = get_settings()
    db_path = settings.training_db_path
    if db_path and db_path.exists():
        return WorkoutRepository(str(db_path))
    return WorkoutRepository()


@lru_cache
def get_plan_repository() -> PlanRepository:
    """Get the plan repository instance."""
    settings = get_settings()
    db_path = settings.training_db_path
    if db_path and db_path.exists():
        return PlanRepository(str(db_path))
    return PlanRepository()


@lru_cache
def get_analysis_cache_repository() -> AnalysisCacheRepository:
    """Get the analysis cache repository instance."""
    settings = get_settings()
    db_path = settings.training_db_path
    if db_path and db_path.exists():
        return AnalysisCacheRepository(str(db_path))
    return AnalysisCacheRepository()


def get_consent_service_dep() -> ConsentService:
    """Get the consent service instance for dependency injection."""
    settings = get_settings()
    db_path = settings.training_db_path
    if db_path and db_path.exists():
        return get_consent_service(str(db_path))
    return get_consent_service()
