"""
Data models for plan deviation detection and adaptation suggestions.

This module defines the structures for:
- Detecting deviations between planned and actual workouts
- Suggesting adaptive changes to training plans
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DeviationType(str, Enum):
    """Classification of workout deviation from plan."""
    AS_PLANNED = "as_planned"  # Workout matched plan within tolerance
    EASIER = "easier"          # Workout was easier than planned
    HARDER = "harder"          # Workout was harder than planned
    SKIPPED = "skipped"        # Planned workout was not completed
    EXTRA = "extra"            # Extra workout not in plan


class AdaptationAction(str, Enum):
    """Types of adaptation actions."""
    REDUCE_INTENSITY = "reduce_intensity"
    INCREASE_INTENSITY = "increase_intensity"
    ADD_RECOVERY = "add_recovery"
    REDISTRIBUTE_LOAD = "redistribute_load"
    EXTEND_PLAN = "extend_plan"
    MAINTAIN = "maintain"
    REDUCE_VOLUME = "reduce_volume"
    INCREASE_VOLUME = "increase_volume"


@dataclass
class DeviationMetrics:
    """Detailed metrics comparing planned vs actual workout."""
    planned_duration_min: float
    actual_duration_min: float
    planned_load: float
    actual_load: float
    planned_intensity: Optional[str] = None  # e.g., "Zone 2", "Tempo"
    actual_avg_hr: Optional[int] = None
    actual_max_hr: Optional[int] = None
    planned_distance_km: Optional[float] = None
    actual_distance_km: Optional[float] = None

    @property
    def duration_deviation_pct(self) -> float:
        """Calculate duration deviation as percentage."""
        if self.planned_duration_min == 0:
            return 0.0
        return ((self.actual_duration_min - self.planned_duration_min)
                / self.planned_duration_min * 100)

    @property
    def load_deviation_pct(self) -> float:
        """Calculate load deviation as percentage."""
        if self.planned_load == 0:
            return 0.0
        return ((self.actual_load - self.planned_load)
                / self.planned_load * 100)

    @property
    def distance_deviation_pct(self) -> Optional[float]:
        """Calculate distance deviation as percentage if available."""
        if self.planned_distance_km and self.actual_distance_km:
            if self.planned_distance_km == 0:
                return 0.0
            return ((self.actual_distance_km - self.planned_distance_km)
                    / self.planned_distance_km * 100)
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "planned_duration_min": self.planned_duration_min,
            "actual_duration_min": self.actual_duration_min,
            "duration_deviation_pct": round(self.duration_deviation_pct, 1),
            "planned_load": self.planned_load,
            "actual_load": self.actual_load,
            "load_deviation_pct": round(self.load_deviation_pct, 1),
            "planned_intensity": self.planned_intensity,
            "actual_avg_hr": self.actual_avg_hr,
            "actual_max_hr": self.actual_max_hr,
            "planned_distance_km": self.planned_distance_km,
            "actual_distance_km": self.actual_distance_km,
            "distance_deviation_pct": (
                round(self.distance_deviation_pct, 1)
                if self.distance_deviation_pct is not None else None
            ),
        }


@dataclass
class PlanDeviation:
    """
    Represents a deviation between a planned session and actual workout.

    Contains:
    - The deviation type classification
    - Quantitative metrics showing the difference
    - Context about when and what was planned
    """
    plan_id: str
    week_number: int
    day_of_week: int
    planned_date: date
    deviation_type: DeviationType
    metrics: Optional[DeviationMetrics] = None
    planned_workout_type: Optional[str] = None
    actual_workout_id: Optional[str] = None
    actual_workout_type: Optional[str] = None
    severity: str = "minor"  # "minor", "moderate", "significant"
    detected_at: datetime = field(default_factory=datetime.now)

    @property
    def is_significant(self) -> bool:
        """Check if deviation is significant enough to warrant adaptation."""
        if self.deviation_type == DeviationType.SKIPPED:
            return True
        if self.deviation_type == DeviationType.AS_PLANNED:
            return False
        if self.metrics:
            # Consider significant if load deviation > 30%
            return abs(self.metrics.load_deviation_pct) > 30
        return self.severity in ("moderate", "significant")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plan_id": self.plan_id,
            "week_number": self.week_number,
            "day_of_week": self.day_of_week,
            "planned_date": self.planned_date.isoformat(),
            "deviation_type": self.deviation_type.value,
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "planned_workout_type": self.planned_workout_type,
            "actual_workout_id": self.actual_workout_id,
            "actual_workout_type": self.actual_workout_type,
            "severity": self.severity,
            "is_significant": self.is_significant,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class SessionAdjustment:
    """Suggested adjustment for a specific session."""
    day_of_week: int
    original_type: str
    suggested_type: str
    original_duration_min: int
    suggested_duration_min: int
    original_load: float
    suggested_load: float
    rationale: str

    @property
    def load_change_pct(self) -> float:
        """Calculate the percentage change in load."""
        if self.original_load == 0:
            return 0.0
        return ((self.suggested_load - self.original_load)
                / self.original_load * 100)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "day_of_week": self.day_of_week,
            "original_type": self.original_type,
            "suggested_type": self.suggested_type,
            "original_duration_min": self.original_duration_min,
            "suggested_duration_min": self.suggested_duration_min,
            "original_load": self.original_load,
            "suggested_load": self.suggested_load,
            "load_change_pct": round(self.load_change_pct, 1),
            "rationale": self.rationale,
        }


@dataclass
class AdaptationSuggestion:
    """
    A suggested adaptation to the training plan based on detected deviations.

    Contains:
    - The actions to take
    - Specific session adjustments
    - Natural language explanation
    - Expected impact on training
    """
    plan_id: str
    deviation: PlanDeviation
    actions: List[AdaptationAction]
    affected_weeks: List[int]
    session_adjustments: List[SessionAdjustment]
    explanation: str  # LLM-generated natural language explanation
    expected_load_change_pct: float
    confidence: float = 0.8  # 0.0 to 1.0
    created_at: datetime = field(default_factory=datetime.now)
    applied: bool = False
    applied_at: Optional[datetime] = None

    @property
    def summary(self) -> str:
        """Generate a short summary of the adaptation."""
        action_names = [a.value.replace("_", " ").title() for a in self.actions]
        return f"{', '.join(action_names)} for weeks {self.affected_weeks}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plan_id": self.plan_id,
            "deviation": self.deviation.to_dict(),
            "actions": [a.value for a in self.actions],
            "affected_weeks": self.affected_weeks,
            "session_adjustments": [adj.to_dict() for adj in self.session_adjustments],
            "explanation": self.explanation,
            "summary": self.summary,
            "expected_load_change_pct": round(self.expected_load_change_pct, 1),
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "applied": self.applied,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
        }


# ============================================================================
# Pydantic Models for API Request/Response
# ============================================================================

class CheckDeviationRequest(BaseModel):
    """Request to check for deviation in recent workouts."""
    workout_id: Optional[str] = Field(
        None,
        description="Specific workout ID to check. If not provided, checks most recent."
    )
    days_back: int = Field(
        7,
        ge=1,
        le=30,
        description="Number of days to look back for workouts"
    )


class DeviationResponse(BaseModel):
    """Response containing deviation detection results."""
    plan_id: str
    deviations: List[Dict[str, Any]]
    has_significant_deviation: bool
    total_deviations: int
    summary: str


class AutoAdaptRequest(BaseModel):
    """Request to auto-adapt the plan based on recent performance."""
    apply_immediately: bool = Field(
        False,
        description="If true, apply adaptations immediately. Otherwise, return suggestions."
    )
    weeks_to_adapt: Optional[List[int]] = Field(
        None,
        description="Specific weeks to adapt. If not provided, adapts next 2-4 weeks."
    )
    include_explanation: bool = Field(
        True,
        description="Include LLM-generated explanation for adaptations"
    )


class AdaptationResponse(BaseModel):
    """Response containing adaptation suggestions or confirmation."""
    plan_id: str
    success: bool
    suggestions: List[Dict[str, Any]]
    applied: bool
    explanation: Optional[str] = None
    affected_weeks: List[int]
    expected_load_change_pct: float
    message: str
