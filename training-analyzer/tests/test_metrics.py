"""Tests for training metrics calculations."""

import math
import pytest
from datetime import date, timedelta

from training_analyzer.metrics.load import (
    calculate_hrss,
    calculate_trimp,
    calculate_relative_effort,
)
from training_analyzer.metrics.fitness import (
    FitnessMetrics,
    calculate_ewma,
    calculate_fitness_metrics,
    determine_risk_zone,
    get_training_recommendation,
)
from training_analyzer.metrics.zones import (
    HRZones,
    calculate_hr_zones_karvonen,
    calculate_hr_zones_lthr,
    calculate_hr_zones_max_hr,
    get_zone_for_hr,
    calculate_zone_time_distribution,
    estimate_max_hr_from_age,
    estimate_lthr_from_max_hr,
)


class TestHRSSCalculation:
    """Tests for Heart Rate Stress Score calculation."""

    def test_hrss_at_threshold_for_one_hour(self):
        """One hour at threshold should give approximately 100 HRSS."""
        hrss = calculate_hrss(
            duration_min=60,
            avg_hr=165,
            threshold_hr=165,
            max_hr=185,
            rest_hr=55,
        )
        # At threshold for 1 hour = 100 HRSS
        assert abs(hrss - 100) < 1, f"Expected ~100, got {hrss}"

    def test_hrss_below_threshold(self):
        """Below threshold should give less than 100 HRSS for one hour."""
        hrss = calculate_hrss(
            duration_min=60,
            avg_hr=140,  # Well below threshold
            threshold_hr=165,
            max_hr=185,
            rest_hr=55,
        )
        assert hrss < 100, f"Expected < 100, got {hrss}"
        assert hrss > 0, f"Expected > 0, got {hrss}"

    def test_hrss_above_threshold(self):
        """Above threshold should give more than 100 HRSS for one hour."""
        hrss = calculate_hrss(
            duration_min=60,
            avg_hr=175,  # Above threshold
            threshold_hr=165,
            max_hr=185,
            rest_hr=55,
        )
        assert hrss > 100, f"Expected > 100, got {hrss}"

    def test_hrss_scales_with_duration(self):
        """HRSS should scale linearly with duration at same intensity."""
        hrss_30min = calculate_hrss(
            duration_min=30,
            avg_hr=165,
            threshold_hr=165,
            max_hr=185,
            rest_hr=55,
        )
        hrss_60min = calculate_hrss(
            duration_min=60,
            avg_hr=165,
            threshold_hr=165,
            max_hr=185,
            rest_hr=55,
        )
        # Should be approximately 2x for 2x duration
        ratio = hrss_60min / hrss_30min
        assert 1.9 < ratio < 2.1, f"Expected ratio ~2, got {ratio}"

    def test_hrss_zero_hr_reserve(self):
        """Should return 0 if HR reserve is zero or negative."""
        hrss = calculate_hrss(
            duration_min=60,
            avg_hr=100,
            threshold_hr=100,
            max_hr=100,  # Same as rest_hr
            rest_hr=100,
        )
        assert hrss == 0.0

    def test_hrss_typical_easy_run(self):
        """Typical easy run values should give reasonable HRSS."""
        hrss = calculate_hrss(
            duration_min=45,
            avg_hr=135,  # Easy pace
            threshold_hr=165,
            max_hr=185,
            rest_hr=55,
        )
        # Easy 45 min run should be roughly 30-50 HRSS
        assert 20 < hrss < 60, f"Expected 20-60, got {hrss}"


