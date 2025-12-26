"""Tests for actionable insights engine."""

import pytest
from garmin_client.insights import (
    get_optimal_strain_target,
    get_strain_recommendation,
    calculate_sleep_need,
    calculate_sleep_debt,
    calculate_sleep_debt_simple,
    get_sleep_debt_info,
    generate_daily_insight,
    get_sleep_target_breakdown,
    format_hours_minutes,
    DailyInsight,
    SleepDebtInfo,
)
from garmin_client.baselines import PersonalBaselines


class TestGetOptimalStrainTarget:
    """Tests for strain target calculation based on recovery zone."""

    def test_green_zone_high_recovery(self):
        """Test strain target for high recovery (green zone)."""
        result = get_optimal_strain_target(85)
        assert result == (14.0, 21.0)

    def test_green_zone_threshold(self):
        """Test strain target at green zone threshold (67%)."""
        result = get_optimal_strain_target(67)
        assert result == (14.0, 21.0)

    def test_yellow_zone(self):
        """Test strain target for yellow zone recovery."""
        result = get_optimal_strain_target(50)
        assert result == (8.0, 14.0)

    def test_yellow_zone_lower_threshold(self):
        """Test strain target at yellow zone lower threshold (34%)."""
        result = get_optimal_strain_target(34)
        assert result == (8.0, 14.0)

    def test_red_zone(self):
        """Test strain target for red zone recovery."""
        result = get_optimal_strain_target(20)
        assert result == (0.0, 8.0)

    def test_red_zone_edge(self):
        """Test strain target just below yellow zone."""
        result = get_optimal_strain_target(33)
        assert result == (0.0, 8.0)

    def test_zero_recovery(self):
        """Test strain target for zero recovery."""
        result = get_optimal_strain_target(0)
        assert result == (0.0, 8.0)

    def test_max_recovery(self):
        """Test strain target for 100% recovery."""
        result = get_optimal_strain_target(100)
        assert result == (14.0, 21.0)


class TestGetStrainRecommendation:
    """Tests for strain recommendation text."""

    def test_green_zone_recommendation(self):
        """Test recommendation for green zone."""
        result = get_strain_recommendation(75)
        assert "intervals" in result.lower() or "racing" in result.lower()

    def test_yellow_zone_recommendation(self):
        """Test recommendation for yellow zone."""
        result = get_strain_recommendation(50)
        assert "cardio" in result.lower() or "technique" in result.lower()

    def test_red_zone_recommendation(self):
        """Test recommendation for red zone."""
        result = get_strain_recommendation(20)
        assert "rest" in result.lower() or "yoga" in result.lower()


class TestCalculateSleepNeed:
    """Tests for personalized sleep need calculation."""

    def test_basic_sleep_need_no_adjustments(self):
        """Test sleep need with no strain or debt adjustments."""
        result = calculate_sleep_need(
            base_sleep_need=7.5,
            yesterday_strain=10,  # At threshold, no adjustment
            sleep_debt=0
        )
        assert result == 7.5

    def test_sleep_need_with_high_strain(self):
        """Test sleep need with high strain yesterday."""
        result = calculate_sleep_need(
            base_sleep_need=7.5,
            yesterday_strain=15,  # 5 points above threshold
            sleep_debt=0
        )
        # strain_adjustment = (15 - 10) * 0.05 = 0.25
        assert result == 7.75

    def test_sleep_need_with_sleep_debt(self):
        """Test sleep need with accumulated sleep debt."""
        result = calculate_sleep_need(
            base_sleep_need=7.5,
            yesterday_strain=10,
            sleep_debt=3.5  # 3.5 hours debt
        )
        # debt_repayment = 3.5 / 7 = 0.5
        assert result == 8.0

    def test_sleep_need_with_both_adjustments(self):
        """Test sleep need with both strain and debt adjustments."""
        result = calculate_sleep_need(
            base_sleep_need=7.0,
            yesterday_strain=16,  # 6 points above threshold
            sleep_debt=2.1  # 2.1 hours debt
        )
        # strain_adjustment = (16 - 10) * 0.05 = 0.30
        # debt_repayment = 2.1 / 7 = 0.30
        # total = 7.0 + 0.30 + 0.30 = 7.60
        assert result == 7.6

    def test_sleep_need_low_strain(self):
        """Test that strain below 10 doesn't reduce sleep need."""
        result = calculate_sleep_need(
            base_sleep_need=7.5,
            yesterday_strain=5,  # Below threshold
            sleep_debt=0
        )
        assert result == 7.5  # No negative adjustment


