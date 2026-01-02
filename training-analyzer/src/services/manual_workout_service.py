"""
Manual Workout Service for RPE-based workout logging.

This service handles workouts logged manually without device data,
using Rate of Perceived Exertion (RPE) to estimate training load.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple
from functools import lru_cache

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


@dataclass
class ManualWorkout:
    """Data class for a manually logged workout."""
    activity_id: str
    user_id: str
    name: str
    activity_type: str
    date: str
    duration_min: int
    distance_km: Optional[float]
    rpe: int
    avg_hr: Optional[int]
    max_hr: Optional[int]
    estimated_load: float
    notes: Optional[str]
    created_at: str


class ManualWorkoutCreate(BaseModel):
    """Request model for creating a manual workout."""
    name: Optional[str] = Field(None, max_length=200)
    activity_type: str = Field(default="running", max_length=50)
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    duration_min: int = Field(..., ge=1, le=720, description="Duration in minutes")
    distance_km: Optional[float] = Field(None, ge=0, le=500, description="Distance in km")
    rpe: int = Field(..., ge=1, le=10, description="Rate of Perceived Exertion (1-10)")
    avg_hr: Optional[int] = Field(None, ge=30, le=250, description="Average heart rate")
    max_hr: Optional[int] = Field(None, ge=30, le=250, description="Maximum heart rate")
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """Validate date format."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @field_validator("activity_type")
    @classmethod
    def validate_activity_type(cls, v: str) -> str:
        """Validate activity type."""
        valid_types = {
            "running", "cycling", "swimming", "walking", "hiking",
            "strength", "yoga", "other"
        }
        if v.lower() not in valid_types:
            raise ValueError(f"Activity type must be one of: {', '.join(valid_types)}")
        return v.lower()


class ManualWorkoutResponse(BaseModel):
    """Response model for a manual workout."""
    activity_id: str
    user_id: str
    name: str
    activity_type: str
    date: str
    duration_min: int
    distance_km: Optional[float]
    rpe: int
    avg_hr: Optional[int]
    max_hr: Optional[int]
    estimated_load: float
    notes: Optional[str]
    created_at: str
    source: str = "manual"


