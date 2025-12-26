"""
Fatigue Prediction Service for burnout prevention and recovery optimization.

Uses training load, HRV data, RPE, and recovery metrics to predict
fatigue levels and recommend appropriate training adjustments.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import statistics


class FatigueLevel(str, Enum):
    """Fatigue levels for athlete state."""
    FRESH = "fresh"          # Ready for hard training
    RECOVERED = "recovered"  # Good to go
    MODERATE = "moderate"    # Some fatigue, can train
    FATIGUED = "fatigued"    # Need easier training
    EXHAUSTED = "exhausted"  # Need rest


class RecoveryState(str, Enum):
    """Recovery state assessment."""
    EXCELLENT = "excellent"
    GOOD = "good"
    MODERATE = "moderate"
    POOR = "poor"
    CRITICAL = "critical"


class RiskLevel(str, Enum):
    """Risk level for overtraining/injury."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DailyReadiness:
    """
    Daily readiness assessment combining multiple factors.
    """
    date: date
    
    # Training load metrics
    ctl: float  # Chronic Training Load (fitness)
    atl: float  # Acute Training Load (fatigue)
    tsb: float  # Training Stress Balance (form)
    acwr: float  # Acute:Chronic Workload Ratio
    
    # Recovery metrics (optional - from wearables)
    hrv_rmssd: Optional[float] = None  # HRV in ms
    resting_hr: Optional[int] = None   # Morning resting HR
    sleep_hours: Optional[float] = None
    sleep_quality: Optional[float] = None  # 0-100
    
    # Subjective metrics
    perceived_fatigue: Optional[int] = None  # 1-10
    perceived_soreness: Optional[int] = None  # 1-10
    perceived_stress: Optional[int] = None   # 1-10
    mood: Optional[int] = None  # 1-10 (10 = great)
    
    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "ctl": self.ctl,
            "atl": self.atl,
            "tsb": self.tsb,
            "acwr": self.acwr,
            "hrv_rmssd": self.hrv_rmssd,
            "resting_hr": self.resting_hr,
            "sleep_hours": self.sleep_hours,
            "sleep_quality": self.sleep_quality,
            "perceived_fatigue": self.perceived_fatigue,
            "perceived_soreness": self.perceived_soreness,
            "perceived_stress": self.perceived_stress,
            "mood": self.mood,
        }


@dataclass
class FatiguePrediction:
    """
    Fatigue prediction with confidence and contributing factors.
    """
    date: date
    fatigue_level: FatigueLevel
    fatigue_score: float  # 0-100 (100 = completely exhausted)
    recovery_state: RecoveryState
    
    # Risk assessments
    overtraining_risk: RiskLevel
    injury_risk: RiskLevel
    burnout_risk: RiskLevel
    
    # Recommendations
    recommended_intensity: str  # "rest", "easy", "moderate", "hard"
    recovery_hours_needed: float
    
    # Contributing factors (weights that led to this prediction)
    contributing_factors: Dict[str, float] = field(default_factory=dict)
    
    # Confidence in prediction
    confidence: float = 0.7
    
    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "fatigue_level": self.fatigue_level.value,
            "fatigue_score": self.fatigue_score,
            "recovery_state": self.recovery_state.value,
            "overtraining_risk": self.overtraining_risk.value,
            "injury_risk": self.injury_risk.value,
            "burnout_risk": self.burnout_risk.value,
            "recommended_intensity": self.recommended_intensity,
            "recovery_hours_needed": self.recovery_hours_needed,
            "contributing_factors": self.contributing_factors,
            "confidence": self.confidence,
        }


