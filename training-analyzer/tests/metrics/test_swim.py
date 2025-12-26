"""Tests for swimming metrics calculations."""

import pytest

from training_analyzer.metrics.swim import (
    calculate_swolf,
    calculate_stroke_rate,
    calculate_pace_per_100m,
    calculate_css,
    estimate_swim_tss,
    get_swim_zones,
    analyze_stroke_efficiency,
    format_swim_pace,
    get_swim_zone_for_pace,
    estimate_css_from_race_times,
)


class TestSwolfCalculation:
    """Tests for SWOLF score calculation."""

    def test_swolf_basic_calculation(self):
        """Basic SWOLF calculation: time + strokes."""
        # 30 seconds + 15 strokes = 45 SWOLF
        swolf = calculate_swolf(30.0, 15)
        assert swolf == 45.0

    def test_swolf_elite_swimmer(self):
        """Elite swimmers typically have SWOLF 35-45 for 25m."""
        # Elite: 15 seconds, 20 strokes in 25m pool
        swolf = calculate_swolf(15.0, 20)
        assert 35 <= swolf <= 45

    def test_swolf_recreational_swimmer(self):
        """Recreational swimmers typically have SWOLF 55-70."""
        # Recreational: 35 seconds, 25 strokes
        swolf = calculate_swolf(35.0, 25)
        assert 55 <= swolf <= 70

    def test_swolf_beginner_swimmer(self):
        """Beginner swimmers may have SWOLF > 70."""
        # Beginner: 45 seconds, 30 strokes
        swolf = calculate_swolf(45.0, 30)
        assert swolf >= 70

    def test_swolf_with_fractional_time(self):
        """SWOLF should handle fractional seconds."""
        swolf = calculate_swolf(28.5, 16)
        assert swolf == 44.5

    def test_swolf_zero_strokes(self):
        """Zero strokes should just return time (e.g., pushing off wall)."""
        swolf = calculate_swolf(10.0, 0)
        assert swolf == 10.0

    def test_swolf_negative_time_raises_error(self):
        """Negative time should raise ValueError."""
        with pytest.raises(ValueError):
            calculate_swolf(-5.0, 15)

    def test_swolf_negative_strokes_raises_error(self):
        """Negative strokes should raise ValueError."""
        with pytest.raises(ValueError):
            calculate_swolf(30.0, -5)


class TestStrokeRateCalculation:
    """Tests for stroke rate calculation."""

    def test_stroke_rate_basic(self):
        """Basic stroke rate: 60 strokes in 60 seconds = 60 spm."""
        rate = calculate_stroke_rate(60, 60.0)
        assert rate == 60.0

    def test_stroke_rate_sprint(self):
        """Sprint swimming typically has high stroke rates (70-90 spm)."""
        # 75 strokes in 60 seconds
        rate = calculate_stroke_rate(75, 60.0)
        assert 70 <= rate <= 90

    def test_stroke_rate_distance(self):
        """Distance swimming has lower stroke rates (50-60 spm)."""
        # 55 strokes in 60 seconds
        rate = calculate_stroke_rate(55, 60.0)
        assert 50 <= rate <= 60

    def test_stroke_rate_zero_duration(self):
        """Zero duration should return 0 (avoid division by zero)."""
        rate = calculate_stroke_rate(10, 0.0)
        assert rate == 0.0

    def test_stroke_rate_negative_strokes_raises_error(self):
        """Negative strokes should raise ValueError."""
        with pytest.raises(ValueError):
            calculate_stroke_rate(-10, 60.0)

    def test_stroke_rate_short_interval(self):
        """Short interval should still calculate correctly."""
        # 12 strokes in 10 seconds = 72 spm
        rate = calculate_stroke_rate(12, 10.0)
        assert rate == 72.0


