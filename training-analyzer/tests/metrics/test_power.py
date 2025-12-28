"""Tests for cycling power metrics calculations."""

import pytest
from datetime import datetime
from typing import List

from training_analyzer.metrics.power import (
    # Dataclasses
    PowerZones,
    CyclingAthleteContext,
    # Functions
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


class TestNormalizedPower:
    """Tests for Normalized Power calculation."""

    def test_np_steady_power(self):
        """Steady power should give NP close to average power."""
        # 30 minutes of steady 200W power at 1Hz
        power_samples = [200] * (30 * 60)
        np = calculate_normalized_power(power_samples, sample_rate_hz=1)

        # With steady power, NP should equal average power
        assert abs(np - 200) < 1, f"Expected ~200, got {np}"

    def test_np_variable_power_higher_than_avg(self):
        """Variable power should give NP higher than average."""
        # Alternating between 100W and 300W (avg = 200W)
        # But NP should be higher due to 4th power weighting
        power_samples = []
        for _ in range(30):  # 30 cycles of 30 seconds each
            power_samples.extend([100] * 30)
            power_samples.extend([300] * 30)

        np = calculate_normalized_power(power_samples, sample_rate_hz=1)
        avg_power = sum(power_samples) / len(power_samples)

        assert np > avg_power, f"NP ({np}) should be higher than avg ({avg_power})"

    def test_np_empty_samples(self):
        """Empty power samples should return 0."""
        np = calculate_normalized_power([])
        assert np == 0.0

    def test_np_insufficient_samples(self):
        """Very few samples should return 0."""
        np = calculate_normalized_power([200, 200])
        assert np == 0.0

    def test_np_minimum_samples(self):
        """Should handle minimum valid samples (3+ seconds)."""
        # 5 seconds of data at 1Hz should work
        power_samples = [200] * 5
        np = calculate_normalized_power(power_samples, sample_rate_hz=1)
        assert np > 0

    def test_np_different_sample_rates(self):
        """NP should be consistent across different sample rates."""
        # 60 seconds at 200W, sampled at 1Hz
        np_1hz = calculate_normalized_power([200] * 60, sample_rate_hz=1)

        # 60 seconds at 200W, sampled at 2Hz (120 samples)
        np_2hz = calculate_normalized_power([200] * 120, sample_rate_hz=2)

        # Should be very close (allow some tolerance for edge effects)
        assert abs(np_1hz - np_2hz) < 5, f"1Hz: {np_1hz}, 2Hz: {np_2hz}"

    def test_np_realistic_workout(self):
        """Test NP with realistic cycling data."""
        # Simulate a workout with warmup, intervals, and cooldown
        power_samples = []

        # Warmup: 5 min at 150W
        power_samples.extend([150] * (5 * 60))

        # 5x(3min @ 300W, 2min @ 100W)
        for _ in range(5):
            power_samples.extend([300] * (3 * 60))
            power_samples.extend([100] * (2 * 60))

        # Cooldown: 5 min at 120W
        power_samples.extend([120] * (5 * 60))

        np = calculate_normalized_power(power_samples, sample_rate_hz=1)
        avg_power = sum(power_samples) / len(power_samples)

        # NP should be 10-30% higher than average for interval workout
        assert np > avg_power * 1.05
        assert np < avg_power * 1.40


class TestIntensityFactor:
    """Tests for Intensity Factor calculation."""

    def test_if_at_ftp(self):
        """At FTP, IF should be 1.0."""
        ftp = 250
        if_ = calculate_intensity_factor(250.0, ftp)
        assert if_ == 1.0

    def test_if_below_ftp(self):
        """Below FTP, IF should be < 1.0."""
        ftp = 250
        if_ = calculate_intensity_factor(200.0, ftp)
        assert if_ == 0.8

    def test_if_above_ftp(self):
        """Above FTP, IF should be > 1.0."""
        ftp = 250
        if_ = calculate_intensity_factor(275.0, ftp)
        assert if_ == 1.1

    def test_if_zero_ftp(self):
        """Zero FTP should return 0."""
        if_ = calculate_intensity_factor(200.0, 0)
        assert if_ == 0.0

    def test_if_typical_endurance_ride(self):
        """Endurance ride IF typically 0.65-0.75."""
        ftp = 250
        if_ = calculate_intensity_factor(175.0, ftp)
        assert 0.65 <= if_ <= 0.75

    def test_if_threshold_workout(self):
        """Threshold workout IF typically 0.90-1.05."""
        ftp = 250
        if_ = calculate_intensity_factor(237.5, ftp)
        assert 0.90 <= if_ <= 1.0


class TestTSS:
    """Tests for Training Stress Score calculation."""

    def test_tss_one_hour_at_ftp(self):
        """One hour at FTP should give TSS of ~100."""
        ftp = 250
        duration_sec = 3600  # 1 hour
        np = 250.0  # At FTP
        if_ = 1.0

        tss = calculate_tss(duration_sec, np, if_, ftp)

        # Should be exactly 100 for 1 hour at FTP
        assert abs(tss - 100) < 0.1, f"Expected ~100, got {tss}"

    def test_tss_two_hours_at_ftp(self):
        """Two hours at FTP should give TSS of ~200."""
        ftp = 250
        duration_sec = 7200  # 2 hours
        np = 250.0
        if_ = 1.0

        tss = calculate_tss(duration_sec, np, if_, ftp)

        assert abs(tss - 200) < 0.1, f"Expected ~200, got {tss}"

    def test_tss_one_hour_at_half_ftp(self):
        """One hour at 50% FTP should give TSS of ~25."""
        ftp = 250
        duration_sec = 3600
        np = 125.0  # 50% of FTP
        if_ = 0.5

        tss = calculate_tss(duration_sec, np, if_, ftp)

        # TSS = (3600 * 125 * 0.5) / (250 * 3600) * 100 = 25
        assert abs(tss - 25) < 0.5, f"Expected ~25, got {tss}"

    def test_tss_zero_duration(self):
        """Zero duration should return 0 TSS."""
        tss = calculate_tss(0, 200.0, 0.8, 250)
        assert tss == 0.0

    def test_tss_zero_ftp(self):
        """Zero FTP should return 0 TSS."""
        tss = calculate_tss(3600, 200.0, 0.8, 0)
        assert tss == 0.0

    def test_tss_simple_convenience(self):
        """Test TSS simple calculation matches full calculation."""
        ftp = 250
        duration_sec = 3600
        np = 225.0

        tss_full = calculate_tss(
            duration_sec,
            np,
            calculate_intensity_factor(np, ftp),
            ftp,
        )
        tss_simple = calculate_tss_simple(duration_sec, np, ftp)

        assert tss_full == tss_simple

    def test_tss_typical_workouts(self):
        """Test TSS for typical workout scenarios."""
        ftp = 250

        # Easy 1-hour ride (IF ~0.65) -> TSS ~42
        tss_easy = calculate_tss_simple(3600, 162.5, ftp)
        assert 35 < tss_easy < 50, f"Easy ride TSS: {tss_easy}"

        # Tempo 1-hour ride (IF ~0.85) -> TSS ~72
        tss_tempo = calculate_tss_simple(3600, 212.5, ftp)
        assert 65 < tss_tempo < 80, f"Tempo ride TSS: {tss_tempo}"

        # Sweet spot 1-hour (IF ~0.90) -> TSS ~81
        tss_ss = calculate_tss_simple(3600, 225.0, ftp)
        assert 75 < tss_ss < 90, f"Sweet spot TSS: {tss_ss}"


class TestVariabilityIndex:
    """Tests for Variability Index calculation."""

    def test_vi_steady_effort(self):
        """Steady effort should have VI close to 1.0."""
        np = 200.0
        avg = 200.0
        vi = calculate_variability_index(np, avg)
        assert vi == 1.0

    def test_vi_variable_effort(self):
        """Variable effort should have VI > 1.0."""
        np = 220.0
        avg = 200.0
        vi = calculate_variability_index(np, avg)
        assert vi == 1.1

    def test_vi_zero_average(self):
        """Zero average should return 0."""
        vi = calculate_variability_index(200.0, 0)
        assert vi == 0.0

    def test_vi_typical_time_trial(self):
        """Time trial VI typically < 1.05."""
        vi = calculate_variability_index(250.0, 245.0)
        assert vi < 1.05

    def test_vi_typical_criterium(self):
        """Criterium VI typically > 1.15."""
        vi = calculate_variability_index(240.0, 200.0)
        assert vi > 1.15


class TestPowerZones:
    """Tests for power zone calculations."""

    def test_power_zones_ftp_250(self):
        """Test zone boundaries for FTP of 250W."""
        zones = calculate_power_zones(250)

        # Zone 1: <55% FTP (0-137)
        assert zones[1] == (0, 137)

        # Zone 2: 55-75% FTP (137-187)
        assert zones[2] == (137, 187)

        # Zone 3: 75-90% FTP (187-225)
        assert zones[3] == (187, 225)

        # Zone 4: 90-105% FTP (225-262)
        assert zones[4] == (225, 262)

        # Zone 5: 105-120% FTP (262-300)
        assert zones[5] == (262, 300)

        # Zone 6: 120-150% FTP (300-375)
        assert zones[6] == (300, 375)

        # Zone 7: >150% FTP
        assert zones[7][0] == 375

    def test_power_zones_ftp_200(self):
        """Test zone boundaries for FTP of 200W."""
        zones = calculate_power_zones(200)

        # Zone 4 should be around FTP (90-105%)
        assert zones[4] == (180, 210)

    def test_power_zones_zero_ftp(self):
        """Zero FTP should return all zero zones."""
        zones = calculate_power_zones(0)
        for zone_num in range(1, 8):
            assert zones[zone_num] == (0, 0)

    def test_power_zone_names(self):
        """Test zone names are correct."""
        names = get_power_zone_names()
        assert names[1] == "Active Recovery"
        assert names[2] == "Endurance"
        assert names[3] == "Tempo"
        assert names[4] == "Threshold"
        assert names[5] == "VO2max"
        assert names[6] == "Anaerobic"
        assert names[7] == "Neuromuscular"

    def test_get_zone_for_power_zone1(self):
        """Test power in Zone 1."""
        zones = calculate_power_zones(250)
        assert get_zone_for_power(100, zones) == 1

    def test_get_zone_for_power_zone4(self):
        """Test power in Zone 4 (threshold)."""
        zones = calculate_power_zones(250)
        # Zone 4 is 225-262 for FTP 250
        assert get_zone_for_power(250, zones) == 4

    def test_get_zone_for_power_zone7(self):
        """Test power in Zone 7 (neuromuscular)."""
        zones = calculate_power_zones(250)
        assert get_zone_for_power(400, zones) == 7

    def test_get_zone_for_power_boundary(self):
        """Test power at zone boundaries."""
        zones = calculate_power_zones(250)
        # At boundary, should be in the lower zone
        assert get_zone_for_power(137, zones) == 1  # Max of zone 1
        assert get_zone_for_power(138, zones) == 2  # Start of zone 2

    def test_get_zone_for_negative_power(self):
        """Negative power should return zone 0."""
        zones = calculate_power_zones(250)
        assert get_zone_for_power(-10, zones) == 0


class TestFTPEstimation:
    """Tests for FTP estimation functions."""

    def test_ftp_from_20min_power(self):
        """FTP = 0.95 * 20min power."""
        ftp = estimate_ftp_from_20min_power(300.0)
        assert ftp == 285

    def test_ftp_from_20min_power_typical(self):
        """Test typical 20-minute test scenario."""
        # If 20min avg is 260W, FTP should be 247W
        ftp = estimate_ftp_from_20min_power(260.0)
        assert ftp == 247

    def test_ftp_from_20min_power_zero(self):
        """Zero power should return 0."""
        ftp = estimate_ftp_from_20min_power(0.0)
        assert ftp == 0

    def test_ftp_from_20min_power_negative(self):
        """Negative power should return 0."""
        ftp = estimate_ftp_from_20min_power(-100.0)
        assert ftp == 0

    def test_ftp_from_ramp_test(self):
        """FTP = 0.75 * max 1-minute power."""
        ftp = estimate_ftp_from_ramp_test(400.0)
        assert ftp == 300

    def test_ftp_from_ramp_test_typical(self):
        """Test typical ramp test scenario."""
        # If max 1-min is 340W, FTP should be 255W
        ftp = estimate_ftp_from_ramp_test(340.0)
        assert ftp == 255

    def test_ftp_from_ramp_test_zero(self):
        """Zero power should return 0."""
        ftp = estimate_ftp_from_ramp_test(0.0)
        assert ftp == 0


class TestPowerZoneDistribution:
    """Tests for power zone distribution calculation."""

    def test_zone_distribution_all_zone2(self):
        """100% in Zone 2 should show 100% for zone 2."""
        ftp = 250
        # Zone 2 is 137-187W for FTP 250
        power_samples = [160] * 100

        dist = get_power_zone_distribution(power_samples, ftp)

        assert dist[2] == 100.0
        assert dist[1] == 0.0
        assert dist[3] == 0.0

    def test_zone_distribution_mixed(self):
        """Mixed zones should show correct percentages."""
        ftp = 250
        # 50 samples in Z2 (160W), 50 in Z4 (240W)
        power_samples = [160] * 50 + [240] * 50

        dist = get_power_zone_distribution(power_samples, ftp)

        assert abs(dist[2] - 50.0) < 1
        assert abs(dist[4] - 50.0) < 1

    def test_zone_distribution_empty(self):
        """Empty samples should return all zeros."""
        dist = get_power_zone_distribution([], 250)
        for zone in range(1, 8):
            assert dist[zone] == 0.0

    def test_zone_distribution_zero_ftp(self):
        """Zero FTP should return all zeros."""
        dist = get_power_zone_distribution([200, 200], 0)
        for zone in range(1, 8):
            assert dist[zone] == 0.0

    def test_zone_distribution_ignores_zeros(self):
        """Zero power values should be ignored."""
        ftp = 250
        # 50 samples at 160W (Z2), 50 samples at 0W (coasting)
        power_samples = [160] * 50 + [0] * 50

        dist = get_power_zone_distribution(power_samples, ftp)

        # Should be 100% Z2 (ignoring the zeros)
        assert dist[2] == 100.0

    def test_zone_distribution_realistic_ride(self):
        """Test with realistic ride data."""
        ftp = 250
        power_samples = []

        # Simulate: 40% Z2, 30% Z3, 20% Z4, 10% Z5
        power_samples.extend([160] * 400)   # Z2
        power_samples.extend([200] * 300)   # Z3
        power_samples.extend([240] * 200)   # Z4
        power_samples.extend([280] * 100)   # Z5

        dist = get_power_zone_distribution(power_samples, ftp)

        assert abs(dist[2] - 40.0) < 1
        assert abs(dist[3] - 30.0) < 1
        assert abs(dist[4] - 20.0) < 1
        assert abs(dist[5] - 10.0) < 1


class TestEfficiencyFactor:
    """Tests for Efficiency Factor calculation."""

    def test_ef_basic(self):
        """Basic EF calculation."""
        ef = calculate_efficiency_factor(200.0, 150)
        assert abs(ef - 1.333) < 0.01

    def test_ef_zero_hr(self):
        """Zero HR should return 0."""
        ef = calculate_efficiency_factor(200.0, 0)
        assert ef == 0.0

    def test_ef_typical_trained_cyclist(self):
        """Trained cyclist EF typically 1.0-2.0."""
        ef = calculate_efficiency_factor(220.0, 145)
        assert 1.0 <= ef <= 2.0


class TestPowerToWeight:
    """Tests for power-to-weight ratio calculation."""

    def test_power_to_weight_basic(self):
        """Basic power-to-weight calculation."""
        pw = calculate_power_to_weight(250.0, 70.0)
        assert abs(pw - 3.57) < 0.01

    def test_power_to_weight_zero_weight(self):
        """Zero weight should return 0."""
        pw = calculate_power_to_weight(250.0, 0.0)
        assert pw == 0.0

    def test_power_to_weight_pro_level(self):
        """Pro cyclist typical values: 5.5-6.5 W/kg."""
        # 400W at 65kg = 6.15 W/kg
        pw = calculate_power_to_weight(400.0, 65.0)
        assert 5.5 <= pw <= 6.5


class TestWorkCalculation:
    """Tests for work (kJ) calculation."""

    def test_work_basic(self):
        """Basic work calculation."""
        # 200W for 1 hour = 720kJ
        power_samples = [200] * 3600
        work = calculate_work(power_samples, sample_rate_hz=1)
        assert work == 720

    def test_work_half_hour(self):
        """30 minutes at 200W = 360kJ."""
        power_samples = [200] * 1800
        work = calculate_work(power_samples, sample_rate_hz=1)
        assert work == 360

    def test_work_empty(self):
        """Empty samples should return 0."""
        work = calculate_work([])
        assert work == 0

    def test_work_different_sample_rate(self):
        """Work should be consistent with different sample rates."""
        # 200W for 1 hour at 1Hz
        work_1hz = calculate_work([200] * 3600, sample_rate_hz=1)

        # 200W for 1 hour at 2Hz (7200 samples)
        work_2hz = calculate_work([200] * 7200, sample_rate_hz=2)

        assert work_1hz == work_2hz == 720


class TestIntegrationScenarios:
    """Integration tests with realistic scenarios."""

    def test_threshold_workout_metrics(self):
        """Test a complete threshold workout scenario."""
        ftp = 250

        # 60 minutes at threshold (NP = FTP)
        power_samples = [250] * (60 * 60)

        np = calculate_normalized_power(power_samples)
        if_ = calculate_intensity_factor(np, ftp)
        tss = calculate_tss_simple(3600, np, ftp)
        vi = calculate_variability_index(np, 250)
        work = calculate_work(power_samples)

        # Assertions
        assert abs(np - 250) < 5
        assert abs(if_ - 1.0) < 0.05
        assert abs(tss - 100) < 5
        assert abs(vi - 1.0) < 0.05
        assert work == 900  # 250W * 3600s / 1000 = 900kJ

    def test_endurance_ride_metrics(self):
        """Test a complete endurance ride scenario."""
        ftp = 250

        # 2 hours at 65% FTP (~162W)
        power_samples = [162] * (2 * 60 * 60)

        np = calculate_normalized_power(power_samples)
        if_ = calculate_intensity_factor(np, ftp)
        tss = calculate_tss_simple(7200, np, ftp)
        work = calculate_work(power_samples)
        zone_dist = get_power_zone_distribution(power_samples, ftp)

        # Assertions
        assert np < 180  # Should be close to avg
        assert 0.60 <= if_ <= 0.70
        assert 75 < tss < 110  # 2 hours at low IF
        assert work == 1166  # ~162W * 7200s / 1000
        assert zone_dist[2] == 100.0  # All in Zone 2

    def test_interval_workout_metrics(self):
        """Test interval workout with high variability."""
        ftp = 250

        # 6x(5min @ 110% FTP, 5min @ 50% FTP)
        power_samples = []
        for _ in range(6):
            power_samples.extend([275] * (5 * 60))  # 110% FTP
            power_samples.extend([125] * (5 * 60))  # 50% FTP

        avg_power = sum(power_samples) / len(power_samples)
        np = calculate_normalized_power(power_samples)
        vi = calculate_variability_index(np, avg_power)

        # NP should be significantly higher than average
        assert np > avg_power * 1.1

        # VI should indicate variable effort
        assert vi > 1.1

    def test_ftp_estimation_consistency(self):
        """Test that both FTP estimation methods give reasonable results."""
        # If someone's 20min power is 280W, FTP = 266
        ftp_20min = estimate_ftp_from_20min_power(280.0)

        # If their max 1-min in ramp test is 360W, FTP = 270
        ftp_ramp = estimate_ftp_from_ramp_test(360.0)

        # Both methods should give similar results (within 5%)
        assert abs(ftp_20min - ftp_ramp) / ftp_20min < 0.05


class TestPowerZonesDataclass:
    """Tests for PowerZones dataclass."""

    def test_power_zones_auto_calculation(self):
        """Test that zones are auto-calculated from FTP."""
        zones = PowerZones(ftp=250)

        # Zone 4 should be around FTP (90-105%)
        assert zones.zone4 == (225, 262)
        # Zone 1 should be <55% FTP
        assert zones.zone1 == (0, 137)

    def test_power_zones_get_zone(self):
        """Test get_zone method."""
        zones = PowerZones(ftp=250)

        assert zones.get_zone(1) == zones.zone1
        assert zones.get_zone(4) == zones.zone4
        assert zones.get_zone(7) == zones.zone7
        assert zones.get_zone(0) == (0, 0)  # Invalid zone
        assert zones.get_zone(8) == (0, 0)  # Invalid zone

    def test_power_zones_get_zone_for_power(self):
        """Test get_zone_for_power method."""
        zones = PowerZones(ftp=250)

        # Test various power values
        assert zones.get_zone_for_power(100) == 1   # Zone 1
        assert zones.get_zone_for_power(160) == 2   # Zone 2
        assert zones.get_zone_for_power(200) == 3   # Zone 3
        assert zones.get_zone_for_power(240) == 4   # Zone 4
        assert zones.get_zone_for_power(280) == 5   # Zone 5
        assert zones.get_zone_for_power(320) == 6   # Zone 6
        assert zones.get_zone_for_power(400) == 7   # Zone 7
        assert zones.get_zone_for_power(-10) == 0   # Negative

    def test_power_zones_to_dict(self):
        """Test serialization to dict."""
        zones = PowerZones(ftp=250)
        d = zones.to_dict()

        assert d["ftp"] == 250
        assert "zones" in d
        assert "zone1" in d["zones"]
        assert d["zones"]["zone1"]["name"] == "Active Recovery"
        assert d["zones"]["zone4"]["name"] == "Threshold"
        assert "updated_at" in d

    def test_power_zones_from_dict(self):
        """Test deserialization from dict."""
        original = PowerZones(ftp=250)
        d = original.to_dict()
        restored = PowerZones.from_dict(d)

        assert restored.ftp == 250
        # Note: from_dict may not preserve exact zone values due to dict structure
        # but the FTP should be preserved

    def test_power_zones_format_zones(self):
        """Test zone formatting for prompts."""
        zones = PowerZones(ftp=250)
        formatted = zones.format_zones()

        assert "Z1 (Active Recovery)" in formatted
        assert "Z4 (Threshold)" in formatted
        assert "Z7 (Neuromuscular)" in formatted
        assert "W" in formatted

    def test_power_zones_zero_ftp(self):
        """Test handling of zero FTP."""
        zones = PowerZones(ftp=0)

        # All zones should be (0, 0)
        for i in range(1, 8):
            assert zones.get_zone(i) == (0, 0)


class TestCyclingAthleteContext:
    """Tests for CyclingAthleteContext dataclass."""

    def test_cycling_context_defaults(self):
        """Test default values."""
        ctx = CyclingAthleteContext()

        assert ctx.ftp == 200
        assert ctx.cycling_ctl == 30.0
        assert ctx.cycling_atl == 30.0
        assert ctx.cycling_tsb == 0.0
        assert ctx.power_zones is not None
        assert ctx.power_zones.ftp == 200

    def test_cycling_context_custom_ftp(self):
        """Test custom FTP initialization."""
        ctx = CyclingAthleteContext(ftp=280)

        assert ctx.ftp == 280
        assert ctx.power_zones.ftp == 280
        # Zone 4 should be around 280W
        assert ctx.power_zones.zone4 == (252, 294)

    def test_cycling_context_with_weight(self):
        """Test power-to-weight calculation."""
        ctx = CyclingAthleteContext(ftp=280, weight_kg=70)

        assert ctx.weight_kg == 70
        assert ctx.power_to_weight == 4.0  # 280 / 70 = 4.0

    def test_cycling_context_update_ftp(self):
        """Test FTP update method."""
        ctx = CyclingAthleteContext(ftp=200, weight_kg=70)
        old_zones = ctx.power_zones

        ctx.update_ftp(280)

        assert ctx.ftp == 280
        assert ctx.power_zones.ftp == 280
        assert ctx.power_zones != old_zones
        assert ctx.ftp_test_date is not None
        assert ctx.power_to_weight == 4.0

    def test_cycling_context_get_target_power_range(self):
        """Test get_target_power_range method."""
        ctx = CyclingAthleteContext(ftp=250)

        # Zone 4 (threshold)
        z4_range = ctx.get_target_power_range(4)
        assert z4_range == (225, 262)

        # Zone 2 (endurance)
        z2_range = ctx.get_target_power_range(2)
        assert z2_range == (137, 187)

    def test_cycling_context_to_dict(self):
        """Test serialization to dict."""
        ctx = CyclingAthleteContext(
            ftp=280,
            weight_kg=70,
            cycling_ctl=50.0,
            cycling_atl=60.0,
            cycling_tsb=-10.0,
        )
        d = ctx.to_dict()

        assert d["ftp"] == 280
        assert d["weight_kg"] == 70
        assert d["power_to_weight"] == 4.0
        assert d["cycling_ctl"] == 50.0
        assert d["cycling_atl"] == 60.0
        assert d["cycling_tsb"] == -10.0
        assert "power_zones" in d

    def test_cycling_context_from_dict(self):
        """Test deserialization from dict."""
        original = CyclingAthleteContext(
            ftp=280,
            weight_kg=70,
            cycling_ctl=50.0,
        )
        d = original.to_dict()
        restored = CyclingAthleteContext.from_dict(d)

        assert restored.ftp == 280
        assert restored.weight_kg == 70
        assert restored.cycling_ctl == 50.0

    def test_cycling_context_to_prompt_context(self):
        """Test prompt context generation."""
        ctx = CyclingAthleteContext(
            ftp=280,
            weight_kg=70,
            cycling_ctl=50.0,
            cycling_atl=60.0,
            cycling_tsb=-10.0,
            typical_efficiency_factor=1.45,
        )
        prompt = ctx.to_prompt_context()

        assert "FTP: 280W" in prompt
        assert "Power-to-Weight: 4.0 W/kg" in prompt
        assert "Cycling CTL: 50.0" in prompt
        assert "Efficiency Factor: 1.45" in prompt


class TestEdgeCases:
    """Tests for edge cases in power calculations."""

    def test_np_with_all_zeros(self):
        """NP with all zero power samples."""
        np = calculate_normalized_power([0] * 100)
        assert np == 0.0

    def test_np_with_negative_values(self):
        """NP with negative power values (should handle gracefully)."""
        # Mix of positive and negative
        samples = [200] * 50 + [-10] * 50
        np = calculate_normalized_power(samples)
        # Should still calculate, though negative values are unusual
        assert np >= 0

    def test_tss_short_ride(self):
        """TSS for a very short ride."""
        # 5 minutes at FTP
        tss = calculate_tss_simple(300, 250.0, 250)
        # Should be ~8.3 TSS
        assert 8 < tss < 9

    def test_vi_very_steady(self):
        """VI for perfectly steady effort."""
        vi = calculate_variability_index(200.0, 200.0)
        assert vi == 1.0

    def test_vi_extreme_variability(self):
        """VI for extremely variable effort."""
        vi = calculate_variability_index(300.0, 150.0)
        assert vi == 2.0

    def test_power_zones_negative_ftp(self):
        """Power zones with negative FTP should return zeros."""
        zones = calculate_power_zones(-100)
        for zone in range(1, 8):
            assert zones[zone] == (0, 0)

    def test_efficiency_factor_high_power(self):
        """Efficiency factor with very high power."""
        ef = calculate_efficiency_factor(350.0, 140)
        assert ef == 2.5

    def test_work_variable_power(self):
        """Work calculation with variable power."""
        # 1800 samples: half at 200W, half at 100W
        samples = [200] * 900 + [100] * 900
        work = calculate_work(samples, sample_rate_hz=1)
        # Total: (200*900 + 100*900) / 1000 = 270 kJ
        assert work == 270
