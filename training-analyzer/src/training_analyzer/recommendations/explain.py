"""
Natural Language Explanation Generator

Produces human-readable explanations for recommendations.
"""

from typing import Dict, Any, Optional, List

from .readiness import ReadinessFactors, ReadinessResult
from .workout import WorkoutRecommendation, WorkoutType, get_workout_description


def explain_readiness(factors: ReadinessFactors, score: float) -> str:
    """
    Generate explanation of readiness score.

    Args:
        factors: Individual readiness factors
        score: Overall readiness score (0-100)

    Returns:
        Human-readable explanation
    """
    parts = []

    # Overall assessment
    if score >= 80:
        parts.append("Your body is well recovered and ready for training.")
    elif score >= 60:
        parts.append("You have moderate readiness for training today.")
    elif score >= 40:
        parts.append("Your readiness is below optimal - consider taking it easy.")
    else:
        parts.append("Your body signals indicate a need for recovery.")

    # Add factor-specific insights
    limiting_factors = []
    positive_factors = []

    # Sleep insights
    if factors.sleep_score is not None:
        if factors.sleep_score < 50:
            limiting_factors.append(
                f"Sleep quality was below optimal ({factors.sleep_score:.0f}/100)"
            )
        elif factors.sleep_score < 70:
            parts.append("Sleep was adequate but not ideal.")
        elif factors.sleep_score >= 85:
            positive_factors.append("excellent sleep")

    # HRV insights
    if factors.hrv_score is not None:
        if factors.hrv_score < 50:
            limiting_factors.append("HRV is significantly below your baseline")
        elif factors.hrv_score < 70:
            parts.append("HRV is slightly below baseline, suggesting some systemic stress.")
        elif factors.hrv_score >= 85:
            positive_factors.append("strong HRV indicating good recovery")

    # Body Battery insights
    if factors.body_battery is not None:
        if factors.body_battery < 40:
            limiting_factors.append(
                f"Body Battery is depleted ({factors.body_battery:.0f}%)"
            )
        elif factors.body_battery < 60:
            parts.append("Body Battery is at moderate levels.")
        elif factors.body_battery >= 80:
            positive_factors.append("high energy reserves")

    # Training load insights
    if factors.training_load_score is not None:
        if factors.training_load_score < 40:
            limiting_factors.append("training load is elevated relative to your fitness")
        elif factors.training_load_score < 60:
            parts.append("Training load is moderately high.")
        elif factors.training_load_score >= 80:
            positive_factors.append("balanced training load with good freshness")

    # Stress insights
    if factors.stress_score is not None:
        if factors.stress_score < 40:
            limiting_factors.append("stress levels have been high")
        elif factors.stress_score >= 75:
            positive_factors.append("low stress levels")

    # Recovery days
    if factors.recovery_days >= 3:
        positive_factors.append(f"{factors.recovery_days} days since your last hard effort")
    elif factors.recovery_days == 0:
        limiting_factors.append("you trained hard yesterday")

    # Build the explanation
    if positive_factors:
        parts.append(
            "Positive signs include: " + ", ".join(positive_factors) + "."
        )

    if limiting_factors:
        parts.append(
            "Factors to consider: " + ", ".join(limiting_factors) + "."
        )

    return " ".join(parts)


