"""Cycling power metrics calculations (NP, IF, TSS, power zones)."""

from typing import Dict, List, Tuple


def calculate_normalized_power(power_samples: List[int], sample_rate_hz: int = 1) -> float:
    """
    Calculate Normalized Power (NP) using 30-second rolling average.

    NP accounts for the physiological cost of variable power output.
    It uses a 30-second rolling average, then takes the 4th power mean.

    Formula: NP = (mean(rolling_30s_power^4))^0.25

    Args:
        power_samples: List of power values in watts (one per sample)
        sample_rate_hz: Sample rate in Hz (samples per second), default 1

    Returns:
        Normalized Power in watts, or 0.0 if insufficient data
    """
    if not power_samples:
        return 0.0

    # Calculate window size for 30-second rolling average
    window_size = 30 * sample_rate_hz

    # Need at least window_size samples for a valid calculation
    if len(power_samples) < window_size:
        # If we don't have enough samples, use what we have
        # but only if we have at least a few seconds of data
        if len(power_samples) < 3 * sample_rate_hz:
            return 0.0
        window_size = len(power_samples)

    # Calculate rolling 30-second averages
    rolling_averages: List[float] = []
    for i in range(len(power_samples) - window_size + 1):
        window = power_samples[i:i + window_size]
        avg = sum(window) / len(window)
        rolling_averages.append(avg)

    if not rolling_averages:
        return 0.0

    # Calculate the 4th power mean
    fourth_power_sum = sum(avg ** 4 for avg in rolling_averages)
    fourth_power_mean = fourth_power_sum / len(rolling_averages)

    # Take the 4th root
    normalized_power = fourth_power_mean ** 0.25

    return round(normalized_power, 1)


def calculate_intensity_factor(normalized_power: float, ftp: int) -> float:
    """
    Calculate Intensity Factor (IF).

    IF represents the relative intensity of the workout compared to FTP.
    IF = 1.0 means the normalized power equals FTP (threshold effort).

    Formula: IF = NP / FTP

    Args:
        normalized_power: Normalized Power in watts
        ftp: Functional Threshold Power in watts

    Returns:
        Intensity Factor (dimensionless ratio)
    """
    if ftp <= 0:
        return 0.0

    intensity_factor = normalized_power / ftp
    return round(intensity_factor, 3)


def calculate_tss(
    duration_sec: int,
    normalized_power: float,
    intensity_factor: float,
    ftp: int,
) -> float:
    """
    Calculate Training Stress Score from power.

    TSS quantifies the total training load of a workout. A TSS of 100
    represents one hour at FTP - the maximum sustainable steady effort.

    Formula: TSS = (duration_sec * NP * IF) / (FTP * 3600) * 100

    Args:
        duration_sec: Duration of activity in seconds
        normalized_power: Normalized Power in watts
        intensity_factor: Intensity Factor (NP/FTP)
        ftp: Functional Threshold Power in watts

    Returns:
        Training Stress Score
    """
    if ftp <= 0 or duration_sec <= 0:
        return 0.0

    tss = (duration_sec * normalized_power * intensity_factor) / (ftp * 3600) * 100
    return round(tss, 1)


def calculate_tss_simple(
    duration_sec: int,
    normalized_power: float,
    ftp: int,
) -> float:
    """
    Calculate Training Stress Score with automatic IF calculation.

    Convenience function that calculates IF internally.

    Args:
        duration_sec: Duration of activity in seconds
        normalized_power: Normalized Power in watts
        ftp: Functional Threshold Power in watts

    Returns:
        Training Stress Score
    """
    if ftp <= 0:
        return 0.0

    intensity_factor = calculate_intensity_factor(normalized_power, ftp)
    return calculate_tss(duration_sec, normalized_power, intensity_factor, ftp)


def calculate_variability_index(normalized_power: float, avg_power: float) -> float:
    """
    Calculate Variability Index (VI).

    VI indicates how variable the power output was during the workout.
    VI = 1.0 means perfectly steady power (NP = Avg Power).
    Higher values indicate more variable/surging efforts.

    Formula: VI = NP / Avg Power

    Typical values:
    - <1.05: Very steady (time trial, indoor trainer)
    - 1.05-1.15: Moderate variability (road race, group ride)
    - >1.15: High variability (criterium, mountain bike)

    Args:
        normalized_power: Normalized Power in watts
        avg_power: Average power in watts

    Returns:
        Variability Index (dimensionless ratio)
    """
    if avg_power <= 0:
        return 0.0

    vi = normalized_power / avg_power
    return round(vi, 3)


def calculate_power_zones(ftp: int) -> Dict[int, Tuple[int, int]]:
    """
    Calculate 7-zone power zones based on FTP.

    Uses the classic Coggan power zones model:
    - Zone 1: Active Recovery (<55% FTP) - Very easy spinning
    - Zone 2: Endurance (55-75% FTP) - Aerobic base training
    - Zone 3: Tempo (75-90% FTP) - Sustainable but uncomfortable
    - Zone 4: Threshold (90-105% FTP) - At or near FTP
    - Zone 5: VO2max (105-120% FTP) - Hard intervals
    - Zone 6: Anaerobic (120-150% FTP) - Short, very hard efforts
    - Zone 7: Neuromuscular (>150% FTP) - Maximal sprints

    Args:
        ftp: Functional Threshold Power in watts

    Returns:
        Dictionary mapping zone number (1-7) to (min_watts, max_watts) tuple
    """
    if ftp <= 0:
        return {i: (0, 0) for i in range(1, 8)}

    return {
        1: (0, int(ftp * 0.55)),
        2: (int(ftp * 0.55), int(ftp * 0.75)),
        3: (int(ftp * 0.75), int(ftp * 0.90)),
        4: (int(ftp * 0.90), int(ftp * 1.05)),
        5: (int(ftp * 1.05), int(ftp * 1.20)),
        6: (int(ftp * 1.20), int(ftp * 1.50)),
        7: (int(ftp * 1.50), int(ftp * 3.00)),  # Upper bound for practical purposes
    }