class TestPacePer100mCalculation:
    """Tests for swim pace calculation."""

    def test_pace_basic(self):
        """Basic pace calculation."""
        # 100m in 90 seconds = 90 sec/100m
        pace = calculate_pace_per_100m(100.0, 90.0)
        assert pace == 90

    def test_pace_elite_swimmer(self):
        """Elite swimmers: ~55-65 sec/100m."""
        # 400m in 240 seconds (4:00) = 60 sec/100m
        pace = calculate_pace_per_100m(400.0, 240.0)
        assert 55 <= pace <= 65

    def test_pace_recreational_swimmer(self):
        """Recreational swimmers: ~100-120 sec/100m."""
        # 500m in 550 seconds = 110 sec/100m
        pace = calculate_pace_per_100m(500.0, 550.0)
        assert 100 <= pace <= 120

    def test_pace_beginner_swimmer(self):
        """Beginner swimmers: ~130-180 sec/100m."""
        # 200m in 320 seconds = 160 sec/100m
        pace = calculate_pace_per_100m(200.0, 320.0)
        assert 130 <= pace <= 180

    def test_pace_rounding(self):
        """Pace should be rounded to nearest second."""
        # 100m in 93.4 seconds = 93 sec/100m
        pace = calculate_pace_per_100m(100.0, 93.4)
        assert pace == 93

        # 100m in 93.6 seconds = 94 sec/100m
        pace = calculate_pace_per_100m(100.0, 93.6)
        assert pace == 94

    def test_pace_zero_distance_raises_error(self):
        """Zero distance should raise ValueError."""
        with pytest.raises(ValueError):
            calculate_pace_per_100m(0.0, 90.0)

    def test_pace_negative_duration_raises_error(self):
        """Negative duration should raise ValueError."""
        with pytest.raises(ValueError):
            calculate_pace_per_100m(100.0, -90.0)


class TestCSSCalculation:
    """Tests for Critical Swim Speed calculation."""

    def test_css_basic_calculation(self):
        """Basic CSS calculation from 400m and 200m times."""
        # 400m in 6:00 (360s), 200m in 2:45 (165s)
        # CSS = 200 / (360 - 165) = 200 / 195 = 1.026 m/s
        # Pace = 100 / 1.026 = 97.5 sec/100m
        css = calculate_css(360, 165)
        assert 95 <= css <= 100

    def test_css_faster_swimmer(self):
        """Faster swimmer CSS calculation."""
        # 400m in 4:30 (270s), 200m in 2:10 (130s)
        # CSS = 200 / (270 - 130) = 200 / 140 = 1.43 m/s
        # Pace = 100 / 1.43 = 70 sec/100m
        css = calculate_css(270, 130)
        assert 68 <= css <= 72

    def test_css_slower_swimmer(self):
        """Slower swimmer CSS calculation."""
        # 400m in 8:00 (480s), 200m in 3:45 (225s)
        # CSS = 200 / (480 - 225) = 200 / 255 = 0.784 m/s
        # Pace = 100 / 0.784 = 127.5 sec/100m
        css = calculate_css(480, 225)
        assert 125 <= css <= 130

    def test_css_invalid_times_raises_error(self):
        """400m time must be greater than 200m time."""
        with pytest.raises(ValueError):
            # 400m faster than 200m is impossible
            calculate_css(180, 200)

    def test_css_equal_times_raises_error(self):
        """Equal times should raise error (division by zero)."""
        with pytest.raises(ValueError):
            calculate_css(200, 200)

    def test_css_negative_times_raises_error(self):
        """Negative times should raise ValueError."""
        with pytest.raises(ValueError):
            calculate_css(-360, 165)
        with pytest.raises(ValueError):
            calculate_css(360, -165)


class TestSwimTSSEstimation:
    """Tests for swim TSS estimation."""

    def test_tss_at_css_pace_one_hour(self):
        """One hour at CSS pace should give approximately 100 TSS."""
        tss = estimate_swim_tss(60, 100, 100)  # 60 min at CSS
        assert abs(tss - 100) < 5  # Should be close to 100

    def test_tss_below_css_pace(self):
        """Swimming slower than CSS should give < 100 TSS for one hour."""
        # Pace of 110 when CSS is 100 (slower than threshold)
        tss = estimate_swim_tss(60, 110, 100)
        assert tss < 100

    def test_tss_above_css_pace(self):
        """Swimming faster than CSS should give > 100 TSS for one hour."""
        # Pace of 90 when CSS is 100 (faster than threshold)
        tss = estimate_swim_tss(60, 90, 100)
        assert tss > 100

    def test_tss_scales_with_duration(self):
        """TSS should scale with duration at same intensity."""
        tss_30 = estimate_swim_tss(30, 100, 100)
        tss_60 = estimate_swim_tss(60, 100, 100)
        ratio = tss_60 / tss_30
        assert 1.9 < ratio < 2.1  # Should be approximately 2x

    def test_tss_easy_swim(self):
        """Easy recovery swim should have low TSS."""
        # 30 min at 120 pace (CSS 100) - very easy
        tss = estimate_swim_tss(30, 120, 100)
        assert 20 < tss < 50

    def test_tss_hard_interval_session(self):
        """Hard interval session should have high TSS."""
        # 45 min at 85 pace (CSS 100) - very hard
        tss = estimate_swim_tss(45, 85, 100)
        assert tss > 80

    def test_tss_zero_duration(self):
        """Zero duration should return 0 TSS."""
        tss = estimate_swim_tss(0, 100, 100)
        assert tss == 0.0

    def test_tss_invalid_pace_raises_error(self):
        """Invalid pace values should raise ValueError."""
        with pytest.raises(ValueError):
            estimate_swim_tss(60, 0, 100)
        with pytest.raises(ValueError):
            estimate_swim_tss(60, 100, 0)


