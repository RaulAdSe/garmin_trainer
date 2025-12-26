"""SQLite-backed repository for structured workouts.

Replaces the in-memory `_workout_store: Dict[str, StructuredWorkout] = {}` from routes/workouts.py
with persistent storage in SQLite, enabling:
- Data persistence across server restarts
- Concurrent access safety
- Support for horizontal scaling
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from contextlib import contextmanager

from .base import Repository
from ...models.workouts import (
    StructuredWorkout,
    WorkoutInterval,
    WorkoutSport,
    IntervalType,
    IntensityZone,
)


class WorkoutRepository(Repository[StructuredWorkout]):
    """
    SQLite-backed repository for StructuredWorkout entities.

    Provides persistent storage for workouts designed by the workout agent,
    replacing in-memory storage with database persistence.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the workout repository.

        Args:
            db_path: Path to SQLite database file. If None, uses the default
                    training.db in the training-analyzer directory.
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            # Use the same default path as TrainingDatabase
            import os
            env_path = os.environ.get("TRAINING_DB_PATH")
            if env_path:
                self.db_path = Path(env_path)
            else:
                self.db_path = Path(__file__).parent.parent.parent.parent.parent / "training.db"

        self._ensure_table_exists()

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_table_exists(self):
        """Ensure the workouts table exists."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workouts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    sport TEXT NOT NULL DEFAULT 'running',
                    intervals_json TEXT NOT NULL,
                    estimated_duration_min INTEGER NOT NULL,
                    estimated_distance_m INTEGER,
                    estimated_load REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_workouts_created_at
                ON workouts(created_at)
            """)

    def _workout_to_row(self, workout: StructuredWorkout) -> dict:
        """Convert a StructuredWorkout to a database row dictionary."""
        intervals_json = json.dumps([i.to_dict() for i in workout.intervals])
        return {
            "id": workout.id,
            "name": workout.name,
            "description": workout.description,
            "sport": workout.sport.value if isinstance(workout.sport, WorkoutSport) else workout.sport,
            "intervals_json": intervals_json,
            "estimated_duration_min": workout.estimated_duration_min,
            "estimated_distance_m": workout.estimated_distance_m,
            "estimated_load": workout.estimated_load,
            "created_at": workout.created_at.isoformat() if workout.created_at else datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

    def _row_to_workout(self, row: sqlite3.Row) -> StructuredWorkout:
        """Convert a database row to a StructuredWorkout."""
        intervals_data = json.loads(row["intervals_json"])
        intervals = [WorkoutInterval.from_dict(i) for i in intervals_data]

        created_at = row["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return StructuredWorkout(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            sport=WorkoutSport(row["sport"]),
            intervals=intervals,
            estimated_duration_min=row["estimated_duration_min"],
            estimated_distance_m=row["estimated_distance_m"],
            estimated_load=row["estimated_load"] or 0.0,
            created_at=created_at,
        )

    def save(self, entity: StructuredWorkout) -> StructuredWorkout:
        """
        Save a workout to the database.

        If the workout already exists (by ID), it will be updated.
        Otherwise, a new workout will be created.

        Args:
            entity: The workout to save

        Returns:
            The saved workout
        """
        row = self._workout_to_row(entity)

        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO workouts
                (id, name, description, sport, intervals_json,
                 estimated_duration_min, estimated_distance_m, estimated_load,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["id"],
                row["name"],
                row["description"],
                row["sport"],
                row["intervals_json"],
                row["estimated_duration_min"],
                row["estimated_distance_m"],
                row["estimated_load"],
                row["created_at"],
                row["updated_at"],
            ))

        return entity

    def get(self, entity_id: str) -> Optional[StructuredWorkout]:
        """
        Retrieve a workout by its ID.

        Args:
            entity_id: The workout ID

        Returns:
            The workout if found, None otherwise
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM workouts WHERE id = ?",
                (entity_id,)
            ).fetchone()

            if row:
                return self._row_to_workout(row)
            return None

    def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        **filters
    ) -> List[StructuredWorkout]:
        """
        Retrieve all workouts matching the given filters.

        Args:
            limit: Maximum number of workouts to return
            offset: Number of workouts to skip
            **filters: Additional filter criteria:
                - sport: Filter by sport type
                - min_duration: Minimum duration in minutes
                - max_duration: Maximum duration in minutes

        Returns:
            List of matching workouts, ordered by creation time (newest first)
        """
        query = "SELECT * FROM workouts WHERE 1=1"
        params = []

        # Apply filters
        if "sport" in filters:
            query += " AND sport = ?"
            params.append(filters["sport"])

        if "min_duration" in filters:
            query += " AND estimated_duration_min >= ?"
            params.append(filters["min_duration"])

        if "max_duration" in filters:
            query += " AND estimated_duration_min <= ?"
            params.append(filters["max_duration"])

        # Order by creation time, newest first
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_workout(row) for row in rows]

    def delete(self, entity_id: str) -> bool:
        """
        Delete a workout by its ID.

        Args:
            entity_id: The workout ID to delete

        Returns:
            True if the workout was deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM workouts WHERE id = ?",
                (entity_id,)
            )
            return cursor.rowcount > 0

    def exists(self, entity_id: str) -> bool:
        """
        Check if a workout exists by its ID.

        Args:
            entity_id: The workout ID to check

        Returns:
            True if the workout exists, False otherwise
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM workouts WHERE id = ?",
                (entity_id,)
            ).fetchone()
            return row is not None

    def count(self, **filters) -> int:
        """
        Count workouts matching the given filters.

        Args:
            **filters: Filter criteria (same as get_all)

        Returns:
            Number of matching workouts
        """
        query = "SELECT COUNT(*) as cnt FROM workouts WHERE 1=1"
        params = []

        if "sport" in filters:
            query += " AND sport = ?"
            params.append(filters["sport"])

        if "min_duration" in filters:
            query += " AND estimated_duration_min >= ?"
            params.append(filters["min_duration"])

        if "max_duration" in filters:
            query += " AND estimated_duration_min <= ?"
            params.append(filters["max_duration"])

        with self._get_connection() as conn:
            row = conn.execute(query, params).fetchone()
            return row["cnt"]

    def get_recent(self, days: int = 7, limit: int = 20) -> List[StructuredWorkout]:
        """
        Get workouts created in the last N days.

        Args:
            days: Number of days to look back
            limit: Maximum number of workouts to return

        Returns:
            List of recent workouts
        """
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM workouts
                WHERE created_at >= datetime('now', '-' || ? || ' days')
                ORDER BY created_at DESC
                LIMIT ?
            """, (days, limit)).fetchall()
            return [self._row_to_workout(row) for row in rows]

    def get_by_sport(self, sport: str, limit: int = 20) -> List[StructuredWorkout]:
        """
        Get workouts for a specific sport.

        Args:
            sport: Sport type ('running', 'cycling', 'swimming')
            limit: Maximum number of workouts to return

        Returns:
            List of workouts for the given sport
        """
        return self.get_all(limit=limit, sport=sport)


# Singleton instance for dependency injection
_workout_repository: Optional[WorkoutRepository] = None


def get_workout_repository() -> WorkoutRepository:
    """Get or create the singleton WorkoutRepository instance."""
    global _workout_repository
    if _workout_repository is None:
        _workout_repository = WorkoutRepository()
    return _workout_repository
