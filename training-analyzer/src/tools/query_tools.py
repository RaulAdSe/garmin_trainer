"""
LangChain-compatible tools for the agentic AI coach.

These tools allow an AI agent to query athlete data on-demand instead of
pre-loading everything. Each tool is decorated with @tool from langchain_core.tools
and can be used directly in LangChain agents.

Tools:
- query_workouts: Query workout history with flexible filters
- query_wellness: Query wellness/recovery data
- get_athlete_profile: Get current athlete profile with fitness metrics
- get_training_patterns: Get detected training patterns
- get_fitness_metrics: Get fitness metrics time series (CTL, ATL, TSB)
- get_garmin_data: Get latest Garmin Connect data
- compare_workouts: Compare multiple workouts side-by-side
- get_workout_details: Get deep analysis of a single workout with condensed stats

Retry Logic:
- Database/API calls use the with_retry decorator for transient failure handling
- Retries use exponential backoff (0.5s, 1s, 2s max)
- Max total retry time is 5 seconds per tool call
- Validation errors are NOT retried
- Mock fallbacks are used when services are unavailable
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from .retry import with_retry, is_retryable, NonRetryableError

logger = logging.getLogger(__name__)


# ============================================================================
# Internal Database Query Functions with Retry Logic
# ============================================================================
# These functions wrap database operations with retry logic.
# They are called by the tool functions, which handle mock fallbacks.


@with_retry(max_retries=2, base_delay=0.5, max_delay=2.0)
def _query_workouts_from_db(
    sport_type: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    limit: int,
    include_laps: bool,
) -> List[Dict[str, Any]]:
    """Internal function to query workouts from database with retry."""
    from ..db.database import TrainingDatabase
    from datetime import datetime as dt

    db = TrainingDatabase()

    # Cap limit at 50 to prevent excessive data retrieval
    limit = min(limit, 50)

    # Use paginated query with activity type filter
    activity_type_filter = sport_type.lower() if sport_type else None
    activities, total = db.get_activities_paginated(
        page=1,
        page_size=limit,
        activity_type=activity_type_filter,
    )

    # Apply date filtering if provided
    if date_from or date_to:
        from_date = dt.strptime(date_from, "%Y-%m-%d").date() if date_from else None
        to_date = dt.strptime(date_to, "%Y-%m-%d").date() if date_to else None

        filtered = []
        for activity in activities:
            activity_date = activity.date
            if isinstance(activity_date, str):
                activity_date = dt.strptime(activity_date[:10], "%Y-%m-%d").date()

            if from_date and activity_date < from_date:
                continue
            if to_date and activity_date > to_date:
                continue
            filtered.append(activity)
        activities = filtered[:limit]

    results = []
    for activity in activities:
        workout_data = {
            "activity_id": activity.activity_id,
            "date": activity.date if isinstance(activity.date, str) else activity.date.isoformat(),
            "sport_type": activity.activity_type,
            "name": activity.activity_name,
            "duration_min": round(activity.duration_min, 1) if activity.duration_min else 0,
            "distance_km": round(activity.distance_km, 2) if activity.distance_km else None,
            "avg_hr": activity.avg_hr,
            "max_hr": activity.max_hr,
            "hrss": round(activity.hrss, 1) if activity.hrss else None,
            "pace_sec_km": activity.pace_sec_per_km,
            "avg_power": getattr(activity, "avg_power", None),
            "elevation_gain_m": getattr(activity, "elevation_gain_m", None),
            "workout_type": getattr(activity, "workout_type", None),
        }

        if include_laps and hasattr(activity, "laps"):
            workout_data["laps"] = activity.laps

        results.append(workout_data)

    return results


@with_retry(max_retries=2, base_delay=0.5, max_delay=2.0)
def _query_wellness_from_service(
    date_from: Optional[str],
    date_to: Optional[str],
    metrics: Optional[List[str]],
    limit: int,
) -> List[Dict[str, Any]]:
    """Internal function to query wellness data with retry."""
    from ..services.coach import CoachService

    coach = CoachService()

    # Parse dates
    end_date = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else datetime.now().date()
    start_date = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else end_date - timedelta(days=limit)

    # Cap limit
    limit = min(limit, 30)

    results = []
    current = end_date

    while current >= start_date and len(results) < limit:
        wellness_data = coach.get_wellness(current)

        if wellness_data:
            record = {
                "date": current.isoformat(),
                "hrv": wellness_data.get("hrv"),
                "rhr": wellness_data.get("resting_hr"),
                "sleep_hours": wellness_data.get("sleep_hours"),
                "sleep_quality": wellness_data.get("sleep_quality"),
                "deep_sleep_min": wellness_data.get("deep_sleep_min"),
                "rem_sleep_min": wellness_data.get("rem_sleep_min"),
                "recovery_score": wellness_data.get("recovery_score"),
                "strain": wellness_data.get("strain"),
                "stress_score": wellness_data.get("stress_score"),
                "body_battery": wellness_data.get("body_battery"),
                "spo2": wellness_data.get("spo2"),
            }

            # Filter to requested metrics if specified
            if metrics:
                record = {
                    "date": record["date"],
                    **{k: v for k, v in record.items() if k in metrics or k == "date"},
                }

            results.append(record)

        current -= timedelta(days=1)

    return results


@with_retry(max_retries=2, base_delay=0.5, max_delay=2.0)
def _get_athlete_profile_from_service() -> Dict[str, Any]:
    """Internal function to get athlete profile with retry."""
    from ..services.coach import CoachService
    from ..models.athlete_context import AthleteContext

    coach = CoachService()

    # Get LLM context which includes all athlete data
    context = coach.get_llm_context()

    if isinstance(context, AthleteContext):
        return context.to_dict()
    elif isinstance(context, dict):
        return context
    else:
        # Build profile from available data
        fitness = coach.get_fitness_metrics()
        readiness = coach.get_readiness()

        return {
            "ctl": fitness.get("ctl", 0),
            "atl": fitness.get("atl", 0),
            "tsb": fitness.get("tsb", 0),
            "acwr": fitness.get("acwr", 1.0),
            "risk_zone": fitness.get("risk_zone", "unknown"),
            "readiness_score": readiness.get("score", 50),
            "readiness_zone": readiness.get("zone", "yellow"),
            "max_hr": 185,
            "rest_hr": 55,
            "threshold_hr": 168,
        }


@with_retry(max_retries=2, base_delay=0.5, max_delay=2.0)
def _get_training_patterns_from_service(
    days: int,
    pattern_types: Optional[List[str]],
) -> Dict[str, Any]:
    """Internal function to get training patterns with retry."""
    from ..services.adaptation import TrainingPatternService

    service = TrainingPatternService()

    # Cap days
    days = min(days, 90)

    # Get patterns
    patterns = service.analyze_patterns(days=days, pattern_types=pattern_types)

    return patterns


@with_retry(max_retries=2, base_delay=0.5, max_delay=2.0)
def _get_fitness_metrics_from_db(
    days: int,
    include_daily: bool,
) -> Dict[str, Any]:
    """Internal function to get fitness metrics with retry."""
    from ..db.database import TrainingDatabase

    db = TrainingDatabase()

    # Cap days
    days = min(days, 180)

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    # Get fitness metrics using correct method name
    metrics = db.get_fitness_range(
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
    )

    if not metrics:
        return {
            "current": {"ctl": 0, "atl": 0, "tsb": 0, "acwr": 1.0},
            "error": "No fitness data available",
        }

    # Get current (most recent) values
    current = metrics[-1] if metrics else None
    current_data = {
        "ctl": round(current.ctl, 1) if current else 0,
        "atl": round(current.atl, 1) if current else 0,
        "tsb": round(current.tsb, 1) if current else 0,
        "acwr": round(current.acwr, 2) if current else 1.0,
        "risk_zone": current.risk_zone if current else "unknown",
    }

    # Calculate trends
    first_week_ctl = sum(m.ctl for m in metrics[:7]) / min(7, len(metrics))
    last_week_ctl = sum(m.ctl for m in metrics[-7:]) / min(7, len(metrics))
    ctl_change = last_week_ctl - first_week_ctl

    trends = {
        "ctl_trend": "improving" if ctl_change > 2 else "declining" if ctl_change < -2 else "stable",
        "ctl_change": round(ctl_change, 1),
        "peak_ctl": round(max(m.ctl for m in metrics), 1),
        "lowest_tsb": round(min(m.tsb for m in metrics), 1),
    }

    result = {
        "period": {
            "days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "current": current_data,
        "trends": trends,
    }

    # Add weekly summaries
    weekly = []
    week_metrics = []
    for m in metrics:
        week_metrics.append(m)
        if len(week_metrics) == 7:
            weekly.append({
                "week_ending": m.date.isoformat() if hasattr(m.date, "isoformat") else str(m.date),
                "avg_ctl": round(sum(x.ctl for x in week_metrics) / 7, 1),
                "avg_atl": round(sum(x.atl for x in week_metrics) / 7, 1),
                "avg_tsb": round(sum(x.tsb for x in week_metrics) / 7, 1),
            })
            week_metrics = []

    result["weekly"] = weekly

    # Add daily if requested
    if include_daily:
        result["daily"] = [
            {
                "date": m.date.isoformat() if hasattr(m.date, "isoformat") else str(m.date),
                "ctl": round(m.ctl, 1),
                "atl": round(m.atl, 1),
                "tsb": round(m.tsb, 1),
                "acwr": round(m.acwr, 2),
                "daily_load": round(getattr(m, "daily_load", 0), 1),
            }
            for m in metrics
        ]

    return result


@with_retry(max_retries=2, base_delay=0.5, max_delay=2.0)
def _get_garmin_data_from_service(
    data_types: Optional[List[str]],
) -> Dict[str, Any]:
    """Internal function to get Garmin data with retry."""
    from ..integrations.garmin import GarminConnectClient
    from ..services.garmin_sync_service import GarminSyncService

    service = GarminSyncService()

    # Get cached Garmin data
    garmin_data = service.get_latest_insights()

    result = {}
    requested = data_types or [
        "vo2max", "race_predictions", "training_status",
        "training_load", "recovery_time", "training_readiness"
    ]

    for data_type in requested:
        if data_type in garmin_data:
            result[data_type] = garmin_data[data_type]

    return result


@with_retry(max_retries=2, base_delay=0.5, max_delay=2.0)
def _compare_workouts_from_db(
    workout_ids: List[str],
    metrics: Optional[List[str]],
) -> Dict[str, Any]:
    """Internal function to compare workouts with retry."""
    from ..db.database import TrainingDatabase

    db = TrainingDatabase()

    workouts = []
    for wid in workout_ids:
        activity = db.get_activity_metrics(wid)
        if activity:
            workouts.append({
                "id": wid,
                "date": activity.date.isoformat() if hasattr(activity.date, "isoformat") else str(activity.date),
                "name": activity.activity_name,
                "sport_type": activity.activity_type,
                "duration_min": round(activity.duration_min, 1),
                "distance_km": round(activity.distance_km, 2) if activity.distance_km else None,
                "pace_sec_km": activity.pace_sec_per_km,
                "avg_hr": activity.avg_hr,
                "max_hr": activity.max_hr,
                "hrss": round(activity.hrss, 1) if activity.hrss else None,
                "avg_power": getattr(activity, "avg_power", None),
                "elevation_gain": getattr(activity, "elevation_gain", None),
            })

    if len(workouts) < 2:
        return {"error": "Could not find enough valid workouts"}

    # Build comparison
    comparison = {}
    requested = metrics or ["pace", "heart_rate", "load", "efficiency"]

    if "pace" in requested or not metrics:
        paces = {w["id"]: w["pace_sec_km"] for w in workouts if w.get("pace_sec_km")}
        if paces:
            fastest = min(paces.values())
            comparison["pace_sec_km"] = {
                **paces,
                "fastest": [k for k, v in paces.items() if v == fastest][0],
                "range": f"{max(paces.values()) - min(paces.values())} sec/km",
            }

    if "heart_rate" in requested or not metrics:
        hrs = {w["id"]: w["avg_hr"] for w in workouts if w.get("avg_hr")}
        if hrs:
            comparison["avg_hr"] = {
                **hrs,
                "range": f"{max(hrs.values()) - min(hrs.values())} bpm",
            }

    if "load" in requested or not metrics:
        loads = {w["id"]: w["hrss"] for w in workouts if w.get("hrss")}
        if loads:
            comparison["hrss"] = {
                **loads,
                "highest": [k for k, v in loads.items() if v == max(loads.values())][0],
            }

    # Generate insights
    insights = {
        "workouts_compared": len(workouts),
        "notable_differences": [],
    }

    # Check for pace improvement with lower HR (efficiency gain)
    if len(workouts) >= 2 and workouts[0].get("pace_sec_km") and workouts[-1].get("pace_sec_km"):
        pace_diff = workouts[0]["pace_sec_km"] - workouts[-1]["pace_sec_km"]
        if workouts[0].get("avg_hr") and workouts[-1].get("avg_hr"):
            hr_diff = workouts[-1]["avg_hr"] - workouts[0]["avg_hr"]
            if pace_diff > 0 and hr_diff <= 0:
                insights["notable_differences"].append(
                    f"Improved by {pace_diff} sec/km at same or lower HR"
                )
                insights["efficiency_winner"] = workouts[-1]["id"]

    return {
        "workouts": workouts,
        "comparison": comparison,
        "insights": insights,
    }


# ============================================================================
# Tool Functions
# ============================================================================


@tool
def query_workouts(
    sport_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    workout_type: Optional[str] = None,
    limit: int = 10,
    include_laps: bool = False,
) -> List[Dict[str, Any]]:
    """Query workout history with flexible filters.

    Use this tool to retrieve past workouts based on various criteria.
    Results are sorted by date descending (most recent first).

    Args:
        sport_type: Filter by sport type. Options: "running", "cycling",
            "swimming", "strength", "walking", "hiking". Leave empty for all sports.
        date_from: Start date filter (ISO format: YYYY-MM-DD).
            Example: "2024-01-01"
        date_to: End date filter (ISO format: YYYY-MM-DD).
            Example: "2024-12-31"
        workout_type: Filter by workout type/intensity. Options: "easy",
            "tempo", "long", "intervals", "recovery", "race". Leave empty for all.
        limit: Maximum number of workouts to return (default 10, max 50).
        include_laps: Whether to include detailed lap/split data for each
            workout. Set to True for detailed analysis.

    Returns:
        List of workout summaries, each containing:
        - activity_id: Unique identifier
        - date: Workout date (ISO format)
        - sport_type: Type of sport
        - name: Workout name/title
        - duration_min: Duration in minutes
        - distance_km: Distance in kilometers (if applicable)
        - avg_hr: Average heart rate
        - max_hr: Maximum heart rate
        - hrss: Heart Rate Stress Score (training load)
        - pace_sec_km: Average pace in seconds per km (running)
        - avg_power: Average power in watts (cycling)
        - elevation_gain_m: Total elevation gain in meters
        - workout_type: Classified workout type
        - laps: List of lap data (if include_laps=True)

    Examples:
        - Get last 5 running workouts: query_workouts(sport_type="running", limit=5)
        - Get interval sessions this month: query_workouts(workout_type="intervals", date_from="2024-12-01")
        - Get all cycling with laps: query_workouts(sport_type="cycling", include_laps=True)
    """
    try:
        # Use internal function with retry logic for database operations
        return _query_workouts_from_db(
            sport_type=sport_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            include_laps=include_laps,
        )

    except ImportError:
        # Return mock data when services are not yet implemented
        logger.debug("Database not available - returning mock workout data")
        return _get_mock_workouts(sport_type, workout_type, limit)

    except Exception as e:
        # Log the error and return mock data as fallback
        logger.warning(f"query_workouts failed after retries: {e}")
        return _get_mock_workouts(sport_type, workout_type, limit)


def _get_mock_workouts(
    sport_type: Optional[str],
    workout_type: Optional[str],
    limit: int,
) -> List[Dict[str, Any]]:
    """Return mock workout data when database is unavailable."""
    return [
        {
            "activity_id": "mock_001",
            "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "sport_type": sport_type or "running",
            "name": "Easy Run",
            "duration_min": 45.0,
            "distance_km": 8.5,
            "avg_hr": 142,
            "max_hr": 158,
            "hrss": 65.2,
            "pace_sec_km": 318,
            "workout_type": workout_type or "easy",
            "note": "Service not yet implemented - returning mock data",
        },
        {
            "activity_id": "mock_002",
            "date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
            "sport_type": sport_type or "running",
            "name": "Tempo Run",
            "duration_min": 55.0,
            "distance_km": 10.2,
            "avg_hr": 165,
            "max_hr": 178,
            "hrss": 95.8,
            "pace_sec_km": 290,
            "workout_type": "tempo",
            "note": "Service not yet implemented - returning mock data",
        },
    ][:limit]


@tool
def query_wellness(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    metrics: Optional[List[str]] = None,
    limit: int = 7,
) -> List[Dict[str, Any]]:
    """Query wellness and recovery data.

    Use this tool to retrieve daily wellness metrics like HRV, sleep,
    recovery scores, and strain. Data typically comes from wearables
    (Garmin, Whoop, etc.).

    Args:
        date_from: Start date (ISO format: YYYY-MM-DD). Defaults to 7 days ago.
        date_to: End date (ISO format: YYYY-MM-DD). Defaults to today.
        metrics: Specific metrics to include. Options: "hrv", "rhr", "sleep",
            "recovery", "strain", "stress", "body_battery", "spo2".
            Leave empty for all available metrics.
        limit: Maximum days to return (default 7, max 30).

    Returns:
        List of daily wellness records, each containing:
        - date: Date of record (ISO format)
        - hrv: Heart Rate Variability (ms) - higher is generally better
        - rhr: Resting Heart Rate (bpm) - lower is generally better
        - sleep_hours: Total sleep duration
        - sleep_quality: Sleep quality score (0-100)
        - deep_sleep_min: Deep sleep duration in minutes
        - rem_sleep_min: REM sleep duration in minutes
        - recovery_score: Overall recovery score (0-100)
        - strain: Daily strain/activity level (0-21 scale for Whoop)
        - stress_score: Stress level (if available)
        - body_battery: Garmin Body Battery (0-100)
        - spo2: Blood oxygen percentage

    Examples:
        - Get last week's recovery: query_wellness(limit=7)
        - Get HRV trend this month: query_wellness(date_from="2024-12-01", metrics=["hrv"])
        - Check sleep patterns: query_wellness(metrics=["sleep", "sleep_quality"])
    """
    try:
        # Use internal function with retry logic for service operations
        return _query_wellness_from_service(
            date_from=date_from,
            date_to=date_to,
            metrics=metrics,
            limit=limit,
        )

    except ImportError:
        # Return mock data when services are not yet implemented
        logger.debug("Coach service not available - returning mock wellness data")
        return _get_mock_wellness(limit)

    except Exception as e:
        # Log the error and return mock data as fallback
        logger.warning(f"query_wellness failed after retries: {e}")
        return _get_mock_wellness(limit)


def _get_mock_wellness(limit: int) -> List[Dict[str, Any]]:
    """Return mock wellness data when service is unavailable."""
    mock_data = []
    end = datetime.now().date()
    for i in range(min(limit, 7)):
        day = end - timedelta(days=i)
        mock_data.append({
            "date": day.isoformat(),
            "hrv": 45 + (i * 2),
            "rhr": 52 - i,
            "sleep_hours": 7.2 + (i * 0.1),
            "sleep_quality": 78 + i,
            "deep_sleep_min": 85 + (i * 5),
            "rem_sleep_min": 95 + (i * 3),
            "recovery_score": 72 + (i * 3),
            "strain": 12.5 - (i * 0.5),
            "body_battery": 65 + (i * 4),
            "note": "Service not yet implemented - returning mock data",
        })
    return mock_data


@tool
def get_athlete_profile() -> Dict[str, Any]:
    """Get current athlete profile with fitness metrics.

    Use this tool to retrieve the athlete's current training status,
    physiological data, and goals. This provides context for making
    personalized recommendations.

    Returns:
        Dictionary containing:
        - Fitness Metrics:
            - ctl: Chronic Training Load (fitness level, 0-150+)
            - atl: Acute Training Load (recent fatigue, 0-150+)
            - tsb: Training Stress Balance (form, typically -30 to +30)
            - acwr: Acute:Chronic Workload Ratio (injury risk, ideal 0.8-1.3)
            - risk_zone: Current risk assessment ("safe", "optimal", "caution", "danger")

        - Physiology:
            - max_hr: Maximum heart rate (bpm)
            - rest_hr: Resting heart rate (bpm)
            - threshold_hr: Lactate threshold HR (bpm)
            - vdot: VDOT running economy score
            - ftp: Functional Threshold Power for cycling (watts)

        - HR Zones:
            - zone1 through zone5: HR ranges for each training zone

        - Training Paces (for runners):
            - easy, long, tempo, threshold, interval, race paces (sec/km)

        - Readiness:
            - readiness_score: Current readiness (0-100)
            - readiness_zone: "green" (go), "yellow" (moderate), "red" (rest)

        - Goals:
            - race_goal: Target race distance
            - race_date: Target race date
            - target_time: Goal finish time

    Example response:
        {
            "ctl": 45.2,
            "atl": 52.8,
            "tsb": -7.6,
            "acwr": 1.15,
            "risk_zone": "optimal",
            "readiness_score": 75,
            "readiness_zone": "green",
            "max_hr": 185,
            "threshold_hr": 168,
            "race_goal": "marathon",
            "target_time": "3:30:00"
        }
    """
    try:
        # Use internal function with retry logic for service operations
        return _get_athlete_profile_from_service()

    except ImportError:
        # Return mock data when services are not yet implemented
        logger.debug("Coach service not available - returning mock athlete profile")
        return _get_mock_athlete_profile()

    except Exception as e:
        # Log the error and return mock data as fallback
        logger.warning(f"get_athlete_profile failed after retries: {e}")
        return _get_mock_athlete_profile()


def _get_mock_athlete_profile() -> Dict[str, Any]:
    """Return mock athlete profile when service is unavailable."""
    return {
        "ctl": 42.5,
        "atl": 48.2,
        "tsb": -5.7,
        "acwr": 1.13,
        "risk_zone": "optimal",
        "max_hr": 185,
        "rest_hr": 52,
        "threshold_hr": 168,
        "vdot": 48.5,
        "readiness_score": 72,
        "readiness_zone": "green",
        "hr_zones": {
            "zone1": {"min": 118, "max": 130},
            "zone2": {"min": 130, "max": 143},
            "zone3": {"min": 143, "max": 156},
            "zone4": {"min": 156, "max": 169},
            "zone5": {"min": 169, "max": 185},
        },
        "training_paces": {
            "easy": "5:45/km",
            "long": "5:30/km",
            "tempo": "4:50/km",
            "threshold": "4:35/km",
            "interval": "4:15/km",
        },
        "race_goal": "half_marathon",
        "race_date": "2025-04-15",
        "target_time": "1:45:00",
        "recent_weekly_hours": 6.5,
        "recent_weekly_load": 320,
        "days_since_hard": 2,
        "note": "Service not yet implemented - returning mock data",
    }


@tool
def get_training_patterns(
    days: int = 28,
    pattern_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Get detected training patterns and trends.

    Use this tool to understand training behavior, identify patterns,
    and spot potential issues. Analyzes workout history to detect
    recurring patterns and trends.

    Args:
        days: Number of days to analyze (default 28, max 90).
        pattern_types: Specific pattern types to detect. Options:
            - "volume": Weekly/monthly volume trends
            - "intensity": Intensity distribution patterns
            - "consistency": Training consistency/regularity
            - "recovery": Recovery pattern analysis
            - "progression": Progressive overload detection
            - "periodization": Block/phase detection
            Leave empty to detect all patterns.

    Returns:
        Dictionary containing:
        - weekly_summary:
            - avg_sessions: Average sessions per week
            - avg_hours: Average training hours per week
            - avg_load: Average weekly training load
            - consistency_score: How consistent training is (0-100)

        - volume_trend:
            - direction: "increasing", "stable", "decreasing"
            - change_pct: Percentage change over period
            - weeks_analyzed: Number of weeks in analysis

        - intensity_distribution:
            - easy_pct: Percentage of easy/zone 1-2 training
            - moderate_pct: Percentage of tempo/zone 3 training
            - hard_pct: Percentage of high-intensity training
            - polarization_score: How polarized training is (0-100)

        - recovery_patterns:
            - avg_rest_days: Average rest days per week
            - back_to_back_hard: Count of consecutive hard days
            - recovery_quality: Quality of recovery periods

        - detected_patterns: List of specific patterns found
            Each pattern has: type, description, confidence, recommendation

    Example:
        {
            "weekly_summary": {
                "avg_sessions": 5.2,
                "avg_hours": 6.8,
                "consistency_score": 85
            },
            "intensity_distribution": {
                "easy_pct": 78,
                "moderate_pct": 12,
                "hard_pct": 10,
                "polarization_score": 82
            },
            "detected_patterns": [
                {
                    "type": "intensity",
                    "description": "Good 80/20 polarization",
                    "confidence": 0.9,
                    "recommendation": "Maintain current intensity distribution"
                }
            ]
        }
    """
    try:
        # Use internal function with retry logic for service operations
        return _get_training_patterns_from_service(
            days=days,
            pattern_types=pattern_types,
        )

    except ImportError:
        # Return mock data when services are not yet implemented
        logger.debug("Pattern service not available - returning mock training patterns")
        return _get_mock_training_patterns(days)

    except Exception as e:
        # Log the error and return mock data as fallback
        logger.warning(f"get_training_patterns failed after retries: {e}")
        return _get_mock_training_patterns(days)


