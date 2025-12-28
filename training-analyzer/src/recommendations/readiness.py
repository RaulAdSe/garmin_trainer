"""
Readiness Score Calculation

Combines multiple factors into a 0-100 readiness score:
- Recovery data (HRV, sleep, Body Battery) from wellness
- Training load balance (TSB, ACWR)
- Recent training pattern

This module also provides full explainability for transparency.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import date, datetime

from ..models.explanations import (
    ImpactType,
    DataSourceType,
    DataSource,
    ExplanationFactor,
    ExplainedRecommendation,
    ExplainedReadiness,
)


@dataclass
class ReadinessFactors:
    """Individual factors contributing to readiness."""

    hrv_score: Optional[float] = None       # 0-100, HRV vs baseline
    sleep_score: Optional[float] = None      # 0-100, sleep quality/duration
    body_battery: Optional[float] = None     # 0-100, Garmin Body Battery
    stress_score: Optional[float] = None     # 0-100, inverse of stress (low stress = high score)
    training_load_score: Optional[float] = None  # 0-100, based on TSB/ACWR
    recovery_days: int = 0                   # Days since last hard workout

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hrv_score": self.hrv_score,
            "sleep_score": self.sleep_score,
            "body_battery": self.body_battery,
            "stress_score": self.stress_score,
            "training_load_score": self.training_load_score,
            "recovery_days": self.recovery_days,
        }

    def available_factors(self) -> List[str]:
        """Return list of factors that have data."""
        available = []
        if self.hrv_score is not None:
            available.append("hrv")
        if self.sleep_score is not None:
            available.append("sleep")
        if self.body_battery is not None:
            available.append("body_battery")
        if self.stress_score is not None:
            available.append("stress")
        if self.training_load_score is not None:
            available.append("training_load")
        return available


@dataclass
class ReadinessResult:
    """Complete readiness assessment."""

    date: date
    overall_score: float                     # 0-100 combined score
    factors: ReadinessFactors
    zone: str                                # 'green', 'yellow', 'red'
    recommendation: str                      # Brief workout recommendation
    explanation: str                         # Why this recommendation

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "date": self.date.isoformat(),
            "overall_score": round(self.overall_score, 1),
            "factors": self.factors.to_dict(),
            "zone": self.zone,
            "recommendation": self.recommendation,
            "explanation": self.explanation,
        }


# Default weights for readiness calculation
DEFAULT_WEIGHTS = {
    'hrv': 0.25,
    'sleep': 0.20,
    'body_battery': 0.15,
    'stress': 0.10,
    'training_load': 0.20,
    'recovery_days': 0.10
}


def calculate_hrv_score(
    hrv_last_night: Optional[int],
    hrv_weekly_avg: Optional[int],
    hrv_status: Optional[str] = None,
) -> Optional[float]:
    """
    Calculate HRV contribution to readiness score.

    Uses ratio of last night's HRV to weekly average.
    A ratio of 1.0 = 75 points (baseline)
    Higher than baseline = up to 100 points
    Lower than baseline = reduced points

    Args:
        hrv_last_night: Last night's average HRV
        hrv_weekly_avg: 7-day HRV average
        hrv_status: Garmin HRV status (BALANCED, HIGH, LOW)

    Returns:
        HRV score 0-100, or None if insufficient data
    """
    if hrv_last_night is None or hrv_weekly_avg is None or hrv_weekly_avg == 0:
        return None

    # Calculate ratio
    ratio = hrv_last_night / hrv_weekly_avg

    # Base score: ratio of 1.0 = 75 points
    # Ratio of 1.2+ = 100 points
    # Ratio of 0.7 = 50 points
    # Ratio of 0.5 = 25 points

    if ratio >= 1.2:
        score = 100.0
    elif ratio >= 1.0:
        # Linear interpolation from 75 to 100 for ratio 1.0-1.2
        score = 75 + (ratio - 1.0) * 125
    elif ratio >= 0.7:
        # Linear interpolation from 50 to 75 for ratio 0.7-1.0
        score = 50 + (ratio - 0.7) * (25 / 0.3)
    elif ratio >= 0.5:
        # Linear interpolation from 25 to 50 for ratio 0.5-0.7
        score = 25 + (ratio - 0.5) * (25 / 0.2)
    else:
        # Very low HRV
        score = max(0, ratio * 50)

    # Bonus/penalty for Garmin status
    if hrv_status == "HIGH":
        score = min(100, score + 5)
    elif hrv_status == "LOW":
        score = max(0, score - 5)

    return min(100, max(0, score))


def calculate_sleep_score(
    total_sleep_hours: Optional[float],
    deep_sleep_pct: Optional[float] = None,
    rem_sleep_pct: Optional[float] = None,
    sleep_efficiency: Optional[float] = None,
    sleep_score: Optional[int] = None,
    target_sleep_hours: float = 8.0,
) -> Optional[float]:
    """
    Calculate sleep contribution to readiness score.

    Components:
    - Duration: 8 hours target = 85 points
    - Deep sleep: 20% target = 15 points

    Args:
        total_sleep_hours: Total sleep duration
        deep_sleep_pct: Percentage of deep sleep
        rem_sleep_pct: Percentage of REM sleep
        sleep_efficiency: Sleep efficiency percentage
        sleep_score: Garmin sleep score (if available)
        target_sleep_hours: Target sleep hours (default 8)

    Returns:
        Sleep score 0-100, or None if insufficient data
    """
    # If Garmin provides a sleep score, use it directly
    if sleep_score is not None:
        return float(sleep_score)

    if total_sleep_hours is None:
        return None

    # Duration component (85% of score)
    duration_ratio = min(1.0, total_sleep_hours / target_sleep_hours)
    duration_score = duration_ratio * 85

    # Deep sleep component (15% of score)
    # Target: 20% deep sleep
    deep_score = 0.0
    if deep_sleep_pct is not None:
        deep_ratio = min(1.0, deep_sleep_pct / 20.0)
        deep_score = deep_ratio * 15
    else:
        # If no deep sleep data, scale up duration
        duration_score = duration_ratio * 100

    score = duration_score + deep_score

    # Efficiency bonus/penalty
    if sleep_efficiency is not None:
        if sleep_efficiency >= 90:
            score = min(100, score + 5)
        elif sleep_efficiency < 70:
            score = max(0, score - 10)

    return min(100, max(0, score))


def calculate_stress_score(
    avg_stress_level: Optional[int],
    rest_stress_duration: int = 0,
    high_stress_duration: int = 0,
) -> Optional[float]:
    """
    Calculate stress contribution to readiness (inverse of stress).

    Low stress = high readiness score
    High stress = low readiness score

    Args:
        avg_stress_level: Average stress level (0-100)
        rest_stress_duration: Time in rest state (seconds)
        high_stress_duration: Time in high stress state (seconds)

    Returns:
        Stress score 0-100 (100 = low stress = good), or None if no data
    """
    if avg_stress_level is None:
        return None

    # Invert: low stress (0-25) = high score (75-100)
    # High stress (75-100) = low score (0-25)
    score = 100 - avg_stress_level

    # Adjust based on time in high stress
    total_duration = rest_stress_duration + high_stress_duration
    if total_duration > 0:
        high_stress_ratio = high_stress_duration / max(1, total_duration)
        # Penalty for prolonged high stress
        if high_stress_ratio > 0.3:
            score = score * 0.9

    return min(100, max(0, score))


def calculate_training_load_score(
    tsb: Optional[float],
    acwr: Optional[float],
) -> Optional[float]:
    """
    Calculate training load contribution to readiness.

    Combines TSB (form) and ACWR (injury risk) into a single score.

    Args:
        tsb: Training Stress Balance (positive = fresh, negative = fatigued)
        acwr: Acute:Chronic Workload Ratio

    Returns:
        Training load score 0-100, or None if no data
    """
    if tsb is None and acwr is None:
        return None

    # TSB component (60% of score)
    # TSB > 20: Very fresh = 100 points
    # TSB 0-20: Fresh = 70-100 points
    # TSB -10 to 0: Neutral = 50-70 points
    # TSB -25 to -10: Fatigued = 30-50 points
    # TSB < -25: Very fatigued = 0-30 points

    tsb_score = 50.0  # Default if no TSB
    if tsb is not None:
        if tsb > 20:
            tsb_score = 100.0
        elif tsb > 0:
            tsb_score = 70 + (tsb / 20) * 30
        elif tsb > -10:
            tsb_score = 50 + (tsb / 10) * 20
        elif tsb > -25:
            tsb_score = 30 + ((tsb + 25) / 15) * 20
        else:
            tsb_score = max(0, 30 + (tsb + 25) * 2)

    # ACWR component (40% of score)
    # ACWR 0.8-1.3 (optimal): 80-100 points
    # ACWR < 0.8 (undertrained): 50-80 points
    # ACWR 1.3-1.5 (caution): 30-60 points
    # ACWR > 1.5 (danger): 0-30 points

    acwr_score = 75.0  # Default if no ACWR
    if acwr is not None:
        if 0.8 <= acwr <= 1.3:
            # Optimal zone
            # Peak at ACWR = 1.0
            distance_from_peak = abs(acwr - 1.0)
            acwr_score = 100 - (distance_from_peak * 50)
        elif acwr < 0.8:
            # Undertrained
            acwr_score = 50 + (acwr / 0.8) * 30
        elif acwr <= 1.5:
            # Caution zone
            acwr_score = 60 - ((acwr - 1.3) / 0.2) * 30
        else:
            # Danger zone
            acwr_score = max(0, 30 - (acwr - 1.5) * 30)

    # Combine: 60% TSB, 40% ACWR
    combined = (tsb_score * 0.6) + (acwr_score * 0.4)

    return min(100, max(0, combined))


def calculate_recovery_days_score(
    days_since_hard: int,
) -> float:
    """
    Calculate recovery days contribution to readiness.

    More recovery days = higher score (up to a point).

    Args:
        days_since_hard: Days since last hard/intense workout

    Returns:
        Recovery score 0-100
    """
    # 0 days: Just did hard workout, score = 30
    # 1 day: Some recovery, score = 60
    # 2+ days: Well recovered, score = 80-100

    if days_since_hard == 0:
        return 30.0
    elif days_since_hard == 1:
        return 60.0
    elif days_since_hard == 2:
        return 85.0
    elif days_since_hard >= 3:
        # Fully recovered but don't want too many rest days
        # 3 days = 100, 4 days = 95, 5+ days = 90
        return max(90, 110 - days_since_hard * 5)

    return 50.0


def _determine_zone(score: float) -> str:
    """Determine readiness zone from score."""
    if score >= 67:
        return "green"
    elif score >= 34:
        return "yellow"
    else:
        return "red"


def _generate_quick_recommendation(score: float, zone: str, factors: ReadinessFactors) -> str:
    """Generate a brief workout recommendation."""
    if zone == "red":
        return "Rest or very light recovery activity recommended"
    elif zone == "yellow":
        if factors.training_load_score is not None and factors.training_load_score < 40:
            return "Easy day - training load is elevated"
        elif factors.sleep_score is not None and factors.sleep_score < 50:
            return "Light activity - prioritize sleep recovery"
        else:
            return "Moderate intensity OK, avoid high-intensity efforts"
    else:  # green
        if score >= 85:
            return "Great day for quality training or a hard workout"
        else:
            return "Good day for moderate-to-hard training"


def _generate_quick_explanation(factors: ReadinessFactors, score: float) -> str:
    """Generate a brief explanation of readiness."""
    limiting_factors = []
    positive_factors = []

    if factors.hrv_score is not None:
        if factors.hrv_score < 50:
            limiting_factors.append("HRV below baseline")
        elif factors.hrv_score >= 80:
            positive_factors.append("HRV strong")

    if factors.sleep_score is not None:
        if factors.sleep_score < 50:
            limiting_factors.append("poor sleep")
        elif factors.sleep_score >= 80:
            positive_factors.append("well-rested")

    if factors.body_battery is not None:
        if factors.body_battery < 40:
            limiting_factors.append("low Body Battery")
        elif factors.body_battery >= 75:
            positive_factors.append("high energy")

    if factors.training_load_score is not None:
        if factors.training_load_score < 40:
            limiting_factors.append("high training load")
        elif factors.training_load_score >= 75:
            positive_factors.append("fresh from training")

    if factors.recovery_days >= 2:
        positive_factors.append(f"{factors.recovery_days} days recovery")
    elif factors.recovery_days == 0:
        limiting_factors.append("trained hard recently")

    # Build explanation
    if limiting_factors and positive_factors:
        return f"Positives: {', '.join(positive_factors)}. Watch: {', '.join(limiting_factors)}."
    elif limiting_factors:
        return f"Limited by: {', '.join(limiting_factors)}."
    elif positive_factors:
        return f"Looking good: {', '.join(positive_factors)}."
    else:
        return "Moderate readiness based on available data."


def calculate_readiness(
    wellness_data: Optional[Dict[str, Any]],
    fitness_metrics: Optional[Dict[str, Any]],
    recent_activities: list,
    weights: Optional[Dict[str, float]] = None,
    target_date: Optional[date] = None,
) -> ReadinessResult:
    """
    Calculate overall readiness score.

    Args:
        wellness_data: Today's wellness (HRV, sleep, Body Battery, stress)
        fitness_metrics: Current CTL/ATL/TSB/ACWR
        recent_activities: Last 7 days of activities
        weights: Optional custom weights for factors
        target_date: Date for assessment (defaults to today)

    Returns:
        ReadinessResult with score, zone, and recommendation
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS.copy()

    if target_date is None:
        target_date = date.today()

    factors = ReadinessFactors()

    # Calculate HRV score
    if wellness_data:
        hrv_data = wellness_data.get("hrv")
        if hrv_data:
            factors.hrv_score = calculate_hrv_score(
                hrv_last_night=hrv_data.get("hrv_last_night_avg"),
                hrv_weekly_avg=hrv_data.get("hrv_weekly_avg"),
                hrv_status=hrv_data.get("hrv_status"),
            )

        # Calculate sleep score
        sleep_data = wellness_data.get("sleep")
        if sleep_data:
            factors.sleep_score = calculate_sleep_score(
                total_sleep_hours=sleep_data.get("total_sleep_hours"),
                deep_sleep_pct=sleep_data.get("deep_sleep_pct"),
                rem_sleep_pct=sleep_data.get("rem_sleep_pct"),
                sleep_efficiency=sleep_data.get("sleep_efficiency"),
                sleep_score=sleep_data.get("sleep_score"),
            )

        # Body Battery (direct value 0-100)
        stress_data = wellness_data.get("stress")
        if stress_data:
            bb_charged = stress_data.get("body_battery_charged")
            bb_high = stress_data.get("body_battery_high")
            # Use charged amount or current high value
            if bb_charged is not None:
                factors.body_battery = float(bb_charged)
            elif bb_high is not None:
                factors.body_battery = float(bb_high)

            # Stress score
            factors.stress_score = calculate_stress_score(
                avg_stress_level=stress_data.get("avg_stress_level"),
                rest_stress_duration=stress_data.get("rest_stress_duration", 0),
                high_stress_duration=stress_data.get("high_stress_duration", 0),
            )

    # Calculate training load score
    if fitness_metrics:
        factors.training_load_score = calculate_training_load_score(
            tsb=fitness_metrics.get("tsb"),
            acwr=fitness_metrics.get("acwr"),
        )

    # Calculate days since last hard workout
    if recent_activities:
        factors.recovery_days = _calculate_days_since_hard(recent_activities, target_date)

    # Calculate weighted average score
    total_weight = 0.0
    weighted_sum = 0.0

    factor_map = {
        'hrv': factors.hrv_score,
        'sleep': factors.sleep_score,
        'body_battery': factors.body_battery,
        'stress': factors.stress_score,
        'training_load': factors.training_load_score,
    }

    for key, value in factor_map.items():
        if value is not None and key in weights:
            weight = weights[key]
            weighted_sum += value * weight
            total_weight += weight

    # Add recovery days contribution
    if 'recovery_days' in weights:
        recovery_score = calculate_recovery_days_score(factors.recovery_days)
        weighted_sum += recovery_score * weights['recovery_days']
        total_weight += weights['recovery_days']

    # Calculate overall score
    if total_weight > 0:
        overall_score = weighted_sum / total_weight
    else:
        # No data available, use conservative estimate
        overall_score = 50.0

    # Determine zone
    zone = _determine_zone(overall_score)

    # Generate recommendation and explanation
    recommendation = _generate_quick_recommendation(overall_score, zone, factors)
    explanation = _generate_quick_explanation(factors, overall_score)

    return ReadinessResult(
        date=target_date,
        overall_score=overall_score,
        factors=factors,
        zone=zone,
        recommendation=recommendation,
        explanation=explanation,
    )


