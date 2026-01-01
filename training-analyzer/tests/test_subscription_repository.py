"""Tests for SubscriptionRepository - Subscription plans, user subscriptions, and usage limits.

This module tests:
1. Subscription plan retrieval (free, pro)
2. User subscription creation and updates
3. Usage tracking and incrementing
4. Usage limit checking (can_use_feature)
5. Usage reset functionality
6. Stripe integration fields
"""

import os
import pytest
import tempfile
import sqlite3
import uuid
from datetime import datetime, date, timedelta
from pathlib import Path

from training_analyzer.db.repositories.subscription_repository import (
    SubscriptionRepository,
    SubscriptionPlan,
    UserSubscription,
    UserUsage,
    get_subscription_repository,
)


@pytest.fixture
def temp_db_path():
    """Create a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def sub_repo(temp_db_path):
    """Create a SubscriptionRepository with a temporary database."""
    return SubscriptionRepository(db_path=temp_db_path)


@pytest.fixture
def sample_subscription(sub_repo):
    """Create a sample user subscription."""
    return sub_repo.create_subscription(
        subscription_id=str(uuid.uuid4()),
        user_id="test-user-123",
        plan_id="free",
        status="active",
    )


class TestSubscriptionRepositoryInit:
    """Tests for repository initialization."""

    def test_creates_subscription_plans_table(self, sub_repo):
        """subscription_plans table should be created on init."""
        with sub_repo._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='subscription_plans'"
            )
            result = cursor.fetchone()
            assert result is not None

    def test_creates_user_subscriptions_table(self, sub_repo):
        """user_subscriptions table should be created on init."""
        with sub_repo._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='user_subscriptions'"
            )
            result = cursor.fetchone()
            assert result is not None

    def test_creates_user_usage_table(self, sub_repo):
        """user_usage table should be created on init."""
        with sub_repo._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='user_usage'"
            )
            result = cursor.fetchone()
            assert result is not None

    def test_creates_default_plans(self, sub_repo):
        """Default free and pro plans should be created."""
        free_plan = sub_repo.get_plan("free")
        pro_plan = sub_repo.get_plan("pro")

        assert free_plan is not None
        assert free_plan.name == "Free"
        assert free_plan.price_cents == 0

        assert pro_plan is not None
        assert pro_plan.name == "Pro"
        assert pro_plan.price_cents == 999


class TestSubscriptionPlans:
    """Tests for subscription plan operations."""

    def test_get_free_plan(self, sub_repo):
        """Should retrieve free plan with limits."""
        plan = sub_repo.get_plan("free")

        assert plan is not None
        assert plan.id == "free"
        assert plan.name == "Free"
        assert plan.price_cents == 0
        assert plan.ai_analyses_per_month == 5
        assert plan.ai_plans_limit == 1
        assert plan.ai_chat_messages_per_day == 10
        assert plan.ai_workouts_per_month == 3
        assert plan.history_days == 180

    def test_get_pro_plan(self, sub_repo):
        """Should retrieve pro plan with unlimited features."""
        plan = sub_repo.get_plan("pro")

        assert plan is not None
        assert plan.id == "pro"
        assert plan.name == "Pro"
        assert plan.price_cents == 999
        # Pro should have None (unlimited) for most limits
        assert plan.ai_analyses_per_month is None
        assert plan.ai_plans_limit is None
        assert plan.ai_chat_messages_per_day is None
        assert plan.ai_workouts_per_month is None
        assert plan.history_days is None

    def test_get_nonexistent_plan(self, sub_repo):
        """Should return None for non-existent plan."""
        plan = sub_repo.get_plan("enterprise")
        assert plan is None

    def test_get_all_plans(self, sub_repo):
        """Should return all active plans ordered by price."""
        plans = sub_repo.get_all_plans()

        assert len(plans) >= 2
        # Free should come first (lowest price)
        assert plans[0].id == "free"
        assert plans[1].id == "pro"

    def test_get_all_plans_active_only(self, sub_repo):
        """Should only return active plans by default."""
        plans = sub_repo.get_all_plans(active_only=True)
        for plan in plans:
            assert plan.is_active is True


class TestUserSubscriptions:
    """Tests for user subscription management."""

    def test_create_subscription_minimal(self, sub_repo):
        """Should create subscription with minimal fields."""
        subscription = sub_repo.create_subscription(
            subscription_id="sub-001",
            user_id="user-001",
        )

        assert subscription.id == "sub-001"
        assert subscription.user_id == "user-001"
        assert subscription.plan_id == "free"
        assert subscription.status == "active"
        assert subscription.stripe_customer_id is None
        assert subscription.stripe_subscription_id is None

    def test_create_subscription_with_stripe(self, sub_repo):
        """Should create subscription with Stripe integration."""
        now = datetime.now()
        period_end = now + timedelta(days=30)

        subscription = sub_repo.create_subscription(
            subscription_id="sub-002",
            user_id="user-002",
            plan_id="pro",
            status="active",
            stripe_customer_id="cus_abc123",
            stripe_subscription_id="sub_xyz789",
            current_period_start=now,
            current_period_end=period_end,
        )

        assert subscription.plan_id == "pro"
        assert subscription.stripe_customer_id == "cus_abc123"
        assert subscription.stripe_subscription_id == "sub_xyz789"
        assert subscription.current_period_start is not None
        assert subscription.current_period_end is not None

    def test_create_subscription_with_trial(self, sub_repo):
        """Should create subscription with trial period."""
        trial_end = datetime.now() + timedelta(days=14)

        subscription = sub_repo.create_subscription(
            subscription_id="sub-003",
            user_id="user-003",
            plan_id="pro",
            status="trialing",
            trial_end=trial_end,
        )

        assert subscription.status == "trialing"
        assert subscription.trial_end is not None

    def test_get_user_subscription(self, sub_repo, sample_subscription):
        """Should retrieve user subscription."""
        subscription = sub_repo.get_user_subscription(sample_subscription.user_id)

        assert subscription is not None
        assert subscription.user_id == sample_subscription.user_id
        assert subscription.plan_id == sample_subscription.plan_id

    def test_get_user_subscription_not_found(self, sub_repo):
        """Should return None for user without subscription."""
        subscription = sub_repo.get_user_subscription("nonexistent-user")
        assert subscription is None

    def test_update_subscription_plan(self, sub_repo, sample_subscription):
        """Should update subscription plan (upgrade/downgrade)."""
        updated = sub_repo.update_subscription(
            sample_subscription.user_id,
            plan_id="pro",
        )

        assert updated is not None
        assert updated.plan_id == "pro"

    def test_update_subscription_status(self, sub_repo, sample_subscription):
        """Should update subscription status."""
        # Cancel subscription
        updated = sub_repo.update_subscription(
            sample_subscription.user_id,
            status="canceled",
        )

        assert updated is not None
        assert updated.status == "canceled"

    def test_update_subscription_cancel_at_period_end(self, sub_repo, sample_subscription):
        """Should set cancellation at period end."""
        updated = sub_repo.update_subscription(
            sample_subscription.user_id,
            cancel_at_period_end=True,
        )

        assert updated is not None
        assert updated.cancel_at_period_end is True

    def test_update_subscription_stripe_ids(self, sub_repo, sample_subscription):
        """Should update Stripe IDs."""
        updated = sub_repo.update_subscription(
            sample_subscription.user_id,
            stripe_customer_id="cus_new123",
            stripe_subscription_id="sub_new456",
        )

        assert updated is not None
        assert updated.stripe_customer_id == "cus_new123"
        assert updated.stripe_subscription_id == "sub_new456"

    def test_update_subscription_nonexistent(self, sub_repo):
        """Should return None for non-existent subscription."""
        result = sub_repo.update_subscription(
            "nonexistent-user",
            plan_id="pro",
        )
        assert result is None

    def test_update_subscription_no_fields(self, sub_repo, sample_subscription):
        """Should return existing subscription when no fields updated."""
        result = sub_repo.update_subscription(sample_subscription.user_id)
        assert result is not None
        assert result.user_id == sample_subscription.user_id


class TestUsageTracking:
    """Tests for usage tracking and limits."""

    def test_get_user_usage_current_period(self, sub_repo, sample_subscription):
        """Should get usage for current billing period."""
        # Increment some usage first
        sub_repo.increment_usage(sample_subscription.user_id, "ai_analyses", 1)

        usage = sub_repo.get_user_usage(sample_subscription.user_id)

        assert usage is not None
        assert usage.user_id == sample_subscription.user_id
        assert usage.ai_analyses_used == 1
        assert usage.period_start == date.today().replace(day=1)

    def test_get_user_usage_no_record(self, sub_repo):
        """Should return None when no usage record exists."""
        usage = sub_repo.get_user_usage("no-usage-user")
        assert usage is None

    def test_increment_usage_ai_analyses(self, sub_repo, sample_subscription):
        """Should increment AI analyses usage."""
        usage = sub_repo.increment_usage(
            sample_subscription.user_id,
            "ai_analyses",
            amount=2,
            tokens=1000,
            cost_cents=5,
        )

        assert usage is not None
        assert usage.ai_analyses_used == 2
        assert usage.ai_tokens_used == 1000
        assert usage.ai_cost_cents == 5

    def test_increment_usage_ai_chat_messages(self, sub_repo, sample_subscription):
        """Should increment AI chat messages usage."""
        usage = sub_repo.increment_usage(
            sample_subscription.user_id,
            "ai_chat_messages",
            amount=5,
        )

        assert usage is not None
        assert usage.ai_chat_messages_used == 5

    def test_increment_usage_ai_workouts(self, sub_repo, sample_subscription):
        """Should increment AI workouts usage."""
        usage = sub_repo.increment_usage(
            sample_subscription.user_id,
            "ai_workouts",
            amount=1,
        )

        assert usage is not None
        assert usage.ai_workouts_generated == 1

    def test_increment_usage_cumulative(self, sub_repo, sample_subscription):
        """Usage should accumulate across multiple increments."""
        sub_repo.increment_usage(sample_subscription.user_id, "ai_analyses", 2)
        sub_repo.increment_usage(sample_subscription.user_id, "ai_analyses", 3)

        usage = sub_repo.get_user_usage(sample_subscription.user_id)
        assert usage.ai_analyses_used == 5

    def test_increment_usage_invalid_feature(self, sub_repo, sample_subscription):
        """Should raise error for invalid feature name."""
        with pytest.raises(ValueError, match="Unknown feature"):
            sub_repo.increment_usage(
                sample_subscription.user_id,
                "invalid_feature",
            )

    def test_increment_usage_creates_record(self, sub_repo):
        """Should create usage record if it doesn't exist."""
        user_id = "new-user-no-usage"

        # Create subscription first
        sub_repo.create_subscription(
            subscription_id="sub-new",
            user_id=user_id,
        )

        usage = sub_repo.increment_usage(user_id, "ai_analyses", 1)

        assert usage is not None
        assert usage.user_id == user_id
        assert usage.ai_analyses_used == 1


