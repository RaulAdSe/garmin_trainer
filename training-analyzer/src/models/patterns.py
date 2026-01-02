"""Pattern recognition models for AI-driven training insights.

Provides data models for:
- Workout timing correlation analysis
- Optimal TSB range detection
- Peak fitness prediction
- Performance correlations
"""

from datetime import date, datetime, time
from enum import Enum
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class DayOfWeek(str, Enum):
    """Days of the week."""
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class TimeOfDay(str, Enum):
    """Time of day buckets for training analysis."""
    EARLY_MORNING = "early_morning"  # 5-7am
    MORNING = "morning"  # 7-10am
    LATE_MORNING = "late_morning"  # 10am-12pm
    AFTERNOON = "afternoon"  # 12-3pm
    LATE_AFTERNOON = "late_afternoon"  # 3-6pm
    EVENING = "evening"  # 6-9pm
    NIGHT = "night"  # 9pm-5am


class PerformanceMetric(str, Enum):
    """Performance metrics for correlation analysis."""
    PACE = "pace"
    HEART_RATE_EFFICIENCY = "heart_rate_efficiency"
    POWER = "power"
    TRAINING_EFFECT = "training_effect"
    EXECUTION_RATING = "execution_rating"


# ==============================================================================
# Timing Analysis Models
# ==============================================================================

class TimeSlotPerformance(BaseModel):
    """Performance metrics for a specific time slot."""
    time_slot: TimeOfDay
    workout_count: int = 0
    avg_performance_score: float = 0.0  # Normalized 0-100
    avg_hr_efficiency: float = 0.0  # Lower is better (HR / pace ratio)
    avg_execution_rating: Optional[float] = None
    sample_workouts: List[str] = Field(default_factory=list)  # Recent workout IDs

    @property
    def is_significant(self) -> bool:
        """Check if sample size is statistically significant."""
        return self.workout_count >= 5


class DayPerformance(BaseModel):
    """Performance metrics for a specific day of week."""
    day: DayOfWeek
    workout_count: int = 0
    avg_performance_score: float = 0.0
    avg_training_load: float = 0.0
    preferred_workout_types: List[str] = Field(default_factory=list)
    sample_workouts: List[str] = Field(default_factory=list)


class OptimalWindow(BaseModel):
    """An identified optimal training window."""
    time_slot: TimeOfDay
    day: Optional[DayOfWeek] = None
    performance_boost: float = 0.0  # Percentage improvement vs average
    confidence: float = 0.0  # 0-1 confidence score
    sample_size: int = 0


class TimingAnalysis(BaseModel):
    """Complete timing pattern analysis for an athlete."""
    user_id: str
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    analysis_period_days: int = 90

    # Performance by time of day
    time_slot_performance: List[TimeSlotPerformance] = Field(default_factory=list)

    # Performance by day of week
    day_performance: List[DayPerformance] = Field(default_factory=list)

    # Identified optimal windows
    optimal_windows: List[OptimalWindow] = Field(default_factory=list)

    # Best single time slot
    best_time_slot: Optional[TimeOfDay] = None
    best_time_slot_boost: float = 0.0

    # Best day of week
    best_day: Optional[DayOfWeek] = None
    best_day_boost: float = 0.0

    # Worst performers (for recommendations)
    avoid_time_slot: Optional[TimeOfDay] = None
    avoid_day: Optional[DayOfWeek] = None

    # Summary stats
    total_workouts_analyzed: int = 0
    data_quality_score: float = 0.0  # 0-1, based on sample sizes and coverage


# ==============================================================================
# TSB Optimal Range Models
# ==============================================================================

class TSBPerformancePoint(BaseModel):
    """A single data point correlating TSB with performance."""
    workout_id: str
    workout_date: date
    tsb: float
    ctl: float
    atl: float
    performance_score: float  # Normalized 0-100
    workout_type: str
    distance_km: Optional[float] = None
    duration_min: Optional[float] = None


class TSBZone(str, Enum):
    """TSB zones for categorization."""
    DEEP_FATIGUE = "deep_fatigue"  # TSB < -25
    FATIGUED = "fatigued"  # -25 <= TSB < -10
    FUNCTIONAL = "functional"  # -10 <= TSB < 0
    FRESH = "fresh"  # 0 <= TSB < 15
    PEAKED = "peaked"  # 15 <= TSB < 30
    DETRAINED = "detrained"  # TSB >= 30


class TSBZoneStats(BaseModel):
    """Statistics for a specific TSB zone."""
    zone: TSBZone
    tsb_range: Tuple[float, float]
    workout_count: int = 0
    avg_performance: float = 0.0
    std_performance: float = 0.0
    best_performance: float = 0.0
    worst_performance: float = 0.0


class TSBOptimalRange(BaseModel):
    """Optimal TSB range analysis for an athlete."""
    user_id: str
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    analysis_period_days: int = 180

    # Core optimal range
    optimal_tsb_min: float = -5.0
    optimal_tsb_max: float = 15.0
    optimal_zone: TSBZone = TSBZone.FRESH

    # Performance by zone
    zone_stats: List[TSBZoneStats] = Field(default_factory=list)

    # Individual data points (for scatter plot)
    data_points: List[TSBPerformancePoint] = Field(default_factory=list)

    # Correlation metrics
    tsb_performance_correlation: float = 0.0  # Pearson correlation coefficient
    correlation_confidence: float = 0.0  # Statistical significance

    # Race timing recommendations
    recommended_taper_days: int = 10
    peak_tsb_target: float = 10.0
    current_tsb: Optional[float] = None
    days_to_peak: Optional[int] = None

    # Summary stats
    total_workouts_analyzed: int = 0
    data_quality_score: float = 0.0