def _calculate_days_since_hard(activities: list, target_date: date) -> int:
    """
    Calculate days since last hard workout.

    A workout is considered 'hard' if:
    - HRSS > 75 (threshold-ish effort for an hour)
    - TRIMP > 100

    Args:
        activities: List of recent activities with hrss/trimp
        target_date: Date to calculate from

    Returns:
        Number of days since last hard workout
    """
    if not activities:
        return 3  # Assume some recovery if no data

    hard_threshold_hrss = 75.0
    hard_threshold_trimp = 100.0

    last_hard_date = None

    for activity in activities:
        # Get activity date
        activity_date_str = activity.get("date")
        if not activity_date_str:
            continue

        try:
            if isinstance(activity_date_str, str):
                activity_date = datetime.strptime(activity_date_str, "%Y-%m-%d").date()
            else:
                activity_date = activity_date_str
        except (ValueError, TypeError):
            continue

        # Check if hard workout
        hrss = activity.get("hrss", 0) or 0
        trimp = activity.get("trimp", 0) or 0

        if hrss >= hard_threshold_hrss or trimp >= hard_threshold_trimp:
            if last_hard_date is None or activity_date > last_hard_date:
                last_hard_date = activity_date

    if last_hard_date is None:
        return 3  # No hard workouts found

    days_since = (target_date - last_hard_date).days
    return max(0, days_since)


