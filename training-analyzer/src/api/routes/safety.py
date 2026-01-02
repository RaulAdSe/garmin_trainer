"""Safety API routes for training load monitoring and injury prevention.

Provides endpoints for ACWR spike detection, monotony/strain analysis,
and safety alert management.

All safety routes require authentication since they expose user-specific
training load data and personalized injury risk assessments.
"""

from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from ..deps import get_training_db, get_coach_service, get_current_user, CurrentUser
from ...services.safety_service import (
    SafetyService,
    get_safety_service,
    AlertSeverity,
    AlertStatus,
    SafetyAlert,
    LoadAnalysis,
    detect_acwr_spike,
    calculate_monotony_strain,
)


router = APIRouter()


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


# =============================================================================
# Dependencies
# =============================================================================


def get_safety_service_dep(training_db=Depends(get_training_db)) -> SafetyService:
    """Get safety service instance using the training database path."""
    return get_safety_service(str(training_db.db_path))


# =============================================================================
# Request/Response Models
# =============================================================================


class SafetyAlertResponse(BaseModel):
    """Response model for a safety alert."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str
    alert_type: str = Field(..., alias="alertType")
    severity: str
    status: str
    title: str
    message: str
    recommendation: str
    metrics: dict = Field(default_factory=dict)
    created_at: str = Field(..., alias="createdAt")
    acknowledged_at: Optional[str] = Field(None, alias="acknowledgedAt")
    week_start: Optional[str] = Field(None, alias="weekStart")


class AlertsListResponse(BaseModel):
    """Response model for listing safety alerts."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    alerts: List[SafetyAlertResponse]
    total: int
    active_count: int = Field(..., alias="activeCount")
    critical_count: int = Field(..., alias="criticalCount")


class AcknowledgeResponse(BaseModel):
    """Response model for acknowledging an alert."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    success: bool
    alert_id: str = Field(..., alias="alertId")
    new_status: str = Field(..., alias="newStatus")


class SpikeAnalysisResponse(BaseModel):
    """Response model for ACWR spike analysis."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    current_week_start: str = Field(..., alias="currentWeekStart")
    previous_week_start: str = Field(..., alias="previousWeekStart")
    current_week_load: float = Field(..., alias="currentWeekLoad")
    previous_week_load: float = Field(..., alias="previousWeekLoad")
    change_pct: float = Field(..., alias="changePct")
    spike_detected: bool = Field(..., alias="spikeDetected")
    severity: Optional[str] = None


class MonotonyStrainResponse(BaseModel):
    """Response model for monotony/strain analysis."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    week_start: str = Field(..., alias="weekStart")
    week_end: str = Field(..., alias="weekEnd")
    daily_loads: List[float] = Field(..., alias="dailyLoads")
    total_load: float = Field(..., alias="totalLoad")
    mean_load: float = Field(..., alias="meanLoad")
    std_dev: float = Field(..., alias="stdDev")
    monotony: float
    strain: float
    monotony_risk: str = Field(..., alias="monotonyRisk")
    strain_risk: str = Field(..., alias="strainRisk")


class LoadAnalysisResponse(BaseModel):
    """Response model for comprehensive load analysis."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    analysis_date: str = Field(..., alias="analysisDate")
    current_week_load: float = Field(..., alias="currentWeekLoad")
    previous_week_load: float = Field(..., alias="previousWeekLoad")
    spike_result: SpikeAnalysisResponse = Field(..., alias="spikeResult")
    monotony_strain: Optional[MonotonyStrainResponse] = Field(None, alias="monotonyStrain")
    alerts: List[SafetyAlertResponse]
    overall_risk: str = Field(..., alias="overallRisk")
    risk_factors: List[str] = Field(default_factory=list, alias="riskFactors")
    recommendations: List[str] = Field(default_factory=list)


# =============================================================================
# Helper Functions
# =============================================================================


