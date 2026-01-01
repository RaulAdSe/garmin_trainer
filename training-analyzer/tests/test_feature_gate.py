"""Tests for FeatureGateService - Feature access based on subscription tier.

This module tests:
1. Feature access checking (can_use_feature)
2. Usage tracking and incrementing
3. Limit enforcement (daily and monthly)
4. Usage summary generation
5. Feature availability by tier
6. Check and increment pattern (with HTTP exception)
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from fastapi import HTTPException

from training_analyzer.services.feature_gate import (
    FeatureGateService,
    Feature,
    FeatureLimit,
    UsageSummary,
    SUBSCRIPTION_LIMITS,
    get_feature_gate_service,
    can_use_feature,
    increment_usage,
    get_usage_summary,
    check_and_increment,
)


@pytest.fixture
def feature_gate():
    """Create a fresh FeatureGateService instance."""
    return FeatureGateService()


class TestFeatureEnum:
    """Tests for Feature enumeration."""

    def test_all_features_defined(self):
        """All expected features should be defined."""
        assert Feature.AI_ANALYSIS.value == "ai_analysis"
        assert Feature.AI_CHAT.value == "ai_chat"
        assert Feature.AI_WORKOUT.value == "ai_workout"
        assert Feature.AI_PLAN.value == "ai_plan"
        assert Feature.DATA_EXPORT.value == "data_export"
        assert Feature.PRIORITY_SYNC.value == "priority_sync"


class TestSubscriptionLimits:
    """Tests for subscription tier limits."""

    def test_free_tier_limits(self):
        """Free tier should have defined limits."""
        free_limits = SUBSCRIPTION_LIMITS["free"]

        assert Feature.AI_ANALYSIS in free_limits
        assert free_limits[Feature.AI_ANALYSIS].monthly_limit == 5
        assert free_limits[Feature.AI_CHAT].daily_limit == 10
        assert free_limits[Feature.AI_WORKOUT].monthly_limit == 3
        assert free_limits[Feature.AI_PLAN].monthly_limit == 1

    def test_free_tier_disabled_features(self):
        """Free tier should have disabled features."""
        free_limits = SUBSCRIPTION_LIMITS["free"]

        # DATA_EXPORT and PRIORITY_SYNC disabled (limit = 0)
        assert free_limits[Feature.DATA_EXPORT].monthly_limit == 0
        assert free_limits[Feature.PRIORITY_SYNC].monthly_limit == 0

    def test_pro_tier_unlimited(self):
        """Pro tier should have unlimited access."""
        pro_limits = SUBSCRIPTION_LIMITS["pro"]

        for feature in Feature:
            feature_limit = pro_limits[feature]
            assert feature_limit.monthly_limit is None
            assert feature_limit.daily_limit is None

    def test_enterprise_tier_unlimited(self):
        """Enterprise tier should have unlimited access."""
        enterprise_limits = SUBSCRIPTION_LIMITS["enterprise"]

        for feature in Feature:
            feature_limit = enterprise_limits[feature]
            assert feature_limit.monthly_limit is None
            assert feature_limit.daily_limit is None


class TestCanUseFeature:
    """Tests for feature access checking."""

    def test_can_use_no_usage(self, feature_gate):
        """Should allow feature when no usage recorded."""
        result = feature_gate.can_use_feature(
            "new-user",
            Feature.AI_ANALYSIS,
            "free",
        )
        assert result is True

    def test_can_use_under_monthly_limit(self, feature_gate):
        """Should allow feature when under monthly limit."""
        # Use 3 of 5 allowed
        for _ in range(3):
            feature_gate.increment_usage("test-user", Feature.AI_ANALYSIS)

        result = feature_gate.can_use_feature(
            "test-user",
            Feature.AI_ANALYSIS,
            "free",
        )
        assert result is True

    def test_cannot_use_at_monthly_limit(self, feature_gate):
        """Should deny feature when at monthly limit."""
        # Use all 5 allowed
        for _ in range(5):
            feature_gate.increment_usage("test-user", Feature.AI_ANALYSIS)

        result = feature_gate.can_use_feature(
            "test-user",
            Feature.AI_ANALYSIS,
            "free",
        )
        assert result is False

    def test_cannot_use_over_monthly_limit(self, feature_gate):
        """Should deny feature when over monthly limit."""
        # Use more than allowed (simulating bypass)
        for _ in range(10):
            feature_gate.increment_usage("test-user", Feature.AI_ANALYSIS)

        result = feature_gate.can_use_feature(
            "test-user",
            Feature.AI_ANALYSIS,
            "free",
        )
        assert result is False

    def test_can_use_under_daily_limit(self, feature_gate):
        """Should allow feature when under daily limit."""
        # Use 5 of 10 daily chat messages
        for _ in range(5):
            feature_gate.increment_usage("test-user", Feature.AI_CHAT)

        result = feature_gate.can_use_feature(
            "test-user",
            Feature.AI_CHAT,
            "free",
        )
        assert result is True

    def test_cannot_use_at_daily_limit(self, feature_gate):
        """Should deny feature when at daily limit."""
        # Use all 10 daily chat messages
        for _ in range(10):
            feature_gate.increment_usage("test-user", Feature.AI_CHAT)

        result = feature_gate.can_use_feature(
            "test-user",
            Feature.AI_CHAT,
            "free",
        )
        assert result is False

    def test_cannot_use_disabled_feature(self, feature_gate):
        """Should deny disabled features (limit = 0)."""
        result = feature_gate.can_use_feature(
            "test-user",
            Feature.DATA_EXPORT,
            "free",
        )
        assert result is False

    def test_can_use_unlimited_pro(self, feature_gate):
        """Pro users should have unlimited access."""
        # Add lots of usage
        for _ in range(100):
            feature_gate.increment_usage("pro-user", Feature.AI_ANALYSIS)

        result = feature_gate.can_use_feature(
            "pro-user",
            Feature.AI_ANALYSIS,
            "pro",
        )
        assert result is True

    def test_can_use_enabled_feature_pro(self, feature_gate):
        """Pro users should access features disabled for free tier."""
        result = feature_gate.can_use_feature(
            "pro-user",
            Feature.DATA_EXPORT,
            "pro",
        )
        assert result is True

    def test_unknown_tier_uses_free(self, feature_gate):
        """Unknown subscription tier should use free limits."""
        # Use up free tier limit
        for _ in range(5):
            feature_gate.increment_usage("test-user", Feature.AI_ANALYSIS)

        result = feature_gate.can_use_feature(
            "test-user",
            Feature.AI_ANALYSIS,
            "unknown_tier",
        )
        assert result is False


class TestUsageIncrement:
    """Tests for usage tracking and incrementing."""

    def test_increment_creates_usage(self, feature_gate):
        """increment_usage should create usage record."""
        feature_gate.increment_usage("new-user", Feature.AI_ANALYSIS)

        # Check internal state
        usage = feature_gate._usage["new-user"][Feature.AI_ANALYSIS.value]
        assert usage["monthly"] == 1
        assert usage["daily"] == 1

    def test_increment_cumulative(self, feature_gate):
        """increment_usage should accumulate."""
        for _ in range(5):
            feature_gate.increment_usage("test-user", Feature.AI_ANALYSIS)

        usage = feature_gate._usage["test-user"][Feature.AI_ANALYSIS.value]
        assert usage["monthly"] == 5
        assert usage["daily"] == 5

    def test_increment_multiple_features(self, feature_gate):
        """Should track different features separately."""
        feature_gate.increment_usage("test-user", Feature.AI_ANALYSIS)
        feature_gate.increment_usage("test-user", Feature.AI_CHAT)
        feature_gate.increment_usage("test-user", Feature.AI_CHAT)

        assert feature_gate._usage["test-user"][Feature.AI_ANALYSIS.value]["monthly"] == 1
        assert feature_gate._usage["test-user"][Feature.AI_CHAT.value]["monthly"] == 2

    def test_increment_multiple_users(self, feature_gate):
        """Should track different users separately."""
        feature_gate.increment_usage("user-1", Feature.AI_ANALYSIS)
        feature_gate.increment_usage("user-2", Feature.AI_ANALYSIS)
        feature_gate.increment_usage("user-2", Feature.AI_ANALYSIS)

        assert feature_gate._usage["user-1"][Feature.AI_ANALYSIS.value]["monthly"] == 1
        assert feature_gate._usage["user-2"][Feature.AI_ANALYSIS.value]["monthly"] == 2


class TestUsageReset:
    """Tests for usage counter reset."""

    def test_daily_counter_resets(self, feature_gate):
        """Daily counter should reset on new day."""
        # Add usage
        feature_gate.increment_usage("test-user", Feature.AI_CHAT)
        feature_gate.increment_usage("test-user", Feature.AI_CHAT)

        # Simulate day change by modifying internal state
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        feature_gate._usage["test-user"][Feature.AI_CHAT.value]["daily_date"] = yesterday

        # Get usage (triggers reset)
        usage = feature_gate._get_user_usage("test-user", Feature.AI_CHAT)

        assert usage["daily"] == 0  # Reset
        assert usage["monthly"] == 2  # Preserved

    def test_monthly_counter_resets(self, feature_gate):
        """Monthly counter should reset on new month."""
        # Add usage
        feature_gate.increment_usage("test-user", Feature.AI_ANALYSIS)
        feature_gate.increment_usage("test-user", Feature.AI_ANALYSIS)

        # Simulate month change by setting both monthly_date AND daily_date to old values
        last_month = (datetime.now(timezone.utc).replace(day=1) - timedelta(days=1)).replace(day=1).date()
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        feature_gate._usage["test-user"][Feature.AI_ANALYSIS.value]["monthly_date"] = last_month
        feature_gate._usage["test-user"][Feature.AI_ANALYSIS.value]["daily_date"] = yesterday

        # Get usage (triggers reset)
        usage = feature_gate._get_user_usage("test-user", Feature.AI_ANALYSIS)

        assert usage["monthly"] == 0  # Reset
        assert usage["daily"] == 0  # Also reset (different day)


class TestUsageSummary:
    """Tests for usage summary generation."""

    def test_get_usage_summary(self, feature_gate):
        """Should return summary for all features."""
        # Add some usage
        feature_gate.increment_usage("test-user", Feature.AI_ANALYSIS)
        feature_gate.increment_usage("test-user", Feature.AI_CHAT)

        summary = feature_gate.get_usage_summary("test-user", "free")

        assert Feature.AI_ANALYSIS.value in summary
        assert Feature.AI_CHAT.value in summary
        assert Feature.AI_WORKOUT.value in summary

    def test_usage_summary_content(self, feature_gate):
        """Summary should contain correct usage info."""
        for _ in range(3):
            feature_gate.increment_usage("test-user", Feature.AI_ANALYSIS)

        summary = feature_gate.get_usage_summary("test-user", "free")
        analysis_summary = summary[Feature.AI_ANALYSIS.value]

        assert analysis_summary.current_usage == 3
        assert analysis_summary.limit == 5
        assert analysis_summary.remaining == 2
        assert analysis_summary.is_limited is False
        assert analysis_summary.period == "monthly"

    def test_usage_summary_at_limit(self, feature_gate):
        """Summary should show when at limit."""
        for _ in range(5):
            feature_gate.increment_usage("test-user", Feature.AI_ANALYSIS)

        summary = feature_gate.get_usage_summary("test-user", "free")
        analysis_summary = summary[Feature.AI_ANALYSIS.value]

        assert analysis_summary.current_usage == 5
        assert analysis_summary.remaining == 0
        assert analysis_summary.is_limited is True

    def test_usage_summary_unlimited(self, feature_gate):
        """Summary should handle unlimited features."""
        summary = feature_gate.get_usage_summary("pro-user", "pro")
        analysis_summary = summary[Feature.AI_ANALYSIS.value]

        assert analysis_summary.limit is None
        assert analysis_summary.remaining is None
        assert analysis_summary.is_limited is False
        assert analysis_summary.period == "unlimited"


class TestCheckAndIncrement:
    """Tests for check_and_increment pattern."""

    def test_check_and_increment_success(self, feature_gate):
        """Should increment when within limits."""
        # Should not raise
        feature_gate.check_and_increment(
            "test-user",
            Feature.AI_ANALYSIS,
            "free",
        )

        usage = feature_gate._usage["test-user"][Feature.AI_ANALYSIS.value]
        assert usage["monthly"] == 1

    def test_check_and_increment_at_limit_raises(self, feature_gate):
        """Should raise HTTP 402 when at limit."""
        # Use up limit
        for _ in range(5):
            feature_gate.increment_usage("test-user", Feature.AI_ANALYSIS)

        with pytest.raises(HTTPException) as exc_info:
            feature_gate.check_and_increment(
                "test-user",
                Feature.AI_ANALYSIS,
                "free",
            )

        assert exc_info.value.status_code == 402
        assert "Monthly limit reached" in exc_info.value.detail

    def test_check_and_increment_daily_limit_raises(self, feature_gate):
        """Should raise HTTP 402 with daily limit message."""
        # Use up daily chat limit
        for _ in range(10):
            feature_gate.increment_usage("test-user", Feature.AI_CHAT)

        with pytest.raises(HTTPException) as exc_info:
            feature_gate.check_and_increment(
                "test-user",
                Feature.AI_CHAT,
                "free",
            )

        assert exc_info.value.status_code == 402
        assert "Daily limit reached" in exc_info.value.detail

    def test_check_and_increment_disabled_raises(self, feature_gate):
        """Should raise HTTP 402 for disabled features."""
        with pytest.raises(HTTPException) as exc_info:
            feature_gate.check_and_increment(
                "test-user",
                Feature.DATA_EXPORT,
                "free",
            )

        assert exc_info.value.status_code == 402
        assert "not available" in exc_info.value.detail
        assert "Upgrade to Pro" in exc_info.value.detail


class TestFeatureAvailability:
    """Tests for feature availability by tier."""

    def test_get_feature_availability_free(self, feature_gate):
        """Should return availability for free tier."""
        availability = feature_gate.get_feature_availability("free")

        assert Feature.AI_ANALYSIS.value in availability
        assert availability[Feature.AI_ANALYSIS.value]["available"] is True
        assert availability[Feature.AI_ANALYSIS.value]["unlimited"] is False
        assert availability[Feature.AI_ANALYSIS.value]["monthly_limit"] == 5

        assert availability[Feature.DATA_EXPORT.value]["available"] is False

    def test_get_feature_availability_pro(self, feature_gate):
        """Should return availability for pro tier."""
        availability = feature_gate.get_feature_availability("pro")

        for feature in Feature:
            assert availability[feature.value]["available"] is True
            assert availability[feature.value]["unlimited"] is True

    def test_get_feature_availability_unknown_tier(self, feature_gate):
        """Unknown tier should use free tier limits."""
        availability = feature_gate.get_feature_availability("unknown")

        assert availability[Feature.AI_ANALYSIS.value]["monthly_limit"] == 5
        assert availability[Feature.DATA_EXPORT.value]["available"] is False


class TestDataclasses:
    """Tests for feature gate dataclasses."""

    def test_feature_limit_defaults(self):
        """FeatureLimit should have correct defaults."""
        limit = FeatureLimit(monthly_limit=10, daily_limit=None)

        assert limit.monthly_limit == 10
        assert limit.daily_limit is None

    def test_usage_summary_structure(self):
        """UsageSummary should have all expected fields."""
        now = datetime.now(timezone.utc)
        summary = UsageSummary(
            feature=Feature.AI_ANALYSIS,
            current_usage=3,
            limit=5,
            period="monthly",
            reset_at=now,
            remaining=2,
            is_limited=False,
        )

        assert summary.feature == Feature.AI_ANALYSIS
        assert summary.current_usage == 3
        assert summary.limit == 5
        assert summary.remaining == 2
        assert summary.is_limited is False


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_get_feature_gate_service_singleton(self, monkeypatch):
        """get_feature_gate_service should return singleton."""
        from training_analyzer.services import feature_gate as fg_module
        monkeypatch.setattr(fg_module, "_feature_gate_service", None)

        service1 = get_feature_gate_service()
        service2 = get_feature_gate_service()

        assert service1 is service2

        # Cleanup
        monkeypatch.setattr(fg_module, "_feature_gate_service", None)

    def test_convenience_can_use_feature(self, monkeypatch):
        """Module-level can_use_feature should work."""
        from training_analyzer.services import feature_gate as fg_module
        monkeypatch.setattr(fg_module, "_feature_gate_service", None)

        result = can_use_feature("test-user", Feature.AI_ANALYSIS, "free")
        assert result is True

        # Cleanup
        monkeypatch.setattr(fg_module, "_feature_gate_service", None)

    def test_convenience_increment_usage(self, monkeypatch):
        """Module-level increment_usage should work."""
        from training_analyzer.services import feature_gate as fg_module
        monkeypatch.setattr(fg_module, "_feature_gate_service", None)

        increment_usage("test-user", Feature.AI_ANALYSIS)

        # Verify through service
        service = get_feature_gate_service()
        usage = service._usage["test-user"][Feature.AI_ANALYSIS.value]
        assert usage["monthly"] == 1

        # Cleanup
        monkeypatch.setattr(fg_module, "_feature_gate_service", None)

    def test_convenience_get_usage_summary(self, monkeypatch):
        """Module-level get_usage_summary should work."""
        from training_analyzer.services import feature_gate as fg_module
        monkeypatch.setattr(fg_module, "_feature_gate_service", None)

        summary = get_usage_summary("test-user", "free")
        assert Feature.AI_ANALYSIS.value in summary

        # Cleanup
        monkeypatch.setattr(fg_module, "_feature_gate_service", None)

    def test_convenience_check_and_increment(self, monkeypatch):
        """Module-level check_and_increment should work."""
        from training_analyzer.services import feature_gate as fg_module
        monkeypatch.setattr(fg_module, "_feature_gate_service", None)

        # Should not raise
        check_and_increment("test-user", Feature.AI_ANALYSIS, "free")

        # Cleanup
        monkeypatch.setattr(fg_module, "_feature_gate_service", None)
