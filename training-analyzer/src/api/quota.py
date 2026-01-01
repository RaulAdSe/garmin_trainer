"""AI usage quota configuration and types.

Defines quota limits per subscription tier for AI features.
Limits are enforced by the quota middleware before AI calls.

Supports both message-based quotas (workout_analysis, chat) and
token-based quotas (chat_tokens) for agentic features with variable cost.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class QuotaPeriod(str, Enum):
    """Time period for quota limits."""
    DAILY = "daily"
    MONTHLY = "monthly"


@dataclass
class QuotaLimit:
    """Limit for a specific analysis type.

    Attributes:
        limit: Maximum allowed requests. -1 means unlimited, 0 means disabled.
        period: Time period for the limit (daily or monthly).
    """
    limit: int
    period: QuotaPeriod

    @property
    def is_unlimited(self) -> bool:
        return self.limit == -1

    @property
    def is_disabled(self) -> bool:
        return self.limit == 0


@dataclass
class QuotaStatus:
    """Current quota status for a user and analysis type."""
    analysis_type: str
    period: QuotaPeriod
    limit: int
    used: int
    remaining: int
    is_exceeded: bool

    @property
    def is_unlimited(self) -> bool:
        return self.limit == -1


@dataclass
class TokenQuotaStatus:
    """Token-based quota status for agentic features.

    Used for features like agentic chat where cost varies per interaction
    based on the number of tokens consumed (including tool calls).
    """
    analysis_type: str
    period: QuotaPeriod
    token_limit: int
    tokens_used: int
    tokens_remaining: int
    is_exceeded: bool
    percent_used: float

    @property
    def is_unlimited(self) -> bool:
        return self.token_limit == -1


# Quota limits by subscription tier
# limit: -1 = unlimited, 0 = disabled, >0 = max requests per period
#
# Note: "chat" is kept for backwards compatibility with message-based quota.
# "chat_tokens" is the new token-based quota for agentic chat features.
QUOTA_LIMITS: Dict[str, Dict[str, QuotaLimit]] = {
    "free": {
        "workout_analysis": QuotaLimit(limit=5, period=QuotaPeriod.MONTHLY),
        "chat_tokens": QuotaLimit(limit=50_000, period=QuotaPeriod.MONTHLY),
        "chat": QuotaLimit(limit=10, period=QuotaPeriod.DAILY),  # Backwards compat
        "plan": QuotaLimit(limit=1, period=QuotaPeriod.MONTHLY),
    },
    "pro": {
        "workout_analysis": QuotaLimit(limit=-1, period=QuotaPeriod.MONTHLY),
        "chat_tokens": QuotaLimit(limit=-1, period=QuotaPeriod.MONTHLY),
        "chat": QuotaLimit(limit=-1, period=QuotaPeriod.DAILY),
        "plan": QuotaLimit(limit=-1, period=QuotaPeriod.MONTHLY),
    },
    "enterprise": {
        "workout_analysis": QuotaLimit(limit=-1, period=QuotaPeriod.MONTHLY),
        "chat_tokens": QuotaLimit(limit=-1, period=QuotaPeriod.MONTHLY),
        "chat": QuotaLimit(limit=-1, period=QuotaPeriod.DAILY),
        "plan": QuotaLimit(limit=-1, period=QuotaPeriod.MONTHLY),
    },
}


def get_quota_limit(subscription_tier: str, analysis_type: str) -> Optional[QuotaLimit]:
    """Get the quota limit for a subscription tier and analysis type.

    Args:
        subscription_tier: User's subscription tier (free, pro, enterprise).
        analysis_type: Type of analysis (workout_analysis, chat, chat_tokens, plan).

    Returns:
        QuotaLimit if defined, None otherwise.
    """
    tier_limits = QUOTA_LIMITS.get(subscription_tier, QUOTA_LIMITS["free"])
    return tier_limits.get(analysis_type)


def get_token_quota_status(
    subscription_tier: str,
    tokens_used: int,
) -> TokenQuotaStatus:
    """Get token quota status for the chat_tokens feature.

    This is used for agentic chat features where cost varies per interaction
    based on the number of tokens consumed (including tool calls).

    Args:
        subscription_tier: User's subscription tier (free, pro, enterprise).
        tokens_used: Total tokens used in the current period.

    Returns:
        TokenQuotaStatus with current usage and limits.
    """
    quota_limit = get_quota_limit(subscription_tier, "chat_tokens")

    # Default to free tier if not found
    if quota_limit is None:
        quota_limit = QUOTA_LIMITS["free"]["chat_tokens"]

    token_limit = quota_limit.limit
    period = quota_limit.period

    # Handle unlimited quota
    if token_limit == -1:
        return TokenQuotaStatus(
            analysis_type="chat_tokens",
            period=period,
            token_limit=token_limit,
            tokens_used=tokens_used,
            tokens_remaining=-1,  # Unlimited
            is_exceeded=False,
            percent_used=0.0,
        )

    tokens_remaining = max(0, token_limit - tokens_used)
    is_exceeded = tokens_used >= token_limit
    percent_used = (tokens_used / token_limit * 100) if token_limit > 0 else 0.0

    return TokenQuotaStatus(
        analysis_type="chat_tokens",
        period=period,
        token_limit=token_limit,
        tokens_used=tokens_used,
        tokens_remaining=tokens_remaining,
        is_exceeded=is_exceeded,
        percent_used=min(100.0, percent_used),
    )
