"""
Pattern Recognition Service for AI-driven training insights.

Analyzes workout history to identify:
- Optimal training times
- Performance correlations with TSB
- Peak fitness predictions
"""

import logging
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..models.patterns import (
    CorrelationAnalysis,
    CorrelationFactor,
    CTLProjection,
    DayOfWeek,
    DayPerformance,
    FitnessPrediction,
    OptimalWindow,
    PerformanceCorrelations,
    PlannedEvent,
    TimeOfDay,
    TimeSlotPerformance,
    TimingAnalysis,
    TSBOptimalRange,
    TSBPerformancePoint,
    TSBZone,
    TSBZoneStats,
    get_day_of_week,
    get_time_of_day,
    get_tsb_zone,
    get_tsb_zone_range,
)
from ..metrics.fitness import calculate_ewma


logger = logging.getLogger(__name__)


class PatternRecognitionService:
    """
    Service for analyzing training patterns and identifying optimization opportunities.

    Uses statistical analysis to find:
    - Best times of day for training
    - Best days of week for training
    - Optimal TSB ranges for peak performance
    - CTL trajectory predictions
    """

    MIN_WORKOUTS_FOR_ANALYSIS = 10
    MIN_WORKOUTS_PER_BUCKET = 3

    def __init__(self, training_db: Any):
        """
        Initialize the pattern recognition service.

        Args:
            training_db: Database instance for fetching workout data
        """
        self._db = training_db

    def analyze_timing_patterns(
        self,
        user_id: str,
        days: int = 90,
    ) -> TimingAnalysis:
        """
        Analyze performance patterns by time of day and day of week.

        Args:
            user_id: User ID to analyze
            days: Number of days to analyze (default 90)

        Returns:
            TimingAnalysis with identified optimal windows
        """
        # Fetch workout data
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        workouts = self._get_workouts_with_performance(user_id, start_date, end_date)

        if len(workouts) < self.MIN_WORKOUTS_FOR_ANALYSIS:
            return TimingAnalysis(
                user_id=user_id,
                analysis_period_days=days,
                total_workouts_analyzed=len(workouts),
                data_quality_score=0.0,
            )

        # Bucket workouts by time of day
        time_buckets: Dict[TimeOfDay, List[Dict]] = defaultdict(list)
        for w in workouts:
            start_time = w.get("start_time")
            if start_time:
                try:
                    if isinstance(start_time, str):
                        # Parse time from string (HH:MM:SS)
                        hour = int(start_time.split(":")[0])
                    elif isinstance(start_time, datetime):
                        hour = start_time.hour
                    else:
                        continue

                    time_slot = get_time_of_day(hour)
                    time_buckets[time_slot].append(w)
                except (ValueError, IndexError):
                    continue

        # Bucket workouts by day of week
        day_buckets: Dict[DayOfWeek, List[Dict]] = defaultdict(list)
        for w in workouts:
            workout_date = w.get("date")
            if workout_date:
                if isinstance(workout_date, str):
                    workout_date = date.fromisoformat(workout_date)
                day = get_day_of_week(workout_date)
                day_buckets[day].append(w)

        # Calculate performance by time slot
        time_slot_performance = []
        for time_slot in TimeOfDay:
            bucket = time_buckets.get(time_slot, [])
            if bucket:
                perf = self._calculate_bucket_performance(bucket)
                time_slot_performance.append(
                    TimeSlotPerformance(
                        time_slot=time_slot,
                        workout_count=len(bucket),
                        avg_performance_score=perf["avg_performance"],
                        avg_hr_efficiency=perf["avg_hr_efficiency"],
                        avg_execution_rating=perf.get("avg_execution_rating"),
                        sample_workouts=[w["activity_id"] for w in bucket[:5]],
                    )
                )

        # Calculate performance by day
        day_performance = []
        for day in DayOfWeek:
            bucket = day_buckets.get(day, [])
            if bucket:
                perf = self._calculate_bucket_performance(bucket)
                workout_types = list(set(w.get("activity_type", "running") for w in bucket))
                day_performance.append(
                    DayPerformance(
                        day=day,
                        workout_count=len(bucket),
                        avg_performance_score=perf["avg_performance"],
                        avg_training_load=perf["avg_load"],
                        preferred_workout_types=workout_types[:3],
                        sample_workouts=[w["activity_id"] for w in bucket[:5]],
                    )
                )

        # Find optimal windows
        optimal_windows = []
        avg_performance = self._calculate_overall_average(workouts)

        # Find best time slot
        best_time_slot = None
        best_time_boost = 0.0
        for slot_perf in time_slot_performance:
            if slot_perf.is_significant and avg_performance > 0:
                boost = (slot_perf.avg_performance_score / avg_performance - 1) * 100
                if boost > best_time_boost:
                    best_time_boost = boost
                    best_time_slot = slot_perf.time_slot

                if boost > 5:  # More than 5% improvement
                    optimal_windows.append(
                        OptimalWindow(
                            time_slot=slot_perf.time_slot,
                            performance_boost=boost,
                            confidence=min(slot_perf.workout_count / 20, 1.0),
                            sample_size=slot_perf.workout_count,
                        )
                    )

        # Find best day
        best_day = None
        best_day_boost = 0.0
        for day_perf in day_performance:
            if day_perf.workout_count >= self.MIN_WORKOUTS_PER_BUCKET and avg_performance > 0:
                boost = (day_perf.avg_performance_score / avg_performance - 1) * 100
                if boost > best_day_boost:
                    best_day_boost = boost
                    best_day = day_perf.day

        # Find worst performers
        avoid_time_slot = None
        worst_time_boost = 0.0
        for slot_perf in time_slot_performance:
            if slot_perf.is_significant and avg_performance > 0:
                boost = (slot_perf.avg_performance_score / avg_performance - 1) * 100
                if boost < worst_time_boost:
                    worst_time_boost = boost
                    avoid_time_slot = slot_perf.time_slot

        avoid_day = None
        worst_day_boost = 0.0
        for day_perf in day_performance:
            if day_perf.workout_count >= self.MIN_WORKOUTS_PER_BUCKET and avg_performance > 0:
                boost = (day_perf.avg_performance_score / avg_performance - 1) * 100
                if boost < worst_day_boost:
                    worst_day_boost = boost
                    avoid_day = day_perf.day

        # Calculate data quality score
        time_coverage = len([s for s in time_slot_performance if s.is_significant]) / len(TimeOfDay)
        day_coverage = len([d for d in day_performance if d.workout_count >= self.MIN_WORKOUTS_PER_BUCKET]) / len(DayOfWeek)
        sample_size_score = min(len(workouts) / 50, 1.0)
        data_quality = (time_coverage + day_coverage + sample_size_score) / 3

        return TimingAnalysis(
            user_id=user_id,
            analysis_period_days=days,
            time_slot_performance=time_slot_performance,
            day_performance=day_performance,
            optimal_windows=sorted(optimal_windows, key=lambda x: -x.performance_boost),
            best_time_slot=best_time_slot,
            best_time_slot_boost=best_time_boost,
            best_day=best_day,
            best_day_boost=best_day_boost,
            avoid_time_slot=avoid_time_slot,
            avoid_day=avoid_day,
            total_workouts_analyzed=len(workouts),
            data_quality_score=data_quality,
        )

    def find_optimal_tsb_range(
        self,
        user_id: str,
        days: int = 180,
    ) -> TSBOptimalRange:
        """
        Find the optimal TSB range for peak performance.

        Analyzes historical workouts to identify the TSB range
        where the athlete performs best.

        Args:
            user_id: User ID to analyze
            days: Number of days to analyze (default 180)

        Returns:
            TSBOptimalRange with optimal range and recommendations
        """
        # Fetch workout data with fitness metrics
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        workouts = self._get_workouts_with_fitness(user_id, start_date, end_date)

        if len(workouts) < self.MIN_WORKOUTS_FOR_ANALYSIS:
            return TSBOptimalRange(
                user_id=user_id,
                analysis_period_days=days,
                total_workouts_analyzed=len(workouts),
                data_quality_score=0.0,
            )

        # Create data points
        data_points = []
        zone_data: Dict[TSBZone, List[float]] = defaultdict(list)

        for w in workouts:
            tsb = w.get("tsb")
            ctl = w.get("ctl", 0)
            atl = w.get("atl", 0)
            performance = self._calculate_performance_score(w)

            if tsb is not None and performance is not None:
                workout_date = w.get("date")
                if isinstance(workout_date, str):
                    workout_date = date.fromisoformat(workout_date)

                data_points.append(
                    TSBPerformancePoint(
                        workout_id=w.get("activity_id", ""),
                        workout_date=workout_date,
                        tsb=tsb,
                        ctl=ctl,
                        atl=atl,
                        performance_score=performance,
                        workout_type=w.get("activity_type", "running"),
                        distance_km=w.get("distance_km"),
                        duration_min=w.get("duration_min"),
                    )
                )

                zone = get_tsb_zone(tsb)
                zone_data[zone].append(performance)

        # Calculate zone statistics
        zone_stats = []
        for zone in TSBZone:
            performances = zone_data.get(zone, [])
            if performances:
                zone_stats.append(
                    TSBZoneStats(
                        zone=zone,
                        tsb_range=get_tsb_zone_range(zone),
                        workout_count=len(performances),
                        avg_performance=sum(performances) / len(performances),
                        std_performance=self._calculate_std(performances),
                        best_performance=max(performances),
                        worst_performance=min(performances),
                    )
                )

        # Find optimal zone (highest average performance with significant sample)
        optimal_zone = TSBZone.FRESH
        optimal_avg = 0.0
        for stat in zone_stats:
            if stat.workout_count >= self.MIN_WORKOUTS_PER_BUCKET:
                if stat.avg_performance > optimal_avg:
                    optimal_avg = stat.avg_performance
                    optimal_zone = stat.zone

        optimal_range = get_tsb_zone_range(optimal_zone)

        # Calculate correlation coefficient
        if len(data_points) >= 10:
            tsb_values = [p.tsb for p in data_points]
            perf_values = [p.performance_score for p in data_points]
            correlation, p_value = self._calculate_correlation(tsb_values, perf_values)
        else:
            correlation = 0.0
            p_value = 1.0

        # Get current fitness state
        current_tsb = None
        days_to_peak = None
        if workouts:
            latest = sorted(workouts, key=lambda x: x.get("date", ""), reverse=True)[0]
            current_tsb = latest.get("tsb")

            if current_tsb is not None:
                target_tsb = (optimal_range[0] + optimal_range[1]) / 2
                if current_tsb < target_tsb:
                    # Estimate days to reach target TSB
                    # Rough estimate: TSB increases ~2-3 per day of rest
                    days_to_peak = max(1, int((target_tsb - current_tsb) / 2.5))

        # Calculate data quality
        zone_coverage = len([s for s in zone_stats if s.workout_count >= self.MIN_WORKOUTS_PER_BUCKET]) / len(TSBZone)
        sample_score = min(len(data_points) / 50, 1.0)
        data_quality = (zone_coverage + sample_score) / 2

        return TSBOptimalRange(
            user_id=user_id,
            analysis_period_days=days,
            optimal_tsb_min=optimal_range[0],
            optimal_tsb_max=optimal_range[1],
            optimal_zone=optimal_zone,
            zone_stats=zone_stats,
            data_points=sorted(data_points, key=lambda x: x.workout_date)[-100:],  # Limit to last 100
            tsb_performance_correlation=correlation,
            correlation_confidence=1 - p_value if p_value < 1 else 0,
            recommended_taper_days=10 if optimal_zone in [TSBZone.FRESH, TSBZone.PEAKED] else 7,
            peak_tsb_target=(optimal_range[0] + optimal_range[1]) / 2,
            current_tsb=current_tsb,
            days_to_peak=days_to_peak,
            total_workouts_analyzed=len(workouts),
            data_quality_score=data_quality,
        )

    def predict_peak_fitness(
        self,
        user_id: str,
        target_date: Optional[date] = None,
        horizon_days: int = 90,
    ) -> FitnessPrediction:
        """
        Predict when CTL will peak and project fitness trajectory.

        Args:
            user_id: User ID to analyze
            target_date: Optional target date (race/goal)
            horizon_days: How far to project (default 90 days)

        Returns:
            FitnessPrediction with trajectory and recommendations
        """
        # Get current fitness state
        current_fitness = self._get_current_fitness(user_id)
        if not current_fitness:
            return FitnessPrediction(
                user_id=user_id,
                prediction_horizon_days=horizon_days,
            )

        current_ctl = current_fitness.get("ctl", 0)
        current_atl = current_fitness.get("atl", 0)
        current_tsb = current_fitness.get("tsb", 0)

        # Calculate average weekly load from recent data
        recent_loads = self._get_recent_weekly_loads(user_id, weeks=4)
        avg_weekly_load = sum(recent_loads) / len(recent_loads) if recent_loads else 0

        # Project CTL trajectory
        ctl_projection = []
        today = date.today()

        # Add historical data points (last 30 days)
        historical = self._get_historical_fitness(user_id, days=30)
        for entry in historical:
            entry_date = entry.get("date")
            if isinstance(entry_date, str):
                entry_date = date.fromisoformat(entry_date)
            ctl_projection.append(
                CTLProjection(
                    date=entry_date,
                    projected_ctl=entry.get("ctl", 0),
                    confidence_lower=entry.get("ctl", 0),
                    confidence_upper=entry.get("ctl", 0),
                    is_historical=True,
                )
            )

        # Project future CTL
        projected_ctl = current_ctl
        daily_load = avg_weekly_load / 7 if avg_weekly_load > 0 else 50  # Default if no data

        natural_peak_date = None
        natural_peak_ctl = current_ctl

        for i in range(1, horizon_days + 1):
            future_date = today + timedelta(days=i)

            # Simple projection: assume consistent daily load
            projected_ctl = calculate_ewma(daily_load, projected_ctl, 42)

            # Calculate confidence bounds (wider as we go further)
            uncertainty = 0.05 * i  # 5% per day
            confidence_lower = projected_ctl * (1 - uncertainty)
            confidence_upper = projected_ctl * (1 + uncertainty)

            ctl_projection.append(
                CTLProjection(
                    date=future_date,
                    projected_ctl=projected_ctl,
                    confidence_lower=confidence_lower,
                    confidence_upper=confidence_upper,
                    is_historical=False,
                )
            )

            # Track peak
            if projected_ctl > natural_peak_ctl:
                natural_peak_ctl = projected_ctl
                natural_peak_date = future_date

        # Calculate days to natural peak
        days_to_natural_peak = None
        if natural_peak_date:
            days_to_natural_peak = (natural_peak_date - today).days

        # Target date analysis
        projected_ctl_at_target = None
        projected_tsb_at_target = None
        weekly_load_recommendation = avg_weekly_load
        load_change_percentage = 0.0
        taper_start_date = None
        target_event = None

        if target_date:
            days_to_target = (target_date - today).days
            if days_to_target > 0:
                # Find CTL at target date
                for proj in ctl_projection:
                    if proj.date == target_date:
                        projected_ctl_at_target = proj.projected_ctl
                        break

                # Estimate TSB at target (simplified: assume ~10 day taper)
                taper_days = min(14, max(7, days_to_target // 3))
                taper_start_date = target_date - timedelta(days=taper_days)

                # During taper, load drops to ~50%, TSB rises
                if days_to_target >= taper_days:
                    projected_tsb_at_target = 10.0  # Target fresh state
                else:
                    projected_tsb_at_target = current_tsb + (days_to_target * 2)

                # Calculate load recommendations
                if projected_ctl_at_target and projected_ctl_at_target < current_ctl * 0.95:
                    # Need to increase load to reach target
                    load_change_percentage = 10.0
                    weekly_load_recommendation = avg_weekly_load * 1.1
                elif projected_ctl_at_target and projected_ctl_at_target > current_ctl * 1.1:
                    # Can reduce load slightly
                    load_change_percentage = -5.0
                    weekly_load_recommendation = avg_weekly_load * 0.95

                target_event = PlannedEvent(
                    name="Target Race",
                    event_date=target_date,
                    event_type="race",
                    priority="A",
                )

        # Fetch planned events
        planned_events = self._get_planned_events(user_id)
        if target_event:
            planned_events.insert(0, target_event)

        # Prediction confidence (based on data quality)
        prediction_confidence = min(len(recent_loads) / 4, 1.0)

        return FitnessPrediction(
            user_id=user_id,
            prediction_horizon_days=horizon_days,
            current_ctl=current_ctl,
            current_atl=current_atl,
            current_tsb=current_tsb,
            current_weekly_load=avg_weekly_load,
            natural_peak_date=natural_peak_date,
            natural_peak_ctl=natural_peak_ctl,
            days_to_natural_peak=days_to_natural_peak,
            target_event=target_event,
            target_date=target_date,
            projected_ctl_at_target=projected_ctl_at_target,
            projected_tsb_at_target=projected_tsb_at_target,
            ctl_projection=ctl_projection,
            weekly_load_recommendation=weekly_load_recommendation,
            load_change_percentage=load_change_percentage,
            taper_start_date=taper_start_date,
            prediction_confidence=prediction_confidence,
            planned_events=planned_events,
        )

    def get_performance_correlations(
        self,
        user_id: str,
        days: int = 180,
    ) -> PerformanceCorrelations:
        """
        Analyze what factors correlate with performance.

        Args:
            user_id: User ID to analyze
            days: Number of days to analyze

        Returns:
            PerformanceCorrelations with identified factors
        """
        # Fetch comprehensive workout data
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        workouts = self._get_workouts_with_context(user_id, start_date, end_date)

        if len(workouts) < self.MIN_WORKOUTS_FOR_ANALYSIS:
            return PerformanceCorrelations(
                user_id=user_id,
                analysis_period_days=days,
                total_workouts_analyzed=len(workouts),
                data_quality_score=0.0,
            )

        # Extract performance scores
        performances = []
        for w in workouts:
            score = self._calculate_performance_score(w)
            if score is not None:
                performances.append({"workout": w, "score": score})

        if len(performances) < self.MIN_WORKOUTS_FOR_ANALYSIS:
            return PerformanceCorrelations(
                user_id=user_id,
                analysis_period_days=days,
                total_workouts_analyzed=len(performances),
                data_quality_score=0.0,
            )

        # Analyze correlations with various factors
        correlations = []
        perf_values = [p["score"] for p in performances]

        # TSB correlation
        tsb_values = [p["workout"].get("tsb") for p in performances]
        if all(v is not None for v in tsb_values):
            r, p = self._calculate_correlation(tsb_values, perf_values)
            correlations.append(
                CorrelationFactor(
                    factor_name="TSB (Form)",
                    correlation_coefficient=r,
                    p_value=p,
                    sample_size=len(performances),
                    is_significant=p < 0.05,
                )
            )

        # Sleep (if available)
        sleep_values = [p["workout"].get("prev_night_sleep_hours") for p in performances]
        valid_sleep = [(s, p) for s, p in zip(sleep_values, perf_values) if s is not None]
        if len(valid_sleep) >= 10:
            r, p = self._calculate_correlation(
                [v[0] for v in valid_sleep],
                [v[1] for v in valid_sleep],
            )
            correlations.append(
                CorrelationFactor(
                    factor_name="Previous Night Sleep",
                    correlation_coefficient=r,
                    p_value=p,
                    sample_size=len(valid_sleep),
                    is_significant=p < 0.05,
                )
            )

        # Days since last workout
        days_rest = [p["workout"].get("days_since_last_workout") for p in performances]
        valid_rest = [(d, p) for d, p in zip(days_rest, perf_values) if d is not None]
        if len(valid_rest) >= 10:
            r, p = self._calculate_correlation(
                [v[0] for v in valid_rest],
                [v[1] for v in valid_rest],
            )
            correlations.append(
                CorrelationFactor(
                    factor_name="Rest Days Before",
                    correlation_coefficient=r,
                    p_value=p,
                    sample_size=len(valid_rest),
                    is_significant=p < 0.05,
                )
            )

        # Weekly load
        weekly_load = [p["workout"].get("weekly_load_so_far") for p in performances]
        valid_load = [(l, p) for l, p in zip(weekly_load, perf_values) if l is not None]
        if len(valid_load) >= 10:
            r, p = self._calculate_correlation(
                [v[0] for v in valid_load],
                [v[1] for v in valid_load],
            )
            correlations.append(
                CorrelationFactor(
                    factor_name="Week-to-Date Training Load",
                    correlation_coefficient=r,
                    p_value=p,
                    sample_size=len(valid_load),
                    is_significant=p < 0.05,
                )
            )

        # CTL (fitness level)
        ctl_values = [p["workout"].get("ctl") for p in performances]
        valid_ctl = [(c, p) for c, p in zip(ctl_values, perf_values) if c is not None]
        if len(valid_ctl) >= 10:
            r, p = self._calculate_correlation(
                [v[0] for v in valid_ctl],
                [v[1] for v in valid_ctl],
            )
            correlations.append(
                CorrelationFactor(
                    factor_name="Fitness (CTL)",
                    correlation_coefficient=r,
                    p_value=p,
                    sample_size=len(valid_ctl),
                    is_significant=p < 0.05,
                )
            )

        # Sort by absolute correlation
        correlations.sort(key=lambda x: abs(x.correlation_coefficient), reverse=True)

        # Extract top factors
        top_positive = [
            c.factor_name
            for c in correlations
            if c.is_significant and c.correlation_coefficient > 0.2
        ][:3]

        top_negative = [
            c.factor_name
            for c in correlations
            if c.is_significant and c.correlation_coefficient < -0.2
        ][:3]

        # Generate insights
        insights = self._generate_correlation_insights(correlations)

        # Data quality
        data_quality = min(len(performances) / 50, 1.0)

        return PerformanceCorrelations(
            user_id=user_id,
            analysis_period_days=days,
            correlations=correlations,
            top_positive_factors=top_positive,
            top_negative_factors=top_negative,
            key_insights=insights,
            total_workouts_analyzed=len(performances),
            data_quality_score=data_quality,
        )

    # ==========================================================================
    # Private Helper Methods
    # ==========================================================================

    def _get_workouts_with_performance(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
    ) -> List[Dict]:
        """Fetch workouts with performance data."""
        try:
            activities = self._db.get_activities_in_range(
                start_date.isoformat(),
                end_date.isoformat(),
            )
            return [a.to_dict() if hasattr(a, "to_dict") else a for a in activities]
        except Exception as e:
            logger.error(f"Failed to fetch workouts: {e}")
            return []

    def _get_workouts_with_fitness(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
    ) -> List[Dict]:
        """Fetch workouts with fitness metrics (CTL, ATL, TSB)."""
        try:
            # Get workouts
            activities = self._db.get_activities_in_range(
                start_date.isoformat(),
                end_date.isoformat(),
            )
            workout_list = [a.to_dict() if hasattr(a, "to_dict") else a for a in activities]

            # Enrich with fitness data if available
            for w in workout_list:
                workout_date = w.get("date")
                if workout_date:
                    fitness = self._db.get_fitness_metrics_for_date(workout_date)
                    if fitness:
                        w["ctl"] = fitness.get("ctl", 0)
                        w["atl"] = fitness.get("atl", 0)
                        w["tsb"] = fitness.get("tsb", 0)

            return workout_list
        except Exception as e:
            logger.error(f"Failed to fetch workouts with fitness: {e}")
            return []

    def _get_workouts_with_context(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
    ) -> List[Dict]:
        """Fetch workouts with full context for correlation analysis."""
        return self._get_workouts_with_fitness(user_id, start_date, end_date)

    def _get_current_fitness(self, user_id: str) -> Optional[Dict]:
        """Get current fitness state."""
        try:
            return self._db.get_current_fitness_metrics()
        except Exception as e:
            logger.error(f"Failed to get current fitness: {e}")
            return None

    def _get_recent_weekly_loads(self, user_id: str, weeks: int = 4) -> List[float]:
        """Get weekly training loads for recent weeks."""
        try:
            loads = []
            today = date.today()
            for week in range(weeks):
                start = today - timedelta(days=7 * (week + 1))
                end = today - timedelta(days=7 * week)
                activities = self._db.get_activities_in_range(
                    start.isoformat(),
                    end.isoformat(),
                )
                weekly_load = sum(
                    a.get("hrss", 0) or a.get("trimp", 0) or 0
                    for a in [act.to_dict() if hasattr(act, "to_dict") else act for act in activities]
                )
                loads.append(weekly_load)
            return loads
        except Exception as e:
            logger.error(f"Failed to get weekly loads: {e}")
            return []

    def _get_historical_fitness(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get historical fitness metrics."""
        try:
            return self._db.get_fitness_history(days) or []
        except Exception as e:
            logger.error(f"Failed to get fitness history: {e}")
            return []

    def _get_planned_events(self, user_id: str) -> List[PlannedEvent]:
        """Get planned races/events."""
        try:
            goals = self._db.get_race_goals() or []
            events = []
            for goal in goals:
                race_date = goal.get("race_date")
                if race_date:
                    if isinstance(race_date, str):
                        race_date = date.fromisoformat(race_date)
                    events.append(
                        PlannedEvent(
                            event_id=goal.get("id"),
                            name=goal.get("race_name", "Race"),
                            event_date=race_date,
                            event_type="race",
                            priority=goal.get("priority", "A"),
                        )
                    )
            return events
        except Exception as e:
            logger.error(f"Failed to get planned events: {e}")
            return []

    def _calculate_performance_score(self, workout: Dict) -> Optional[float]:
        """
        Calculate a normalized performance score for a workout.

        Uses HR efficiency, pace, and execution rating.
        Returns a score from 0-100.
        """
        scores = []

        # HR efficiency (lower HR for same pace = better)
        avg_hr = workout.get("avg_hr")
        avg_pace = workout.get("avg_pace_sec_km")
        if avg_hr and avg_pace and avg_pace > 0:
            # HR per pace unit (lower is better)
            efficiency = avg_hr / (avg_pace / 60)  # HR per min/km
            # Normalize: typical range is 30-50
            efficiency_score = max(0, min(100, (50 - efficiency) * 5 + 50))
            scores.append(efficiency_score)

        # Pace relative to expected (if zones available)
        # For now, use raw pace as indicator

        # Execution rating
        execution = workout.get("execution_rating")
        if execution:
            rating_scores = {
                "excellent": 95,
                "good": 80,
                "fair": 60,
                "needs_improvement": 40,
            }
            scores.append(rating_scores.get(execution, 60))

        # Training effect score
        te_score = workout.get("training_effect_score")
        if te_score:
            scores.append(te_score * 20)  # Scale 0-5 to 0-100

        if scores:
            return sum(scores) / len(scores)
        return None

    def _calculate_bucket_performance(self, workouts: List[Dict]) -> Dict:
        """Calculate aggregate performance metrics for a bucket of workouts."""
        performances = []
        hr_efficiencies = []
        execution_ratings = []
        loads = []

        for w in workouts:
            perf = self._calculate_performance_score(w)
            if perf is not None:
                performances.append(perf)

            avg_hr = w.get("avg_hr")
            avg_pace = w.get("avg_pace_sec_km")
            if avg_hr and avg_pace and avg_pace > 0:
                hr_efficiencies.append(avg_hr / (avg_pace / 60))

            execution = w.get("execution_rating")
            if execution:
                rating_values = {
                    "excellent": 4,
                    "good": 3,
                    "fair": 2,
                    "needs_improvement": 1,
                }
                execution_ratings.append(rating_values.get(execution, 2))

            load = w.get("hrss") or w.get("trimp") or 0
            loads.append(load)

        return {
            "avg_performance": sum(performances) / len(performances) if performances else 0,
            "avg_hr_efficiency": sum(hr_efficiencies) / len(hr_efficiencies) if hr_efficiencies else 0,
            "avg_execution_rating": sum(execution_ratings) / len(execution_ratings) if execution_ratings else None,
            "avg_load": sum(loads) / len(loads) if loads else 0,
        }

    def _calculate_overall_average(self, workouts: List[Dict]) -> float:
        """Calculate overall average performance across all workouts."""
        performances = []
        for w in workouts:
            perf = self._calculate_performance_score(w)
            if perf is not None:
                performances.append(perf)
        return sum(performances) / len(performances) if performances else 0

    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)

    def _calculate_correlation(
        self,
        x: List[float],
        y: List[float],
    ) -> Tuple[float, float]:
        """
        Calculate Pearson correlation coefficient and p-value.

        Returns:
            Tuple of (correlation coefficient, p-value)
        """
        n = len(x)
        if n < 3 or n != len(y):
            return 0.0, 1.0

        # Calculate means
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        # Calculate correlation
        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        denominator_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
        denominator_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))

        if denominator_x == 0 or denominator_y == 0:
            return 0.0, 1.0

        r = numerator / (denominator_x * denominator_y)

        # Calculate t-statistic and p-value (simplified)
        if abs(r) >= 1:
            p_value = 0.0
        else:
            t_stat = r * math.sqrt(n - 2) / math.sqrt(1 - r ** 2)
            # Approximate p-value using normal distribution for large n
            p_value = 2 * (1 - self._normal_cdf(abs(t_stat)))

        return round(r, 3), round(p_value, 4)

    def _normal_cdf(self, x: float) -> float:
        """Approximate normal CDF using error function."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def _generate_correlation_insights(
        self,
        correlations: List[CorrelationFactor],
    ) -> List[str]:
        """Generate human-readable insights from correlations."""
        insights = []

        for corr in correlations[:5]:  # Top 5 correlations
            if corr.is_significant:
                direction = "positively" if corr.correlation_coefficient > 0 else "negatively"
                strength = corr.correlation_strength

                if strength in ["strong", "moderate"]:
                    insights.append(
                        f"{corr.factor_name} is {strength}ly {direction} correlated with performance"
                    )

        # Add specific recommendations
        for corr in correlations:
            if corr.factor_name == "TSB (Form)" and corr.is_significant:
                if corr.correlation_coefficient > 0.3:
                    insights.append("You perform better when well-rested (higher TSB)")
                elif corr.correlation_coefficient < -0.3:
                    insights.append("You may be detrained when too rested - maintain training load")

            if corr.factor_name == "Previous Night Sleep" and corr.is_significant:
                if corr.correlation_coefficient > 0.3:
                    insights.append("Sleep quality strongly impacts your performance")

        return insights[:5]  # Limit to top 5 insights