def alert_to_response(alert: SafetyAlert) -> SafetyAlertResponse:
    """Convert SafetyAlert dataclass to response model."""
    return SafetyAlertResponse(
        id=alert.id,
        alert_type=alert.alert_type.value,
        severity=alert.severity.value,
        status=alert.status.value,
        title=alert.title,
        message=alert.message,
        recommendation=alert.recommendation,
        metrics=alert.metrics,
        created_at=alert.created_at.isoformat(),
        acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        week_start=alert.week_start.isoformat() if alert.week_start else None,
    )


def get_weekly_loads_from_activities(
    activities: List[dict],
    week_start: date,
) -> List[float]:
    """
    Extract daily training loads for a week from activities.

    Args:
        activities: List of activity dictionaries
        week_start: Start date of the week (Monday)

    Returns:
        List of 7 daily load values (Mon-Sun)
    """
    daily_loads = [0.0] * 7

    for activity in activities:
        activity_date_str = activity.get("date")
        if not activity_date_str:
            continue

        try:
            if isinstance(activity_date_str, str):
                activity_date = date.fromisoformat(activity_date_str)
            else:
                activity_date = activity_date_str
        except (ValueError, TypeError):
            continue

        # Calculate day index (0 = Monday, 6 = Sunday)
        day_offset = (activity_date - week_start).days

        if 0 <= day_offset < 7:
            # Use HRSS if available, otherwise TRIMP, otherwise estimate from duration
            load = activity.get("hrss") or activity.get("trimp")
            if load is None:
                # Rough estimate: 1 TSS per minute for moderate activity
                duration_min = activity.get("duration_min", 0) or 0
                load = duration_min * 0.8  # Conservative estimate

            daily_loads[day_offset] += float(load)

    return daily_loads


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/alerts", response_model=AlertsListResponse)
async def get_safety_alerts(
    status: Optional[str] = Query(
        None,
        description="Filter by status: active, acknowledged, resolved, dismissed"
    ),
    severity: Optional[str] = Query(
        None,
        description="Filter by severity: info, moderate, critical"
    ),
    days: int = Query(
        14,
        ge=1,
        le=90,
        description="Number of days to look back"
    ),
    current_user: CurrentUser = Depends(get_current_user),
    safety_service: SafetyService = Depends(get_safety_service_dep),
):
    """
    Get safety alerts for the current user.

    Returns all safety alerts within the specified time period,
    optionally filtered by status and severity.

    Requires authentication.
    """
    try:
        # Get all alerts for user
        all_alerts = safety_service.get_active_alerts(user_id=current_user.id)

        # Also get acknowledged/resolved alerts from the internal store
        # For a complete view
        from datetime import datetime
        cutoff = datetime.now() - timedelta(days=days)

        all_from_store = [
            a for a in safety_service._alerts.values()
            if a.created_at >= cutoff
            and (a.user_id == current_user.id or a.user_id is None)
        ]

        # Apply filters
        filtered_alerts = all_from_store

        if status:
            try:
                status_enum = AlertStatus(status.lower())
                filtered_alerts = [a for a in filtered_alerts if a.status == status_enum]
            except ValueError:
                pass  # Invalid status, don't filter

        if severity:
            try:
                severity_enum = AlertSeverity(severity.lower())
                filtered_alerts = [a for a in filtered_alerts if a.severity == severity_enum]
            except ValueError:
                pass  # Invalid severity, don't filter

        # Sort by severity and date
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.MODERATE: 1,
            AlertSeverity.INFO: 2,
        }
        sorted_alerts = sorted(
            filtered_alerts,
            key=lambda a: (severity_order.get(a.severity, 3), -a.created_at.timestamp()),
        )

        # Convert to response models
        alert_responses = [alert_to_response(a) for a in sorted_alerts]

        # Calculate counts
        active_count = sum(1 for a in sorted_alerts if a.status == AlertStatus.ACTIVE)
        critical_count = sum(1 for a in sorted_alerts if a.severity == AlertSeverity.CRITICAL)

        return AlertsListResponse(
            alerts=alert_responses,
            total=len(alert_responses),
            active_count=active_count,
            critical_count=critical_count,
        )

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to get safety alerts: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get safety alerts. Please try again later.",
        )


