"""Feature gating service for subscription-based feature limits.

This module manages feature access based on user subscription tiers
and tracks usage for rate limiting purposes.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import HTTPException, status


class Feature(Enum):
    """Enumeration of features that can be gated by subscription."""

    AI_ANALYSIS = "ai_analysis"
    AI_CHAT = "ai_chat"
    AI_WORKOUT = "ai_workout"
    AI_PLAN = "ai_plan"
    DATA_EXPORT = "data_export"
    PRIORITY_SYNC = "priority_sync"


@dataclass
class FeatureLimit:
    """Defines the limits for a feature."""

    monthly_limit: int | None  # None means unlimited
    daily_limit: int | None  # None means no daily limit


@dataclass
class UsageSummary:
    """Summary of a user's feature usage."""

    feature: Feature
    current_usage: int
    limit: int | None  # None means unlimited
    period: str  # "daily" or "monthly"
    reset_at: datetime
    remaining: int | None  # None means unlimited
    is_limited: bool


# Subscription tier feature limits
# None = unlimited
SUBSCRIPTION_LIMITS: dict[str, dict[Feature, FeatureLimit]] = {
    "free": {
        Feature.AI_ANALYSIS: FeatureLimit(monthly_limit=5, daily_limit=None),
        Feature.AI_CHAT: FeatureLimit(monthly_limit=None, daily_limit=10),
        Feature.AI_WORKOUT: FeatureLimit(monthly_limit=3, daily_limit=None),
        Feature.AI_PLAN: FeatureLimit(monthly_limit=1, daily_limit=None),
        Feature.DATA_EXPORT: FeatureLimit(monthly_limit=0, daily_limit=None),  # Disabled
        Feature.PRIORITY_SYNC: FeatureLimit(monthly_limit=0, daily_limit=None),  # Disabled
    },
    "pro": {
        Feature.AI_ANALYSIS: FeatureLimit(monthly_limit=None, daily_limit=None),
        Feature.AI_CHAT: FeatureLimit(monthly_limit=None, daily_limit=None),
        Feature.AI_WORKOUT: FeatureLimit(monthly_limit=None, daily_limit=None),
        Feature.AI_PLAN: FeatureLimit(monthly_limit=None, daily_limit=None),
        Feature.DATA_EXPORT: FeatureLimit(monthly_limit=None, daily_limit=None),
        Feature.PRIORITY_SYNC: FeatureLimit(monthly_limit=None, daily_limit=None),
    },
    "enterprise": {
        Feature.AI_ANALYSIS: FeatureLimit(monthly_limit=None, daily_limit=None),
        Feature.AI_CHAT: FeatureLimit(monthly_limit=None, daily_limit=None),
        Feature.AI_WORKOUT: FeatureLimit(monthly_limit=None, daily_limit=None),
        Feature.AI_PLAN: FeatureLimit(monthly_limit=None, daily_limit=None),
        Feature.DATA_EXPORT: FeatureLimit(monthly_limit=None, daily_limit=None),
        Feature.PRIORITY_SYNC: FeatureLimit(monthly_limit=None, daily_limit=None),
    },
}