class ManualWorkoutService:
    """
    Service for managing manually logged workouts.

    Uses session-RPE method (Foster et al.) to estimate training load
    from duration and perceived exertion, allowing athletes without
    heart rate monitors to still track their training load.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the manual workout service.

        Args:
            db_path: Path to the SQLite database. Defaults to training.db.
        """
        import sqlite3
        from pathlib import Path

        if db_path:
            self._db_path = db_path
        else:
            # Default to training.db in data directory
            self._db_path = str(Path(__file__).parent.parent.parent / "data" / "training.db")

        self._ensure_table_exists()

    def _get_connection(self):
        """Get a database connection."""
        import sqlite3
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table_exists(self):
        """Ensure the manual_workouts table exists."""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS manual_workouts (
                    activity_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    activity_type TEXT DEFAULT 'running',
                    date TEXT NOT NULL,
                    duration_min INTEGER NOT NULL,
                    distance_km REAL,
                    rpe INTEGER NOT NULL CHECK (rpe >= 1 AND rpe <= 10),
                    avg_hr INTEGER,
                    max_hr INTEGER,
                    estimated_load REAL NOT NULL,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_manual_workouts_user
                ON manual_workouts(user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_manual_workouts_date
                ON manual_workouts(date)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_manual_workouts_user_date
                ON manual_workouts(user_id, date)
            """)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def estimate_load_from_rpe(duration_min: int, rpe: int) -> float:
        """
        Estimate training load from RPE using session-RPE method.

        The session-RPE method (Foster et al., 2001) multiplies session
        duration by the RPE to get a single number representing internal
        training load.

        Load = Duration (minutes) x RPE (1-10)

        This is then normalized to approximately match the TRIMP scale
        (typically 50-200 for most workouts) for comparison with
        device-tracked workouts.

        Args:
            duration_min: Duration of workout in minutes
            rpe: Rate of Perceived Exertion (1-10 scale)

        Returns:
            Estimated training load (normalized to approximate TRIMP scale)

        References:
            Foster, C., et al. (2001). A new approach to monitoring exercise training.
            Journal of Strength and Conditioning Research, 15(1), 109-115.
        """
        # Session-RPE method: Duration x RPE
        base_load = duration_min * rpe

        # Normalize to approximate TRIMP scale
        # A typical 60-min easy run (RPE 3-4) should yield ~50-70 load
        # A hard 60-min tempo (RPE 7-8) should yield ~100-150 load
        # The 0.8 factor brings session-RPE roughly in line with TRIMP
        normalized_load = base_load * 0.8

        return round(normalized_load, 1)

    def log_manual_workout(
        self,
        user_id: str,
        workout_data: ManualWorkoutCreate,
    ) -> ManualWorkout:
        """
        Log a manual workout.

        Args:
            user_id: The user's ID
            workout_data: The workout data to log

        Returns:
            The created ManualWorkout

        Raises:
            ValueError: If workout data is invalid
        """
        # Generate unique activity ID
        activity_id = f"manual_{uuid.uuid4().hex[:12]}"

        # Generate name if not provided
        name = workout_data.name
        if not name:
            # Format: "Morning Run" or "Afternoon Cycling"
            date_obj = datetime.strptime(workout_data.date, "%Y-%m-%d")
            time_of_day = "Morning" if datetime.now().hour < 12 else "Afternoon" if datetime.now().hour < 17 else "Evening"
            activity_label = workout_data.activity_type.title()
            name = f"{time_of_day} {activity_label}"

        # Calculate estimated load
        estimated_load = self.estimate_load_from_rpe(
            workout_data.duration_min,
            workout_data.rpe
        )

        created_at = datetime.utcnow().isoformat()

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO manual_workouts (
                    activity_id, user_id, name, activity_type, date,
                    duration_min, distance_km, rpe, avg_hr, max_hr,
                    estimated_load, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    activity_id,
                    user_id,
                    name,
                    workout_data.activity_type,
                    workout_data.date,
                    workout_data.duration_min,
                    workout_data.distance_km,
                    workout_data.rpe,
                    workout_data.avg_hr,
                    workout_data.max_hr,
                    estimated_load,
                    workout_data.notes,
                    created_at,
                )
            )
            conn.commit()

            logger.info(
                f"Logged manual workout {activity_id} for user {user_id}: "
                f"{name}, {workout_data.duration_min}min, RPE {workout_data.rpe}, "
                f"load {estimated_load}"
            )

            return ManualWorkout(
                activity_id=activity_id,
                user_id=user_id,
                name=name,
                activity_type=workout_data.activity_type,
                date=workout_data.date,
                duration_min=workout_data.duration_min,
                distance_km=workout_data.distance_km,
                rpe=workout_data.rpe,
                avg_hr=workout_data.avg_hr,
                max_hr=workout_data.max_hr,
                estimated_load=estimated_load,
                notes=workout_data.notes,
                created_at=created_at,
            )

        finally:
            conn.close()

    def get_manual_workouts(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Tuple[List[ManualWorkout], int]:
        """
        Get manual workouts for a user.

        Args:
            user_id: The user's ID
            limit: Maximum number of workouts to return
            offset: Number of workouts to skip
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)

        Returns:
            Tuple of (list of ManualWorkout, total count)
        """
        conn = self._get_connection()
        try:
            # Build query with optional date filters
            where_clauses = ["user_id = ?"]
            params: List = [user_id]

            if start_date:
                where_clauses.append("date >= ?")
                params.append(start_date)
            if end_date:
                where_clauses.append("date <= ?")
                params.append(end_date)

            where_sql = " AND ".join(where_clauses)

            # Get total count
            count_row = conn.execute(
                f"SELECT COUNT(*) as count FROM manual_workouts WHERE {where_sql}",
                params
            ).fetchone()
            total = count_row["count"] if count_row else 0

            # Get workouts with pagination
            query_params = params + [limit, offset]
            rows = conn.execute(
                f"""
                SELECT * FROM manual_workouts
                WHERE {where_sql}
                ORDER BY date DESC, created_at DESC
                LIMIT ? OFFSET ?
                """,
                query_params
            ).fetchall()

            workouts = [
                ManualWorkout(
                    activity_id=row["activity_id"],
                    user_id=row["user_id"],
                    name=row["name"],
                    activity_type=row["activity_type"],
                    date=row["date"],
                    duration_min=row["duration_min"],
                    distance_km=row["distance_km"],
                    rpe=row["rpe"],
                    avg_hr=row["avg_hr"],
                    max_hr=row["max_hr"],
                    estimated_load=row["estimated_load"],
                    notes=row["notes"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

            return workouts, total

        finally:
            conn.close()

    def get_manual_workout(
        self,
        user_id: str,
        workout_id: str,
    ) -> Optional[ManualWorkout]:
        """
        Get a specific manual workout.

        Args:
            user_id: The user's ID
            workout_id: The workout's activity_id

        Returns:
            ManualWorkout if found, None otherwise
        """
        conn = self._get_connection()
        try:
            row = conn.execute(
                """
                SELECT * FROM manual_workouts
                WHERE activity_id = ? AND user_id = ?
                """,
                (workout_id, user_id)
            ).fetchone()

            if not row:
                return None

            return ManualWorkout(
                activity_id=row["activity_id"],
                user_id=row["user_id"],
                name=row["name"],
                activity_type=row["activity_type"],
                date=row["date"],
                duration_min=row["duration_min"],
                distance_km=row["distance_km"],
                rpe=row["rpe"],
                avg_hr=row["avg_hr"],
                max_hr=row["max_hr"],
                estimated_load=row["estimated_load"],
                notes=row["notes"],
                created_at=row["created_at"],
            )

        finally:
            conn.close()

    def delete_manual_workout(
        self,
        user_id: str,
        workout_id: str,
    ) -> bool:
        """
        Delete a manual workout.

        Args:
            user_id: The user's ID
            workout_id: The workout's activity_id

        Returns:
            True if workout was deleted, False if not found
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                DELETE FROM manual_workouts
                WHERE activity_id = ? AND user_id = ?
                """,
                (workout_id, user_id)
            )
            conn.commit()

            deleted = cursor.rowcount > 0

            if deleted:
                logger.info(f"Deleted manual workout {workout_id} for user {user_id}")
            else:
                logger.warning(
                    f"Manual workout {workout_id} not found for user {user_id}"
                )

            return deleted

        finally:
            conn.close()

    def get_weekly_load_summary(
        self,
        user_id: str,
        weeks: int = 4,
    ) -> List[dict]:
        """
        Get weekly training load summary from manual workouts.

        Args:
            user_id: The user's ID
            weeks: Number of weeks to include

        Returns:
            List of weekly summaries with total load and workout count
        """
        from datetime import timedelta

        conn = self._get_connection()
        try:
            # Calculate date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(weeks=weeks * 7)

            rows = conn.execute(
                """
                SELECT
                    strftime('%Y-%W', date) as week,
                    SUM(estimated_load) as total_load,
                    COUNT(*) as workout_count,
                    SUM(duration_min) as total_duration,
                    SUM(distance_km) as total_distance,
                    AVG(rpe) as avg_rpe
                FROM manual_workouts
                WHERE user_id = ? AND date >= ? AND date <= ?
                GROUP BY strftime('%Y-%W', date)
                ORDER BY week DESC
                """,
                (user_id, start_date.isoformat(), end_date.isoformat())
            ).fetchall()

            return [
                {
                    "week": row["week"],
                    "total_load": round(row["total_load"] or 0, 1),
                    "workout_count": row["workout_count"],
                    "total_duration_min": row["total_duration"] or 0,
                    "total_distance_km": round(row["total_distance"] or 0, 1),
                    "avg_rpe": round(row["avg_rpe"] or 0, 1),
                }
                for row in rows
            ]

        finally:
            conn.close()


@lru_cache
def get_manual_workout_service(db_path: Optional[str] = None) -> ManualWorkoutService:
    """Get or create a ManualWorkoutService instance."""
    from ..config import get_settings

    if db_path:
        return ManualWorkoutService(db_path)

    settings = get_settings()
    if settings.training_db_path and settings.training_db_path.exists():
        return ManualWorkoutService(str(settings.training_db_path))

    return ManualWorkoutService()
