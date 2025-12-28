"""Workout analysis data models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from ..analysis.condensation import CondensedWorkoutData


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class AnalysisStatus(str, Enum):
    """Status of a workout analysis."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkoutExecutionRating(str, Enum):
    """Rating of workout execution quality."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    NEEDS_IMPROVEMENT = "needs_improvement"


# ============================================================================
# Pydantic Models (for API request/response)
# ============================================================================

class AnalysisRequest(BaseModel):
    """Request for workout analysis."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "includeSimilar": True,
                "forceRefresh": False,
            }
        },
    )

    # workout_id is optional here since it's typically in the URL path
    workout_id: Optional[str] = Field(default=None, description="ID of the workout to analyze")
    include_similar: bool = Field(default=True, description="Include similar workout comparison")
    force_refresh: bool = Field(default=False, description="Force re-analysis even if cached")


class BatchAnalysisRequest(BaseModel):
    """Request for batch workout analysis."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "workoutIds": ["activity_123", "activity_456", "activity_789"],
                "forceRefresh": False,
            }
        },
    )

    workout_ids: List[str] = Field(..., description="List of workout IDs to analyze")
    force_refresh: bool = Field(default=False, description="Force re-analysis even if cached")


class WorkoutInsight(BaseModel):
    """A single insight about the workout."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    category: str = Field(..., description="Category of insight (pace, heart_rate, effort, recovery)")
    observation: str = Field(..., description="The observation")
    is_positive: bool = Field(..., description="Whether this is a positive observation")
    importance: str = Field(default="medium", description="Importance level: low, medium, high")


class ScoreColor(str, Enum):
    """Color indicators for score cards."""
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    BLUE = "blue"
    GRAY = "gray"


class ScoreCard(BaseModel):
    """A score card representing a specific metric with visualization data."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    name: str = Field(..., description="Name of the score (e.g., 'Pace Consistency', 'HR Control')")
    value: float = Field(..., description="Current score value")
    max_value: float = Field(default=100.0, description="Maximum possible value for the score")
    label: str = Field(..., description="Human-readable label (e.g., 'Good', 'Excellent', 'Needs Work')")
    color: ScoreColor = Field(default=ScoreColor.GRAY, description="Color indicator for the score")
    description: str = Field(default="", description="Brief explanation of what this score measures")
    unit: Optional[str] = Field(default=None, description="Unit for the value (e.g., '%', 'bpm', 'hours')")


class InsightCategory(str, Enum):
    """Category types for categorized insights."""
    PERFORMANCE = "performance"
    CAUTION = "caution"
    TREND = "trend"
    RECOMMENDATION = "recommendation"
    ACHIEVEMENT = "achievement"


class CategorizedInsight(BaseModel):
    """A categorized insight with icon and detailed explanation."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    category: InsightCategory = Field(..., description="Category of the insight")
    icon: str = Field(..., description="Emoji icon representing the insight type")
    text: str = Field(..., description="Short, concise insight text")
    detail: str = Field(default="", description="Longer explanation for hover/expansion")


