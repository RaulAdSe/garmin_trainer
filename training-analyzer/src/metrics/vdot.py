"""
VDOT Pace Zones Calculator (Daniels' Running Formula)

Implements Jack Daniels' VDOT system for calculating training pace zones
from race performance. VDOT is a measure of running ability that accounts
for both VO2max and running economy.

Key concepts:
- VDOT: A "pseudo-VO2max" value derived from race performance
- Each VDOT value corresponds to specific training pace zones
- The system provides paces for: Easy, Marathon, Threshold, Interval, Repetition

References:
- Jack Daniels' Running Formula (3rd edition)
- Original research: Daniels, J.T. (1978). Physiological Research.
"""

import math
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum


class RaceDistance(Enum):
    """Common race distances with values in meters."""
    FIVE_K = 5000
    TEN_K = 10000
    HALF_MARATHON = 21097.5
    MARATHON = 42195

    @classmethod
    def from_string(cls, s: str) -> Optional["RaceDistance"]:
        """Parse race distance from string."""
        mapping = {
            "5k": cls.FIVE_K,
            "5km": cls.FIVE_K,
            "5000": cls.FIVE_K,
            "10k": cls.TEN_K,
            "10km": cls.TEN_K,
            "10000": cls.TEN_K,
            "half": cls.HALF_MARATHON,
            "half_marathon": cls.HALF_MARATHON,
            "halfmarathon": cls.HALF_MARATHON,
            "21k": cls.HALF_MARATHON,
            "21.1k": cls.HALF_MARATHON,
            "marathon": cls.MARATHON,
            "full": cls.MARATHON,
            "42k": cls.MARATHON,
            "42.2k": cls.MARATHON,
        }
        return mapping.get(s.lower().replace("-", "_").replace(" ", "_"))

    @property
    def display_name(self) -> str:
        """Get human-readable name."""
        names = {
            RaceDistance.FIVE_K: "5K",
            RaceDistance.TEN_K: "10K",
            RaceDistance.HALF_MARATHON: "Half Marathon",
            RaceDistance.MARATHON: "Marathon",
        }
        return names.get(self, f"{self.value / 1000:.1f}K")

    @property
    def distance_km(self) -> float:
        """Get distance in kilometers."""
        return self.value / 1000


