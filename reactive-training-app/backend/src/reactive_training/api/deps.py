"""Dependency injection for API routes."""

import sys
from functools import lru_cache
from pathlib import Path

from ..config import get_settings

# Add training-analyzer to path for imports
settings = get_settings()
training_analyzer_path = settings.project_root / "training-analyzer" / "src"
if str(training_analyzer_path) not in sys.path:
    sys.path.insert(0, str(training_analyzer_path))

from training_analyzer.services.coach import CoachService
from training_analyzer.db.database import TrainingDatabase


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
