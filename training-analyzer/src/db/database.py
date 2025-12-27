"""SQLite database for storing training metrics."""

import sqlite3
import os
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from dataclasses import dataclass

from .schema import SCHEMA


@dataclass
class UserProfile:
    """User profile for personalized training calculations."""

    id: int
    max_hr: Optional[int]
    rest_hr: Optional[int]
    threshold_hr: Optional[int]
    gender: str
    age: Optional[int]
    weight_kg: Optional[float]
    updated_at: Optional[str]

    def to_dict(self) -> dict:
        return {
            "max_hr": self.max_hr,
            "rest_hr": self.rest_hr,
            "threshold_hr": self.threshold_hr,
            "gender": self.gender,
            "age": self.age,
            "weight_kg": self.weight_kg,
        }


@dataclass
class ActivityMetrics:
    """Enriched activity metrics."""

    activity_id: str
    date: str
    activity_type: Optional[str]
    activity_name: Optional[str]
    hrss: Optional[float]
    trimp: Optional[float]
    avg_hr: Optional[int]
    max_hr: Optional[int]
    duration_min: Optional[float]
    distance_km: Optional[float]
    pace_sec_per_km: Optional[float]
    zone1_pct: Optional[float]
    zone2_pct: Optional[float]
    zone3_pct: Optional[float]
    zone4_pct: Optional[float]
    zone5_pct: Optional[float]
    # Phase 2: Multi-sport extensions
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
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "activity_id": self.activity_id,
            "date": self.date,
            "activity_type": self.activity_type,
            "activity_name": self.activity_name,
            "hrss": self.hrss,
            "trimp": self.trimp,
            "avg_hr": self.avg_hr,
            "max_hr": self.max_hr,
            "duration_min": self.duration_min,
            "distance_km": self.distance_km,
            "pace_sec_per_km": self.pace_sec_per_km,
            "zone1_pct": self.zone1_pct,
            "zone2_pct": self.zone2_pct,
            "zone3_pct": self.zone3_pct,
            "zone4_pct": self.zone4_pct,
            "zone5_pct": self.zone5_pct,
            # Phase 2: Multi-sport extensions
            "sport_type": self.sport_type,
            "avg_power": self.avg_power,
            "max_power": self.max_power,
            "normalized_power": self.normalized_power,
            "tss": self.tss,
            "intensity_factor": self.intensity_factor,
            "variability_index": self.variability_index,
            "avg_speed_kmh": self.avg_speed_kmh,
            "elevation_gain_m": self.elevation_gain_m,
            "cadence": self.cadence,
        }


@dataclass
class DailyFitnessMetrics:
    """Daily fitness metrics from the Fitness-Fatigue model."""

    date: str
    daily_load: float
    ctl: float
    atl: float
    tsb: float
    acwr: float
    risk_zone: str
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "daily_load": self.daily_load,
            "ctl": self.ctl,
            "atl": self.atl,
            "tsb": self.tsb,
            "acwr": self.acwr,
            "risk_zone": self.risk_zone,
        }


@dataclass
class GarminFitnessData:
    """Daily Garmin fitness data including VO2max, race predictions, and training status."""

    date: str
    # VO2max metrics
    vo2max_running: Optional[float] = None
    vo2max_cycling: Optional[float] = None
    fitness_age: Optional[int] = None
    # Race predictions (times in seconds)
    race_time_5k: Optional[int] = None
    race_time_10k: Optional[int] = None
    race_time_half: Optional[int] = None
    race_time_marathon: Optional[int] = None
    # Training status
    training_status: Optional[str] = None
    training_status_description: Optional[str] = None
    fitness_trend: Optional[str] = None
    # Training readiness
    training_readiness_score: Optional[int] = None
    training_readiness_level: Optional[str] = None
    # ACWR
    acwr_percent: Optional[float] = None
    acwr_status: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "vo2max_running": self.vo2max_running,
            "vo2max_cycling": self.vo2max_cycling,
            "fitness_age": self.fitness_age,
            "race_time_5k": self.race_time_5k,
            "race_time_10k": self.race_time_10k,
            "race_time_half": self.race_time_half,
            "race_time_marathon": self.race_time_marathon,
            "training_status": self.training_status,
            "training_status_description": self.training_status_description,
            "fitness_trend": self.fitness_trend,
            "training_readiness_score": self.training_readiness_score,
            "training_readiness_level": self.training_readiness_level,
            "acwr_percent": self.acwr_percent,
            "acwr_status": self.acwr_status,
        }

    def format_race_time(self, seconds: Optional[int]) -> Optional[str]:
        """Format race time in seconds to HH:MM:SS or MM:SS."""
        if seconds is None:
            return None
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def get_race_predictions_formatted(self) -> dict:
        """Get race predictions with formatted times."""
        return {
            "5k": self.format_race_time(self.race_time_5k),
            "10k": self.format_race_time(self.race_time_10k),
            "half_marathon": self.format_race_time(self.race_time_half),
            "marathon": self.format_race_time(self.race_time_marathon),
        }


