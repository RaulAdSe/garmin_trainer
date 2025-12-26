"""Swimming metrics calculations (SWOLF, CSS, stroke analysis)."""

import statistics
from typing import Any, Dict, List, Tuple


def calculate_swolf(time_per_length_sec: float, strokes_per_length: int) -> float:
    """
    Calculate SWOLF score (efficiency metric).

    SWOLF = Time per length (sec) + Strokes per length
    Lower is better (more efficient).

    Typical SWOLF scores:
    - Elite swimmers: 35-45 (25m pool)
    - Competitive: 45-55
    - Recreational: 55-70
    - Beginner: 70+

    Args:
        time_per_length_sec: Time to complete one length in seconds
        strokes_per_length: Number of strokes per length

    Returns:
        SWOLF score (time + strokes)
    """
    if time_per_length_sec < 0 or strokes_per_length < 0:
        raise ValueError("Time and strokes must be non-negative")

    return round(time_per_length_sec + strokes_per_length, 1)


def calculate_stroke_rate(strokes: int, duration_sec: float) -> float:
    """
    Calculate stroke rate in strokes per minute.

    Typical stroke rates:
    - Distance freestyle: 50-60 strokes/min
    - Middle distance: 60-70 strokes/min
    - Sprint: 70-90 strokes/min

    Args:
        strokes: Total number of strokes
        duration_sec: Duration in seconds

    Returns:
        Stroke rate in strokes per minute
    """
    if duration_sec <= 0:
        return 0.0
    if strokes < 0:
        raise ValueError("Strokes must be non-negative")

    return round((strokes / duration_sec) * 60, 1)


def calculate_pace_per_100m(distance_m: float, duration_sec: float) -> int:
    """
    Calculate swim pace in seconds per 100m.

    Typical swim paces:
    - Elite: 55-65 sec/100m
    - Competitive: 75-90 sec/100m
    - Recreational: 100-120 sec/100m
    - Beginner: 130-180 sec/100m

    Args:
        distance_m: Total distance swum in meters
        duration_sec: Total duration in seconds

    Returns:
        Pace in seconds per 100m (rounded to nearest second)
    """
    if distance_m <= 0:
        raise ValueError("Distance must be positive")
    if duration_sec < 0:
        raise ValueError("Duration must be non-negative")

    pace = (duration_sec / distance_m) * 100
    return int(round(pace))


def calculate_css(t400_sec: float, t200_sec: float) -> int:
    """
    Calculate Critical Swim Speed (threshold pace) from test times.

    CSS represents the pace you can theoretically maintain indefinitely,
    similar to cycling FTP or running threshold pace. It's derived from
    a 400m and 200m time trial.

    CSS = (400m - 200m) / (T400 - T200)

    The formula calculates the speed (m/s) and converts to pace (sec/100m).

    Args:
        t400_sec: Time to swim 400m in seconds (e.g., 360 for 6:00)
        t200_sec: Time to swim 200m in seconds (e.g., 165 for 2:45)

    Returns:
        CSS pace in seconds per 100m

    Raises:
        ValueError: If times are invalid (t400 must be > t200, both positive)
    """
    if t200_sec <= 0 or t400_sec <= 0:
        raise ValueError("Both times must be positive")
    if t400_sec <= t200_sec:
        raise ValueError("400m time must be greater than 200m time")

    # CSS speed in m/s = (400 - 200) / (T400 - T200)
    css_speed = 200 / (t400_sec - t200_sec)

    # Convert to pace per 100m
    # pace = 100m / speed = 100 / css_speed
    css_pace = 100 / css_speed

    return int(round(css_pace))


def estimate_swim_tss(duration_min: float, pace_per_100m: int, css_pace: int) -> float:
    """
    Estimate swim TSS based on intensity relative to CSS.

    Similar to running rTSS but for swimming. Uses the intensity factor
    (ratio of actual pace to CSS pace) squared, multiplied by duration.

    Formula: TSS = (duration_min * IF^2) / 60 * 100
    where IF = CSS_pace / actual_pace (faster pace = higher IF)

    Note: IF is inverted compared to running because in swimming, lower
    pace numbers mean faster swimming.

    Typical swim TSS values:
    - Easy 30min: 25-35
    - Moderate 45min: 45-60
    - Hard 60min: 80-120
    - Race: 100-200+

    Args:
        duration_min: Duration of swim in minutes
        pace_per_100m: Average pace during swim in sec/100m
        css_pace: Critical Swim Speed pace in sec/100m

    Returns:
        Estimated swim TSS value
    """
    if duration_min <= 0:
        return 0.0
    if pace_per_100m <= 0 or css_pace <= 0:
        raise ValueError("Pace values must be positive")

    # Intensity Factor: CSS/pace (faster pace = higher IF)
    # If you swim at CSS pace, IF = 1.0
    # If you swim faster than CSS, IF > 1.0
    # If you swim slower than CSS, IF < 1.0
    intensity_factor = css_pace / pace_per_100m

    # Cap IF at reasonable limits (0.5 to 1.5)
    intensity_factor = max(0.5, min(1.5, intensity_factor))

    # TSS formula: (duration * IF^2) / 60 * 100
    # This gives ~100 TSS for 1 hour at CSS pace
    tss = (duration_min * (intensity_factor ** 2)) / 60 * 100

    return round(tss, 1)


