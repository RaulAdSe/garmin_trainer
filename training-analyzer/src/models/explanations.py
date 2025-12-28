"""
Explanation models for transparent recommendations.

These models provide the mathematical reasoning and data behind every recommendation,
differentiating from "black box" competitors by showing users exactly why
recommendations are made.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class ImpactType(str, Enum):
    """Impact direction of a factor on the recommendation."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class DataSourceType(str, Enum):
    """Source of the data used in explanations."""
    GARMIN_HRV = "garmin_hrv"
    GARMIN_SLEEP = "garmin_sleep"
    GARMIN_STRESS = "garmin_stress"
    GARMIN_BODY_BATTERY = "garmin_body_battery"
    CALCULATED_TSB = "calculated_tsb"
    CALCULATED_ACWR = "calculated_acwr"
    CALCULATED_CTL = "calculated_ctl"
    CALCULATED_ATL = "calculated_atl"
    ACTIVITY_HISTORY = "activity_history"
    USER_PROFILE = "user_profile"
    TRAINING_PLAN = "training_plan"


@dataclass
class DataSource:
    """Information about where data came from."""
    source_type: DataSourceType
    source_name: str  # Human-readable name
    last_updated: Optional[str] = None  # ISO date string
    confidence: float = 1.0  # 0-1, how reliable is this data


@dataclass
class ExplanationFactor:
    """
    A single contributing factor to a recommendation.

    This provides transparency into what data influenced a decision
    and how much weight it carried.
    """
    name: str  # e.g., "HRV Score", "Training Load"
    value: Any  # e.g., 85.2, "BALANCED", True
    display_value: str  # Human-readable value, e.g., "85.2 ms", "15% below baseline"
    impact: ImpactType  # positive, negative, or neutral
    weight: float  # 0-1, how much this factor contributed
    contribution_points: float  # Actual points contributed to score
    explanation: str  # Human-readable explanation
    threshold: Optional[str] = None  # e.g., "Target: > 75"
    baseline: Optional[Any] = None  # Reference value for comparison
    data_sources: List[DataSource] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "display_value": self.display_value,
            "impact": self.impact.value,
            "weight": round(self.weight, 3),
            "contribution_points": round(self.contribution_points, 1),
            "explanation": self.explanation,
            "threshold": self.threshold,
            "baseline": self.baseline,
            "data_sources": [
                {
                    "source_type": ds.source_type.value,
                    "source_name": ds.source_name,
                    "last_updated": ds.last_updated,
                    "confidence": ds.confidence,
                }
                for ds in self.data_sources
            ],
        }


@dataclass
class ExplainedRecommendation:
    """
    A recommendation with full transparency into reasoning.

    This is the core model for explainability - it combines the actual
    recommendation with all the factors, data, and reasoning that led to it.
    """
    recommendation: str  # The actual recommendation text
    confidence: float  # 0-1 confidence score
    confidence_explanation: str  # Why this confidence level
    factors: List[ExplanationFactor]  # All contributing factors
    data_points: Dict[str, Any]  # Raw data used in calculation
    calculation_summary: str  # Brief summary of the calculation
    alternatives_considered: List[str] = field(default_factory=list)
    key_driver: Optional[str] = None  # The most influential factor

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "recommendation": self.recommendation,
            "confidence": round(self.confidence, 2),
            "confidence_explanation": self.confidence_explanation,
            "factors": [f.to_dict() for f in self.factors],
            "data_points": self.data_points,
            "calculation_summary": self.calculation_summary,
            "alternatives_considered": self.alternatives_considered,
            "key_driver": self.key_driver,
        }

    def get_positive_factors(self) -> List[ExplanationFactor]:
        """Get all factors with positive impact."""
        return [f for f in self.factors if f.impact == ImpactType.POSITIVE]

    def get_negative_factors(self) -> List[ExplanationFactor]:
        """Get all factors with negative impact."""
        return [f for f in self.factors if f.impact == ImpactType.NEGATIVE]

    def get_limiting_factor(self) -> Optional[ExplanationFactor]:
        """Get the most impactful negative factor (if any)."""
        negative = self.get_negative_factors()
        if not negative:
            return None
        return max(negative, key=lambda f: abs(f.contribution_points))


@dataclass
class ExplainedReadiness:
    """
    Complete explained readiness assessment.

    Extends ReadinessResult with full factor breakdown and reasoning.
    """
    date: str  # ISO date string
    overall_score: float  # 0-100
    zone: str  # 'green', 'yellow', 'red'
    recommendation: ExplainedRecommendation
    factor_breakdown: List[ExplanationFactor]
    score_calculation: str  # Step-by-step calculation
    comparison_to_baseline: Optional[str] = None  # e.g., "5% above your 7-day average"
    trend: Optional[str] = None  # e.g., "improving", "declining", "stable"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "date": self.date,
            "overall_score": round(self.overall_score, 1),
            "zone": self.zone,
            "recommendation": self.recommendation.to_dict(),
            "factor_breakdown": [f.to_dict() for f in self.factor_breakdown],
            "score_calculation": self.score_calculation,
            "comparison_to_baseline": self.comparison_to_baseline,
            "trend": self.trend,
        }


@dataclass
class ExplainedWorkoutRecommendation:
    """
    Workout recommendation with full explanation of why this type/intensity.
    """
    workout_type: str  # e.g., "easy", "tempo", "intervals"
    duration_min: int
    intensity_description: str
    hr_zone_target: Optional[str]
    recommendation: ExplainedRecommendation
    decision_tree: List[str]  # The logic path that led to this decision
    readiness_influence: float  # How much readiness affected this (0-1)
    load_influence: float  # How much training load affected this (0-1)
    pattern_influence: float  # How much hard/easy pattern affected this (0-1)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "workout_type": self.workout_type,
            "duration_min": self.duration_min,
            "intensity_description": self.intensity_description,
            "hr_zone_target": self.hr_zone_target,
            "recommendation": self.recommendation.to_dict(),
            "decision_tree": self.decision_tree,
            "readiness_influence": round(self.readiness_influence, 2),
            "load_influence": round(self.load_influence, 2),
            "pattern_influence": round(self.pattern_influence, 2),
        }


@dataclass
class ExplainedSessionRationale:
    """
    Explanation for why a specific training plan session was scheduled.
    """
    session_id: str
    session_name: str
    session_type: str
    scheduled_date: str
    rationale: ExplainedRecommendation
    periodization_context: str  # e.g., "Week 3 of Build Phase"
    weekly_context: str  # e.g., "2nd hard session this week"
    progression_note: Optional[str] = None  # e.g., "10% increase from last week"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "session_type": self.session_type,
            "scheduled_date": self.scheduled_date,
            "rationale": self.rationale.to_dict(),
            "periodization_context": self.periodization_context,
            "weekly_context": self.weekly_context,
            "progression_note": self.progression_note,
        }
