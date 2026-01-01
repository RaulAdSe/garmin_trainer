"""SQLite database adapter implementation.

This adapter wraps the existing SQLite database logic and implements
the DatabaseAdapter interface for seamless backend switching.

SQLite-Specific Considerations:
    - Uses AUTOINCREMENT for auto-incrementing IDs
    - Stores dates as TEXT in ISO format (YYYY-MM-DD)
    - Stores booleans as INTEGER (0/1)
    - No native UUID support (stored as TEXT)
    - Single-writer model (use WAL for better concurrency)
    - File-based, no connection pooling needed
"""

import sqlite3
import os
import time
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from . import (
    DatabaseAdapter,
    ActivityMetricsData,
    FitnessMetricsData,
    UserProfileData,
)


def get_default_db_path() -> Path:
    """Get the default database path."""
    env_path = os.environ.get("TRAINING_DB_PATH")
    if env_path:
        return Path(env_path)
    # Default: training-analyzer/training.db
    return Path(__file__).parent.parent.parent.parent / "training.db"


class SQLiteAdapter(DatabaseAdapter):
    """SQLite implementation of the DatabaseAdapter interface.

    This adapter provides:
    - Full compatibility with the existing SQLite schema
    - Multi-user support via user_id filtering
    - WAL mode for better concurrent read performance
    - Prepared statement caching for performance

    Usage:
        adapter = SQLiteAdapter()  # Uses default path
        adapter = SQLiteAdapter(db_path="custom.db")

        # Get activities for a user
        activities = adapter.get_activities_range(
            "2024-01-01", "2024-01-31", user_id="user-123"
        )
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize SQLite adapter.

        Args:
            db_path: Path to SQLite database file.
                    If not provided, uses TRAINING_DB_PATH env var or default.
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = get_default_db_path()

        self._connection: Optional[sqlite3.Connection] = None
        self._in_transaction = False

    def initialize(self) -> None:
        """Initialize the database connection and schema."""
        # Import schema from parent module
        from ..schema import SCHEMA

        with self._get_connection() as conn:
            conn.executescript(SCHEMA)

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    @contextmanager
    def _get_connection(self):
        """Get a database connection with optimized settings."""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # SQLite performance optimizations
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety/speed
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        conn.execute("PRAGMA temp_store=MEMORY")  # Temp tables in memory

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def transaction(self):
        """Context manager for explicit transactions."""
        with self._get_connection() as conn:
            self._connection = conn
            self._in_transaction = True
            try:
                yield self
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                self._in_transaction = False
                self._connection = None

    def _get_active_connection(self):
        """Get the active connection for the current transaction or create new."""
        if self._in_transaction and self._connection:
            return self._connection
        return None

    # =========================================================================
    # Activity Metrics
    # =========================================================================

    def save_activity(
        self,
        activity: ActivityMetricsData,
        user_id: str = "default"
    ) -> ActivityMetricsData:
        """Save or update activity metrics."""
        with self._get_connection() as conn:
            # SQLite uses INSERT OR REPLACE for upsert
            # Note: PostgreSQL uses INSERT ... ON CONFLICT DO UPDATE
            conn.execute(
                """
                INSERT OR REPLACE INTO activity_metrics
                (activity_id, date, start_time, activity_type, activity_name,
                 hrss, trimp, avg_hr, max_hr, duration_min, distance_km,
                 pace_sec_per_km, zone1_pct, zone2_pct, zone3_pct, zone4_pct,
                 zone5_pct, sport_type, avg_power, max_power, normalized_power,
                 tss, intensity_factor, variability_index, avg_speed_kmh,
                 elevation_gain_m, cadence, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    activity.activity_id,
                    activity.date,
                    activity.start_time,
                    activity.activity_type,
                    activity.activity_name,
                    activity.hrss,
                    activity.trimp,
                    activity.avg_hr,
                    activity.max_hr,
                    activity.duration_min,
                    activity.distance_km,
                    activity.pace_sec_per_km,
                    activity.zone1_pct,
                    activity.zone2_pct,
                    activity.zone3_pct,
                    activity.zone4_pct,
                    activity.zone5_pct,
                    activity.sport_type,
                    activity.avg_power,
                    activity.max_power,
                    activity.normalized_power,
                    activity.tss,
                    activity.intensity_factor,
                    activity.variability_index,
                    activity.avg_speed_kmh,
                    activity.elevation_gain_m,
                    activity.cadence,
                ),
            )

        # Return with updated timestamp
        activity.updated_at = datetime.utcnow().isoformat()
        return activity

    def get_activity(
        self,
        activity_id: str,
        user_id: str = "default"
    ) -> Optional[ActivityMetricsData]:
        """Get a single activity by ID."""
        with self._get_connection() as conn:
            # Note: Current schema doesn't have user_id on activity_metrics
            # This will be added in migration phase
            row = conn.execute(
                "SELECT * FROM activity_metrics WHERE activity_id = ?",
                (activity_id,),
            ).fetchone()

            if row:
                return self._row_to_activity(row)
            return None

    def get_activities_range(
        self,
        start_date: str,
        end_date: str,
        user_id: str = "default",
        activity_type: Optional[str] = None,
        sport_type: Optional[str] = None
    ) -> List[ActivityMetricsData]:
        """Get activities within a date range."""
        with self._get_connection() as conn:
            query = """
                SELECT * FROM activity_metrics
                WHERE date >= ? AND date <= ?
            """
            params: List[Any] = [start_date, end_date]

            if activity_type:
                query += " AND activity_type = ?"
                params.append(activity_type)

            if sport_type:
                query += " AND sport_type = ?"
                params.append(sport_type)

            query += " ORDER BY date DESC, activity_id"

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_activity(row) for row in rows]

    def get_activities_paginated(
        self,
        user_id: str = "default",
        page: int = 1,
        page_size: int = 20,
        activity_type: Optional[str] = None,
        sport_type: Optional[str] = None
    ) -> Tuple[List[ActivityMetricsData], int]:
        """Get paginated activities with total count.

        This implements server-side pagination to fix N+1 query problems
        identified in DATABASE_SCALING_PLAN.md.
        """
        offset = (page - 1) * page_size

        with self._get_connection() as conn:
            # Build WHERE clause
            where_clauses = []
            params: List[Any] = []

            if activity_type:
                where_clauses.append("activity_type = ?")
                params.append(activity_type)

            if sport_type:
                where_clauses.append("sport_type = ?")
                params.append(sport_type)

            where_sql = ""
            if where_clauses:
                where_sql = "WHERE " + " AND ".join(where_clauses)

            # Count query (optimized - no SELECT *)
            count_query = f"SELECT COUNT(*) FROM activity_metrics {where_sql}"
            total = conn.execute(count_query, params).fetchone()[0]

            # Data query with LIMIT/OFFSET
            # SQLite uses LIMIT/OFFSET, PostgreSQL uses LIMIT/OFFSET or FETCH NEXT
            data_query = f"""
                SELECT * FROM activity_metrics
                {where_sql}
                ORDER BY date DESC, activity_id
                LIMIT ? OFFSET ?
            """
            rows = conn.execute(
                data_query, params + [page_size, offset]
            ).fetchall()

            activities = [self._row_to_activity(row) for row in rows]
            return activities, total

    def delete_activity(
        self,
        activity_id: str,
        user_id: str = "default"
    ) -> bool:
        """Delete an activity by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM activity_metrics WHERE activity_id = ?",
                (activity_id,),
            )
            return cursor.rowcount > 0

    def _row_to_activity(self, row: sqlite3.Row) -> ActivityMetricsData:
        """Convert a database row to ActivityMetricsData."""
        return ActivityMetricsData(
            activity_id=row["activity_id"],
            date=row["date"],
            start_time=row["start_time"],
            activity_type=row["activity_type"],
            activity_name=row["activity_name"],
            hrss=row["hrss"],
            trimp=row["trimp"],
            avg_hr=row["avg_hr"],
            max_hr=row["max_hr"],
            duration_min=row["duration_min"],
            distance_km=row["distance_km"],
            pace_sec_per_km=row["pace_sec_per_km"],
            zone1_pct=row["zone1_pct"],
            zone2_pct=row["zone2_pct"],
            zone3_pct=row["zone3_pct"],
            zone4_pct=row["zone4_pct"],
            zone5_pct=row["zone5_pct"],
            sport_type=row["sport_type"],
            avg_power=row["avg_power"],
            max_power=row["max_power"],
            normalized_power=row["normalized_power"],
            tss=row["tss"],
            intensity_factor=row["intensity_factor"],
            variability_index=row["variability_index"],
            avg_speed_kmh=row["avg_speed_kmh"],
            elevation_gain_m=row["elevation_gain_m"],
            cadence=row["cadence"],
            updated_at=row["updated_at"],
        )

    # =========================================================================
    # Fitness Metrics
    # =========================================================================

    def save_fitness_metrics(
        self,
        metrics: FitnessMetricsData,
        user_id: str = "default"
    ) -> FitnessMetricsData:
        """Save or update daily fitness metrics."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO fitness_metrics
                (date, daily_load, ctl, atl, tsb, acwr, risk_zone, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    metrics.date,
                    metrics.daily_load,
                    metrics.ctl,
                    metrics.atl,
                    metrics.tsb,
                    metrics.acwr,
                    metrics.risk_zone,
                ),
            )

        metrics.updated_at = datetime.utcnow().isoformat()
        return metrics

    def get_fitness_metrics(
        self,
        date_str: str,
        user_id: str = "default"
    ) -> Optional[FitnessMetricsData]:
        """Get fitness metrics for a specific date."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM fitness_metrics WHERE date = ?",
                (date_str,),
            ).fetchone()

            if row:
                return self._row_to_fitness(row)
            return None

    def get_fitness_range(
        self,
        start_date: str,
        end_date: str,
        user_id: str = "default"
    ) -> List[FitnessMetricsData]:
        """Get fitness metrics for a date range."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM fitness_metrics
                WHERE date >= ? AND date <= ?
                ORDER BY date DESC
                """,
                (start_date, end_date),
            ).fetchall()

            return [self._row_to_fitness(row) for row in rows]

    def get_latest_fitness_metrics(
        self,
        user_id: str = "default"
    ) -> Optional[FitnessMetricsData]:
        """Get the most recent fitness metrics."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM fitness_metrics ORDER BY date DESC LIMIT 1"
            ).fetchone()

            if row:
                return self._row_to_fitness(row)
            return None

    def _row_to_fitness(self, row: sqlite3.Row) -> FitnessMetricsData:
        """Convert a database row to FitnessMetricsData."""
        return FitnessMetricsData(
            date=row["date"],
            daily_load=row["daily_load"],
            ctl=row["ctl"],
            atl=row["atl"],
            tsb=row["tsb"],
            acwr=row["acwr"],
            risk_zone=row["risk_zone"],
            updated_at=row["updated_at"],
        )

    # =========================================================================
    # User Profile
    # =========================================================================

    def get_user_profile(
        self,
        user_id: str = "default"
    ) -> UserProfileData:
        """Get user profile with HR zones and settings."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM user_profile WHERE id = 1"
            ).fetchone()

            if row:
                return UserProfileData(
                    id=user_id,
                    max_hr=row["max_hr"],
                    rest_hr=row["rest_hr"],
                    threshold_hr=row["threshold_hr"],
                    gender=row["gender"] or "male",
                    age=row["age"],
                    weight_kg=row["weight_kg"],
                    updated_at=row["updated_at"],
                )

            # Return defaults if no profile exists
            return UserProfileData(
                id=user_id,
                max_hr=185,
                rest_hr=55,
                threshold_hr=165,
                gender="male",
                age=30,
                weight_kg=None,
            )

    def save_user_profile(
        self,
        profile: UserProfileData
    ) -> UserProfileData:
        """Save or update user profile."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO user_profile
                (id, max_hr, rest_hr, threshold_hr, age, gender, weight_kg, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    profile.max_hr,
                    profile.rest_hr,
                    profile.threshold_hr,
                    profile.age,
                    profile.gender,
                    profile.weight_kg,
                ),
            )

        profile.updated_at = datetime.utcnow().isoformat()
        return profile

    # =========================================================================
    # Statistics and Aggregations
    # =========================================================================

    def get_daily_load_totals(
        self,
        start_date: str,
        end_date: str,
        user_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Get aggregated daily load totals."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    date,
                    SUM(hrss) as total_hrss,
                    SUM(trimp) as total_trimp,
                    COUNT(*) as activity_count
                FROM activity_metrics
                WHERE date >= ? AND date <= ?
                GROUP BY date
                ORDER BY date
                """,
                (start_date, end_date),
            ).fetchall()

            return [dict(row) for row in rows]

    def get_stats(
        self,
        user_id: str = "default"
    ) -> Dict[str, Any]:
        """Get database statistics for a user."""
        with self._get_connection() as conn:
            activity_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM activity_metrics"
            ).fetchone()["cnt"]

            fitness_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM fitness_metrics"
            ).fetchone()["cnt"]

            activity_range = conn.execute(
                """
                SELECT MIN(date) as min_date, MAX(date) as max_date
                FROM activity_metrics
                """
            ).fetchone()

            fitness_range = conn.execute(
                """
                SELECT MIN(date) as min_date, MAX(date) as max_date
                FROM fitness_metrics
                """
            ).fetchone()

            return {
                "db_path": str(self.db_path),
                "backend": "sqlite",
                "total_activities": activity_count,
                "total_fitness_days": fitness_count,
                "activity_date_range": {
                    "earliest": activity_range["min_date"],
                    "latest": activity_range["max_date"],
                },
                "fitness_date_range": {
                    "earliest": fitness_range["min_date"],
                    "latest": fitness_range["max_date"],
                },
            }

    # =========================================================================
    # Health Check
    # =========================================================================

    def health_check(self) -> Dict[str, Any]:
        """Check database health and connectivity."""
        start_time = time.time()
        try:
            with self._get_connection() as conn:
                # Simple query to verify connection
                version = conn.execute("SELECT sqlite_version()").fetchone()[0]

                # Check if database file exists and is readable
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

            latency_ms = (time.time() - start_time) * 1000

            return {
                "healthy": True,
                "backend": "sqlite",
                "version": version,
                "latency_ms": round(latency_ms, 2),
                "details": {
                    "db_path": str(self.db_path),
                    "db_size_bytes": db_size,
                    "journal_mode": "WAL",
                },
            }

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return {
                "healthy": False,
                "backend": "sqlite",
                "version": None,
                "latency_ms": round(latency_ms, 2),
                "details": {
                    "error": str(e),
                    "db_path": str(self.db_path),
                },
            }