def _get_mock_training_patterns(days: int) -> Dict[str, Any]:
    """Return mock training patterns when service is unavailable."""
    return {
        "period_analyzed": {
            "days": days,
            "start_date": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
            "end_date": datetime.now().strftime("%Y-%m-%d"),
        },
        "weekly_summary": {
            "avg_sessions": 5.3,
            "avg_hours": 6.5,
            "avg_load": 285,
            "consistency_score": 82,
        },
        "volume_trend": {
            "direction": "stable",
            "change_pct": 3.2,
            "weeks_analyzed": days // 7,
        },
        "intensity_distribution": {
            "easy_pct": 75,
            "moderate_pct": 15,
            "hard_pct": 10,
            "polarization_score": 78,
        },
        "recovery_patterns": {
            "avg_rest_days": 1.8,
            "back_to_back_hard": 2,
            "recovery_quality": "good",
        },
        "detected_patterns": [
            {
                "type": "consistency",
                "description": "Regular training rhythm with consistent weekly volume",
                "confidence": 0.88,
                "recommendation": "Good consistency - maintain current schedule",
            },
            {
                "type": "intensity",
                "description": "Slightly too much moderate-intensity work",
                "confidence": 0.72,
                "recommendation": "Consider converting some tempo runs to easy runs",
            },
        ],
        "note": "Service not yet implemented - returning mock data",
    }


