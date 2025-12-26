"""Dependency injection for API routes."""

from functools import lru_cache

from ..config import get_settings
from ..services.coach import CoachService
from ..db.database import TrainingDatabase


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
