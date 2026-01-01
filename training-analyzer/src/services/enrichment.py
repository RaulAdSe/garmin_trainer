"""Activity enrichment service.

This service reads raw activities from the n8n database,
calculates training metrics, and stores enriched data.
"""

import logging
import sqlite3
import os
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)

from ..db.database import (
    TrainingDatabase,
    UserProfile,
    ActivityMetrics,
    DailyFitnessMetrics,
)
from ..metrics.load import calculate_hrss, calculate_trimp
from ..metrics.fitness import calculate_fitness_metrics, FitnessMetrics
from ..metrics.power import (
    calculate_normalized_power,
    calculate_intensity_factor,
    calculate_tss_simple,
    calculate_variability_index,
    calculate_power_zones,
    get_power_zone_distribution,
)


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
            logger.warning(f"Could not read from n8n database: {e}")
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

        # Extract cadence - try multiple common field names from Garmin API
        # For running: averageRunningCadenceInStepsPerMinute (doubled from single foot)
        # For cycling: averageBikingCadenceInRevPerMinute
        cadence = None
        activity_type_lower = (raw_activity.get("activity_type") or "").lower()

        # Try running cadence fields (Garmin reports single-foot, we want total spm)
        if "run" in activity_type_lower:
            cadence = raw_activity.get("averageRunningCadenceInStepsPerMinute")
            if cadence is None:
                # Try alternative field names
                cadence = raw_activity.get("avg_running_cadence")
                if cadence is None:
                    cadence = raw_activity.get("avg_cadence")
                if cadence is not None and cadence < 120:
                    # Garmin reports half cadence (one foot), double it
                    cadence = int(cadence * 2)
        elif "cycling" in activity_type_lower or "biking" in activity_type_lower:
            cadence = raw_activity.get("averageBikingCadenceInRevPerMinute")
            if cadence is None:
                cadence = raw_activity.get("avg_cycling_cadence")
                if cadence is None:
                    cadence = raw_activity.get("avg_cadence")
        else:
            # Generic cadence field
            cadence = raw_activity.get("avg_cadence")

        # Ensure cadence is valid integer if present
        if cadence is not None:
            try:
                cadence = int(cadence)
                if cadence <= 0:
                    cadence = None
            except (ValueError, TypeError):
                cadence = None

        return ActivityMetrics(
            activity_id=activity_id,
            date=activity_date,
            start_time=start_time if start_time else None,  # Full ISO timestamp
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
            cadence=cadence,
        )

    def enrich_cycling_activity_with_power(
        self,
        raw_activity: Dict[str, Any],
        ftp: int,
        power_samples: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Enrich a cycling activity with power-based metrics.

        This method calculates NP, IF, TSS, VI, and power zone distribution
        for cycling activities when power data is available.

        Args:
            raw_activity: Raw activity data (should be cycling activity)
            ftp: Athlete's Functional Threshold Power in watts
            power_samples: Optional list of power values (1Hz). If not provided,
                          will attempt to use avg_power from raw_activity.

        Returns:
            Dictionary with power metrics:
            - normalized_power: NP in watts
            - intensity_factor: IF (NP/FTP)
            - tss: Training Stress Score
            - variability_index: VI (NP/Avg Power)
            - avg_power: Average power in watts
            - max_power: Maximum power in watts
            - power_zone_distribution: Dict with % time in each zone (1-7)
        """
        if ftp <= 0:
            return {}

        # Extract basic power data from activity
        avg_power = raw_activity.get("avg_power")
        max_power = raw_activity.get("max_power")
        duration_s = raw_activity.get("duration_s", 0) or 0

        # Calculate NP from power samples if available
        if power_samples and len(power_samples) > 0:
            np = calculate_normalized_power(power_samples, sample_rate_hz=1)

            # Calculate average power from samples
            if avg_power is None:
                avg_power = sum(power_samples) / len(power_samples)

            # Get max power from samples if not provided
            if max_power is None:
                max_power = max(power_samples)

            # Calculate power zone distribution
            zone_dist = get_power_zone_distribution(power_samples, ftp)
        else:
            # No power samples - estimate NP from avg power
            # For steady riding, NP ~ avg_power; for variable, NP is higher
            # Use avg_power as NP estimate (conservative)
            if avg_power is None or avg_power <= 0:
                return {}
            np = float(avg_power)
            zone_dist = {}

        # Calculate power metrics
        if_ = calculate_intensity_factor(np, ftp)
        tss = calculate_tss_simple(duration_s, np, ftp)
        vi = calculate_variability_index(np, float(avg_power)) if avg_power else 0.0

        return {
            "normalized_power": round(np, 0),
            "intensity_factor": if_,
            "tss": tss,
            "variability_index": vi,
            "avg_power": avg_power,
            "max_power": max_power,
            "power_zone_distribution": zone_dist,
        }

    def save_cycling_power_metrics(
        self,
        activity_id: str,
        power_metrics: Dict[str, Any],
    ) -> None:
        """
        Save power metrics for a cycling activity to the database.

        Updates the activity_metrics table with power-specific fields.

        Args:
            activity_id: The activity ID to update
            power_metrics: Dictionary with power metrics from
                          enrich_cycling_activity_with_power()
        """
        if not power_metrics:
            return

        with self.training_db._get_connection() as conn:
            conn.execute(
                """
                UPDATE activity_metrics
                SET normalized_power = ?,
                    intensity_factor = ?,
                    tss = ?,
                    variability_index = ?,
                    avg_power = ?,
                    max_power = ?,
                    sport_type = 'cycling',
                    updated_at = CURRENT_TIMESTAMP
                WHERE activity_id = ?
                """,
                (
                    power_metrics.get("normalized_power"),
                    power_metrics.get("intensity_factor"),
                    power_metrics.get("tss"),
                    power_metrics.get("variability_index"),
                    power_metrics.get("avg_power"),
                    power_metrics.get("max_power"),
                    activity_id,
                ),
            )

    def get_athlete_ftp(self) -> Optional[int]:
        """
        Get the athlete's FTP from the power_zones table.

        Returns:
            FTP in watts, or None if not set
        """
        with self.training_db._get_connection() as conn:
            row = conn.execute(
                "SELECT ftp FROM power_zones WHERE athlete_id = 'default' LIMIT 1"
            ).fetchone()
            if row:
                return row["ftp"]
            return None

    def set_athlete_ftp(self, ftp: int) -> None:
        """
        Set the athlete's FTP and calculate power zones.

        Args:
            ftp: Functional Threshold Power in watts
        """
        zones = calculate_power_zones(ftp)

        with self.training_db._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO power_zones
                (athlete_id, ftp, zone1_max, zone2_max, zone3_max,
                 zone4_max, zone5_max, zone6_max, zone7_max, updated_at)
                VALUES ('default', ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    ftp,
                    zones[1][1],  # Zone 1 max
                    zones[2][1],  # Zone 2 max
                    zones[3][1],  # Zone 3 max
                    zones[4][1],  # Zone 4 max
                    zones[5][1],  # Zone 5 max
                    zones[6][1],  # Zone 6 max
                    zones[7][1],  # Zone 7 max
                ),
            )

    def enrich_cycling_activities(
        self,
        days: int = 30,
        ftp: Optional[int] = None,
    ) -> Tuple[int, int]:
        """
        Enrich all cycling activities with power metrics.

        This processes cycling activities from the last N days and adds
        power-based training metrics (NP, IF, TSS, VI).

        Args:
            days: Number of days to look back
            ftp: FTP to use for calculations. If not provided, uses stored FTP.

        Returns:
            Tuple of (processed_count, success_count)
        """
        # Get FTP - use provided, or look up stored value
        if ftp is None:
            ftp = self.get_athlete_ftp()
            if ftp is None:
                logger.warning("No FTP set. Use set_athlete_ftp() first.")
                return 0, 0

        # Get cycling activities
        raw_activities = self.get_raw_activities(
            days=days,
            activity_types=["cycling", "virtual_cycling", "indoor_cycling"],
        )

        processed = 0
        success = 0

        for raw_activity in raw_activities:
            processed += 1
            try:
                # Get power samples if available (from separate stream data)
                power_samples = raw_activity.get("power_samples")

                # Calculate power metrics
                power_metrics = self.enrich_cycling_activity_with_power(
                    raw_activity=raw_activity,
                    ftp=ftp,
                    power_samples=power_samples,
                )

                if power_metrics:
                    activity_id = str(raw_activity.get("activity_id", ""))
                    if activity_id:
                        self.save_cycling_power_metrics(activity_id, power_metrics)
                        success += 1

            except Exception as e:
                logger.warning(
                    f"Error enriching cycling activity "
                    f"{raw_activity.get('activity_id')}: {e}"
                )

        return processed, success

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
                logger.warning(f"Error enriching activity {raw_activity.get('activity_id')}: {e}")

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