@dataclass
class ACWRAlert:
    """
    Alert for dangerous ACWR levels.
    """
    date: date
    acwr: float
    risk_level: RiskLevel
    message: str
    recommended_action: str
    
    @classmethod
    def evaluate(cls, acwr: float, current_date: date = None) -> Optional["ACWRAlert"]:
        """
        Evaluate ACWR and return alert if needed.
        
        ACWR zones:
        - <0.8: Undertraining (fitness loss risk)
        - 0.8-1.3: Sweet spot (optimal training)
        - 1.3-1.5: Caution zone (elevated injury risk)
        - >1.5: Danger zone (high injury risk)
        """
        if current_date is None:
            current_date = date.today()
        
        if acwr < 0.8:
            return cls(
                date=current_date,
                acwr=acwr,
                risk_level=RiskLevel.MODERATE,
                message=f"ACWR is {acwr:.2f} - you may be undertraining",
                recommended_action="Consider gradually increasing training load to maintain fitness",
            )
        elif 0.8 <= acwr <= 1.3:
            return None  # No alert needed - sweet spot
        elif 1.3 < acwr <= 1.5:
            return cls(
                date=current_date,
                acwr=acwr,
                risk_level=RiskLevel.MODERATE,
                message=f"ACWR is {acwr:.2f} - elevated injury risk",
                recommended_action="Reduce training intensity or add recovery days",
            )
        else:  # > 1.5
            return cls(
                date=current_date,
                acwr=acwr,
                risk_level=RiskLevel.HIGH,
                message=f"ACWR is {acwr:.2f} - danger zone! High injury risk",
                recommended_action="URGENT: Reduce training load immediately. Add rest days.",
            )
    
    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "acwr": self.acwr,
            "risk_level": self.risk_level.value,
            "message": self.message,
            "recommended_action": self.recommended_action,
        }


@dataclass
class RecoveryEstimate:
    """
    Estimated recovery time and recommendations.
    """
    hours_until_recovered: float
    hours_until_fresh: float
    
    optimal_next_hard_workout: date
    optimal_next_easy_workout: date
    
    recovery_activities: List[str]  # Recommended recovery activities
    sleep_recommendation: float  # Hours of sleep recommended
    
    def to_dict(self) -> dict:
        return {
            "hours_until_recovered": self.hours_until_recovered,
            "hours_until_fresh": self.hours_until_fresh,
            "optimal_next_hard_workout": self.optimal_next_hard_workout.isoformat(),
            "optimal_next_easy_workout": self.optimal_next_easy_workout.isoformat(),
            "recovery_activities": self.recovery_activities,
            "sleep_recommendation": self.sleep_recommendation,
        }


