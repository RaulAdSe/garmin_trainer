"""Recovery module data models for sleep debt, HRV trends, and recovery time estimation."""

from datetime import date as date_type, datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


# =============================================================================
# Enums
# =============================================================================

class SleepDebtImpact(str, Enum):
    """Impact level of accumulated sleep debt."""
    MINIMAL = "minimal"        # < 3 hours debt
    MODERATE = "moderate"      # 3-7 hours debt
    SIGNIFICANT = "significant"  # 7-14 hours debt
    CRITICAL = "critical"      # > 14 hours debt


class HRVTrendDirection(str, Enum):
    """Direction of HRV trend."""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    INSUFFICIENT_DATA = "insufficient_data"


class RecoveryStatus(str, Enum):
    """Overall recovery status."""
    EXCELLENT = "excellent"    # Fully recovered, ready for hard training
    GOOD = "good"              # Well recovered, can train normally
    MODERATE = "moderate"      # Some fatigue, consider easier training
    POOR = "poor"              # High fatigue, prioritize recovery
    CRITICAL = "critical"      # Exhausted, rest required


# =============================================================================
# Sleep Models
# =============================================================================

class SleepRecord(BaseModel):
    """Individual sleep record from wearable."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    date: date_type = Field(..., description="Date of sleep (night ending on this date)")
    duration_hours: float = Field(..., ge=0, le=24, description="Total sleep duration in hours")
    quality_score: Optional[float] = Field(None, ge=0, le=100, description="Sleep quality score 0-100")
    deep_sleep_hours: Optional[float] = Field(None, ge=0, description="Deep sleep duration")
    rem_sleep_hours: Optional[float] = Field(None, ge=0, description="REM sleep duration")
    light_sleep_hours: Optional[float] = Field(None, ge=0, description="Light sleep duration")
    awake_time_hours: Optional[float] = Field(None, ge=0, description="Time awake during sleep period")
    sleep_start: Optional[datetime] = Field(None, description="Bedtime")
    sleep_end: Optional[datetime] = Field(None, description="Wake time")


class SleepDebtAnalysis(BaseModel):
    """Analysis of 7-day rolling sleep debt."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    total_debt_hours: float = Field(..., description="Total accumulated sleep debt in hours")
    daily_debt_breakdown: List[float] = Field(
        default_factory=list,
        description="Daily debt values for the period"
    )
    target_hours: float = Field(default=8.0, description="Target sleep hours per night")
    window_days: int = Field(default=7, description="Analysis window in days")
    average_sleep_hours: float = Field(..., description="Average sleep per night")
    impact_level: SleepDebtImpact = Field(..., description="Impact level of debt")
    recommendation: str = Field(..., description="Recovery recommendation")
    trend: str = Field(default="stable", description="Trend direction: improving, stable, declining")

    # Additional metrics
    sleep_consistency_score: Optional[float] = Field(
        None, ge=0, le=100,
        description="Consistency of sleep schedule (0-100)"
    )
    average_quality: Optional[float] = Field(
        None, ge=0, le=100,
        description="Average sleep quality over the period"
    )


# =============================================================================
# HRV Models
# =============================================================================

class HRVRecord(BaseModel):
    """Individual HRV measurement."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    date: date_type = Field(..., description="Date of measurement")
    rmssd: float = Field(..., ge=0, description="RMSSD value in milliseconds")
    sdnn: Optional[float] = Field(None, ge=0, description="SDNN value in milliseconds")
    lf_power: Optional[float] = Field(None, ge=0, description="Low frequency power")
    hf_power: Optional[float] = Field(None, ge=0, description="High frequency power")
    lf_hf_ratio: Optional[float] = Field(None, ge=0, description="LF/HF ratio")
    measurement_time: Optional[datetime] = Field(None, description="When HRV was measured")


class HRVTrendAnalysis(BaseModel):
    """HRV trend analysis with rolling averages and coefficient of variation."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # Current values
    current_rmssd: Optional[float] = Field(None, description="Most recent RMSSD")
    current_date: Optional[date_type] = Field(None, description="Date of current measurement")

    # Rolling averages
    rolling_average_7d: Optional[float] = Field(None, description="7-day rolling average RMSSD")
    rolling_average_30d: Optional[float] = Field(None, description="30-day rolling average RMSSD")

    # Coefficient of variation (more stable indicator)
    cv_7d: Optional[float] = Field(
        None,
        description="7-day coefficient of variation (CV% = std_dev/mean * 100)"
    )
    cv_30d: Optional[float] = Field(
        None,
        description="30-day coefficient of variation"
    )

    # LF/HF ratio if available
    current_lf_hf_ratio: Optional[float] = Field(None, description="Current LF/HF ratio")
    average_lf_hf_ratio_7d: Optional[float] = Field(None, description="7-day average LF/HF ratio")

    # Trend analysis
    trend_direction: HRVTrendDirection = Field(
        default=HRVTrendDirection.INSUFFICIENT_DATA,
        description="Direction of HRV trend"
    )
    trend_percentage: Optional[float] = Field(
        None,
        description="Percentage change from baseline"
    )

    # Baseline (top 25th percentile over 30 days)
    baseline_rmssd: Optional[float] = Field(None, description="Baseline RMSSD value")
    relative_to_baseline: Optional[float] = Field(
        None,
        description="Current RMSSD as percentage of baseline"
    )

    # Status interpretation
    interpretation: str = Field(default="", description="Human-readable interpretation")
    data_points_7d: int = Field(default=0, description="Number of data points in 7-day window")
    data_points_30d: int = Field(default=0, description="Number of data points in 30-day window")