class TestSwimZones:
    """Tests for swim zone calculation."""

    def test_zones_structure(self):
        """Zones should have correct structure."""
        zones = get_swim_zones(100)  # CSS = 100 sec/100m

        assert "zone1_recovery" in zones
        assert "zone2_aerobic" in zones
        assert "zone3_threshold" in zones
        assert "zone4_vo2max" in zones
        assert "zone5_sprint" in zones

        # Each zone should be a tuple of (min, max)
        for zone_name, (fast, slow) in zones.items():
            assert isinstance(fast, int)
            assert isinstance(slow, int)
            # In swimming, fast pace = lower number
            assert fast <= slow

    def test_zones_threshold_around_css(self):
        """Zone 3 (threshold) should be centered around CSS pace."""
        css = 100
        zones = get_swim_zones(css)

        # Zone 3 should bracket CSS (95-105% of CSS)
        z3_fast, z3_slow = zones["zone3_threshold"]
        assert z3_fast <= css <= z3_slow

    def test_zones_ordering(self):
        """Zones should be properly ordered (Z5 fastest to Z1 slowest)."""
        zones = get_swim_zones(100)

        z5 = zones["zone5_sprint"]
        z4 = zones["zone4_vo2max"]
        z3 = zones["zone3_threshold"]
        z2 = zones["zone2_aerobic"]
        z1 = zones["zone1_recovery"]

        # Z5 should be faster (lower numbers) than Z4, etc.
        assert z5[1] <= z4[0] or z5[1] <= z4[1]  # Allow overlap
        assert z4[1] <= z3[0] or z4[1] <= z3[1]
        assert z3[1] <= z2[0] or z3[1] <= z2[1]
        assert z2[1] <= z1[0] or z2[1] <= z1[1]

    def test_zones_for_different_css_values(self):
        """Zones should scale proportionally with CSS."""
        zones_fast = get_swim_zones(80)  # Fast swimmer
        zones_slow = get_swim_zones(120)  # Slower swimmer

        # Zone boundaries should scale with CSS
        assert zones_fast["zone3_threshold"][0] < zones_slow["zone3_threshold"][0]
        assert zones_fast["zone3_threshold"][1] < zones_slow["zone3_threshold"][1]

    def test_zones_invalid_css_raises_error(self):
        """Invalid CSS should raise ValueError."""
        with pytest.raises(ValueError):
            get_swim_zones(0)
        with pytest.raises(ValueError):
            get_swim_zones(-100)


