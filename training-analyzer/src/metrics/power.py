"""Cycling power metrics calculations (NP, IF, TSS, power zones)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass
class PowerZones:
    """
    Power training zones based on FTP (Functional Threshold Power).

    Uses the classic 7-zone Coggan model:
    - Zone 1: Active Recovery (<55% FTP)
    - Zone 2: Endurance (55-75% FTP)
    - Zone 3: Tempo (75-90% FTP)
    - Zone 4: Threshold (90-105% FTP)
    - Zone 5: VO2max (105-120% FTP)
    - Zone 6: Anaerobic (120-150% FTP)
    - Zone 7: Neuromuscular (>150% FTP)
    """
    ftp: int
    zone1: Tuple[int, int] = field(default=(0, 0))
    zone2: Tuple[int, int] = field(default=(0, 0))
    zone3: Tuple[int, int] = field(default=(0, 0))
    zone4: Tuple[int, int] = field(default=(0, 0))
    zone5: Tuple[int, int] = field(default=(0, 0))
    zone6: Tuple[int, int] = field(default=(0, 0))
    zone7: Tuple[int, int] = field(default=(0, 0))
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Calculate zones based on FTP if not provided."""
        if self.ftp > 0 and self.zone1 == (0, 0):
            zones = calculate_power_zones(self.ftp)
            self.zone1 = zones[1]
            self.zone2 = zones[2]
            self.zone3 = zones[3]
            self.zone4 = zones[4]
            self.zone5 = zones[5]
            self.zone6 = zones[6]
            self.zone7 = zones[7]
        if self.updated_at is None:
            self.updated_at = datetime.now()

    def get_zone(self, zone_num: int) -> Tuple[int, int]:
        """Get zone range by number (1-7)."""
        zone_map = {
            1: self.zone1,
            2: self.zone2,
            3: self.zone3,
            4: self.zone4,
            5: self.zone5,
            6: self.zone6,
            7: self.zone7,
        }
        return zone_map.get(zone_num, (0, 0))

    def get_zone_for_power(self, power: int) -> int:
        """Return zone number (1-7) for a given power value."""
        if power < 0:
            return 0
        zones = [self.zone1, self.zone2, self.zone3, self.zone4,
                 self.zone5, self.zone6, self.zone7]
        for i, (min_w, max_w) in enumerate(zones, 1):
            if power <= max_w:
                return i
        return 7

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        zone_names = get_power_zone_names()
        return {
            "ftp": self.ftp,
            "zones": {
                f"zone{i}": {
                    "name": zone_names[i],
                    "min": self.get_zone(i)[0],
                    "max": self.get_zone(i)[1],
                }
                for i in range(1, 8)
            },
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def format_zones(self) -> str:
        """Format zones for prompt injection."""
        zone_names = get_power_zone_names()
        lines = []
        for i in range(1, 8):
            min_w, max_w = self.get_zone(i)
            lines.append(f"Z{i} ({zone_names[i]}): {min_w}-{max_w}W")
        return ", ".join(lines)

    @classmethod
    def from_dict(cls, data: Dict) -> "PowerZones":
        """Create PowerZones from dictionary."""
        zones_data = data.get("zones", {})
        return cls(
            ftp=data.get("ftp", 0),
            zone1=tuple(zones_data.get("zone1", {}).values())[:2] if zones_data.get("zone1") else (0, 0),
            zone2=tuple(zones_data.get("zone2", {}).values())[:2] if zones_data.get("zone2") else (0, 0),
            zone3=tuple(zones_data.get("zone3", {}).values())[:2] if zones_data.get("zone3") else (0, 0),
            zone4=tuple(zones_data.get("zone4", {}).values())[:2] if zones_data.get("zone4") else (0, 0),
            zone5=tuple(zones_data.get("zone5", {}).values())[:2] if zones_data.get("zone5") else (0, 0),
            zone6=tuple(zones_data.get("zone6", {}).values())[:2] if zones_data.get("zone6") else (0, 0),
            zone7=tuple(zones_data.get("zone7", {}).values())[:2] if zones_data.get("zone7") else (0, 0),
        )


@dataclass
class CyclingAthleteContext:
    """
    Cycling-specific athlete context for personalized workout analysis and design.

    Contains FTP, power zones, and cycling-specific training metrics.
    """
    # Functional Threshold Power (1-hour max sustainable power)
    ftp: int = 200

    # FTP test date for staleness tracking
    ftp_test_date: Optional[datetime] = None

    # Power zones (auto-calculated from FTP)
    power_zones: Optional[PowerZones] = None

    # Cycling-specific fitness metrics
    cycling_ctl: float = 30.0  # Cycling-specific Chronic Training Load
    cycling_atl: float = 30.0  # Cycling-specific Acute Training Load
    cycling_tsb: float = 0.0   # Cycling-specific TSB

    # Efficiency metrics
    typical_efficiency_factor: Optional[float] = None  # NP/HR typical value
    power_to_weight: Optional[float] = None  # W/kg at FTP

    # Athlete weight (for W/kg calculations)
    weight_kg: Optional[float] = None

    # Training preferences
    preferred_indoor_outdoor: str = "outdoor"  # indoor, outdoor, both

    def __post_init__(self):
        """Initialize power zones from FTP if not provided."""
        if self.power_zones is None and self.ftp > 0:
            self.power_zones = PowerZones(ftp=self.ftp)
        if self.weight_kg and self.ftp:
            self.power_to_weight = round(self.ftp / self.weight_kg, 2)

    def update_ftp(self, new_ftp: int, test_date: Optional[datetime] = None):
        """Update FTP and recalculate zones."""
        self.ftp = new_ftp
        self.ftp_test_date = test_date or datetime.now()
        self.power_zones = PowerZones(ftp=new_ftp, updated_at=self.ftp_test_date)
        if self.weight_kg:
            self.power_to_weight = round(self.ftp / self.weight_kg, 2)

    def get_target_power_range(self, zone: int) -> Tuple[int, int]:
        """Get target power range for a zone."""
        if self.power_zones:
            return self.power_zones.get_zone(zone)
        # Fallback calculation
        zones = calculate_power_zones(self.ftp)
        return zones.get(zone, (0, 0))

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "ftp": self.ftp,
            "ftp_test_date": self.ftp_test_date.isoformat() if self.ftp_test_date else None,
            "power_zones": self.power_zones.to_dict() if self.power_zones else None,
            "cycling_ctl": self.cycling_ctl,
            "cycling_atl": self.cycling_atl,
            "cycling_tsb": self.cycling_tsb,
            "typical_efficiency_factor": self.typical_efficiency_factor,
            "power_to_weight": self.power_to_weight,
            "weight_kg": self.weight_kg,
            "preferred_indoor_outdoor": self.preferred_indoor_outdoor,
        }

    def to_prompt_context(self) -> str:
        """Convert to formatted string for LLM prompt injection."""
        lines = [
            f"FTP: {self.ftp}W",
        ]
        if self.power_to_weight:
            lines.append(f"Power-to-Weight: {self.power_to_weight} W/kg")
        if self.power_zones:
            lines.append(f"Power Zones: {self.power_zones.format_zones()}")
        lines.extend([
            f"Cycling CTL: {self.cycling_ctl:.1f} | ATL: {self.cycling_atl:.1f} | TSB: {self.cycling_tsb:.1f}",
        ])
        if self.typical_efficiency_factor:
            lines.append(f"Typical Efficiency Factor: {self.typical_efficiency_factor:.2f}")
        return "\n".join(lines)

    @classmethod
    def from_dict(cls, data: Dict) -> "CyclingAthleteContext":
        """Create CyclingAthleteContext from dictionary."""
        power_zones = None
        if data.get("power_zones"):
            power_zones = PowerZones.from_dict(data["power_zones"])

        ftp_test_date = None
        if data.get("ftp_test_date"):
            if isinstance(data["ftp_test_date"], str):
                ftp_test_date = datetime.fromisoformat(data["ftp_test_date"])
            else:
                ftp_test_date = data["ftp_test_date"]

        return cls(
            ftp=data.get("ftp", 200),
            ftp_test_date=ftp_test_date,
            power_zones=power_zones,
            cycling_ctl=data.get("cycling_ctl", 30.0),
            cycling_atl=data.get("cycling_atl", 30.0),
            cycling_tsb=data.get("cycling_tsb", 0.0),
            typical_efficiency_factor=data.get("typical_efficiency_factor"),
            power_to_weight=data.get("power_to_weight"),
            weight_kg=data.get("weight_kg"),
            preferred_indoor_outdoor=data.get("preferred_indoor_outdoor", "outdoor"),
        )


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
