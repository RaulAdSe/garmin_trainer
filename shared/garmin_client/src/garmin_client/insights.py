"""Actionable insights engine - the core WHOOP philosophy.

This module transforms raw data into decisions. The user should know in 2 seconds:
"Should I push today or recover?"

Key concepts:
- Daily decision framework: GO, MODERATE, or RECOVER
- Optimal strain targets based on recovery zone
- Personalized sleep need calculation
- Sleep debt tracking and repayment
"""

from dataclasses import dataclass, asdict
from typing import Optional, Tuple, List

from garmin_client.baselines import PersonalBaselines


@dataclass
class DailyInsight:
    """Today's actionable recommendation."""
    decision: str  # "GO", "MODERATE", "RECOVER"
    headline: str  # "Push hard today" or "Recovery focus"
    explanation: str  # Why this recommendation
    strain_target: Tuple[float, float]  # (min, max) recommended strain
    sleep_target: float  # Hours needed tonight

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'decision': self.decision,
            'headline': self.headline,
            'explanation': self.explanation,
            'strain_target': list(self.strain_target),
            'sleep_target': self.sleep_target,
        }


@dataclass
class SleepDebtInfo:
    """Sleep debt tracking information."""
    accumulated_debt: float  # Total sleep debt in hours
    nightly_repayment: float  # Suggested repayment per night
    days_to_clear: int  # Days to clear debt at current rate

    def to_dict(self) -> dict:
        return asdict(self)


def get_optimal_strain_target(recovery: int) -> Tuple[float, float]:
    """Get recommended strain range based on recovery score.

    The strain scale is logarithmic (0-21):
    - 0-8: Light day (walking, easy activity)
    - 8-14: Moderate (steady workout)
    - 14-18: Hard (tough training session)
    - 18-21: All-out (race, competition, extreme effort)

    Args:
        recovery: Recovery score (0-100)

    Returns:
        Tuple of (min_strain, max_strain) recommended for today
    """
    if recovery >= 67:  # Green zone
        return (14.0, 21.0)
    elif recovery >= 34:  # Yellow zone
        return (8.0, 14.0)
    else:  # Red zone
        return (0.0, 8.0)


def get_strain_recommendation(recovery: int) -> str:
    """Get workout recommendation based on recovery zone.

    Args:
        recovery: Recovery score (0-100)

    Returns:
        Human-readable workout recommendation
    """
    if recovery >= 67:
        return "Great day for intervals or racing"
    elif recovery >= 34:
        return "Steady cardio or technique work"
    else:
        return "Rest, mobility, light yoga"


def calculate_sleep_need(
    base_sleep_need: float,
    yesterday_strain: float,
    sleep_debt: float
) -> float:
    """Calculate tonight's personalized sleep target.

    Formula:
    - Base need (your personal average)
    - + Strain adjustment (higher strain = more sleep needed)
    - + Debt repayment (spread over 7 days)

    Args:
        base_sleep_need: Personal baseline sleep (hours)
        yesterday_strain: Yesterday's strain score (0-21)
        sleep_debt: Accumulated sleep debt (hours)

    Returns:
        Tonight's sleep target in hours
    """
    # Strain adjustment: ~3 min per strain point above 10
    # This reflects higher recovery needs after intense training
    strain_adjustment = max(0, (yesterday_strain - 10) * 0.05)

    # Debt repayment: spread over 7 days to avoid unrealistic targets
    # Research shows you can't fully repay sleep debt in one night
    debt_repayment = max(0, sleep_debt) / 7

    return round(base_sleep_need + strain_adjustment + debt_repayment, 2)


def calculate_sleep_debt(
    actual_hours: List[float],
    needed_hours: List[float]
) -> float:
    """Calculate accumulated sleep debt over recent days.

    Sleep debt accumulates when you consistently sleep less than needed.
    This tracks the deficit to help plan recovery.

    Args:
        actual_hours: List of actual sleep hours (most recent first)
        needed_hours: List of required sleep hours (most recent first)

    Returns:
        Accumulated sleep debt in hours (always >= 0)
    """
    debt = 0.0
    for actual, needed in zip(actual_hours, needed_hours):
        if actual is not None and needed is not None:
            debt += max(0, needed - actual)
    return round(debt, 2)


def calculate_sleep_debt_simple(
    actual_hours: List[float],
    baseline_sleep: float,
    days: int = 7
) -> float:
    """Calculate sleep debt using a simple baseline comparison.

    Simpler version that compares actual sleep to your personal baseline
    over the past N days.

    Args:
        actual_hours: List of actual sleep hours (most recent first)
        baseline_sleep: Your personal sleep baseline (hours)
        days: Number of days to calculate debt over

    Returns:
        Accumulated sleep debt in hours (always >= 0)
    """
    debt = 0.0
    for actual in actual_hours[:days]:
        if actual is not None and baseline_sleep is not None:
            debt += max(0, baseline_sleep - actual)
    return round(debt, 2)


def get_sleep_debt_info(
    sleep_debt: float,
    baseline_sleep: float
) -> SleepDebtInfo:
    """Get detailed sleep debt information.

    Args:
        sleep_debt: Accumulated sleep debt in hours
        baseline_sleep: Personal sleep baseline in hours

    Returns:
        SleepDebtInfo with accumulated debt, repayment plan, and days to clear
    """
    # Cap repayment at 1 hour per night to be realistic
    nightly_repayment = min(1.0, sleep_debt / 7) if sleep_debt > 0 else 0

    # Calculate days to clear at this rate
    days_to_clear = int(sleep_debt / nightly_repayment) if nightly_repayment > 0 else 0

    return SleepDebtInfo(
        accumulated_debt=sleep_debt,
        nightly_repayment=round(nightly_repayment, 2),
        days_to_clear=days_to_clear,
    )


