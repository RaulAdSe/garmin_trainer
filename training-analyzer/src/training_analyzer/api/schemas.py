"""
API schemas for request/response validation.

This module defines Pydantic models for all API endpoints,
ensuring consistent validation and documentation.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


T = TypeVar("T")


# ============================================================================
# Base Response Models
# ============================================================================

class ErrorDetail(BaseModel):
    """Error detail for API responses."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: ErrorDetail

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Workout with ID 'xyz' not found",
                }
            }
        }
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items", ge=0)
    page: int = Field(..., description="Current page number", ge=1)
    page_size: int = Field(..., description="Items per page", ge=1)
    total_pages: int = Field(..., description="Total number of pages", ge=0)
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SuccessResponse(BaseModel):
    """Simple success response."""

    success: bool = True
    message: Optional[str] = None


# ============================================================================
# Workout Schemas
# ============================================================================

class WorkoutMetrics(BaseModel):
    """Workout metrics."""

    avg_hr: Optional[int] = Field(None, description="Average heart rate in bpm")
    max_hr: Optional[int] = Field(None, description="Maximum heart rate in bpm")
    avg_pace: Optional[int] = Field(None, description="Average pace in seconds per km")
    cadence: Optional[int] = Field(None, description="Average cadence in steps per minute")
    elevation_gain: Optional[float] = Field(None, description="Elevation gain in meters")
    calories: Optional[int] = Field(None, description="Calories burned")


class HRZoneDistribution(BaseModel):
    """Heart rate zone distribution."""

    zone1_pct: float = Field(default=0.0, description="Percentage in Zone 1")
    zone2_pct: float = Field(default=0.0, description="Percentage in Zone 2")
    zone3_pct: float = Field(default=0.0, description="Percentage in Zone 3")
    zone4_pct: float = Field(default=0.0, description="Percentage in Zone 4")
    zone5_pct: float = Field(default=0.0, description="Percentage in Zone 5")


class WorkoutSummaryResponse(BaseModel):
    """Summary information about a workout."""

    id: str = Field(..., description="Workout ID")
    name: str = Field(..., description="Workout name")
    activity_type: str = Field(..., description="Type of activity")
    date: str = Field(..., description="Workout date")
    duration_min: float = Field(..., description="Duration in minutes")
    distance_km: Optional[float] = Field(None, description="Distance in kilometers")
    avg_hr: Optional[int] = Field(None, description="Average heart rate")
    hrss: Optional[float] = Field(None, description="Heart Rate Stress Score")
    has_analysis: bool = Field(default=False, description="Whether analysis exists")


class WorkoutDetailResponse(BaseModel):
    """Full workout details."""

    id: str
    name: str
    activity_type: str
    date: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_min: float
    distance_km: Optional[float] = None
    metrics: WorkoutMetrics
    zones: HRZoneDistribution
    hrss: Optional[float] = None
    trimp: Optional[float] = None
    notes: Optional[str] = None


class WorkoutListRequest(BaseModel):
    """Request parameters for workout listing."""

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(default="date", description="Sort field")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    start_date: Optional[str] = Field(None, description="Filter: start date")
    end_date: Optional[str] = Field(None, description="Filter: end date")
    activity_type: Optional[str] = Field(None, description="Filter: activity type")


# ============================================================================
# Analysis Schemas
# ============================================================================

class AnalysisRequestBody(BaseModel):
    """Request body for workout analysis."""

    include_context: bool = Field(default=True, description="Include athlete context")
    include_similar: bool = Field(default=True, description="Include similar workout comparison")
    regenerate: bool = Field(default=False, description="Force re-analysis")


class WorkoutInsightResponse(BaseModel):
    """A single insight about the workout."""

    category: str = Field(..., description="Category: pace, heart_rate, effort, recovery")
    observation: str = Field(..., description="The observation")
    is_positive: bool = Field(..., description="Whether positive")
    importance: str = Field(default="medium", description="low, medium, high")


class AnalysisContextResponse(BaseModel):
    """Context used for analysis."""

    ctl: Optional[float] = Field(None, description="Chronic Training Load")
    atl: Optional[float] = Field(None, description="Acute Training Load")
    tsb: Optional[float] = Field(None, description="Training Stress Balance")
    acwr: Optional[float] = Field(None, description="Acute:Chronic Workload Ratio")
    readiness_score: Optional[float] = Field(None, description="Readiness score")
    readiness_zone: Optional[str] = Field(None, description="Readiness zone")