# =============================================================================
# Recovery Time Estimation
# =============================================================================

class RecoveryTimeEstimate(BaseModel):
    """Post-workout recovery time estimation."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # Core estimate
    hours_until_recovered: float = Field(..., description="Hours until recovered for easy training")
    hours_until_fresh: float = Field(..., description="Hours until ready for hard training")

    # Optimal timing
    next_easy_workout_at: datetime = Field(..., description="When easy workout is OK")
    next_hard_workout_at: datetime = Field(..., description="When hard workout is OK")

    # Factors that influenced the estimate
    factors: Dict[str, Any] = Field(
        default_factory=dict,
        description="Factors and their contributions"
    )

    # Adjustments
    workout_intensity_impact: float = Field(
        default=0.0,
        description="Hours added due to workout intensity"
    )
    sleep_debt_impact: float = Field(
        default=0.0,
        description="Hours added due to sleep debt"
    )
    hrv_status_impact: float = Field(
        default=0.0,
        description="Hours added due to HRV status"
    )
    current_fatigue_impact: float = Field(
        default=0.0,
        description="Hours added due to current fatigue state (TSB)"
    )

    # Recommendations
    recovery_activities: List[str] = Field(
        default_factory=list,
        description="Suggested recovery activities"
    )
    sleep_recommendation_hours: float = Field(
        default=8.0,
        description="Recommended sleep tonight"
    )


# =============================================================================
# Combined Recovery Module
# =============================================================================

class RecoveryModuleData(BaseModel):
    """Complete recovery module data combining all components."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    # Core components
    sleep_debt: Optional[SleepDebtAnalysis] = Field(
        None, description="Sleep debt analysis"
    )
    hrv_trend: Optional[HRVTrendAnalysis] = Field(
        None, description="HRV trend analysis"
    )
    recovery_time: Optional[RecoveryTimeEstimate] = Field(
        None, description="Recovery time estimation"
    )

    # Overall status
    overall_recovery_status: RecoveryStatus = Field(
        default=RecoveryStatus.MODERATE,
        description="Overall recovery status"
    )
    recovery_score: float = Field(
        default=50.0, ge=0, le=100,
        description="Overall recovery score (0-100)"
    )

    # Summary
    summary_message: str = Field(
        default="",
        description="Human-readable summary"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Top recommendations for recovery"
    )

    # Timestamps
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this analysis was generated"
    )
    data_freshness_hours: Optional[float] = Field(
        None,
        description="Age of most recent data in hours"
    )


# =============================================================================
# API Request/Response Models
# =============================================================================

class RecoveryModuleRequest(BaseModel):
    """Request for recovery module data."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    target_date: Optional[date_type] = Field(
        None, description="Target date for analysis (defaults to today)"
    )
    include_sleep_debt: bool = Field(
        default=True, description="Include sleep debt analysis"
    )
    include_hrv_trend: bool = Field(
        default=True, description="Include HRV trend analysis"
    )
    include_recovery_time: bool = Field(
        default=True, description="Include recovery time estimation"
    )
    sleep_target_hours: float = Field(
        default=8.0, ge=4.0, le=12.0, description="Target sleep hours for debt calculation"
    )


class RecoveryModuleResponse(BaseModel):
    """API response for recovery module."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    success: bool = Field(..., description="Whether the request succeeded")
    data: Optional[RecoveryModuleData] = Field(
        None, description="Recovery module data"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


class SleepDebtResponse(BaseModel):
    """API response for sleep debt only."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    success: bool = Field(...)
    data: Optional[SleepDebtAnalysis] = Field(None)
    error: Optional[str] = Field(None)


class HRVTrendResponse(BaseModel):
    """API response for HRV trend only."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    success: bool = Field(...)
    data: Optional[HRVTrendAnalysis] = Field(None)
    error: Optional[str] = Field(None)


class RecoveryTimeResponse(BaseModel):
    """API response for recovery time estimation."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    success: bool = Field(...)
    data: Optional[RecoveryTimeEstimate] = Field(None)
    workout_id: Optional[str] = Field(None, description="Workout this estimate is for")
    error: Optional[str] = Field(None)