@router.post("/alerts/{alert_id}/acknowledge", response_model=AcknowledgeResponse)
async def acknowledge_alert(
    alert_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    safety_service: SafetyService = Depends(get_safety_service_dep),
):
    """
    Acknowledge a safety alert.

    Marks the alert as seen by the user. The alert will no longer
    appear in the active alerts list but remains in history.

    Requires authentication.
    """
    try:
        alert = safety_service.acknowledge_alert(alert_id)

        if not alert:
            raise HTTPException(
                status_code=404,
                detail=f"Alert {alert_id} not found",
            )

        return AcknowledgeResponse(
            success=True,
            alert_id=alert_id,
            new_status=alert.status.value,
        )

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to acknowledge alert {alert_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to acknowledge alert. Please try again later.",
        )


@router.post("/alerts/{alert_id}/dismiss", response_model=AcknowledgeResponse)
async def dismiss_alert(
    alert_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    safety_service: SafetyService = Depends(get_safety_service_dep),
):
    """
    Dismiss a safety alert.

    Indicates the user has chosen to ignore this alert.
    Use sparingly - these alerts are for your safety.

    Requires authentication.
    """
    try:
        alert = safety_service.dismiss_alert(alert_id)

        if not alert:
            raise HTTPException(
                status_code=404,
                detail=f"Alert {alert_id} not found",
            )

        return AcknowledgeResponse(
            success=True,
            alert_id=alert_id,
            new_status=alert.status.value,
        )

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to dismiss alert {alert_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to dismiss alert. Please try again later.",
        )


@router.get("/load-analysis", response_model=LoadAnalysisResponse)
async def get_load_analysis(
    current_user: CurrentUser = Depends(get_current_user),
    coach_service=Depends(get_coach_service),
    safety_service: SafetyService = Depends(get_safety_service_dep),
):
    """
    Get comprehensive training load analysis with spike detection.

    Analyzes the current and previous week's training loads to detect:
    - Week-over-week load spikes (>15% warning, >25% critical)
    - Training monotony (repetitive training patterns)
    - Training strain (accumulated stress)

    Returns risk assessment and actionable recommendations.

    Requires authentication.
    """
    try:
        # Calculate week boundaries
        today = date.today()
        # Get Monday of current week
        current_week_start = today - timedelta(days=today.weekday())
        previous_week_start = current_week_start - timedelta(days=7)

        # Get activities for both weeks
        # Need 14 days of data for both current and previous week
        activities = coach_service.get_recent_activities(days=14)

        # Extract daily loads for each week
        current_week_loads = get_weekly_loads_from_activities(
            activities, current_week_start
        )
        previous_week_loads = get_weekly_loads_from_activities(
            activities, previous_week_start
        )

        # Perform comprehensive analysis
        analysis = safety_service.analyze_training_load(
            current_week_loads=current_week_loads,
            previous_week_loads=previous_week_loads,
            current_week_start=current_week_start,
            user_id=current_user.id,
        )

        # Build spike result response
        spike_response = SpikeAnalysisResponse(
            current_week_start=analysis.spike_result.current_week_start.isoformat(),
            previous_week_start=analysis.spike_result.previous_week_start.isoformat(),
            current_week_load=round(analysis.spike_result.current_week_load, 1),
            previous_week_load=round(analysis.spike_result.previous_week_load, 1),
            change_pct=round(analysis.spike_result.change_pct * 100, 1),
            spike_detected=analysis.spike_result.spike_detected,
            severity=analysis.spike_result.severity.value if analysis.spike_result.severity else None,
        )

        # Build monotony/strain response
        monotony_response = None
        if analysis.monotony_strain:
            ms = analysis.monotony_strain
            monotony_response = MonotonyStrainResponse(
                week_start=ms.week_start.isoformat(),
                week_end=ms.week_end.isoformat(),
                daily_loads=[round(l, 1) for l in ms.daily_loads],
                total_load=round(ms.total_load, 1),
                mean_load=round(ms.mean_load, 1),
                std_dev=round(ms.std_dev, 2),
                monotony=round(ms.monotony, 2),
                strain=round(ms.strain, 0),
                monotony_risk=ms.monotony_risk.value,
                strain_risk=ms.strain_risk.value,
            )

        # Convert alerts
        alert_responses = [alert_to_response(a) for a in analysis.alerts]

        return LoadAnalysisResponse(
            analysis_date=analysis.analysis_date.isoformat(),
            current_week_load=round(analysis.current_week_load, 1),
            previous_week_load=round(analysis.previous_week_load, 1),
            spike_result=spike_response,
            monotony_strain=monotony_response,
            alerts=alert_responses,
            overall_risk=analysis.overall_risk.value,
            risk_factors=analysis.risk_factors,
            recommendations=analysis.recommendations,
        )

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to analyze training load: {e}")
        import traceback
        logging.getLogger(__name__).error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze training load. Please try again later.",
        )