class TestUsageLimitChecking:
    """Tests for can_use_feature limit checking."""

    def test_can_use_feature_under_limit(self, sub_repo, sample_subscription):
        """Should return True when under limit."""
        # Free plan has 5 ai_analyses per month
        sub_repo.increment_usage(sample_subscription.user_id, "ai_analyses", 3)

        result = sub_repo.can_use_feature(sample_subscription.user_id, "ai_analyses")
        assert result is True

    def test_can_use_feature_at_limit(self, sub_repo, sample_subscription):
        """Should return False when at limit."""
        # Free plan has 5 ai_analyses per month
        sub_repo.increment_usage(sample_subscription.user_id, "ai_analyses", 5)

        result = sub_repo.can_use_feature(sample_subscription.user_id, "ai_analyses")
        assert result is False

    def test_can_use_feature_over_limit(self, sub_repo, sample_subscription):
        """Should return False when over limit."""
        # Free plan has 5 ai_analyses per month
        sub_repo.increment_usage(sample_subscription.user_id, "ai_analyses", 10)

        result = sub_repo.can_use_feature(sample_subscription.user_id, "ai_analyses")
        assert result is False

    def test_can_use_feature_no_usage_record(self, sub_repo, sample_subscription):
        """Should return True when no usage record exists."""
        result = sub_repo.can_use_feature(sample_subscription.user_id, "ai_analyses")
        assert result is True

    def test_can_use_feature_pro_unlimited(self, sub_repo):
        """Pro users should have unlimited access."""
        user_id = "pro-user"
        sub_repo.create_subscription(
            subscription_id="sub-pro",
            user_id=user_id,
            plan_id="pro",
        )

        # Even with high usage, should still be allowed
        sub_repo.increment_usage(user_id, "ai_analyses", 1000)

        result = sub_repo.can_use_feature(user_id, "ai_analyses")
        assert result is True

    def test_can_use_feature_no_subscription(self, sub_repo):
        """User without subscription should use free tier limits."""
        # Don't create subscription - should default to free
        result = sub_repo.can_use_feature("no-subscription-user", "ai_analyses")
        assert result is True  # No usage yet, so allowed


