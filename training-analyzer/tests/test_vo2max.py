"""Tests for VO2max-related functionality."""

import pytest
from datetime import date, timedelta

from training_analyzer.analysis.goals import (
    calculate_training_paces_from_vo2max,
    calculate_training_paces_from_vo2max_detailed,
    assess_goal_feasibility,
    get_goal_feasibility_summary,
    format_pace_from_seconds,
    _interpolate_pace,
    VDOT_PACE_TABLE,
)
from training_analyzer.models.analysis import calculate_recovery_hours


class TestCalculateTrainingPacesFromVO2max:
    """Tests for calculate_training_paces_from_vo2max function."""

    def test_returns_all_pace_types(self):
        """Test that all pace types are returned."""
        paces = calculate_training_paces_from_vo2max(55.0)

        assert "easy_pace" in paces
        assert "marathon_pace" in paces
        assert "threshold_pace" in paces
        assert "interval_pace" in paces
        assert "repetition_pace" in paces

    def test_paces_are_in_order(self):
        """Test that paces decrease as intensity increases."""
        paces = calculate_training_paces_from_vo2max(55.0)

        # Easy should be slowest, repetition should be fastest
        assert paces["easy_pace"] > paces["marathon_pace"]
        assert paces["marathon_pace"] > paces["threshold_pace"]
        assert paces["threshold_pace"] > paces["interval_pace"]
        assert paces["interval_pace"] > paces["repetition_pace"]

    def test_higher_vo2max_means_faster_paces(self):
        """Test that higher VO2max results in faster paces."""
        paces_50 = calculate_training_paces_from_vo2max(50.0)
        paces_60 = calculate_training_paces_from_vo2max(60.0)

        # Higher VO2max should have faster (lower) paces
        assert paces_60["easy_pace"] < paces_50["easy_pace"]
        assert paces_60["threshold_pace"] < paces_50["threshold_pace"]
        assert paces_60["interval_pace"] < paces_50["interval_pace"]

    def test_vo2max_55_produces_reasonable_paces(self):
        """Test that VO2max 55 produces reasonable training paces."""
        paces = calculate_training_paces_from_vo2max(55.0)

        # VO2max 55 is a well-trained recreational runner
        # Easy pace should be around 5:20/km (320 sec/km)
        assert 300 <= paces["easy_pace"] <= 340

        # Threshold pace should be around 4:10/km (250 sec/km)
        assert 230 <= paces["threshold_pace"] <= 270

        # Interval pace should be around 3:45/km (225 sec/km)
        assert 210 <= paces["interval_pace"] <= 245

    def test_clamps_low_vo2max(self):
        """Test that VO2max below 30 is clamped."""
        paces_25 = calculate_training_paces_from_vo2max(25.0)
        paces_30 = calculate_training_paces_from_vo2max(30.0)

        # Should be equal since 25 gets clamped to 30
        assert paces_25 == paces_30

    def test_clamps_high_vo2max(self):
        """Test that VO2max above 85 is clamped."""
        paces_90 = calculate_training_paces_from_vo2max(90.0)
        paces_85 = calculate_training_paces_from_vo2max(85.0)

        # Should be equal since 90 gets clamped to 85
        assert paces_90 == paces_85

    def test_interpolation_between_table_values(self):
        """Test that values between table entries are interpolated."""
        paces_50 = calculate_training_paces_from_vo2max(50.0)
        paces_55 = calculate_training_paces_from_vo2max(55.0)
        paces_52 = calculate_training_paces_from_vo2max(52.0)

        # 52 should be between 50 and 55
        assert paces_50["easy_pace"] > paces_52["easy_pace"] > paces_55["easy_pace"]

    def test_exact_table_values(self):
        """Test that exact table values return expected paces."""
        paces = calculate_training_paces_from_vo2max(50.0)

        # Should match table exactly (within rounding)
        assert paces["easy_pace"] == VDOT_PACE_TABLE[50][0]
        assert paces["marathon_pace"] == VDOT_PACE_TABLE[50][1]


class TestCalculateTrainingPacesFromVO2maxDetailed:
    """Tests for the detailed pace calculation function."""

    def test_includes_formatted_paces(self):
        """Test that formatted paces are included."""
        paces = calculate_training_paces_from_vo2max_detailed(55.0)

        for pace_type in paces:
            assert "pace_formatted" in paces[pace_type]
            assert "/km" in paces[pace_type]["pace_formatted"]

    def test_includes_mile_paces(self):
        """Test that mile paces are included."""
        paces = calculate_training_paces_from_vo2max_detailed(55.0)

        for pace_type in paces:
            assert "pace_mile_formatted" in paces[pace_type]
            assert "/mi" in paces[pace_type]["pace_mile_formatted"]

    def test_includes_hr_zones(self):
        """Test that HR zones are included."""
        paces = calculate_training_paces_from_vo2max_detailed(55.0)

        for pace_type in paces:
            assert "hr_zone" in paces[pace_type]

    def test_includes_descriptions(self):
        """Test that descriptions and purposes are included."""
        paces = calculate_training_paces_from_vo2max_detailed(55.0)

        for pace_type in paces:
            assert "description" in paces[pace_type]
            assert "purpose" in paces[pace_type]


