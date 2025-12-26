"""Workout analysis data models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field


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

    # Structured insights
    insights: List[WorkoutInsight] = Field(default_factory=list, description="Structured insights")

    # Ratings
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

    def to_prompt_context(self) -> str:
        """Convert to formatted string for LLM prompt injection."""
        lines = [
            f"CTL: {self.ctl:.1f} | ATL: {self.atl:.1f} | TSB: {self.tsb:.1f}",
            f"ACWR: {self.acwr:.2f} | Risk Zone: {self.risk_zone}",
            f"Readiness: {self.readiness_score:.0f}/100 ({self.readiness_zone})",
        ]

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
    tss: Optional[float] = None  # Training Stress Score (power-based)
    intensity_factor: Optional[float] = None
    variability_index: Optional[float] = None

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
            tss=data.get("tss"),
            intensity_factor=data.get("intensity_factor"),
            variability_index=data.get("variability_index"),
            avg_speed_kmh=data.get("avg_speed_kmh"),
            elevation_gain_m=data.get("elevation_gain_m"),
            pool_length_m=data.get("pool_length_m"),
            total_strokes=data.get("total_strokes"),
            avg_swolf=data.get("avg_swolf"),
            avg_stroke_rate=data.get("avg_stroke_rate"),
            css_pace_sec=data.get("css_pace_sec"),
        )
