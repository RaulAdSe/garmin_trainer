"""
Safety Service for training load monitoring and injury prevention.

Provides ACWR spike detection, training monotony/strain calculations,
and safety alert management to help prevent overtraining injuries.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import statistics
import logging
import uuid

from pydantic import BaseModel, ConfigDict, Field


logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================


class AlertSeverity(str, Enum):
    """Severity levels for safety alerts."""
    INFO = "info"           # Informational, no action needed
    MODERATE = "moderate"   # Warning, consider adjusting
    CRITICAL = "critical"   # Danger, action required


class AlertType(str, Enum):
    """Types of safety alerts."""
    ACWR_SPIKE = "acwr_spike"                   # Week-over-week load spike
    HIGH_MONOTONY = "high_monotony"             # Training too repetitive
    HIGH_STRAIN = "high_strain"                 # Accumulated strain too high
    ACUTE_CHRONIC_RATIO = "acute_chronic_ratio" # ACWR outside optimal range
    CONSECUTIVE_HARD_DAYS = "consecutive_hard"  # Too many hard days in a row
    INSUFFICIENT_RECOVERY = "insufficient_recovery"  # Not enough rest


class AlertStatus(str, Enum):
    """Status of a safety alert."""
    ACTIVE = "active"           # Alert is active and needs attention
    ACKNOWLEDGED = "acknowledged"  # User has seen the alert
    RESOLVED = "resolved"       # Condition no longer applies
    DISMISSED = "dismissed"     # User dismissed the alert


# Thresholds based on sports science research
ACWR_SPIKE_WARNING_THRESHOLD = 0.15   # 15% week-over-week increase
ACWR_SPIKE_DANGER_THRESHOLD = 0.25    # 25% week-over-week increase
MONOTONY_WARNING_THRESHOLD = 2.0      # Monotony > 2.0 is concerning
STRAIN_WARNING_THRESHOLD = 6000       # Strain > 6000 is high risk
STRAIN_CRITICAL_THRESHOLD = 8000      # Strain > 8000 is very high risk


# =============================================================================
# Data Models
# =============================================================================


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


@dataclass
class SafetyAlert:
    """
    A safety alert indicating a potential injury risk.
    """
    id: str
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    title: str
    message: str
    recommendation: str

    # Metrics that triggered the alert
    metrics: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    # Optional context
    week_start: Optional[date] = None
    user_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "alertType": self.alert_type.value,
            "severity": self.severity.value,
            "status": self.status.value,
            "title": self.title,
            "message": self.message,
            "recommendation": self.recommendation,
            "metrics": self.metrics,
            "createdAt": self.created_at.isoformat(),
            "acknowledgedAt": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolvedAt": self.resolved_at.isoformat() if self.resolved_at else None,
            "weekStart": self.week_start.isoformat() if self.week_start else None,
        }


@dataclass
class MonotonyStrainResult:
    """
    Result of monotony and strain calculations for a training week.
    """
    week_start: date
    week_end: date

    # Daily loads
    daily_loads: List[float]

    # Calculated metrics
    total_load: float
    mean_load: float
    std_dev: float
    monotony: float      # mean / std_dev
    strain: float        # total_load * monotony

    # Risk assessment
    monotony_risk: AlertSeverity
    strain_risk: AlertSeverity

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "weekStart": self.week_start.isoformat(),
            "weekEnd": self.week_end.isoformat(),
            "dailyLoads": self.daily_loads,
            "totalLoad": round(self.total_load, 1),
            "meanLoad": round(self.mean_load, 1),
            "stdDev": round(self.std_dev, 2),
            "monotony": round(self.monotony, 2),
            "strain": round(self.strain, 0),
            "monotonyRisk": self.monotony_risk.value,
            "strainRisk": self.strain_risk.value,
        }


@dataclass
class ACWRSpikeResult:
    """
    Result of ACWR spike detection between two weeks.
    """
    current_week_start: date
    previous_week_start: date
    current_week_load: float
    previous_week_load: float
    change_pct: float           # Percentage change
    spike_detected: bool
    severity: Optional[AlertSeverity]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "currentWeekStart": self.current_week_start.isoformat(),
            "previousWeekStart": self.previous_week_start.isoformat(),
            "currentWeekLoad": round(self.current_week_load, 1),
            "previousWeekLoad": round(self.previous_week_load, 1),
            "changePct": round(self.change_pct * 100, 1),
            "spikeDetected": self.spike_detected,
            "severity": self.severity.value if self.severity else None,
        }


@dataclass
class LoadAnalysis:
    """
    Comprehensive load analysis including spike detection and monotony/strain.
    """
    analysis_date: date

    # Weekly metrics
    current_week_load: float
    previous_week_load: float

    # Spike detection
    spike_result: ACWRSpikeResult

    # Monotony/Strain
    monotony_strain: Optional[MonotonyStrainResult]

    # Active alerts
    alerts: List[SafetyAlert]

    # Overall risk assessment
    overall_risk: AlertSeverity
    risk_factors: List[str]
    recommendations: List[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "analysisDate": self.analysis_date.isoformat(),
            "currentWeekLoad": round(self.current_week_load, 1),
            "previousWeekLoad": round(self.previous_week_load, 1),
            "spikeResult": self.spike_result.to_dict(),
            "monotonyStrain": self.monotony_strain.to_dict() if self.monotony_strain else None,
            "alerts": [a.to_dict() for a in self.alerts],
            "overallRisk": self.overall_risk.value,
            "riskFactors": self.risk_factors,
            "recommendations": self.recommendations,
        }


# =============================================================================
# Pydantic Response Models (for API)
# =============================================================================


class SafetyAlertResponse(BaseModel):
    """API response model for a safety alert."""

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
    metrics: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(..., alias="createdAt")
    acknowledged_at: Optional[str] = Field(None, alias="acknowledgedAt")
    week_start: Optional[str] = Field(None, alias="weekStart")


class LoadAnalysisResponse(BaseModel):
    """API response model for load analysis."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    analysis_date: str = Field(..., alias="analysisDate")
    current_week_load: float = Field(..., alias="currentWeekLoad")
    previous_week_load: float = Field(..., alias="previousWeekLoad")
    change_pct: float = Field(..., alias="changePct")
    spike_detected: bool = Field(..., alias="spikeDetected")
    spike_severity: Optional[str] = Field(None, alias="spikeSeverity")
    monotony: Optional[float] = None
    strain: Optional[float] = None
    monotony_risk: Optional[str] = Field(None, alias="monotonyRisk")
    strain_risk: Optional[str] = Field(None, alias="strainRisk")
    overall_risk: str = Field(..., alias="overallRisk")
    risk_factors: List[str] = Field(default_factory=list, alias="riskFactors")
    recommendations: List[str] = Field(default_factory=list)
    alerts_count: int = Field(0, alias="alertsCount")