class WorkoutAnalysisResponse(BaseModel):
    """Complete workout analysis response."""

    workout_id: str = Field(..., description="ID of the analyzed workout")
    analysis_id: str = Field(..., description="Unique analysis ID")
    status: str = Field(..., description="Status: pending, in_progress, completed, failed")
    summary: str = Field(default="", description="2-3 sentence summary")
    what_worked_well: List[str] = Field(default_factory=list)
    observations: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    insights: List[WorkoutInsightResponse] = Field(default_factory=list)
    execution_rating: Optional[str] = Field(None, description="excellent, good, fair, needs_improvement")
    training_fit: Optional[str] = Field(None, description="How this fits training plan")
    context: Optional[AnalysisContextResponse] = None
    model_used: str = Field(default="gpt-5-mini")
    created_at: str = Field(..., description="ISO timestamp")
    cached: bool = Field(default=False, description="Whether served from cache")


class StreamChunkResponse(BaseModel):
    """SSE stream chunk response."""

    type: str = Field(..., description="chunk type: content, done, error")
    content: Optional[str] = Field(None, description="Content chunk")
    analysis: Optional[Dict[str, Any]] = Field(None, description="Final analysis")
    error: Optional[str] = Field(None, description="Error message")


# ============================================================================
# Training Plan Schemas
# ============================================================================

class PlanGoalRequest(BaseModel):
    """Request body for plan goal."""

    race_distance: str = Field(..., description="5k, 10k, half, marathon, ultra, custom")
    race_date: str = Field(..., description="Race date (YYYY-MM-DD)")
    target_time: Optional[str] = Field(None, description="Target time (H:MM:SS or MM:SS)")
    race_name: Optional[str] = Field(None, description="Name of the race")
    priority: str = Field(default="A", description="A, B, or C race")
    custom_distance_km: Optional[float] = Field(None, description="For custom distance")


class PlanConstraintsRequest(BaseModel):
    """Request body for plan constraints."""

    days_per_week: int = Field(default=5, ge=3, le=7)
    long_run_day: str = Field(default="sunday", description="Day for long run")
    rest_days: List[str] = Field(default_factory=list, description="Rest day names")
    max_weekly_hours: float = Field(default=8.0, ge=2.0, le=20.0)
    max_session_duration_min: int = Field(default=150, ge=30, le=240)
    include_cross_training: bool = Field(default=False)
    current_fitness_level: str = Field(default="intermediate")


class CreatePlanRequest(BaseModel):
    """Request to create a training plan."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    goal: PlanGoalRequest
    constraints: PlanConstraintsRequest = Field(default_factory=PlanConstraintsRequest)
    periodization_type: Optional[str] = Field(None, description="linear, undulating, block")
    start_date: Optional[str] = Field(None, description="Start date (default: next Monday)")


class GeneratePlanRequest(CreatePlanRequest):
    """Request to generate a training plan with AI."""

    regenerate: bool = Field(default=False, description="Force regeneration")


class UpdatePlanRequest(BaseModel):
    """Request to update a training plan."""

    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class SessionResponse(BaseModel):
    """Training session response."""

    id: str
    day_of_week: int
    date: str
    session_type: str
    name: str
    description: str
    target_duration_min: int
    target_load: float
    actual_duration: Optional[int] = None
    actual_load: Optional[float] = None
    completion_status: str
    workout_id: Optional[str] = None
    notes: Optional[str] = None


class WeekResponse(BaseModel):
    """Training week response."""

    id: str
    week_number: int
    start_date: str
    end_date: str
    phase: str
    target_load: float
    actual_load: float
    sessions: List[SessionResponse]
    focus_areas: List[str]
    is_cutback: bool = False
    notes: Optional[str] = None


class PlanSummaryResponse(BaseModel):
    """Plan summary for listing."""

    id: str
    name: str
    status: str
    goal_race: str
    goal_date: str
    total_weeks: int
    current_week: int
    compliance_pct: float
    created_at: str


class PlanDetailResponse(BaseModel):
    """Full plan details."""

    id: str
    name: str
    description: Optional[str] = None
    status: str
    goal: Dict[str, Any]
    constraints: Dict[str, Any]
    periodization_type: str
    start_date: str
    end_date: str
    total_weeks: int
    current_week: int
    weeks: List[WeekResponse]
    compliance_pct: float
    created_at: str
    updated_at: str


class UpdateSessionRequest(BaseModel):
    """Request to update a session."""

    completion_status: Optional[str] = Field(None, description="pending, completed, skipped, partial")
    actual_duration: Optional[int] = Field(None, ge=0)
    actual_distance: Optional[float] = Field(None, ge=0)
    actual_load: Optional[float] = Field(None, ge=0)
    workout_id: Optional[str] = None
    notes: Optional[str] = None


class AdaptPlanRequest(BaseModel):
    """Request to adapt a training plan."""

    reason: Optional[str] = Field(None, description="Reason for adaptation")


class PlanProgressResponse(BaseModel):
    """Streaming progress response."""

    type: str = Field(..., description="progress, done, error")
    phase: Optional[str] = None
    message: Optional[str] = None
    percentage: Optional[int] = None
    plan: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ============================================================================
# Workout Design Schemas
# ============================================================================

class IntervalRequest(BaseModel):
    """Request for a workout interval."""

    type: str = Field(..., description="warmup, work, recovery, cooldown, rest")
    duration_sec: int = Field(..., ge=0, description="Duration in seconds")
    distance_m: Optional[int] = Field(None, ge=0, description="Distance in meters")
    target_pace_min: Optional[int] = Field(None, description="Min pace (sec/km)")
    target_pace_max: Optional[int] = Field(None, description="Max pace (sec/km)")
    target_hr_min: Optional[int] = Field(None, ge=0, le=250)
    target_hr_max: Optional[int] = Field(None, ge=0, le=250)
    repetitions: int = Field(default=1, ge=1)
    notes: Optional[str] = None


class DesignWorkoutRequest(BaseModel):
    """Request to design a structured workout."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    workout_type: str = Field(..., description="running, cycling, swimming")
    intervals: List[IntervalRequest]
    sport: str = Field(default="running")