# ==============================================================================
# Peak Fitness Prediction Models
# ==============================================================================

class CTLProjection(BaseModel):
    """A single CTL projection point."""
    date: date
    projected_ctl: float
    confidence_lower: float  # Lower bound of confidence interval
    confidence_upper: float  # Upper bound of confidence interval
    is_historical: bool = False  # True if this is actual data, not projection


class PlannedEvent(BaseModel):
    """A planned race or event."""
    event_id: Optional[str] = None
    name: str
    event_date: date
    event_type: str = "race"  # race, goal_workout, milestone
    priority: str = "A"  # A, B, C priority


class FitnessPrediction(BaseModel):
    """Peak fitness prediction for an athlete."""
    user_id: str
    predicted_at: datetime = Field(default_factory=datetime.utcnow)
    prediction_horizon_days: int = 90

    # Current state
    current_ctl: float = 0.0
    current_atl: float = 0.0
    current_tsb: float = 0.0
    current_weekly_load: float = 0.0

    # Peak prediction (without target date)
    natural_peak_date: Optional[date] = None
    natural_peak_ctl: Optional[float] = None
    days_to_natural_peak: Optional[int] = None

    # Target event analysis
    target_event: Optional[PlannedEvent] = None
    target_date: Optional[date] = None
    projected_ctl_at_target: Optional[float] = None
    projected_tsb_at_target: Optional[float] = None

    # CTL trajectory (for chart)
    ctl_projection: List[CTLProjection] = Field(default_factory=list)

    # Recommendations
    weekly_load_recommendation: float = 0.0
    load_change_percentage: float = 0.0  # +/- percentage change needed
    taper_start_date: Optional[date] = None

    # Confidence
    prediction_confidence: float = 0.0  # 0-1

    # Planned events
    planned_events: List[PlannedEvent] = Field(default_factory=list)


# ==============================================================================
# Correlation Analysis Models
# ==============================================================================

class CorrelationFactor(BaseModel):
    """A factor that correlates with performance."""
    factor_name: str
    correlation_coefficient: float  # -1 to 1
    p_value: float  # Statistical significance
    sample_size: int
    is_significant: bool = False  # p < 0.05

    @property
    def correlation_strength(self) -> str:
        """Interpret correlation strength."""
        r = abs(self.correlation_coefficient)
        if r >= 0.7:
            return "strong"
        elif r >= 0.4:
            return "moderate"
        elif r >= 0.2:
            return "weak"
        return "negligible"

    @property
    def correlation_direction(self) -> str:
        """Interpret correlation direction."""
        if self.correlation_coefficient > 0:
            return "positive"
        elif self.correlation_coefficient < 0:
            return "negative"
        return "none"


class PerformanceCorrelations(BaseModel):
    """Complete correlation analysis for performance factors."""
    user_id: str
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    analysis_period_days: int = 180

    # Key correlations
    correlations: List[CorrelationFactor] = Field(default_factory=list)

    # Top positive and negative factors
    top_positive_factors: List[str] = Field(default_factory=list)
    top_negative_factors: List[str] = Field(default_factory=list)

    # Insights
    key_insights: List[str] = Field(default_factory=list)

    # Data quality
    total_workouts_analyzed: int = 0
    data_quality_score: float = 0.0


class CorrelationAnalysis(BaseModel):
    """Combined correlation analysis response."""
    timing_correlations: Optional[TimingAnalysis] = None
    tsb_correlations: Optional[TSBOptimalRange] = None
    performance_correlations: Optional[PerformanceCorrelations] = None


# ==============================================================================
# Helper Functions
# ==============================================================================

def get_time_of_day(hour: int) -> TimeOfDay:
    """Convert hour (0-23) to TimeOfDay enum."""
    if 5 <= hour < 7:
        return TimeOfDay.EARLY_MORNING
    elif 7 <= hour < 10:
        return TimeOfDay.MORNING
    elif 10 <= hour < 12:
        return TimeOfDay.LATE_MORNING
    elif 12 <= hour < 15:
        return TimeOfDay.AFTERNOON
    elif 15 <= hour < 18:
        return TimeOfDay.LATE_AFTERNOON
    elif 18 <= hour < 21:
        return TimeOfDay.EVENING
    else:
        return TimeOfDay.NIGHT


def get_day_of_week(d: date) -> DayOfWeek:
    """Convert date to DayOfWeek enum."""
    days = [
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY,
        DayOfWeek.SATURDAY,
        DayOfWeek.SUNDAY,
    ]
    return days[d.weekday()]


def get_tsb_zone(tsb: float) -> TSBZone:
    """Categorize TSB value into a zone."""
    if tsb < -25:
        return TSBZone.DEEP_FATIGUE
    elif tsb < -10:
        return TSBZone.FATIGUED
    elif tsb < 0:
        return TSBZone.FUNCTIONAL
    elif tsb < 15:
        return TSBZone.FRESH
    elif tsb < 30:
        return TSBZone.PEAKED
    else:
        return TSBZone.DETRAINED


def get_tsb_zone_range(zone: TSBZone) -> Tuple[float, float]:
    """Get the TSB range for a zone."""
    ranges = {
        TSBZone.DEEP_FATIGUE: (-100.0, -25.0),
        TSBZone.FATIGUED: (-25.0, -10.0),
        TSBZone.FUNCTIONAL: (-10.0, 0.0),
        TSBZone.FRESH: (0.0, 15.0),
        TSBZone.PEAKED: (15.0, 30.0),
        TSBZone.DETRAINED: (30.0, 100.0),
    }
    return ranges.get(zone, (-100.0, 100.0))