class FatiguePredictionService:
    """
    Service for predicting fatigue and managing recovery.
    
    Uses a weighted scoring model based on:
    - Training load metrics (CTL, ATL, TSB, ACWR)
    - Recovery data (HRV, sleep, resting HR)
    - Subjective feedback (RPE, mood, soreness)
    """
    
    # Weights for fatigue calculation
    WEIGHTS = {
        "tsb": 0.25,           # Training Stress Balance
        "acwr": 0.20,          # Acute:Chronic Workload Ratio
        "hrv": 0.15,           # Heart Rate Variability
        "sleep": 0.10,         # Sleep quality/quantity
        "resting_hr": 0.10,    # Resting heart rate deviation
        "perceived": 0.20,     # Subjective feelings
    }
    
    def __init__(self):
        """Initialize the fatigue prediction service."""
        self._readiness_history: List[DailyReadiness] = []
        self._hrv_baseline: Optional[float] = None
        self._rhr_baseline: Optional[int] = None
    
    def set_baselines(
        self,
        hrv_baseline: Optional[float] = None,
        rhr_baseline: Optional[int] = None,
    ) -> None:
        """Set baseline values for HRV and resting HR."""
        self._hrv_baseline = hrv_baseline
        self._rhr_baseline = rhr_baseline
    
    def record_readiness(self, readiness: DailyReadiness) -> None:
        """Record daily readiness data."""
        self._readiness_history.append(readiness)
        
        # Update baselines if enough data
        self._update_baselines()
    
    def _update_baselines(self) -> None:
        """Update baselines from recent data."""
        recent = self._readiness_history[-30:]  # Last 30 days
        
        # HRV baseline (use top 25th percentile as "recovered" baseline)
        hrv_values = [r.hrv_rmssd for r in recent if r.hrv_rmssd is not None]
        if len(hrv_values) >= 7:
            sorted_hrv = sorted(hrv_values, reverse=True)
            top_quartile = sorted_hrv[:len(sorted_hrv) // 4] or sorted_hrv[:1]
            self._hrv_baseline = statistics.mean(top_quartile)
        
        # RHR baseline (use bottom 25th percentile)
        rhr_values = [r.resting_hr for r in recent if r.resting_hr is not None]
        if len(rhr_values) >= 7:
            sorted_rhr = sorted(rhr_values)
            bottom_quartile = sorted_rhr[:len(sorted_rhr) // 4] or sorted_rhr[:1]
            self._rhr_baseline = int(statistics.mean(bottom_quartile))
    
    def predict_fatigue(
        self,
        readiness: DailyReadiness,
    ) -> FatiguePrediction:
        """
        Predict fatigue level based on readiness data.
        
        Uses weighted scoring model to combine multiple factors.
        """
        factors: Dict[str, float] = {}
        
        # === TSB-based fatigue (0-100) ===
        # TSB < -20: very fatigued (score 80-100)
        # TSB -20 to 0: moderately fatigued (score 40-80)
        # TSB 0 to 20: recovered (score 10-40)
        # TSB > 20: fresh but maybe undertrained (score 0-10)
        if readiness.tsb < -30:
            tsb_score = 100
        elif readiness.tsb < -20:
            tsb_score = 80 + ((readiness.tsb + 20) / -10) * 20
        elif readiness.tsb < 0:
            tsb_score = 40 + ((readiness.tsb) / -20) * 40
        elif readiness.tsb < 20:
            tsb_score = 10 + ((20 - readiness.tsb) / 20) * 30
        else:
            tsb_score = max(0, 10 - (readiness.tsb - 20) / 2)
        factors["tsb"] = tsb_score
        
        # === ACWR-based fatigue ===
        # Sweet spot (0.8-1.3): low fatigue contribution
        # High ACWR (>1.3): high fatigue contribution
        if readiness.acwr < 0.8:
            acwr_score = 30  # Some concern for undertraining
        elif readiness.acwr <= 1.3:
            acwr_score = 20  # Sweet spot
        elif readiness.acwr <= 1.5:
            acwr_score = 60  # Caution
        else:
            acwr_score = 90  # Danger
        factors["acwr"] = acwr_score
        
        # === HRV-based fatigue ===
        if readiness.hrv_rmssd is not None and self._hrv_baseline:
            hrv_ratio = readiness.hrv_rmssd / self._hrv_baseline
            if hrv_ratio >= 1.0:
                hrv_score = 10  # At or above baseline = recovered
            elif hrv_ratio >= 0.85:
                hrv_score = 30
            elif hrv_ratio >= 0.70:
                hrv_score = 60
            else:
                hrv_score = 90  # Significantly suppressed
            factors["hrv"] = hrv_score
        else:
            factors["hrv"] = 40  # Default if no data
        
        # === Sleep-based fatigue ===
        if readiness.sleep_hours is not None:
            if readiness.sleep_hours >= 8:
                sleep_score = 10
            elif readiness.sleep_hours >= 7:
                sleep_score = 25
            elif readiness.sleep_hours >= 6:
                sleep_score = 50
            else:
                sleep_score = 80
            
            # Adjust by quality if available
            if readiness.sleep_quality is not None:
                quality_factor = (100 - readiness.sleep_quality) / 100
                sleep_score = sleep_score * 0.7 + sleep_score * quality_factor * 0.3
            
            factors["sleep"] = sleep_score
        else:
            factors["sleep"] = 35  # Default if no data
        
        # === Resting HR-based fatigue ===
        if readiness.resting_hr is not None and self._rhr_baseline:
            rhr_elevation = readiness.resting_hr - self._rhr_baseline
            if rhr_elevation <= 0:
                rhr_score = 10  # At or below baseline
            elif rhr_elevation <= 3:
                rhr_score = 25
            elif rhr_elevation <= 6:
                rhr_score = 50
            elif rhr_elevation <= 10:
                rhr_score = 75
            else:
                rhr_score = 95  # Significantly elevated
            factors["resting_hr"] = rhr_score
        else:
            factors["resting_hr"] = 35  # Default
        
        # === Perceived fatigue ===
        perceived_scores = []
        if readiness.perceived_fatigue is not None:
            perceived_scores.append(readiness.perceived_fatigue * 10)
        if readiness.perceived_soreness is not None:
            perceived_scores.append(readiness.perceived_soreness * 10)
        if readiness.perceived_stress is not None:
            perceived_scores.append(readiness.perceived_stress * 10)
        if readiness.mood is not None:
            perceived_scores.append((10 - readiness.mood) * 10)  # Invert mood
        
        if perceived_scores:
            factors["perceived"] = statistics.mean(perceived_scores)
        else:
            factors["perceived"] = 40  # Default
        
        # === Calculate weighted fatigue score ===
        fatigue_score = sum(
            factors.get(k, 40) * self.WEIGHTS.get(k, 0)
            for k in self.WEIGHTS.keys()
        )
        
        # Normalize to 0-100
        fatigue_score = max(0, min(100, fatigue_score))
        
        # Determine fatigue level
        if fatigue_score < 20:
            fatigue_level = FatigueLevel.FRESH
            recovery_state = RecoveryState.EXCELLENT
            recommended_intensity = "hard"
        elif fatigue_score < 40:
            fatigue_level = FatigueLevel.RECOVERED
            recovery_state = RecoveryState.GOOD
            recommended_intensity = "moderate"
        elif fatigue_score < 60:
            fatigue_level = FatigueLevel.MODERATE
            recovery_state = RecoveryState.MODERATE
            recommended_intensity = "easy"
        elif fatigue_score < 80:
            fatigue_level = FatigueLevel.FATIGUED
            recovery_state = RecoveryState.POOR
            recommended_intensity = "easy"
        else:
            fatigue_level = FatigueLevel.EXHAUSTED
            recovery_state = RecoveryState.CRITICAL
            recommended_intensity = "rest"
        
        # Assess risks
        overtraining_risk = self._assess_overtraining_risk(readiness, fatigue_score)
        injury_risk = self._assess_injury_risk(readiness)
        burnout_risk = self._assess_burnout_risk(fatigue_score)
        
        # Estimate recovery time
        recovery_hours = self._estimate_recovery_hours(fatigue_score, readiness.tsb)
        
        # Calculate confidence based on data availability
        data_points = sum(1 for v in [
            readiness.hrv_rmssd,
            readiness.sleep_hours,
            readiness.resting_hr,
            readiness.perceived_fatigue,
        ] if v is not None)
        confidence = 0.5 + (data_points * 0.1)  # 0.5 to 0.9
        
        return FatiguePrediction(
            date=readiness.date,
            fatigue_level=fatigue_level,
            fatigue_score=round(fatigue_score, 1),
            recovery_state=recovery_state,
            overtraining_risk=overtraining_risk,
            injury_risk=injury_risk,
            burnout_risk=burnout_risk,
            recommended_intensity=recommended_intensity,
            recovery_hours_needed=recovery_hours,
            contributing_factors={k: round(v, 1) for k, v in factors.items()},
            confidence=round(confidence, 2),
        )
    
    def _assess_overtraining_risk(
        self,
        readiness: DailyReadiness,
        fatigue_score: float,
    ) -> RiskLevel:
        """Assess overtraining syndrome risk."""
        risk_score = 0
        
        # High fatigue score
        if fatigue_score >= 80:
            risk_score += 3
        elif fatigue_score >= 60:
            risk_score += 2
        
        # High ACWR
        if readiness.acwr > 1.5:
            risk_score += 3
        elif readiness.acwr > 1.3:
            risk_score += 2
        
        # Very negative TSB
        if readiness.tsb < -25:
            risk_score += 2
        elif readiness.tsb < -15:
            risk_score += 1
        
        # Prolonged high load (check history)
        high_load_days = sum(
            1 for r in self._readiness_history[-14:]
            if r.tsb < -10
        )
        if high_load_days >= 10:
            risk_score += 2
        
        if risk_score >= 6:
            return RiskLevel.CRITICAL
        elif risk_score >= 4:
            return RiskLevel.HIGH
        elif risk_score >= 2:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW
    
    def _assess_injury_risk(self, readiness: DailyReadiness) -> RiskLevel:
        """Assess injury risk based on ACWR."""
        if readiness.acwr > 1.5:
            return RiskLevel.HIGH
        elif readiness.acwr > 1.3:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW
    
    def _assess_burnout_risk(self, fatigue_score: float) -> RiskLevel:
        """Assess burnout risk based on sustained fatigue."""
        # Check if fatigue has been elevated for extended period
        high_fatigue_streak = 0
        for r in reversed(self._readiness_history[-14:]):
            if r.tsb < -10:
                high_fatigue_streak += 1
            else:
                break
        
        if fatigue_score >= 70 and high_fatigue_streak >= 7:
            return RiskLevel.HIGH
        elif fatigue_score >= 60 and high_fatigue_streak >= 5:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW
    
    def _estimate_recovery_hours(
        self,
        fatigue_score: float,
        tsb: float,
    ) -> float:
        """Estimate hours needed for recovery."""
        # Base recovery time based on fatigue score
        if fatigue_score < 30:
            base_hours = 12
        elif fatigue_score < 50:
            base_hours = 24
        elif fatigue_score < 70:
            base_hours = 36
        elif fatigue_score < 85:
            base_hours = 48
        else:
            base_hours = 72
        
        # Adjust for TSB
        if tsb < -20:
            base_hours *= 1.3
        elif tsb < -10:
            base_hours *= 1.1
        
        return round(base_hours, 1)
    
    def estimate_recovery(
        self,
        current_fatigue_score: float,
        current_tsb: float,
    ) -> RecoveryEstimate:
        """
        Estimate recovery timeline and provide recommendations.
        """
        # Calculate recovery times
        hours_until_recovered = self._estimate_recovery_hours(current_fatigue_score, current_tsb)
        hours_until_fresh = hours_until_recovered * 1.5
        
        # Calculate optimal workout dates
        today = date.today()
        easy_workout_date = today + timedelta(hours=hours_until_recovered / 2)
        hard_workout_date = today + timedelta(hours=hours_until_fresh)
        
        # Recovery activity recommendations based on fatigue level
        if current_fatigue_score >= 70:
            activities = [
                "Complete rest today",
                "Light stretching or yoga",
                "Meditation or breathing exercises",
                "Extra sleep (aim for 9+ hours)",
                "Hydration focus",
            ]
            sleep_rec = 9.0
        elif current_fatigue_score >= 50:
            activities = [
                "Active recovery: easy walk or swim",
                "Foam rolling and mobility work",
                "Adequate sleep (8+ hours)",
                "Nutrition focus - protein and carbs",
            ]
            sleep_rec = 8.5
        elif current_fatigue_score >= 30:
            activities = [
                "Light cross-training",
                "Stretching routine",
                "Normal sleep schedule",
            ]
            sleep_rec = 8.0
        else:
            activities = [
                "Normal training can resume",
                "Maintain good sleep habits",
            ]
            sleep_rec = 7.5
        
        return RecoveryEstimate(
            hours_until_recovered=hours_until_recovered,
            hours_until_fresh=hours_until_fresh,
            optimal_next_hard_workout=hard_workout_date,
            optimal_next_easy_workout=easy_workout_date,
            recovery_activities=activities,
            sleep_recommendation=sleep_rec,
        )
    
    def check_acwr_alert(
        self,
        ctl: float,
        atl: float,
    ) -> Optional[ACWRAlert]:
        """
        Check if ACWR warrants an alert.
        
        Returns alert if ACWR is outside optimal range.
        """
        if ctl <= 0:
            return None
        
        acwr = atl / ctl
        return ACWRAlert.evaluate(acwr)
    
    def get_fatigue_trend(self, days: int = 14) -> Dict[str, Any]:
        """Get fatigue trend over recent period."""
        recent = self._readiness_history[-days:]
        
        if len(recent) < 3:
            return {"status": "insufficient_data"}
        
        # Calculate average fatigue indicators
        tsb_values = [r.tsb for r in recent]
        acwr_values = [r.acwr for r in recent]
        
        avg_tsb = statistics.mean(tsb_values)
        avg_acwr = statistics.mean(acwr_values)
        
        # Determine trend
        first_half_tsb = statistics.mean(tsb_values[:len(tsb_values)//2])
        second_half_tsb = statistics.mean(tsb_values[len(tsb_values)//2:])
        
        if second_half_tsb > first_half_tsb + 5:
            trend = "recovering"
        elif second_half_tsb < first_half_tsb - 5:
            trend = "accumulating_fatigue"
        else:
            trend = "stable"
        
        return {
            "period_days": days,
            "data_points": len(recent),
            "avg_tsb": round(avg_tsb, 1),
            "avg_acwr": round(avg_acwr, 2),
            "trend": trend,
            "current_tsb": recent[-1].tsb if recent else None,
            "current_acwr": recent[-1].acwr if recent else None,
        }


# Singleton instance
_fatigue_service: Optional[FatiguePredictionService] = None


def get_fatigue_service() -> FatiguePredictionService:
    """Get the fatigue prediction service singleton."""
    global _fatigue_service
    if _fatigue_service is None:
        _fatigue_service = FatiguePredictionService()
    return _fatigue_service