class AnalysisContext(BaseModel):
    """Context used for the analysis."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    ctl: Optional[float] = Field(None, description="Chronic Training Load")
    atl: Optional[float] = Field(None, description="Acute Training Load")
    tsb: Optional[float] = Field(None, description="Training Stress Balance")
    acwr: Optional[float] = Field(None, description="Acute:Chronic Workload Ratio")
    readiness_score: Optional[float] = Field(None, description="Readiness score")
    readiness_zone: Optional[str] = Field(None, description="Readiness zone (green/yellow/red)")
    recent_load_7d: Optional[float] = Field(None, description="Last 7 days total load")
    similar_workouts_count: int = Field(default=0, description="Number of similar workouts used")


class WorkoutAnalysisResult(BaseModel):
    """Complete analysis result for a workout."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "workoutId": "activity_12345",
                "analysisId": "analysis_abc123",
                "status": "completed",
                "summary": "Strong tempo run with consistent pacing. Heart rate well-controlled in Zone 3.",
                "whatWentWell": [
                    "Consistent pace throughout - negative split of 10 sec/km",
                    "Heart rate stayed in target Zone 3 for 85% of the run",
                ],
                "improvements": [
                    "Slight cardiac drift in last 10 minutes",
                    "Cadence dropped in final kilometer",
                ],
                "recommendations": [
                    "Consider a longer warmup to reduce initial HR spike",
                    "Add 30-second pickups in the final km to practice finishing strong",
                ],
                "executionRating": "good",
                "trainingFit": "Excellent timing - you're fresh after two easy days",
                "overallScore": 78,
                "trainingEffectScore": 3.2,
                "loadScore": 85,
                "recoveryHours": 24,
                "modelUsed": "gpt-5-mini",
            }
        },
    )

    workout_id: str = Field(..., description="ID of the analyzed workout")
    analysis_id: str = Field(..., description="Unique ID for this analysis")
    status: AnalysisStatus = Field(..., description="Status of the analysis")

    # Analysis content
    summary: str = Field(default="", description="2-3 sentence summary of the workout")
    # Note: what_worked_well serializes to whatWentWell for frontend compatibility
    what_worked_well: List[str] = Field(
        default_factory=list,
        description="List of positive observations",
        serialization_alias="whatWentWell",
    )
    # Note: observations serializes to improvements for frontend compatibility
    observations: List[str] = Field(
        default_factory=list,
        description="Notable patterns or concerns",
        serialization_alias="improvements",
    )
    recommendations: List[str] = Field(default_factory=list, description="Actionable suggestions")

    # Structured insights (legacy)
    insights: List[WorkoutInsight] = Field(default_factory=list, description="Structured insights")

    # =========================================================================
    # NEW: Structured Scores
    # =========================================================================
    overall_score: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Overall workout quality score (0-100)"
    )
    training_effect_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=5.0,
        description="Training stimulus level (0.0-5.0, like Garmin Training Effect)"
    )
    load_score: Optional[int] = Field(
        default=None,
        description="Training load contribution (based on HRSS/TRIMP)"
    )
    recovery_hours: Optional[int] = Field(
        default=None,
        ge=0,
        description="Estimated recovery time needed in hours"
    )

    # Score cards for detailed metrics visualization
    scores: List[ScoreCard] = Field(
        default_factory=list,
        description="Detailed score cards for various workout metrics"
    )

    # Categorized insights with icons and details
    categorized_insights: List[CategorizedInsight] = Field(
        default_factory=list,
        description="Categorized insights with icons and detailed explanations"
    )

    # =========================================================================
    # Ratings (existing)
    # =========================================================================
    execution_rating: Optional[WorkoutExecutionRating] = Field(None, description="Overall execution rating")
    effort_alignment: Optional[str] = Field(None, description="How well effort matched target")

    # Training context fit
    training_fit: Optional[str] = Field(None, description="How this fits training plan/goals")

    # Metadata
    context: Optional[AnalysisContext] = Field(None, description="Context used for analysis")
    model_used: str = Field(default="gpt-5-mini", description="LLM model used")
    raw_response: Optional[str] = Field(None, description="Raw LLM response")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    cached_at: Optional[datetime] = Field(None, description="When this was cached")


class AnalysisResponse(BaseModel):
    """API response wrapper for analysis."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "success": True,
                "analysis": {
                    "workoutId": "activity_12345",
                    "summary": "Strong tempo run...",
                },
                "cached": False,
            }
        },
    )

    success: bool = Field(..., description="Whether the analysis succeeded")
    analysis: Optional[WorkoutAnalysisResult] = Field(None, description="The analysis result")
    error: Optional[str] = Field(None, description="Error message if failed")
    cached: bool = Field(default=False, description="Whether this was served from cache")


class BatchAnalysisResponse(BaseModel):
    """Response for batch analysis."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    analyses: List[AnalysisResponse] = Field(..., description="List of analysis results")
    total_count: int = Field(..., description="Total workouts requested")
    success_count: int = Field(..., description="Number of successful analyses")
    cached_count: int = Field(default=0, description="Number served from cache")
    failed_count: int = Field(default=0, description="Number of failures")


class RecentWorkoutWithAnalysis(BaseModel):
    """A workout with its analysis summary."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    workout_id: str
    date: str
    activity_type: str
    duration_min: float
    distance_km: Optional[float] = None
    avg_hr: Optional[int] = None
    hrss: Optional[float] = None
    ai_summary: Optional[str] = None
    execution_rating: Optional[WorkoutExecutionRating] = None
    has_full_analysis: bool = False


class RecentWorkoutsResponse(BaseModel):
    """Response for recent workouts with analysis."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    workouts: List[RecentWorkoutWithAnalysis]
    count: int


# ============================================================================
# Dataclasses (for internal use)
# ============================================================================