class TestTRIMPCalculation:
    """Tests for Training Impulse calculation."""

    def test_trimp_male_basic(self):
        """Basic TRIMP calculation for male."""
        trimp = calculate_trimp(
            duration_min=60,
            avg_hr=150,
            rest_hr=55,
            max_hr=185,
            gender="male",
        )
        # TRIMP for 1 hour at moderate intensity should be substantial
        assert trimp > 50, f"Expected > 50, got {trimp}"
        assert trimp < 200, f"Expected < 200, got {trimp}"

    def test_trimp_female_basic(self):
        """Basic TRIMP calculation for female."""
        trimp = calculate_trimp(
            duration_min=60,
            avg_hr=150,
            rest_hr=55,
            max_hr=185,
            gender="female",
        )
        # Female TRIMP should be similar magnitude but different due to coefficients
        assert trimp > 50
        assert trimp < 200

    def test_trimp_male_vs_female_difference(self):
        """Male and female TRIMP should differ due to different coefficients."""
        trimp_male = calculate_trimp(
            duration_min=60,
            avg_hr=150,
            rest_hr=55,
            max_hr=185,
            gender="male",
        )
        trimp_female = calculate_trimp(
            duration_min=60,
            avg_hr=150,
            rest_hr=55,
            max_hr=185,
            gender="female",
        )
        # They should be different (female coefficients are different)
        assert trimp_male != trimp_female

    def test_trimp_increases_with_intensity(self):
        """Higher intensity should give higher TRIMP."""
        trimp_low = calculate_trimp(
            duration_min=60,
            avg_hr=120,
            rest_hr=55,
            max_hr=185,
            gender="male",
        )
        trimp_high = calculate_trimp(
            duration_min=60,
            avg_hr=170,
            rest_hr=55,
            max_hr=185,
            gender="male",
        )
        assert trimp_high > trimp_low * 2, "High intensity should be much higher due to exponential"

    def test_trimp_zero_hr_reserve(self):
        """Should return 0 if HR reserve is zero or negative."""
        trimp = calculate_trimp(
            duration_min=60,
            avg_hr=100,
            rest_hr=100,
            max_hr=100,
            gender="male",
        )
        assert trimp == 0.0


class TestRelativeEffort:
    """Tests for relative effort calculation."""

    def test_relative_effort_basic(self):
        """Basic relative effort calculation."""
        effort = calculate_relative_effort(
            duration_min=60,
            avg_hr=150,
            max_hr=185,
            rest_hr=55,
        )
        assert effort > 0
        assert effort < 500

    def test_relative_effort_scales_with_duration(self):
        """Relative effort should scale with duration."""
        effort_30 = calculate_relative_effort(30, 150, 185, 55)
        effort_60 = calculate_relative_effort(60, 150, 185, 55)
        assert effort_60 > effort_30


class TestEWMACalculation:
    """Tests for Exponentially Weighted Moving Average."""

    def test_ewma_decay(self):
        """EWMA should decay towards current value."""
        # Start with 100, add 0s - should decay
        ewma = 100.0
        for _ in range(7):
            ewma = calculate_ewma(0, ewma, 7)
        # After 7 days of zeros with TC=7, should be at ~37% of original
        expected = 100 * math.exp(-1)  # ~36.8
        assert abs(ewma - expected) < 1, f"Expected ~{expected}, got {ewma}"

    def test_ewma_buildup(self):
        """EWMA should build up with consistent load."""
        ewma = 0.0
        for _ in range(42):
            ewma = calculate_ewma(100, ewma, 42)
        # After 42 days of 100 with TC=42, should be at ~63% of 100
        expected = 100 * (1 - math.exp(-1))  # ~63.2
        assert abs(ewma - expected) < 1, f"Expected ~{expected}, got {ewma}"

    def test_ewma_steady_state(self):
        """EWMA should reach steady state with constant input."""
        ewma = 0.0
        for _ in range(200):  # Many iterations
            ewma = calculate_ewma(100, ewma, 42)
        # Should converge to 100
        assert abs(ewma - 100) < 1, f"Expected ~100, got {ewma}"


