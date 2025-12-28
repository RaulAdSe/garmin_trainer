"""Tests for swimming metrics calculations."""

import pytest
from training_analyzer.metrics.swim import (
    calculate_swolf,
    calculate_stroke_rate,
    calculate_pace_per_100m,
    calculate_css,
    calculate_swim_tss,
    calculate_swim_zones,
    calculate_stroke_efficiency,
    calculate_swim_efficiency_index,
    estimate_swim_tss,
    get_swim_zones,
    get_swim_zone_for_pace,
    format_swim_pace,
    analyze_stroke_efficiency,
    analyze_swim_session,
    estimate_css_from_race_times,
)


class TestSWOLFCalculation:
    """Tests for SWOLF score calculation."""

    def test_swolf_basic_calculation(self):
        """SWOLF = time + strokes."""
        swolf = calculate_swolf(time_per_length_sec=30.0, strokes_per_length=18)
        assert swolf == 48.0

    def test_swolf_elite_range(self):
        """Elite swimmers should have SWOLF 35-45 in 25m pool."""
        swolf = calculate_swolf(time_per_length_sec=20.0, strokes_per_length=16)
        assert 35 <= swolf <= 45

    def test_swolf_recreational_range(self):
        """Recreational swimmers typically 55-70."""
        swolf = calculate_swolf(time_per_length_sec=35.0, strokes_per_length=22)
        assert 55 <= swolf <= 70

    def test_swolf_negative_time_raises(self):
        """Negative time should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_swolf(time_per_length_sec=-5.0, strokes_per_length=18)

    def test_swolf_negative_strokes_raises(self):
        """Negative strokes should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_swolf(time_per_length_sec=30.0, strokes_per_length=-5)

    def test_swolf_zero_values(self):
        """Zero values should work (edge case)."""
        swolf = calculate_swolf(time_per_length_sec=0.0, strokes_per_length=0)
        assert swolf == 0.0


class TestCSSCalculation:
    """Tests for Critical Swim Speed calculation."""

    def test_css_basic_calculation(self):
        """CSS from 400m and 200m test times."""
        # 400m in 6:00 (360s), 200m in 2:45 (165s)
        # CSS speed = 200 / (360 - 165) = 200 / 195 = 1.026 m/s
        # CSS pace = 100 / 1.026 = 97.5 sec/100m
        css = calculate_css(t400_sec=360.0, t200_sec=165.0)
        assert 95 <= css <= 100  # Around 1:37-1:40/100m

    def test_css_faster_swimmer(self):
        """Faster swimmer should have lower CSS pace."""
        # 400m in 5:00 (300s), 200m in 2:20 (140s)
        # CSS speed = 200 / (300 - 140) = 200 / 160 = 1.25 m/s
        # CSS pace = 100 / 1.25 = 80 sec/100m (1:20/100m)
        css = calculate_css(t400_sec=300.0, t200_sec=140.0)
        assert css < 85  # Should be around 1:20/100m

    def test_css_slower_swimmer(self):
        """Slower swimmer should have higher CSS pace."""
        # 400m in 8:00 (480s), 200m in 3:40 (220s)
        css = calculate_css(t400_sec=480.0, t200_sec=220.0)
        assert css > 70  # Above 1:10/100m

    def test_css_negative_time_raises(self):
        """Negative times should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            calculate_css(t400_sec=-360.0, t200_sec=165.0)

    def test_css_invalid_order_raises(self):
        """400m time must be greater than 200m time."""
        with pytest.raises(ValueError, match="greater than"):
            calculate_css(t400_sec=165.0, t200_sec=360.0)

    def test_css_equal_times_raises(self):
        """Equal times should raise ValueError."""
        with pytest.raises(ValueError, match="greater than"):
            calculate_css(t400_sec=200.0, t200_sec=200.0)


class TestSwimZones:
    """Tests for swim zone calculation."""

    def test_swim_zones_basic(self):
        """Test zone calculation from CSS."""
        css_pace = 100  # 1:40/100m
        zones = get_swim_zones(css_pace)

        assert "zone1_recovery" in zones
        assert "zone2_aerobic" in zones
        assert "zone3_threshold" in zones
        assert "zone4_vo2max" in zones
        assert "zone5_sprint" in zones

    def test_swim_zones_ordering(self):
        """Zone paces should be properly ordered (lower = faster)."""
        css_pace = 100
        zones = get_swim_zones(css_pace)

        # Zone 5 (sprint) should be fastest (lowest numbers)
        # Zone 1 (recovery) should be slowest (highest numbers)
        assert zones["zone5_sprint"][0] < zones["zone4_vo2max"][0]
        assert zones["zone4_vo2max"][0] < zones["zone3_threshold"][0]
        assert zones["zone3_threshold"][0] < zones["zone2_aerobic"][0]
        assert zones["zone2_aerobic"][0] < zones["zone1_recovery"][0]

    def test_swim_zones_threshold_around_css(self):
        """Zone 3 (threshold) should be around CSS pace."""
        css_pace = 100
        zones = get_swim_zones(css_pace)

        z3_fast, z3_slow = zones["zone3_threshold"]
        # Zone 3 should bracket CSS (95-105% of CSS)
        assert z3_fast < css_pace < z3_slow

    def test_calculate_swim_zones_alias(self):
        """calculate_swim_zones should be alias for get_swim_zones."""
        css_pace = 100
        zones1 = get_swim_zones(css_pace)
        zones2 = calculate_swim_zones(css_pace)
        assert zones1 == zones2

    def test_swim_zones_negative_css_raises(self):
        """Negative CSS should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            get_swim_zones(-100)


