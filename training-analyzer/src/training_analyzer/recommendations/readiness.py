"""
Readiness Score Calculation

Combines multiple factors into a 0-100 readiness score:
- Recovery data (HRV, sleep, Body Battery) from wellness
- Training load balance (TSB, ACWR)
- Recent training pattern
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import date, datetime


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
