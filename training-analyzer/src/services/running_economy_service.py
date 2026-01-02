"""
Running Economy Service for tracking efficiency and cardiac drift.

Running economy is a measure of how efficiently a runner uses oxygen at a given pace.
A better (lower) economy ratio means less cardiac effort for the same pace.

Based on sports science research:
- Saunders et al. (2004): Running economy factors
- Jones (2006): Economy improvement through training
- Barnes & Kilding (2015): Running economy determinants

Cardiac drift is the gradual increase in heart rate during exercise at constant
intensity, reflecting cardiovascular stress and hydration status.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import logging

from ..models.running_economy import (
    CardiacDriftAnalysis,
    CardiacDriftSeverity,
    CardiacDriftTrend,
    EconomyCurrentResponse,
    EconomyDataPoint,
    EconomyMetrics,
    EconomyTrend,
    EconomyTrendResponse,
    PaceZone,
    PaceZonesEconomy,
    ZoneEconomy,
    calculate_cardiac_drift,
    calculate_economy_ratio,
    classify_pace_zone,
    format_pace,
    get_drift_recommendation,
    get_economy_label,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Running activity types to include
RUNNING_ACTIVITY_TYPES = {
    "running", "run", "trail_running", "treadmill_running", "track_running"
}

# Minimum duration (minutes) to include in economy calculations
MIN_DURATION_MINUTES = 10

# Minimum distance (km) to include in economy calculations
MIN_DISTANCE_KM = 1.5

# Default pace thresholds (sec/km) for zone classification
DEFAULT_EASY_PACE = 360  # 6:00/km
DEFAULT_TEMPO_PACE = 300  # 5:00/km
DEFAULT_THRESHOLD_PACE = 285  # 4:45/km


# =============================================================================
# Running Economy Service Class
# =============================================================================

class RunningEconomyService:
    """
    Service for tracking running economy and cardiac drift.

    Running economy is calculated as:
        economy = pace_seconds_per_km / avg_hr

    Lower values indicate better economy (less HR for same pace).

    Example:
        At 5:00/km (300 sec) with 150 bpm avg HR:
        economy = 300 / 150 = 2.0

        If after training, same pace with 145 bpm:
        economy = 300 / 145 = 2.07 (3.4% improvement)
    """

    def __init__(
        self,
        easy_pace: int = DEFAULT_EASY_PACE,
        tempo_pace: int = DEFAULT_TEMPO_PACE,
        threshold_pace: int = DEFAULT_THRESHOLD_PACE,
    ):
        """
        Initialize the running economy service.

        Args:
            easy_pace: Easy pace threshold in sec/km
            tempo_pace: Tempo pace threshold in sec/km
            threshold_pace: Threshold pace threshold in sec/km
        """
        self._easy_pace = easy_pace
        self._tempo_pace = tempo_pace
        self._threshold_pace = threshold_pace
        self._logger = logging.getLogger(__name__)

    def _is_running_workout(self, activity: Dict[str, Any]) -> bool:
        """Check if an activity is a running workout."""
        activity_type = activity.get("type", "").lower()
        return activity_type in RUNNING_ACTIVITY_TYPES

    def _extract_workout_data(
        self,
        activity: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract relevant data from a workout for economy calculations.

        Returns None if the workout doesn't meet minimum criteria.
        """
        if not self._is_running_workout(activity):
            return None

        # Get required fields
        avg_hr = activity.get("avg_hr") or activity.get("avgHeartRate")
        pace = activity.get("pace_sec_per_km") or activity.get("avgPace")
        duration_min = activity.get("duration_min")
        distance_km = activity.get("distance_km")

        # Try to extract from metrics if not at top level
        if avg_hr is None and "metrics" in activity:
            avg_hr = activity["metrics"].get("avgHeartRate")
        if pace is None and "metrics" in activity:
            pace = activity["metrics"].get("avgPace")

        # Convert distance from meters if needed
        if distance_km is None:
            distance = activity.get("distance")
            if distance is not None:
                distance_km = distance / 1000

        # Convert duration from seconds if needed
        if duration_min is None:
            duration = activity.get("duration")
            if duration is not None:
                duration_min = duration / 60

        # Validate required fields
        if not avg_hr or not pace or avg_hr <= 0 or pace <= 0:
            return None

        # Check minimum duration and distance
        if duration_min and duration_min < MIN_DURATION_MINUTES:
            return None
        if distance_km and distance_km < MIN_DISTANCE_KM:
            return None

        # Parse date
        workout_date = activity.get("date", "")
        if isinstance(workout_date, datetime):
            workout_date = workout_date.date().isoformat()
        elif isinstance(workout_date, date):
            workout_date = workout_date.isoformat()
        elif isinstance(workout_date, str) and "T" in workout_date:
            workout_date = workout_date.split("T")[0]

        return {
            "workout_id": activity.get("id") or activity.get("activity_id", ""),
            "workout_date": workout_date,
            "workout_type": activity.get("type", "running"),
            "avg_hr": int(avg_hr),
            "pace_sec_per_km": int(pace),
            "duration_min": float(duration_min or 0),
            "distance_km": float(distance_km or 0),
        }

    def calculate_economy(
        self,
        activity: Dict[str, Any],
        best_economy: Optional[float] = None,
    ) -> Optional[EconomyMetrics]:
        """
        Calculate running economy metrics for a single workout.

        Args:
            activity: Activity dictionary with workout data
            best_economy: Personal best economy for comparison

        Returns:
            EconomyMetrics or None if calculation not possible
        """
        data = self._extract_workout_data(activity)
        if not data:
            return None

        pace = data["pace_sec_per_km"]
        avg_hr = data["avg_hr"]

        # Calculate economy ratio
        economy_ratio = calculate_economy_ratio(pace, avg_hr)

        # Classify pace zone
        pace_zone = classify_pace_zone(
            pace,
            self._easy_pace,
            self._tempo_pace,
            self._threshold_pace,
        )

        # Calculate comparison to best
        comparison_to_best = None
        if best_economy and best_economy > 0:
            comparison_to_best = ((economy_ratio - best_economy) / best_economy) * 100

        return EconomyMetrics(
            economy_ratio=economy_ratio,
            pace_sec_per_km=pace,
            avg_hr=avg_hr,
            workout_id=data["workout_id"],
            workout_date=data["workout_date"],
            workout_type=data["workout_type"],
            distance_km=data["distance_km"],
            duration_min=data["duration_min"],
            best_economy=best_economy,
            comparison_to_best=round(comparison_to_best, 1) if comparison_to_best else None,
            pace_zone=pace_zone,
            pace_formatted=format_pace(pace),
            economy_label=get_economy_label(economy_ratio, best_economy),
        )

    def detect_cardiac_drift(
        self,
        activity: Dict[str, Any],
        time_series_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[CardiacDriftAnalysis]:
        """
        Detect cardiac drift in a workout by comparing first and second half HR.

        Cardiac drift >5% typically indicates:
        - Aerobic base deficiency
        - Dehydration
        - Overheating
        - Insufficient fueling

        Args:
            activity: Activity dictionary
            time_series_data: Optional time-series HR data

        Returns:
            CardiacDriftAnalysis or None if not calculable
        """
        if not self._is_running_workout(activity):
            return None

        # Parse workout date
        workout_date = activity.get("date", "")
        if isinstance(workout_date, datetime):
            workout_date = workout_date.date().isoformat()
        elif isinstance(workout_date, date):
            workout_date = workout_date.isoformat()
        elif isinstance(workout_date, str) and "T" in workout_date:
            workout_date = workout_date.split("T")[0]

        workout_id = activity.get("id") or activity.get("activity_id", "")

        # Try to get first/second half HR from time series
        first_half_hr = None
        second_half_hr = None
        first_half_pace = None
        second_half_pace = None

        if time_series_data and len(time_series_data) > 10:
            # Split time series into halves
            mid_point = len(time_series_data) // 2
            first_half = time_series_data[:mid_point]
            second_half = time_series_data[mid_point:]

            # Calculate average HR for each half
            first_half_hrs = [p.get("hr") or p.get("heart_rate") for p in first_half if (p.get("hr") or p.get("heart_rate"))]
            second_half_hrs = [p.get("hr") or p.get("heart_rate") for p in second_half if (p.get("hr") or p.get("heart_rate"))]

            if first_half_hrs and second_half_hrs:
                first_half_hr = sum(first_half_hrs) / len(first_half_hrs)
                second_half_hr = sum(second_half_hrs) / len(second_half_hrs)

            # Calculate average pace for each half if available
            first_half_paces = [p.get("pace") for p in first_half if p.get("pace")]
            second_half_paces = [p.get("pace") for p in second_half if p.get("pace")]

            if first_half_paces and second_half_paces:
                first_half_pace = int(sum(first_half_paces) / len(first_half_paces))
                second_half_pace = int(sum(second_half_paces) / len(second_half_paces))

        # Fallback: estimate from splits if available
        if first_half_hr is None and "splits" in activity:
            splits = activity.get("splits", [])
            if len(splits) >= 2:
                mid = len(splits) // 2
                first_split_hrs = [s.get("avg_hr") or s.get("avgHR") for s in splits[:mid] if (s.get("avg_hr") or s.get("avgHR"))]
                second_split_hrs = [s.get("avg_hr") or s.get("avgHR") for s in splits[mid:] if (s.get("avg_hr") or s.get("avgHR"))]

                if first_split_hrs and second_split_hrs:
                    first_half_hr = sum(first_split_hrs) / len(first_split_hrs)
                    second_half_hr = sum(second_split_hrs) / len(second_split_hrs)

        # Cannot calculate drift without half-by-half data
        if first_half_hr is None or second_half_hr is None:
            return None

        # Calculate drift
        drift_bpm, drift_percent, severity = calculate_cardiac_drift(
            first_half_hr, second_half_hr
        )

        # Calculate pace change if available
        pace_change_percent = None
        if first_half_pace and second_half_pace and first_half_pace > 0:
            pace_change_percent = ((second_half_pace - first_half_pace) / first_half_pace) * 100

        return CardiacDriftAnalysis(
            workout_id=workout_id,
            workout_date=workout_date,
            first_half_hr=round(first_half_hr, 1),
            second_half_hr=round(second_half_hr, 1),
            drift_bpm=drift_bpm,
            drift_percent=drift_percent,
            severity=severity,
            is_concerning=severity in (CardiacDriftSeverity.CONCERNING, CardiacDriftSeverity.SIGNIFICANT),
            first_half_pace=first_half_pace,
            second_half_pace=second_half_pace,
            pace_change_percent=round(pace_change_percent, 1) if pace_change_percent else None,
            recommendation=get_drift_recommendation(drift_percent, severity),
        )

    def get_economy_trend(
        self,
        activities: List[Dict[str, Any]],
        days: int = 90,
    ) -> EconomyTrend:
        """
        Get running economy trend over a specified period.

        Args:
            activities: List of recent activities
            days: Number of days to analyze (default 90)

        Returns:
            EconomyTrend with trend analysis
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Filter and process running workouts
        economy_data: List[EconomyDataPoint] = []

        for activity in activities:
            metrics = self.calculate_economy(activity)
            if metrics:
                # Check if within date range
                try:
                    workout_date = date.fromisoformat(metrics.workout_date)
                    if start_date <= workout_date <= end_date:
                        economy_data.append(EconomyDataPoint(
                            date=metrics.workout_date,
                            economy_ratio=metrics.economy_ratio,
                            pace_sec_per_km=metrics.pace_sec_per_km,
                            avg_hr=metrics.avg_hr,
                            workout_id=metrics.workout_id,
                            pace_zone=metrics.pace_zone,
                        ))
                except (ValueError, TypeError):
                    continue

        # Sort by date
        economy_data.sort(key=lambda x: x.date)

        # Calculate trend metrics
        if not economy_data:
            return EconomyTrend(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                days=days,
                data_points=[],
                workout_count=0,
            )

        # Find best economy
        best_point = min(economy_data, key=lambda x: x.economy_ratio)
        current_point = economy_data[-1]

        # Calculate averages
        avg_economy = sum(p.economy_ratio for p in economy_data) / len(economy_data)
        avg_pace = sum(p.pace_sec_per_km for p in economy_data) // len(economy_data)
        avg_hr = sum(p.avg_hr for p in economy_data) // len(economy_data)

        # Calculate improvement (compare first quarter to last quarter)
        if len(economy_data) >= 4:
            quarter_size = len(economy_data) // 4
            first_quarter = economy_data[:quarter_size]
            last_quarter = economy_data[-quarter_size:]

            first_avg = sum(p.economy_ratio for p in first_quarter) / len(first_quarter)
            last_avg = sum(p.economy_ratio for p in last_quarter) / len(last_quarter)

            if first_avg > 0:
                improvement_percent = ((first_avg - last_avg) / first_avg) * 100
            else:
                improvement_percent = 0

            # Determine trend direction
            if improvement_percent > 3:
                trend_direction = "improving"
            elif improvement_percent < -3:
                trend_direction = "declining"
            else:
                trend_direction = "stable"
        else:
            improvement_percent = 0
            trend_direction = "stable"

        # Current vs best
        current_vs_best = None
        if best_point.economy_ratio > 0:
            current_vs_best = ((current_point.economy_ratio - best_point.economy_ratio) / best_point.economy_ratio) * 100

        return EconomyTrend(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            days=days,
            data_points=economy_data,
            workout_count=len(economy_data),
            improvement_percent=round(improvement_percent, 1),
            trend_direction=trend_direction,
            best_economy=best_point.economy_ratio,
            best_economy_date=best_point.date,
            best_economy_workout_id=best_point.workout_id,
            current_economy=current_point.economy_ratio,
            current_vs_best=round(current_vs_best, 1) if current_vs_best else None,
            avg_economy=round(avg_economy, 3),
            avg_pace_sec_per_km=avg_pace,
            avg_hr=avg_hr,
        )

    def get_pace_specific_economy(
        self,
        activities: List[Dict[str, Any]],
        days: int = 90,
    ) -> PaceZonesEconomy:
        """
        Get economy breakdown by pace zone.

        This shows how efficient the runner is at different intensities.

        Args:
            activities: List of recent activities
            days: Number of days to analyze

        Returns:
            PaceZonesEconomy with zone-by-zone breakdown
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Collect economy data by zone
        zone_data: Dict[PaceZone, List[float]] = {
            PaceZone.EASY: [],
            PaceZone.LONG: [],
            PaceZone.TEMPO: [],
            PaceZone.THRESHOLD: [],
            PaceZone.INTERVAL: [],
        }
        zone_paces: Dict[PaceZone, List[int]] = {zone: [] for zone in PaceZone}
        zone_hrs: Dict[PaceZone, List[int]] = {zone: [] for zone in PaceZone}

        for activity in activities:
            metrics = self.calculate_economy(activity)
            if metrics and metrics.pace_zone:
                try:
                    workout_date = date.fromisoformat(metrics.workout_date)
                    if start_date <= workout_date <= end_date:
                        zone_data[metrics.pace_zone].append(metrics.economy_ratio)
                        zone_paces[metrics.pace_zone].append(metrics.pace_sec_per_km)
                        zone_hrs[metrics.pace_zone].append(metrics.avg_hr)
                except (ValueError, TypeError):
                    continue

        # Build zone economy list
        zones: List[ZoneEconomy] = []
        total_workouts = 0
        best_zone = None
        best_economy = float("inf")

        zone_names = {
            PaceZone.EASY: "Easy",
            PaceZone.LONG: "Long Run",
            PaceZone.TEMPO: "Tempo",
            PaceZone.THRESHOLD: "Threshold",
            PaceZone.INTERVAL: "Interval",
        }

        for zone in PaceZone:
            data = zone_data[zone]
            if not data:
                continue

            avg_economy = sum(data) / len(data)
            min_economy = min(data)
            max_economy = max(data)

            paces = zone_paces[zone]
            hrs = zone_hrs[zone]

            avg_pace = sum(paces) // len(paces) if paces else 0
            avg_hr = sum(hrs) // len(hrs) if hrs else 0

            # Pace and HR ranges
            if paces:
                pace_range = f"{format_pace(min(paces))} - {format_pace(max(paces))}"
            else:
                pace_range = ""

            if hrs:
                hr_range = f"{min(hrs)} - {max(hrs)} bpm"
            else:
                hr_range = ""

            zones.append(ZoneEconomy(
                pace_zone=zone,
                zone_name=zone_names[zone],
                avg_economy=round(avg_economy, 3),
                best_economy=min_economy,
                worst_economy=max_economy,
                workout_count=len(data),
                avg_pace_sec_per_km=avg_pace,
                avg_hr=avg_hr,
                pace_range=pace_range,
                hr_range=hr_range,
            ))

            total_workouts += len(data)

            if min_economy < best_economy:
                best_economy = min_economy
                best_zone = zone

        return PaceZonesEconomy(
            zones=zones,
            total_workouts=total_workouts,
            best_zone=best_zone,
        )

    def get_cardiac_drift_trend(
        self,
        activities: List[Dict[str, Any]],
        time_series_by_workout: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        days: int = 90,
    ) -> CardiacDriftTrend:
        """
        Get cardiac drift trends over time.

        Args:
            activities: List of recent activities
            time_series_by_workout: Optional dict mapping workout IDs to time series
            days: Number of days to analyze

        Returns:
            CardiacDriftTrend with trend analysis
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        drift_data: List[Dict[str, Any]] = []
        concerning_count = 0

        for activity in activities:
            workout_id = activity.get("id") or activity.get("activity_id", "")

            # Get time series if available
            time_series = None
            if time_series_by_workout and workout_id in time_series_by_workout:
                time_series = time_series_by_workout[workout_id]

            analysis = self.detect_cardiac_drift(activity, time_series)
            if analysis:
                try:
                    workout_date = date.fromisoformat(analysis.workout_date)
                    if start_date <= workout_date <= end_date:
                        drift_data.append({
                            "date": analysis.workout_date,
                            "drift_percent": analysis.drift_percent,
                            "severity": analysis.severity.value,
                            "workout_id": analysis.workout_id,
                        })

                        if analysis.is_concerning:
                            concerning_count += 1
                except (ValueError, TypeError):
                    continue

        # Sort by date
        drift_data.sort(key=lambda x: x["date"])

        if not drift_data:
            return CardiacDriftTrend(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                data_points=[],
                avg_drift_percent=0,
                concerning_count=0,
                improvement_trend="stable",
                aerobic_base_assessment="Insufficient data to assess aerobic base.",
            )

        # Calculate averages
        avg_drift = sum(d["drift_percent"] for d in drift_data) / len(drift_data)

        # Determine trend (compare first half to second half)
        if len(drift_data) >= 4:
            mid = len(drift_data) // 2
            first_half_avg = sum(d["drift_percent"] for d in drift_data[:mid]) / mid
            second_half_avg = sum(d["drift_percent"] for d in drift_data[mid:]) / (len(drift_data) - mid)

            if first_half_avg - second_half_avg > 1.5:
                improvement_trend = "improving"
            elif second_half_avg - first_half_avg > 1.5:
                improvement_trend = "worsening"
            else:
                improvement_trend = "stable"
        else:
            improvement_trend = "stable"

        # Generate aerobic base assessment
        if avg_drift < 3:
            aerobic_base_assessment = "Excellent aerobic base. Your cardiovascular system maintains efficiency well during runs."
        elif avg_drift < 5:
            aerobic_base_assessment = "Good aerobic fitness. Continue with your current training to maintain and improve."
        elif avg_drift < 8:
            aerobic_base_assessment = "Room for aerobic improvement. Consider adding more Zone 2 runs and ensuring proper hydration."
        else:
            aerobic_base_assessment = "Aerobic base needs attention. Prioritize easy running, proper hydration, and adequate fueling during longer runs."

        return CardiacDriftTrend(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            data_points=drift_data,
            avg_drift_percent=round(avg_drift, 1),
            concerning_count=concerning_count,
            improvement_trend=improvement_trend,
            aerobic_base_assessment=aerobic_base_assessment,
        )

    def get_current_economy(
        self,
        activities: List[Dict[str, Any]],
    ) -> EconomyCurrentResponse:
        """
        Get the most recent economy metrics.

        Args:
            activities: List of recent activities (sorted newest first)

        Returns:
            EconomyCurrentResponse with latest metrics
        """
        # Get best economy for comparison
        trend = self.get_economy_trend(activities, days=365)
        best_economy = trend.best_economy if trend.workout_count > 0 else None

        # Find most recent valid running workout
        for activity in activities:
            metrics = self.calculate_economy(activity, best_economy)
            if metrics:
                return EconomyCurrentResponse(
                    metrics=metrics,
                    has_data=True,
                )

        return EconomyCurrentResponse(
            has_data=False,
            message="No recent running workouts found with pace and HR data.",
        )


# =============================================================================
# Singleton Instance
# =============================================================================

_running_economy_service: Optional[RunningEconomyService] = None


def get_running_economy_service() -> RunningEconomyService:
    """
    Get the running economy service singleton.

    Returns:
        RunningEconomyService instance
    """
    global _running_economy_service
    if _running_economy_service is None:
        _running_economy_service = RunningEconomyService()
    return _running_economy_service