class TestCalculateSleepDebt:
    """Tests for sleep debt calculation."""

    def test_no_debt_when_exceeding_need(self):
        """Test no debt when actual exceeds needed."""
        actual = [8.0, 8.5, 7.5]
        needed = [7.0, 7.0, 7.0]
        result = calculate_sleep_debt(actual, needed)
        assert result == 0.0

    def test_accumulates_debt(self):
        """Test debt accumulates when sleeping less than needed."""
        actual = [6.0, 6.0, 6.0]
        needed = [7.0, 7.0, 7.0]
        result = calculate_sleep_debt(actual, needed)
        assert result == 3.0  # 1h short each day * 3 days

    def test_mixed_nights(self):
        """Test debt calculation with mixed nights."""
        actual = [6.0, 8.0, 5.0]
        needed = [7.0, 7.0, 7.0]
        result = calculate_sleep_debt(actual, needed)
        # Night 1: 1h debt, Night 2: 0 debt, Night 3: 2h debt
        assert result == 3.0

    def test_empty_lists(self):
        """Test empty lists return zero."""
        result = calculate_sleep_debt([], [])
        assert result == 0.0


class TestCalculateSleepDebtSimple:
    """Tests for simple sleep debt calculation."""

    def test_no_debt_at_baseline(self):
        """Test no debt when sleeping at baseline."""
        actual = [7.5, 7.5, 7.5]
        result = calculate_sleep_debt_simple(actual, baseline_sleep=7.5, days=3)
        assert result == 0.0

    def test_debt_below_baseline(self):
        """Test debt when sleeping below baseline."""
        actual = [6.5, 6.0, 6.5]  # 1h, 1.5h, 1h short
        result = calculate_sleep_debt_simple(actual, baseline_sleep=7.5, days=3)
        assert result == 3.5

    def test_respects_days_limit(self):
        """Test that only specified days are counted."""
        actual = [6.5, 6.5, 6.5, 6.5, 6.5]  # 5 days, each 1h short
        result = calculate_sleep_debt_simple(actual, baseline_sleep=7.5, days=3)
        assert result == 3.0  # Only 3 days counted

    def test_handles_none_values(self):
        """Test that None values are skipped."""
        actual = [6.5, None, 6.5]
        result = calculate_sleep_debt_simple(actual, baseline_sleep=7.5, days=3)
        assert result == 2.0  # Only 2 valid days counted


class TestGetSleepDebtInfo:
    """Tests for sleep debt info generation."""

    def test_no_debt(self):
        """Test info when no sleep debt."""
        result = get_sleep_debt_info(sleep_debt=0, baseline_sleep=7.5)
        assert result.accumulated_debt == 0
        assert result.nightly_repayment == 0
        assert result.days_to_clear == 0

    def test_moderate_debt(self):
        """Test info with moderate debt."""
        result = get_sleep_debt_info(sleep_debt=3.5, baseline_sleep=7.5)
        assert result.accumulated_debt == 3.5
        assert result.nightly_repayment == 0.5  # 3.5 / 7
        assert result.days_to_clear == 7

    def test_high_debt_capped_repayment(self):
        """Test that nightly repayment is capped at 1 hour."""
        result = get_sleep_debt_info(sleep_debt=10.0, baseline_sleep=7.5)
        assert result.accumulated_debt == 10.0
        assert result.nightly_repayment == 1.0  # Capped at 1 hour
        assert result.days_to_clear == 10