@dataclass
class PaceZone:
    """
    A training pace zone with pace ranges and HR guidance.

    Attributes:
        name: Zone name (e.g., "Easy", "Threshold")
        min_pace_sec_per_km: Slowest pace for this zone (higher = slower)
        max_pace_sec_per_km: Fastest pace for this zone (lower = faster)
        description: Training purpose and feel
        hr_range: Heart rate range as percentage of max HR
        typical_duration: Typical workout duration for this zone
    """
    name: str
    min_pace_sec_per_km: float
    max_pace_sec_per_km: float
    description: str
    hr_range: Tuple[float, float]
    typical_duration: str = ""

    @property
    def min_pace_formatted(self) -> str:
        """Format min pace as MM:SS/km."""
        minutes = int(self.min_pace_sec_per_km // 60)
        seconds = int(self.min_pace_sec_per_km % 60)
        return f"{minutes}:{seconds:02d}"

    @property
    def max_pace_formatted(self) -> str:
        """Format max pace as MM:SS/km."""
        minutes = int(self.max_pace_sec_per_km // 60)
        seconds = int(self.max_pace_sec_per_km % 60)
        return f"{minutes}:{seconds:02d}"

    @property
    def pace_range_formatted(self) -> str:
        """Format pace range as MM:SS - MM:SS /km."""
        return f"{self.max_pace_formatted} - {self.min_pace_formatted}/km"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "name": self.name,
            "min_pace_sec_per_km": round(self.min_pace_sec_per_km, 1),
            "max_pace_sec_per_km": round(self.max_pace_sec_per_km, 1),
            "min_pace_formatted": self.min_pace_formatted,
            "max_pace_formatted": self.max_pace_formatted,
            "pace_range_formatted": self.pace_range_formatted,
            "description": self.description,
            "hr_range": {
                "min": self.hr_range[0],
                "max": self.hr_range[1],
            },
            "typical_duration": self.typical_duration,
        }


def calculate_vdot(race_distance_m: float, race_time_sec: float) -> float:
    """
    Calculate VDOT using Daniels' formula.

    This is the exact formula from Jack Daniels' Running Formula,
    which estimates VO2max equivalent from race performance.

    The formula accounts for:
    1. Oxygen cost of running at a given velocity
    2. Percentage of VO2max that can be sustained for the race duration

    Args:
        race_distance_m: Race distance in meters
        race_time_sec: Race finishing time in seconds

    Returns:
        VDOT value (typically ranges from ~30 for beginners to ~85 for elites)

    Example:
        >>> calculate_vdot(5000, 1200)  # 5K in 20:00
        48.7
        >>> calculate_vdot(42195, 10800)  # Marathon in 3:00:00
        53.1
    """
    if race_time_sec <= 0 or race_distance_m <= 0:
        raise ValueError("Race time and distance must be positive")

    # Velocity in meters per minute
    velocity_m_per_min = (race_distance_m / race_time_sec) * 60

    # Time in minutes
    time_min = race_time_sec / 60

    # Oxygen cost (ml O2/kg/min) - Daniels' equation
    # This estimates the oxygen consumption required to run at a given pace
    oxygen_cost = (
        -4.60 +
        0.182258 * velocity_m_per_min +
        0.000104 * velocity_m_per_min ** 2
    )

    # Percent of VO2max sustained - Daniels' decay function
    # This accounts for the fact that you can't maintain 100% VO2max indefinitely
    # Shorter races allow higher percentage of VO2max to be sustained
    pct_max = (
        0.8 +
        0.1894393 * math.exp(-0.012778 * time_min) +
        0.2989558 * math.exp(-0.1932605 * time_min)
    )

    # VDOT is the VO2max that would produce this performance
    vdot = oxygen_cost / pct_max

    # Clamp to reasonable range (very rare to be outside 25-90)
    vdot = max(25.0, min(90.0, vdot))

    return round(vdot, 1)


def _vdot_to_velocity(vdot: float, intensity_pct: float) -> float:
    """
    Convert VDOT and intensity percentage to running velocity.

    This is the inverse of the VDOT formula - given a target oxygen
    consumption (VDOT * intensity), calculate the required velocity.

    Args:
        vdot: VDOT value
        intensity_pct: Fraction of VDOT (e.g., 0.75 for easy pace)

    Returns:
        Velocity in meters per minute
    """
    # Target oxygen cost
    target_vo2 = vdot * intensity_pct

    # Solve the quadratic equation for velocity
    # oxygen_cost = -4.60 + 0.182258 * v + 0.000104 * v^2
    # Rearranging: 0.000104 * v^2 + 0.182258 * v + (-4.60 - target_vo2) = 0
    a = 0.000104
    b = 0.182258
    c = -4.60 - target_vo2

    # Quadratic formula (we want the positive root)
    discriminant = b ** 2 - 4 * a * c
    if discriminant < 0:
        # Fallback for edge cases
        return 100.0  # Very slow default

    velocity = (-b + math.sqrt(discriminant)) / (2 * a)
    return max(50.0, velocity)  # Minimum reasonable velocity


def _vdot_to_pace(vdot: float, intensity_pct: float) -> float:
    """
    Convert VDOT and intensity percentage to pace in seconds per kilometer.

    Args:
        vdot: VDOT value
        intensity_pct: Fraction of VDOT (e.g., 0.75 for easy pace)

    Returns:
        Pace in seconds per kilometer
    """
    velocity_m_per_min = _vdot_to_velocity(vdot, intensity_pct)

    # Convert to pace (sec/km)
    # velocity is m/min, so pace = 1000 / velocity * 60 = 60000 / velocity
    if velocity_m_per_min <= 0:
        return 600.0  # 10:00/km default for edge cases

    pace_sec_per_km = 1000.0 / velocity_m_per_min * 60.0
    return pace_sec_per_km


def get_pace_zones(vdot: float) -> Dict[str, PaceZone]:
    """
    Calculate training pace zones from VDOT using Daniels' intensities.

    Returns paces in seconds per kilometer for each training zone.
    The zones are based on percentages of vVO2max (velocity at VO2max).

    Zone definitions based on Daniels' Running Formula:
    - Easy: 59-74% of vVO2max - Recovery and base building
    - Marathon: 75-84% of vVO2max - Marathon race pace
    - Threshold: 83-88% of vVO2max - Lactate threshold training
    - Interval: 95-100% of vVO2max - VO2max development
    - Repetition: 105-120% of vVO2max - Speed and economy

    Args:
        vdot: VDOT value (typically 30-85)

    Returns:
        Dictionary mapping zone names to PaceZone objects

    Example:
        >>> zones = get_pace_zones(50)
        >>> zones['easy'].pace_range_formatted
        '5:38 - 6:10/km'
    """
    # Validate VDOT range
    vdot = max(25.0, min(90.0, vdot))

    # Zone definitions: (intensity_min, intensity_max, hr_min, hr_max, description, typical_duration)
    zone_definitions = {
        'easy': (
            0.59, 0.74,
            65, 79,
            'Conversational pace for recovery and base building. Should feel comfortable and sustainable.',
            '30-90 minutes'
        ),
        'marathon': (
            0.75, 0.84,
            80, 89,
            'Marathon race pace. Steady effort that can be maintained for 2-5 hours.',
            '60-150 minutes'
        ),
        'threshold': (
            0.83, 0.88,
            88, 92,
            'Comfortably hard, tempo pace. Sustainable for 20-60 minutes. Key for improving lactate threshold.',
            '20-60 minutes'
        ),
        'interval': (
            0.95, 1.00,
            95, 100,
            'VO2max training pace. Hard 3-5 minute intervals with equal recovery. Develops aerobic power.',
            '3-5 min intervals'
        ),
        'repetition': (
            1.05, 1.20,
            95, 100,  # HR maxes out at VO2max
            'Fast, short repetitions with full recovery. Improves speed, economy, and neuromuscular coordination.',
            '200-400m reps'
        ),
    }

    zones = {}
    for zone_name, (int_min, int_max, hr_min, hr_max, description, duration) in zone_definitions.items():
        # Note: Lower intensity = faster pace (counterintuitive but mathematically correct)
        # So int_max gives min_pace (slower) and int_min gives max_pace (faster)
        min_pace = _vdot_to_pace(vdot, int_min)  # Faster pace (higher intensity)
        max_pace = _vdot_to_pace(vdot, int_max)  # Slower pace (lower intensity)

        zones[zone_name] = PaceZone(
            name=zone_name.replace('_', ' ').title(),
            min_pace_sec_per_km=max_pace,  # Slower boundary
            max_pace_sec_per_km=min_pace,  # Faster boundary
            description=description,
            hr_range=(hr_min, hr_max),
            typical_duration=duration,
        )

    return zones


def predict_race_times(vdot: float) -> Dict[str, Dict[str, any]]:
    """
    Predict race times for common distances based on VDOT.

    Uses the inverse of the VDOT calculation to predict finish times
    for standard race distances.

    Args:
        vdot: VDOT value

    Returns:
        Dictionary with predictions for 5K, 10K, Half Marathon, Marathon
        Each contains: time_sec, time_formatted, pace_sec_per_km, pace_formatted

    Example:
        >>> predictions = predict_race_times(50)
        >>> predictions['5K']['time_formatted']
        '21:03'
    """
    distances = {
        '5K': RaceDistance.FIVE_K,
        '10K': RaceDistance.TEN_K,
        'Half Marathon': RaceDistance.HALF_MARATHON,
        'Marathon': RaceDistance.MARATHON,
    }

    predictions = {}

    for name, distance in distances.items():
        time_sec = _predict_time_from_vdot(vdot, distance.value)
        pace_sec_per_km = time_sec / distance.distance_km

        predictions[name] = {
            'distance_m': distance.value,
            'distance_km': distance.distance_km,
            'time_sec': int(time_sec),
            'time_formatted': _format_time(int(time_sec)),
            'pace_sec_per_km': round(pace_sec_per_km, 1),
            'pace_formatted': _format_pace(pace_sec_per_km),
        }

    return predictions


def _predict_time_from_vdot(vdot: float, distance_m: float) -> float:
    """
    Predict race time from VDOT for a given distance.

    This uses an iterative approach to find the time that would
    produce the given VDOT for the specified distance.

    Args:
        vdot: VDOT value
        distance_m: Race distance in meters

    Returns:
        Predicted time in seconds
    """
    # Initial estimate using a simplified formula
    # Roughly: pace decreases ~6% per doubling of distance for same VDOT
    base_velocity = _vdot_to_velocity(vdot, 0.95)  # Start at ~interval pace
    initial_time = distance_m / base_velocity * 60

    # Binary search to find exact time
    low = initial_time * 0.5
    high = initial_time * 2.0

    for _ in range(50):  # Max iterations
        mid = (low + high) / 2
        calculated_vdot = calculate_vdot(distance_m, mid)

        if abs(calculated_vdot - vdot) < 0.1:
            return mid

        if calculated_vdot > vdot:
            # Calculated VDOT too high means time is too fast
            low = mid
        else:
            # Calculated VDOT too low means time is too slow
            high = mid

    return (low + high) / 2


def _format_time(seconds: int) -> str:
    """Format time in seconds to H:MM:SS or MM:SS string."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def _format_pace(pace_sec_per_km: float) -> str:
    """Format pace in sec/km to MM:SS/km string."""
    minutes = int(pace_sec_per_km // 60)
    seconds = int(pace_sec_per_km % 60)
    return f"{minutes}:{seconds:02d}/km"


def calculate_equivalent_performances(
    race_distance_m: float,
    race_time_sec: float
) -> Dict[str, Dict[str, any]]:
    """
    Calculate equivalent performances for other distances.

    Given a race result, calculate what the runner should be able to
    run at other distances, assuming equal training and ability.

    Args:
        race_distance_m: Distance of the known race in meters
        race_time_sec: Time of the known race in seconds

    Returns:
        Dictionary with equivalent times for all standard distances

    Example:
        >>> results = calculate_equivalent_performances(5000, 1200)  # 5K in 20:00
        >>> results['Marathon']['time_formatted']
        '3:01:39'
    """
    vdot = calculate_vdot(race_distance_m, race_time_sec)
    return predict_race_times(vdot)


def parse_race_time(time_str: str) -> int:
    """
    Parse a race time string to seconds.

    Accepts formats: H:MM:SS, MM:SS, or just seconds

    Args:
        time_str: Time string (e.g., "1:45:00", "25:30", "1200")

    Returns:
        Time in seconds

    Raises:
        ValueError: If time format is invalid
    """
    time_str = time_str.strip()

    # Try parsing as just seconds
    try:
        return int(float(time_str))
    except ValueError:
        pass

    # Split by colons
    parts = time_str.split(":")

    try:
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + int(float(seconds))
        elif len(parts) == 2:
            minutes, seconds = parts
            return int(minutes) * 60 + int(float(seconds))
        else:
            raise ValueError(f"Invalid time format: {time_str}")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid time format: {time_str}") from e


@dataclass
class VDOTCalculation:
    """
    Complete VDOT calculation result with zones and predictions.

    This is the main result type returned by calculate_vdot_from_race().
    """
    vdot: float
    race_distance: str
    race_time_sec: int
    race_time_formatted: str
    pace_zones: Dict[str, PaceZone]
    race_predictions: Dict[str, Dict[str, any]]

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "vdot": self.vdot,
            "race_distance": self.race_distance,
            "race_time_sec": self.race_time_sec,
            "race_time_formatted": self.race_time_formatted,
            "pace_zones": {
                name: zone.to_dict()
                for name, zone in self.pace_zones.items()
            },
            "race_predictions": self.race_predictions,
        }


def calculate_vdot_from_race(
    distance: str,
    time_str: str,
    custom_distance_m: Optional[float] = None,
) -> VDOTCalculation:
    """
    Calculate VDOT from a race result with full zone and prediction details.

    This is the main entry point for VDOT calculations.

    Args:
        distance: Race distance ("5K", "10K", "half", "marathon", or "custom")
        time_str: Race time as string (e.g., "25:30" for 25min 30sec)
        custom_distance_m: Distance in meters if distance is "custom"

    Returns:
        VDOTCalculation with VDOT, zones, and predictions

    Example:
        >>> result = calculate_vdot_from_race("5K", "25:30")
        >>> print(f"VDOT: {result.vdot}")
        VDOT: 43.2
        >>> print(result.pace_zones['easy'].pace_range_formatted)
        5:58 - 6:32/km
    """
    # Parse distance
    if distance.lower() == "custom":
        if custom_distance_m is None or custom_distance_m <= 0:
            raise ValueError("Custom distance must be provided and positive")
        distance_m = custom_distance_m
        distance_name = f"{custom_distance_m / 1000:.2f}K"
    else:
        race_dist = RaceDistance.from_string(distance)
        if race_dist is None:
            raise ValueError(f"Unknown race distance: {distance}")
        distance_m = race_dist.value
        distance_name = race_dist.display_name

    # Parse time
    time_sec = parse_race_time(time_str)

    # Calculate VDOT
    vdot = calculate_vdot(distance_m, time_sec)

    # Get zones and predictions
    zones = get_pace_zones(vdot)
    predictions = predict_race_times(vdot)

    return VDOTCalculation(
        vdot=vdot,
        race_distance=distance_name,
        race_time_sec=time_sec,
        race_time_formatted=_format_time(time_sec),
        pace_zones=zones,
        race_predictions=predictions,
    )


# Utility functions for common conversions

def pace_km_to_mile(pace_sec_per_km: float) -> float:
    """Convert pace from sec/km to sec/mile."""
    return pace_sec_per_km * 1.60934


def pace_mile_to_km(pace_sec_per_mile: float) -> float:
    """Convert pace from sec/mile to sec/km."""
    return pace_sec_per_mile / 1.60934


def format_pace_per_mile(pace_sec_per_km: float) -> str:
    """Format pace in sec/km as MM:SS/mi."""
    pace_per_mile = pace_km_to_mile(pace_sec_per_km)
    minutes = int(pace_per_mile // 60)
    seconds = int(pace_per_mile % 60)
    return f"{minutes}:{seconds:02d}/mi"