# =============================================================================
# Core Functions
# =============================================================================


def detect_acwr_spike(
    current_week_load: float,
    previous_week_load: float,
    current_week_start: Optional[date] = None,
    previous_week_start: Optional[date] = None,
) -> ACWRSpikeResult:
    """
    Detect week-over-week training load spikes.

    Based on research showing that rapid increases in training load
    are associated with increased injury risk.

    Args:
        current_week_load: Total training load for current week
        previous_week_load: Total training load for previous week
        current_week_start: Start date of current week (optional)
        previous_week_start: Start date of previous week (optional)

    Returns:
        ACWRSpikeResult with spike detection results

    Thresholds (based on Gabbett et al.):
        - >15% increase: Moderate risk (warning)
        - >25% increase: Critical risk (danger)
    """
    # Handle edge cases
    if previous_week_load <= 0:
        # No previous load to compare against
        return ACWRSpikeResult(
            current_week_start=current_week_start or date.today(),
            previous_week_start=previous_week_start or (date.today() - timedelta(days=7)),
            current_week_load=current_week_load,
            previous_week_load=previous_week_load,
            change_pct=0.0,
            spike_detected=False,
            severity=None,
        )

    # Calculate percentage change
    change_pct = (current_week_load - previous_week_load) / previous_week_load

    # Determine severity
    severity = None
    spike_detected = False

    if change_pct > ACWR_SPIKE_DANGER_THRESHOLD:  # >25%
        severity = AlertSeverity.CRITICAL
        spike_detected = True
    elif change_pct > ACWR_SPIKE_WARNING_THRESHOLD:  # >15%
        severity = AlertSeverity.MODERATE
        spike_detected = True

    return ACWRSpikeResult(
        current_week_start=current_week_start or date.today(),
        previous_week_start=previous_week_start or (date.today() - timedelta(days=7)),
        current_week_load=current_week_load,
        previous_week_load=previous_week_load,
        change_pct=change_pct,
        spike_detected=spike_detected,
        severity=severity,
    )