class TestStrokeEfficiencyAnalysis:
    """Tests for stroke efficiency analysis."""

    def test_efficiency_basic_analysis(self):
        """Basic stroke efficiency analysis."""
        strokes = [18, 19, 18, 20, 19, 18, 19, 20]
        times = [30.0, 31.0, 30.5, 32.0, 31.5, 31.0, 32.0, 33.0]

        result = analyze_stroke_efficiency(strokes, times)

        assert "avg_swolf" in result
        assert "swolf_trend" in result
        assert "stroke_count_consistency" in result
        assert "fatigue_indicator" in result

    def test_efficiency_average_swolf(self):
        """Average SWOLF should be calculated correctly."""
        # All same: 30 sec + 15 strokes = 45 SWOLF
        strokes = [15, 15, 15, 15]
        times = [30.0, 30.0, 30.0, 30.0]

        result = analyze_stroke_efficiency(strokes, times)
        assert result["avg_swolf"] == 45.0

    def test_efficiency_stable_trend(self):
        """Stable swimming should show stable trend."""
        strokes = [18, 18, 18, 18, 18, 18, 18, 18]
        times = [30.0, 30.0, 30.0, 30.0, 30.0, 30.0, 30.0, 30.0]

        result = analyze_stroke_efficiency(strokes, times)
        assert result["swolf_trend"] == "stable"

    def test_efficiency_declining_trend(self):
        """Fatigue should show declining trend (worsening SWOLF)."""
        # Start good, end worse
        strokes = [16, 16, 17, 17, 20, 21, 22, 22]
        times = [28.0, 28.0, 29.0, 30.0, 33.0, 34.0, 35.0, 36.0]

        result = analyze_stroke_efficiency(strokes, times)
        assert result["swolf_trend"] == "declining"

    def test_efficiency_improving_trend(self):
        """Warming up should show improving trend (better SWOLF)."""
        # Start slow, get better
        strokes = [22, 21, 20, 19, 17, 16, 16, 15]
        times = [35.0, 34.0, 33.0, 31.0, 29.0, 28.0, 28.0, 27.0]

        result = analyze_stroke_efficiency(strokes, times)
        assert result["swolf_trend"] == "improving"

    def test_efficiency_consistency_perfect(self):
        """Perfect consistency should have 0% CV."""
        strokes = [18, 18, 18, 18]
        times = [30.0, 30.0, 30.0, 30.0]

        result = analyze_stroke_efficiency(strokes, times)
        assert result["stroke_count_consistency"] == 0.0

    def test_efficiency_consistency_variable(self):
        """Variable stroke counts should have higher CV."""
        strokes = [15, 20, 15, 20, 15, 20]  # High variability
        times = [30.0, 32.0, 30.0, 32.0, 30.0, 32.0]

        result = analyze_stroke_efficiency(strokes, times)
        assert result["stroke_count_consistency"] > 10  # Should be significant

    def test_efficiency_fatigue_indicator_no_fatigue(self):
        """No fatigue should have indicator close to 1.0."""
        strokes = [18, 18, 18, 18, 18, 18, 18, 18]
        times = [30.0] * 8

        result = analyze_stroke_efficiency(strokes, times)
        assert 0.95 <= result["fatigue_indicator"] <= 1.05

    def test_efficiency_fatigue_indicator_with_fatigue(self):
        """Fatigue should show indicator > 1.0 (more strokes at end)."""
        # First quarter: 16 strokes, last quarter: 22 strokes
        strokes = [16, 16, 17, 17, 18, 19, 21, 22]
        times = [28.0, 28.0, 29.0, 30.0, 31.0, 32.0, 34.0, 35.0]

        result = analyze_stroke_efficiency(strokes, times)
        assert result["fatigue_indicator"] > 1.2  # Significant fatigue

    def test_efficiency_empty_data(self):
        """Empty data should return default values."""
        result = analyze_stroke_efficiency([], [])

        assert result["avg_swolf"] == 0.0
        assert result["swolf_trend"] == "stable"
        assert result["stroke_count_consistency"] == 0.0
        assert result["fatigue_indicator"] == 1.0

    def test_efficiency_mismatched_lengths_raises_error(self):
        """Mismatched input lengths should raise ValueError."""
        with pytest.raises(ValueError):
            analyze_stroke_efficiency([18, 19], [30.0, 31.0, 32.0])


class TestFormatSwimPace:
    """Tests for swim pace formatting."""

    def test_format_pace_basic(self):
        """Basic pace formatting."""
        assert format_swim_pace(90) == "1:30/100m"
        assert format_swim_pace(100) == "1:40/100m"
        assert format_swim_pace(120) == "2:00/100m"

    def test_format_pace_sub_minute(self):
        """Sub-minute pace formatting."""
        assert format_swim_pace(55) == "0:55/100m"

    def test_format_pace_with_seconds_padding(self):
        """Seconds should be zero-padded."""
        assert format_swim_pace(65) == "1:05/100m"
        assert format_swim_pace(122) == "2:02/100m"


