"""Running economy data models for tracking efficiency and cardiac drift."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class PaceZone(str, Enum):
    """Pace zones for economy tracking."""
    EASY = "easy"
    LONG = "long"
    TEMPO = "tempo"
    THRESHOLD = "threshold"
    INTERVAL = "interval"


class CardiacDriftSeverity(str, Enum):
    """Severity levels for cardiac drift."""
    NONE = "none"           # <2% drift
    MINIMAL = "minimal"     # 2-5% drift
    CONCERNING = "concerning"  # 5-8% drift
    SIGNIFICANT = "significant"  # >8% drift


# ============================================================================
# Pydantic Models (for API request/response)
# ============================================================================

class EconomyMetrics(BaseModel):
    """Running economy metrics for a single workout."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # Core economy calculation
    economy_ratio: float = Field(
        ...,
        description="Pace (sec/km) divided by avg HR. Lower = better economy."
    )
    pace_sec_per_km: int = Field(..., description="Average pace in seconds per km")
    avg_hr: int = Field(..., description="Average heart rate in bpm")

    # Context
    workout_id: str = Field(..., description="ID of the workout")
    workout_date: str = Field(..., description="Date of the workout")
    workout_type: str = Field(default="running", description="Type of activity")
    distance_km: float = Field(default=0.0, description="Distance in kilometers")
    duration_min: float = Field(default=0.0, description="Duration in minutes")

    # Comparison to personal best
    best_economy: Optional[float] = Field(None, description="Personal best economy ratio")
    comparison_to_best: Optional[float] = Field(
        None,
        description="Percentage difference from best economy (negative = better)"
    )

    # Pace zone context
    pace_zone: Optional[PaceZone] = Field(None, description="Pace zone for this workout")

    # Formatted display values
    pace_formatted: str = Field(default="", description="Pace in mm:ss format")
    economy_label: str = Field(default="", description="Human-readable economy label")


class CardiacDriftAnalysis(BaseModel):
    """Cardiac drift analysis for a workout."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    workout_id: str = Field(..., description="ID of the workout")
    workout_date: str = Field(..., description="Date of the workout")

    # First and second half HR
    first_half_hr: float = Field(..., description="Average HR during first half")
    second_half_hr: float = Field(..., description="Average HR during second half")

    # Drift calculation
    drift_bpm: float = Field(..., description="HR drift in bpm")
    drift_percent: float = Field(..., description="HR drift as percentage")

    # Assessment
    severity: CardiacDriftSeverity = Field(..., description="Severity of drift")
    is_concerning: bool = Field(
        default=False,
        description="True if drift >5% (indicates aerobic base deficiency)"
    )

    # Context
    first_half_pace: Optional[int] = Field(None, description="First half pace sec/km")
    second_half_pace: Optional[int] = Field(None, description="Second half pace sec/km")
    pace_change_percent: Optional[float] = Field(
        None,
        description="Pace change percentage (for drift context)"
    )

    # Recommendation
    recommendation: str = Field(
        default="",
        description="Recommendation based on drift analysis"
    )


class EconomyDataPoint(BaseModel):
    """A single data point for economy trend."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    date: str
    economy_ratio: float
    pace_sec_per_km: int
    avg_hr: int
    workout_id: str
    pace_zone: Optional[PaceZone] = None