def _get_impact_type(score: float, threshold_good: float = 70, threshold_bad: float = 50) -> ImpactType:
    """Determine impact type based on score thresholds."""
    if score >= threshold_good:
        return ImpactType.POSITIVE
    elif score < threshold_bad:
        return ImpactType.NEGATIVE
    return ImpactType.NEUTRAL


def _format_percentage_change(current: float, baseline: float) -> str:
    """Format a percentage change with sign."""
    if baseline == 0:
        return "N/A"
    pct = ((current - baseline) / baseline) * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"


def calculate_explained_readiness(
    wellness_data: Optional[Dict[str, Any]],
    fitness_metrics: Optional[Dict[str, Any]],
    recent_activities: list,
    weights: Optional[Dict[str, float]] = None,
    target_date: Optional[date] = None,
) -> ExplainedReadiness:
    """
    Calculate readiness with full explainability.

    This extends calculate_readiness to provide complete transparency
    into the calculation, showing exactly what data was used, how each
    factor contributed, and the mathematical reasoning.

    Args:
        wellness_data: Today's wellness (HRV, sleep, Body Battery, stress)
        fitness_metrics: Current CTL/ATL/TSB/ACWR
        recent_activities: Last 7 days of activities
        weights: Optional custom weights for factors
        target_date: Date for assessment (defaults to today)

    Returns:
        ExplainedReadiness with full factor breakdown
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS.copy()

    if target_date is None:
        target_date = date.today()

    # First, calculate the standard readiness
    result = calculate_readiness(
        wellness_data=wellness_data,
        fitness_metrics=fitness_metrics,
        recent_activities=recent_activities,
        weights=weights,
        target_date=target_date,
    )

    # Now build the detailed factor breakdown
    factor_breakdown: List[ExplanationFactor] = []
    calculation_steps: List[str] = []
    data_points: Dict[str, Any] = {}
    total_weight = 0.0
    weighted_sum = 0.0

    # HRV Factor
    if result.factors.hrv_score is not None:
        hrv_data = wellness_data.get("hrv", {}) if wellness_data else {}
        hrv_last = hrv_data.get("hrv_last_night_avg")
        hrv_weekly = hrv_data.get("hrv_weekly_avg")

        impact = _get_impact_type(result.factors.hrv_score)
        weight = weights.get('hrv', 0.25)
        contribution = result.factors.hrv_score * weight

        # Determine display value
        if hrv_last and hrv_weekly and hrv_weekly > 0:
            ratio = hrv_last / hrv_weekly
            if ratio >= 1.0:
                display = f"{((ratio - 1) * 100):.0f}% above baseline"
            else:
                display = f"{((1 - ratio) * 100):.0f}% below baseline"
        else:
            display = f"{result.factors.hrv_score:.0f}/100"

        explanation = _get_hrv_explanation(result.factors.hrv_score, hrv_data)

        factor_breakdown.append(ExplanationFactor(
            name="HRV Score",
            value=result.factors.hrv_score,
            display_value=display,
            impact=impact,
            weight=weight,
            contribution_points=contribution,
            explanation=explanation,
            threshold="Target: > 75 (at or above baseline)",
            baseline=hrv_weekly,
            data_sources=[
                DataSource(
                    source_type=DataSourceType.GARMIN_HRV,
                    source_name="Garmin HRV",
                    last_updated=target_date.isoformat(),
                    confidence=0.95,
                )
            ],
        ))

        data_points["hrv"] = {
            "last_night": hrv_last,
            "weekly_avg": hrv_weekly,
            "score": result.factors.hrv_score,
            "status": hrv_data.get("hrv_status"),
        }
        calculation_steps.append(
            f"HRV: {result.factors.hrv_score:.1f} x {weight:.2f} = {contribution:.1f}"
        )
        total_weight += weight
        weighted_sum += contribution

    # Sleep Factor
    if result.factors.sleep_score is not None:
        sleep_data = wellness_data.get("sleep", {}) if wellness_data else {}
        total_hours = sleep_data.get("total_sleep_hours", 0)
        deep_pct = sleep_data.get("deep_sleep_pct")

        impact = _get_impact_type(result.factors.sleep_score)
        weight = weights.get('sleep', 0.20)
        contribution = result.factors.sleep_score * weight

        if total_hours:
            display = f"{total_hours:.1f} hours ({result.factors.sleep_score:.0f}/100)"
        else:
            display = f"{result.factors.sleep_score:.0f}/100"

        explanation = _get_sleep_explanation(result.factors.sleep_score, sleep_data)

        factor_breakdown.append(ExplanationFactor(
            name="Sleep Quality",
            value=result.factors.sleep_score,
            display_value=display,
            impact=impact,
            weight=weight,
            contribution_points=contribution,
            explanation=explanation,
            threshold="Target: 8+ hours with 20%+ deep sleep",
            baseline=8.0,  # Target hours
            data_sources=[
                DataSource(
                    source_type=DataSourceType.GARMIN_SLEEP,
                    source_name="Garmin Sleep Tracking",
                    last_updated=target_date.isoformat(),
                    confidence=0.90,
                )
            ],
        ))

        data_points["sleep"] = {
            "total_hours": total_hours,
            "deep_sleep_pct": deep_pct,
            "score": result.factors.sleep_score,
        }
        calculation_steps.append(
            f"Sleep: {result.factors.sleep_score:.1f} x {weight:.2f} = {contribution:.1f}"
        )
        total_weight += weight
        weighted_sum += contribution

    # Body Battery Factor
    if result.factors.body_battery is not None:
        impact = _get_impact_type(result.factors.body_battery, 75, 40)
        weight = weights.get('body_battery', 0.15)
        contribution = result.factors.body_battery * weight

        explanation = _get_body_battery_explanation(result.factors.body_battery)

        factor_breakdown.append(ExplanationFactor(
            name="Body Battery",
            value=result.factors.body_battery,
            display_value=f"{result.factors.body_battery:.0f}%",
            impact=impact,
            weight=weight,
            contribution_points=contribution,
            explanation=explanation,
            threshold="Target: > 75%",
            baseline=75,
            data_sources=[
                DataSource(
                    source_type=DataSourceType.GARMIN_BODY_BATTERY,
                    source_name="Garmin Body Battery",
                    last_updated=target_date.isoformat(),
                    confidence=0.85,
                )
            ],
        ))

        data_points["body_battery"] = result.factors.body_battery
        calculation_steps.append(
            f"Body Battery: {result.factors.body_battery:.1f} x {weight:.2f} = {contribution:.1f}"
        )
        total_weight += weight
        weighted_sum += contribution

    # Stress Factor
    if result.factors.stress_score is not None:
        impact = _get_impact_type(result.factors.stress_score)
        weight = weights.get('stress', 0.10)
        contribution = result.factors.stress_score * weight

        stress_data = wellness_data.get("stress", {}) if wellness_data else {}
        avg_stress = stress_data.get("avg_stress_level", 0)

        explanation = _get_stress_explanation(result.factors.stress_score, avg_stress)

        factor_breakdown.append(ExplanationFactor(
            name="Stress Level",
            value=result.factors.stress_score,
            display_value=f"{100 - result.factors.stress_score:.0f} avg stress" if avg_stress else f"{result.factors.stress_score:.0f}/100",
            impact=impact,
            weight=weight,
            contribution_points=contribution,
            explanation=explanation,
            threshold="Target: < 40 average stress (inverted to score)",
            baseline=40,
            data_sources=[
                DataSource(
                    source_type=DataSourceType.GARMIN_STRESS,
                    source_name="Garmin Stress Tracking",
                    last_updated=target_date.isoformat(),
                    confidence=0.80,
                )
            ],
        ))

        data_points["stress"] = {
            "avg_level": avg_stress,
            "score": result.factors.stress_score,
        }
        calculation_steps.append(
            f"Stress: {result.factors.stress_score:.1f} x {weight:.2f} = {contribution:.1f}"
        )
        total_weight += weight
        weighted_sum += contribution

    # Training Load Factor
    if result.factors.training_load_score is not None:
        impact = _get_impact_type(result.factors.training_load_score)
        weight = weights.get('training_load', 0.20)
        contribution = result.factors.training_load_score * weight

        tsb = fitness_metrics.get("tsb") if fitness_metrics else None
        acwr = fitness_metrics.get("acwr") if fitness_metrics else None

        explanation = _get_training_load_explanation(
            result.factors.training_load_score, tsb, acwr
        )

        display_parts = []
        if tsb is not None:
            display_parts.append(f"TSB: {tsb:+.1f}")
        if acwr is not None:
            display_parts.append(f"ACWR: {acwr:.2f}")
        display = ", ".join(display_parts) if display_parts else f"{result.factors.training_load_score:.0f}/100"

        factor_breakdown.append(ExplanationFactor(
            name="Training Load Balance",
            value=result.factors.training_load_score,
            display_value=display,
            impact=impact,
            weight=weight,
            contribution_points=contribution,
            explanation=explanation,
            threshold="Optimal: TSB 0-20, ACWR 0.8-1.3",
            baseline={"tsb_target": 10, "acwr_target": 1.0},
            data_sources=[
                DataSource(
                    source_type=DataSourceType.CALCULATED_TSB,
                    source_name="Training Stress Balance",
                    confidence=0.90,
                ),
                DataSource(
                    source_type=DataSourceType.CALCULATED_ACWR,
                    source_name="Acute:Chronic Workload Ratio",
                    confidence=0.90,
                ),
            ],
        ))

        data_points["training_load"] = {
            "tsb": tsb,
            "acwr": acwr,
            "score": result.factors.training_load_score,
        }
        calculation_steps.append(
            f"Training Load: {result.factors.training_load_score:.1f} x {weight:.2f} = {contribution:.1f}"
        )
        total_weight += weight
        weighted_sum += contribution

    # Recovery Days Factor
    recovery_score = calculate_recovery_days_score(result.factors.recovery_days)
    weight = weights.get('recovery_days', 0.10)
    contribution = recovery_score * weight

    if result.factors.recovery_days == 0:
        impact = ImpactType.NEGATIVE
    elif result.factors.recovery_days >= 2:
        impact = ImpactType.POSITIVE
    else:
        impact = ImpactType.NEUTRAL

    explanation = _get_recovery_days_explanation(result.factors.recovery_days)

    factor_breakdown.append(ExplanationFactor(
        name="Recovery Time",
        value=result.factors.recovery_days,
        display_value=f"{result.factors.recovery_days} days since hard workout",
        impact=impact,
        weight=weight,
        contribution_points=contribution,
        explanation=explanation,
        threshold="Optimal: 2+ days between hard workouts",
        baseline=2,
        data_sources=[
            DataSource(
                source_type=DataSourceType.ACTIVITY_HISTORY,
                source_name="Recent Activities",
                confidence=1.0,
            )
        ],
    ))

    data_points["recovery_days"] = result.factors.recovery_days
    calculation_steps.append(
        f"Recovery: {recovery_score:.1f} x {weight:.2f} = {contribution:.1f}"
    )
    total_weight += weight
    weighted_sum += contribution

    # Build score calculation summary
    if total_weight > 0:
        final_score = weighted_sum / total_weight
        calculation_steps.append(f"---")
        calculation_steps.append(f"Total weighted: {weighted_sum:.1f} / {total_weight:.2f} = {final_score:.1f}")
    else:
        final_score = 50.0
        calculation_steps.append("No factors available, defaulting to 50")

    score_calculation = "\n".join(calculation_steps)

    # Find key driver (most impactful factor)
    if factor_breakdown:
        key_factor = max(factor_breakdown, key=lambda f: abs(f.contribution_points))
        key_driver = key_factor.name
    else:
        key_driver = None

    # Determine alternatives considered
    alternatives = []
    if result.zone == "green":
        alternatives = ["Quality training session", "Long run", "Tempo workout"]
    elif result.zone == "yellow":
        alternatives = ["Easy run", "Cross-training", "Light activity"]
    else:
        alternatives = ["Complete rest", "Light stretching", "Walk"]

    # Build the explained recommendation
    explained_rec = ExplainedRecommendation(
        recommendation=result.recommendation,
        confidence=_calculate_confidence(factor_breakdown, result.factors),
        confidence_explanation=_get_confidence_explanation(factor_breakdown),
        factors=factor_breakdown,
        data_points=data_points,
        calculation_summary=score_calculation,
        alternatives_considered=alternatives,
        key_driver=key_driver,
    )

    return ExplainedReadiness(
        date=target_date.isoformat(),
        overall_score=result.overall_score,
        zone=result.zone,
        recommendation=explained_rec,
        factor_breakdown=factor_breakdown,
        score_calculation=score_calculation,
        comparison_to_baseline=None,  # Could add 7-day comparison
        trend=None,  # Could add trend analysis
    )


def _get_hrv_explanation(score: float, hrv_data: Dict) -> str:
    """Generate human-readable HRV explanation."""
    hrv_last = hrv_data.get("hrv_last_night_avg")
    hrv_weekly = hrv_data.get("hrv_weekly_avg")

    if hrv_last and hrv_weekly and hrv_weekly > 0:
        ratio = hrv_last / hrv_weekly
        if ratio >= 1.2:
            return f"Excellent HRV ({hrv_last} ms) - significantly above your baseline of {hrv_weekly} ms. Your autonomic nervous system is well-recovered."
        elif ratio >= 1.0:
            return f"Good HRV ({hrv_last} ms) - at or above your baseline of {hrv_weekly} ms. Normal recovery state."
        elif ratio >= 0.85:
            return f"HRV slightly below baseline ({hrv_last} ms vs {hrv_weekly} ms avg). Some systemic stress may be present."
        else:
            return f"HRV significantly below baseline ({hrv_last} ms vs {hrv_weekly} ms avg). Consider prioritizing recovery."

    if score >= 80:
        return "Strong HRV indicating good autonomic recovery."
    elif score >= 60:
        return "Moderate HRV - adequate recovery state."
    else:
        return "Lower HRV suggests accumulated stress or incomplete recovery."


def _get_sleep_explanation(score: float, sleep_data: Dict) -> str:
    """Generate human-readable sleep explanation."""
    hours = sleep_data.get("total_sleep_hours", 0)
    deep_pct = sleep_data.get("deep_sleep_pct")

    parts = []

    if hours:
        if hours >= 8:
            parts.append(f"Excellent sleep duration ({hours:.1f} hours)")
        elif hours >= 7:
            parts.append(f"Good sleep duration ({hours:.1f} hours)")
        elif hours >= 6:
            parts.append(f"Adequate but below optimal sleep ({hours:.1f} hours)")
        else:
            parts.append(f"Insufficient sleep ({hours:.1f} hours) - recovery compromised")

    if deep_pct:
        if deep_pct >= 20:
            parts.append(f"with excellent deep sleep ({deep_pct:.0f}%)")
        elif deep_pct >= 15:
            parts.append(f"with adequate deep sleep ({deep_pct:.0f}%)")
        else:
            parts.append(f"but low deep sleep ({deep_pct:.0f}%) may limit recovery")

    return ". ".join(parts) + "." if parts else "Sleep data analyzed."


def _get_body_battery_explanation(score: float) -> str:
    """Generate human-readable Body Battery explanation."""
    if score >= 80:
        return f"High energy reserves ({score:.0f}%) - well-charged for demanding training."
    elif score >= 60:
        return f"Moderate energy ({score:.0f}%) - suitable for normal training."
    elif score >= 40:
        return f"Lower energy ({score:.0f}%) - consider easier training today."
    else:
        return f"Depleted energy reserves ({score:.0f}%) - prioritize rest and recovery."


def _get_stress_explanation(score: float, avg_stress: float) -> str:
    """Generate human-readable stress explanation."""
    # Score is inverted stress (high score = low stress)
    if score >= 70:
        return f"Low stress levels (avg {avg_stress:.0f}) - body is relaxed and ready for training."
    elif score >= 50:
        return f"Moderate stress levels (avg {avg_stress:.0f}) - normal baseline."
    else:
        return f"Elevated stress (avg {avg_stress:.0f}) - may impact recovery and performance."


def _get_training_load_explanation(score: float, tsb: Optional[float], acwr: Optional[float]) -> str:
    """Generate human-readable training load explanation."""
    parts = []

    if tsb is not None:
        if tsb > 20:
            parts.append(f"Very fresh (TSB: {tsb:+.1f}) - well-rested with positive form")
        elif tsb > 0:
            parts.append(f"Fresh (TSB: {tsb:+.1f}) - good balance of fitness and fatigue")
        elif tsb > -10:
            parts.append(f"Neutral fatigue (TSB: {tsb:+.1f}) - manageable training load")
        elif tsb > -25:
            parts.append(f"Accumulated fatigue (TSB: {tsb:+.1f}) - consider recovery")
        else:
            parts.append(f"High fatigue (TSB: {tsb:+.1f}) - recovery strongly recommended")

    if acwr is not None:
        if 0.8 <= acwr <= 1.3:
            parts.append(f"optimal training load ratio (ACWR: {acwr:.2f})")
        elif acwr < 0.8:
            parts.append(f"undertrained (ACWR: {acwr:.2f}) - can increase load")
        elif acwr <= 1.5:
            parts.append(f"elevated load ratio (ACWR: {acwr:.2f}) - caution advised")
        else:
            parts.append(f"high injury risk zone (ACWR: {acwr:.2f}) - reduce training")

    if parts:
        return parts[0].capitalize() + (", " + parts[1] if len(parts) > 1 else "") + "."
    return "Training load analyzed."


def _get_recovery_days_explanation(days: int) -> str:
    """Generate human-readable recovery days explanation."""
    if days == 0:
        return "Hard workout was yesterday - body still recovering from intense effort."
    elif days == 1:
        return "One day since hard workout - partial recovery. Easy day recommended."
    elif days == 2:
        return "Two days of recovery - good window for quality training."
    elif days >= 3:
        return f"{days} days since last hard effort - fully recovered and ready for intensity."
    return "Recovery status analyzed."


def _calculate_confidence(factors: List[ExplanationFactor], readiness_factors: ReadinessFactors) -> float:
    """Calculate confidence in the recommendation based on data availability."""
    available = readiness_factors.available_factors()

    # Base confidence on data availability
    if len(available) >= 5:
        confidence = 0.95
    elif len(available) >= 3:
        confidence = 0.85
    elif len(available) >= 1:
        confidence = 0.70
    else:
        confidence = 0.50

    # Adjust for data source confidence
    if factors:
        avg_source_confidence = sum(
            sum(ds.confidence for ds in f.data_sources) / max(len(f.data_sources), 1)
            for f in factors
        ) / len(factors)
        confidence *= avg_source_confidence

    return min(0.99, max(0.30, confidence))


def _get_confidence_explanation(factors: List[ExplanationFactor]) -> str:
    """Explain the confidence level."""
    if len(factors) >= 5:
        return "High confidence - comprehensive data from multiple sources available."
    elif len(factors) >= 3:
        return "Good confidence - key metrics available for assessment."
    elif len(factors) >= 1:
        return "Moderate confidence - limited data available, recommendation may be less precise."
    return "Low confidence - insufficient data for reliable assessment."
