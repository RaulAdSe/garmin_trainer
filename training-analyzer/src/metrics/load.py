"""Training load calculations (HRSS, TRIMP)."""

import math


def calculate_hrss(
    duration_min: float,
    avg_hr: int,
    threshold_hr: int,
    max_hr: int,
    rest_hr: int,
) -> float:
    """
    Heart Rate Stress Score - TSS equivalent for HR-based training.
    Uses normalized HR and intensity factor.

    Args:
        duration_min: Duration of activity in minutes
        avg_hr: Average heart rate during activity
        threshold_hr: Lactate threshold heart rate
        max_hr: Maximum heart rate
        rest_hr: Resting heart rate

    Returns:
        HRSS value (similar scale to TSS: 100 = 1 hour at threshold)
    """
    # Normalize HR to 0-1 scale based on heart rate reserve
    hr_reserve = max_hr - rest_hr
    if hr_reserve <= 0:
        return 0.0

    normalized_hr = (avg_hr - rest_hr) / hr_reserve
    normalized_hr = max(0, min(1, normalized_hr))  # Clamp to [0, 1]

    # Threshold as percentage of reserve
    threshold_reserve_ratio = (threshold_hr - rest_hr) / hr_reserve
    if threshold_reserve_ratio <= 0:
        threshold_reserve_ratio = 0.85  # Default assumption

    # Intensity Factor (IF) = ratio of session HR to threshold HR
    intensity_factor = normalized_hr / threshold_reserve_ratio

    # HRSS = (duration * IF^2) / 60 * 100
    # This gives ~100 HRSS for 1 hour at threshold
    hrss = (duration_min * (intensity_factor ** 2)) / 60 * 100
    return round(hrss, 1)


def calculate_trimp(
    duration_min: float,
    avg_hr: int,
    rest_hr: int,
    max_hr: int,
    gender: str = "male",
) -> float:
    """
    Training Impulse using Banister's exponential formula.

    TRIMP accounts for both duration and intensity, with an exponential
    weighting that emphasizes high-intensity work.

    Args:
        duration_min: Duration of activity in minutes
        avg_hr: Average heart rate during activity
        rest_hr: Resting heart rate
        max_hr: Maximum heart rate
        gender: 'male' or 'female' (different coefficients due to
                physiological differences in heart rate response)

    Returns:
        TRIMP value (arbitrary units, typical session: 50-150)
    """
    hr_reserve = max_hr - rest_hr
    if hr_reserve <= 0:
        return 0.0

    # Heart rate ratio (fraction of HRR used)
    delta_hr = (avg_hr - rest_hr) / hr_reserve
    delta_hr = max(0, min(1, delta_hr))  # Clamp to [0, 1]

    # Gender-specific coefficients for exponential weighting
    # These come from Banister's original research
    if gender.lower() == "female":
        a, b = 0.86, 1.67
    else:
        a, b = 0.64, 1.92

    # TRIMP = duration * delta_hr * a * e^(b * delta_hr)
    trimp = duration_min * delta_hr * a * math.exp(b * delta_hr)
    return round(trimp, 1)


def calculate_relative_effort(
    duration_min: float,
    avg_hr: int,
    max_hr: int,
    rest_hr: int,
) -> float:
    """
    Calculate a simplified relative effort score.

    This is a more intuitive metric that scales with duration and intensity.
    Similar to Strava's Relative Effort but simplified.

    Args:
        duration_min: Duration of activity in minutes
        avg_hr: Average heart rate during activity
        max_hr: Maximum heart rate
        rest_hr: Resting heart rate

    Returns:
        Relative effort score (scale roughly 0-500 for typical workouts)
    """
    hr_reserve = max_hr - rest_hr
    if hr_reserve <= 0:
        return 0.0

    # Calculate intensity as percentage of HRR
    intensity = (avg_hr - rest_hr) / hr_reserve
    intensity = max(0, min(1, intensity))

    # Apply exponential weighting for high intensity
    weighted_intensity = intensity ** 1.5

    # Scale to give reasonable numbers
    effort = duration_min * weighted_intensity * 2
    return round(effort, 1)
