"""Flexible workout query service for the AI agentic architecture.

This service provides parameterized, safe SQL queries for the AI agent
to query workout data on-demand. It's designed to be used as a LangChain
tool backend.

Part of Phase 1: Core Query Tools for the agentic AI system.
See: docs/ai-agentic-architecture.md
"""

import os
import sqlite3
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseService


logger = logging.getLogger(__name__)


# Valid values for filtering
VALID_SPORT_TYPES = {"running", "cycling", "strength", "swimming", "hiking", "walking"}
VALID_WORKOUT_TYPES = {"easy", "tempo", "long", "intervals", "recovery", "race", "threshold"}
VALID_ORDER_COLUMNS = {
    "start_time", "date", "duration_min", "distance_km",
    "hrss", "avg_hr", "activity_name"
}


@dataclass
class WorkoutSummary:
    """Structured workout summary for AI consumption.

    Contains the core fields needed for the AI to understand and reason
    about a workout.
    """
    activity_id: str
    start_time: Optional[str]
    sport_type: Optional[str]
    duration_seconds: Optional[float]
    distance_meters: Optional[float]
    avg_hr: Optional[int]
    max_hr: Optional[int]
    training_load: Optional[float]
    workout_type: Optional[str]
    title: Optional[str]
    laps: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "activity_id": self.activity_id,
            "start_time": self.start_time,
            "sport_type": self.sport_type,
            "duration_seconds": self.duration_seconds,
            "distance_meters": self.distance_meters,
            "avg_hr": self.avg_hr,
            "max_hr": self.max_hr,
            "training_load": self.training_load,
            "workout_type": self.workout_type,
            "title": self.title,
        }
        if self.laps is not None:
            result["laps"] = self.laps
        return result


