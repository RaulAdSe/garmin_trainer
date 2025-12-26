"""Heart rate zone calculations."""

from dataclasses import dataclass
from typing import Tuple, List


@dataclass
class HRZones:
    """Heart rate training zones."""

    zone1: Tuple[int, int]  # Recovery / Easy
    zone2: Tuple[int, int]  # Aerobic / Endurance
    zone3: Tuple[int, int]  # Tempo / Moderate
    zone4: Tuple[int, int]  # Threshold / Hard
    zone5: Tuple[int, int]  # VO2max / Maximum

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "zone1": {"min": self.zone1[0], "max": self.zone1[1], "name": "Recovery"},
            "zone2": {"min": self.zone2[0], "max": self.zone2[1], "name": "Aerobic"},
            "zone3": {"min": self.zone3[0], "max": self.zone3[1], "name": "Tempo"},
            "zone4": {"min": self.zone4[0], "max": self.zone4[1], "name": "Threshold"},
            "zone5": {"min": self.zone5[0], "max": self.zone5[1], "name": "VO2max"},
        }

    def get_zone_ranges(self) -> List[Tuple[int, int, int, str]]:
        """Get all zones as list of (zone_num, min_hr, max_hr, name)."""
        return [
            (1, self.zone1[0], self.zone1[1], "Recovery"),
            (2, self.zone2[0], self.zone2[1], "Aerobic"),
            (3, self.zone3[0], self.zone3[1], "Tempo"),
            (4, self.zone4[0], self.zone4[1], "Threshold"),
            (5, self.zone5[0], self.zone5[1], "VO2max"),
        ]


def calculate_hr_zones_karvonen(max_hr: int, rest_hr: int) -> HRZones:
    """
    Calculate HR zones using Karvonen (Heart Rate Reserve) method.

    This method uses the heart rate reserve (HRR = max_hr - rest_hr)
    to set zones based on percentage of reserve.

    Zone boundaries (% of HRR):
    - Zone 1: 50-60% - Recovery
    - Zone 2: 60-70% - Aerobic
    - Zone 3: 70-80% - Tempo
    - Zone 4: 80-90% - Threshold
    - Zone 5: 90-100% - VO2max

    Args:
        max_hr: Maximum heart rate
        rest_hr: Resting heart rate

    Returns:
        HRZones with calculated boundaries
    """
    hr_reserve = max_hr - rest_hr

    def zone_hr(pct: float) -> int:
        return int(rest_hr + (hr_reserve * pct))

    return HRZones(
        zone1=(zone_hr(0.50), zone_hr(0.60)),
        zone2=(zone_hr(0.60), zone_hr(0.70)),
        zone3=(zone_hr(0.70), zone_hr(0.80)),
        zone4=(zone_hr(0.80), zone_hr(0.90)),
        zone5=(zone_hr(0.90), max_hr),
    )


def calculate_hr_zones_lthr(lthr: int, max_hr: int) -> HRZones:
    """
    Calculate HR zones based on Lactate Threshold Heart Rate (LTHR).

    This method uses percentages of LTHR, which is often more accurate
    for trained athletes. LTHR is typically ~90% of max HR but varies.

    Zone boundaries (% of LTHR):
    - Zone 1: 65-80% - Recovery
    - Zone 2: 80-89% - Aerobic
    - Zone 3: 89-93% - Tempo
    - Zone 4: 93-99% - Threshold
    - Zone 5: 99%+ - VO2max

    Based on Joe Friel's zone system.

    Args:
        lthr: Lactate Threshold Heart Rate
        max_hr: Maximum heart rate (for zone 5 upper bound)

    Returns:
        HRZones with calculated boundaries
    """
    return HRZones(
        zone1=(int(lthr * 0.65), int(lthr * 0.80)),
        zone2=(int(lthr * 0.80), int(lthr * 0.89)),
        zone3=(int(lthr * 0.89), int(lthr * 0.93)),
        zone4=(int(lthr * 0.93), int(lthr * 0.99)),
        zone5=(int(lthr * 0.99), max_hr),
    )


def calculate_hr_zones_max_hr(max_hr: int) -> HRZones:
    """
    Calculate HR zones based on maximum heart rate only.

    This is a simpler method when resting HR is unknown.
    Less personalized but still useful.

    Zone boundaries (% of max HR):
    - Zone 1: 50-60% - Recovery
    - Zone 2: 60-70% - Aerobic
    - Zone 3: 70-80% - Tempo
    - Zone 4: 80-90% - Threshold
    - Zone 5: 90-100% - VO2max

    Args:
        max_hr: Maximum heart rate

    Returns:
        HRZones with calculated boundaries
    """
    return HRZones(
        zone1=(int(max_hr * 0.50), int(max_hr * 0.60)),
        zone2=(int(max_hr * 0.60), int(max_hr * 0.70)),
        zone3=(int(max_hr * 0.70), int(max_hr * 0.80)),
        zone4=(int(max_hr * 0.80), int(max_hr * 0.90)),
        zone5=(int(max_hr * 0.90), max_hr),
    )


def get_zone_for_hr(hr: int, zones: HRZones) -> int:
    """
    Return zone number (1-5) for a given heart rate.

    Args:
        hr: Heart rate to classify
        zones: HRZones object with zone boundaries

    Returns:
        Zone number (1-5), or 0 if below zone 1
    """
    if hr < zones.zone1[0]:
        return 0  # Below zone 1
    elif hr <= zones.zone1[1]:
        return 1
    elif hr <= zones.zone2[1]:
        return 2
    elif hr <= zones.zone3[1]:
        return 3
    elif hr <= zones.zone4[1]:
        return 4
    else:
        return 5


def calculate_zone_time_distribution(
    hr_samples: List[int],
    zones: HRZones,
) -> dict:
    """
    Calculate time spent in each zone from HR samples.

    Args:
        hr_samples: List of heart rate values (one per time unit)
        zones: HRZones object with zone boundaries

    Returns:
        Dictionary with zone percentages and counts
    """
    if not hr_samples:
        return {
            "zone1_pct": 0.0,
            "zone2_pct": 0.0,
            "zone3_pct": 0.0,
            "zone4_pct": 0.0,
            "zone5_pct": 0.0,
            "total_samples": 0,
        }

    zone_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 0: 0}

    for hr in hr_samples:
        zone = get_zone_for_hr(hr, zones)
        zone_counts[zone] = zone_counts.get(zone, 0) + 1

    total = len(hr_samples)

    return {
        "zone1_pct": round(zone_counts[1] / total * 100, 1),
        "zone2_pct": round(zone_counts[2] / total * 100, 1),
        "zone3_pct": round(zone_counts[3] / total * 100, 1),
        "zone4_pct": round(zone_counts[4] / total * 100, 1),
        "zone5_pct": round(zone_counts[5] / total * 100, 1),
        "below_zone1_pct": round(zone_counts[0] / total * 100, 1),
        "total_samples": total,
    }


def estimate_max_hr_from_age(age: int) -> int:
    """
    Estimate maximum heart rate from age using Tanaka formula.

    Tanaka formula: 208 - (0.7 * age)
    More accurate than the older 220 - age formula.

    Args:
        age: Age in years

    Returns:
        Estimated maximum heart rate
    """
    return int(208 - (0.7 * age))


def estimate_lthr_from_max_hr(max_hr: int) -> int:
    """
    Estimate lactate threshold heart rate from max HR.

    LTHR is typically around 90% of max HR for trained athletes,
    though it can vary significantly (85-95%).

    Args:
        max_hr: Maximum heart rate

    Returns:
        Estimated lactate threshold heart rate
    """
    return int(max_hr * 0.90)