def explain_workout(
    recommendation: WorkoutRecommendation,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate detailed explanation of workout recommendation.

    Args:
        recommendation: The workout recommendation
        context: Optional context (readiness, fitness metrics, etc.)

    Returns:
        Human-readable explanation
    """
    workout_info = get_workout_description(recommendation.workout_type)
    parts = []

    # Main recommendation
    parts.append(f"Today's recommendation: {workout_info['name']}")
    parts.append("")

    # Why this workout
    parts.append(f"Why: {recommendation.reason}")
    parts.append("")

    # What to do
    parts.append("What to do:")
    parts.append(f"  - Duration: {recommendation.duration_min} minutes")
    parts.append(f"  - Intensity: {recommendation.intensity_description}")
    if recommendation.hr_zone_target:
        parts.append(f"  - Target: {recommendation.hr_zone_target}")
    parts.append("")

    # Purpose
    parts.append(f"Purpose: {workout_info['purpose']}")
    parts.append("")

    # Guidelines
    if workout_info.get("guidelines"):
        parts.append("Guidelines:")
        for guideline in workout_info["guidelines"]:
            parts.append(f"  - {guideline}")
        parts.append("")

    # Alternatives
    if recommendation.alternatives:
        parts.append("Alternatives if needed:")
        for alt in recommendation.alternatives:
            parts.append(f"  - {alt}")
        parts.append("")

    # Warnings
    if recommendation.warnings:
        parts.append("Notes:")
        for warning in recommendation.warnings:
            parts.append(f"  ! {warning}")

    return "\n".join(parts)


def generate_daily_narrative(
    readiness: ReadinessResult,
    recommendation: WorkoutRecommendation,
    fitness_status: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate a complete daily training narrative.

    This is the main output for the daily briefing - a cohesive
    paragraph that summarizes everything.

    Args:
        readiness: Readiness assessment
        recommendation: Workout recommendation
        fitness_status: Optional fitness metrics (CTL, ATL, TSB, ACWR)

    Returns:
        Narrative paragraph for daily briefing
    """
    parts = []

    # Opening based on readiness zone
    if readiness.zone == "green":
        if readiness.overall_score >= 85:
            parts.append("You're looking great today!")
        else:
            parts.append("You're in good shape for training today.")
    elif readiness.zone == "yellow":
        parts.append("Your body is showing some signs of fatigue today.")
    else:
        parts.append("Your recovery indicators suggest you need rest.")

    # Readiness summary
    parts.append(
        f"Your readiness score is {readiness.overall_score:.0f}/100."
    )

    # Key factor callouts
    factors = readiness.factors
    callouts = []

    if factors.sleep_score is not None:
        if factors.sleep_score < 60:
            callouts.append("sleep was below optimal")
        elif factors.sleep_score >= 85:
            callouts.append("you slept well")

    if factors.hrv_score is not None:
        if factors.hrv_score < 60:
            callouts.append("HRV is lower than usual")
        elif factors.hrv_score >= 85:
            callouts.append("your HRV is strong")

    if factors.body_battery is not None:
        if factors.body_battery < 50:
            callouts.append("your energy is low")
        elif factors.body_battery >= 80:
            callouts.append("your energy is high")

    if callouts:
        parts.append("Key observations: " + ", ".join(callouts) + ".")

    # Training status context
    if fitness_status:
        tsb = fitness_status.get("tsb")
        acwr = fitness_status.get("acwr")
        risk_zone = fitness_status.get("risk_zone")

        if risk_zone == "danger":
            parts.append(
                "Your training load ratio is in the danger zone - "
                "injury risk is elevated."
            )
        elif risk_zone == "caution":
            parts.append(
                "Your training load is running high relative to your baseline."
            )
        elif risk_zone == "undertrained":
            parts.append(
                "You've been under your usual training load recently."
            )

        if tsb is not None:
            if tsb > 15:
                parts.append("You're well-rested with positive form.")
            elif tsb < -20:
                parts.append("Training fatigue has accumulated.")

    # Workout recommendation
    workout_info = get_workout_description(recommendation.workout_type)
    if recommendation.workout_type == WorkoutType.REST:
        parts.append("Take a complete rest day to recover.")
    elif recommendation.workout_type == WorkoutType.RECOVERY:
        parts.append(
            f"A {recommendation.duration_min}-minute recovery activity "
            "would support your recovery without adding stress."
        )
    else:
        parts.append(
            f"I recommend a {recommendation.duration_min}-minute "
            f"{workout_info['name'].lower()}."
        )

    # Add reasoning
    if recommendation.workout_type.intensity_level >= 3:
        parts.append(f"You're ready for this quality work.")
    elif recommendation.workout_type.intensity_level <= 1:
        parts.append("Prioritize recovery today.")

    # Closing advice
    if recommendation.warnings:
        parts.append(recommendation.warnings[0])
    elif readiness.zone == "green" and recommendation.workout_type.intensity_level >= 3:
        parts.append("Enjoy your workout!")
    elif readiness.zone == "yellow":
        parts.append("Listen to your body and adjust as needed.")

    return " ".join(parts)


def format_training_status(
    ctl: float,
    atl: float,
    tsb: float,
    acwr: float,
    risk_zone: str,
) -> str:
    """
    Format training status metrics for display.

    Args:
        ctl: Chronic Training Load
        atl: Acute Training Load
        tsb: Training Stress Balance
        acwr: Acute:Chronic Workload Ratio
        risk_zone: Risk zone classification

    Returns:
        Formatted status string
    """
    lines = []

    lines.append("Training Status:")
    lines.append(f"  Fitness (CTL):  {ctl:.1f}")
    lines.append(f"  Fatigue (ATL):  {atl:.1f}")

    # TSB with interpretation
    if tsb > 15:
        tsb_status = "Fresh"
    elif tsb > 0:
        tsb_status = "Positive"
    elif tsb > -15:
        tsb_status = "Neutral"
    else:
        tsb_status = "Fatigued"
    lines.append(f"  Form (TSB):     {tsb:+.1f} ({tsb_status})")

    # ACWR with zone
    zone_display = {
        "optimal": "Optimal",
        "undertrained": "Low",
        "caution": "Caution",
        "danger": "Danger",
    }
    lines.append(f"  ACWR:           {acwr:.2f} ({zone_display.get(risk_zone, risk_zone)})")

    return "\n".join(lines)


def format_readiness_factors(factors: ReadinessFactors) -> str:
    """
    Format readiness factors for display.

    Args:
        factors: ReadinessFactors object

    Returns:
        Formatted factors string
    """
    lines = ["Readiness Factors:"]

    if factors.hrv_score is not None:
        lines.append(f"  HRV:            {factors.hrv_score:.0f}/100")

    if factors.sleep_score is not None:
        lines.append(f"  Sleep:          {factors.sleep_score:.0f}/100")

    if factors.body_battery is not None:
        lines.append(f"  Body Battery:   {factors.body_battery:.0f}/100")

    if factors.stress_score is not None:
        lines.append(f"  Stress:         {factors.stress_score:.0f}/100")

    if factors.training_load_score is not None:
        lines.append(f"  Training Load:  {factors.training_load_score:.0f}/100")

    lines.append(f"  Recovery Days:  {factors.recovery_days}")

    return "\n".join(lines)


def generate_weekly_narrative(
    weekly_stats: Dict[str, Any],
) -> str:
    """
    Generate narrative summary of the training week.

    Args:
        weekly_stats: Dictionary with weekly statistics

    Returns:
        Weekly summary narrative
    """
    parts = []

    # Opening
    total_load = weekly_stats.get("total_load", 0)
    target_load = weekly_stats.get("target_load", 0)
    workout_count = weekly_stats.get("workout_count", 0)

    parts.append(f"This week you completed {workout_count} workouts.")

    # Load summary
    if target_load > 0:
        load_pct = (total_load / target_load) * 100
        if load_pct >= 90:
            parts.append(f"You hit {load_pct:.0f}% of your target training load.")
        elif load_pct >= 70:
            parts.append(
                f"Your training load was {load_pct:.0f}% of target - "
                "a solid week."
            )
        else:
            parts.append(
                f"Training load was lighter than planned at {load_pct:.0f}% of target."
            )
    else:
        parts.append(f"Total training load: {total_load:.0f}.")

    # CTL change
    ctl_change = weekly_stats.get("ctl_change", 0)
    if ctl_change > 2:
        parts.append(
            f"Your fitness (CTL) improved by {ctl_change:.1f} points."
        )
    elif ctl_change < -2:
        parts.append(
            f"Your fitness (CTL) decreased by {abs(ctl_change):.1f} points - "
            "likely due to reduced training."
        )
    else:
        parts.append("Your fitness level remained stable.")

    # Distribution
    hard_days = weekly_stats.get("hard_days", 0)
    easy_days = weekly_stats.get("easy_days", 0)
    rest_days = weekly_stats.get("rest_days", 0)

    if hard_days > 0:
        parts.append(
            f"You had {hard_days} hard sessions, {easy_days} easy days, "
            f"and {rest_days} rest days."
        )

    # Trend
    avg_readiness = weekly_stats.get("avg_readiness", 0)
    if avg_readiness >= 70:
        parts.append("Overall, you recovered well throughout the week.")
    elif avg_readiness >= 50:
        parts.append("Recovery was moderate - watch for accumulated fatigue.")
    else:
        parts.append(
            "Your average readiness was low this week - "
            "consider extra recovery."
        )

    return " ".join(parts)
