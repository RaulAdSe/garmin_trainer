"""
Workout Adaptation Engine for intelligent training adjustments.

Tracks planned vs completed workouts, analyzes performance trends,
predicts workout outcomes, and auto-adjusts upcoming workouts.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import statistics


class AdaptationTrigger(str, Enum):
    """Reasons for workout adaptation."""
    OVERREACHING = "overreaching"  # ATL much higher than CTL
    UNDERTRAINING = "undertraining"  # Not hitting targets consistently
    PERFORMANCE_DECLINE = "performance_decline"  # Declining trends
    RECOVERY_NEEDED = "recovery_needed"  # Low TSB, high fatigue
    RACE_TAPER = "race_taper"  # Approaching race
    ILLNESS_RECOVERY = "illness_recovery"  # Coming back from illness
    MANUAL_ADJUSTMENT = "manual_adjustment"  # User requested


class AdaptationType(str, Enum):
    """Types of workout adaptations."""
    REDUCE_VOLUME = "reduce_volume"  # Less time/distance
    REDUCE_INTENSITY = "reduce_intensity"  # Easier effort
    INCREASE_VOLUME = "increase_volume"  # More time/distance
    INCREASE_INTENSITY = "increase_intensity"  # Harder effort
    ADD_RECOVERY = "add_recovery"  # Insert recovery day
    SKIP_WORKOUT = "skip_workout"  # Remove workout
    SWAP_WORKOUT = "swap_workout"  # Replace with different type
    MAINTAIN = "maintain"  # No change needed


@dataclass
class WorkoutCompletion:
    """
    Tracks a completed workout against its planned version.
    """
    workout_id: str
    planned_date: date
    completed_date: Optional[date]
    
    # Planned metrics
    planned_duration_min: int
    planned_load: float
    planned_type: str
    
    # Completed metrics (None if not completed)
    actual_duration_min: Optional[int] = None
    actual_load: Optional[float] = None
    actual_avg_hr: Optional[int] = None
    actual_distance_km: Optional[float] = None
    
    # Subjective feedback
    rpe: Optional[int] = None  # 1-10 Rate of Perceived Exertion
    feeling: Optional[str] = None  # "great", "good", "ok", "tired", "exhausted"
    notes: Optional[str] = None
    
    @property
    def was_completed(self) -> bool:
        """Check if workout was completed."""
        return self.completed_date is not None
    
    @property
    def compliance_pct(self) -> Optional[float]:
        """Calculate compliance percentage (actual vs planned load)."""
        if not self.was_completed or self.actual_load is None:
            return None
        if self.planned_load <= 0:
            return 100.0
        return min(150.0, (self.actual_load / self.planned_load) * 100)
    
    @property
    def duration_compliance_pct(self) -> Optional[float]:
        """Calculate duration compliance percentage."""
        if not self.was_completed or self.actual_duration_min is None:
            return None
        if self.planned_duration_min <= 0:
            return 100.0
        return min(150.0, (self.actual_duration_min / self.planned_duration_min) * 100)
    
    def to_dict(self) -> dict:
        return {
            "workout_id": self.workout_id,
            "planned_date": self.planned_date.isoformat(),
            "completed_date": self.completed_date.isoformat() if self.completed_date else None,
            "planned_duration_min": self.planned_duration_min,
            "planned_load": self.planned_load,
            "planned_type": self.planned_type,
            "actual_duration_min": self.actual_duration_min,
            "actual_load": self.actual_load,
            "actual_avg_hr": self.actual_avg_hr,
            "actual_distance_km": self.actual_distance_km,
            "rpe": self.rpe,
            "feeling": self.feeling,
            "notes": self.notes,
            "was_completed": self.was_completed,
            "compliance_pct": self.compliance_pct,
        }


@dataclass
class PerformanceTrend:
    """
    Analysis of performance trends over time.
    """
    metric_name: str
    period_days: int
    values: List[float]
    dates: List[date]
    
    @property
    def trend_direction(self) -> str:
        """Calculate trend direction: improving, declining, or stable."""
        if len(self.values) < 3:
            return "insufficient_data"
        
        # Simple linear regression slope
        n = len(self.values)
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(self.values)
        
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(self.values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        # Normalize slope by mean value
        if y_mean > 0:
            normalized_slope = slope / y_mean * 100  # % change per data point
        else:
            normalized_slope = slope
        
        # Threshold for significance
        if normalized_slope > 1.0:
            return "improving"
        elif normalized_slope < -1.0:
            return "declining"
        else:
            return "stable"
    
    @property
    def current_value(self) -> Optional[float]:
        """Get most recent value."""
        return self.values[-1] if self.values else None
    
    @property
    def average_value(self) -> Optional[float]:
        """Get average value over period."""
        return statistics.mean(self.values) if self.values else None
    
    @property
    def change_pct(self) -> Optional[float]:
        """Calculate percentage change from start to end."""
        if len(self.values) < 2:
            return None
        if self.values[0] == 0:
            return None
        return ((self.values[-1] - self.values[0]) / self.values[0]) * 100
    
    def to_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "period_days": self.period_days,
            "trend_direction": self.trend_direction,
            "current_value": self.current_value,
            "average_value": self.average_value,
            "change_pct": self.change_pct,
            "data_points": len(self.values),
        }


@dataclass
class AdaptationRecommendation:
    """
    A recommendation for adapting upcoming workouts.
    """
    trigger: AdaptationTrigger
    adaptation_type: AdaptationType
    target_workout_id: Optional[str]
    target_date: Optional[date]
    
    # Adjustment parameters
    volume_multiplier: float = 1.0  # e.g., 0.8 = reduce 20%
    intensity_multiplier: float = 1.0
    
    # Explanation
    reason: str = ""
    confidence: float = 0.8  # 0-1 confidence in recommendation
    
    # Status
    applied: bool = False
    applied_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "trigger": self.trigger.value,
            "adaptation_type": self.adaptation_type.value,
            "target_workout_id": self.target_workout_id,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "volume_multiplier": self.volume_multiplier,
            "intensity_multiplier": self.intensity_multiplier,
            "reason": self.reason,
            "confidence": self.confidence,
            "applied": self.applied,
        }


@dataclass
class WorkoutPrediction:
    """
    Predicted outcome for a planned workout.
    """
    workout_id: str
    planned_date: date
    planned_type: str
    
    # Predictions
    predicted_load: float
    predicted_completion_probability: float  # 0-1
    predicted_quality: str  # "excellent", "good", "moderate", "poor"
    
    # Factors affecting prediction
    current_fatigue_level: float  # 0-1
    recent_compliance_rate: float  # 0-1
    days_since_rest: int
    
    # Risk assessment
    injury_risk: str  # "low", "moderate", "high"
    overtraining_risk: str
    
    def to_dict(self) -> dict:
        return {
            "workout_id": self.workout_id,
            "planned_date": self.planned_date.isoformat(),
            "planned_type": self.planned_type,
            "predicted_load": self.predicted_load,
            "predicted_completion_probability": self.predicted_completion_probability,
            "predicted_quality": self.predicted_quality,
            "current_fatigue_level": self.current_fatigue_level,
            "recent_compliance_rate": self.recent_compliance_rate,
            "days_since_rest": self.days_since_rest,
            "injury_risk": self.injury_risk,
            "overtraining_risk": self.overtraining_risk,
        }


class WorkoutAdaptationEngine:
    """
    Intelligent engine for adapting training based on performance data.
    
    Features:
    - Track planned vs completed workouts
    - Analyze performance trends
    - Predict workout outcomes
    - Generate adaptation recommendations
    """
    
    def __init__(self):
        """Initialize the adaptation engine."""
        self._completions: List[WorkoutCompletion] = []
        self._recommendations: List[AdaptationRecommendation] = []
    
    def record_completion(self, completion: WorkoutCompletion) -> None:
        """Record a workout completion."""
        self._completions.append(completion)
    
    def get_compliance_rate(self, days: int = 14) -> float:
        """
        Calculate workout compliance rate over recent period.
        
        Returns percentage of planned workouts completed (0-100).
        """
        cutoff = date.today() - timedelta(days=days)
        recent = [c for c in self._completions if c.planned_date >= cutoff]
        
        if not recent:
            return 100.0  # No data = assume compliant
        
        completed = sum(1 for c in recent if c.was_completed)
        return (completed / len(recent)) * 100
    
    def get_load_compliance(self, days: int = 14) -> float:
        """
        Calculate average load compliance over recent period.
        
        Returns average of (actual_load / planned_load) * 100.
        """
        cutoff = date.today() - timedelta(days=days)
        recent = [
            c for c in self._completions 
            if c.planned_date >= cutoff and c.compliance_pct is not None
        ]
        
        if not recent:
            return 100.0
        
        return statistics.mean(c.compliance_pct for c in recent)
    
    def analyze_trends(
        self,
        metric: str = "load",
        days: int = 28,
    ) -> PerformanceTrend:
        """
        Analyze performance trends for a given metric.
        
        Args:
            metric: "load", "duration", "compliance", "rpe"
            days: Number of days to analyze
        """
        cutoff = date.today() - timedelta(days=days)
        recent = [
            c for c in self._completions 
            if c.planned_date >= cutoff and c.was_completed
        ]
        
        # Sort by date
        recent.sort(key=lambda c: c.completed_date or c.planned_date)
        
        values: List[float] = []
        dates: List[date] = []
        
        for c in recent:
            if metric == "load" and c.actual_load is not None:
                values.append(c.actual_load)
                dates.append(c.completed_date or c.planned_date)
            elif metric == "duration" and c.actual_duration_min is not None:
                values.append(float(c.actual_duration_min))
                dates.append(c.completed_date or c.planned_date)
            elif metric == "compliance" and c.compliance_pct is not None:
                values.append(c.compliance_pct)
                dates.append(c.completed_date or c.planned_date)
            elif metric == "rpe" and c.rpe is not None:
                values.append(float(c.rpe))
                dates.append(c.completed_date or c.planned_date)
        
        return PerformanceTrend(
            metric_name=metric,
            period_days=days,
            values=values,
            dates=dates,
        )
    
    def predict_workout_outcome(
        self,
        workout_id: str,
        planned_date: date,
        planned_type: str,
        planned_load: float,
        current_ctl: float,
        current_atl: float,
        current_tsb: float,
    ) -> WorkoutPrediction:
        """
        Predict the outcome of a planned workout.
        
        Uses current fitness state and historical compliance to predict
        whether the workout will be completed successfully.
        """
        # Calculate fatigue level (0-1, based on TSB)
        # Negative TSB = more fatigued
        fatigue_level = max(0.0, min(1.0, 0.5 - (current_tsb / 20)))
        
        # Get recent compliance
        compliance_rate = self.get_compliance_rate(14) / 100
        
        # Calculate days since last rest day
        days_since_rest = self._calculate_days_since_rest()
        
        # Predict completion probability
        # Factors: fatigue, compliance history, days since rest
        base_probability = 0.85
        fatigue_penalty = fatigue_level * 0.2
        compliance_bonus = (compliance_rate - 0.7) * 0.3 if compliance_rate > 0.7 else 0
        rest_penalty = min(0.15, (days_since_rest - 3) * 0.03) if days_since_rest > 3 else 0
        
        completion_prob = max(0.3, min(0.98, 
            base_probability - fatigue_penalty + compliance_bonus - rest_penalty
        ))
        
        # Predict quality
        if fatigue_level < 0.3 and completion_prob > 0.85:
            quality = "excellent"
        elif fatigue_level < 0.5 and completion_prob > 0.7:
            quality = "good"
        elif completion_prob > 0.5:
            quality = "moderate"
        else:
            quality = "poor"
        
        # Assess risks
        # ACWR-based injury risk
        if current_atl > 0:
            acwr = current_atl / current_ctl if current_ctl > 0 else 1.0
        else:
            acwr = 1.0
        
        if acwr > 1.5:
            injury_risk = "high"
            overtraining_risk = "high"
        elif acwr > 1.3:
            injury_risk = "moderate"
            overtraining_risk = "moderate"
        else:
            injury_risk = "low"
            overtraining_risk = "low"
        
        return WorkoutPrediction(
            workout_id=workout_id,
            planned_date=planned_date,
            planned_type=planned_type,
            predicted_load=planned_load * completion_prob,
            predicted_completion_probability=completion_prob,
            predicted_quality=quality,
            current_fatigue_level=fatigue_level,
            recent_compliance_rate=compliance_rate,
            days_since_rest=days_since_rest,
            injury_risk=injury_risk,
            overtraining_risk=overtraining_risk,
        )
    
    def generate_adaptations(
        self,
        current_ctl: float,
        current_atl: float,
        current_tsb: float,
        upcoming_race_date: Optional[date] = None,
    ) -> List[AdaptationRecommendation]:
        """
        Generate adaptation recommendations based on current state.
        
        Returns list of recommendations for adjusting upcoming workouts.
        """
        recommendations: List[AdaptationRecommendation] = []
        
        # Calculate key metrics
        tsb = current_tsb
        acwr = current_atl / current_ctl if current_ctl > 0 else 1.0
        compliance = self.get_compliance_rate(14)
        load_compliance = self.get_load_compliance(14)
        
        # Check for overreaching (high ACWR)
        if acwr > 1.5:
            recommendations.append(AdaptationRecommendation(
                trigger=AdaptationTrigger.OVERREACHING,
                adaptation_type=AdaptationType.REDUCE_VOLUME,
                target_workout_id=None,
                target_date=date.today() + timedelta(days=1),
                volume_multiplier=0.7,
                intensity_multiplier=0.9,
                reason=f"ACWR is {acwr:.2f} (>1.5 danger zone). Reduce training load to prevent injury.",
                confidence=0.9,
            ))
        elif acwr > 1.3:
            recommendations.append(AdaptationRecommendation(
                trigger=AdaptationTrigger.OVERREACHING,
                adaptation_type=AdaptationType.REDUCE_INTENSITY,
                target_workout_id=None,
                target_date=date.today() + timedelta(days=1),
                volume_multiplier=0.9,
                intensity_multiplier=0.85,
                reason=f"ACWR is {acwr:.2f} (elevated). Consider easier workouts.",
                confidence=0.75,
            ))
        
        # Check for recovery needed (very negative TSB)
        if tsb < -20:
            recommendations.append(AdaptationRecommendation(
                trigger=AdaptationTrigger.RECOVERY_NEEDED,
                adaptation_type=AdaptationType.ADD_RECOVERY,
                target_workout_id=None,
                target_date=date.today() + timedelta(days=1),
                volume_multiplier=0.5,
                intensity_multiplier=0.6,
                reason=f"TSB is {tsb:.1f} (very fatigued). Add recovery day.",
                confidence=0.85,
            ))
        elif tsb < -10:
            recommendations.append(AdaptationRecommendation(
                trigger=AdaptationTrigger.RECOVERY_NEEDED,
                adaptation_type=AdaptationType.REDUCE_INTENSITY,
                target_workout_id=None,
                target_date=date.today() + timedelta(days=1),
                volume_multiplier=0.85,
                intensity_multiplier=0.8,
                reason=f"TSB is {tsb:.1f} (fatigued). Reduce intensity.",
                confidence=0.7,
            ))
        
        # Check for undertraining (low compliance)
        if compliance < 70:
            recommendations.append(AdaptationRecommendation(
                trigger=AdaptationTrigger.UNDERTRAINING,
                adaptation_type=AdaptationType.REDUCE_VOLUME,
                target_workout_id=None,
                target_date=None,
                volume_multiplier=0.8,
                intensity_multiplier=1.0,
                reason=f"Compliance is {compliance:.0f}%. Reduce workout duration to improve adherence.",
                confidence=0.65,
            ))
        
        # Check for race taper
        if upcoming_race_date:
            days_to_race = (upcoming_race_date - date.today()).days
            if 1 <= days_to_race <= 7:
                recommendations.append(AdaptationRecommendation(
                    trigger=AdaptationTrigger.RACE_TAPER,
                    adaptation_type=AdaptationType.REDUCE_VOLUME,
                    target_workout_id=None,
                    target_date=date.today(),
                    volume_multiplier=0.4,
                    intensity_multiplier=0.7,
                    reason=f"Race in {days_to_race} days. Final taper phase.",
                    confidence=0.95,
                ))
            elif 8 <= days_to_race <= 14:
                recommendations.append(AdaptationRecommendation(
                    trigger=AdaptationTrigger.RACE_TAPER,
                    adaptation_type=AdaptationType.REDUCE_VOLUME,
                    target_workout_id=None,
                    target_date=date.today(),
                    volume_multiplier=0.7,
                    intensity_multiplier=0.9,
                    reason=f"Race in {days_to_race} days. Begin taper.",
                    confidence=0.9,
                ))
        
        # Check for performance trends
        load_trend = self.analyze_trends("load", 28)
        if load_trend.trend_direction == "declining" and load_trend.change_pct and load_trend.change_pct < -20:
            recommendations.append(AdaptationRecommendation(
                trigger=AdaptationTrigger.PERFORMANCE_DECLINE,
                adaptation_type=AdaptationType.MAINTAIN,
                target_workout_id=None,
                target_date=None,
                reason=f"Training load declining ({load_trend.change_pct:.0f}%). Consider if intentional recovery or loss of motivation.",
                confidence=0.6,
            ))
        
        self._recommendations.extend(recommendations)
        return recommendations
    
    def apply_adaptation(
        self,
        recommendation: AdaptationRecommendation,
        workout_load: float,
        workout_duration_min: int,
    ) -> Tuple[float, int]:
        """
        Apply an adaptation recommendation to a workout.
        
        Returns adjusted (load, duration_min).
        """
        adjusted_load = workout_load * recommendation.volume_multiplier * recommendation.intensity_multiplier
        adjusted_duration = int(workout_duration_min * recommendation.volume_multiplier)
        
        recommendation.applied = True
        recommendation.applied_at = datetime.now()
        
        return adjusted_load, adjusted_duration
    
    def _calculate_days_since_rest(self) -> int:
        """Calculate days since last rest/easy day."""
        if not self._completions:
            return 0
        
        # Sort by date descending
        recent = sorted(
            [c for c in self._completions if c.was_completed],
            key=lambda c: c.completed_date or c.planned_date,
            reverse=True
        )
        
        days = 0
        for c in recent:
            # Consider "rest" if load < 30 or RPE <= 3
            if (c.actual_load and c.actual_load < 30) or (c.rpe and c.rpe <= 3):
                break
            days += 1
            if days >= 14:  # Cap at 2 weeks
                break
        
        return days
    
    def get_adaptation_summary(self) -> Dict[str, Any]:
        """Get a summary of adaptation state."""
        return {
            "total_completions": len(self._completions),
            "compliance_rate_14d": self.get_compliance_rate(14),
            "load_compliance_14d": self.get_load_compliance(14),
            "days_since_rest": self._calculate_days_since_rest(),
            "pending_recommendations": len([r for r in self._recommendations if not r.applied]),
            "applied_recommendations": len([r for r in self._recommendations if r.applied]),
            "trends": {
                "load": self.analyze_trends("load", 28).to_dict(),
                "rpe": self.analyze_trends("rpe", 14).to_dict(),
            },
        }


# Singleton instance
_adaptation_engine: Optional[WorkoutAdaptationEngine] = None


def get_adaptation_engine() -> WorkoutAdaptationEngine:
    """Get the workout adaptation engine singleton."""
    global _adaptation_engine
    if _adaptation_engine is None:
        _adaptation_engine = WorkoutAdaptationEngine()
    return _adaptation_engine