class WorkoutQueryService(BaseService):
    """
    Flexible workout query service for the AI agentic system.

    Provides parameterized, safe SQL queries that the AI can use to
    query workout data on-demand. This enables the AI to answer questions
    like "Show my last 5 tempo runs" or "What did I do last week?"
    without pre-loading all data into the prompt.

    Key features:
    - Parameterized queries (no SQL injection risk)
    - Flexible filtering by sport, date, workout type
    - Pagination with limit/offset
    - Optional lap data inclusion
    - User-scoped queries for multi-tenant support

    Usage:
        service = get_workout_query_service()
        workouts = service.query(
            sport_type="running",
            workout_type="tempo",
            limit=5
        )
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        Initialize the workout query service.

        Args:
            db_path: Path to SQLite database file. If None, uses the default
                    training.db location (TRAINING_DB_PATH env or default path).
        """
        super().__init__(logger=logger)

        if db_path:
            self.db_path = Path(db_path)
        else:
            # Use the same default path as TrainingDatabase
            env_path = os.environ.get("TRAINING_DB_PATH")
            if env_path:
                self.db_path = Path(env_path)
            else:
                # Path: training-analyzer/src/services/workout_query_service.py
                # Go up 2 levels to training-analyzer/, then add training.db
                self.db_path = Path(__file__).parent.parent.parent / "training.db"

        self._logger.info(f"WorkoutQueryService initialized with db_path: {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def query(
        self,
        sport_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        workout_type: Optional[str] = None,
        limit: int = 10,
        include_laps: bool = False,
        order_by: str = "start_time",
        order_desc: bool = True,
        user_id: Optional[str] = None,
        **kwargs  # Ignore extra args from tool calling
    ) -> List[Dict[str, Any]]:
        """
        Query workouts with flexible filters.

        This is the main method for the AI agent to query workout data.
        All parameters are optional and can be combined.

        Args:
            sport_type: Filter by sport type. Valid values:
                       "running", "cycling", "strength", "swimming"
            date_from: Start date (inclusive) in ISO format YYYY-MM-DD.
                      Example: "2024-01-01"
            date_to: End date (inclusive) in ISO format YYYY-MM-DD.
                    Example: "2024-01-31"
            workout_type: Filter by workout type. Valid values:
                         "easy", "tempo", "long", "intervals", "recovery", "race"
            limit: Maximum number of results to return. Default 10, max 100.
            include_laps: Whether to include lap/split data for each workout.
                         Note: Lap data may not be available for all workouts.
            order_by: Column to order results by. Valid values:
                     "start_time" (default), "date", "duration_min",
                     "distance_km", "hrss", "avg_hr"
            order_desc: If True (default), order descending (newest first).
                       If False, order ascending (oldest first).
            user_id: Filter by user ID for multi-tenant support.
                    Currently not implemented (single-user mode).

        Returns:
            List of workout dictionaries with keys:
            - activity_id: Unique identifier for the workout
            - start_time: ISO timestamp when workout started
            - sport_type: Type of sport (running, cycling, etc.)
            - duration_seconds: Total duration in seconds
            - distance_meters: Total distance in meters
            - avg_hr: Average heart rate (bpm)
            - max_hr: Maximum heart rate (bpm)
            - training_load: HRSS/TRIMP training load score
            - workout_type: Type of workout (easy, tempo, etc.)
            - title: Workout name/title
            - laps: (optional) List of lap data if include_laps=True

        Examples:
            # Get last 5 tempo runs
            query(workout_type="tempo", sport_type="running", limit=5)

            # Get all workouts from last week
            query(date_from="2024-01-08", date_to="2024-01-14")

            # Get longest runs this month
            query(sport_type="running", order_by="duration_min", limit=10)
        """
        # Validate and sanitize inputs
        limit = min(max(1, limit), 100)  # Clamp to 1-100

        # Validate order_by to prevent SQL injection
        if order_by not in VALID_ORDER_COLUMNS:
            self._logger.warning(f"Invalid order_by '{order_by}', defaulting to 'start_time'")
            order_by = "start_time"

        # Map order_by to actual column name if needed
        order_column = order_by
        if order_by == "start_time" and order_by not in ["date"]:
            # Use start_time if available, fall back to date
            order_column = "COALESCE(start_time, date)"

        # Build the query with parameterized values
        # Note: We query from activity_metrics table (the main activity table)
        query = """
            SELECT
                activity_id,
                start_time,
                sport_type,
                duration_min,
                distance_km,
                avg_hr,
                max_hr,
                hrss as training_load,
                activity_type as workout_type,
                activity_name as title
            FROM activity_metrics
            WHERE 1=1
        """
        params: List[Any] = []

        # Add filters with parameterized queries
        if sport_type:
            sport_type_lower = sport_type.lower()
            if sport_type_lower in VALID_SPORT_TYPES:
                query += " AND LOWER(sport_type) = ?"
                params.append(sport_type_lower)
            else:
                self._logger.warning(f"Invalid sport_type: {sport_type}")

        if date_from:
            # Validate date format
            try:
                datetime.strptime(date_from, "%Y-%m-%d")
                query += " AND date >= ?"
                params.append(date_from)
            except ValueError:
                self._logger.warning(f"Invalid date_from format: {date_from}")

        if date_to:
            # Validate date format
            try:
                datetime.strptime(date_to, "%Y-%m-%d")
                query += " AND date <= ?"
                params.append(date_to)
            except ValueError:
                self._logger.warning(f"Invalid date_to format: {date_to}")

        if workout_type:
            workout_type_lower = workout_type.lower()
            if workout_type_lower in VALID_WORKOUT_TYPES:
                # activity_type in activity_metrics may contain values like "running", "cycling"
                # but we might also have a specific workout_type field or need to infer
                query += " AND LOWER(activity_type) = ?"
                params.append(workout_type_lower)
            else:
                self._logger.warning(f"Invalid workout_type: {workout_type}")

        # Note: user_id filtering is not yet implemented
        # When multi-tenant support is added, add:
        # if user_id:
        #     query += " AND user_id = ?"
        #     params.append(user_id)

        # Add ordering - use safe column name (already validated)
        order_direction = "DESC" if order_desc else "ASC"
        query += f" ORDER BY {order_column} {order_direction}"

        # Add limit
        query += " LIMIT ?"
        params.append(limit)

        # Execute query
        try:
            with self._get_connection() as conn:
                rows = conn.execute(query, params).fetchall()

                workouts = []
                for row in rows:
                    workout = WorkoutSummary(
                        activity_id=row["activity_id"],
                        start_time=row["start_time"],
                        sport_type=row["sport_type"],
                        # Convert duration from minutes to seconds
                        duration_seconds=(
                            row["duration_min"] * 60
                            if row["duration_min"] is not None
                            else None
                        ),
                        # Convert distance from km to meters
                        distance_meters=(
                            row["distance_km"] * 1000
                            if row["distance_km"] is not None
                            else None
                        ),
                        avg_hr=row["avg_hr"],
                        max_hr=row["max_hr"],
                        training_load=row["training_load"],
                        workout_type=row["workout_type"],
                        title=row["title"],
                        laps=None,
                    )

                    # Fetch laps if requested
                    if include_laps:
                        workout.laps = self._get_laps_for_activity(
                            conn, row["activity_id"]
                        )

                    workouts.append(workout.to_dict())

                self._logger.debug(
                    f"Query returned {len(workouts)} workouts "
                    f"(sport={sport_type}, type={workout_type}, limit={limit})"
                )

                return workouts

        except sqlite3.Error as e:
            self._logger.error(f"Database error in query: {e}")
            raise

    def _get_laps_for_activity(
        self,
        conn: sqlite3.Connection,
        activity_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get lap/split data for an activity.

        Note: The activity_laps table is not yet implemented in the schema.
        This method is a placeholder that returns an empty list.
        When the table is added, this will be updated to query lap data.

        Args:
            conn: Database connection
            activity_id: The activity ID to get laps for

        Returns:
            List of lap dictionaries, or empty list if no laps found
        """
        # TODO: Implement when activity_laps table is added to schema
        # Expected schema:
        # CREATE TABLE activity_laps (
        #     id INTEGER PRIMARY KEY,
        #     activity_id TEXT NOT NULL,
        #     lap_number INTEGER NOT NULL,
        #     start_time TEXT,
        #     duration_sec REAL,
        #     distance_m REAL,
        #     avg_hr INTEGER,
        #     max_hr INTEGER,
        #     avg_pace_sec_per_km REAL,
        #     elevation_gain_m REAL,
        #     FOREIGN KEY (activity_id) REFERENCES activity_metrics(activity_id)
        # );
        #
        # When implemented:
        # query = """
        #     SELECT * FROM activity_laps
        #     WHERE activity_id = ?
        #     ORDER BY lap_number ASC
        # """
        # rows = conn.execute(query, (activity_id,)).fetchall()
        # return [dict(row) for row in rows]

        return []

    def get_activity_by_id(
        self,
        activity_id: str,
        include_laps: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single activity by its ID.

        Args:
            activity_id: The unique activity identifier
            include_laps: Whether to include lap data

        Returns:
            Workout dictionary or None if not found
        """
        query = """
            SELECT
                activity_id,
                start_time,
                sport_type,
                duration_min,
                distance_km,
                avg_hr,
                max_hr,
                hrss as training_load,
                activity_type as workout_type,
                activity_name as title
            FROM activity_metrics
            WHERE activity_id = ?
        """

        try:
            with self._get_connection() as conn:
                row = conn.execute(query, (activity_id,)).fetchone()

                if row is None:
                    return None

                workout = WorkoutSummary(
                    activity_id=row["activity_id"],
                    start_time=row["start_time"],
                    sport_type=row["sport_type"],
                    duration_seconds=(
                        row["duration_min"] * 60
                        if row["duration_min"] is not None
                        else None
                    ),
                    distance_meters=(
                        row["distance_km"] * 1000
                        if row["distance_km"] is not None
                        else None
                    ),
                    avg_hr=row["avg_hr"],
                    max_hr=row["max_hr"],
                    training_load=row["training_load"],
                    workout_type=row["workout_type"],
                    title=row["title"],
                    laps=None,
                )

                if include_laps:
                    workout.laps = self._get_laps_for_activity(conn, activity_id)

                return workout.to_dict()

        except sqlite3.Error as e:
            self._logger.error(f"Database error in get_activity_by_id: {e}")
            raise

    def get_recent_activities(
        self,
        days: int = 7,
        limit: int = 20,
        sport_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Convenience method to get recent activities.

        Args:
            days: Number of days to look back (default 7)
            limit: Maximum results (default 20)
            sport_type: Optional sport type filter

        Returns:
            List of workout dictionaries
        """
        from datetime import timedelta

        today = datetime.now().date()
        date_from = (today - timedelta(days=days)).isoformat()
        date_to = today.isoformat()

        return self.query(
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            sport_type=sport_type,
        )

    def get_workout_count(
        self,
        sport_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> int:
        """
        Get count of workouts matching the filters.

        Useful for the AI to understand training volume.

        Args:
            sport_type: Optional sport type filter
            date_from: Optional start date (YYYY-MM-DD)
            date_to: Optional end date (YYYY-MM-DD)

        Returns:
            Count of matching workouts
        """
        query = "SELECT COUNT(*) as cnt FROM activity_metrics WHERE 1=1"
        params: List[Any] = []

        if sport_type:
            sport_type_lower = sport_type.lower()
            if sport_type_lower in VALID_SPORT_TYPES:
                query += " AND LOWER(sport_type) = ?"
                params.append(sport_type_lower)

        if date_from:
            try:
                datetime.strptime(date_from, "%Y-%m-%d")
                query += " AND date >= ?"
                params.append(date_from)
            except ValueError:
                pass

        if date_to:
            try:
                datetime.strptime(date_to, "%Y-%m-%d")
                query += " AND date <= ?"
                params.append(date_to)
            except ValueError:
                pass

        try:
            with self._get_connection() as conn:
                row = conn.execute(query, params).fetchone()
                return row["cnt"]
        except sqlite3.Error as e:
            self._logger.error(f"Database error in get_workout_count: {e}")
            raise


# =============================================================================
# Singleton Pattern
# =============================================================================

_workout_query_service: Optional[WorkoutQueryService] = None


def get_workout_query_service(db_path: Optional[str] = None) -> WorkoutQueryService:
    """
    Get or create the singleton WorkoutQueryService instance.

    This follows the same singleton pattern used by other services
    like WorkoutRepository. The singleton is created on first call
    and reused for subsequent calls.

    Args:
        db_path: Optional database path. Only used on first call
                when creating the singleton. Ignored on subsequent calls.

    Returns:
        The WorkoutQueryService singleton instance.

    Example:
        # In LangChain tool:
        @tool
        def query_workouts(...) -> list[dict]:
            service = get_workout_query_service()
            return service.query(...)
    """
    global _workout_query_service

    if _workout_query_service is None:
        _workout_query_service = WorkoutQueryService(db_path=db_path)

    return _workout_query_service


def reset_workout_query_service() -> None:
    """
    Reset the singleton instance.

    Primarily used for testing to ensure a fresh instance.
    """
    global _workout_query_service
    _workout_query_service = None
