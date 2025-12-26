"""
AI Training Coach Service

Integrates all analysis into recommendations:
1. Fetches wellness data from whoop-dashboard's database
2. Gets fitness metrics from training-analyzer's database
3. Gets recent activities
4. Calculates readiness
5. Generates workout recommendation
6. Produces natural language output
"""

import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from ..db.database import TrainingDatabase, DailyFitnessMetrics, ActivityMetrics
from ..recommendations.readiness import (
    calculate_readiness,
    ReadinessResult,
    ReadinessFactors,
)
from ..recommendations.workout import (
    recommend_workout,
    WorkoutRecommendation,
    WorkoutType,
)
from ..recommendations.explain import (
    explain_readiness,
    explain_workout,
    generate_daily_narrative,
    format_training_status,
    format_readiness_factors,
    generate_weekly_narrative,
)


def find_wellness_db() -> Optional[Path]:
    """
    Find the wellness database from whoop-dashboard.

    Checks:
    1. WELLNESS_DB_PATH environment variable
    2. Default location relative to project structure
    """
    # Check environment variable
    env_path = os.environ.get("WELLNESS_DB_PATH")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    # Try to find relative to this file
    # training-analyzer/src/training_analyzer/services/coach.py
    # -> whoop-dashboard/wellness.db
    project_root = Path(__file__).parent.parent.parent.parent.parent
    possible_paths = [
        project_root / "whoop-dashboard" / "wellness.db",
        project_root / "wellness.db",
        Path.home() / ".garmin_insights" / "wellness.db",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None


class CoachService:
    """AI Training Coach - integrates all analysis into recommendations."""

    def __init__(
        self,
        training_db: Optional[TrainingDatabase] = None,
        wellness_db_path: Optional[str] = None,
    ):
        """
        Initialize the coach service.

        Args:
            training_db: TrainingDatabase instance (created if not provided)
            wellness_db_path: Path to wellness database (auto-detected if not provided)
        """
        self.training_db = training_db or TrainingDatabase()
        self._wellness_db_path = wellness_db_path

    @property
    def wellness_db_path(self) -> Optional[Path]:
        """Get the wellness database path."""
        if self._wellness_db_path:
            return Path(self._wellness_db_path)
        return find_wellness_db()

    @contextmanager
    def _get_wellness_connection(self):
        """Get connection to wellness database."""
        if not self.wellness_db_path or not self.wellness_db_path.exists():
            yield None
            return

        conn = sqlite3.connect(self.wellness_db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def get_wellness_data(self, target_date: str) -> Optional[Dict[str, Any]]:
        """
        Get wellness data for a specific date.

        Args:
            target_date: Date string (YYYY-MM-DD)

        Returns:
            Dictionary with hrv, sleep, stress, activity data, or None
        """
        with self._get_wellness_connection() as conn:
            if conn is None:
                return None

            try:
                # Get HRV data
                hrv_row = conn.execute(
                    "SELECT * FROM hrv_data WHERE date = ?",
                    (target_date,)
                ).fetchone()

                # Get sleep data
                sleep_row = conn.execute(
                    "SELECT * FROM sleep_data WHERE date = ?",
                    (target_date,)
                ).fetchone()

                # Get stress data
                stress_row = conn.execute(
                    "SELECT * FROM stress_data WHERE date = ?",
                    (target_date,)
                ).fetchone()

                # Get activity data
                activity_row = conn.execute(
                    "SELECT * FROM activity_data WHERE date = ?",
                    (target_date,)
                ).fetchone()

                # Get training readiness if available
                tr_row = conn.execute(
                    """SELECT training_readiness_score, training_readiness_level
                       FROM daily_wellness WHERE date = ?""",
                    (target_date,)
                ).fetchone()

                result = {}

                if hrv_row:
                    result["hrv"] = {
                        "hrv_last_night_avg": hrv_row["hrv_last_night_avg"],
                        "hrv_weekly_avg": hrv_row["hrv_weekly_avg"],
                        "hrv_status": hrv_row["hrv_status"],
                    }

                if sleep_row:
                    total_seconds = sleep_row["total_sleep_seconds"] or 0
                    deep_seconds = sleep_row["deep_sleep_seconds"] or 0
                    rem_seconds = sleep_row["rem_sleep_seconds"] or 0

                    result["sleep"] = {
                        "total_sleep_hours": round(total_seconds / 3600, 2),
                        "deep_sleep_pct": round(
                            deep_seconds / max(1, total_seconds) * 100, 1
                        ),
                        "rem_sleep_pct": round(
                            rem_seconds / max(1, total_seconds) * 100, 1
                        ),
                        "sleep_efficiency": sleep_row["sleep_efficiency"],
                        "sleep_score": sleep_row["sleep_score"],
                    }

                if stress_row:
                    result["stress"] = {
                        "avg_stress_level": stress_row["avg_stress_level"],
                        "body_battery_charged": stress_row["body_battery_charged"],
                        "body_battery_drained": stress_row["body_battery_drained"],
                        "body_battery_high": stress_row["body_battery_high"],
                        "body_battery_low": stress_row["body_battery_low"],
                        "rest_stress_duration": stress_row["rest_stress_duration"],
                        "high_stress_duration": stress_row["high_stress_duration"],
                    }

                if tr_row:
                    result["training_readiness"] = {
                        "score": tr_row["training_readiness_score"],
                        "level": tr_row["training_readiness_level"],
                    }

                return result if result else None

            except sqlite3.Error:
                return None

    def get_fitness_metrics(
        self, target_date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get fitness metrics for a date.

        Args:
            target_date: Date string (defaults to latest available)

        Returns:
            Dictionary with ctl, atl, tsb, acwr, risk_zone
        """
        if target_date:
            metrics = self.training_db.get_fitness_metrics(target_date)
        else:
            metrics = self.training_db.get_latest_fitness_metrics()

        if not metrics:
            return None

        return {
            "date": metrics.date,
            "daily_load": metrics.daily_load,
            "ctl": metrics.ctl,
            "atl": metrics.atl,
            "tsb": metrics.tsb,
            "acwr": metrics.acwr,
            "risk_zone": metrics.risk_zone,
        }

    def get_recent_activities(
        self, days: int = 7, end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent activities.

        Args:
            days: Number of days to look back
            end_date: End date (defaults to today)

        Returns:
            List of activity dictionaries
        """
        if end_date is None:
            end_date = date.today()

        start_date = end_date - timedelta(days=days)

        activities = self.training_db.get_activities_range(
            start_date.isoformat(),
            end_date.isoformat(),
        )

        return [a.to_dict() for a in activities]

    def get_weekly_load(
        self, week_start: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get training load for the current week.

        Args:
            week_start: Start of week (defaults to most recent Monday)

        Returns:
            Dictionary with weekly load stats
        """
        if week_start is None:
            today = date.today()
            # Get most recent Monday
            week_start = today - timedelta(days=today.weekday())

        week_end = week_start + timedelta(days=6)

        daily_loads = self.training_db.get_daily_load_totals(
            week_start.isoformat(),
            week_end.isoformat(),
        )

        total_load = sum(d.get("total_hrss", 0) or 0 for d in daily_loads)
        workout_count = sum(d.get("activity_count", 0) or 0 for d in daily_loads)

        return {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "total_load": total_load,
            "workout_count": workout_count,
            "daily_loads": daily_loads,
        }

    def _calculate_target_weekly_load(self) -> float:
        """
        Calculate target weekly load based on recent CTL.

        Target weekly load should roughly maintain CTL.
        """
        latest = self.training_db.get_latest_fitness_metrics()
        if not latest or latest.ctl == 0:
            return 300.0  # Default target

        # To maintain CTL, weekly load should be about CTL * 7 * decay_factor
        # Simplified: target ~= CTL * 7
        return latest.ctl * 7

    def _calculate_days_since_long(
        self, activities: List[Dict[str, Any]], target_date: date
    ) -> int:
        """Calculate days since last long workout (>60 min)."""
        long_threshold_min = 60.0

        last_long_date = None
        for activity in activities:
            duration = activity.get("duration_min", 0) or 0
            if duration >= long_threshold_min:
                activity_date_str = activity.get("date")
                if activity_date_str:
                    try:
                        activity_date = datetime.strptime(
                            activity_date_str, "%Y-%m-%d"
                        ).date()
                        if last_long_date is None or activity_date > last_long_date:
                            last_long_date = activity_date
                    except ValueError:
                        continue

        if last_long_date is None:
            return 7  # Assume a week since last long run

        return max(0, (target_date - last_long_date).days)

    def get_daily_briefing(
        self, target_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get complete daily training briefing.

        Returns:
            {
                'date': '2024-01-15',
                'readiness': {
                    'score': 75,
                    'zone': 'green',
                    'factors': {...}
                },
                'recommendation': {
                    'workout_type': 'tempo',
                    'duration': 45,
                    'target_intensity': 'Zone 3-4',
                    'reason': 'Good recovery, time to build fitness'
                },
                'training_status': {
                    'ctl': 45.2,
                    'atl': 52.1,
                    'tsb': -6.9,
                    'acwr': 1.15,
                    'risk_zone': 'optimal'
                },
                'narrative': "You're well recovered and ready for quality work..."
            }
        """
        if target_date is None:
            target_date = date.today()

        date_str = target_date.isoformat()

        # Gather all data
        wellness_data = self.get_wellness_data(date_str)
        fitness_metrics = self.get_fitness_metrics(date_str)
        recent_activities = self.get_recent_activities(days=7, end_date=target_date)
        weekly_load = self.get_weekly_load()

        # Calculate readiness
        readiness = calculate_readiness(
            wellness_data=wellness_data,
            fitness_metrics=fitness_metrics,
            recent_activities=recent_activities,
            target_date=target_date,
        )

        # Generate workout recommendation
        # Get parameters for recommendation
        acwr = fitness_metrics.get("acwr", 1.0) if fitness_metrics else 1.0
        tsb = fitness_metrics.get("tsb", 0.0) if fitness_metrics else 0.0
        days_since_hard = readiness.factors.recovery_days
        days_since_long = self._calculate_days_since_long(recent_activities, target_date)
        weekly_load_so_far = weekly_load.get("total_load", 0)
        target_weekly_load = self._calculate_target_weekly_load()

        recommendation = recommend_workout(
            readiness_score=readiness.overall_score,
            acwr=acwr,
            tsb=tsb,
            days_since_hard=days_since_hard,
            days_since_long=days_since_long,
            weekly_load_so_far=weekly_load_so_far,
            target_weekly_load=target_weekly_load,
            day_of_week=target_date.weekday(),
        )

        # Generate narrative
        narrative = generate_daily_narrative(
            readiness=readiness,
            recommendation=recommendation,
            fitness_status=fitness_metrics,
        )

        return {
            "date": date_str,
            "readiness": {
                "score": round(readiness.overall_score, 1),
                "zone": readiness.zone,
                "factors": readiness.factors.to_dict(),
                "recommendation": readiness.recommendation,
                "explanation": readiness.explanation,
            },
            "recommendation": {
                "workout_type": recommendation.workout_type.value,
                "duration_min": recommendation.duration_min,
                "intensity_description": recommendation.intensity_description,
                "hr_zone_target": recommendation.hr_zone_target,
                "reason": recommendation.reason,
                "alternatives": recommendation.alternatives,
                "warnings": recommendation.warnings,
            },
            "training_status": fitness_metrics,
            "weekly_load": {
                "current": weekly_load_so_far,
                "target": target_weekly_load,
                "workout_count": weekly_load.get("workout_count", 0),
            },
            "narrative": narrative,
            "data_sources": {
                "wellness_available": wellness_data is not None,
                "fitness_available": fitness_metrics is not None,
                "activities_count": len(recent_activities),
            },
        }

    def get_weekly_summary(
        self, weeks_back: int = 0
    ) -> Dict[str, Any]:
        """
        Get weekly training summary with trends.

        Args:
            weeks_back: How many weeks ago (0 = current week)

        Returns:
            Weekly summary dictionary
        """
        # Calculate week dates
        today = date.today()
        current_monday = today - timedelta(days=today.weekday())
        target_monday = current_monday - timedelta(weeks=weeks_back)
        target_sunday = target_monday + timedelta(days=6)

        # Get activities for the week
        activities = self.training_db.get_activities_range(
            target_monday.isoformat(),
            target_sunday.isoformat(),
        )

        # Get fitness metrics
        start_fitness = self.training_db.get_fitness_metrics(target_monday.isoformat())
        end_fitness = self.training_db.get_fitness_metrics(target_sunday.isoformat())

        # Calculate stats
        total_load = sum(a.hrss or 0 for a in activities)
        total_duration = sum(a.duration_min or 0 for a in activities)
        total_distance = sum(a.distance_km or 0 for a in activities)

        # Count workout types
        hard_days = sum(
            1 for a in activities if (a.hrss or 0) >= 75 or (a.trimp or 0) >= 100
        )

        # Get unique workout days
        workout_dates = set(a.date for a in activities)
        easy_days = len(workout_dates) - hard_days
        rest_days = 7 - len(workout_dates)

        # CTL change
        ctl_start = start_fitness.ctl if start_fitness else 0
        ctl_end = end_fitness.ctl if end_fitness else 0
        ctl_change = ctl_end - ctl_start

        # Get wellness/readiness data for the week (average)
        readiness_scores = []
        for day_offset in range(7):
            day = target_monday + timedelta(days=day_offset)
            wellness = self.get_wellness_data(day.isoformat())
            if wellness:
                # Simple recovery proxy from body battery
                bb = (
                    wellness.get("stress", {}).get("body_battery_charged")
                    or wellness.get("stress", {}).get("body_battery_high")
                )
                if bb:
                    readiness_scores.append(bb)

        avg_readiness = (
            sum(readiness_scores) / len(readiness_scores) if readiness_scores else 0
        )

        # Target load (based on previous week or CTL)
        target_load = self._calculate_target_weekly_load()

        weekly_stats = {
            "week_start": target_monday.isoformat(),
            "week_end": target_sunday.isoformat(),
            "total_load": total_load,
            "target_load": target_load,
            "total_duration_min": total_duration,
            "total_distance_km": total_distance,
            "workout_count": len(activities),
            "hard_days": hard_days,
            "easy_days": easy_days,
            "rest_days": rest_days,
            "ctl_start": ctl_start,
            "ctl_end": ctl_end,
            "ctl_change": ctl_change,
            "avg_readiness": avg_readiness,
        }

        # Generate narrative
        narrative = generate_weekly_narrative(weekly_stats)

        return {
            **weekly_stats,
            "narrative": narrative,
            "activities": [a.to_dict() for a in activities],
        }

    def get_why_explanation(
        self, target_date: Optional[date] = None
    ) -> str:
        """
        Get detailed explanation of why today's workout was recommended.

        Args:
            target_date: Date to explain (defaults to today)

        Returns:
            Detailed explanation string
        """
        briefing = self.get_daily_briefing(target_date)

        parts = []

        # Readiness explanation
        factors = ReadinessFactors(**briefing["readiness"]["factors"])
        readiness_explanation = explain_readiness(
            factors,
            briefing["readiness"]["score"],
        )
        parts.append("READINESS ANALYSIS")
        parts.append("=" * 40)
        parts.append(readiness_explanation)
        parts.append("")

        # Readiness factors breakdown
        parts.append(format_readiness_factors(factors))
        parts.append("")

        # Training status
        if briefing["training_status"]:
            ts = briefing["training_status"]
            parts.append(
                format_training_status(
                    ctl=ts["ctl"],
                    atl=ts["atl"],
                    tsb=ts["tsb"],
                    acwr=ts["acwr"],
                    risk_zone=ts["risk_zone"],
                )
            )
            parts.append("")

        # Workout recommendation details
        rec = briefing["recommendation"]
        recommendation = WorkoutRecommendation(
            workout_type=WorkoutType(rec["workout_type"]),
            duration_min=rec["duration_min"],
            intensity_description=rec["intensity_description"],
            hr_zone_target=rec["hr_zone_target"],
            reason=rec["reason"],
            alternatives=rec["alternatives"],
            warnings=rec["warnings"],
        )

        parts.append("WORKOUT RECOMMENDATION")
        parts.append("=" * 40)
        parts.append(explain_workout(recommendation))

        return "\n".join(parts)

    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get current status summary (for CLI status command).

        Returns:
            Summary with key metrics and status
        """
        today = date.today()
        briefing = self.get_daily_briefing(today)

        return {
            "date": today.isoformat(),
            "readiness_score": briefing["readiness"]["score"],
            "readiness_zone": briefing["readiness"]["zone"],
            "recommended_workout": briefing["recommendation"]["workout_type"],
            "recommended_duration": briefing["recommendation"]["duration_min"],
            "training_status": briefing["training_status"],
            "weekly_load": briefing["weekly_load"],
            "narrative": briefing["narrative"],
            "data_sources": briefing["data_sources"],
        }

    def get_llm_context(
        self, target_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive athlete context for LLM prompt injection.

        This method aggregates all relevant data for contextualizing
        LLM responses with personalized athlete information.

        Args:
            target_date: Date for context (defaults to today)

        Returns:
            Dictionary with structured context for LLM prompts:
            - fitness_metrics: CTL, ATL, TSB, ACWR, risk zone
            - physiology: max_hr, rest_hr, lthr, age, gender
            - hr_zones: Calculated HR zones (Karvonen method)
            - training_paces: Paces based on race goals
            - race_goals: Active race goals with progress
            - readiness: Current readiness score and zone
            - recent_activities: Summary of recent training
        """
        if target_date is None:
            target_date = date.today()

        date_str = target_date.isoformat()

        # Get user profile for physiological data
        profile = self.training_db.get_user_profile()

        # Get fitness metrics
        fitness_metrics = self.get_fitness_metrics(date_str)

        # Get wellness and readiness
        wellness_data = self.get_wellness_data(date_str)
        recent_activities = self.get_recent_activities(days=7, end_date=target_date)

        from ..recommendations.readiness import calculate_readiness

        readiness = calculate_readiness(
            wellness_data=wellness_data,
            fitness_metrics=fitness_metrics,
            recent_activities=recent_activities,
            target_date=target_date,
        )

        # Build HR zones (Karvonen method)
        hr_zones = []
        if profile:
            max_hr = profile.max_hr or 185
            rest_hr = profile.rest_hr or 55
            hr_reserve = max_hr - rest_hr

            zone_defs = [
                (1, "Recovery", 0.50, 0.60, "Active recovery, easy breathing"),
                (2, "Aerobic", 0.60, 0.70, "Base building, conversational pace"),
                (3, "Tempo", 0.70, 0.80, "Comfortably hard, lactate threshold"),
                (4, "Threshold", 0.80, 0.90, "Hard, sustainable for 20-30 min"),
                (5, "VO2max", 0.90, 1.00, "Very hard, 3-8 min efforts"),
            ]

            for zone_num, name, low_pct, high_pct, desc in zone_defs:
                min_hr = int(rest_hr + hr_reserve * low_pct)
                max_hr_zone = int(rest_hr + hr_reserve * high_pct)
                hr_zones.append({
                    "zone": zone_num,
                    "name": name,
                    "min_hr": min_hr,
                    "max_hr": max_hr_zone,
                    "description": desc,
                })

        # Get race goals and training paces
        goals = self.training_db.get_race_goals()
        training_paces = []
        vdot = None

        if goals:
            from ..analysis.goals import (
                calculate_training_paces,
                calculate_vdot,
                RaceGoal,
                RaceDistance,
            )

            # Use first goal to calculate paces
            first_goal_data = goals[0]
            distance_str = str(first_goal_data.get("distance", "10k"))
            distance = RaceDistance.from_string(distance_str) or RaceDistance.TEN_K
            target_time = first_goal_data.get("target_time_sec", 3000)

            # Parse race date
            race_date_str = first_goal_data.get("race_date")
            if race_date_str:
                if isinstance(race_date_str, str):
                    race_date_parsed = datetime.strptime(
                        race_date_str, "%Y-%m-%d"
                    ).date()
                else:
                    race_date_parsed = race_date_str
            else:
                race_date_parsed = date.today() + timedelta(days=90)

            goal = RaceGoal(
                race_date=race_date_parsed,
                distance=distance,
                target_time_sec=target_time,
            )

            # Calculate VDOT
            vdot = calculate_vdot(target_time, distance)

            # Calculate training paces
            paces = calculate_training_paces(goal)
            for pace_type, pace_data in paces.items():
                training_paces.append({
                    "name": pace_data["name"],
                    "pace_sec_per_km": pace_data["pace_sec"],
                    "pace_formatted": pace_data["pace_formatted"],
                    "hr_zone": pace_data["hr_zone"],
                    "description": pace_data["description"],
                    "purpose": pace_data["purpose"],
                })

        # Build recent activity summary
        recent_summary = {
            "count": len(recent_activities),
            "total_distance_km": sum(
                a.get("distance_km", 0) or 0 for a in recent_activities
            ),
            "total_duration_min": sum(
                a.get("duration_min", 0) or 0 for a in recent_activities
            ),
            "total_load": sum(
                a.get("hrss", 0) or 0 for a in recent_activities
            ),
        }

        # Build race goals response
        race_goals_data = []
        for goal_data in goals[:3]:  # Max 3 goals
            race_goals_data.append({
                "distance": goal_data.get("distance_name", goal_data.get("distance")),
                "target_time_sec": goal_data.get("target_time_sec"),
                "target_time_formatted": goal_data.get("target_time_formatted"),
                "target_pace_formatted": goal_data.get("target_pace_formatted"),
                "race_date": goal_data.get("race_date"),
                "weeks_remaining": goal_data.get("weeks_until_race"),
            })

        return {
            "fitness_metrics": fitness_metrics or {
                "ctl": 0,
                "atl": 0,
                "tsb": 0,
                "acwr": 1.0,
                "risk_zone": "unknown",
            },
            "physiology": {
                "max_hr": profile.max_hr if profile else 185,
                "rest_hr": profile.rest_hr if profile else 55,
                "lthr": profile.threshold_hr if profile else 165,
                "age": profile.age if profile else None,
                "gender": profile.gender if profile else None,
                "weight_kg": profile.weight_kg if profile else None,
                "vdot": round(vdot, 1) if vdot else None,
            },
            "hr_zones": hr_zones,
            "training_paces": training_paces,
            "race_goals": race_goals_data,
            "readiness": {
                "score": round(readiness.overall_score, 1),
                "zone": readiness.zone,
                "recommendation": readiness.recommendation,
            },
            "recent_activities": recent_summary,
            "date": date_str,
        }