class TestGenerateDailyInsight:
    """Tests for daily insight generation."""

    def test_go_decision_green_zone(self):
        """Test GO decision in green zone."""
        result = generate_daily_insight(
            recovery=75,
            hrv_direction='up',
            sleep_hours=7.5,
            sleep_baseline=7.5,
            strain_yesterday=10,
        )
        assert result.decision == "GO"
        assert result.headline == "Push hard today"
        assert result.strain_target == (14.0, 21.0)

    def test_moderate_decision_yellow_zone(self):
        """Test MODERATE decision in yellow zone."""
        result = generate_daily_insight(
            recovery=50,
            hrv_direction='stable',
            sleep_hours=7.0,
            sleep_baseline=7.5,
            strain_yesterday=12,
        )
        assert result.decision == "MODERATE"
        assert result.headline == "Moderate effort today"
        assert result.strain_target == (8.0, 14.0)

    def test_recover_decision_red_zone(self):
        """Test RECOVER decision in red zone."""
        result = generate_daily_insight(
            recovery=25,
            hrv_direction='down',
            sleep_hours=5.0,
            sleep_baseline=7.5,
            strain_yesterday=8,
        )
        assert result.decision == "RECOVER"
        assert result.headline == "Recovery focus"
        assert result.strain_target == (0.0, 8.0)

    def test_insight_includes_sleep_target(self):
        """Test that insight includes calculated sleep target."""
        result = generate_daily_insight(
            recovery=60,
            hrv_direction='stable',
            sleep_hours=6.5,
            sleep_baseline=7.5,
            strain_yesterday=15,
        )
        # sleep_debt = 7.5 - 6.5 = 1.0
        # strain_adjustment = (15 - 10) * 0.05 = 0.25
        # debt_repayment = 1.0 / 7 = 0.14
        # sleep_target = 7.5 + 0.25 + 0.14 = 7.89
        assert result.sleep_target > 7.5

    def test_explanation_mentions_recovery(self):
        """Test that explanation includes recovery percentage."""
        result = generate_daily_insight(
            recovery=80,
            hrv_direction='up',
            sleep_hours=8.0,
            sleep_baseline=7.5,
            strain_yesterday=10,
        )
        assert "80%" in result.explanation

    def test_to_dict_serialization(self):
        """Test that DailyInsight can be serialized to dict."""
        result = generate_daily_insight(
            recovery=70,
            hrv_direction='up',
            sleep_hours=7.5,
            sleep_baseline=7.5,
            strain_yesterday=10,
        )
        d = result.to_dict()
        assert 'decision' in d
        assert 'headline' in d
        assert 'explanation' in d
        assert 'strain_target' in d
        assert 'sleep_target' in d
        assert isinstance(d['strain_target'], list)


class TestGetSleepTargetBreakdown:
    """Tests for sleep target breakdown."""

    def test_breakdown_components(self):
        """Test that breakdown includes all components."""
        result = get_sleep_target_breakdown(
            sleep_baseline=7.5,
            strain_yesterday=15,
            sleep_debt=2.0
        )
        assert 'baseline' in result
        assert 'strain_adjustment' in result
        assert 'strain_adjustment_minutes' in result
        assert 'debt_repayment' in result
        assert 'debt_repayment_minutes' in result
        assert 'total' in result
        assert 'total_formatted' in result

    def test_breakdown_values(self):
        """Test breakdown calculation values."""
        result = get_sleep_target_breakdown(
            sleep_baseline=7.0,
            strain_yesterday=16,  # 6 above threshold
            sleep_debt=3.5
        )
        assert result['baseline'] == 7.0
        assert result['strain_adjustment'] == 0.3  # (16-10) * 0.05
        assert result['strain_adjustment_minutes'] == 18
        assert result['debt_repayment'] == 0.5  # 3.5 / 7
        assert result['debt_repayment_minutes'] == 30

    def test_breakdown_with_no_adjustments(self):
        """Test breakdown when no adjustments needed."""
        result = get_sleep_target_breakdown(
            sleep_baseline=7.5,
            strain_yesterday=8,  # Below threshold
            sleep_debt=0
        )
        assert result['strain_adjustment'] == 0
        assert result['debt_repayment'] == 0
        assert result['total'] == 7.5


class TestFormatHoursMinutes:
    """Tests for hours/minutes formatting."""

    def test_whole_hours(self):
        """Test formatting whole hours."""
        assert format_hours_minutes(7.0) == "7h 00m"
        assert format_hours_minutes(8.0) == "8h 00m"

    def test_half_hours(self):
        """Test formatting half hours."""
        assert format_hours_minutes(7.5) == "7h 30m"

    def test_quarter_hours(self):
        """Test formatting quarter hours."""
        assert format_hours_minutes(7.25) == "7h 15m"
        assert format_hours_minutes(7.75) == "7h 45m"

    def test_arbitrary_minutes(self):
        """Test formatting arbitrary minutes."""
        # 7.8 hours = 7h 48m (0.8 * 60 = 48, but floating point may give 47)
        result = format_hours_minutes(7.8)
        # Allow for floating-point rounding
        assert result in ["7h 47m", "7h 48m"]