class EconomyTrend(BaseModel):
    """Economy trend over time."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # Time range
    start_date: str = Field(..., description="Start date of trend period")
    end_date: str = Field(..., description="End date of trend period")
    days: int = Field(..., description="Number of days in period")

    # Data points
    data_points: List[EconomyDataPoint] = Field(
        default_factory=list,
        description="Economy data points over time"
    )
    workout_count: int = Field(default=0, description="Number of running workouts")

    # Trend analysis
    improvement_percent: float = Field(
        default=0.0,
        description="Percentage improvement (negative = better economy)"
    )
    trend_direction: str = Field(
        default="stable",
        description="Trend direction: improving, stable, declining"
    )

    # Best values
    best_economy: float = Field(default=0.0, description="Best economy ratio in period")
    best_economy_date: Optional[str] = Field(None, description="Date of best economy")
    best_economy_workout_id: Optional[str] = Field(None, description="Workout with best economy")

    # Current values
    current_economy: float = Field(default=0.0, description="Most recent economy ratio")
    current_vs_best: Optional[float] = Field(
        None,
        description="Current vs best percentage difference"
    )

    # Average values
    avg_economy: float = Field(default=0.0, description="Average economy ratio in period")
    avg_pace_sec_per_km: int = Field(default=0, description="Average pace in period")
    avg_hr: int = Field(default=0, description="Average HR in period")


class ZoneEconomy(BaseModel):
    """Economy metrics for a specific pace zone."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    pace_zone: PaceZone
    zone_name: str = Field(..., description="Human-readable zone name")

    # Economy stats
    avg_economy: float = Field(..., description="Average economy in this zone")
    best_economy: float = Field(..., description="Best economy in this zone")
    worst_economy: float = Field(..., description="Worst economy in this zone")

    # Sample size
    workout_count: int = Field(default=0, description="Number of workouts in this zone")

    # Pace and HR ranges
    avg_pace_sec_per_km: int = Field(default=0, description="Average pace in zone")
    avg_hr: int = Field(default=0, description="Average HR in zone")
    pace_range: str = Field(default="", description="Pace range in zone")
    hr_range: str = Field(default="", description="HR range in zone")

    # Recent trend
    recent_improvement: Optional[float] = Field(
        None,
        description="Improvement over last 4 weeks"
    )


class PaceZonesEconomy(BaseModel):
    """Economy breakdown by pace zone."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    zones: List[ZoneEconomy] = Field(
        default_factory=list,
        description="Economy metrics by zone"
    )

    # Overall stats
    total_workouts: int = Field(default=0, description="Total running workouts")
    best_zone: Optional[PaceZone] = Field(None, description="Zone with best economy")
    most_improved_zone: Optional[PaceZone] = Field(
        None,
        description="Zone with most improvement"
    )


class CardiacDriftTrend(BaseModel):
    """Cardiac drift trends over time."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    start_date: str
    end_date: str

    # Drift data points
    data_points: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Drift data points over time"
    )

    # Trend analysis
    avg_drift_percent: float = Field(default=0.0, description="Average drift percentage")
    concerning_count: int = Field(default=0, description="Number of concerning drifts (>5%)")
    improvement_trend: str = Field(
        default="stable",
        description="Trend in drift: improving, stable, worsening"
    )

    # Recommendations
    aerobic_base_assessment: str = Field(
        default="",
        description="Assessment of aerobic base based on drift patterns"
    )


# ============================================================================
# API Response Models
# ============================================================================

class EconomyCurrentResponse(BaseModel):
    """Response for current economy metrics endpoint."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    metrics: Optional[EconomyMetrics] = Field(
        None,
        description="Most recent economy metrics"
    )
    has_data: bool = Field(default=False, description="Whether economy data exists")
    message: Optional[str] = Field(None, description="Status message")


class EconomyTrendResponse(BaseModel):
    """Response for economy trend endpoint."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    trend: EconomyTrend
    success: bool = Field(default=True)
    message: Optional[str] = None


class CardiacDriftResponse(BaseModel):
    """Response for cardiac drift endpoint."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    analysis: Optional[CardiacDriftAnalysis] = None
    success: bool = Field(default=True)
    message: Optional[str] = None


class PaceZonesEconomyResponse(BaseModel):
    """Response for pace zones economy endpoint."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    zones_economy: PaceZonesEconomy
    success: bool = Field(default=True)
    message: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================

def calculate_economy_ratio(pace_sec_per_km: int, avg_hr: int) -> float:
    """
    Calculate running economy ratio.

    Economy = Pace / HR
    Lower values indicate better economy (less cardiac cost for same pace).

    Args:
        pace_sec_per_km: Pace in seconds per kilometer
        avg_hr: Average heart rate in bpm

    Returns:
        Economy ratio (typically 1.5-3.0 for most runners)
    """
    if avg_hr <= 0:
        return 0.0
    return round(pace_sec_per_km / avg_hr, 3)