def calculate_monotony_strain(
    daily_loads: List[float],
    week_start: Optional[date] = None,
) -> MonotonyStrainResult:
    """
    Calculate training monotony and strain for injury risk assessment.

    Monotony measures how repetitive training is - low variation increases
    injury and overtraining risk. Strain combines load and monotony.

    Formulas:
        Monotony = Mean daily load / Standard deviation of daily loads
        Strain = Total weekly load * Monotony

    Args:
        daily_loads: List of 7 daily training loads (Mon-Sun)
        week_start: Start date of the week (optional)

    Returns:
        MonotonyStrainResult with calculated metrics and risk levels

    Risk thresholds (Foster, 1998):
        - Monotony > 2.0: Elevated risk
        - Strain > 6000: High risk
        - Strain > 8000: Very high risk
    """
    if not daily_loads:
        daily_loads = [0.0] * 7

    # Pad to 7 days if needed
    while len(daily_loads) < 7:
        daily_loads.append(0.0)

    # Take only first 7 days
    daily_loads = daily_loads[:7]

    # Calculate basic statistics
    total_load = sum(daily_loads)
    mean_load = statistics.mean(daily_loads)

    # Handle case where all days are the same (std_dev = 0)
    try:
        std_dev = statistics.stdev(daily_loads)
    except statistics.StatisticsError:
        std_dev = 0.0

    # Calculate monotony (handle division by zero)
    if std_dev > 0:
        monotony = mean_load / std_dev
    else:
        # All days the same = perfect monotony = concerning
        monotony = 10.0 if mean_load > 0 else 0.0

    # Calculate strain
    strain = total_load * monotony

    # Assess monotony risk
    if monotony > 2.5:
        monotony_risk = AlertSeverity.CRITICAL
    elif monotony > MONOTONY_WARNING_THRESHOLD:
        monotony_risk = AlertSeverity.MODERATE
    else:
        monotony_risk = AlertSeverity.INFO

    # Assess strain risk
    if strain > STRAIN_CRITICAL_THRESHOLD:
        strain_risk = AlertSeverity.CRITICAL
    elif strain > STRAIN_WARNING_THRESHOLD:
        strain_risk = AlertSeverity.MODERATE
    else:
        strain_risk = AlertSeverity.INFO

    week_start_date = week_start or date.today()
    week_end_date = week_start_date + timedelta(days=6)

    return MonotonyStrainResult(
        week_start=week_start_date,
        week_end=week_end_date,
        daily_loads=daily_loads,
        total_load=total_load,
        mean_load=mean_load,
        std_dev=std_dev,
        monotony=monotony,
        strain=strain,
        monotony_risk=monotony_risk,
        strain_risk=strain_risk,
    )