@tool
def get_fitness_metrics(
    days: int = 42,
    include_daily: bool = False,
) -> Dict[str, Any]:
    """Get fitness metrics time series (CTL, ATL, TSB).

    Use this tool to understand fitness progression over time. Returns
    the Performance Management Chart (PMC) data that tracks chronic
    load (fitness), acute load (fatigue), and form (freshness).

    Args:
        days: Number of days of history (default 42, max 180).
        include_daily: Whether to include daily values. If False, returns
            only current values and weekly summaries (more efficient).

    Returns:
        Dictionary containing:
        - current:
            - ctl: Current Chronic Training Load (fitness)
            - atl: Current Acute Training Load (fatigue)
            - tsb: Current Training Stress Balance (form)
            - acwr: Current Acute:Chronic Workload Ratio
            - risk_zone: Current injury risk zone

        - trends:
            - ctl_trend: "improving", "stable", "declining"
            - ctl_change: Change in CTL over period
            - peak_ctl: Highest CTL in period
            - lowest_tsb: Lowest TSB (deepest fatigue) in period

        - weekly: List of weekly summaries with CTL/ATL/TSB averages

        - daily: (if include_daily=True) List of daily values
            Each day has: date, ctl, atl, tsb, acwr, daily_load

    CTL/ATL/TSB Interpretation:
        - CTL (Fitness): 42-day exponentially weighted average of load
            - < 30: Beginner/detrained
            - 30-50: Recreational
            - 50-80: Competitive amateur
            - 80-120: Serious competitive
            - > 120: Elite

        - ATL (Fatigue): 7-day exponentially weighted average
            - Represents recent training stress

        - TSB (Form): CTL - ATL
            - Positive (5-25): Fresh, good for racing
            - Near zero (-10 to 5): Functional training
            - Negative (-10 to -30): Training hard, building fitness
            - Very negative (< -30): Risk of overtraining

    Example:
        {
            "current": {
                "ctl": 52.3,
                "atl": 58.7,
                "tsb": -6.4,
                "acwr": 1.12
            },
            "trends": {
                "ctl_trend": "improving",
                "ctl_change": 4.2,
                "peak_ctl": 54.1
            }
        }
    """
    try:
        # Use internal function with retry logic for database operations
        return _get_fitness_metrics_from_db(
            days=days,
            include_daily=include_daily,
        )

    except ImportError:
        # Return mock data when services are not yet implemented
        logger.debug("Database not available - returning mock fitness metrics")
        return _get_mock_fitness_metrics(days, include_daily)

    except Exception as e:
        # Log the error and return mock data as fallback
        logger.warning(f"get_fitness_metrics failed after retries: {e}")
        return _get_mock_fitness_metrics(days, include_daily)