class TestFitnessMetrics:
    """Tests for fitness metrics calculation (CTL/ATL/TSB/ACWR)."""

    def test_fitness_metrics_basic(self):
        """Basic fitness metrics calculation."""
        loads = [
            (date(2024, 1, 1), 100.0),
            (date(2024, 1, 2), 50.0),
            (date(2024, 1, 3), 0.0),
            (date(2024, 1, 4), 75.0),
        ]
        results = calculate_fitness_metrics(loads)

        assert len(results) == 4
        assert all(isinstance(r, FitnessMetrics) for r in results)
        assert results[0].date == date(2024, 1, 1)

    def test_fitness_metrics_tsb_calculation(self):
        """TSB should equal CTL - ATL."""
        loads = [(date(2024, 1, i), 100.0) for i in range(1, 31)]
        results = calculate_fitness_metrics(loads)

        for r in results:
            expected_tsb = r.ctl - r.atl
            # Tolerance of 0.5 to account for rounding in individual components
            assert abs(r.tsb - expected_tsb) < 0.5

    def test_fitness_metrics_acwr(self):
        """ACWR should be ATL / CTL."""
        # Build up fitness first - use multiple months to get 50 days
        loads = [(date(2024, 1, i), 100.0) for i in range(1, 32)]  # Jan
        loads += [(date(2024, 2, i), 100.0) for i in range(1, 20)]  # Feb 1-19
        results = calculate_fitness_metrics(loads)

        # Check ACWR for later entries where CTL is significant
        last_result = results[-1]
        if last_result.ctl > 10:
            expected_acwr = last_result.atl / last_result.ctl
            assert abs(last_result.acwr - expected_acwr) < 0.01

    def test_fitness_metrics_ordering(self):
        """Results should be in date order."""
        loads = [
            (date(2024, 1, 5), 100.0),
            (date(2024, 1, 1), 100.0),
            (date(2024, 1, 3), 100.0),
        ]
        results = calculate_fitness_metrics(loads)

        dates = [r.date for r in results]
        assert dates == sorted(dates)

    def test_fitness_metrics_empty_input(self):
        """Should handle empty input."""
        results = calculate_fitness_metrics([])
        assert results == []


class TestRiskZone:
    """Tests for ACWR risk zone classification."""

    def test_undertrained_zone(self):
        """ACWR < 0.8 should be undertrained."""
        assert determine_risk_zone(0.5) == "undertrained"
        assert determine_risk_zone(0.79) == "undertrained"

    def test_optimal_zone(self):
        """ACWR 0.8-1.3 should be optimal."""
        assert determine_risk_zone(0.8) == "optimal"
        assert determine_risk_zone(1.0) == "optimal"
        assert determine_risk_zone(1.3) == "optimal"

    def test_caution_zone(self):
        """ACWR 1.3-1.5 should be caution."""
        assert determine_risk_zone(1.31) == "caution"
        assert determine_risk_zone(1.4) == "caution"
        assert determine_risk_zone(1.5) == "caution"

    def test_danger_zone(self):
        """ACWR > 1.5 should be danger."""
        assert determine_risk_zone(1.51) == "danger"
        assert determine_risk_zone(2.0) == "danger"


class TestTrainingRecommendation:
    """Tests for training recommendations."""

    def test_high_acwr_recommendation(self):
        """High ACWR should recommend reducing load."""
        rec = get_training_recommendation(tsb=0, acwr=1.6)
        assert "reduce" in rec.lower() or "risk" in rec.lower()

    def test_low_acwr_recommendation(self):
        """Low ACWR should suggest increasing load."""
        rec = get_training_recommendation(tsb=0, acwr=0.5)
        assert "increase" in rec.lower() or "safe" in rec.lower()

    def test_fresh_recommendation(self):
        """High TSB in optimal zone should suggest hard workout."""
        rec = get_training_recommendation(tsb=30, acwr=1.0)
        assert "hard" in rec.lower() or "fresh" in rec.lower()


class TestHRZones:
    """Tests for HR zone calculations."""

    def test_karvonen_zones_calculation(self):
        """Test Karvonen zone calculation."""
        zones = calculate_hr_zones_karvonen(max_hr=185, rest_hr=55)

        # Check that zones are properly ordered
        assert zones.zone1[1] <= zones.zone2[0] or zones.zone1[1] == zones.zone2[0]
        assert zones.zone2[1] <= zones.zone3[0] or zones.zone2[1] == zones.zone3[0]
        assert zones.zone3[1] <= zones.zone4[0] or zones.zone3[1] == zones.zone4[0]
        assert zones.zone4[1] <= zones.zone5[0] or zones.zone4[1] == zones.zone5[0]

        # Check zone 5 ends at max HR
        assert zones.zone5[1] == 185

    def test_karvonen_zones_values(self):
        """Test specific Karvonen zone values."""
        zones = calculate_hr_zones_karvonen(max_hr=185, rest_hr=55)
        hr_reserve = 185 - 55  # 130

        # Zone 1: 50-60% of HRR
        expected_z1_low = 55 + int(130 * 0.50)  # 120
        expected_z1_high = 55 + int(130 * 0.60)  # 133
        assert zones.zone1 == (expected_z1_low, expected_z1_high)

    def test_lthr_zones_calculation(self):
        """Test LTHR zone calculation."""
        zones = calculate_hr_zones_lthr(lthr=165, max_hr=185)

        # Check zone 5 ends at max HR
        assert zones.zone5[1] == 185

        # Zone 4 should be around threshold
        assert zones.zone4[0] <= 165 <= zones.zone4[1] + 10

    def test_max_hr_only_zones(self):
        """Test zones calculated from max HR only."""
        zones = calculate_hr_zones_max_hr(max_hr=180)

        # Zone 1 should start at 50% of max HR
        assert zones.zone1[0] == int(180 * 0.50)  # 90
        assert zones.zone5[1] == 180


