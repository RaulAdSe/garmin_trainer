"""Activity enrichment service.

This service reads raw activities from the n8n database,
calculates training metrics, and stores enriched data.
"""

import sqlite3
import os
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

from ..db.database import (
    TrainingDatabase,
    UserProfile,
    ActivityMetrics,
    DailyFitnessMetrics,
)
from ..metrics.load import calculate_hrss, calculate_trimp
from ..metrics.fitness import calculate_fitness_metrics, FitnessMetrics


def get_n8n_db_path() -> Optional[Path]:
    """
    Get the path to the n8n SQLite database.

    n8n stores its database in the .n8n directory by default.
    Can be overridden with N8N_DB_PATH environment variable.
    """
    # Check environment variable first
    env_path = os.environ.get("N8N_DB_PATH")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    # Try common n8n locations
    home = Path.home()
    possible_paths = [
        home / ".n8n" / "database.sqlite",
        home / ".n8n" / "n8n.sqlite",
        Path("/home/node/.n8n/database.sqlite"),  # Docker default
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None


class EnrichmentService:
    """
    Service to enrich raw activities with training metrics.

    Reads from n8n raw_activities table, calculates HRSS/TRIMP,
    and updates fitness metrics (CTL/ATL/TSB).
    """

    def __init__(
        self,
        training_db: Optional[TrainingDatabase] = None,
        n8n_db_path: Optional[str] = None,
    ):
        """
        Initialize the enrichment service.

        Args:
            training_db: TrainingDatabase instance (created if not provided)
            n8n_db_path: Path to n8n SQLite database (auto-detected if not provided)
        """
        self.training_db = training_db or TrainingDatabase()
        self._n8n_db_path = n8n_db_path

    @property
    def n8n_db_path(self) -> Optional[Path]:
        """Get the n8n database path."""
        if self._n8n_db_path:
            return Path(self._n8n_db_path)
        return get_n8n_db_path()

    @contextmanager
    def _get_n8n_connection(self):
        """Get connection to n8n database."""
        if not self.n8n_db_path or not self.n8n_db_path.exists():
            raise FileNotFoundError(
                f"n8n database not found. Set N8N_DB_PATH environment variable. "
                f"Tried: {self.n8n_db_path}"
            )

        conn = sqlite3.connect(self.n8n_db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def get_raw_activities(
        self,
        days: int = 30,
        activity_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch raw activities from n8n database.

        Args:
            days: Number of days to look back
            activity_types: Filter by activity types (e.g., ['running', 'cycling'])

        Returns:
            List of raw activity dictionaries
        """
        try:
            with self._get_n8n_connection() as conn:
                # First check if the table exists and get its structure
                # n8n uses a generic table structure with JSON data
                cursor = conn.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name LIKE '%raw_activities%'
                    """
                )
                tables = cursor.fetchall()

                if not tables:
                    # Try to find any table that might contain activities
                    cursor = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                    all_tables = [row["name"] for row in cursor.fetchall()]
                    raise ValueError(
                        f"raw_activities table not found. Available tables: {all_tables}"
                    )

                table_name = tables[0]["name"]

                # Calculate date cutoff
                cutoff_date = (
                    datetime.now() - timedelta(days=days)
                ).strftime("%Y-%m-%d")

                # Query activities
                query = f"""
                    SELECT * FROM "{table_name}"
                    WHERE start_time >= ?
                    ORDER BY start_time DESC
                """
                cursor = conn.execute(query, (cutoff_date,))
                rows = cursor.fetchall()

                activities = []
                for row in rows:
                    activity = dict(row)

                    # Filter by activity type if specified
                    if activity_types:
                        activity_type = activity.get("activity_type", "").lower()
                        if activity_type not in [t.lower() for t in activity_types]:
                            continue

                    activities.append(activity)

                return activities

        except Exception as e:
            # If we can't connect to n8n, return empty list with warning
            print(f"Warning: Could not read from n8n database: {e}")
            return []

    def enrich_activity(
        self, raw_activity: Dict[str, Any], profile: UserProfile
    ) -> Optional[ActivityMetrics]:
        """
        Enrich a single activity with training metrics.

        Args:
            raw_activity: Raw activity data from n8n
            profile: User profile with HR settings

        Returns:
            ActivityMetrics with calculated values, or None if insufficient data
        """
        # Extract required fields
        activity_id = str(raw_activity.get("activity_id", ""))
        if not activity_id:
            return None

        # Parse start time to get date
        start_time = raw_activity.get("start_time", "")
        if start_time:
            # Handle various date formats
            try:
                if "T" in start_time:
                    activity_date = start_time.split("T")[0]
                else:
                    activity_date = start_time.split(" ")[0]
            except (ValueError, IndexError):
                activity_date = datetime.now().strftime("%Y-%m-%d")
        else:
            activity_date = datetime.now().strftime("%Y-%m-%d")

        # Extract HR data
        avg_hr = raw_activity.get("avg_hr")
        max_hr_activity = raw_activity.get("max_hr")

        # Extract duration (convert from seconds to minutes)
        duration_s = raw_activity.get("duration_s", 0) or 0
        duration_min = duration_s / 60.0

        # Extract distance (convert from meters to km)
        distance_m = raw_activity.get("distance_m", 0) or 0
        distance_km = distance_m / 1000.0

        # Calculate pace if we have distance and duration
        pace_sec_per_km = None
        if distance_km > 0 and duration_s > 0:
            pace_sec_per_km = duration_s / distance_km

        # Calculate training metrics if we have HR data
        hrss = None
        trimp = None

        if avg_hr and profile.max_hr and profile.rest_hr:
            # Use activity max_hr if available, otherwise use profile
            max_hr = max_hr_activity or profile.max_hr

            # Calculate HRSS
            if profile.threshold_hr:
                hrss = calculate_hrss(
                    duration_min=duration_min,
                    avg_hr=avg_hr,
                    threshold_hr=profile.threshold_hr,
                    max_hr=max_hr,
                    rest_hr=profile.rest_hr,
                )

            # Calculate TRIMP
            trimp = calculate_trimp(
                duration_min=duration_min,
                avg_hr=avg_hr,
                rest_hr=profile.rest_hr,
                max_hr=max_hr,
                gender=profile.gender,
            )

        return ActivityMetrics(
            activity_id=activity_id,
            date=activity_date,
            activity_type=raw_activity.get("activity_type"),
            activity_name=raw_activity.get("activity_name"),
            hrss=hrss,
            trimp=trimp,
            avg_hr=avg_hr,
            max_hr=max_hr_activity,
            duration_min=round(duration_min, 1) if duration_min else None,
            distance_km=round(distance_km, 2) if distance_km else None,
            pace_sec_per_km=round(pace_sec_per_km, 0) if pace_sec_per_km else None,
            zone1_pct=None,  # Would require HR stream data
            zone2_pct=None,
            zone3_pct=None,
            zone4_pct=None,
            zone5_pct=None,
        )

    def enrich_activities(
        self,
        days: int = 30,
        activity_types: Optional[List[str]] = None,
    ) -> Tuple[int, int]:
        """
        Enrich all raw activities from the last N days.

        Args:
            days: Number of days to process
            activity_types: Filter by activity types

        Returns:
            Tuple of (processed_count, success_count)
        """
        profile = self.training_db.get_user_profile()
        raw_activities = self.get_raw_activities(days=days, activity_types=activity_types)

        processed = 0
        success = 0

        for raw_activity in raw_activities:
            processed += 1
            try:
                metrics = self.enrich_activity(raw_activity, profile)
                if metrics:
                    self.training_db.save_activity_metrics(metrics)
                    success += 1
            except Exception as e:
                print(f"Error enriching activity {raw_activity.get('activity_id')}: {e}")

        return processed, success

    def calculate_fitness_from_activities(
        self,
        days: int = 90,
        load_metric: str = "hrss",
    ) -> int:
        """
        Calculate and store fitness metrics from enriched activities.

        Args:
            days: Number of days to calculate
            load_metric: Which metric to use ('hrss' or 'trimp')

        Returns:
            Number of days calculated
        """
        # Get date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        # Get daily load totals
        daily_loads = self.training_db.get_daily_load_totals(
            start_date.isoformat(), end_date.isoformat()
        )

        # Convert to format expected by fitness calculation
        load_data: List[Tuple[date, float]] = []
        for row in daily_loads:
            activity_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
            if load_metric == "trimp":
                load = row.get("total_trimp", 0) or 0
            else:
                load = row.get("total_hrss", 0) or 0
            load_data.append((activity_date, load))

        if not load_data:
            return 0

        # Get initial values from previous calculation if available
        initial_ctl = 0.0
        initial_atl = 0.0

        # Calculate fitness metrics
        fitness_results = calculate_fitness_metrics(
            daily_loads=load_data,
            initial_ctl=initial_ctl,
            initial_atl=initial_atl,
        )

        # Save results
        for fm in fitness_results:
            daily_metrics = DailyFitnessMetrics(
                date=fm.date.isoformat(),
                daily_load=fm.daily_load,
                ctl=fm.ctl,
                atl=fm.atl,
                tsb=fm.tsb,
                acwr=fm.acwr,
                risk_zone=fm.risk_zone,
            )
            self.training_db.save_fitness_metrics(daily_metrics)

        return len(fitness_results)

    def run_full_enrichment(
        self,
        days: int = 30,
        load_metric: str = "hrss",
    ) -> Dict[str, Any]:
        """
        Run full enrichment pipeline: activities + fitness metrics.

        Args:
            days: Number of days to process
            load_metric: Which metric to use for fitness ('hrss' or 'trimp')

        Returns:
            Summary of enrichment results
        """
        # Enrich activities
        processed, success = self.enrich_activities(days=days)

        # Calculate fitness metrics
        # Use a longer window for fitness to build up CTL
        fitness_days = self.calculate_fitness_from_activities(
            days=days + 42,  # Extra days to warm up CTL
            load_metric=load_metric,
        )

        return {
            "activities_processed": processed,
            "activities_enriched": success,
            "fitness_days_calculated": fitness_days,
        }