def _get_mock_fitness_metrics(days: int, include_daily: bool) -> Dict[str, Any]:
    """Return mock fitness metrics when database is unavailable."""
    result = {
        "period": {
            "days": days,
            "start_date": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
            "end_date": datetime.now().strftime("%Y-%m-%d"),
        },
        "current": {
            "ctl": 48.5,
            "atl": 54.2,
            "tsb": -5.7,
            "acwr": 1.12,
            "risk_zone": "optimal",
        },
        "trends": {
            "ctl_trend": "improving",
            "ctl_change": 3.8,
            "peak_ctl": 51.2,
            "lowest_tsb": -12.5,
        },
        "weekly": [
            {"week_ending": (datetime.now() - timedelta(days=7*i)).strftime("%Y-%m-%d"),
             "avg_ctl": 48.5 - (i * 0.8),
             "avg_atl": 54.2 - (i * 1.2),
             "avg_tsb": -5.7 + (i * 0.4)}
            for i in range(days // 7)
        ],
        "note": "Service not yet implemented - returning mock data",
    }

    if include_daily:
        result["daily"] = [
            {
                "date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"),
                "ctl": 48.5 - (i * 0.1),
                "atl": 54.2 - (i * 0.3),
                "tsb": -5.7 + (i * 0.2),
                "acwr": 1.12 - (i * 0.01),
                "daily_load": 45 + (i % 7) * 10,
            }
            for i in range(days)
        ]

    return result