class FeatureGateService:
    """Service for checking and tracking feature usage.

    In production, this would integrate with the database to track
    persistent usage. For local development, it uses in-memory storage.
    """

    def __init__(self) -> None:
        """Initialize the feature gate service with in-memory storage."""
        # In-memory storage for development
        # Structure: {user_id: {feature: {"monthly": count, "daily": count, "daily_date": date, "monthly_date": month}}}
        self._usage: dict[str, dict[str, dict[str, Any]]] = {}

    def _get_user_usage(self, user_id: str, feature: Feature) -> dict[str, Any]:
        """Get or initialize usage tracking for a user and feature."""
        if user_id not in self._usage:
            self._usage[user_id] = {}

        feature_key = feature.value

        if feature_key not in self._usage[user_id]:
            now = datetime.now(timezone.utc)
            self._usage[user_id][feature_key] = {
                "monthly": 0,
                "daily": 0,
                "daily_date": now.date(),
                "monthly_date": now.replace(day=1).date(),
            }

        # Reset counters if period has changed
        usage = self._usage[user_id][feature_key]
        now = datetime.now(timezone.utc)
        today = now.date()
        this_month = now.replace(day=1).date()

        if usage["daily_date"] != today:
            usage["daily"] = 0
            usage["daily_date"] = today

        if usage["monthly_date"] != this_month:
            usage["monthly"] = 0
            usage["monthly_date"] = this_month

        return usage

    def can_use_feature(
        self,
        user_id: str,
        feature: Feature,
        subscription_tier: str = "free",
    ) -> bool:
        """Check if a user can use a specific feature.

        Args:
            user_id: The user's unique identifier.
            feature: The feature to check access for.
            subscription_tier: The user's subscription tier.

        Returns:
            True if the user can use the feature, False otherwise.
        """
        limits = SUBSCRIPTION_LIMITS.get(subscription_tier, SUBSCRIPTION_LIMITS["free"])
        feature_limit = limits.get(feature)

        if feature_limit is None:
            return True  # No limit defined, allow access

        usage = self._get_user_usage(user_id, feature)

        # Check if feature is completely disabled (limit = 0)
        if feature_limit.monthly_limit == 0:
            return False

        # Check monthly limit
        if feature_limit.monthly_limit is not None:
            if usage["monthly"] >= feature_limit.monthly_limit:
                return False

        # Check daily limit
        if feature_limit.daily_limit is not None:
            if usage["daily"] >= feature_limit.daily_limit:
                return False

        return True

    def increment_usage(
        self,
        user_id: str,
        feature: Feature,
    ) -> None:
        """Increment the usage counter for a feature.

        Args:
            user_id: The user's unique identifier.
            feature: The feature to increment usage for.
        """
        usage = self._get_user_usage(user_id, feature)
        usage["monthly"] += 1
        usage["daily"] += 1

    def get_usage_summary(
        self,
        user_id: str,
        subscription_tier: str = "free",
    ) -> dict[str, UsageSummary]:
        """Get a summary of feature usage for a user.

        Args:
            user_id: The user's unique identifier.
            subscription_tier: The user's subscription tier.

        Returns:
            Dictionary mapping feature names to UsageSummary objects.
        """
        limits = SUBSCRIPTION_LIMITS.get(subscription_tier, SUBSCRIPTION_LIMITS["free"])
        now = datetime.now(timezone.utc)

        summaries = {}

        for feature in Feature:
            feature_limit = limits.get(feature)
            usage = self._get_user_usage(user_id, feature)

            # Determine which limit is active (daily or monthly)
            if feature_limit and feature_limit.daily_limit is not None:
                current = usage["daily"]
                limit = feature_limit.daily_limit
                period = "daily"
                # Reset at midnight UTC
                tomorrow = (now + __import__("datetime").timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                reset_at = tomorrow
            elif feature_limit and feature_limit.monthly_limit is not None:
                current = usage["monthly"]
                limit = feature_limit.monthly_limit
                period = "monthly"
                # Reset at start of next month
                if now.month == 12:
                    next_month = now.replace(year=now.year + 1, month=1, day=1)
                else:
                    next_month = now.replace(month=now.month + 1, day=1)
                reset_at = next_month.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                current = 0
                limit = None
                period = "unlimited"
                reset_at = now

            remaining = None if limit is None else max(0, limit - current)
            is_limited = limit is not None and current >= limit

            summaries[feature.value] = UsageSummary(
                feature=feature,
                current_usage=current,
                limit=limit,
                period=period,
                reset_at=reset_at,
                remaining=remaining,
                is_limited=is_limited,
            )

        return summaries

    def check_and_increment(
        self,
        user_id: str,
        feature: Feature,
        subscription_tier: str = "free",
    ) -> None:
        """Check if feature can be used and increment usage if allowed.

        This is a convenience method that combines can_use_feature and
        increment_usage, raising an HTTP 402 exception if the limit is reached.

        Args:
            user_id: The user's unique identifier.
            feature: The feature to check and increment.
            subscription_tier: The user's subscription tier.

        Raises:
            HTTPException (402): If the feature limit has been reached.
        """
        if not self.can_use_feature(user_id, feature, subscription_tier):
            limits = SUBSCRIPTION_LIMITS.get(subscription_tier, SUBSCRIPTION_LIMITS["free"])
            feature_limit = limits.get(feature)

            if feature_limit and feature_limit.monthly_limit == 0:
                detail = (
                    f"{feature.value} is not available on the {subscription_tier} tier. "
                    "Upgrade to Pro for access."
                )
            else:
                usage = self._get_user_usage(user_id, feature)
                summary = self.get_usage_summary(user_id, subscription_tier).get(feature.value)

                if summary and summary.period == "daily":
                    detail = (
                        f"Daily limit reached for {feature.value}. "
                        f"Used {usage['daily']}/{feature_limit.daily_limit if feature_limit else 'N/A'} today. "
                        f"Resets at midnight UTC or upgrade to Pro for unlimited access."
                    )
                else:
                    detail = (
                        f"Monthly limit reached for {feature.value}. "
                        f"Used {usage['monthly']}/{feature_limit.monthly_limit if feature_limit else 'N/A'} this month. "
                        "Upgrade to Pro for unlimited access."
                    )

            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=detail,
            )

        self.increment_usage(user_id, feature)

    def get_feature_availability(
        self,
        subscription_tier: str = "free",
    ) -> dict[str, dict[str, Any]]:
        """Get feature availability for a subscription tier.

        Args:
            subscription_tier: The subscription tier to check.

        Returns:
            Dictionary with feature availability information.
        """
        limits = SUBSCRIPTION_LIMITS.get(subscription_tier, SUBSCRIPTION_LIMITS["free"])

        availability = {}
        for feature in Feature:
            feature_limit = limits.get(feature)

            if feature_limit is None:
                availability[feature.value] = {
                    "available": True,
                    "unlimited": True,
                    "monthly_limit": None,
                    "daily_limit": None,
                }
            elif feature_limit.monthly_limit == 0:
                availability[feature.value] = {
                    "available": False,
                    "unlimited": False,
                    "monthly_limit": 0,
                    "daily_limit": None,
                }
            else:
                availability[feature.value] = {
                    "available": True,
                    "unlimited": feature_limit.monthly_limit is None
                    and feature_limit.daily_limit is None,
                    "monthly_limit": feature_limit.monthly_limit,
                    "daily_limit": feature_limit.daily_limit,
                }

        return availability