class TestDailyInsight:
    """Tests for DailyInsight dataclass."""

    def test_creation(self):
        """Test DailyInsight creation."""
        insight = DailyInsight(
            decision="GO",
            headline="Push hard today",
            explanation="Your body is ready.",
            strain_target=(14.0, 21.0),
            sleep_target=7.5
        )
        assert insight.decision == "GO"
        assert insight.strain_target == (14.0, 21.0)

    def test_to_dict(self):
        """Test DailyInsight to_dict method."""
        insight = DailyInsight(
            decision="MODERATE",
            headline="Moderate effort",
            explanation="Take it easy.",
            strain_target=(8.0, 14.0),
            sleep_target=8.0
        )
        d = insight.to_dict()
        assert d['decision'] == "MODERATE"
        assert d['strain_target'] == [8.0, 14.0]  # Converted to list
        assert d['sleep_target'] == 8.0


class TestSleepDebtInfo:
    """Tests for SleepDebtInfo dataclass."""

    def test_creation(self):
        """Test SleepDebtInfo creation."""
        info = SleepDebtInfo(
            accumulated_debt=3.5,
            nightly_repayment=0.5,
            days_to_clear=7
        )
        assert info.accumulated_debt == 3.5
        assert info.days_to_clear == 7

    def test_to_dict(self):
        """Test SleepDebtInfo to_dict method."""
        info = SleepDebtInfo(
            accumulated_debt=2.0,
            nightly_repayment=0.29,
            days_to_clear=7
        )
        d = info.to_dict()
        assert d['accumulated_debt'] == 2.0
        assert d['nightly_repayment'] == 0.29
        assert d['days_to_clear'] == 7


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_recovery_at_zone_boundaries(self):
        """Test decisions at exact zone boundaries."""
        # At 67% - should be GO
        result_67 = generate_daily_insight(67, 'stable', 7.5, 7.5, 10)
        assert result_67.decision == "GO"

        # At 66% - should be MODERATE
        result_66 = generate_daily_insight(66, 'stable', 7.5, 7.5, 10)
        assert result_66.decision == "MODERATE"

        # At 34% - should be MODERATE
        result_34 = generate_daily_insight(34, 'stable', 7.5, 7.5, 10)
        assert result_34.decision == "MODERATE"

        # At 33% - should be RECOVER
        result_33 = generate_daily_insight(33, 'stable', 7.5, 7.5, 10)
        assert result_33.decision == "RECOVER"

    def test_extreme_strain_values(self):
        """Test with extreme strain values."""
        # Very high strain
        result_high = generate_daily_insight(50, 'stable', 7.5, 7.5, 21)
        assert result_high.sleep_target > 7.5  # Should have strain adjustment

        # Very low strain
        result_low = generate_daily_insight(50, 'stable', 7.5, 7.5, 0)
        # No strain adjustment below 10
        assert result_low.sleep_target == 7.5

    def test_zero_sleep(self):
        """Test with zero sleep (edge case)."""
        result = generate_daily_insight(30, 'down', 0, 7.5, 10)
        assert result.decision == "RECOVER"
        # With 0 sleep and 7.5 baseline, debt = max(0, 7.5 - 0) = 7.5 hours
        # Sleep target = 7.5 + 0 (strain at 10) + 7.5/7 (debt repayment) = 8.57
        assert result.sleep_target > 7.5  # Should have debt repayment added
        # More precise: 7.5 + 7.5/7 = 7.5 + 1.07 = 8.57
        assert abs(result.sleep_target - 8.57) < 0.1

    def test_high_sleep_baseline(self):
        """Test with high sleep baseline."""
        result = generate_daily_insight(70, 'up', 9.0, 9.0, 10)
        assert result.decision == "GO"
        assert result.sleep_target == 9.0  # No adjustments needed