def get_power_zone_names() -> Dict[int, str]:
    """
    Get descriptive names for each power zone.

    Returns:
        Dictionary mapping zone number to zone name
    """
    return {
        1: "Active Recovery",
        2: "Endurance",
        3: "Tempo",
        4: "Threshold",
        5: "VO2max",
        6: "Anaerobic",
        7: "Neuromuscular",
    }


def get_zone_for_power(power: int, zones: Dict[int, Tuple[int, int]]) -> int:
    """
    Return zone number (1-7) for a given power value.

    Args:
        power: Power value in watts
        zones: Power zones dictionary from calculate_power_zones()

    Returns:
        Zone number (1-7), or 0 if power is negative
    """
    if power < 0:
        return 0

    for zone_num in range(1, 8):
        min_power, max_power = zones[zone_num]
        if power <= max_power:
            return zone_num

    # Above zone 7 (shouldn't happen in practice)
    return 7


def estimate_ftp_from_20min_power(avg_20min_power: float) -> int:
    """
    Estimate FTP from 20-minute power test.

    The standard 20-minute FTP test applies a 5% reduction to the
    20-minute average power to estimate the 60-minute sustainable power.

    Formula: FTP = 0.95 * 20min avg power

    Args:
        avg_20min_power: Average power over 20-minute test (watts)

    Returns:
        Estimated FTP in watts (rounded to integer)
    """
    if avg_20min_power <= 0:
        return 0

    ftp = 0.95 * avg_20min_power
    return int(round(ftp))


def estimate_ftp_from_ramp_test(max_1min_power: float) -> int:
    """
    Estimate FTP from ramp test (MAP test).

    In a ramp test, FTP is typically estimated as 75% of the maximum
    1-minute power achieved during the test.

    Formula: FTP = 0.75 * Max 1-minute power

    Args:
        max_1min_power: Maximum average power over any 1-minute period (watts)

    Returns:
        Estimated FTP in watts (rounded to integer)
    """
    if max_1min_power <= 0:
        return 0

    ftp = 0.75 * max_1min_power
    return int(round(ftp))


def get_power_zone_distribution(
    power_samples: List[int],
    ftp: int,
) -> Dict[int, float]:
    """
    Calculate percentage of time in each power zone.

    Args:
        power_samples: List of power values in watts (one per time unit)
        ftp: Functional Threshold Power in watts

    Returns:
        Dictionary with zone percentages, e.g., {1: 10.5, 2: 45.2, ...}
    """
    if not power_samples or ftp <= 0:
        return {zone: 0.0 for zone in range(1, 8)}

    zones = calculate_power_zones(ftp)
    zone_counts = {zone: 0 for zone in range(1, 8)}

    for power in power_samples:
        # Skip zero/negative power (coasting or data errors)
        if power <= 0:
            continue
        zone = get_zone_for_power(power, zones)
        zone_counts[zone] += 1

    # Count total valid samples (non-zero power)
    total_valid = sum(zone_counts.values())

    if total_valid == 0:
        return {zone: 0.0 for zone in range(1, 8)}

    return {
        zone: round(count / total_valid * 100, 1)
        for zone, count in zone_counts.items()
    }


def calculate_efficiency_factor(
    normalized_power: float,
    avg_hr: int,
) -> float:
    """
    Calculate Efficiency Factor (EF).

    EF measures aerobic efficiency - how much power you produce per
    heartbeat. Higher is better and indicates improving fitness.

    Formula: EF = NP / Avg HR

    Typical values: 1.0-2.0 for trained cyclists

    Args:
        normalized_power: Normalized Power in watts
        avg_hr: Average heart rate during activity

    Returns:
        Efficiency Factor in watts/bpm
    """
    if avg_hr <= 0:
        return 0.0

    ef = normalized_power / avg_hr
    return round(ef, 3)


def calculate_power_to_weight(power: float, weight_kg: float) -> float:
    """
    Calculate power-to-weight ratio.

    This is a key metric for climbing performance in cycling.

    Formula: P/W = Power / Weight (W/kg)

    Typical FTP values:
    - Recreational: 2.0-2.5 W/kg
    - Competitive amateur: 3.0-3.5 W/kg
    - Elite amateur: 4.0-4.5 W/kg
    - Professional: 5.0-6.5 W/kg

    Args:
        power: Power in watts
        weight_kg: Body weight in kilograms

    Returns:
        Power-to-weight ratio in W/kg
    """
    if weight_kg <= 0:
        return 0.0

    pw_ratio = power / weight_kg
    return round(pw_ratio, 2)


def calculate_work(power_samples: List[int], sample_rate_hz: int = 1) -> int:
    """
    Calculate total work done in kilojoules.

    Work = sum(Power * time) converted to kJ

    Args:
        power_samples: List of power values in watts
        sample_rate_hz: Sample rate in Hz (samples per second)

    Returns:
        Total work in kilojoules
    """
    if not power_samples or sample_rate_hz <= 0:
        return 0

    # Time per sample in seconds
    time_per_sample = 1.0 / sample_rate_hz

    # Sum all power * time (in watt-seconds = joules)
    total_joules = sum(power_samples) * time_per_sample

    # Convert to kilojoules
    total_kj = total_joules / 1000

    return int(round(total_kj))
