"""Training metrics calculations."""

from .load import calculate_hrss, calculate_trimp
from .fitness import (
    FitnessMetrics,
    calculate_ewma,
    calculate_fitness_metrics,
)
from .zones import (
    HRZones,
    calculate_hr_zones_karvonen,
    calculate_hr_zones_lthr,
    get_zone_for_hr,
)
from .power import (
    calculate_normalized_power,
    calculate_intensity_factor,
    calculate_tss,
    calculate_tss_simple,
    calculate_variability_index,
    calculate_power_zones,
    get_power_zone_names,
    get_zone_for_power,
    estimate_ftp_from_20min_power,
    estimate_ftp_from_ramp_test,
    get_power_zone_distribution,
    calculate_efficiency_factor,
    calculate_power_to_weight,
    calculate_work,
)

__all__ = [
    # Load calculations
    "calculate_hrss",
    "calculate_trimp",
    # Fitness model
    "FitnessMetrics",
    "calculate_ewma",
    "calculate_fitness_metrics",
    # HR Zones
    "HRZones",
    "calculate_hr_zones_karvonen",
    "calculate_hr_zones_lthr",
    "get_zone_for_hr",
    # Power metrics (cycling)
    "calculate_normalized_power",
    "calculate_intensity_factor",
    "calculate_tss",
    "calculate_tss_simple",
    "calculate_variability_index",
    "calculate_power_zones",
    "get_power_zone_names",
    "get_zone_for_power",
    "estimate_ftp_from_20min_power",
    "estimate_ftp_from_ramp_test",
    "get_power_zone_distribution",
    "calculate_efficiency_factor",
    "calculate_power_to_weight",
    "calculate_work",
]