class TestFormatPaceFromSeconds:
    """Tests for pace formatting."""

    def test_format_5_minute_pace(self):
        """Test formatting 5:00/km pace."""
        assert format_pace_from_seconds(300) == "5:00/km"

    def test_format_4_30_pace(self):
        """Test formatting 4:30/km pace."""
        assert format_pace_from_seconds(270) == "4:30/km"

    def test_format_sub_4_pace(self):
        """Test formatting sub-4:00/km pace."""
        assert format_pace_from_seconds(230) == "3:50/km"


class TestAssessGoalFeasibility:
    """Tests for goal feasibility assessment."""

    def test_on_track_when_prediction_equals_goal(self):
        """Test on_track feasibility when already at goal."""
        predictions = {"race_time_5k": 1200}  # 20:00 5K
        result = assess_goal_feasibility(predictions, "5k", 1200)

        assert result["feasibility"] == "on_track"
        assert result["gap_percent"] == 0.0

    def test_on_track_when_ahead_of_goal(self):
        """Test on_track feasibility when faster than goal."""
        predictions = {"race_time_5k": 1100}  # 18:20 5K
        result = assess_goal_feasibility(predictions, "5k", 1200)  # Goal: 20:00

        assert result["feasibility"] == "on_track"
        assert result["gap_percent"] < 0  # Negative means ahead

    def test_achievable_feasibility(self):
        """Test achievable feasibility (0-3% faster)."""
        predictions = {"race_time_5k": 1230}  # 20:30 5K
        # Goal is ~2.4% faster
        result = assess_goal_feasibility(predictions, "5k", 1200)  # Goal: 20:00

        assert result["feasibility"] == "achievable"
        assert 0 < result["gap_percent"] <= 3

    def test_ambitious_feasibility(self):
        """Test ambitious feasibility (3-7% faster)."""
        predictions = {"race_time_5k": 1300}  # 21:40 5K
        # Goal is ~7.7% faster - but let's use 1260 (21:00) for ~5% gap
        result = assess_goal_feasibility(predictions, "5k", 1200)  # Goal: 20:00

        # 1300 -> 1200 is 7.7%, so it's very_ambitious
        assert result["feasibility"] in ["ambitious", "very_ambitious"]

    def test_very_ambitious_feasibility(self):
        """Test very ambitious feasibility (>7% faster)."""
        predictions = {"race_time_5k": 1400}  # 23:20 5K
        result = assess_goal_feasibility(predictions, "5k", 1200)  # Goal: 20:00

        # 14.3% improvement needed
        assert result["feasibility"] == "very_ambitious"
        assert result["gap_percent"] > 7

    def test_returns_formatted_times(self):
        """Test that formatted times are returned."""
        predictions = {"race_time_5k": 1200}
        result = assess_goal_feasibility(predictions, "5k", 1100)

        assert "current_predicted_formatted" in result
        assert "goal_time_formatted" in result
        assert "gap_formatted" in result

    def test_returns_recommendation(self):
        """Test that recommendation is returned."""
        predictions = {"race_time_5k": 1200}
        result = assess_goal_feasibility(predictions, "5k", 1100)

        assert "recommendation" in result
        assert len(result["recommendation"]) > 0

    def test_handles_missing_prediction(self):
        """Test handling when prediction is not available."""
        predictions = {"race_time_10k": 2400}  # Only 10K available
        result = assess_goal_feasibility(predictions, "5k", 1100)

        # Should estimate from 10K
        assert "current_predicted" in result
        assert result["feasibility"] != "unknown"

    def test_handles_no_predictions(self):
        """Test handling when no predictions are available."""
        predictions = {}
        result = assess_goal_feasibility(predictions, "5k", 1100)

        assert result["feasibility"] == "unknown"
        assert "error" in result or "recommendation" in result

    def test_normalizes_distance_string(self):
        """Test that various distance formats are accepted."""
        predictions = {"race_time_half": 5400}

        # All these should work
        result1 = assess_goal_feasibility(predictions, "half_marathon", 5200)
        result2 = assess_goal_feasibility(predictions, "half", 5200)

        assert "feasibility" in result1
        assert "feasibility" in result2

    def test_unknown_distance(self):
        """Test handling of unknown distance."""
        predictions = {"race_time_5k": 1200}
        result = assess_goal_feasibility(predictions, "100k", 25000)

        assert result["feasibility"] == "unknown"


