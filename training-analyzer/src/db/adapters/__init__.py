"""Database adapters for multi-database support.

This module provides an adapter pattern for database access, enabling
seamless migration from SQLite to PostgreSQL (Supabase) or other backends.

The adapter pattern allows the application to switch between different
database implementations without changing the business logic.

Usage:
    # SQLite (development)
    from src.db.adapters import SQLiteAdapter
    adapter = SQLiteAdapter(db_path="training.db")

    # Supabase/PostgreSQL (production)
    from src.db.adapters import SupabaseAdapter
    adapter = SupabaseAdapter(url=SUPABASE_URL, key=SUPABASE_KEY)

    # Use the adapter
    activities = adapter.get_activities_range(start, end, user_id="user-123")

See DATABASE_SCALING_PLAN.md for the full migration strategy.
"""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Tuple, Generic, TypeVar
from dataclasses import dataclass
from datetime import date, datetime


# Type variable for generic entity types
T = TypeVar("T")


@dataclass
class ActivityMetricsData:
    """Data transfer object for activity metrics.

    This is used by adapters to transfer data between the database
    and the application layer in a database-agnostic way.
    """
    activity_id: str
    date: str
    activity_type: Optional[str] = None
    activity_name: Optional[str] = None
    hrss: Optional[float] = None
    trimp: Optional[float] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    duration_min: Optional[float] = None
    distance_km: Optional[float] = None
    pace_sec_per_km: Optional[float] = None
    zone1_pct: Optional[float] = None
    zone2_pct: Optional[float] = None
    zone3_pct: Optional[float] = None
    zone4_pct: Optional[float] = None
    zone5_pct: Optional[float] = None
    start_time: Optional[str] = None
    sport_type: Optional[str] = None
    avg_power: Optional[int] = None
    max_power: Optional[int] = None
    normalized_power: Optional[int] = None
    tss: Optional[float] = None
    intensity_factor: Optional[float] = None
    variability_index: Optional[float] = None
    avg_speed_kmh: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    cadence: Optional[int] = None
    user_id: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class FitnessMetricsData:
    """Data transfer object for daily fitness metrics."""
    date: str
    daily_load: float
    ctl: float
    atl: float
    tsb: float
    acwr: float
    risk_zone: str
    user_id: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class UserProfileData:
    """Data transfer object for user profile."""
    id: str
    max_hr: Optional[int] = None
    rest_hr: Optional[int] = None
    threshold_hr: Optional[int] = None
    gender: str = "male"
    age: Optional[int] = None
    weight_kg: Optional[float] = None
    timezone: str = "UTC"
    updated_at: Optional[str] = None