def generate_go_explanation(
    recovery: int,
    hrv_direction: str,
    strain_target: Tuple[float, float]
) -> str:
    """Generate explanation for GO decision.

    Args:
        recovery: Recovery score
        hrv_direction: 'up', 'down', or 'stable'
        strain_target: Recommended strain range

    Returns:
        Human-readable explanation
    """
    parts = [f"Recovery at {recovery}% puts you in the green zone."]

    if hrv_direction == 'up':
        parts.append("HRV trending up shows strong autonomic recovery.")
    elif hrv_direction == 'stable':
        parts.append("HRV is stable at your baseline.")

    parts.append(f"Target strain {strain_target[0]:.0f}-{strain_target[1]:.0f} today.")
    parts.append("Great day for intervals, tempo work, or competition.")

    return " ".join(parts)


def generate_moderate_explanation(
    recovery: int,
    hrv_direction: str
) -> str:
    """Generate explanation for MODERATE decision.

    Args:
        recovery: Recovery score
        hrv_direction: 'up', 'down', or 'stable'

    Returns:
        Human-readable explanation
    """
    parts = [f"Recovery at {recovery}% - yellow zone."]

    if hrv_direction == 'down':
        parts.append("HRV below baseline suggests your body is still adapting.")
    elif hrv_direction == 'stable':
        parts.append("Your body is in a balanced state.")

    parts.append("Good day for steady-state cardio, technique drills, or moderate effort.")
    parts.append("Avoid all-out efforts to prevent overtraining.")

    return " ".join(parts)


def generate_recover_explanation(
    recovery: int,
    hrv_direction: str,
    sleep_hours: Optional[float]
) -> str:
    """Generate explanation for RECOVER decision.

    Args:
        recovery: Recovery score
        hrv_direction: 'up', 'down', or 'stable'
        sleep_hours: Last night's sleep hours

    Returns:
        Human-readable explanation
    """
    parts = [f"Recovery at {recovery}% - red zone."]

    if hrv_direction == 'down':
        parts.append("HRV significantly below baseline indicates stress or incomplete recovery.")

    if sleep_hours and sleep_hours < 6:
        parts.append(f"Only {sleep_hours:.1f}h sleep is limiting your recovery.")

    parts.append("Focus on rest, hydration, and quality sleep tonight.")
    parts.append("Light movement like walking or yoga is fine.")

    return " ".join(parts)


def generate_daily_insight(
    recovery: int,
    hrv_direction: str,  # 'up', 'down', 'stable'
    sleep_hours: float,
    sleep_baseline: float,
    strain_yesterday: float,
    baselines: Optional[PersonalBaselines] = None
) -> DailyInsight:
    """Generate today's actionable insight.

    This is the core function that answers: "Should I push today or recover?"

    Args:
        recovery: Today's recovery score (0-100)
        hrv_direction: HRV trend direction ('up', 'down', 'stable')
        sleep_hours: Last night's sleep hours
        sleep_baseline: Personal sleep baseline (from baselines or default)
        strain_yesterday: Yesterday's strain score (0-21)
        baselines: Optional PersonalBaselines for more context

    Returns:
        DailyInsight with decision, explanation, and targets
    """
    strain_target = get_optimal_strain_target(recovery)

    # Calculate tonight's sleep need
    # Use simple debt calculation based on last night vs baseline
    # Note: use 'is not None' to handle 0 sleep hours correctly
    sleep_debt = max(0, sleep_baseline - sleep_hours) if sleep_hours is not None else 0
    sleep_target = calculate_sleep_need(sleep_baseline, strain_yesterday, sleep_debt)

    if recovery >= 67:
        decision = "GO"
        headline = "Push hard today"
        explanation = generate_go_explanation(recovery, hrv_direction, strain_target)
    elif recovery >= 34:
        decision = "MODERATE"
        headline = "Moderate effort today"
        explanation = generate_moderate_explanation(recovery, hrv_direction)
    else:
        decision = "RECOVER"
        headline = "Recovery focus"
        explanation = generate_recover_explanation(recovery, hrv_direction, sleep_hours)

    return DailyInsight(
        decision=decision,
        headline=headline,
        explanation=explanation,
        strain_target=strain_target,
        sleep_target=sleep_target,
    )


def get_sleep_target_breakdown(
    sleep_baseline: float,
    strain_yesterday: float,
    sleep_debt: float
) -> dict:
    """Get detailed breakdown of tonight's sleep target.

    Returns a breakdown showing:
    - Your baseline need
    - Strain adjustment
    - Debt repayment
    - Total target

    Args:
        sleep_baseline: Personal sleep baseline in hours
        strain_yesterday: Yesterday's strain (0-21)
        sleep_debt: Accumulated sleep debt in hours

    Returns:
        Dictionary with breakdown components
    """
    strain_adjustment = max(0, (strain_yesterday - 10) * 0.05)
    debt_repayment = max(0, sleep_debt) / 7
    total = sleep_baseline + strain_adjustment + debt_repayment

    return {
        'baseline': round(sleep_baseline, 2),
        'strain_adjustment': round(strain_adjustment, 2),
        'strain_adjustment_minutes': round(strain_adjustment * 60),
        'debt_repayment': round(debt_repayment, 2),
        'debt_repayment_minutes': round(debt_repayment * 60),
        'total_debt': round(sleep_debt, 2),
        'total': round(total, 2),
        'total_formatted': format_hours_minutes(total),
    }


def format_hours_minutes(hours: float) -> str:
    """Format hours as 'Xh Ym' string.

    Args:
        hours: Hours as float (e.g., 7.75)

    Returns:
        Formatted string (e.g., '7h 45m')
    """
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}h {m:02d}m"