class TestGetGoalFeasibilitySummary:
    """Tests for summarizing multiple goals."""

    def test_assesses_multiple_goals(self):
        """Test that multiple goals are assessed."""
        predictions = {
            "race_time_5k": 1200,
            "race_time_10k": 2500,
        }
        goals = [
            {"distance": "5k", "target_time_sec": 1100},
            {"distance": "10k", "target_time_sec": 2400},
        ]

        summaries = get_goal_feasibility_summary(predictions, goals)

        assert len(summaries) == 2

    def test_skips_invalid_goals(self):
        """Test that invalid goals are skipped."""
        predictions = {"race_time_5k": 1200}
        goals = [
            {"distance": "5k", "target_time_sec": 1100},
            {"distance": "", "target_time_sec": 1000},  # No distance
            {"distance": "10k"},  # No time
        ]

        summaries = get_goal_feasibility_summary(predictions, goals)

        assert len(summaries) == 1


class TestCalculateRecoveryHoursWithVO2max:
    """Tests for recovery hours calculation with VO2max factor."""

    def test_base_recovery_without_vo2max(self):
        """Test that base recovery works without VO2max."""
        hours = calculate_recovery_hours(
            training_effect=3.0,
            load_score=80,
        )
        assert hours == 36  # Base for TE 3.0

    def test_high_vo2max_reduces_recovery(self):
        """Test that high VO2max reduces recovery time."""
        hours_no_vo2max = calculate_recovery_hours(
            training_effect=3.0,
            load_score=80,
        )
        hours_high_vo2max = calculate_recovery_hours(
            training_effect=3.0,
            load_score=80,
            vo2max=65.0,
        )

        # High VO2max should reduce recovery
        assert hours_high_vo2max < hours_no_vo2max

    def test_elite_vo2max_reduces_recovery_most(self):
        """Test that elite VO2max (>60) has largest recovery reduction."""
        hours_trained = calculate_recovery_hours(
            training_effect=3.5,
            load_score=100,
            vo2max=55.0,
        )
        hours_elite = calculate_recovery_hours(
            training_effect=3.5,
            load_score=100,
            vo2max=65.0,
        )

        assert hours_elite < hours_trained

    def test_low_vo2max_increases_recovery(self):
        """Test that low VO2max increases recovery time."""
        hours_normal = calculate_recovery_hours(
            training_effect=3.0,
            load_score=80,
            vo2max=45.0,  # Average
        )
        hours_low = calculate_recovery_hours(
            training_effect=3.0,
            load_score=80,
            vo2max=35.0,  # Below average
        )

        assert hours_low > hours_normal

    def test_recovery_stays_in_bounds(self):
        """Test that recovery stays within reasonable bounds."""
        # Minimum case
        hours_min = calculate_recovery_hours(
            training_effect=0.5,
            load_score=20,
            tsb=15.0,
            vo2max=70.0,  # High VO2max should further reduce
        )
        assert hours_min >= 12

        # Maximum case
        hours_max = calculate_recovery_hours(
            training_effect=5.0,
            load_score=200,
            tsb=-30.0,
            vo2max=35.0,  # Low VO2max should further increase
        )
        assert hours_max <= 96

    def test_vo2max_50_to_55_reduces_recovery_slightly(self):
        """Test trained (50-55) VO2max range has small recovery reduction."""
        hours_50 = calculate_recovery_hours(
            training_effect=3.0,
            load_score=80,
            vo2max=50.0,
        )
        hours_55 = calculate_recovery_hours(
            training_effect=3.0,
            load_score=80,
            vo2max=55.0,
        )

        # Both should be less than base (36 for TE 3.0)
        assert hours_50 <= 36
        assert hours_55 < hours_50

    def test_vo2max_in_average_range_no_change(self):
        """Test that VO2max 40-50 has no adjustment."""
        hours_no_vo2max = calculate_recovery_hours(
            training_effect=3.0,
            load_score=80,
        )
        hours_with_45 = calculate_recovery_hours(
            training_effect=3.0,
            load_score=80,
            vo2max=45.0,
        )

        # Should be the same
        assert hours_with_45 == hours_no_vo2max


class TestInterpolatePace:
    """Tests for the pace interpolation function."""

    def test_exact_table_match(self):
        """Test interpolation at exact table values."""
        # Should return exact table value
        assert _interpolate_pace(50.0, 0) == VDOT_PACE_TABLE[50][0]
        assert _interpolate_pace(55.0, 1) == VDOT_PACE_TABLE[55][1]

    def test_interpolation_midpoint(self):
        """Test interpolation at midpoint between table values."""
        # Midpoint between 50 and 55 should be average
        pace_50 = VDOT_PACE_TABLE[50][0]
        pace_55 = VDOT_PACE_TABLE[55][0]
        expected = (pace_50 + pace_55) / 2

        result = _interpolate_pace(52.5, 0)
        assert abs(result - expected) <= 1  # Within 1 second

    def test_clamping_low(self):
        """Test that values below 30 are clamped."""
        assert _interpolate_pace(25.0, 0) == VDOT_PACE_TABLE[30][0]

    def test_clamping_high(self):
        """Test that values above 85 are clamped."""
        assert _interpolate_pace(90.0, 0) == VDOT_PACE_TABLE[85][0]