def get_default_db_path() -> Path:
    """Get the default database path."""
    # Check environment variable first
    env_path = os.environ.get("TRAINING_DB_PATH")
    if env_path:
        return Path(env_path)

    # Default to training-analyzer directory
    # Path: training-analyzer/src/db/database.py
    # Go up 3 levels to training-analyzer/, then add training.db
    return Path(__file__).parent.parent.parent / "training.db"


class TrainingDatabase:
    """SQLite database manager for training metrics."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the training database.

        Args:
            db_path: Path to SQLite database file. If not provided,
                     uses TRAINING_DB_PATH env var or default location.
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = get_default_db_path()

        self._init_db()

    def _init_db(self):
        """Initialize database tables."""
        with self._get_connection() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # === User Profile Methods ===

    def get_user_profile(self) -> UserProfile:
        """Get the user profile."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM user_profile WHERE id = 1"
            ).fetchone()

            if row:
                return UserProfile(
                    id=row["id"],
                    max_hr=row["max_hr"],
                    rest_hr=row["rest_hr"],
                    threshold_hr=row["threshold_hr"],
                    gender=row["gender"],
                    age=row["age"],
                    weight_kg=row["weight_kg"],
                    updated_at=row["updated_at"],
                )

            # Return defaults if no profile
            return UserProfile(
                id=1,
                max_hr=185,
                rest_hr=55,
                threshold_hr=165,
                gender="male",
                age=30,
                weight_kg=None,
                updated_at=None,
            )

    def update_user_profile(
        self,
        max_hr: Optional[int] = None,
        rest_hr: Optional[int] = None,
        threshold_hr: Optional[int] = None,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        weight_kg: Optional[float] = None,
    ) -> UserProfile:
        """
        Update user profile with provided values.
        Only updates fields that are provided (not None).
        """
        current = self.get_user_profile()

        # Update only provided fields
        new_max_hr = max_hr if max_hr is not None else current.max_hr
        new_rest_hr = rest_hr if rest_hr is not None else current.rest_hr
        new_threshold_hr = threshold_hr if threshold_hr is not None else current.threshold_hr
        new_age = age if age is not None else current.age
        new_gender = gender if gender is not None else current.gender
        new_weight_kg = weight_kg if weight_kg is not None else current.weight_kg

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO user_profile
                (id, max_hr, rest_hr, threshold_hr, age, gender, weight_kg, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (new_max_hr, new_rest_hr, new_threshold_hr, new_age, new_gender, new_weight_kg),
            )

        return self.get_user_profile()

    # === Activity Metrics Methods ===

    def save_activity_metrics(self, metrics: ActivityMetrics) -> None:
        """Save or update activity metrics."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO activity_metrics
                (activity_id, date, activity_type, activity_name, hrss, trimp,
                 avg_hr, max_hr, duration_min, distance_km, pace_sec_per_km,
                 zone1_pct, zone2_pct, zone3_pct, zone4_pct, zone5_pct,
                 sport_type, avg_power, max_power, normalized_power, tss,
                 intensity_factor, variability_index, avg_speed_kmh,
                 elevation_gain_m, cadence, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    metrics.activity_id,
                    metrics.date,
                    metrics.activity_type,
                    metrics.activity_name,
                    metrics.hrss,
                    metrics.trimp,
                    metrics.avg_hr,
                    metrics.max_hr,
                    metrics.duration_min,
                    metrics.distance_km,
                    metrics.pace_sec_per_km,
                    metrics.zone1_pct,
                    metrics.zone2_pct,
                    metrics.zone3_pct,
                    metrics.zone4_pct,
                    metrics.zone5_pct,
                    metrics.sport_type,
                    metrics.avg_power,
                    metrics.max_power,
                    metrics.normalized_power,
                    metrics.tss,
                    metrics.intensity_factor,
                    metrics.variability_index,
                    metrics.avg_speed_kmh,
                    metrics.elevation_gain_m,
                    metrics.cadence,
                ),
            )

    def get_activity_metrics(self, activity_id: str) -> Optional[ActivityMetrics]:
        """Get metrics for a specific activity."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM activity_metrics WHERE activity_id = ?",
                (activity_id,),
            ).fetchone()

            if row:
                return ActivityMetrics(**dict(row))
            return None

    def get_activities_for_date(self, date_str: str) -> List[ActivityMetrics]:
        """Get all activities for a specific date."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM activity_metrics WHERE date = ? ORDER BY activity_id",
                (date_str,),
            ).fetchall()

            return [ActivityMetrics(**dict(row)) for row in rows]

    def get_activities_range(
        self, start_date: str, end_date: str
    ) -> List[ActivityMetrics]:
        """Get all activities in a date range."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM activity_metrics
                WHERE date >= ? AND date <= ?
                ORDER BY date DESC, activity_id
                """,
                (start_date, end_date),
            ).fetchall()

            return [ActivityMetrics(**dict(row)) for row in rows]

    def get_unenriched_activity_ids(self) -> List[str]:
        """Get activity IDs that haven't been enriched yet."""
        # This would query the source database - to be implemented
        # in the enrichment service
        return []

    # === Fitness Metrics Methods ===

    def save_fitness_metrics(self, metrics: DailyFitnessMetrics) -> None:
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

    def get_fitness_metrics(self, date_str: str) -> Optional[DailyFitnessMetrics]:
        """Get fitness metrics for a specific date."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM fitness_metrics WHERE date = ?",
                (date_str,),
            ).fetchone()

            if row:
                return DailyFitnessMetrics(**dict(row))
            return None

    def get_fitness_range(
        self, start_date: str, end_date: str
    ) -> List[DailyFitnessMetrics]:
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

            return [DailyFitnessMetrics(**dict(row)) for row in rows]

    def get_latest_fitness_metrics(self) -> Optional[DailyFitnessMetrics]:
        """Get the most recent fitness metrics."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM fitness_metrics ORDER BY date DESC LIMIT 1"
            ).fetchone()

            if row:
                return DailyFitnessMetrics(**dict(row))
            return None

    # === Utility Methods ===

    def get_daily_load_totals(self, start_date: str, end_date: str) -> List[Dict]:
        """Get aggregated daily load totals from activity metrics."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT date, SUM(hrss) as total_hrss, SUM(trimp) as total_trimp,
                       COUNT(*) as activity_count
                FROM activity_metrics
                WHERE date >= ? AND date <= ?
                GROUP BY date
                ORDER BY date
                """,
                (start_date, end_date),
            ).fetchall()

            return [dict(row) for row in rows]

    def get_stats(self) -> dict:
        """Get database statistics."""
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

    # === Race Goals Methods ===

    def save_race_goal(
        self,
        race_date: str,
        distance: str,
        target_time_sec: int,
        notes: Optional[str] = None,
    ) -> int:
        """
        Save a new race goal.

        Args:
            race_date: Race date (YYYY-MM-DD)
            distance: Distance identifier (e.g., "5k", "half_marathon")
            target_time_sec: Target finish time in seconds
            notes: Optional notes about the goal

        Returns:
            ID of the created goal
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO race_goals (race_date, distance, target_time_sec, notes)
                VALUES (?, ?, ?, ?)
                """,
                (race_date, distance, target_time_sec, notes),
            )
            return cursor.lastrowid

    def get_race_goals(self, upcoming_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get race goals.

        Args:
            upcoming_only: If True, only return future goals

        Returns:
            List of goal dictionaries
        """
        with self._get_connection() as conn:
            if upcoming_only:
                today = date.today().isoformat()
                rows = conn.execute(
                    """
                    SELECT * FROM race_goals
                    WHERE race_date >= ?
                    ORDER BY race_date ASC
                    """,
                    (today,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM race_goals ORDER BY race_date DESC"
                ).fetchall()

            return [dict(row) for row in rows]

    def get_race_goal(self, goal_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific race goal by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM race_goals WHERE id = ?",
                (goal_id,),
            ).fetchone()

            return dict(row) if row else None

    def delete_race_goal(self, goal_id: int) -> bool:
        """Delete a race goal by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM race_goals WHERE id = ?",
                (goal_id,),
            )
            return cursor.rowcount > 0

    # === Weekly Summary Methods ===

    def save_weekly_summary(
        self,
        week_start: str,
        total_distance_km: float,
        total_duration_min: float,
        total_load: float,
        activity_count: int,
        zone_distribution: str,  # JSON string
        ctl_start: float,
        ctl_end: float,
        ctl_change: float,
        atl_change: float,
        week_over_week_change: float,
        is_recovery_week: bool,
        insights: str,  # JSON string
    ) -> None:
        """Save or update a weekly summary."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO weekly_summaries
                (week_start, total_distance_km, total_duration_min, total_load,
                 activity_count, zone_distribution, ctl_start, ctl_end,
                 ctl_change, atl_change, week_over_week_change, is_recovery_week,
                 insights, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    week_start,
                    total_distance_km,
                    total_duration_min,
                    total_load,
                    activity_count,
                    zone_distribution,
                    ctl_start,
                    ctl_end,
                    ctl_change,
                    atl_change,
                    week_over_week_change,
                    1 if is_recovery_week else 0,
                    insights,
                ),
            )

    def get_weekly_summary(self, week_start: str) -> Optional[Dict[str, Any]]:
        """Get a weekly summary by week start date."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM weekly_summaries WHERE week_start = ?",
                (week_start,),
            ).fetchone()

            return dict(row) if row else None

    def get_weekly_summaries(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Get weekly summaries for a date range."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM weekly_summaries
                WHERE week_start >= ? AND week_start <= ?
                ORDER BY week_start DESC
                """,
                (start_date, end_date),
            ).fetchall()

            return [dict(row) for row in rows]

    def get_recent_weekly_summaries(self, weeks: int = 8) -> List[Dict[str, Any]]:
        """Get the most recent weekly summaries."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM weekly_summaries
                ORDER BY week_start DESC
                LIMIT ?
                """,
                (weeks,),
            ).fetchall()

            return [dict(row) for row in rows]

    # === Garmin Fitness Data Methods ===

    def save_garmin_fitness_data(self, data: GarminFitnessData) -> None:
        """Save or update Garmin fitness data for a specific date."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO garmin_fitness_data
                (date, vo2max_running, vo2max_cycling, fitness_age,
                 race_time_5k, race_time_10k, race_time_half, race_time_marathon,
                 training_status, training_status_description, fitness_trend,
                 training_readiness_score, training_readiness_level,
                 acwr_percent, acwr_status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    data.date,
                    data.vo2max_running,
                    data.vo2max_cycling,
                    data.fitness_age,
                    data.race_time_5k,
                    data.race_time_10k,
                    data.race_time_half,
                    data.race_time_marathon,
                    data.training_status,
                    data.training_status_description,
                    data.fitness_trend,
                    data.training_readiness_score,
                    data.training_readiness_level,
                    data.acwr_percent,
                    data.acwr_status,
                ),
            )

    def get_garmin_fitness_data(self, date_str: str) -> Optional[GarminFitnessData]:
        """Get Garmin fitness data for a specific date."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM garmin_fitness_data WHERE date = ?",
                (date_str,),
            ).fetchone()

            if row:
                return GarminFitnessData(**dict(row))
            return None

    def get_garmin_fitness_range(
        self, start_date: str, end_date: str
    ) -> List[GarminFitnessData]:
        """Get Garmin fitness data for a date range."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM garmin_fitness_data
                WHERE date >= ? AND date <= ?
                ORDER BY date DESC
                """,
                (start_date, end_date),
            ).fetchall()

            return [GarminFitnessData(**dict(row)) for row in rows]

    def get_latest_garmin_fitness_data(self) -> Optional[GarminFitnessData]:
        """Get the most recent Garmin fitness data."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM garmin_fitness_data ORDER BY date DESC LIMIT 1"
            ).fetchone()

            if row:
                return GarminFitnessData(**dict(row))
            return None

    def get_garmin_fitness_for_workout(self, workout_date: str) -> Optional[GarminFitnessData]:
        """
        Get the Garmin fitness data that was valid for a specific workout date.

        Returns the fitness data from that date or the most recent data before it.
        This is useful for looking up what the athlete's VO2max/predictions were
        at the time of a specific workout.
        """
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM garmin_fitness_data
                WHERE date <= ?
                ORDER BY date DESC
                LIMIT 1
                """,
                (workout_date,),
            ).fetchone()

            if row:
                return GarminFitnessData(**dict(row))
            return None