def get_swim_zones(css_pace: int) -> Dict[str, Tuple[int, int]]:
    """
    Calculate swim training zones based on CSS.

    Returns zones with pace ranges (sec/100m). Note that in swimming,
    LOWER pace numbers mean FASTER swimming, so zone 5 (fastest) has
    the lowest numbers.

    Zone definitions based on CSS percentages:
    - Zone 1 (Recovery): >115% CSS pace (slower than CSS)
    - Zone 2 (Aerobic Endurance): 105-115% CSS
    - Zone 3 (Threshold): 95-105% CSS
    - Zone 4 (VO2max): 85-95% CSS (faster than CSS)
    - Zone 5 (Sprint): <85% CSS (much faster)

    Args:
        css_pace: Critical Swim Speed pace in sec/100m

    Returns:
        Dictionary with zone names and (min, max) pace ranges in sec/100m
        Note: For zones, "min" is the faster pace (lower number)
    """
    if css_pace <= 0:
        raise ValueError("CSS pace must be positive")

    # Calculate zone boundaries
    # Zone 1: >115% (slower, higher numbers)
    z1_fast = int(round(css_pace * 1.15))  # The "fast" end of Z1
    z1_slow = int(round(css_pace * 1.40))  # Upper limit for recovery

    # Zone 2: 105-115%
    z2_fast = int(round(css_pace * 1.05))
    z2_slow = int(round(css_pace * 1.15))

    # Zone 3: 95-105% (around threshold)
    z3_fast = int(round(css_pace * 0.95))
    z3_slow = int(round(css_pace * 1.05))

    # Zone 4: 85-95% (faster than threshold)
    z4_fast = int(round(css_pace * 0.85))
    z4_slow = int(round(css_pace * 0.95))

    # Zone 5: <85% (sprint, fastest)
    z5_fast = int(round(css_pace * 0.70))  # Lower limit
    z5_slow = int(round(css_pace * 0.85))

    return {
        "zone1_recovery": (z1_fast, z1_slow),
        "zone2_aerobic": (z2_fast, z2_slow),
        "zone3_threshold": (z3_fast, z3_slow),
        "zone4_vo2max": (z4_fast, z4_slow),
        "zone5_sprint": (z5_fast, z5_slow),
    }