class TestZoneClassification:
    """Tests for HR zone classification."""

    def test_get_zone_for_hr(self):
        """Test zone classification for specific HR values."""
        zones = calculate_hr_zones_karvonen(max_hr=185, rest_hr=55)

        # Test each zone
        assert get_zone_for_hr(zones.zone1[0], zones) == 1
        assert get_zone_for_hr(zones.zone2[0] + 1, zones) == 2
        assert get_zone_for_hr(zones.zone3[0] + 1, zones) == 3
        assert get_zone_for_hr(zones.zone4[0] + 1, zones) == 4
        assert get_zone_for_hr(180, zones) == 5

    def test_get_zone_below_zone1(self):
        """HR below zone 1 should return 0."""
        zones = calculate_hr_zones_karvonen(max_hr=185, rest_hr=55)
        assert get_zone_for_hr(50, zones) == 0


class TestZoneTimeDistribution:
    """Tests for zone time distribution calculation."""

    def test_zone_distribution_basic(self):
        """Basic zone distribution calculation."""
        zones = calculate_hr_zones_karvonen(max_hr=185, rest_hr=55)

        # Create HR samples mostly in zone 2
        samples = [140] * 100  # All in zone 2

        dist = calculate_zone_time_distribution(samples, zones)

        assert dist["zone2_pct"] == 100.0
        assert dist["zone1_pct"] == 0.0
        assert dist["total_samples"] == 100

    def test_zone_distribution_empty(self):
        """Empty samples should return zeros."""
        zones = calculate_hr_zones_karvonen(max_hr=185, rest_hr=55)
        dist = calculate_zone_time_distribution([], zones)

        assert dist["total_samples"] == 0
        assert dist["zone1_pct"] == 0.0

    def test_zone_distribution_mixed(self):
        """Mixed samples should give proper percentages."""
        zones = calculate_hr_zones_karvonen(max_hr=185, rest_hr=55)

        # 50 samples in zone 2, 50 in zone 4
        samples = [140] * 50 + [170] * 50

        dist = calculate_zone_time_distribution(samples, zones)

        assert abs(dist["zone2_pct"] - 50.0) < 1
        assert abs(dist["zone4_pct"] - 50.0) < 1


class TestHREstimation:
    """Tests for HR estimation functions."""

    def test_estimate_max_hr_from_age(self):
        """Test Tanaka formula for max HR estimation."""
        # Tanaka: 208 - 0.7 * age
        assert estimate_max_hr_from_age(30) == 208 - 21  # 187
        assert estimate_max_hr_from_age(40) == 208 - 28  # 180
        assert estimate_max_hr_from_age(50) == 208 - 35  # 173

    def test_estimate_lthr_from_max_hr(self):
        """LTHR should be ~90% of max HR."""
        assert estimate_lthr_from_max_hr(200) == 180
        assert estimate_lthr_from_max_hr(185) == int(185 * 0.90)


class TestHRZonesDataclass:
    """Tests for HRZones dataclass methods."""

    def test_zones_to_dict(self):
        """Test zones serialization to dict."""
        zones = calculate_hr_zones_karvonen(max_hr=185, rest_hr=55)
        d = zones.to_dict()

        assert "zone1" in d
        assert d["zone1"]["name"] == "Recovery"
        assert "min" in d["zone1"]
        assert "max" in d["zone1"]

    def test_zones_get_zone_ranges(self):
        """Test getting all zone ranges."""
        zones = calculate_hr_zones_karvonen(max_hr=185, rest_hr=55)
        ranges = zones.get_zone_ranges()

        assert len(ranges) == 5
        assert ranges[0][0] == 1  # Zone 1
        assert ranges[0][3] == "Recovery"  # Zone 1 name
