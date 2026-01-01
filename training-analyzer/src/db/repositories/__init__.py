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
from .strava_repository import StravaRepository, get_strava_repository
from .user_repository import UserRepository, get_user_repository
from .subscription_repository import SubscriptionRepository, get_subscription_repository
from .garmin_credentials_repository import (
    GarminCredentialsRepository,
    get_garmin_credentials_repository,
)
from .ai_usage_repository import AIUsageRepository, get_ai_usage_repository

__all__ = [
    # Base classes
    "Repository",
    "AsyncRepository",
    # Workout and plan repositories
    "WorkoutRepository",
    "PlanRepository",
    "AnalysisCacheRepository",
    # Strava integration
    "StravaRepository",
    "get_strava_repository",
    # User management
    "UserRepository",
    "get_user_repository",
    # Subscription and usage
    "SubscriptionRepository",
    "get_subscription_repository",
    # Garmin integration
    "GarminCredentialsRepository",
    "get_garmin_credentials_repository",
    # AI usage tracking
    "AIUsageRepository",
    "get_ai_usage_repository",
]