def analyze_stroke_efficiency(
    strokes_per_length: List[int],
    times_per_length: List[float],
) -> Dict[str, Any]:
    """
    Analyze stroke efficiency over a swim session.

    Provides insights into:
    - Average SWOLF score
    - SWOLF trend (improving, declining, or stable)
    - Stroke count consistency (coefficient of variation)
    - Fatigue indicator (comparing last 25% to first 25%)

    Args:
        strokes_per_length: List of stroke counts for each length
        times_per_length: List of times (in seconds) for each length

    Returns:
        Dictionary with:
        - avg_swolf: Average SWOLF score across all lengths
        - swolf_trend: "improving", "declining", or "stable"
        - stroke_count_consistency: Coefficient of variation (%) for strokes
        - fatigue_indicator: Ratio of avg strokes (last 25% / first 25%)
    """
    if len(strokes_per_length) != len(times_per_length):
        raise ValueError("Strokes and times lists must have same length")

    if len(strokes_per_length) == 0:
        return {
            "avg_swolf": 0.0,
            "swolf_trend": "stable",
            "stroke_count_consistency": 0.0,
            "fatigue_indicator": 1.0,
        }

    # Calculate SWOLF for each length
    swolf_scores = [
        calculate_swolf(t, s)
        for t, s in zip(times_per_length, strokes_per_length)
    ]

    # Average SWOLF
    avg_swolf = round(statistics.mean(swolf_scores), 1)

    # SWOLF trend analysis (compare first half vs second half)
    n = len(swolf_scores)
    if n >= 4:
        first_half = swolf_scores[:n // 2]
        second_half = swolf_scores[n // 2:]
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)

        # Determine trend (5% threshold for significance)
        diff_pct = (second_avg - first_avg) / first_avg * 100 if first_avg > 0 else 0

        if diff_pct > 5:
            swolf_trend = "declining"  # SWOLF increasing = getting worse
        elif diff_pct < -5:
            swolf_trend = "improving"  # SWOLF decreasing = getting better
        else:
            swolf_trend = "stable"
    else:
        swolf_trend = "stable"

    # Stroke count consistency (coefficient of variation)
    if len(strokes_per_length) >= 2:
        stroke_mean = statistics.mean(strokes_per_length)
        stroke_stdev = statistics.stdev(strokes_per_length)
        stroke_cv = (stroke_stdev / stroke_mean * 100) if stroke_mean > 0 else 0.0
        stroke_count_consistency = round(stroke_cv, 1)
    else:
        stroke_count_consistency = 0.0

    # Fatigue indicator (last 25% vs first 25% stroke count)
    if n >= 4:
        quarter = max(1, n // 4)
        first_quarter = strokes_per_length[:quarter]
        last_quarter = strokes_per_length[-quarter:]

        first_avg = statistics.mean(first_quarter)
        last_avg = statistics.mean(last_quarter)

        fatigue_indicator = round(last_avg / first_avg, 2) if first_avg > 0 else 1.0
    else:
        fatigue_indicator = 1.0

    return {
        "avg_swolf": avg_swolf,
        "swolf_trend": swolf_trend,
        "stroke_count_consistency": stroke_count_consistency,
        "fatigue_indicator": fatigue_indicator,
    }


def format_swim_pace(pace_sec: int) -> str:
    """
    Format swim pace (sec/100m) to mm:ss format.

    Args:
        pace_sec: Pace in seconds per 100m

    Returns:
        Formatted string like "1:45/100m"
    """
    minutes = pace_sec // 60
    seconds = pace_sec % 60
    return f"{minutes}:{seconds:02d}/100m"


def get_swim_zone_for_pace(pace: int, css_pace: int) -> int:
    """
    Determine which swim zone a given pace falls into.

    Args:
        pace: Swim pace in sec/100m
        css_pace: CSS pace in sec/100m

    Returns:
        Zone number (1-5), or 0 if pace is extremely slow
    """
    if css_pace <= 0:
        return 0

    # Calculate percentage of CSS
    # Higher percentage = slower pace
    pct_of_css = pace / css_pace

    if pct_of_css > 1.40:
        return 0  # Too slow, not really training
    elif pct_of_css > 1.15:
        return 1  # Recovery
    elif pct_of_css > 1.05:
        return 2  # Aerobic
    elif pct_of_css > 0.95:
        return 3  # Threshold
    elif pct_of_css > 0.85:
        return 4  # VO2max
    else:
        return 5  # Sprint


def estimate_css_from_race_times(
    race_distance_m: int,
    race_time_sec: float,
) -> int:
    """
    Estimate CSS from a race result when 400m/200m test isn't available.

    Uses approximations based on common race distances:
    - 100m sprint: CSS ~ 108% of race pace
    - 200m: CSS ~ 102% of race pace
    - 400m: CSS ~ 97% of race pace
    - 800m: CSS ~ 94% of race pace
    - 1500m: CSS ~ 100% of race pace (1500m is close to CSS pace)

    Args:
        race_distance_m: Race distance in meters
        race_time_sec: Race time in seconds

    Returns:
        Estimated CSS pace in sec/100m
    """
    if race_distance_m <= 0 or race_time_sec <= 0:
        raise ValueError("Distance and time must be positive")

    # Calculate race pace per 100m
    race_pace = (race_time_sec / race_distance_m) * 100

    # Apply distance-specific multiplier to estimate CSS
    # CSS is typically close to 1500m pace
    if race_distance_m <= 100:
        multiplier = 1.08  # Sprint is faster than CSS
    elif race_distance_m <= 200:
        multiplier = 1.02
    elif race_distance_m <= 400:
        multiplier = 0.97
    elif race_distance_m <= 800:
        multiplier = 0.94
    elif race_distance_m <= 1500:
        multiplier = 1.00  # 1500m is close to CSS pace
    else:
        multiplier = 1.03  # Longer distances are slower than CSS

    css_pace = int(round(race_pace * multiplier))
    return css_pace
