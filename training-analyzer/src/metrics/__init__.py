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
    # Power zone dataclasses
    PowerZones,
    CyclingAthleteContext,
    # Power calculations
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
from .swim import (
    # Core swim calculations
    calculate_swolf,
    calculate_stroke_rate,
    calculate_pace_per_100m,
    calculate_css,
    calculate_swim_tss,
    calculate_swim_zones,
    calculate_stroke_efficiency,
    calculate_swim_efficiency_index,
    # Aliases and utilities
    estimate_swim_tss,
    get_swim_zones,
    get_swim_zone_for_pace,
    format_swim_pace,
    # Analysis functions
    analyze_stroke_efficiency,
    analyze_swim_session,
    estimate_css_from_race_times,
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
    # Power zone dataclasses
    "PowerZones",
    "CyclingAthleteContext",
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
    # Swim metrics
    "calculate_swolf",
    "calculate_stroke_rate",
    "calculate_pace_per_100m",
    "calculate_css",
    "calculate_swim_tss",
    "calculate_swim_zones",
    "calculate_stroke_efficiency",
    "calculate_swim_efficiency_index",
    "estimate_swim_tss",
    "get_swim_zones",
    "get_swim_zone_for_pace",
    "format_swim_pace",
    "analyze_stroke_efficiency",
    "analyze_swim_session",
    "estimate_css_from_race_times",
]
