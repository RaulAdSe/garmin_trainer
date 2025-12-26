"""Repository pattern implementations for database persistence.

This module provides a Repository pattern abstraction for data persistence,
enabling:
- Clean separation between business logic and data access
- Easy swapping of storage backends (in-memory, SQLite, PostgreSQL)
- Thread-safe concurrent access
- Horizontal scaling support
"""

from .base import Repository, AsyncRepository
from .workout_repository import WorkoutRepository
from .plan_repository import PlanRepository
from .analysis_cache_repository import AnalysisCacheRepository

__all__ = [
    "Repository",
    "AsyncRepository",
    "WorkoutRepository",
    "PlanRepository",
    "AnalysisCacheRepository",
]