@tool
def get_garmin_data(
    data_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Get latest Garmin Connect data (VO2max, race predictions, training status).

    Use this tool to retrieve Garmin-specific insights like VO2max estimates,
    race predictions, training status, and recovery metrics that Garmin
    calculates from their advanced algorithms.

    Args:
        data_types: Specific Garmin data to retrieve. Options:
            - "vo2max": VO2max running and cycling estimates
            - "race_predictions": Predicted race times
            - "training_status": Current training status
            - "training_load": 7-day training load breakdown
            - "recovery_time": Recovery time recommendation
            - "heat_acclimation": Heat and altitude acclimation
            - "training_readiness": Training readiness score
            - "hrv_status": HRV status and baseline
            - "body_battery": Body battery level
            Leave empty for all available data.

    Returns:
        Dictionary containing (availability depends on device):

        - vo2max:
            - running: VO2max for running (mL/kg/min)
            - cycling: VO2max for cycling (mL/kg/min)
            - trend: "improving", "stable", "declining"

        - race_predictions:
            - 5k, 10k, half_marathon, marathon: Predicted times
            - last_updated: When predictions were last calculated

        - training_status:
            - status: "productive", "maintaining", "recovering",
                     "unproductive", "detraining", "overreaching"
            - description: Explanation of current status

        - training_load:
            - total: 7-day total load
            - anaerobic: High-intensity load
            - low_aerobic: Easy effort load
            - high_aerobic: Threshold effort load
            - focus: Current training focus

        - recovery_time:
            - hours: Recommended recovery hours
            - ready_by: Date/time when fully recovered

        - training_readiness:
            - score: 0-100 readiness score
            - factors: Contributing factors

    Example:
        {
            "vo2max": {
                "running": 52.0,
                "cycling": 48.5,
                "trend": "improving"
            },
            "race_predictions": {
                "5k": "22:15",
                "10k": "46:30",
                "half_marathon": "1:42:00",
                "marathon": "3:35:00"
            },
            "training_status": {
                "status": "productive",
                "description": "Your training is producing positive results"
            }
        }
    """
    try:
        # Use internal function with retry logic for service operations
        return _get_garmin_data_from_service(data_types=data_types)

    except ImportError:
        # Return mock data when services are not yet implemented
        logger.debug("Garmin service not available - returning mock Garmin data")
        return _get_mock_garmin_data(data_types)

    except Exception as e:
        # Log the error and return mock data as fallback
        logger.warning(f"get_garmin_data failed after retries: {e}")
        return _get_mock_garmin_data(data_types)


def _get_mock_garmin_data(data_types: Optional[List[str]]) -> Dict[str, Any]:
    """Return mock Garmin data when service is unavailable."""
    requested = data_types or [
        "vo2max", "race_predictions", "training_status",
        "training_load", "recovery_time", "training_readiness"
    ]

    mock_data = {
        "vo2max": {
            "running": 51.5,
            "cycling": 47.0,
            "trend": "improving",
            "last_updated": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        },
        "race_predictions": {
            "5k": "22:30",
            "10k": "47:15",
            "half_marathon": "1:44:00",
            "marathon": "3:40:00",
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
        },
        "training_status": {
            "status": "productive",
            "description": "Your training is producing positive fitness improvements",
            "primary_benefit": "VO2max",
        },
        "training_load": {
            "total": 685,
            "anaerobic": 120,
            "low_aerobic": 380,
            "high_aerobic": 185,
            "focus": "base_building",
            "optimal_range": {"min": 600, "max": 900},
        },
        "recovery_time": {
            "hours": 18,
            "ready_by": (datetime.now() + timedelta(hours=18)).strftime("%Y-%m-%d %H:%M"),
        },
        "training_readiness": {
            "score": 72,
            "factors": {
                "sleep": "good",
                "recovery": "moderate",
                "training_history": "balanced",
                "hrv_status": "normal",
            },
        },
        "hrv_status": {
            "current": 48,
            "baseline": 45,
            "status": "balanced",
            "trend": "stable",
        },
        "body_battery": {
            "current": 68,
            "morning": 85,
            "drain_rate": "normal",
        },
    }

    result = {k: v for k, v in mock_data.items() if k in requested}
    result["note"] = "Service not yet implemented - returning mock data"

    return result


@tool
def compare_workouts(
    workout_ids: List[str],
    metrics: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compare multiple workouts side-by-side.

    Use this tool to compare 2-5 workouts across various metrics.
    Useful for tracking progress, comparing similar workouts, or
    analyzing performance differences.

    Args:
        workout_ids: List of workout activity IDs to compare (2-5 workouts).
            Get IDs from query_workouts tool.
        metrics: Specific metrics to compare. Options:
            - "pace": Pace comparison (for running)
            - "power": Power metrics (for cycling)
            - "heart_rate": HR and zones
            - "load": Training load comparison
            - "efficiency": Efficiency metrics (HR:pace ratio, etc.)
            - "splits": Split/lap comparison
            Leave empty to compare all available metrics.

    Returns:
        Dictionary containing:
        - workouts: List of workout summaries being compared

        - comparison: Side-by-side metric comparison
            Each metric has values for each workout and analysis

        - insights: Key differences and observations
            - faster_workout: Which was faster (if applicable)
            - efficiency_winner: Most efficient effort
            - notable_differences: Key differences to note

        - recommendations: Suggestions based on comparison

    Example:
        {
            "workouts": [
                {"id": "w1", "date": "2024-12-01", "name": "Easy Run"},
                {"id": "w2", "date": "2024-12-15", "name": "Easy Run"}
            ],
            "comparison": {
                "pace_sec_km": {"w1": 345, "w2": 338, "improvement": "2%"},
                "avg_hr": {"w1": 145, "w2": 142, "change": "-3 bpm"}
            },
            "insights": {
                "faster_workout": "w2",
                "efficiency_winner": "w2",
                "notable_differences": [
                    "7 sec/km faster at 3 bpm lower heart rate"
                ]
            }
        }
    """
    # Validation errors are non-retryable
    if len(workout_ids) < 2:
        return {"error": "Need at least 2 workouts to compare"}
    if len(workout_ids) > 5:
        return {"error": "Maximum 5 workouts can be compared at once"}

    try:
        # Use internal function with retry logic for database operations
        return _compare_workouts_from_db(
            workout_ids=workout_ids,
            metrics=metrics,
        )

    except ImportError:
        # Return mock data when services are not yet implemented
        logger.debug("Database not available - returning mock workout comparison")
        return _get_mock_workout_comparison(workout_ids)

    except Exception as e:
        # Log the error and return mock data as fallback
        logger.warning(f"compare_workouts failed after retries: {e}")
        return _get_mock_workout_comparison(workout_ids)


def _get_mock_workout_comparison(workout_ids: List[str]) -> Dict[str, Any]:
    """Return mock workout comparison when database is unavailable."""
    mock_workouts = [
        {
            "id": wid,
            "date": (datetime.now() - timedelta(days=i*7)).strftime("%Y-%m-%d"),
            "name": f"Workout {i+1}",
            "sport_type": "running",
            "duration_min": 45 + (i * 2),
            "distance_km": 8.0 + (i * 0.3),
            "pace_sec_km": 340 - (i * 5),
            "avg_hr": 148 - (i * 2),
            "hrss": 65 + (i * 3),
        }
        for i, wid in enumerate(workout_ids)
    ]

    return {
        "workouts": mock_workouts,
        "comparison": {
            "pace_sec_km": {
                workout_ids[0]: 340,
                workout_ids[1]: 335,
                "improvement": "1.5%",
            },
            "avg_hr": {
                workout_ids[0]: 148,
                workout_ids[1]: 146,
                "change": "-2 bpm",
            },
            "hrss": {
                workout_ids[0]: 65,
                workout_ids[1]: 68,
                "change": "+3",
            },
        },
        "insights": {
            "workouts_compared": len(workout_ids),
            "efficiency_winner": workout_ids[1],
            "notable_differences": [
                "5 sec/km faster at 2 bpm lower heart rate - improved efficiency"
            ],
        },
        "note": "Service not yet implemented - returning mock data",
    }


# ============================================================================
# Workout Details with Condensed Time Series Analysis
# ============================================================================

@with_retry(max_retries=2, base_delay=0.5, max_delay=2.0)
def _fetch_workout_time_series(activity_id: str) -> Optional[Dict[str, Any]]:
    """Fetch time series data from Garmin for a workout.

    Returns raw time series and splits, or None if unavailable.
    """
    try:
        import garth
        from pathlib import Path

        # Try to use existing garth session
        token_dir = Path.home() / ".garmin_tokens"

        if not token_dir.exists():
            logger.warning("No Garmin token directory found")
            return None

        garth.resume(token_dir)

        # Fetch activity details (time series)
        details = garth.connectapi(
            f"/activity-service/activity/{activity_id}/details",
            params={"maxChartSize": 2000, "maxPolylineSize": 4000}
        )

        # Fetch splits
        try:
            splits = garth.connectapi(f"/activity-service/activity/{activity_id}/splits")
        except Exception:
            splits = {}

        # Fetch summary for duration/distance
        summary = garth.connectapi(f"/activity-service/activity/{activity_id}")

        return {
            "details": details,
            "splits": splits,
            "summary": summary,
        }

    except ImportError:
        logger.warning("garth not installed")
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch Garmin time series: {e}")
        return None


def _condense_garmin_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Condense raw Garmin time series data into statistical summaries."""
    from ..analysis.condensation import (
        condense_workout_data,
        CondensedWorkoutData,
    )

    details = raw_data.get("details", {})
    splits_data = raw_data.get("splits", {})
    summary = raw_data.get("summary", {})

    # Extract time series from Garmin details format
    metrics = details.get("metricDescriptors", [])
    activity_detail_metrics = details.get("activityDetailMetrics", [])

    # Build metric index
    metric_index = {m.get("key"): i for i, m in enumerate(metrics)}

    # Extract HR, pace, elevation, cadence points
    hr_points = []
    pace_points = []
    elevation_points = []
    cadence_points = []

    hr_idx = metric_index.get("directHeartRate")
    pace_idx = metric_index.get("directSpeed")  # Will convert to pace
    elev_idx = metric_index.get("directElevation")
    cadence_idx = metric_index.get("directRunCadence")

    for i, point in enumerate(activity_detail_metrics):
        metrics_arr = point.get("metrics", [])
        timestamp = i  # Index as proxy for timestamp

        if hr_idx is not None and hr_idx < len(metrics_arr) and metrics_arr[hr_idx]:
            hr_points.append({"timestamp": timestamp, "hr": int(metrics_arr[hr_idx])})

        if pace_idx is not None and pace_idx < len(metrics_arr) and metrics_arr[pace_idx]:
            speed = metrics_arr[pace_idx]  # m/s
            if speed > 0:
                pace_sec_km = 1000 / speed  # Convert to sec/km
                pace_points.append({"timestamp": timestamp, "value": pace_sec_km})

        if elev_idx is not None and elev_idx < len(metrics_arr) and metrics_arr[elev_idx]:
            elevation_points.append({"timestamp": timestamp, "elevation": metrics_arr[elev_idx]})

        if cadence_idx is not None and cadence_idx < len(metrics_arr) and metrics_arr[cadence_idx]:
            cadence_points.append({"timestamp": timestamp, "cadence": int(metrics_arr[cadence_idx] * 2)})  # Garmin stores as steps/2

    # Extract splits
    splits = []
    lap_dtos = splits_data.get("lapDTOs", []) or []
    for lap in lap_dtos:
        split_pace = None
        duration = lap.get("duration", 0)
        distance = lap.get("distance", 0)
        if duration > 0 and distance > 0:
            split_pace = (duration / 1000) / (distance / 1000)  # sec/km

        splits.append({
            "split_number": lap.get("lapIndex", 0) + 1,
            "duration_sec": (lap.get("duration") or 0) / 1000,
            "distance_m": lap.get("distance"),
            "pace": split_pace,
            "avg_hr": lap.get("averageHR"),
            "max_hr": lap.get("maxHR"),
            "elevation_gain": lap.get("elevationGain"),
        })

    # Build time series dict
    time_series = {}
    if hr_points:
        time_series["heart_rate"] = hr_points
    if pace_points:
        time_series["pace_or_speed"] = pace_points
    if elevation_points:
        time_series["elevation"] = elevation_points
    if cadence_points:
        time_series["cadence"] = cadence_points

    # Get duration and distance from summary
    duration_sec = (summary.get("duration") or 0) / 1000
    distance_km = (summary.get("distance") or 0) / 1000
    activity_type = summary.get("activityType", {}).get("typeKey", "running")

    # Condense the data
    condensed = condense_workout_data(
        time_series=time_series if time_series else None,
        splits=splits if splits else None,
        hr_zones=None,  # Could fetch from athlete profile
        duration_sec=int(duration_sec),
        distance_km=distance_km,
        activity_type=activity_type,
    )

    # Convert to dict format for the tool response
    result = {
        "activity_id": summary.get("activityId"),
        "date": summary.get("startTimeLocal", "")[:10] if summary.get("startTimeLocal") else None,
        "name": summary.get("activityName"),
        "sport_type": activity_type,
        "duration_min": round(duration_sec / 60, 1),
        "distance_km": round(distance_km, 2),
    }

    # Add condensed HR summary
    if condensed.hr_summary and condensed.hr_summary.mean > 0:
        result["hr_analysis"] = {
            "avg_hr": round(condensed.hr_summary.mean),
            "peak_hr": condensed.hr_summary.peak_hr,
            "hr_drift_pct": round(condensed.hr_summary.hr_drift, 1),
            "hr_variability_cv": round(condensed.hr_summary.cv, 1),
            "zone_transitions": condensed.hr_summary.zone_transitions,
            "is_interval_workout": condensed.hr_summary.is_interval_workout,
            "summary": condensed.hr_summary.to_prompt_text(),
        }

    # Add condensed pace summary
    if condensed.pace_summary and condensed.pace_summary.mean_pace > 0:
        result["pace_analysis"] = {
            "avg_pace_sec_km": round(condensed.pace_summary.mean_pace),
            "avg_pace_formatted": condensed.pace_summary.format_pace(condensed.pace_summary.mean_pace),
            "consistency_score": round(condensed.pace_summary.consistency_score),
            "fade_index": round(condensed.pace_summary.fade_index, 2),
            "negative_split": condensed.pace_summary.negative_split_ratio < 0.98,
            "trend": condensed.pace_summary.trend.value,
            "best_km_pace": condensed.pace_summary.format_pace(condensed.pace_summary.best_km_pace),
            "worst_km_pace": condensed.pace_summary.format_pace(condensed.pace_summary.worst_km_pace),
            "summary": condensed.pace_summary.to_prompt_text(),
        }

    # Add condensed elevation summary
    if condensed.elevation_summary and condensed.elevation_summary.total_gain_m > 10:
        result["elevation_analysis"] = {
            "total_gain_m": round(condensed.elevation_summary.total_gain_m),
            "total_loss_m": round(condensed.elevation_summary.total_loss_m),
            "terrain_type": condensed.elevation_summary.terrain_type.value,
            "climb_count": condensed.elevation_summary.climb_count,
            "summary": condensed.elevation_summary.to_prompt_text(),
        }

    # Add condensed splits summary
    if condensed.splits_summary and condensed.splits_summary.total_splits > 0:
        result["splits_analysis"] = {
            "total_splits": condensed.splits_summary.total_splits,
            "even_split_score": round(condensed.splits_summary.even_split_score),
            "fastest_split": condensed.splits_summary.fastest_split,
            "slowest_split": condensed.splits_summary.slowest_split,
            "trend": condensed.splits_summary.trend.value,
            "summary": condensed.splits_summary.to_prompt_text(),
        }

    # Add condensed cadence summary
    if condensed.cadence_summary and condensed.cadence_summary.mean > 0:
        result["cadence_analysis"] = {
            "avg_cadence": round(condensed.cadence_summary.mean),
            "cadence_cv": round(condensed.cadence_summary.cv, 1),
            "cadence_drop_pct": round(condensed.cadence_summary.cadence_drop_pct, 1),
            "time_in_optimal_pct": round(condensed.cadence_summary.time_in_optimal_pct),
            "is_consistent": condensed.cadence_summary.is_consistent,
            "summary": condensed.cadence_summary.to_prompt_text(),
        }

    # Add coaching insights
    if condensed.insights:
        result["coaching_insights"] = condensed.insights

    return result


@tool
def get_workout_details(
    workout_id: str,
) -> Dict[str, Any]:
    """Get deep analysis of a single workout with condensed time-series statistics.

    Use this tool when you need detailed analysis of a specific workout beyond
    basic metrics. This fetches and analyzes the full time-series data (HR, pace,
    elevation, cadence, splits) and returns condensed statistical summaries.

    This is more detailed than query_workouts and provides:
    - HR analysis: drift, variability, zone transitions, interval detection
    - Pace analysis: consistency score, fade index, negative splits, trend
    - Elevation analysis: terrain type, climb count, grades
    - Splits analysis: even split score, fastest/slowest km, trend
    - Cadence analysis: consistency, fatigue indicators, optimal zone time
    - Coaching insights: Pre-computed observations about the workout

    Args:
        workout_id: The activity ID of the workout to analyze.
            Get this from query_workouts results.

    Returns:
        Dictionary containing:

        - activity_id: Workout identifier
        - date: Workout date
        - name: Workout name
        - sport_type: Activity type
        - duration_min: Duration in minutes
        - distance_km: Distance in km

        - hr_analysis (if HR data available):
            - avg_hr: Average heart rate
            - peak_hr: Maximum heart rate
            - hr_drift_pct: % change from start to end (cardiac drift)
            - hr_variability_cv: Coefficient of variation (higher = more variable)
            - zone_transitions: Number of HR zone boundary crossings
            - is_interval_workout: True if pattern suggests intervals
            - summary: Human-readable HR summary

        - pace_analysis (if pace data available):
            - avg_pace_sec_km: Average pace in seconds per km
            - avg_pace_formatted: "5:30/km" format
            - consistency_score: 0-100 (higher = more consistent)
            - fade_index: >1.0 means slowed down, <1.0 means sped up
            - negative_split: True if second half was faster
            - trend: "steady", "accelerating", "decelerating", "variable"
            - best_km_pace / worst_km_pace: Formatted paces
            - summary: Human-readable pace summary

        - elevation_analysis (if significant elevation):
            - total_gain_m / total_loss_m: Elevation change
            - terrain_type: "flat", "rolling", "hilly", "mountainous"
            - climb_count: Number of distinct climbs
            - summary: Human-readable elevation summary

        - splits_analysis (if splits data available):
            - total_splits: Number of km splits
            - even_split_score: 0-100 (higher = more even pacing)
            - fastest_split / slowest_split: Split numbers
            - trend: Pacing trend across workout
            - summary: Human-readable splits summary

        - cadence_analysis (if cadence data available):
            - avg_cadence: Average steps/min (running) or rpm (cycling)
            - cadence_cv: Variability (lower = more consistent)
            - cadence_drop_pct: Drop in final quarter (fatigue indicator)
            - time_in_optimal_pct: % time in 170-185 spm zone (running)
            - is_consistent: True if CV < 8%
            - summary: Human-readable cadence summary

        - coaching_insights: List of key observations like:
            - "Cardiac drift: +8% (hydration/fatigue concern)"
            - "Strong negative split execution"
            - "Cadence dropped 7% in final quarter (fatigue sign)"

    Examples:
        User: "Tell me about my tempo run yesterday"
        1. First call query_workouts(workout_type="tempo", limit=1) to get the ID
        2. Then call get_workout_details(workout_id) for deep analysis

        User: "How consistent was my pacing in that long run?"
        → get_workout_details returns pace_analysis.consistency_score and splits_analysis
    """
    if not workout_id:
        return {"error": "workout_id is required"}

    try:
        # Try to fetch and condense real data
        raw_data = _fetch_workout_time_series(workout_id)

        if raw_data:
            return _condense_garmin_data(raw_data)
        else:
            # Fall back to mock data
            logger.debug("No time series data available - returning mock condensed data")
            return _get_mock_workout_details(workout_id)

    except ImportError as e:
        logger.debug(f"Import error in get_workout_details: {e}")
        return _get_mock_workout_details(workout_id)

    except Exception as e:
        logger.warning(f"get_workout_details failed: {e}")
        return _get_mock_workout_details(workout_id)


def _get_mock_workout_details(workout_id: str) -> Dict[str, Any]:
    """Return mock condensed workout data when Garmin data is unavailable."""
    return {
        "activity_id": workout_id,
        "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "name": "Tempo Run",
        "sport_type": "running",
        "duration_min": 48.5,
        "distance_km": 10.2,
        "hr_analysis": {
            "avg_hr": 162,
            "peak_hr": 178,
            "hr_drift_pct": 5.2,
            "hr_variability_cv": 6.8,
            "zone_transitions": 3,
            "is_interval_workout": False,
            "summary": "HR: avg 162 bpm, steady (CV=6.8%) | HR Drift: +5.2% (+8 bpm) | Peak: 178 bpm (late in workout)",
        },
        "pace_analysis": {
            "avg_pace_sec_km": 285,
            "avg_pace_formatted": "4:45/km",
            "consistency_score": 82,
            "fade_index": 1.03,
            "negative_split": False,
            "trend": "steady",
            "best_km_pace": "4:38/km",
            "worst_km_pace": "4:52/km",
            "summary": "Pace: avg 4:45/km, good consistency (82/100) | Range: 4:38/km to 4:52/km",
        },
        "elevation_analysis": {
            "total_gain_m": 85,
            "total_loss_m": 78,
            "terrain_type": "rolling",
            "climb_count": 4,
            "summary": "Elevation: +85m / -78m (rolling) | Climbs: 4",
        },
        "splits_analysis": {
            "total_splits": 10,
            "even_split_score": 78,
            "fastest_split": 8,
            "slowest_split": 2,
            "trend": "steady",
            "summary": "Splits (10km): 8/10 within 5% of avg | Fastest: km 8 (4:38/km) | Slowest: km 2 (4:52/km)",
        },
        "cadence_analysis": {
            "avg_cadence": 178,
            "cadence_cv": 4.2,
            "cadence_drop_pct": 2.1,
            "time_in_optimal_pct": 85,
            "is_consistent": True,
            "summary": "Cadence: avg 178 spm, very consistent (CV=4.2%) | Optimal cadence zone: 85% (excellent form)",
        },
        "coaching_insights": [
            "HR drift within normal range for tempo effort",
            "Good pacing consistency - well-controlled effort",
            "Excellent running cadence maintained throughout",
        ],
        "note": "Mock data - Garmin time series not available",
    }