@dataclass
class AthleteContext:
    """
    Athlete context for analysis.

    This contains all the relevant information about the athlete
    that should be considered during workout analysis.
    """
    # Fitness metrics
    ctl: float = 0.0
    atl: float = 0.0
    tsb: float = 0.0
    acwr: float = 1.0
    risk_zone: str = "unknown"

    # Physiology
    max_hr: int = 185
    rest_hr: int = 55
    threshold_hr: int = 165
    vdot: Optional[float] = None

    # VO2max and fitness level
    vo2max_running: Optional[float] = None  # ml/kg/min
    vo2max_cycling: Optional[float] = None  # ml/kg/min
    training_status: Optional[str] = None  # productive, unproductive, maintaining, etc.

    # Garmin race predictions (in seconds)
    race_prediction_5k: Optional[int] = None
    race_prediction_10k: Optional[int] = None
    race_prediction_half: Optional[int] = None
    race_prediction_marathon: Optional[int] = None

    # Daily activity (past 7 days averages)
    avg_daily_steps: Optional[int] = None
    avg_active_minutes: Optional[int] = None

    # Previous day activity (the day BEFORE the workout)
    prev_day_steps: Optional[int] = None
    prev_day_active_minutes: Optional[int] = None
    prev_day_date: Optional[str] = None

    # HR Zones (as tuples of (min, max))
    hr_zones: Dict[int, tuple] = field(default_factory=dict)

    # Training paces (in seconds per km)
    training_paces: Dict[str, int] = field(default_factory=dict)

    # Goals
    race_goal: Optional[str] = None
    race_date: Optional[str] = None
    target_time: Optional[str] = None

    # Current readiness
    readiness_score: float = 50.0
    readiness_zone: str = "yellow"

    # Recent activity
    recent_load_7d: float = 0.0
    days_since_hard: int = 0

    def __post_init__(self):
        """Initialize default HR zones if not provided."""
        if not self.hr_zones:
            hr_reserve = self.max_hr - self.rest_hr
            self.hr_zones = {
                1: (int(self.rest_hr + hr_reserve * 0.50), int(self.rest_hr + hr_reserve * 0.60)),
                2: (int(self.rest_hr + hr_reserve * 0.60), int(self.rest_hr + hr_reserve * 0.70)),
                3: (int(self.rest_hr + hr_reserve * 0.70), int(self.rest_hr + hr_reserve * 0.80)),
                4: (int(self.rest_hr + hr_reserve * 0.80), int(self.rest_hr + hr_reserve * 0.90)),
                5: (int(self.rest_hr + hr_reserve * 0.90), self.max_hr),
            }

    def format_hr_zones(self) -> str:
        """Format HR zones for prompt injection."""
        zone_strs = []
        for zone, (min_hr, max_hr) in sorted(self.hr_zones.items()):
            zone_strs.append(f"Z{zone}: {min_hr}-{max_hr} bpm")
        return ", ".join(zone_strs)

    def format_training_paces(self) -> str:
        """Format training paces for prompt injection."""
        pace_strs = []
        for name, pace_sec in self.training_paces.items():
            pace_min = pace_sec // 60
            pace_s = pace_sec % 60
            pace_strs.append(f"{name}: {pace_min}:{pace_s:02d}/km")
        return ", ".join(pace_strs)

    def format_race_prediction(self, seconds: int) -> str:
        """Format race prediction time from seconds to human-readable."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def to_prompt_context(self) -> str:
        """Convert to formatted string for LLM prompt injection."""
        lines = [
            f"CTL: {self.ctl:.1f} | ATL: {self.atl:.1f} | TSB: {self.tsb:.1f}",
            f"ACWR: {self.acwr:.2f} | Risk Zone: {self.risk_zone}",
            f"Readiness: {self.readiness_score:.0f}/100 ({self.readiness_zone})",
        ]

        # VO2max and training status
        if self.vo2max_running or self.vo2max_cycling or self.training_status:
            lines.append("")
            lines.append("FITNESS LEVEL:")
            if self.vo2max_running:
                lines.append(f"  VO2max (Running): {self.vo2max_running:.1f} ml/kg/min")
            if self.vo2max_cycling:
                lines.append(f"  VO2max (Cycling): {self.vo2max_cycling:.1f} ml/kg/min")
            if self.training_status:
                lines.append(f"  Training Status: {self.training_status}")

        # Race predictions
        has_predictions = any([
            self.race_prediction_5k,
            self.race_prediction_10k,
            self.race_prediction_half,
            self.race_prediction_marathon
        ])
        if has_predictions:
            lines.append("")
            lines.append("RACE PREDICTIONS (Garmin):")
            predictions = []
            if self.race_prediction_5k:
                predictions.append(f"5K: {self.format_race_prediction(self.race_prediction_5k)}")
            if self.race_prediction_10k:
                predictions.append(f"10K: {self.format_race_prediction(self.race_prediction_10k)}")
            if self.race_prediction_half:
                predictions.append(f"HM: {self.format_race_prediction(self.race_prediction_half)}")
            if self.race_prediction_marathon:
                predictions.append(f"Marathon: {self.format_race_prediction(self.race_prediction_marathon)}")
            lines.append(f"  {' | '.join(predictions)}")

        # Daily activity
        if self.prev_day_steps is not None or self.avg_daily_steps or self.avg_active_minutes:
            lines.append("")
            lines.append("DAILY ACTIVITY:")

            # Previous day activity with classification
            if self.prev_day_steps is not None:
                # Classify activity level
                if self.prev_day_steps < 5000:
                    activity_level = "LOW - rest day"
                elif self.prev_day_steps <= 12000:
                    activity_level = "NORMAL"
                else:
                    activity_level = "HIGH - very active"

                prev_day_label = f"({self.prev_day_date})" if self.prev_day_date else ""
                active_min_str = f", {self.prev_day_active_minutes} active min" if self.prev_day_active_minutes else ""
                lines.append(f"  Previous day {prev_day_label}: {self.prev_day_steps:,} steps{active_min_str} ({activity_level})")

            # 7-day average
            if self.avg_daily_steps or self.avg_active_minutes:
                avg_parts = []
                if self.avg_daily_steps:
                    avg_parts.append(f"{self.avg_daily_steps:,} steps/day")
                if self.avg_active_minutes:
                    avg_parts.append(f"{self.avg_active_minutes} active min/day")
                lines.append(f"  7-day average: {', '.join(avg_parts)}")

        if self.vdot:
            lines.append(f"VDOT: {self.vdot:.1f}")

        if self.race_goal:
            goal_line = f"Target Race: {self.race_goal}"
            if self.target_time:
                goal_line += f" in {self.target_time}"
            if self.race_date:
                goal_line += f" on {self.race_date}"
            lines.append(goal_line)

        if self.training_paces:
            lines.append(f"Training Paces: {self.format_training_paces()}")

        lines.append(f"HR Zones: {self.format_hr_zones()}")

        return "\n".join(lines)


@dataclass
class WorkoutData:
    """
    Workout data for analysis.

    Contains all the relevant workout metrics.
    """
    activity_id: str
    date: str
    activity_type: str = "running"
    activity_name: str = ""

    # Duration and distance
    duration_min: float = 0.0
    distance_km: float = 0.0

    # Heart rate
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None

    # Pace
    pace_sec_per_km: Optional[int] = None

    # Training load
    hrss: Optional[float] = None
    trimp: Optional[float] = None

    # Zone distribution (percentages)
    zone1_pct: float = 0.0
    zone2_pct: float = 0.0
    zone3_pct: float = 0.0
    zone4_pct: float = 0.0
    zone5_pct: float = 0.0

    # Additional metrics
    cadence: Optional[int] = None
    elevation_gain: Optional[float] = None
    calories: Optional[int] = None

    # ==========================================================================
    # Phase 2: Multi-sport Extensions
    # ==========================================================================

    # Sport classification (more specific than activity_type)
    sport_type: Optional[str] = None  # running, cycling, swimming, strength, etc.

    # Power metrics (cycling/running with power meter)
    avg_power: Optional[int] = None
    max_power: Optional[int] = None
    normalized_power: Optional[int] = None
    power_tss: Optional[float] = None  # Training Stress Score (power-based)
    tss: Optional[float] = None  # Alias for power_tss (backward compatibility)
    intensity_factor: Optional[float] = None
    variability_index: Optional[float] = None

    # Cycling-specific cadence (RPM)
    cycling_cadence: Optional[int] = None

    # Speed metrics
    avg_speed_kmh: Optional[float] = None

    # Elevation
    elevation_gain_m: Optional[float] = None

    # Swimming metrics
    pool_length_m: Optional[int] = None
    total_strokes: Optional[int] = None
    avg_swolf: Optional[float] = None
    avg_stroke_rate: Optional[float] = None
    css_pace_sec: Optional[int] = None  # Critical Swim Speed pace

    # Condensed time-series data (populated when detailed data is available)
    condensed_data: Optional[Any] = None  # CondensedWorkoutData

    def format_pace(self) -> str:
        """Format pace as min:sec/km."""
        if not self.pace_sec_per_km:
            return "N/A"
        pace_min = int(self.pace_sec_per_km // 60)
        pace_sec = int(self.pace_sec_per_km % 60)
        return f"{pace_min}:{pace_sec:02d}/km"

    def format_zone_distribution(self) -> str:
        """Format zone distribution for display."""
        zones = [
            ("Z1", self.zone1_pct),
            ("Z2", self.zone2_pct),
            ("Z3", self.zone3_pct),
            ("Z4", self.zone4_pct),
            ("Z5", self.zone5_pct),
        ]
        return ", ".join(f"{name}: {pct:.0f}%" for name, pct in zones if pct > 0)

    def format_speed(self) -> str:
        """Format speed as km/h."""
        if not self.avg_speed_kmh:
            return "N/A"
        return f"{self.avg_speed_kmh:.1f} km/h"

    def format_swim_pace(self) -> str:
        """Format CSS pace as min:sec/100m."""
        if not self.css_pace_sec:
            return "N/A"
        pace_min = int(self.css_pace_sec // 60)
        pace_sec = int(self.css_pace_sec % 60)
        return f"{pace_min}:{pace_sec:02d}/100m"

    def to_prompt_data(self) -> str:
        """Convert to formatted string for LLM prompt."""
        sport = self.sport_type or self.activity_type
        lines = [
            f"Activity: {self.activity_type}",
            f"Sport Type: {sport}" if self.sport_type and self.sport_type != self.activity_type else None,
            f"Date: {self.date}",
            f"Name: {self.activity_name}" if self.activity_name else None,
            f"Duration: {self.duration_min:.0f} minutes",
            f"Distance: {self.distance_km:.2f} km",
        ]

        if self.pace_sec_per_km:
            lines.append(f"Avg Pace: {self.format_pace()}")
        if self.avg_speed_kmh:
            lines.append(f"Avg Speed: {self.format_speed()}")

        if self.avg_hr:
            lines.append(f"Avg HR: {self.avg_hr} bpm")
        if self.max_hr:
            lines.append(f"Max HR: {self.max_hr} bpm")

        if any([self.zone1_pct, self.zone2_pct, self.zone3_pct, self.zone4_pct, self.zone5_pct]):
            lines.append(f"HR Zones: {self.format_zone_distribution()}")

        if self.hrss:
            lines.append(f"Training Load (HRSS): {self.hrss:.1f}")
        if self.trimp:
            lines.append(f"TRIMP: {self.trimp:.1f}")

        # Power metrics (cycling/running power)
        if self.avg_power:
            lines.append(f"Avg Power: {self.avg_power} W")
        if self.max_power:
            lines.append(f"Max Power: {self.max_power} W")
        if self.normalized_power:
            lines.append(f"Normalized Power: {self.normalized_power} W")
        if self.tss:
            lines.append(f"TSS: {self.tss:.1f}")
        if self.intensity_factor:
            lines.append(f"Intensity Factor: {self.intensity_factor:.2f}")
        if self.variability_index:
            lines.append(f"Variability Index: {self.variability_index:.2f}")

        if self.cadence:
            lines.append(f"Avg Cadence: {self.cadence} spm")
        if self.cycling_cadence:
            lines.append(f"Avg Cycling Cadence: {self.cycling_cadence} rpm")
        if self.elevation_gain:
            lines.append(f"Elevation Gain: {self.elevation_gain:.0f} m")
        if self.elevation_gain_m:
            lines.append(f"Elevation Gain: {self.elevation_gain_m:.0f} m")

        # Swimming metrics
        if self.pool_length_m:
            lines.append(f"Pool Length: {self.pool_length_m} m")
        if self.total_strokes:
            lines.append(f"Total Strokes: {self.total_strokes}")
        if self.avg_swolf:
            lines.append(f"Avg SWOLF: {self.avg_swolf:.1f}")
        if self.avg_stroke_rate:
            lines.append(f"Avg Stroke Rate: {self.avg_stroke_rate:.1f} spm")
        if self.css_pace_sec:
            lines.append(f"CSS Pace: {self.format_swim_pace()}")

        # Add condensed time-series analysis if available
        if self.condensed_data:
            lines.append("")
            lines.append("--- DETAILED DYNAMICS ---")
            condensed_text = self.condensed_data.to_prompt_data()
            if condensed_text:
                lines.append(condensed_text)

        return "\n".join(line for line in lines if line is not None)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkoutData":
        """Create WorkoutData from dictionary."""
        return cls(
            activity_id=data.get("activity_id", "unknown"),
            date=data.get("date", "unknown"),
            activity_type=data.get("activity_type", "running"),
            activity_name=data.get("activity_name", ""),
            duration_min=data.get("duration_min", 0.0) or 0.0,
            distance_km=data.get("distance_km", 0.0) or 0.0,
            avg_hr=data.get("avg_hr"),
            max_hr=data.get("max_hr"),
            pace_sec_per_km=data.get("pace_sec_per_km"),
            hrss=data.get("hrss"),
            trimp=data.get("trimp"),
            zone1_pct=data.get("zone1_pct", 0.0) or 0.0,
            zone2_pct=data.get("zone2_pct", 0.0) or 0.0,
            zone3_pct=data.get("zone3_pct", 0.0) or 0.0,
            zone4_pct=data.get("zone4_pct", 0.0) or 0.0,
            zone5_pct=data.get("zone5_pct", 0.0) or 0.0,
            cadence=data.get("cadence"),
            elevation_gain=data.get("elevation_gain"),
            calories=data.get("calories"),
            # Phase 2: Multi-sport extensions
            sport_type=data.get("sport_type"),
            avg_power=data.get("avg_power"),
            max_power=data.get("max_power"),
            normalized_power=data.get("normalized_power"),
            power_tss=data.get("power_tss"),
            tss=data.get("tss") or data.get("power_tss"),
            intensity_factor=data.get("intensity_factor"),
            variability_index=data.get("variability_index"),
            cycling_cadence=data.get("cycling_cadence"),
            avg_speed_kmh=data.get("avg_speed_kmh"),
            elevation_gain_m=data.get("elevation_gain_m"),
            pool_length_m=data.get("pool_length_m"),
            total_strokes=data.get("total_strokes"),
            avg_swolf=data.get("avg_swolf"),
            avg_stroke_rate=data.get("avg_stroke_rate"),
            css_pace_sec=data.get("css_pace_sec"),
        )


# ============================================================================
# Score Calculation Functions
# ============================================================================

def calculate_training_effect(
    duration_min: float,
    avg_hr: Optional[int],
    max_hr: int = 185,
    rest_hr: int = 55,
    zone3_pct: float = 0.0,
    zone4_pct: float = 0.0,
    zone5_pct: float = 0.0,
) -> float:
    """
    Calculate training effect score (0.0-5.0) based on workout intensity and duration.

    This approximates Garmin's Training Effect algorithm:
    - 0.0-0.9: No benefit
    - 1.0-1.9: Minor benefit
    - 2.0-2.9: Maintaining
    - 3.0-3.9: Improving
    - 4.0-4.9: Highly improving
    - 5.0: Overreaching

    Args:
        duration_min: Workout duration in minutes
        avg_hr: Average heart rate during workout
        max_hr: Athlete's max heart rate
        rest_hr: Athlete's resting heart rate
        zone3_pct: Percentage of time in zone 3
        zone4_pct: Percentage of time in zone 4
        zone5_pct: Percentage of time in zone 5

    Returns:
        Training effect score between 0.0 and 5.0
    """
    if not avg_hr or duration_min < 5:
        return 0.0

    # Calculate intensity factor (0-1) based on HR reserve
    hr_reserve = max_hr - rest_hr
    if hr_reserve <= 0:
        return 0.0

    intensity = (avg_hr - rest_hr) / hr_reserve
    intensity = max(0.0, min(1.0, intensity))

    # Weight high-intensity zones more heavily
    high_intensity_bonus = (zone3_pct * 0.01 + zone4_pct * 0.02 + zone5_pct * 0.03)

    # Duration factor (diminishing returns after 60 min)
    duration_factor = min(1.5, duration_min / 40)

    # Base training effect calculation
    training_effect = intensity * duration_factor * 3.0 + high_intensity_bonus

    # Clamp to valid range
    return round(max(0.0, min(5.0, training_effect)), 1)


def calculate_load_score(
    hrss: Optional[float] = None,
    trimp: Optional[float] = None,
    tss: Optional[float] = None,
    duration_min: float = 0.0,
    avg_hr: Optional[int] = None,
    max_hr: int = 185,
) -> int:
    """
    Calculate a normalized load score based on available training load metrics.

    Priority: HRSS > TSS > TRIMP > estimated from HR

    Args:
        hrss: Heart Rate Stress Score (0-200+ typical)
        trimp: Training Impulse (0-300+ typical)
        tss: Training Stress Score for power-based activities
        duration_min: Workout duration in minutes
        avg_hr: Average heart rate
        max_hr: Max heart rate for estimation

    Returns:
        Normalized load score (0-200+ typical, scaled appropriately)
    """
    # Use available metrics in priority order
    if hrss is not None and hrss > 0:
        return round(hrss)

    if tss is not None and tss > 0:
        return round(tss)

    if trimp is not None and trimp > 0:
        # TRIMP is typically larger scale, normalize
        return round(trimp * 0.7)

    # Fallback: estimate from duration and HR intensity
    if duration_min > 0 and avg_hr and max_hr > 0:
        intensity_pct = (avg_hr / max_hr) * 100
        estimated_load = duration_min * (intensity_pct / 100) * 1.2
        return round(estimated_load)

    return 0


def calculate_recovery_hours(
    training_effect: float,
    load_score: int,
    tsb: Optional[float] = None,
    execution_rating: Optional[str] = None,
    vo2max: Optional[float] = None,
) -> int:
    """
    Estimate recovery hours needed based on workout intensity and current fitness.

    Higher VO2max indicates better aerobic fitness and typically faster recovery.
    Athletes with higher VO2max can clear metabolic byproducts more efficiently.

    Args:
        training_effect: Training effect score (0.0-5.0)
        load_score: Training load score
        tsb: Training Stress Balance (fatigue indicator)
        execution_rating: How well the workout was executed
        vo2max: VO2max value in ml/kg/min (optional, used to adjust recovery)

    Returns:
        Estimated recovery hours (typically 12-72)
    """
    # Base recovery from training effect
    if training_effect < 1.0:
        base_hours = 12
    elif training_effect < 2.0:
        base_hours = 18
    elif training_effect < 3.0:
        base_hours = 24
    elif training_effect < 4.0:
        base_hours = 36
    elif training_effect < 4.5:
        base_hours = 48
    else:
        base_hours = 72

    # Adjust for load score
    if load_score > 150:
        base_hours += 12
    elif load_score > 100:
        base_hours += 6

    # Adjust for fatigue (negative TSB = more tired = more recovery needed)
    if tsb is not None:
        if tsb < -20:
            base_hours += 12
        elif tsb < -10:
            base_hours += 6
        elif tsb > 10:
            base_hours -= 6

    # Adjust for VO2max (higher fitness = faster recovery)
    # Research suggests well-trained athletes recover faster due to:
    # - Better lactate clearance
    # - More efficient cardiovascular system
    # - Enhanced mitochondrial function
    if vo2max is not None:
        if vo2max > 60:
            # Elite/highly trained: reduce recovery by 15-20%
            recovery_reduction = 0.80 + (0.05 * (70 - min(vo2max, 70)) / 10)
            base_hours = int(base_hours * recovery_reduction)
        elif vo2max > 55:
            # Well-trained: reduce recovery by 10-15%
            recovery_reduction = 0.85 + (0.05 * (60 - vo2max) / 5)
            base_hours = int(base_hours * recovery_reduction)
        elif vo2max > 50:
            # Trained: reduce recovery by 5-10%
            recovery_reduction = 0.90 + (0.05 * (55 - vo2max) / 5)
            base_hours = int(base_hours * recovery_reduction)
        elif vo2max < 40:
            # Lower fitness: increase recovery by 10%
            base_hours = int(base_hours * 1.10)
        # 40-50 is average range, no adjustment

    # Clamp to reasonable range
    return max(12, min(96, base_hours))


def calculate_overall_score(
    execution_rating: Optional[str] = None,
    training_effect: float = 0.0,
    load_score: int = 0,
    zone_distribution_quality: float = 0.0,
) -> int:
    """
    Calculate an overall workout quality score (0-100).

    Factors:
    - Execution rating (40% weight)
    - Training effect appropriateness (30% weight)
    - Load score achievement (20% weight)
    - Zone distribution quality (10% weight)

    Args:
        execution_rating: 'excellent', 'good', 'fair', 'needs_improvement'
        training_effect: Training effect score (0.0-5.0)
        load_score: Training load achieved
        zone_distribution_quality: 0-1 score for zone distribution

    Returns:
        Overall score from 0-100
    """
    # Execution rating contribution (0-40 points)
    rating_scores = {
        "excellent": 40,
        "good": 32,
        "fair": 20,
        "needs_improvement": 10,
    }
    execution_score = rating_scores.get(execution_rating, 25)

    # Training effect contribution (0-30 points)
    # 2.5-4.0 is optimal for most workouts
    if 2.5 <= training_effect <= 4.0:
        te_score = 30
    elif training_effect < 1.0:
        te_score = 5
    elif training_effect < 2.0:
        te_score = 15
    elif training_effect < 2.5:
        te_score = 22
    elif training_effect < 4.5:
        te_score = 25
    else:
        te_score = 20  # Overreaching is not always ideal

    # Load score contribution (0-20 points)
    # Normalize load score: 50-150 is typical good range
    if 50 <= load_score <= 150:
        load_contribution = 20
    elif load_score < 30:
        load_contribution = 5
    elif load_score < 50:
        load_contribution = 12
    else:
        load_contribution = 15  # Very high load

    # Zone distribution contribution (0-10 points)
    zone_contribution = int(zone_distribution_quality * 10)

    total = execution_score + te_score + load_contribution + zone_contribution
    return max(0, min(100, total))


def get_score_color(value: float, thresholds: Dict[str, float]) -> ScoreColor:
    """
    Determine the appropriate color for a score based on thresholds.

    Args:
        value: The score value
        thresholds: Dict with 'green', 'yellow' thresholds (red is below yellow)

    Returns:
        ScoreColor enum value
    """
    if value >= thresholds.get("green", 80):
        return ScoreColor.GREEN
    elif value >= thresholds.get("yellow", 50):
        return ScoreColor.YELLOW
    else:
        return ScoreColor.RED


def get_score_label(value: float, scale: str = "percent") -> str:
    """
    Get a human-readable label for a score value.

    Args:
        value: The score value
        scale: Type of scale ('percent', 'training_effect', 'custom')

    Returns:
        Human-readable label
    """
    if scale == "percent":
        if value >= 90:
            return "Excellent"
        elif value >= 75:
            return "Good"
        elif value >= 50:
            return "Fair"
        elif value >= 25:
            return "Below Average"
        else:
            return "Poor"
    elif scale == "training_effect":
        if value >= 4.5:
            return "Overreaching"
        elif value >= 3.5:
            return "Highly Improving"
        elif value >= 2.5:
            return "Improving"
        elif value >= 1.5:
            return "Maintaining"
        elif value >= 0.5:
            return "Minor Benefit"
        else:
            return "No Benefit"
    else:
        return "N/A"


def build_default_score_cards(
    workout_data: Dict[str, Any],
    training_effect: float,
    load_score: int,
    recovery_hours: int,
    execution_rating: Optional[str] = None,
) -> List[ScoreCard]:
    """
    Build a list of default score cards from workout data.

    Args:
        workout_data: Dictionary containing workout metrics
        training_effect: Calculated training effect
        load_score: Calculated load score
        recovery_hours: Calculated recovery hours
        execution_rating: Execution rating string

    Returns:
        List of ScoreCard objects
    """
    cards = []

    # Training Effect card
    cards.append(ScoreCard(
        name="Training Effect",
        value=training_effect,
        max_value=5.0,
        label=get_score_label(training_effect, "training_effect"),
        color=get_score_color(training_effect, {"green": 2.5, "yellow": 1.5}),
        description="Measures the impact on your aerobic fitness",
    ))

    # Training Load card
    load_label = "High" if load_score > 120 else "Moderate" if load_score > 60 else "Low"
    cards.append(ScoreCard(
        name="Training Load",
        value=float(load_score),
        max_value=200.0,
        label=load_label,
        color=get_score_color(load_score, {"green": 50, "yellow": 30}),
        description="Training stress from this workout (HRSS/TRIMP)",
    ))

    # Recovery Time card
    recovery_label = f"{recovery_hours}h"
    recovery_color = ScoreColor.GREEN if recovery_hours <= 24 else ScoreColor.YELLOW if recovery_hours <= 48 else ScoreColor.RED
    cards.append(ScoreCard(
        name="Recovery Time",
        value=float(recovery_hours),
        max_value=96.0,
        label=recovery_label,
        color=recovery_color,
        description="Estimated time until full recovery",
        unit="hours",
    ))

    # HR Control card (if HR data available)
    avg_hr = workout_data.get("avg_hr")
    max_hr_workout = workout_data.get("max_hr")
    if avg_hr and max_hr_workout:
        hr_efficiency = min(100, (avg_hr / max_hr_workout) * 100)
        hr_label = "Steady" if 75 <= hr_efficiency <= 90 else "High" if hr_efficiency > 90 else "Low"
        cards.append(ScoreCard(
            name="HR Control",
            value=round(hr_efficiency, 1),
            max_value=100.0,
            label=hr_label,
            color=ScoreColor.GREEN if 75 <= hr_efficiency <= 90 else ScoreColor.YELLOW,
            description="Avg HR relative to max HR during workout",
            unit="%",
        ))

    # Zone Distribution card (if zone data available)
    zone2_pct = workout_data.get("zone2_pct", 0) or 0
    zone3_pct = workout_data.get("zone3_pct", 0) or 0
    zone4_pct = workout_data.get("zone4_pct", 0) or 0
    aerobic_pct = zone2_pct + zone3_pct
    if aerobic_pct > 0:
        zone_label = "Aerobic" if aerobic_pct > 60 else "Mixed" if aerobic_pct > 30 else "Anaerobic"
        cards.append(ScoreCard(
            name="Zone Distribution",
            value=round(aerobic_pct, 1),
            max_value=100.0,
            label=zone_label,
            color=ScoreColor.GREEN if aerobic_pct > 50 else ScoreColor.YELLOW,
            description="Time spent in aerobic zones (Z2-Z3)",
            unit="%",
        ))

    return cards