class TestGetSwimZoneForPace:
    """Tests for swim zone classification by pace."""

    def test_zone_at_css(self):
        """Pace at CSS should be Zone 3."""
        zone = get_swim_zone_for_pace(100, 100)
        assert zone == 3

    def test_zone_recovery(self):
        """Very slow pace should be Zone 1."""
        zone = get_swim_zone_for_pace(125, 100)  # 125% of CSS
        assert zone == 1

    def test_zone_aerobic(self):
        """Moderately slow pace should be Zone 2."""
        zone = get_swim_zone_for_pace(110, 100)  # 110% of CSS
        assert zone == 2

    def test_zone_threshold(self):
        """Pace near CSS should be Zone 3."""
        zone = get_swim_zone_for_pace(98, 100)  # 98% of CSS
        assert zone == 3

    def test_zone_vo2max(self):
        """Faster than CSS should be Zone 4."""
        zone = get_swim_zone_for_pace(90, 100)  # 90% of CSS
        assert zone == 4

    def test_zone_sprint(self):
        """Much faster than CSS should be Zone 5."""
        zone = get_swim_zone_for_pace(80, 100)  # 80% of CSS
        assert zone == 5

    def test_zone_extremely_slow(self):
        """Extremely slow pace should return Zone 0."""
        zone = get_swim_zone_for_pace(150, 100)  # 150% of CSS
        assert zone == 0


class TestEstimateCSSFromRaceTimes:
    """Tests for CSS estimation from race results."""

    def test_estimate_from_400m(self):
        """CSS estimation from 400m race."""
        # 400m in 5:00 (300s) = 75 sec/100m race pace
        # CSS should be slightly slower (97% adjustment)
        css = estimate_css_from_race_times(400, 300)
        assert 70 <= css <= 80

    def test_estimate_from_200m(self):
        """CSS estimation from 200m race."""
        # 200m in 2:30 (150s) = 75 sec/100m race pace
        # CSS should be slightly faster (102% adjustment)
        css = estimate_css_from_race_times(200, 150)
        assert 75 <= css <= 80

    def test_estimate_from_1500m(self):
        """CSS estimation from 1500m race (should be close to CSS)."""
        # 1500m in 25:00 (1500s) = 100 sec/100m race pace
        # 1500m pace is close to CSS
        css = estimate_css_from_race_times(1500, 1500)
        assert 95 <= css <= 105

    def test_estimate_from_100m_sprint(self):
        """CSS estimation from 100m sprint."""
        # 100m in 60s = 60 sec/100m sprint pace
        # CSS should be slower (108% adjustment)
        css = estimate_css_from_race_times(100, 60)
        assert 60 <= css <= 70

    def test_estimate_invalid_inputs_raises_error(self):
        """Invalid inputs should raise ValueError."""
        with pytest.raises(ValueError):
            estimate_css_from_race_times(0, 300)
        with pytest.raises(ValueError):
            estimate_css_from_race_times(400, 0)
        with pytest.raises(ValueError):
            estimate_css_from_race_times(-400, 300)


class TestEdgeCases:
    """Tests for edge cases with very fast/slow swimmers."""

    def test_elite_swimmer_metrics(self):
        """Test metrics for elite/competitive swimmers."""
        # Elite: 400m in 4:00 (240s), 200m in 1:50 (110s)
        css = calculate_css(240, 110)
        assert css < 80  # Elite CSS

        zones = get_swim_zones(css)
        # Z5 sprint should be very fast
        assert zones["zone5_sprint"][0] < 60

    def test_beginner_swimmer_metrics(self):
        """Test metrics for beginner swimmers."""
        # Beginner: 400m in 10:00 (600s), 200m in 4:30 (270s)
        css = calculate_css(600, 270)
        assert css > 50  # Beginner CSS is slower

        zones = get_swim_zones(css)
        # Z1 recovery can be quite slow
        assert zones["zone1_recovery"][1] > 70

    def test_very_long_swim_tss(self):
        """Test TSS for very long swims."""
        # 2 hour easy swim at 120% CSS pace
        tss = estimate_swim_tss(120, 120, 100)
        assert 80 < tss < 150  # Should be significant but not extreme

    def test_very_short_interval_metrics(self):
        """Test metrics for very short intervals."""
        # 25m sprint: 12 seconds, 10 strokes
        swolf = calculate_swolf(12.0, 10)
        assert 20 <= swolf <= 30  # Elite sprint SWOLF

        stroke_rate = calculate_stroke_rate(10, 12.0)
        assert stroke_rate == 50.0  # 50 strokes/min

    def test_open_water_long_distance(self):
        """Test metrics for open water/long distance swimming."""
        # 5K swim in 75 minutes
        pace = calculate_pace_per_100m(5000.0, 4500.0)  # 75 min = 4500 sec
        assert pace == 90  # 1:30/100m pace

        # TSS for long open water swim
        tss = estimate_swim_tss(75, 90, 85)  # At CSS pace
        assert tss > 100  # Should be significant load
