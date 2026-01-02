"""
Recovery Module Service for sleep debt, HRV trends, and post-workout recovery estimation.

This module provides enhanced recovery analysis including:
1. 7-day rolling sleep debt tracking
2. HRV trend analysis with coefficient of variation
3. Post-workout recovery time estimation
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import statistics
import logging

from ..models.recovery import (
    SleepRecord,
    SleepDebtAnalysis,
    SleepDebtImpact,
    HRVRecord,
    HRVTrendAnalysis,
    HRVTrendDirection,
    RecoveryTimeEstimate,
    RecoveryModuleData,
    RecoveryStatus,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Sleep Debt Calculations
# =============================================================================

def calculate_sleep_debt(
    sleep_records: List[SleepRecord],
    target_hours: float = 8.0,
    window_days: int = 7,
) -> SleepDebtAnalysis:
    """
    Calculate 7-day rolling sleep debt.

    Sleep debt accumulates when actual sleep is less than target.
    Research suggests recovery from sleep debt requires more than
    1:1 compensation.

    Args:
        sleep_records: List of sleep records, newest last
        target_hours: Target sleep hours per night (default 8.0)
        window_days: Number of days to analyze (default 7)

    Returns:
        SleepDebtAnalysis with debt calculation and recommendations
    """
    if not sleep_records:
        return SleepDebtAnalysis(
            total_debt_hours=0.0,
            daily_debt_breakdown=[],
            target_hours=target_hours,
            window_days=window_days,
            average_sleep_hours=0.0,
            impact_level=SleepDebtImpact.MINIMAL,
            recommendation="No sleep data available. Connect your wearable to track sleep.",
            trend="insufficient_data",
        )

    # Get the most recent records within the window
    recent_records = sleep_records[-window_days:] if len(sleep_records) >= window_days else sleep_records

    # Calculate daily debt (capped at 0, no "sleep surplus" carrying over)
    daily_debt = []
    for record in recent_records:
        debt = max(0, target_hours - record.duration_hours)
        daily_debt.append(round(debt, 2))

    total_debt = sum(daily_debt)
    average_sleep = sum(r.duration_hours for r in recent_records) / len(recent_records)

    # Calculate sleep consistency (variance in sleep times)
    sleep_consistency = _calculate_sleep_consistency(recent_records)

    # Calculate average quality if available
    quality_scores = [r.quality_score for r in recent_records if r.quality_score is not None]
    average_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None

    # Determine impact level
    if total_debt < 3:
        impact_level = SleepDebtImpact.MINIMAL
    elif total_debt < 7:
        impact_level = SleepDebtImpact.MODERATE
    elif total_debt < 14:
        impact_level = SleepDebtImpact.SIGNIFICANT
    else:
        impact_level = SleepDebtImpact.CRITICAL

    # Generate recommendation
    recommendation = _get_sleep_recommendation(impact_level, total_debt, average_sleep, target_hours)

    # Calculate trend (compare recent half to older half)
    trend = _calculate_sleep_trend(daily_debt)

    return SleepDebtAnalysis(
        total_debt_hours=round(total_debt, 1),
        daily_debt_breakdown=daily_debt,
        target_hours=target_hours,
        window_days=window_days,
        average_sleep_hours=round(average_sleep, 1),
        impact_level=impact_level,
        recommendation=recommendation,
        trend=trend,
        sleep_consistency_score=round(sleep_consistency, 1) if sleep_consistency else None,
        average_quality=round(average_quality, 1) if average_quality else None,
    )


def _calculate_sleep_consistency(records: List[SleepRecord]) -> Optional[float]:
    """
    Calculate sleep consistency score (0-100).

    Higher score = more consistent sleep schedule.
    Based on variance of bedtimes and sleep durations.
    """
    if len(records) < 3:
        return None

    durations = [r.duration_hours for r in records]

    # Calculate coefficient of variation for duration
    mean_duration = statistics.mean(durations)
    if mean_duration == 0:
        return None

    try:
        stdev_duration = statistics.stdev(durations)
        cv = (stdev_duration / mean_duration) * 100

        # Convert CV to a 0-100 score (lower CV = higher consistency)
        # CV of 0% = 100 score, CV of 50%+ = 0 score
        consistency_score = max(0, 100 - (cv * 2))
        return consistency_score
    except statistics.StatisticsError:
        return None


def _calculate_sleep_trend(daily_debt: List[float]) -> str:
    """Determine if sleep is improving, stable, or declining."""
    if len(daily_debt) < 4:
        return "insufficient_data"

    mid = len(daily_debt) // 2
    first_half_avg = sum(daily_debt[:mid]) / mid
    second_half_avg = sum(daily_debt[mid:]) / (len(daily_debt) - mid)

    diff = first_half_avg - second_half_avg

    if diff > 0.5:  # First half had more debt = improving
        return "improving"
    elif diff < -0.5:  # Second half has more debt = declining
        return "declining"
    else:
        return "stable"


def _get_sleep_recommendation(
    impact: SleepDebtImpact,
    total_debt: float,
    average_sleep: float,
    target: float,
) -> str:
    """Generate personalized sleep recommendation based on debt level."""
    if impact == SleepDebtImpact.MINIMAL:
        return (
            f"Your sleep is well-managed! Averaging {average_sleep:.1f}h per night "
            f"meets your {target:.1f}h target. Keep up the consistent sleep schedule."
        )
    elif impact == SleepDebtImpact.MODERATE:
        extra_needed = (total_debt / 7) * 1.5  # 1.5x recovery factor
        return (
            f"You have accumulated {total_debt:.1f}h of sleep debt. "
            f"Consider adding {extra_needed:.1f}h extra sleep over the next week, "
            f"or take a 20-30 minute nap on rest days."
        )
    elif impact == SleepDebtImpact.SIGNIFICANT:
        return (
            f"Significant sleep debt of {total_debt:.1f}h may affect recovery and performance. "
            f"Prioritize 8-9 hours of sleep each night this week. "
            f"Consider reducing training intensity until debt decreases."
        )
    else:  # CRITICAL
        return (
            f"Critical sleep debt of {total_debt:.1f}h detected. This significantly impacts "
            f"recovery, immune function, and injury risk. "
            f"Prioritize sleep above training - consider extra rest days."
        )


# =============================================================================
# HRV Trend Calculations
# =============================================================================

def calculate_hrv_trend(
    hrv_records: List[HRVRecord],
) -> HRVTrendAnalysis:
    """
    Calculate HRV trend analysis with rolling averages and coefficient of variation.

    The coefficient of variation (CV) is more stable than raw HRV values and
    helps identify meaningful changes vs. normal daily variation.

    Args:
        hrv_records: List of HRV records, newest last

    Returns:
        HRVTrendAnalysis with trend direction and interpretations
    """
    if not hrv_records:
        return HRVTrendAnalysis(
            trend_direction=HRVTrendDirection.INSUFFICIENT_DATA,
            interpretation="No HRV data available. Connect your wearable to track HRV.",
        )

    # Sort by date to ensure correct order
    sorted_records = sorted(hrv_records, key=lambda r: r.date)

    # Extract RMSSD values
    all_rmssd = [(r.date, r.rmssd) for r in sorted_records if r.rmssd is not None]

    if len(all_rmssd) < 3:
        return HRVTrendAnalysis(
            current_rmssd=all_rmssd[-1][1] if all_rmssd else None,
            current_date=all_rmssd[-1][0] if all_rmssd else None,
            data_points_7d=len(all_rmssd),
            data_points_30d=len(all_rmssd),
            trend_direction=HRVTrendDirection.INSUFFICIENT_DATA,
            interpretation="Need at least 3 HRV measurements for trend analysis.",
        )

    # Get current value
    current_date, current_rmssd = all_rmssd[-1]

    # Calculate rolling averages
    today = date.today()
    rmssd_7d = [v for d, v in all_rmssd if (today - d).days <= 7]
    rmssd_30d = [v for d, v in all_rmssd if (today - d).days <= 30]

    rolling_avg_7d = statistics.mean(rmssd_7d) if rmssd_7d else None
    rolling_avg_30d = statistics.mean(rmssd_30d) if rmssd_30d else None

    # Calculate coefficient of variation
    cv_7d = _calculate_cv(rmssd_7d) if len(rmssd_7d) >= 3 else None
    cv_30d = _calculate_cv(rmssd_30d) if len(rmssd_30d) >= 5 else None

    # Calculate baseline (top 25th percentile of last 30 days)
    baseline_rmssd = _calculate_hrv_baseline(rmssd_30d) if len(rmssd_30d) >= 7 else None

    # Calculate relative to baseline
    relative_to_baseline = None
    if baseline_rmssd and baseline_rmssd > 0:
        relative_to_baseline = (current_rmssd / baseline_rmssd) * 100

    # LF/HF ratio analysis
    lf_hf_values = [r.lf_hf_ratio for r in sorted_records if r.lf_hf_ratio is not None]
    current_lf_hf = lf_hf_values[-1] if lf_hf_values else None
    avg_lf_hf_7d = None
    if lf_hf_values:
        recent_lf_hf = lf_hf_values[-7:] if len(lf_hf_values) >= 7 else lf_hf_values
        avg_lf_hf_7d = statistics.mean(recent_lf_hf)

    # Determine trend direction
    trend_direction, trend_percentage = _determine_hrv_trend(
        rmssd_7d, rmssd_30d, baseline_rmssd, current_rmssd
    )

    # Generate interpretation
    interpretation = _interpret_hrv_status(
        current_rmssd, rolling_avg_7d, baseline_rmssd, relative_to_baseline, trend_direction
    )

    return HRVTrendAnalysis(
        current_rmssd=round(current_rmssd, 1),
        current_date=current_date,
        rolling_average_7d=round(rolling_avg_7d, 1) if rolling_avg_7d else None,
        rolling_average_30d=round(rolling_avg_30d, 1) if rolling_avg_30d else None,
        cv_7d=round(cv_7d, 1) if cv_7d else None,
        cv_30d=round(cv_30d, 1) if cv_30d else None,
        current_lf_hf_ratio=round(current_lf_hf, 2) if current_lf_hf else None,
        average_lf_hf_ratio_7d=round(avg_lf_hf_7d, 2) if avg_lf_hf_7d else None,
        trend_direction=trend_direction,
        trend_percentage=round(trend_percentage, 1) if trend_percentage else None,
        baseline_rmssd=round(baseline_rmssd, 1) if baseline_rmssd else None,
        relative_to_baseline=round(relative_to_baseline, 1) if relative_to_baseline else None,
        interpretation=interpretation,
        data_points_7d=len(rmssd_7d),
        data_points_30d=len(rmssd_30d),
    )


def _calculate_cv(values: List[float]) -> Optional[float]:
    """
    Calculate Coefficient of Variation (CV%).

    CV% = (std_dev / mean) * 100

    Lower CV indicates more stable HRV, which is generally positive.
    Typical CV for HRV is 5-15%.
    """
    if len(values) < 2:
        return None

    mean_val = statistics.mean(values)
    if mean_val == 0:
        return None

    try:
        stdev_val = statistics.stdev(values)
        return (stdev_val / mean_val) * 100
    except statistics.StatisticsError:
        return None


def _calculate_hrv_baseline(rmssd_values: List[float]) -> Optional[float]:
    """
    Calculate HRV baseline as top 25th percentile.

    This represents the athlete's "recovered" HRV state.
    """
    if len(rmssd_values) < 4:
        return None

    sorted_values = sorted(rmssd_values, reverse=True)
    top_quartile_count = max(1, len(sorted_values) // 4)
    top_quartile = sorted_values[:top_quartile_count]

    return statistics.mean(top_quartile)


def _determine_hrv_trend(
    rmssd_7d: List[float],
    rmssd_30d: List[float],
    baseline: Optional[float],
    current: float,
) -> Tuple[HRVTrendDirection, Optional[float]]:
    """Determine HRV trend direction and percentage change."""
    if len(rmssd_7d) < 3:
        return HRVTrendDirection.INSUFFICIENT_DATA, None

    avg_7d = statistics.mean(rmssd_7d)
    avg_30d = statistics.mean(rmssd_30d) if len(rmssd_30d) >= 7 else avg_7d

    if avg_30d == 0:
        return HRVTrendDirection.STABLE, None

    # Calculate percentage change (7d avg vs 30d avg)
    percentage_change = ((avg_7d - avg_30d) / avg_30d) * 100

    if percentage_change > 5:
        return HRVTrendDirection.IMPROVING, percentage_change
    elif percentage_change < -5:
        return HRVTrendDirection.DECLINING, percentage_change
    else:
        return HRVTrendDirection.STABLE, percentage_change


def _interpret_hrv_status(
    current: float,
    avg_7d: Optional[float],
    baseline: Optional[float],
    relative_to_baseline: Optional[float],
    trend: HRVTrendDirection,
) -> str:
    """Generate human-readable HRV interpretation."""
    parts = []

    if relative_to_baseline is not None:
        if relative_to_baseline >= 100:
            parts.append(
                f"Your HRV ({current:.0f}ms) is at or above your recovered baseline - "
                f"excellent recovery status."
            )
        elif relative_to_baseline >= 85:
            parts.append(
                f"Your HRV ({current:.0f}ms) is {100 - relative_to_baseline:.0f}% below baseline - "
                f"good recovery but some accumulated fatigue."
            )
        elif relative_to_baseline >= 70:
            parts.append(
                f"Your HRV ({current:.0f}ms) is {100 - relative_to_baseline:.0f}% below baseline - "
                f"moderate fatigue detected. Consider easier training."
            )
        else:
            parts.append(
                f"Your HRV ({current:.0f}ms) is {100 - relative_to_baseline:.0f}% below baseline - "
                f"significant fatigue. Prioritize recovery."
            )
    elif current:
        parts.append(f"Current HRV: {current:.0f}ms.")

    if trend == HRVTrendDirection.IMPROVING:
        parts.append("Your HRV trend is improving over the past week.")
    elif trend == HRVTrendDirection.DECLINING:
        parts.append("Your HRV trend is declining - monitor recovery closely.")
    elif trend == HRVTrendDirection.STABLE:
        parts.append("Your HRV is stable.")

    return " ".join(parts)


# =============================================================================
# Recovery Time Estimation
# =============================================================================

def estimate_recovery_time(
    workout_intensity: float,  # 0-100
    workout_duration_min: float,
    workout_hrss: Optional[float] = None,
    current_tsb: Optional[float] = None,
    sleep_debt_hours: Optional[float] = None,
    hrv_relative_to_baseline: Optional[float] = None,
    vo2max: Optional[float] = None,
) -> RecoveryTimeEstimate:
    """
    Estimate post-workout recovery time based on multiple factors.

    This combines:
    - Workout intensity and duration
    - Current fatigue state (TSB)
    - Sleep debt
    - HRV status
    - Fitness level (VO2max)

    Args:
        workout_intensity: Intensity score 0-100
        workout_duration_min: Duration in minutes
        workout_hrss: Heart Rate Stress Score if available
        current_tsb: Training Stress Balance (-30 to +30 typical)
        sleep_debt_hours: Accumulated sleep debt
        hrv_relative_to_baseline: HRV as percentage of baseline (100 = at baseline)
        vo2max: VO2max for fitness-based adjustment

    Returns:
        RecoveryTimeEstimate with hours and recommendations
    """
    factors = {}

    # Base recovery time from intensity and duration
    base_hours = _calculate_base_recovery(workout_intensity, workout_duration_min, workout_hrss)
    factors["base"] = base_hours

    # Adjustments
    intensity_impact = 0.0
    sleep_impact = 0.0
    hrv_impact = 0.0
    fatigue_impact = 0.0

    # 1. Intensity adjustment
    if workout_intensity > 80:
        intensity_impact = base_hours * 0.3  # +30% for very hard
    elif workout_intensity > 60:
        intensity_impact = base_hours * 0.15  # +15% for hard
    factors["intensity"] = intensity_impact

    # 2. Sleep debt adjustment
    if sleep_debt_hours:
        if sleep_debt_hours > 10:
            sleep_impact = base_hours * 0.4  # +40% for severe debt
        elif sleep_debt_hours > 5:
            sleep_impact = base_hours * 0.2  # +20% for moderate debt
        elif sleep_debt_hours > 2:
            sleep_impact = base_hours * 0.1  # +10% for mild debt
    factors["sleep_debt"] = sleep_impact

    # 3. HRV status adjustment
    if hrv_relative_to_baseline:
        if hrv_relative_to_baseline < 70:
            hrv_impact = base_hours * 0.35  # +35% for suppressed HRV
        elif hrv_relative_to_baseline < 85:
            hrv_impact = base_hours * 0.15  # +15% for below baseline
        elif hrv_relative_to_baseline > 105:
            hrv_impact = -base_hours * 0.1  # -10% for elevated HRV
    factors["hrv"] = hrv_impact

    # 4. Current fatigue (TSB) adjustment
    if current_tsb is not None:
        if current_tsb < -20:
            fatigue_impact = base_hours * 0.3  # +30% for very tired
        elif current_tsb < -10:
            fatigue_impact = base_hours * 0.15  # +15% for tired
        elif current_tsb > 10:
            fatigue_impact = -base_hours * 0.1  # -10% for fresh
    factors["fatigue"] = fatigue_impact

    # 5. VO2max adjustment (fitter athletes recover faster)
    vo2max_factor = 1.0
    if vo2max:
        if vo2max > 60:
            vo2max_factor = 0.80  # 20% faster
        elif vo2max > 55:
            vo2max_factor = 0.85  # 15% faster
        elif vo2max > 50:
            vo2max_factor = 0.90  # 10% faster
        elif vo2max < 40:
            vo2max_factor = 1.10  # 10% slower
    factors["vo2max_factor"] = vo2max_factor

    # Calculate total recovery time
    total_hours = (base_hours + intensity_impact + sleep_impact + hrv_impact + fatigue_impact) * vo2max_factor
    total_hours = max(12, min(96, total_hours))  # Clamp to 12-96 hours

    # Hours until "fresh" for hard training (add 50%)
    hours_until_fresh = total_hours * 1.5

    now = datetime.utcnow()
    next_easy = now + timedelta(hours=total_hours)
    next_hard = now + timedelta(hours=hours_until_fresh)

    # Generate recovery activities based on estimated time
    activities = _get_recovery_activities(total_hours)

    # Sleep recommendation
    sleep_rec = 8.0
    if total_hours > 48:
        sleep_rec = 9.0
    elif total_hours < 24:
        sleep_rec = 7.5

    return RecoveryTimeEstimate(
        hours_until_recovered=round(total_hours, 1),
        hours_until_fresh=round(hours_until_fresh, 1),
        next_easy_workout_at=next_easy,
        next_hard_workout_at=next_hard,
        factors=factors,
        workout_intensity_impact=round(intensity_impact, 1),
        sleep_debt_impact=round(sleep_impact, 1),
        hrv_status_impact=round(hrv_impact, 1),
        current_fatigue_impact=round(fatigue_impact, 1),
        recovery_activities=activities,
        sleep_recommendation_hours=sleep_rec,
    )


def _calculate_base_recovery(
    intensity: float,
    duration_min: float,
    hrss: Optional[float] = None,
) -> float:
    """Calculate base recovery hours from workout characteristics."""
    # If HRSS is available, use it (more accurate)
    if hrss:
        if hrss > 150:
            return 48
        elif hrss > 100:
            return 36
        elif hrss > 60:
            return 24
        else:
            return 18

    # Otherwise estimate from intensity and duration
    # Intensity 0-100, Duration in minutes
    intensity_factor = intensity / 100
    duration_factor = min(1.5, duration_min / 60)  # Cap at 1.5 for 90+ min

    # Base formula: light workouts need ~12h, hard long workouts need ~48h
    base = 12 + (intensity_factor * duration_factor * 36)

    return base


def _get_recovery_activities(hours: float) -> List[str]:
    """Get recommended recovery activities based on recovery time needed."""
    if hours > 60:
        return [
            "Complete rest today",
            "Light stretching or yoga",
            "Extra sleep (9+ hours)",
            "Hydration focus",
            "Anti-inflammatory nutrition",
        ]
    elif hours > 36:
        return [
            "Active recovery: easy walk or swim",
            "Foam rolling and mobility work",
            "Adequate sleep (8+ hours)",
            "Protein-rich meals",
        ]
    elif hours > 24:
        return [
            "Light cross-training",
            "Stretching routine",
            "Normal sleep schedule",
            "Stay hydrated",
        ]
    else:
        return [
            "Normal training can resume soon",
            "Maintain good sleep habits",
            "Light movement encouraged",
        ]


# =============================================================================
# Combined Recovery Module
# =============================================================================

def get_recovery_module_data(
    sleep_records: Optional[List[SleepRecord]] = None,
    hrv_records: Optional[List[HRVRecord]] = None,
    last_workout: Optional[Dict[str, Any]] = None,
    current_tsb: Optional[float] = None,
    vo2max: Optional[float] = None,
    target_sleep_hours: float = 8.0,
) -> RecoveryModuleData:
    """
    Get complete recovery module data combining all components.

    Args:
        sleep_records: List of sleep records
        hrv_records: List of HRV records
        last_workout: Last workout data (intensity, duration, hrss)
        current_tsb: Current Training Stress Balance
        vo2max: VO2max value

    Returns:
        RecoveryModuleData with all recovery components
    """
    # Calculate sleep debt
    sleep_debt = None
    if sleep_records:
        sleep_debt = calculate_sleep_debt(sleep_records, target_hours=target_sleep_hours)

    # Calculate HRV trend
    hrv_trend = None
    if hrv_records:
        hrv_trend = calculate_hrv_trend(hrv_records)

    # Calculate recovery time estimate
    recovery_time = None
    if last_workout:
        recovery_time = estimate_recovery_time(
            workout_intensity=last_workout.get("intensity", 50),
            workout_duration_min=last_workout.get("duration_min", 30),
            workout_hrss=last_workout.get("hrss"),
            current_tsb=current_tsb,
            sleep_debt_hours=sleep_debt.total_debt_hours if sleep_debt else None,
            hrv_relative_to_baseline=hrv_trend.relative_to_baseline if hrv_trend else None,
            vo2max=vo2max,
        )

    # Calculate overall recovery status and score
    overall_status, recovery_score = _calculate_overall_recovery(
        sleep_debt, hrv_trend, current_tsb
    )

    # Generate summary and recommendations
    summary_message = _generate_recovery_summary(overall_status, sleep_debt, hrv_trend)
    recommendations = _generate_recovery_recommendations(overall_status, sleep_debt, hrv_trend)

    # Calculate data freshness
    data_freshness = _calculate_data_freshness(sleep_records, hrv_records)

    return RecoveryModuleData(
        sleep_debt=sleep_debt,
        hrv_trend=hrv_trend,
        recovery_time=recovery_time,
        overall_recovery_status=overall_status,
        recovery_score=recovery_score,
        summary_message=summary_message,
        recommendations=recommendations,
        generated_at=datetime.utcnow(),
        data_freshness_hours=data_freshness,
    )


def _calculate_overall_recovery(
    sleep_debt: Optional[SleepDebtAnalysis],
    hrv_trend: Optional[HRVTrendAnalysis],
    current_tsb: Optional[float],
) -> Tuple[RecoveryStatus, float]:
    """Calculate overall recovery status and score."""
    score = 50.0  # Base score

    # Sleep debt factor (0-30 points)
    if sleep_debt:
        if sleep_debt.impact_level == SleepDebtImpact.MINIMAL:
            score += 30
        elif sleep_debt.impact_level == SleepDebtImpact.MODERATE:
            score += 15
        elif sleep_debt.impact_level == SleepDebtImpact.SIGNIFICANT:
            score -= 10
        else:  # CRITICAL
            score -= 25

    # HRV factor (0-30 points)
    if hrv_trend and hrv_trend.relative_to_baseline:
        rel = hrv_trend.relative_to_baseline
        if rel >= 100:
            score += 30
        elif rel >= 85:
            score += 15
        elif rel >= 70:
            score -= 5
        else:
            score -= 20

    # TSB factor (0-20 points)
    if current_tsb is not None:
        if current_tsb > 10:
            score += 20
        elif current_tsb > 0:
            score += 10
        elif current_tsb > -10:
            score -= 5
        elif current_tsb > -20:
            score -= 15
        else:
            score -= 25

    # Clamp score to 0-100
    score = max(0, min(100, score))

    # Determine status from score
    if score >= 80:
        status = RecoveryStatus.EXCELLENT
    elif score >= 60:
        status = RecoveryStatus.GOOD
    elif score >= 40:
        status = RecoveryStatus.MODERATE
    elif score >= 20:
        status = RecoveryStatus.POOR
    else:
        status = RecoveryStatus.CRITICAL

    return status, round(score, 1)


def _generate_recovery_summary(
    status: RecoveryStatus,
    sleep_debt: Optional[SleepDebtAnalysis],
    hrv_trend: Optional[HRVTrendAnalysis],
) -> str:
    """Generate a human-readable recovery summary."""
    if status == RecoveryStatus.EXCELLENT:
        return (
            "Your recovery metrics look excellent! You're well-rested and your body "
            "is showing strong adaptation signals. Great time for quality training."
        )
    elif status == RecoveryStatus.GOOD:
        return (
            "Your recovery is good. You have the capacity for normal training, "
            "though you might want to monitor how you feel during harder sessions."
        )
    elif status == RecoveryStatus.MODERATE:
        return (
            "Your recovery is moderate. Consider easier training today and focus on "
            "getting quality sleep tonight. Your body is adapting but needs support."
        )
    elif status == RecoveryStatus.POOR:
        return (
            "Your recovery indicators suggest accumulated fatigue. Prioritize rest "
            "and recovery activities. Training through this may increase injury risk."
        )
    else:  # CRITICAL
        return (
            "Your body is showing signs of significant fatigue. Rest is not optional - "
            "it's essential. Take at least one full rest day and focus on sleep."
        )


def _generate_recovery_recommendations(
    status: RecoveryStatus,
    sleep_debt: Optional[SleepDebtAnalysis],
    hrv_trend: Optional[HRVTrendAnalysis],
) -> List[str]:
    """Generate actionable recovery recommendations."""
    recommendations = []

    # Sleep-based recommendations
    if sleep_debt:
        if sleep_debt.impact_level in [SleepDebtImpact.SIGNIFICANT, SleepDebtImpact.CRITICAL]:
            recommendations.append("Prioritize sleep: aim for 8-9 hours for the next few nights")
        elif sleep_debt.impact_level == SleepDebtImpact.MODERATE:
            recommendations.append("Consider an earlier bedtime to reduce sleep debt")

    # HRV-based recommendations
    if hrv_trend and hrv_trend.relative_to_baseline:
        if hrv_trend.relative_to_baseline < 70:
            recommendations.append("Your HRV is suppressed - focus on stress reduction and recovery")
        elif hrv_trend.trend_direction == HRVTrendDirection.DECLINING:
            recommendations.append("Monitor your HRV trend closely over the next few days")

    # Status-based recommendations
    if status == RecoveryStatus.CRITICAL:
        recommendations.insert(0, "Take a complete rest day today")
        recommendations.append("Consider a short nap (20-30 min) if possible")
    elif status == RecoveryStatus.POOR:
        recommendations.insert(0, "Keep today's training easy - active recovery only")
    elif status == RecoveryStatus.MODERATE:
        recommendations.append("Listen to your body during training and don't push through fatigue")

    # General good practices
    if status in [RecoveryStatus.EXCELLENT, RecoveryStatus.GOOD]:
        if len(recommendations) == 0:
            recommendations.append("Maintain your current sleep and recovery practices")
            recommendations.append("Your body is responding well to training load")

    return recommendations[:5]  # Return top 5 recommendations


def _calculate_data_freshness(
    sleep_records: Optional[List[SleepRecord]],
    hrv_records: Optional[List[HRVRecord]],
) -> Optional[float]:
    """Calculate age of most recent data in hours."""
    most_recent = None

    if sleep_records:
        latest_sleep = max(r.date for r in sleep_records)
        sleep_datetime = datetime.combine(latest_sleep, datetime.min.time())
        if most_recent is None or sleep_datetime > most_recent:
            most_recent = sleep_datetime

    if hrv_records:
        latest_hrv = max(r.date for r in hrv_records)
        hrv_datetime = datetime.combine(latest_hrv, datetime.min.time())
        if most_recent is None or hrv_datetime > most_recent:
            most_recent = hrv_datetime

    if most_recent:
        age = datetime.utcnow() - most_recent
        return round(age.total_seconds() / 3600, 1)

    return None


# =============================================================================
# Singleton instance
# =============================================================================

_recovery_service: Optional["RecoveryModuleService"] = None


class RecoveryModuleService:
    """Service class for recovery module operations."""

    def __init__(self):
        """Initialize the recovery module service."""
        self._sleep_cache: Dict[str, List[SleepRecord]] = {}
        self._hrv_cache: Dict[str, List[HRVRecord]] = {}

    def get_sleep_debt(
        self,
        sleep_records: List[SleepRecord],
        target_hours: float = 8.0,
        window_days: int = 7,
    ) -> SleepDebtAnalysis:
        """Calculate sleep debt from records."""
        return calculate_sleep_debt(sleep_records, target_hours, window_days)

    def get_hrv_trend(
        self,
        hrv_records: List[HRVRecord],
    ) -> HRVTrendAnalysis:
        """Calculate HRV trend from records."""
        return calculate_hrv_trend(hrv_records)

    def get_recovery_time(
        self,
        workout_intensity: float,
        workout_duration_min: float,
        workout_hrss: Optional[float] = None,
        current_tsb: Optional[float] = None,
        sleep_debt_hours: Optional[float] = None,
        hrv_relative_to_baseline: Optional[float] = None,
        vo2max: Optional[float] = None,
    ) -> RecoveryTimeEstimate:
        """Estimate recovery time for a workout."""
        return estimate_recovery_time(
            workout_intensity=workout_intensity,
            workout_duration_min=workout_duration_min,
            workout_hrss=workout_hrss,
            current_tsb=current_tsb,
            sleep_debt_hours=sleep_debt_hours,
            hrv_relative_to_baseline=hrv_relative_to_baseline,
            vo2max=vo2max,
        )

    def get_full_recovery_data(
        self,
        sleep_records: Optional[List[SleepRecord]] = None,
        hrv_records: Optional[List[HRVRecord]] = None,
        last_workout: Optional[Dict[str, Any]] = None,
        current_tsb: Optional[float] = None,
        vo2max: Optional[float] = None,
        target_sleep_hours: float = 8.0,
    ) -> RecoveryModuleData:
        """Get complete recovery module data."""
        return get_recovery_module_data(
            sleep_records=sleep_records,
            hrv_records=hrv_records,
            last_workout=last_workout,
            current_tsb=current_tsb,
            vo2max=vo2max,
            target_sleep_hours=target_sleep_hours,
        )


def get_recovery_service() -> RecoveryModuleService:
    """Get the recovery module service singleton."""
    global _recovery_service
    if _recovery_service is None:
        _recovery_service = RecoveryModuleService()
    return _recovery_service