# Module-level singleton
_feature_gate_service: FeatureGateService | None = None


def get_feature_gate_service() -> FeatureGateService:
    """Get or create the feature gate service singleton."""
    global _feature_gate_service
    if _feature_gate_service is None:
        _feature_gate_service = FeatureGateService()
    return _feature_gate_service


# Convenience functions
def can_use_feature(
    user_id: str,
    feature: Feature,
    subscription_tier: str = "free",
) -> bool:
    """Check if a user can use a specific feature.

    Args:
        user_id: The user's unique identifier.
        feature: The feature to check access for.
        subscription_tier: The user's subscription tier.

    Returns:
        True if the user can use the feature, False otherwise.
    """
    return get_feature_gate_service().can_use_feature(user_id, feature, subscription_tier)


def increment_usage(user_id: str, feature: Feature) -> None:
    """Increment the usage counter for a feature.

    Args:
        user_id: The user's unique identifier.
        feature: The feature to increment usage for.
    """
    get_feature_gate_service().increment_usage(user_id, feature)


def get_usage_summary(
    user_id: str,
    subscription_tier: str = "free",
) -> dict[str, UsageSummary]:
    """Get a summary of feature usage for a user.

    Args:
        user_id: The user's unique identifier.
        subscription_tier: The user's subscription tier.

    Returns:
        Dictionary mapping feature names to UsageSummary objects.
    """
    return get_feature_gate_service().get_usage_summary(user_id, subscription_tier)


def check_and_increment(
    user_id: str,
    feature: Feature,
    subscription_tier: str = "free",
) -> None:
    """Check if feature can be used and increment usage if allowed.

    Args:
        user_id: The user's unique identifier.
        feature: The feature to check and increment.
        subscription_tier: The user's subscription tier.

    Raises:
        HTTPException (402): If the feature limit has been reached.
    """
    get_feature_gate_service().check_and_increment(user_id, feature, subscription_tier)