@router.get("/spike-check", response_model=SpikeAnalysisResponse)
async def check_spike(
    current_load: float = Query(..., description="Current week total training load"),
    previous_load: float = Query(..., description="Previous week total training load"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Quick check for ACWR spike between two load values.

    This is a lightweight endpoint for quick checks without
    requiring full activity data.

    Thresholds:
    - >15% increase: Moderate warning
    - >25% increase: Critical danger

    Requires authentication.
    """
    try:
        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())
        previous_week_start = current_week_start - timedelta(days=7)

        result = detect_acwr_spike(
            current_week_load=current_load,
            previous_week_load=previous_load,
            current_week_start=current_week_start,
            previous_week_start=previous_week_start,
        )

        return SpikeAnalysisResponse(
            current_week_start=result.current_week_start.isoformat(),
            previous_week_start=result.previous_week_start.isoformat(),
            current_week_load=round(result.current_week_load, 1),
            previous_week_load=round(result.previous_week_load, 1),
            change_pct=round(result.change_pct * 100, 1),
            spike_detected=result.spike_detected,
            severity=result.severity.value if result.severity else None,
        )

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to check spike: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to check spike. Please try again later.",
        )


@router.get("/monotony", response_model=MonotonyStrainResponse)
async def get_monotony_strain(
    current_user: CurrentUser = Depends(get_current_user),
    coach_service=Depends(get_coach_service),
):
    """
    Calculate monotony and strain for the current week.

    Monotony measures training variety - high monotony (>2.0)
    indicates repetitive training that increases injury risk.

    Strain combines load and monotony to assess accumulated stress.
    High strain (>6000) indicates elevated risk.

    Requires authentication.
    """
    try:
        # Calculate week boundaries
        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())

        # Get this week's activities
        activities = coach_service.get_recent_activities(days=7)

        # Extract daily loads
        daily_loads = get_weekly_loads_from_activities(activities, current_week_start)

        # Calculate monotony/strain
        result = calculate_monotony_strain(
            daily_loads=daily_loads,
            week_start=current_week_start,
        )

        return MonotonyStrainResponse(
            week_start=result.week_start.isoformat(),
            week_end=result.week_end.isoformat(),
            daily_loads=[round(l, 1) for l in result.daily_loads],
            total_load=round(result.total_load, 1),
            mean_load=round(result.mean_load, 1),
            std_dev=round(result.std_dev, 2),
            monotony=round(result.monotony, 2),
            strain=round(result.strain, 0),
            monotony_risk=result.monotony_risk.value,
            strain_risk=result.strain_risk.value,
        )

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to calculate monotony/strain: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to calculate monotony/strain. Please try again later.",
        )