def create_spike_alert(
    spike_result: ACWRSpikeResult,
    user_id: Optional[str] = None,
) -> Optional[SafetyAlert]:
    """
    Create a safety alert for a detected ACWR spike.

    Args:
        spike_result: Result from detect_acwr_spike
        user_id: Optional user ID

    Returns:
        SafetyAlert if spike was detected, None otherwise
    """
    if not spike_result.spike_detected or spike_result.severity is None:
        return None

    change_pct_display = abs(spike_result.change_pct * 100)

    if spike_result.severity == AlertSeverity.CRITICAL:
        title = "Critical Training Load Spike Detected"
        message = (
            f"Your training load increased by {change_pct_display:.0f}% this week "
            f"compared to last week. This significant increase puts you at high "
            f"risk for injury or overtraining."
        )
        recommendation = (
            "Reduce training intensity immediately. Consider taking an extra rest day "
            "and reducing volume by 20-30% for the next few days. Focus on recovery."
        )
    else:
        title = "Training Load Spike Warning"
        message = (
            f"Your training load increased by {change_pct_display:.0f}% this week. "
            f"While some progression is good, rapid increases can lead to injury."
        )
        recommendation = (
            "Monitor how you're feeling closely. Consider adding extra recovery time "
            "and avoid any additional load increases this week."
        )

    return SafetyAlert(
        id=str(uuid.uuid4()),
        alert_type=AlertType.ACWR_SPIKE,
        severity=spike_result.severity,
        status=AlertStatus.ACTIVE,
        title=title,
        message=message,
        recommendation=recommendation,
        metrics={
            "currentWeekLoad": spike_result.current_week_load,
            "previousWeekLoad": spike_result.previous_week_load,
            "changePct": spike_result.change_pct * 100,
        },
        week_start=spike_result.current_week_start,
        user_id=user_id,
    )


def create_monotony_alert(
    monotony_strain: MonotonyStrainResult,
    user_id: Optional[str] = None,
) -> Optional[SafetyAlert]:
    """
    Create a safety alert for high monotony.

    Args:
        monotony_strain: Result from calculate_monotony_strain
        user_id: Optional user ID

    Returns:
        SafetyAlert if monotony is concerning, None otherwise
    """
    if monotony_strain.monotony_risk == AlertSeverity.INFO:
        return None

    if monotony_strain.monotony_risk == AlertSeverity.CRITICAL:
        title = "Very High Training Monotony"
        message = (
            f"Your training monotony is {monotony_strain.monotony:.1f}, which is very high. "
            f"Repetitive training with little variation increases injury and illness risk."
        )
        recommendation = (
            "Add variety to your training immediately. Include different workout types, "
            "varying intensities, and cross-training. Consider a recovery day."
        )
    else:
        title = "Elevated Training Monotony"
        message = (
            f"Your training monotony is {monotony_strain.monotony:.1f}. "
            f"Consider adding more variety to your training to reduce injury risk."
        )
        recommendation = (
            "Try varying your workout intensities more. Mix easy days with harder sessions "
            "and consider adding different activities."
        )

    return SafetyAlert(
        id=str(uuid.uuid4()),
        alert_type=AlertType.HIGH_MONOTONY,
        severity=monotony_strain.monotony_risk,
        status=AlertStatus.ACTIVE,
        title=title,
        message=message,
        recommendation=recommendation,
        metrics={
            "monotony": monotony_strain.monotony,
            "meanLoad": monotony_strain.mean_load,
            "stdDev": monotony_strain.std_dev,
        },
        week_start=monotony_strain.week_start,
        user_id=user_id,
    )


