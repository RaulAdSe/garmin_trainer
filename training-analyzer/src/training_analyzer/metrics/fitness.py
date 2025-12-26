"""Fitness-Fatigue model calculations (CTL, ATL, TSB, ACWR)."""

import math
from datetime import date, timedelta
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class FitnessMetrics:
    """Daily fitness metrics from the Fitness-Fatigue model."""

    date: date
    daily_load: float  # TSS/HRSS/TRIMP for the day
    ctl: float  # Chronic Training Load (fitness) - 42 day EWMA
    atl: float  # Acute Training Load (fatigue) - 7 day EWMA
    tsb: float  # Training Stress Balance (form) = CTL - ATL
    acwr: float  # Acute:Chronic Workload Ratio
    risk_zone: str  # 'optimal', 'caution', 'danger', 'undertrained'

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "date": self.date.isoformat(),
            "daily_load": self.daily_load,
            "ctl": self.ctl,
            "atl": self.atl,
            "tsb": self.tsb,
            "acwr": self.acwr,
            "risk_zone": self.risk_zone,
        }


def calculate_ewma(
    current_value: float,
    previous_ewma: float,
    time_constant: int,
) -> float:
    """
    Exponentially Weighted Moving Average.

    Uses the formula: EWMA_n = EWMA_{n-1} * decay + value * (1 - decay)
    where decay = e^(-1/time_constant)

    Args:
        current_value: Today's training load
        previous_ewma: Yesterday's EWMA value
        time_constant: Time constant in days (42 for CTL, 7 for ATL)

    Returns:
        New EWMA value
    """
    decay = math.exp(-1 / time_constant)
    return previous_ewma * decay + current_value * (1 - decay)


def determine_risk_zone(acwr: float) -> str:
    """
    Determine injury risk zone based on ACWR.

    Based on research by Gabbett (2016) and others:
    - < 0.8: Undertrained (not enough stimulus)
    - 0.8 - 1.3: Optimal (sweet spot for adaptation)
    - 1.3 - 1.5: Caution (elevated injury risk)
    - > 1.5: Danger (high injury risk)

    Args:
        acwr: Acute:Chronic Workload Ratio

    Returns:
        Risk zone classification string
    """
    if acwr < 0.8:
        return "undertrained"
    elif acwr <= 1.3:
        return "optimal"
    elif acwr <= 1.5:
        return "caution"
    else:
        return "danger"


def calculate_fitness_metrics(
    daily_loads: List[Tuple[date, float]],
    initial_ctl: float = 0.0,
    initial_atl: float = 0.0,
    ctl_time_constant: int = 42,
    atl_time_constant: int = 7,
) -> List[FitnessMetrics]:
    """
    Calculate CTL, ATL, TSB, and ACWR for a series of daily loads.

    The Fitness-Fatigue (Banister) model uses two exponential moving averages:
    - CTL (Chronic Training Load): 42-day EWMA representing "fitness"
    - ATL (Acute Training Load): 7-day EWMA representing "fatigue"
    - TSB (Training Stress Balance): CTL - ATL representing "form"
    - ACWR (Acute:Chronic Workload Ratio): ATL / CTL for injury risk

    Args:
        daily_loads: List of (date, load) tuples, need not be consecutive
        initial_ctl: Starting CTL value (for new users, use 0)
        initial_atl: Starting ATL value (for new users, use 0)
        ctl_time_constant: Days for CTL calculation (default 42)
        atl_time_constant: Days for ATL calculation (default 7)

    Returns:
        List of FitnessMetrics, one per day in the input
    """
    if not daily_loads:
        return []

    # Sort by date
    sorted_loads = sorted(daily_loads, key=lambda x: x[0])

    results = []
    ctl = initial_ctl
    atl = initial_atl

    # Track the previous date to handle gaps
    prev_date: Optional[date] = None

    for workout_date, load in sorted_loads:
        # Fill in zero-load days for any gaps
        if prev_date is not None:
            days_gap = (workout_date - prev_date).days
            for gap_day in range(1, days_gap):
                # Update CTL/ATL with zero load for missing days
                ctl = calculate_ewma(0.0, ctl, ctl_time_constant)
                atl = calculate_ewma(0.0, atl, atl_time_constant)

        # Calculate metrics for this day
        ctl = calculate_ewma(load, ctl, ctl_time_constant)
        atl = calculate_ewma(load, atl, atl_time_constant)
        tsb = ctl - atl

        # ACWR with minimum CTL threshold to avoid division issues
        # When CTL is very low, the ratio is meaningless
        min_ctl_threshold = 10.0
        if ctl > min_ctl_threshold:
            acwr = atl / ctl
        else:
            # Default to 1.0 (optimal) when insufficient training history
            acwr = 1.0

        risk_zone = determine_risk_zone(acwr)

        results.append(
            FitnessMetrics(
                date=workout_date,
                daily_load=round(load, 1),
                ctl=round(ctl, 1),
                atl=round(atl, 1),
                tsb=round(tsb, 1),
                acwr=round(acwr, 2),
                risk_zone=risk_zone,
            )
        )

        prev_date = workout_date

    return results


def get_training_recommendation(tsb: float, acwr: float) -> str:
    """
    Get a training recommendation based on current form and risk.

    Args:
        tsb: Training Stress Balance
        acwr: Acute:Chronic Workload Ratio

    Returns:
        Training recommendation string
    """
    # Danger zone - reduce training
    if acwr > 1.5:
        return "High injury risk. Reduce training load significantly."

    # Caution zone
    if acwr > 1.3:
        return "Elevated injury risk. Consider an easy day or rest."

    # Undertrained
    if acwr < 0.8:
        return "Training load low. Safe to increase intensity."

    # Optimal zone - base recommendation on form (TSB)
    if tsb > 25:
        return "Fresh and recovered. Good day for a hard workout."
    elif tsb > 0:
        return "Positive form. Can push moderately."
    elif tsb > -10:
        return "Slightly fatigued. Moderate intensity recommended."
    elif tsb > -25:
        return "Fatigued. Easy training recommended."
    else:
        return "Very fatigued. Consider rest or very easy activity."
