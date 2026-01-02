"""Personal Record (PR) detection service.

This service handles:
- Detection of new personal records from workouts
- Comparison of current workout to existing PRs
- Storage and retrieval of personal records
"""

import logging
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from ..models.personal_records import (
    PersonalRecord,
    PRType,
    ActivityType,
    PRDetectionResult,
    PRSummary,
    PRComparisonResult,
    PRThresholds,
)

logger = logging.getLogger(__name__)


class PRDetectionService:
    """Service for detecting and managing personal records."""

    def __init__(self, db_path: str):
        """Initialize the PR detection service.

        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        self._ensure_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self) -> None:
        """Ensure the personal_records table exists."""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS personal_records (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL DEFAULT 'default',
                    pr_type TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    workout_id TEXT NOT NULL,
                    achieved_at TEXT NOT NULL,
                    previous_value REAL,
                    improvement REAL,
                    improvement_percent REAL,
                    workout_name TEXT,
                    workout_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pr_user_type
                ON personal_records(user_id, pr_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pr_achieved
                ON personal_records(achieved_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pr_activity_type
                ON personal_records(activity_type)
            """)
            conn.commit()
        finally:
            conn.close()

    def detect_prs(
        self,
        workout_id: str,
        user_id: str = "default"
    ) -> PRDetectionResult:
        """Detect personal records from a workout.

        Analyzes a workout for potential PRs based on thresholds from
        DEEP_ANALYSIS.md:
        - Running pace: minimum 1km distance
        - Running distance: minimum 10min duration
        - Elevation: minimum 3km distance

        Args:
            workout_id: ID of the workout to analyze
            user_id: User identifier

        Returns:
            PRDetectionResult with new PRs and near-PRs
        """
        conn = self._get_connection()
        try:
            # Get workout data
            workout = conn.execute("""
                SELECT
                    activity_id,
                    date,
                    activity_name,
                    activity_type,
                    distance_km,
                    duration_min,
                    pace_sec_per_km,
                    elevation_gain_m,
                    avg_power
                FROM activity_metrics
                WHERE activity_id = ?
            """, (workout_id,)).fetchone()

            if not workout:
                logger.warning(f"Workout not found: {workout_id}")
                return PRDetectionResult(
                    new_prs=[],
                    near_prs=[],
                    workout_id=workout_id,
                    has_new_pr=False
                )

            new_prs: List[PersonalRecord] = []
            near_prs: List[dict] = []

            # Map activity type
            activity_type = self._map_activity_type(workout["activity_type"])

            # Check for pace PR (for running activities with sufficient distance)
            if self._is_running_activity(workout["activity_type"]):
                if workout["distance_km"] and workout["distance_km"] >= PRThresholds.PACE_MIN_DISTANCE_M / 1000:
                    pace_pr = self._check_pace_pr(
                        conn, user_id, workout, activity_type
                    )
                    if pace_pr:
                        new_prs.append(pace_pr)
                    else:
                        near_pace = self._check_near_pace_pr(
                            conn, user_id, workout, activity_type
                        )
                        if near_pace:
                            near_prs.append(near_pace)

            # Check for distance PR (for activities with sufficient duration)
            if workout["duration_min"] and workout["duration_min"] >= PRThresholds.DISTANCE_MIN_DURATION_MIN:
                if workout["distance_km"]:
                    distance_pr = self._check_distance_pr(
                        conn, user_id, workout, activity_type
                    )
                    if distance_pr:
                        new_prs.append(distance_pr)

            # Check for elevation PR (for activities with sufficient distance)
            if workout["distance_km"] and workout["distance_km"] >= PRThresholds.ELEVATION_MIN_DISTANCE_M / 1000:
                if workout["elevation_gain_m"]:
                    elevation_pr = self._check_elevation_pr(
                        conn, user_id, workout, activity_type
                    )
                    if elevation_pr:
                        new_prs.append(elevation_pr)

            # Check for power PR (cycling/running with power)
            if workout["avg_power"] and workout["avg_power"] > 0:
                power_pr = self._check_power_pr(
                    conn, user_id, workout, activity_type
                )
                if power_pr:
                    new_prs.append(power_pr)

            # Save new PRs
            for pr in new_prs:
                self._save_pr(conn, pr)

            conn.commit()

            return PRDetectionResult(
                new_prs=new_prs,
                near_prs=near_prs,
                workout_id=workout_id,
                has_new_pr=len(new_prs) > 0
            )

        finally:
            conn.close()

    def _is_running_activity(self, activity_type: str) -> bool:
        """Check if activity is a running type."""
        running_types = ["running", "trail_running", "treadmill_running"]
        return activity_type.lower() in running_types if activity_type else False

    def _map_activity_type(self, activity_type: str) -> ActivityType:
        """Map raw activity type to ActivityType enum."""
        if not activity_type:
            return ActivityType.OTHER

        activity_lower = activity_type.lower()
        mapping = {
            "running": ActivityType.RUNNING,
            "trail_running": ActivityType.TRAIL_RUNNING,
            "cycling": ActivityType.CYCLING,
            "swimming": ActivityType.SWIMMING,
            "walking": ActivityType.WALKING,
            "hiking": ActivityType.HIKING,
        }
        return mapping.get(activity_lower, ActivityType.OTHER)

    def _check_pace_pr(
        self,
        conn: sqlite3.Connection,
        user_id: str,
        workout: sqlite3.Row,
        activity_type: ActivityType
    ) -> Optional[PersonalRecord]:
        """Check if workout contains a pace PR."""
        current_pace = workout["pace_sec_per_km"]
        if not current_pace or current_pace <= 0:
            return None

        # Get current best pace for this activity type
        current_best = conn.execute("""
            SELECT value
            FROM personal_records
            WHERE user_id = ?
            AND pr_type = ?
            AND activity_type = ?
            ORDER BY value ASC
            LIMIT 1
        """, (user_id, PRType.PACE.value, activity_type.value)).fetchone()

        if current_best is None or current_pace < current_best["value"]:
            previous_value = current_best["value"] if current_best else None
            improvement = previous_value - current_pace if previous_value else None
            improvement_pct = (improvement / previous_value * 100) if previous_value and improvement else None

            return PersonalRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                pr_type=PRType.PACE,
                activity_type=activity_type,
                value=current_pace,
                unit="sec/km",
                workout_id=workout["activity_id"],
                achieved_at=datetime.now(),
                previous_value=previous_value,
                improvement=improvement,
                improvement_percent=improvement_pct,
                workout_name=workout["activity_name"],
                workout_date=workout["date"]
            )

        return None

    def _check_near_pace_pr(
        self,
        conn: sqlite3.Connection,
        user_id: str,
        workout: sqlite3.Row,
        activity_type: ActivityType
    ) -> Optional[dict]:
        """Check if workout is near a pace PR."""
        current_pace = workout["pace_sec_per_km"]
        if not current_pace or current_pace <= 0:
            return None

        current_best = conn.execute("""
            SELECT value
            FROM personal_records
            WHERE user_id = ?
            AND pr_type = ?
            AND activity_type = ?
            ORDER BY value ASC
            LIMIT 1
        """, (user_id, PRType.PACE.value, activity_type.value)).fetchone()

        if current_best:
            threshold = current_best["value"] * (1 + PRThresholds.NEAR_PR_THRESHOLD_PERCENT / 100)
            if current_pace <= threshold:
                return {
                    "pr_type": PRType.PACE.value,
                    "current_value": current_pace,
                    "best_value": current_best["value"],
                    "difference": current_pace - current_best["value"],
                    "difference_percent": (current_pace - current_best["value"]) / current_best["value"] * 100,
                    "unit": "sec/km"
                }

        return None

    def _check_distance_pr(
        self,
        conn: sqlite3.Connection,
        user_id: str,
        workout: sqlite3.Row,
        activity_type: ActivityType
    ) -> Optional[PersonalRecord]:
        """Check if workout contains a distance PR."""
        current_distance = workout["distance_km"]
        if not current_distance or current_distance <= 0:
            return None

        # Convert to meters for storage
        distance_m = current_distance * 1000

        current_best = conn.execute("""
            SELECT value
            FROM personal_records
            WHERE user_id = ?
            AND pr_type = ?
            AND activity_type = ?
            ORDER BY value DESC
            LIMIT 1
        """, (user_id, PRType.DISTANCE.value, activity_type.value)).fetchone()

        if current_best is None or distance_m > current_best["value"]:
            previous_value = current_best["value"] if current_best else None
            improvement = distance_m - previous_value if previous_value else None
            improvement_pct = (improvement / previous_value * 100) if previous_value and improvement else None

            return PersonalRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                pr_type=PRType.DISTANCE,
                activity_type=activity_type,
                value=distance_m,
                unit="m",
                workout_id=workout["activity_id"],
                achieved_at=datetime.now(),
                previous_value=previous_value,
                improvement=improvement,
                improvement_percent=improvement_pct,
                workout_name=workout["activity_name"],
                workout_date=workout["date"]
            )

        return None

    def _check_elevation_pr(
        self,
        conn: sqlite3.Connection,
        user_id: str,
        workout: sqlite3.Row,
        activity_type: ActivityType
    ) -> Optional[PersonalRecord]:
        """Check if workout contains an elevation gain PR."""
        current_elevation = workout["elevation_gain_m"]
        if not current_elevation or current_elevation <= 0:
            return None

        current_best = conn.execute("""
            SELECT value
            FROM personal_records
            WHERE user_id = ?
            AND pr_type = ?
            AND activity_type = ?
            ORDER BY value DESC
            LIMIT 1
        """, (user_id, PRType.ELEVATION.value, activity_type.value)).fetchone()

        if current_best is None or current_elevation > current_best["value"]:
            previous_value = current_best["value"] if current_best else None
            improvement = current_elevation - previous_value if previous_value else None
            improvement_pct = (improvement / previous_value * 100) if previous_value and improvement else None

            return PersonalRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                pr_type=PRType.ELEVATION,
                activity_type=activity_type,
                value=current_elevation,
                unit="m",
                workout_id=workout["activity_id"],
                achieved_at=datetime.now(),
                previous_value=previous_value,
                improvement=improvement,
                improvement_percent=improvement_pct,
                workout_name=workout["activity_name"],
                workout_date=workout["date"]
            )

        return None

    def _check_power_pr(
        self,
        conn: sqlite3.Connection,
        user_id: str,
        workout: sqlite3.Row,
        activity_type: ActivityType
    ) -> Optional[PersonalRecord]:
        """Check if workout contains a power PR."""
        current_power = workout["avg_power"]
        if not current_power or current_power <= 0:
            return None

        current_best = conn.execute("""
            SELECT value
            FROM personal_records
            WHERE user_id = ?
            AND pr_type = ?
            AND activity_type = ?
            ORDER BY value DESC
            LIMIT 1
        """, (user_id, PRType.POWER.value, activity_type.value)).fetchone()

        if current_best is None or current_power > current_best["value"]:
            previous_value = current_best["value"] if current_best else None
            improvement = current_power - previous_value if previous_value else None
            improvement_pct = (improvement / previous_value * 100) if previous_value and improvement else None

            return PersonalRecord(
                id=str(uuid.uuid4()),
                user_id=user_id,
                pr_type=PRType.POWER,
                activity_type=activity_type,
                value=current_power,
                unit="W",
                workout_id=workout["activity_id"],
                achieved_at=datetime.now(),
                previous_value=previous_value,
                improvement=improvement,
                improvement_percent=improvement_pct,
                workout_name=workout["activity_name"],
                workout_date=workout["date"]
            )

        return None

    def _save_pr(self, conn: sqlite3.Connection, pr: PersonalRecord) -> None:
        """Save a personal record to the database."""
        conn.execute("""
            INSERT INTO personal_records (
                id, user_id, pr_type, activity_type, value, unit,
                workout_id, achieved_at, previous_value, improvement,
                improvement_percent, workout_name, workout_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pr.id,
            pr.user_id,
            pr.pr_type.value,
            pr.activity_type.value,
            pr.value,
            pr.unit,
            pr.workout_id,
            pr.achieved_at.isoformat(),
            pr.previous_value,
            pr.improvement,
            pr.improvement_percent,
            pr.workout_name,
            pr.workout_date
        ))

    def get_user_prs(
        self,
        user_id: str = "default",
        pr_type: Optional[PRType] = None,
        activity_type: Optional[ActivityType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[PersonalRecord]:
        """Get personal records for a user.

        Args:
            user_id: User identifier
            pr_type: Filter by PR type
            activity_type: Filter by activity type
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of personal records
        """
        conn = self._get_connection()
        try:
            query = """
                SELECT *
                FROM personal_records
                WHERE user_id = ?
            """
            params: List[Any] = [user_id]

            if pr_type:
                query += " AND pr_type = ?"
                params.append(pr_type.value)

            if activity_type:
                query += " AND activity_type = ?"
                params.append(activity_type.value)

            query += " ORDER BY achieved_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(query, params).fetchall()

            return [self._row_to_pr(row) for row in rows]

        finally:
            conn.close()

    def get_recent_prs(
        self,
        user_id: str = "default",
        days: int = 30
    ) -> List[PersonalRecord]:
        """Get recent personal records.

        Args:
            user_id: User identifier
            days: Number of days to look back

        Returns:
            List of recent personal records
        """
        conn = self._get_connection()
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            rows = conn.execute("""
                SELECT *
                FROM personal_records
                WHERE user_id = ?
                AND achieved_at >= ?
                ORDER BY achieved_at DESC
            """, (user_id, cutoff_date)).fetchall()

            return [self._row_to_pr(row) for row in rows]

        finally:
            conn.close()

    def get_pr_summary(self, user_id: str = "default") -> PRSummary:
        """Get summary of user's personal records.

        Args:
            user_id: User identifier

        Returns:
            Summary of personal records
        """
        conn = self._get_connection()
        try:
            # Total count
            total = conn.execute("""
                SELECT COUNT(*) as count
                FROM personal_records
                WHERE user_id = ?
            """, (user_id,)).fetchone()["count"]

            # Recent count (last 30 days)
            cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
            recent = conn.execute("""
                SELECT COUNT(*) as count
                FROM personal_records
                WHERE user_id = ?
                AND achieved_at >= ?
            """, (user_id, cutoff_date)).fetchone()["count"]

            # Count by type
            type_counts = conn.execute("""
                SELECT pr_type, COUNT(*) as count
                FROM personal_records
                WHERE user_id = ?
                GROUP BY pr_type
            """, (user_id,)).fetchall()

            prs_by_type = {row["pr_type"]: row["count"] for row in type_counts}

            # Latest PR
            latest_row = conn.execute("""
                SELECT *
                FROM personal_records
                WHERE user_id = ?
                ORDER BY achieved_at DESC
                LIMIT 1
            """, (user_id,)).fetchone()

            latest_pr = self._row_to_pr(latest_row) if latest_row else None

            return PRSummary(
                total_prs=total,
                recent_prs=recent,
                prs_by_type=prs_by_type,
                latest_pr=latest_pr
            )

        finally:
            conn.close()

    def compare_to_best(
        self,
        workout_id: str,
        user_id: str = "default"
    ) -> PRComparisonResult:
        """Compare a workout to existing personal records.

        Args:
            workout_id: ID of the workout to compare
            user_id: User identifier

        Returns:
            Comparison results showing how workout compares to PRs
        """
        conn = self._get_connection()
        try:
            # Get workout data
            workout = conn.execute("""
                SELECT
                    activity_id,
                    activity_type,
                    distance_km,
                    duration_min,
                    pace_sec_per_km,
                    elevation_gain_m,
                    avg_power
                FROM activity_metrics
                WHERE activity_id = ?
            """, (workout_id,)).fetchone()

            if not workout:
                return PRComparisonResult(
                    workout_id=workout_id,
                    comparisons=[],
                    potential_prs=[]
                )

            activity_type = self._map_activity_type(workout["activity_type"])
            comparisons = []
            potential_prs = []

            # Compare pace
            if workout["pace_sec_per_km"]:
                pace_pr = conn.execute("""
                    SELECT value
                    FROM personal_records
                    WHERE user_id = ?
                    AND pr_type = ?
                    AND activity_type = ?
                    ORDER BY value ASC
                    LIMIT 1
                """, (user_id, PRType.PACE.value, activity_type.value)).fetchone()

                if pace_pr:
                    diff = workout["pace_sec_per_km"] - pace_pr["value"]
                    diff_pct = diff / pace_pr["value"] * 100
                    comparisons.append({
                        "pr_type": PRType.PACE.value,
                        "workout_value": workout["pace_sec_per_km"],
                        "pr_value": pace_pr["value"],
                        "difference": diff,
                        "difference_percent": diff_pct,
                        "unit": "sec/km",
                        "is_better": diff < 0
                    })

            # Compare distance
            if workout["distance_km"]:
                distance_m = workout["distance_km"] * 1000
                dist_pr = conn.execute("""
                    SELECT value
                    FROM personal_records
                    WHERE user_id = ?
                    AND pr_type = ?
                    AND activity_type = ?
                    ORDER BY value DESC
                    LIMIT 1
                """, (user_id, PRType.DISTANCE.value, activity_type.value)).fetchone()

                if dist_pr:
                    diff = distance_m - dist_pr["value"]
                    diff_pct = diff / dist_pr["value"] * 100
                    comparisons.append({
                        "pr_type": PRType.DISTANCE.value,
                        "workout_value": distance_m,
                        "pr_value": dist_pr["value"],
                        "difference": diff,
                        "difference_percent": diff_pct,
                        "unit": "m",
                        "is_better": diff > 0
                    })

            return PRComparisonResult(
                workout_id=workout_id,
                comparisons=comparisons,
                potential_prs=potential_prs
            )

        finally:
            conn.close()

    def get_best_prs(self, user_id: str = "default") -> Dict[str, PersonalRecord]:
        """Get the current best PR for each type/activity combination.

        Args:
            user_id: User identifier

        Returns:
            Dictionary mapping pr_type:activity_type to best PR
        """
        conn = self._get_connection()
        try:
            # For pace, lower is better; for others, higher is better
            best_prs = {}

            # Get best pace PRs (lowest value)
            pace_rows = conn.execute("""
                SELECT *
                FROM personal_records
                WHERE user_id = ?
                AND pr_type = ?
                AND value = (
                    SELECT MIN(value)
                    FROM personal_records p2
                    WHERE p2.user_id = personal_records.user_id
                    AND p2.pr_type = personal_records.pr_type
                    AND p2.activity_type = personal_records.activity_type
                )
            """, (user_id, PRType.PACE.value)).fetchall()

            for row in pace_rows:
                key = f"{row['pr_type']}:{row['activity_type']}"
                best_prs[key] = self._row_to_pr(row)

            # Get best for other PR types (highest value)
            for pr_type in [PRType.DISTANCE, PRType.DURATION, PRType.ELEVATION, PRType.POWER]:
                other_rows = conn.execute("""
                    SELECT *
                    FROM personal_records
                    WHERE user_id = ?
                    AND pr_type = ?
                    AND value = (
                        SELECT MAX(value)
                        FROM personal_records p2
                        WHERE p2.user_id = personal_records.user_id
                        AND p2.pr_type = personal_records.pr_type
                        AND p2.activity_type = personal_records.activity_type
                    )
                """, (user_id, pr_type.value)).fetchall()

                for row in other_rows:
                    key = f"{row['pr_type']}:{row['activity_type']}"
                    best_prs[key] = self._row_to_pr(row)

            return best_prs

        finally:
            conn.close()

    def _row_to_pr(self, row: sqlite3.Row) -> PersonalRecord:
        """Convert a database row to a PersonalRecord."""
        return PersonalRecord(
            id=row["id"],
            user_id=row["user_id"],
            pr_type=PRType(row["pr_type"]),
            activity_type=ActivityType(row["activity_type"]),
            value=row["value"],
            unit=row["unit"],
            workout_id=row["workout_id"],
            achieved_at=datetime.fromisoformat(row["achieved_at"]),
            previous_value=row["previous_value"],
            improvement=row["improvement"],
            improvement_percent=row["improvement_percent"],
            workout_name=row["workout_name"],
            workout_date=row["workout_date"]
        )