class TestSwimZoneClassification:
    """Tests for classifying pace into zones."""

    def test_zone_for_pace_at_css(self):
        """Pace at CSS should be Zone 3."""
        css_pace = 100
        zone = get_swim_zone_for_pace(100, css_pace)
        assert zone == 3

    def test_zone_for_pace_recovery(self):
        """Slow pace should be Zone 1."""
        css_pace = 100
        zone = get_swim_zone_for_pace(125, css_pace)  # 125% of CSS
        assert zone == 1

    def test_zone_for_pace_sprint(self):
        """Fast pace should be Zone 5."""
        css_pace = 100
        zone = get_swim_zone_for_pace(75, css_pace)  # 75% of CSS
        assert zone == 5

    def test_zone_for_pace_too_slow(self):
        """Very slow pace should return 0."""
        css_pace = 100
        zone = get_swim_zone_for_pace(150, css_pace)  # 150% of CSS
        assert zone == 0


class TestSwimTSS:
    """Tests for swim Training Stress Score calculation."""

    def test_swim_tss_at_css(self):
        """One hour at CSS pace should give approximately 100 TSS."""
        tss = estimate_swim_tss(duration_min=60, pace_per_100m=100, css_pace=100)
        # At CSS (IF=1.0), 60 min should give 100 TSS
        assert 95 <= tss <= 105

    def test_swim_tss_faster_than_css(self):
        """Faster than CSS should give higher TSS."""
        tss_at_css = estimate_swim_tss(duration_min=60, pace_per_100m=100, css_pace=100)
        tss_fast = estimate_swim_tss(duration_min=60, pace_per_100m=90, css_pace=100)
        assert tss_fast > tss_at_css

    def test_swim_tss_slower_than_css(self):
        """Slower than CSS should give lower TSS."""
        tss_at_css = estimate_swim_tss(duration_min=60, pace_per_100m=100, css_pace=100)
        tss_slow = estimate_swim_tss(duration_min=60, pace_per_100m=110, css_pace=100)
        assert tss_slow < tss_at_css

    def test_swim_tss_scales_with_duration(self):
        """TSS should scale with duration."""
        tss_30 = estimate_swim_tss(duration_min=30, pace_per_100m=100, css_pace=100)
        tss_60 = estimate_swim_tss(duration_min=60, pace_per_100m=100, css_pace=100)
        # Should be approximately 2x for 2x duration
        ratio = tss_60 / tss_30
        assert 1.9 < ratio < 2.1

    def test_swim_tss_zero_duration(self):
        """Zero duration should give 0 TSS."""
        tss = estimate_swim_tss(duration_min=0, pace_per_100m=100, css_pace=100)
        assert tss == 0.0

    def test_calculate_swim_tss_alias(self):
        """calculate_swim_tss should be alias for estimate_swim_tss."""
        tss1 = estimate_swim_tss(duration_min=60, pace_per_100m=100, css_pace=100)
        tss2 = calculate_swim_tss(duration_min=60, pace_per_100m=100, css_pace=100)
        assert tss1 == tss2


