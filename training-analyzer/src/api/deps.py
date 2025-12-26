"""Dependency injection for API routes."""

from functools import lru_cache

from ..config import get_settings
from ..services.coach import CoachService
from ..db.database import TrainingDatabase
from ..db.repositories.workout_repository import WorkoutRepository
from ..db.repositories.plan_repository import PlanRepository
from ..db.repositories.analysis_cache_repository import AnalysisCacheRepository


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