def calculate_cardiac_drift(
    first_half_hr: float,
    second_half_hr: float
) -> tuple[float, float, CardiacDriftSeverity]:
    """
    Calculate cardiac drift between workout halves.

    Cardiac drift is the increase in HR during the second half of a workout
    at the same pace. It indicates aerobic endurance capacity.

    Args:
        first_half_hr: Average HR during first half
        second_half_hr: Average HR during second half

    Returns:
        Tuple of (drift_bpm, drift_percent, severity)
    """
    if first_half_hr <= 0:
        return 0.0, 0.0, CardiacDriftSeverity.NONE

    drift_bpm = second_half_hr - first_half_hr
    drift_percent = (drift_bpm / first_half_hr) * 100

    # Determine severity
    if drift_percent < 2:
        severity = CardiacDriftSeverity.NONE
    elif drift_percent < 5:
        severity = CardiacDriftSeverity.MINIMAL
    elif drift_percent < 8:
        severity = CardiacDriftSeverity.CONCERNING
    else:
        severity = CardiacDriftSeverity.SIGNIFICANT

    return round(drift_bpm, 1), round(drift_percent, 1), severity


def format_pace(pace_sec_per_km: int) -> str:
    """Format pace as mm:ss/km."""
    minutes = pace_sec_per_km // 60
    seconds = pace_sec_per_km % 60
    return f"{minutes}:{seconds:02d}/km"


def get_economy_label(economy_ratio: float, best_economy: Optional[float] = None) -> str:
    """
    Get a human-readable label for economy ratio.

    Labels are relative to the athlete's best or absolute ranges.
    """
    if best_economy and best_economy > 0:
        pct_diff = ((economy_ratio - best_economy) / best_economy) * 100
        if pct_diff <= 0:
            return "Personal Best"
        elif pct_diff < 3:
            return "Near Best"
        elif pct_diff < 8:
            return "Good"
        elif pct_diff < 15:
            return "Average"
        else:
            return "Below Average"

    # Absolute labels (lower is better)
    if economy_ratio < 1.8:
        return "Excellent"
    elif economy_ratio < 2.1:
        return "Very Good"
    elif economy_ratio < 2.4:
        return "Good"
    elif economy_ratio < 2.7:
        return "Average"
    else:
        return "Below Average"


def get_drift_recommendation(
    drift_percent: float,
    severity: CardiacDriftSeverity
) -> str:
    """Get a recommendation based on cardiac drift analysis."""
    if severity == CardiacDriftSeverity.NONE:
        return "Excellent aerobic control. Your cardiovascular system maintained efficiency throughout the workout."
    elif severity == CardiacDriftSeverity.MINIMAL:
        return "Good aerobic fitness. Minor drift is normal for longer efforts. Continue building your aerobic base."
    elif severity == CardiacDriftSeverity.CONCERNING:
        return f"Cardiac drift of {drift_percent:.1f}% indicates room for aerobic base improvement. Consider more Zone 2 training and ensuring adequate hydration."
    else:
        return f"Significant drift of {drift_percent:.1f}% suggests aerobic base deficiency. Prioritize easy runs in Zone 2, proper pacing, hydration, and fueling. Consider shorter duration or lower intensity."


def classify_pace_zone(
    pace_sec_per_km: int,
    easy_pace: int = 360,
    tempo_pace: int = 300,
    threshold_pace: int = 285
) -> PaceZone:
    """
    Classify a pace into a training zone.

    Uses default paces or athlete-specific paces if provided.
    """
    if pace_sec_per_km >= easy_pace:
        return PaceZone.EASY
    elif pace_sec_per_km >= tempo_pace:
        return PaceZone.LONG
    elif pace_sec_per_km >= threshold_pace:
        return PaceZone.TEMPO
    elif pace_sec_per_km >= threshold_pace - 30:
        return PaceZone.THRESHOLD
    else:
        return PaceZone.INTERVAL