class DatabaseAdapter(ABC):
    """Abstract base class for database adapters.

    This interface defines the contract that all database implementations
    must follow, enabling the application to work with different backends
    (SQLite, PostgreSQL/Supabase, etc.) without code changes.

    Key differences between backends:

    SQLite:
        - AUTOINCREMENT for auto-incrementing IDs
        - TEXT for dates (stored as ISO strings)
        - INTEGER for booleans (0/1)
        - No native UUID type
        - File-based, single-writer

    PostgreSQL/Supabase:
        - SERIAL or BIGSERIAL for auto-incrementing IDs
        - DATE, TIMESTAMP, TIMESTAMPTZ for dates
        - BOOLEAN native type
        - UUID native type
        - Client-server, connection pooling
        - Row-Level Security (RLS) for multi-tenancy

    All methods include user_id parameter for multi-tenant support.
    Default "default" user_id maintains backward compatibility.
    """

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the database connection and schema.

        For SQLite: Creates tables if they don't exist.
        For Supabase: Verifies connection and permissions.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the database connection and cleanup resources."""
        pass

    @abstractmethod
    @contextmanager
    def transaction(self):
        """Context manager for database transactions.

        Usage:
            with adapter.transaction():
                adapter.save_activity(...)
                adapter.save_fitness_metrics(...)

        Yields:
            The adapter instance for chaining operations.
        """
        pass

    # =========================================================================
    # Activity Metrics
    # =========================================================================

    @abstractmethod
    def save_activity(
        self,
        activity: ActivityMetricsData,
        user_id: str = "default"
    ) -> ActivityMetricsData:
        """Save or update activity metrics.

        Args:
            activity: The activity data to save
            user_id: User identifier for multi-tenant isolation

        Returns:
            The saved activity (may include generated fields like updated_at)
        """
        pass

    @abstractmethod
    def get_activity(
        self,
        activity_id: str,
        user_id: str = "default"
    ) -> Optional[ActivityMetricsData]:
        """Get a single activity by ID.

        Args:
            activity_id: The activity identifier
            user_id: User identifier for multi-tenant isolation

        Returns:
            The activity if found, None otherwise
        """
        pass

    @abstractmethod
    def get_activities_range(
        self,
        start_date: str,
        end_date: str,
        user_id: str = "default",
        activity_type: Optional[str] = None,
        sport_type: Optional[str] = None
    ) -> List[ActivityMetricsData]:
        """Get activities within a date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            user_id: User identifier for multi-tenant isolation
            activity_type: Optional filter by activity type
            sport_type: Optional filter by sport type

        Returns:
            List of activities ordered by date descending
        """
        pass

    @abstractmethod
    def get_activities_paginated(
        self,
        user_id: str = "default",
        page: int = 1,
        page_size: int = 20,
        activity_type: Optional[str] = None,
        sport_type: Optional[str] = None
    ) -> Tuple[List[ActivityMetricsData], int]:
        """Get paginated activities with total count.

        Args:
            user_id: User identifier for multi-tenant isolation
            page: Page number (1-indexed)
            page_size: Number of items per page
            activity_type: Optional filter by activity type
            sport_type: Optional filter by sport type

        Returns:
            Tuple of (activities list, total count)
        """
        pass

    @abstractmethod
    def delete_activity(
        self,
        activity_id: str,
        user_id: str = "default"
    ) -> bool:
        """Delete an activity by ID.

        Args:
            activity_id: The activity identifier
            user_id: User identifier for multi-tenant isolation

        Returns:
            True if deleted, False if not found
        """
        pass

    # =========================================================================
    # Fitness Metrics
    # =========================================================================

    @abstractmethod
    def save_fitness_metrics(
        self,
        metrics: FitnessMetricsData,
        user_id: str = "default"
    ) -> FitnessMetricsData:
        """Save or update daily fitness metrics.

        Args:
            metrics: The fitness metrics to save
            user_id: User identifier for multi-tenant isolation

        Returns:
            The saved metrics
        """
        pass

    @abstractmethod
    def get_fitness_metrics(
        self,
        date_str: str,
        user_id: str = "default"
    ) -> Optional[FitnessMetricsData]:
        """Get fitness metrics for a specific date.

        Args:
            date_str: The date (YYYY-MM-DD)
            user_id: User identifier for multi-tenant isolation

        Returns:
            The fitness metrics if found, None otherwise
        """
        pass

    @abstractmethod
    def get_fitness_range(
        self,
        start_date: str,
        end_date: str,
        user_id: str = "default"
    ) -> List[FitnessMetricsData]:
        """Get fitness metrics for a date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            user_id: User identifier for multi-tenant isolation

        Returns:
            List of fitness metrics ordered by date descending
        """
        pass

    @abstractmethod
    def get_latest_fitness_metrics(
        self,
        user_id: str = "default"
    ) -> Optional[FitnessMetricsData]:
        """Get the most recent fitness metrics.

        Args:
            user_id: User identifier for multi-tenant isolation

        Returns:
            The latest fitness metrics if any exist
        """
        pass

    # =========================================================================
    # User Profile
    # =========================================================================

    @abstractmethod
    def get_user_profile(
        self,
        user_id: str = "default"
    ) -> UserProfileData:
        """Get user profile with HR zones and settings.

        Args:
            user_id: User identifier

        Returns:
            User profile (with defaults if not found)
        """
        pass

    @abstractmethod
    def save_user_profile(
        self,
        profile: UserProfileData
    ) -> UserProfileData:
        """Save or update user profile.

        Args:
            profile: The profile to save

        Returns:
            The saved profile
        """
        pass

    # =========================================================================
    # Statistics and Aggregations
    # =========================================================================

    @abstractmethod
    def get_daily_load_totals(
        self,
        start_date: str,
        end_date: str,
        user_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Get aggregated daily load totals.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            user_id: User identifier for multi-tenant isolation

        Returns:
            List of dicts with date, total_hrss, total_trimp, activity_count
        """
        pass

    @abstractmethod
    def get_stats(
        self,
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """Get database statistics for a user.

        Args:
            user_id: User identifier for multi-tenant isolation

        Returns:
            Dict with activity count, fitness days, date ranges, etc.
        """
        pass

    # =========================================================================
    # Health Check
    # =========================================================================

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check database health and connectivity.

        Returns:
            Dict with:
                - healthy: bool
                - backend: str (sqlite, postgresql)
                - version: str
                - latency_ms: float
                - details: Any additional info
        """
        pass


# Export the adapter classes
from .sqlite_adapter import SQLiteAdapter
from .supabase_adapter import SupabaseAdapter

__all__ = [
    "DatabaseAdapter",
    "SQLiteAdapter",
    "SupabaseAdapter",
    "ActivityMetricsData",
    "FitnessMetricsData",
    "UserProfileData",
]