class TestStrokeEfficiency:
    """Tests for stroke efficiency (DPS) calculation."""

    def test_stroke_efficiency_basic(self):
        """Basic DPS calculation."""
        # 25m in 15 strokes = 1.67 m/stroke
        dps = calculate_stroke_efficiency(distance_m=25.0, strokes=15)
        assert abs(dps - 1.67) < 0.01

    def test_stroke_efficiency_elite(self):
        """Elite swimmer DPS should be 2.0-2.5 m/stroke."""
        dps = calculate_stroke_efficiency(distance_m=25.0, strokes=11)
        assert 2.0 <= dps <= 2.5

    def test_stroke_efficiency_beginner(self):
        """Beginner swimmer DPS should be lower."""
        dps = calculate_stroke_efficiency(distance_m=25.0, strokes=25)
        assert dps < 1.2

    def test_stroke_efficiency_zero_strokes_zero_distance(self):
        """Zero strokes and zero distance should return 0."""
        dps = calculate_stroke_efficiency(distance_m=0.0, strokes=0)
        assert dps == 0.0

    def test_stroke_efficiency_zero_strokes_positive_distance_raises(self):
        """Zero strokes with positive distance should raise."""
        with pytest.raises(ValueError, match="zero strokes"):
            calculate_stroke_efficiency(distance_m=25.0, strokes=0)

    def test_stroke_efficiency_negative_distance_raises(self):
        """Negative distance should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_stroke_efficiency(distance_m=-25.0, strokes=15)

    def test_stroke_efficiency_negative_strokes_raises(self):
        """Negative strokes should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_stroke_efficiency(distance_m=25.0, strokes=-15)


class TestSwimEfficiencyIndex:
    """Tests for swim efficiency index calculation."""

    def test_efficiency_index_elite_25m(self):
        """Elite SWOLF in 25m pool should give high efficiency."""
        efficiency = calculate_swim_efficiency_index(swolf=40.0, pool_length_m=25)
        assert efficiency >= 85

    def test_efficiency_index_beginner_25m(self):
        """Beginner SWOLF in 25m pool should give low efficiency."""
        efficiency = calculate_swim_efficiency_index(swolf=75.0, pool_length_m=25)
        assert efficiency <= 20

    def test_efficiency_index_50m_pool(self):
        """50m pool should have different scaling."""
        # Same SWOLF in 50m pool means different efficiency
        eff_25m = calculate_swim_efficiency_index(swolf=60.0, pool_length_m=25)
        eff_50m = calculate_swim_efficiency_index(swolf=60.0, pool_length_m=50)
        # 60 is poor in 25m pool but excellent in 50m pool
        assert eff_50m > eff_25m

    def test_efficiency_index_zero_swolf(self):
        """Zero SWOLF should return 0."""
        efficiency = calculate_swim_efficiency_index(swolf=0.0, pool_length_m=25)
        assert efficiency == 0.0

    def test_efficiency_index_clamped_to_100(self):
        """Very low SWOLF should be clamped to 100."""
        efficiency = calculate_swim_efficiency_index(swolf=30.0, pool_length_m=25)
        assert efficiency == 100.0