def create_strain_alert(
    monotony_strain: MonotonyStrainResult,
    user_id: Optional[str] = None,
) -> Optional[SafetyAlert]:
    """
    Create a safety alert for high strain.

    Args:
        monotony_strain: Result from calculate_monotony_strain
        user_id: Optional user ID

    Returns:
        SafetyAlert if strain is concerning, None otherwise
    """
    if monotony_strain.strain_risk == AlertSeverity.INFO:
        return None

    if monotony_strain.strain_risk == AlertSeverity.CRITICAL:
        title = "Critical Training Strain Level"
        message = (
            f"Your training strain is {monotony_strain.strain:.0f}, which is critically high. "
            f"This level of accumulated stress significantly increases injury risk."
        )
        recommendation = (
            "Reduce training volume immediately. Take 1-2 complete rest days and focus "
            "on recovery activities like sleep, nutrition, and light stretching."
        )
    else:
        title = "High Training Strain"
        message = (
            f"Your training strain is {monotony_strain.strain:.0f}. "
            f"High strain combined with insufficient recovery can lead to overtraining."
        )
        recommendation = (
            "Consider reducing your next few workouts in intensity or duration. "
            "Prioritize sleep and recovery."
        )

    return SafetyAlert(
        id=str(uuid.uuid4()),
        alert_type=AlertType.HIGH_STRAIN,
        severity=monotony_strain.strain_risk,
        status=AlertStatus.ACTIVE,
        title=title,
        message=message,
        recommendation=recommendation,
        metrics={
            "strain": monotony_strain.strain,
            "totalLoad": monotony_strain.total_load,
            "monotony": monotony_strain.monotony,
        },
        week_start=monotony_strain.week_start,
        user_id=user_id,
    )


# =============================================================================
# Safety Service Class
# =============================================================================