class GenerateWorkoutRequest(BaseModel):
    """Request to generate workout suggestions."""

    workout_type: str = Field(..., description="easy, long, tempo, intervals, threshold")
    target_duration_min: int = Field(default=60, ge=10, le=300)
    target_load: Optional[float] = Field(None, description="Target training load")
    focus: Optional[str] = Field(None, description="Focus area")
    include_athlete_context: bool = Field(default=True)
    suggestions_count: int = Field(default=3, ge=1, le=5)


class IntervalResponse(BaseModel):
    """Response for a workout interval."""

    type: str
    duration_sec: int
    distance_m: Optional[int] = None
    target_pace_range: Optional[tuple[int, int]] = None
    target_hr_range: Optional[tuple[int, int]] = None
    repetitions: int
    notes: Optional[str] = None


class StructuredWorkoutResponse(BaseModel):
    """Response for a structured workout."""

    id: str
    name: str
    description: Optional[str] = None
    sport: str
    intervals: List[IntervalResponse]
    total_duration_sec: int
    total_distance_m: Optional[int] = None
    estimated_load: Optional[float] = None
    created_at: str


class WorkoutSuggestionResponse(BaseModel):
    """AI-generated workout suggestion."""

    id: str
    title: str
    description: str
    workout: StructuredWorkoutResponse
    rationale: str
    difficulty: str
    focus_area: str
    estimated_load: float


class GenerateWorkoutResponse(BaseModel):
    """Response for workout generation."""

    suggestions: List[WorkoutSuggestionResponse]
    athlete_context: Optional[Dict[str, Any]] = None


class FITExportResponse(BaseModel):
    """Response for FIT file export."""

    success: bool
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    expires_at: Optional[str] = None
    error: Optional[str] = None


class GarminExportResponse(BaseModel):
    """Response for Garmin Connect export."""

    success: bool
    garmin_workout_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# Athlete Schemas
# ============================================================================

class AthleteProfileResponse(BaseModel):
    """Athlete profile response."""

    max_hr: int
    rest_hr: int
    threshold_hr: int
    hr_zones: Dict[int, Dict[str, int]]
    training_paces: Dict[str, int]
    vdot: Optional[float] = None


class FitnessMetricsResponse(BaseModel):
    """Fitness metrics response."""

    ctl: float = Field(..., description="Chronic Training Load (fitness)")
    atl: float = Field(..., description="Acute Training Load (fatigue)")
    tsb: float = Field(..., description="Training Stress Balance (form)")
    acwr: float = Field(..., description="Acute:Chronic Workload Ratio")
    risk_zone: str = Field(..., description="undertraining, optimal, overreaching, danger")


class ReadinessResponse(BaseModel):
    """Readiness assessment response."""

    score: float = Field(..., ge=0, le=100)
    zone: str = Field(..., description="green, yellow, red")
    recommendation: str
    factors: Dict[str, Any]


class AthleteContextResponse(BaseModel):
    """Full athlete context response."""

    profile: AthleteProfileResponse
    fitness: FitnessMetricsResponse
    readiness: ReadinessResponse
    race_goal: Optional[Dict[str, Any]] = None
    recent_load_7d: float
    days_since_hard: int


# ============================================================================
# Health Check
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="healthy, degraded, unhealthy")
    version: str
    timestamp: str
    services: Dict[str, str] = Field(default_factory=dict)