class TestStrokeAnalysis:
    """Tests for stroke efficiency analysis."""

    def test_analyze_stroke_efficiency_basic(self):
        """Basic stroke analysis with consistent data."""
        strokes = [18, 18, 18, 18, 18, 18, 18, 18]
        times = [30.0, 30.0, 30.0, 30.0, 30.0, 30.0, 30.0, 30.0]

        result = analyze_stroke_efficiency(strokes, times)

        assert "avg_swolf" in result
        assert result["avg_swolf"] == 48.0
        assert result["swolf_trend"] == "stable"
        assert result["stroke_count_consistency"] < 5  # Low CV

    def test_analyze_stroke_efficiency_declining(self):
        """Analysis should detect declining efficiency (fatigue)."""
        # Start efficient, end less efficient
        strokes = [16, 17, 18, 19, 20, 21, 22, 23]
        times = [28.0, 29.0, 30.0, 31.0, 32.0, 33.0, 34.0, 35.0]

        result = analyze_stroke_efficiency(strokes, times)

        assert result["swolf_trend"] == "declining"
        assert result["fatigue_indicator"] > 1.0  # Last quarter worse than first

    def test_analyze_stroke_efficiency_improving(self):
        """Analysis should detect improving efficiency."""
        # Start tired, improve as session progresses
        strokes = [22, 21, 20, 19, 18, 17, 16, 15]
        times = [34.0, 33.0, 32.0, 31.0, 30.0, 29.0, 28.0, 27.0]

        result = analyze_stroke_efficiency(strokes, times)

        assert result["swolf_trend"] == "improving"
        assert result["fatigue_indicator"] < 1.0

    def test_analyze_stroke_efficiency_empty(self):
        """Empty input should return defaults."""
        result = analyze_stroke_efficiency([], [])

        assert result["avg_swolf"] == 0.0
        assert result["swolf_trend"] == "stable"
        assert result["fatigue_indicator"] == 1.0

    def test_analyze_stroke_efficiency_mismatched_lengths_raises(self):
        """Mismatched list lengths should raise ValueError."""
        with pytest.raises(ValueError, match="same length"):
            analyze_stroke_efficiency([18, 18], [30.0])


class TestSwimSessionAnalysis:
    """Tests for comprehensive swim session analysis."""

    def test_analyze_swim_session_basic(self):
        """Basic session analysis."""
        lengths = [
            {"time_sec": 30.0, "strokes": 18},
            {"time_sec": 31.0, "strokes": 18},
            {"time_sec": 30.5, "strokes": 17},
            {"time_sec": 30.0, "strokes": 18},
        ]

        result = analyze_swim_session(lengths, pool_length_m=25)

        assert result["total_distance_m"] == 100
        assert result["avg_pace_per_100m"] > 0
        assert "stroke_analysis" in result
        assert "efficiency_index" in result

    def test_analyze_swim_session_with_css(self):
        """Session analysis with CSS should include zone distribution."""
        lengths = [
            {"time_sec": 30.0, "strokes": 18},
            {"time_sec": 30.0, "strokes": 18},
            {"time_sec": 30.0, "strokes": 18},
            {"time_sec": 30.0, "strokes": 18},
        ]

        result = analyze_swim_session(lengths, pool_length_m=25, css_pace=120)

        assert "zone_distribution" in result
        assert len(result["zone_distribution"]) > 0

    def test_analyze_swim_session_empty(self):
        """Empty session should return zeros."""
        result = analyze_swim_session([], pool_length_m=25)

        assert result["total_distance_m"] == 0
        assert result["avg_pace_per_100m"] == 0


