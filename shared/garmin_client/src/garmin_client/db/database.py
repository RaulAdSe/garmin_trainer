"""SQLite database for storing wellness data."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from contextlib import contextmanager

from .models import DailyWellness, SleepData, HRVData, StressData, ActivityData


class Database:
    """SQLite database manager for wellness data."""

    def __init__(self, db_path: str = "wellness.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize database tables."""
        with self._get_connection() as conn:
            conn.executescript("""
                -- Daily wellness summary
                CREATE TABLE IF NOT EXISTS daily_wellness (
                    date TEXT PRIMARY KEY,
                    fetched_at TEXT NOT NULL,
                    resting_heart_rate INTEGER,
                    training_readiness_score INTEGER,
                    training_readiness_level TEXT,
                    raw_json TEXT
                );

                -- Sleep data
                CREATE TABLE IF NOT EXISTS sleep_data (
                    date TEXT PRIMARY KEY,
                    sleep_start TEXT,
                    sleep_end TEXT,
                    total_sleep_seconds INTEGER DEFAULT 0,
                    deep_sleep_seconds INTEGER DEFAULT 0,
                    light_sleep_seconds INTEGER DEFAULT 0,
                    rem_sleep_seconds INTEGER DEFAULT 0,
                    awake_seconds INTEGER DEFAULT 0,
                    sleep_score INTEGER,
                    sleep_efficiency REAL,
                    avg_spo2 REAL,
                    avg_respiration REAL,
                    FOREIGN KEY (date) REFERENCES daily_wellness(date)
                );

                -- HRV data
                CREATE TABLE IF NOT EXISTS hrv_data (
                    date TEXT PRIMARY KEY,
                    hrv_weekly_avg INTEGER,
                    hrv_last_night_avg INTEGER,
                    hrv_last_night_5min_high INTEGER,
                    hrv_status TEXT,
                    baseline_low INTEGER,
                    baseline_balanced_low INTEGER,
                    baseline_balanced_upper INTEGER,
                    FOREIGN KEY (date) REFERENCES daily_wellness(date)
                );

                -- Stress & Body Battery data
                CREATE TABLE IF NOT EXISTS stress_data (
                    date TEXT PRIMARY KEY,
                    avg_stress_level INTEGER,
                    max_stress_level INTEGER,
                    rest_stress_duration INTEGER DEFAULT 0,
                    low_stress_duration INTEGER DEFAULT 0,
                    medium_stress_duration INTEGER DEFAULT 0,
                    high_stress_duration INTEGER DEFAULT 0,
                    body_battery_charged INTEGER,
                    body_battery_drained INTEGER,
                    body_battery_high INTEGER,
                    body_battery_low INTEGER,
                    FOREIGN KEY (date) REFERENCES daily_wellness(date)
                );

                -- Activity data
                CREATE TABLE IF NOT EXISTS activity_data (
                    date TEXT PRIMARY KEY,
                    steps INTEGER DEFAULT 0,
                    steps_goal INTEGER DEFAULT 10000,
                    total_distance_m INTEGER DEFAULT 0,
                    active_calories INTEGER,
                    total_calories INTEGER,
                    intensity_minutes INTEGER DEFAULT 0,
                    floors_climbed INTEGER DEFAULT 0,
                    FOREIGN KEY (date) REFERENCES daily_wellness(date)
                );

                -- Personal baselines (7-day and 30-day rolling averages)
                CREATE TABLE IF NOT EXISTS baselines (
                    date TEXT PRIMARY KEY,
                    hrv_7d_avg REAL,
                    hrv_30d_avg REAL,
                    rhr_7d_avg REAL,
                    rhr_30d_avg REAL,
                    sleep_7d_avg REAL,
                    sleep_30d_avg REAL,
                    strain_7d_avg REAL,
                    recovery_7d_avg REAL,
                    FOREIGN KEY (date) REFERENCES daily_wellness(date)
                );

                -- Training readiness data from Garmin
                CREATE TABLE IF NOT EXISTS training_readiness (
                    date TEXT PRIMARY KEY,
                    score INTEGER,
                    level TEXT,
                    hrv_feedback TEXT,
                    sleep_feedback TEXT,
                    recovery_feedback TEXT,
                    acclimation_feedback TEXT,
                    primary_feedback TEXT,
                    FOREIGN KEY (date) REFERENCES daily_wellness(date)
                );

                -- Indexes for common queries
                CREATE INDEX IF NOT EXISTS idx_wellness_date ON daily_wellness(date);
                CREATE INDEX IF NOT EXISTS idx_sleep_date ON sleep_data(date);
                CREATE INDEX IF NOT EXISTS idx_baselines_date ON baselines(date);
            """)

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

    def save_wellness(self, wellness: DailyWellness) -> None:
        """Save or update a daily wellness record."""
        with self._get_connection() as conn:
            # Main wellness record
            conn.execute("""
                INSERT OR REPLACE INTO daily_wellness
                (date, fetched_at, resting_heart_rate, training_readiness_score,
                 training_readiness_level, raw_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                wellness.date,
                wellness.fetched_at,
                wellness.resting_heart_rate,
                wellness.training_readiness_score,
                wellness.training_readiness_level,
                wellness.raw_json,
            ))

            # Sleep data
            if wellness.sleep:
                s = wellness.sleep
                conn.execute("""
                    INSERT OR REPLACE INTO sleep_data
                    (date, sleep_start, sleep_end, total_sleep_seconds, deep_sleep_seconds,
                     light_sleep_seconds, rem_sleep_seconds, awake_seconds, sleep_score,
                     sleep_efficiency, avg_spo2, avg_respiration)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    s.date, s.sleep_start, s.sleep_end, s.total_sleep_seconds,
                    s.deep_sleep_seconds, s.light_sleep_seconds, s.rem_sleep_seconds,
                    s.awake_seconds, s.sleep_score, s.sleep_efficiency,
                    s.avg_spo2, s.avg_respiration,
                ))

            # HRV data
            if wellness.hrv:
                h = wellness.hrv
                conn.execute("""
                    INSERT OR REPLACE INTO hrv_data
                    (date, hrv_weekly_avg, hrv_last_night_avg, hrv_last_night_5min_high,
                     hrv_status, baseline_low, baseline_balanced_low, baseline_balanced_upper)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    h.date, h.hrv_weekly_avg, h.hrv_last_night_avg, h.hrv_last_night_5min_high,
                    h.hrv_status, h.baseline_low, h.baseline_balanced_low, h.baseline_balanced_upper,
                ))

            # Stress data
            if wellness.stress:
                st = wellness.stress
                conn.execute("""
                    INSERT OR REPLACE INTO stress_data
                    (date, avg_stress_level, max_stress_level, rest_stress_duration,
                     low_stress_duration, medium_stress_duration, high_stress_duration,
                     body_battery_charged, body_battery_drained, body_battery_high, body_battery_low)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    st.date, st.avg_stress_level, st.max_stress_level, st.rest_stress_duration,
                    st.low_stress_duration, st.medium_stress_duration, st.high_stress_duration,
                    st.body_battery_charged, st.body_battery_drained, st.body_battery_high, st.body_battery_low,
                ))

            # Activity data
            if wellness.activity:
                a = wellness.activity
                conn.execute("""
                    INSERT OR REPLACE INTO activity_data
                    (date, steps, steps_goal, total_distance_m, active_calories,
                     total_calories, intensity_minutes, floors_climbed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    a.date, a.steps, a.steps_goal, a.total_distance_m,
                    a.active_calories, a.total_calories, a.intensity_minutes, a.floors_climbed,
                ))

    def get_wellness(self, date_str: str) -> Optional[DailyWellness]:
        """Get wellness data for a specific date."""
        with self._get_connection() as conn:
            # Get main record
            row = conn.execute(
                "SELECT * FROM daily_wellness WHERE date = ?", (date_str,)
            ).fetchone()

            if not row:
                return None

            # Get related data
            sleep_row = conn.execute(
                "SELECT * FROM sleep_data WHERE date = ?", (date_str,)
            ).fetchone()

            hrv_row = conn.execute(
                "SELECT * FROM hrv_data WHERE date = ?", (date_str,)
            ).fetchone()

            stress_row = conn.execute(
                "SELECT * FROM stress_data WHERE date = ?", (date_str,)
            ).fetchone()

            activity_row = conn.execute(
                "SELECT * FROM activity_data WHERE date = ?", (date_str,)
            ).fetchone()

            return DailyWellness(
                date=row["date"],
                fetched_at=row["fetched_at"],
                resting_heart_rate=row["resting_heart_rate"],
                training_readiness_score=row["training_readiness_score"],
                training_readiness_level=row["training_readiness_level"],
                raw_json=row["raw_json"],
                sleep=SleepData(**dict(sleep_row)) if sleep_row else None,
                hrv=HRVData(**dict(hrv_row)) if hrv_row else None,
                stress=StressData(**dict(stress_row)) if stress_row else None,
                activity=ActivityData(**dict(activity_row)) if activity_row else None,
            )

    def get_wellness_range(self, start_date: str, end_date: str) -> List[DailyWellness]:
        """Get wellness data for a date range."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT date FROM daily_wellness
                WHERE date >= ? AND date <= ?
                ORDER BY date DESC
            """, (start_date, end_date)).fetchall()

        return [self.get_wellness(row["date"]) for row in rows]

    def get_latest_date(self) -> Optional[str]:
        """Get the most recent date in the database."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT MAX(date) as max_date FROM daily_wellness"
            ).fetchone()
            return row["max_date"] if row else None

    def get_stats(self) -> dict:
        """Get database statistics."""
        with self._get_connection() as conn:
            wellness_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM daily_wellness"
            ).fetchone()["cnt"]

            date_range = conn.execute("""
                SELECT MIN(date) as min_date, MAX(date) as max_date
                FROM daily_wellness
            """).fetchone()

            return {
                "total_days": wellness_count,
                "earliest_date": date_range["min_date"],
                "latest_date": date_range["max_date"],
                "db_path": str(self.db_path),
            }