class TestUsageReset:
    """Tests for usage reset functionality."""

    def test_reset_usage(self, sub_repo, sample_subscription):
        """Should reset all usage counters."""
        # Add some usage
        sub_repo.increment_usage(sample_subscription.user_id, "ai_analyses", 5)
        sub_repo.increment_usage(sample_subscription.user_id, "ai_chat_messages", 10)
        sub_repo.increment_usage(
            sample_subscription.user_id,
            "ai_workouts",
            amount=3,
            tokens=5000,
            cost_cents=100,
        )

        # Reset
        result = sub_repo.reset_usage(sample_subscription.user_id)
        assert result is True

        # Verify reset
        usage = sub_repo.get_user_usage(sample_subscription.user_id)
        assert usage.ai_analyses_used == 0
        assert usage.ai_chat_messages_used == 0
        assert usage.ai_workouts_generated == 0
        assert usage.ai_tokens_used == 0
        assert usage.ai_cost_cents == 0

    def test_reset_usage_no_record(self, sub_repo):
        """Should return False when no usage record exists."""
        result = sub_repo.reset_usage("no-usage-user")
        assert result is False


class TestSubscriptionDataclasses:
    """Tests for subscription-related dataclasses."""

    def test_subscription_plan_defaults(self):
        """SubscriptionPlan should have sensible defaults."""
        plan = SubscriptionPlan(id="test", name="Test")

        assert plan.description is None
        assert plan.price_cents == 0
        assert plan.billing_period == "month"
        assert plan.stripe_price_id is None
        assert plan.is_active is True

    def test_user_subscription_defaults(self):
        """UserSubscription should have sensible defaults."""
        subscription = UserSubscription(
            id="sub-test",
            user_id="user-test",
            plan_id="free",
        )

        assert subscription.status == "active"
        assert subscription.stripe_customer_id is None
        assert subscription.stripe_subscription_id is None
        assert subscription.cancel_at_period_end is False
        assert subscription.trial_end is None

    def test_user_usage_defaults(self):
        """UserUsage should have sensible defaults."""
        today = date.today()
        usage = UserUsage(
            id="usage-test",
            user_id="user-test",
            period_start=today,
            period_end=today + timedelta(days=30),
        )

        assert usage.ai_analyses_used == 0
        assert usage.ai_chat_messages_used == 0
        assert usage.ai_workouts_generated == 0
        assert usage.ai_tokens_used == 0
        assert usage.ai_cost_cents == 0


class TestSingletonPattern:
    """Tests for singleton repository pattern."""

    def test_get_subscription_repository_returns_singleton(self, monkeypatch):
        """get_subscription_repository should return same instance."""
        from training_analyzer.db.repositories import subscription_repository
        monkeypatch.setattr(subscription_repository, "_subscription_repository", None)

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_path = f.name

        try:
            monkeypatch.setenv("TRAINING_DB_PATH", temp_path)

            repo1 = get_subscription_repository()
            repo2 = get_subscription_repository()

            assert repo1 is repo2
        finally:
            monkeypatch.setattr(subscription_repository, "_subscription_repository", None)
            try:
                os.unlink(temp_path)
            except OSError:
                pass