class SafetyService:
    """
    Service for monitoring training safety and generating alerts.

    Tracks training loads, detects dangerous patterns, and provides
    actionable recommendations to prevent injuries.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the safety service.

        Args:
            db_path: Path to the database (for persisting alerts)
        """
        self._db_path = db_path
        self._alerts: Dict[str, SafetyAlert] = {}
        self._logger = logging.getLogger(__name__)

    def analyze_training_load(
        self,
        current_week_loads: List[float],
        previous_week_loads: List[float],
        current_week_start: Optional[date] = None,
        user_id: Optional[str] = None,
    ) -> LoadAnalysis:
        """
        Perform comprehensive training load analysis.

        Analyzes week-over-week load changes, monotony, and strain
        to identify potential injury risks.

        Args:
            current_week_loads: Daily loads for current week (7 values)
            previous_week_loads: Daily loads for previous week (7 values)
            current_week_start: Start date of current week
            user_id: Optional user ID for alerts

        Returns:
            LoadAnalysis with comprehensive results and alerts
        """
        week_start = current_week_start or date.today()
        prev_week_start = week_start - timedelta(days=7)

        # Calculate weekly totals
        current_total = sum(current_week_loads)
        previous_total = sum(previous_week_loads)

        # Detect spikes
        spike_result = detect_acwr_spike(
            current_week_load=current_total,
            previous_week_load=previous_total,
            current_week_start=week_start,
            previous_week_start=prev_week_start,
        )

        # Calculate monotony/strain
        monotony_strain = calculate_monotony_strain(
            daily_loads=current_week_loads,
            week_start=week_start,
        )

        # Generate alerts
        alerts: List[SafetyAlert] = []

        spike_alert = create_spike_alert(spike_result, user_id)
        if spike_alert:
            alerts.append(spike_alert)
            self._alerts[spike_alert.id] = spike_alert

        monotony_alert = create_monotony_alert(monotony_strain, user_id)
        if monotony_alert:
            alerts.append(monotony_alert)
            self._alerts[monotony_alert.id] = monotony_alert

        strain_alert = create_strain_alert(monotony_strain, user_id)
        if strain_alert:
            alerts.append(strain_alert)
            self._alerts[strain_alert.id] = strain_alert

        # Determine overall risk and generate recommendations
        risk_factors: List[str] = []
        recommendations: List[str] = []

        if spike_result.spike_detected:
            risk_factors.append(f"Training load spike: {spike_result.change_pct * 100:.0f}% increase")

        if monotony_strain.monotony_risk != AlertSeverity.INFO:
            risk_factors.append(f"High monotony: {monotony_strain.monotony:.1f}")

        if monotony_strain.strain_risk != AlertSeverity.INFO:
            risk_factors.append(f"High strain: {monotony_strain.strain:.0f}")

        # Determine overall risk level
        severities = [a.severity for a in alerts]
        if AlertSeverity.CRITICAL in severities:
            overall_risk = AlertSeverity.CRITICAL
            recommendations.append("Reduce training load immediately")
            recommendations.append("Take 1-2 rest days this week")
            recommendations.append("Focus on sleep and recovery")
        elif AlertSeverity.MODERATE in severities:
            overall_risk = AlertSeverity.MODERATE
            recommendations.append("Monitor fatigue levels closely")
            recommendations.append("Avoid adding more training load this week")
            recommendations.append("Consider an extra easy day")
        else:
            overall_risk = AlertSeverity.INFO
            recommendations.append("Training load is within safe ranges")
            recommendations.append("Continue with planned training")

        return LoadAnalysis(
            analysis_date=week_start,
            current_week_load=current_total,
            previous_week_load=previous_total,
            spike_result=spike_result,
            monotony_strain=monotony_strain,
            alerts=alerts,
            overall_risk=overall_risk,
            risk_factors=risk_factors,
            recommendations=recommendations,
        )

    def get_active_alerts(self, user_id: Optional[str] = None) -> List[SafetyAlert]:
        """
        Get all active (unacknowledged) alerts.

        Args:
            user_id: Optional user ID to filter alerts

        Returns:
            List of active SafetyAlert objects
        """
        alerts = [
            a for a in self._alerts.values()
            if a.status == AlertStatus.ACTIVE
        ]

        if user_id:
            alerts = [a for a in alerts if a.user_id == user_id or a.user_id is None]

        # Sort by severity (critical first) then by date
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.MODERATE: 1,
            AlertSeverity.INFO: 2,
        }

        return sorted(
            alerts,
            key=lambda a: (severity_order.get(a.severity, 3), -a.created_at.timestamp()),
        )

    def get_alert(self, alert_id: str) -> Optional[SafetyAlert]:
        """
        Get a specific alert by ID.

        Args:
            alert_id: The alert ID

        Returns:
            SafetyAlert if found, None otherwise
        """
        return self._alerts.get(alert_id)

    def acknowledge_alert(self, alert_id: str) -> Optional[SafetyAlert]:
        """
        Acknowledge an alert (mark as seen by user).

        Args:
            alert_id: The alert ID to acknowledge

        Returns:
            Updated SafetyAlert if found, None otherwise
        """
        alert = self._alerts.get(alert_id)
        if alert:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.now()
            self._logger.info(f"Alert {alert_id} acknowledged")
        return alert

    def dismiss_alert(self, alert_id: str) -> Optional[SafetyAlert]:
        """
        Dismiss an alert (user chose to ignore).

        Args:
            alert_id: The alert ID to dismiss

        Returns:
            Updated SafetyAlert if found, None otherwise
        """
        alert = self._alerts.get(alert_id)
        if alert:
            alert.status = AlertStatus.DISMISSED
            self._logger.info(f"Alert {alert_id} dismissed")
        return alert

    def resolve_alert(self, alert_id: str) -> Optional[SafetyAlert]:
        """
        Resolve an alert (condition no longer applies).

        Args:
            alert_id: The alert ID to resolve

        Returns:
            Updated SafetyAlert if found, None otherwise
        """
        alert = self._alerts.get(alert_id)
        if alert:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now()
            self._logger.info(f"Alert {alert_id} resolved")
        return alert

    def clear_old_alerts(self, days: int = 14) -> int:
        """
        Clear alerts older than specified days.

        Args:
            days: Number of days to keep alerts

        Returns:
            Number of alerts cleared
        """
        cutoff = datetime.now() - timedelta(days=days)
        old_alerts = [
            aid for aid, a in self._alerts.items()
            if a.created_at < cutoff
        ]

        for aid in old_alerts:
            del self._alerts[aid]

        return len(old_alerts)


# =============================================================================
# Singleton Instance
# =============================================================================


_safety_service: Optional[SafetyService] = None


def get_safety_service(db_path: Optional[str] = None) -> SafetyService:
    """
    Get the safety service singleton.

    Args:
        db_path: Optional database path

    Returns:
        SafetyService instance
    """
    global _safety_service
    if _safety_service is None:
        _safety_service = SafetyService(db_path=db_path)
    return _safety_service