class TestCSSEstimation:
    """Tests for CSS estimation from race times."""

    def test_estimate_css_from_1500m(self):
        """1500m race pace should be close to CSS."""
        # 1500m in 25 minutes = 100 sec/100m
        css = estimate_css_from_race_times(race_distance_m=1500, race_time_sec=1500)
        assert abs(css - 100) < 5  # Should be close to race pace

    def test_estimate_css_from_100m_sprint(self):
        """100m sprint is faster than CSS."""
        # 100m in 60 seconds = 60 sec/100m
        css = estimate_css_from_race_times(race_distance_m=100, race_time_sec=60)
        # CSS should be slower than sprint pace (higher number)
        assert css > 60

    def test_estimate_css_from_400m(self):
        """400m race pace should be slightly faster than CSS."""
        # 400m in 360 seconds = 90 sec/100m
        css = estimate_css_from_race_times(race_distance_m=400, race_time_sec=360)
        # CSS should be slightly slower (higher number)
        assert css > 85

    def test_estimate_css_negative_values_raises(self):
        """Negative values should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            estimate_css_from_race_times(race_distance_m=-100, race_time_sec=60)


class TestFormatSwimPace:
    """Tests for swim pace formatting."""

    def test_format_swim_pace_basic(self):
        """Basic pace formatting."""
        formatted = format_swim_pace(105)  # 1:45/100m
        assert formatted == "1:45/100m"

    def test_format_swim_pace_under_minute(self):
        """Sub-minute pace formatting."""
        formatted = format_swim_pace(55)  # 0:55/100m
        assert formatted == "0:55/100m"

    def test_format_swim_pace_two_minutes(self):
        """Two minute pace formatting."""
        formatted = format_swim_pace(125)  # 2:05/100m
        assert formatted == "2:05/100m"

    def test_format_swim_pace_padded_seconds(self):
        """Seconds should be zero-padded."""
        formatted = format_swim_pace(65)  # 1:05/100m
        assert formatted == "1:05/100m"


class TestPaceCalculation:
    """Tests for pace per 100m calculation."""

    def test_pace_basic_calculation(self):
        """Basic pace calculation."""
        # 100m in 100 seconds = 100 sec/100m
        pace = calculate_pace_per_100m(distance_m=100, duration_sec=100)
        assert pace == 100

    def test_pace_longer_distance(self):
        """Pace calculation over longer distance."""
        # 1000m in 1000 seconds = 100 sec/100m
        pace = calculate_pace_per_100m(distance_m=1000, duration_sec=1000)
        assert pace == 100

    def test_pace_zero_distance_raises(self):
        """Zero distance should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            calculate_pace_per_100m(distance_m=0, duration_sec=100)

    def test_pace_negative_duration_raises(self):
        """Negative duration should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_pace_per_100m(distance_m=100, duration_sec=-100)


class TestStrokeRate:
    """Tests for stroke rate calculation."""

    def test_stroke_rate_basic(self):
        """Basic stroke rate calculation."""
        # 60 strokes in 60 seconds = 60 strokes/min
        rate = calculate_stroke_rate(strokes=60, duration_sec=60)
        assert rate == 60.0

    def test_stroke_rate_distance_freestyle(self):
        """Distance freestyle typical stroke rate."""
        # 55 strokes in 60 seconds = 55 spm
        rate = calculate_stroke_rate(strokes=55, duration_sec=60)
        assert 50 <= rate <= 60

    def test_stroke_rate_sprint(self):
        """Sprint typical stroke rate."""
        # 80 strokes in 60 seconds = 80 spm
        rate = calculate_stroke_rate(strokes=80, duration_sec=60)
        assert 70 <= rate <= 90

    def test_stroke_rate_zero_duration(self):
        """Zero duration should return 0."""
        rate = calculate_stroke_rate(strokes=60, duration_sec=0)
        assert rate == 0.0

    def test_stroke_rate_negative_strokes_raises(self):
        """Negative strokes should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_stroke_rate(strokes=-60, duration_sec=60)
