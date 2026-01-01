"""Quota enforcement middleware for AI endpoints.

Checks user's AI usage against their subscription tier limits
before allowing AI operations. Returns HTTP 402 when quota exceeded.
"""

from datetime import date
from typing import Tuple

from fastapi import Depends, HTTPException, status

from .auth import CurrentUser, get_current_user
from ..quota import QuotaPeriod, QuotaStatus, get_quota_limit
from ...db.repositories.ai_usage_repository import get_ai_usage_repository


class QuotaExceededError(HTTPException):
    """Raised when user has exceeded their AI usage quota."""

    def __init__(self, quota_status: QuotaStatus):
        detail = {
            "error": "quota_exceeded",
            "message": (
                f"You have reached your {quota_status.period.value} limit of "
                f"{quota_status.limit} {quota_status.analysis_type.replace('_', ' ')} requests. "
                f"Upgrade to Pro for unlimited access."
            ),
            "analysis_type": quota_status.analysis_type,
            "period": quota_status.period.value,
            "limit": quota_status.limit,
            "used": quota_status.used,
            "upgrade_url": "/settings/billing",
        }
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=detail,
        )


class FeatureDisabledError(HTTPException):
    """Raised when a feature is disabled for the user's subscription tier."""

    def __init__(self, analysis_type: str, subscription_tier: str):
        detail = {
            "error": "feature_unavailable",
            "message": (
                f"{analysis_type.replace('_', ' ').title()} is not available "
                f"on the {subscription_tier} plan. Upgrade to Pro to access this feature."
            ),
            "upgrade_url": "/settings/billing",
        }
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=detail,
        )


def get_period_dates(period: QuotaPeriod) -> Tuple[date, date]:
    """Get the start and end dates for a quota period.

    Args:
        period: The quota period (daily or monthly).

    Returns:
        Tuple of (period_start, period_end) dates.
    """
    today = date.today()

    if period == QuotaPeriod.DAILY:
        return today, today
    elif period == QuotaPeriod.MONTHLY:
        return today.replace(day=1), today
    else:
        raise ValueError(f"Unknown period: {period}")


def require_quota(analysis_type: str):
    """Create a dependency that checks quota before allowing AI operations.

    Args:
        analysis_type: The type of analysis to check ('workout_analysis', 'chat', 'plan').

    Returns:
        A FastAPI dependency function that validates quota.

    Raises:
        HTTPException (402): If quota is exceeded or feature is disabled.

    Example:
        @router.post("/analyze")
        async def analyze(
            current_user: CurrentUser = Depends(require_quota("workout_analysis")),
        ):
            # User has quota available
            ...
    """

    async def check_quota(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        """Check if user has remaining quota for the analysis type."""

        # Get the quota limit for this user's tier
        quota_limit = get_quota_limit(current_user.subscription_tier, analysis_type)

        # If no limit defined or unlimited (-1), allow the request
        if quota_limit is None or quota_limit.is_unlimited:
            return current_user

        # If limit is 0, feature is disabled for this tier
        if quota_limit.is_disabled:
            raise FeatureDisabledError(analysis_type, current_user.subscription_tier)

        # Get current usage count from database
        ai_usage_repo = get_ai_usage_repository()
        period_start, period_end = get_period_dates(quota_limit.period)

        used_count = ai_usage_repo.get_usage_count(
            user_id=current_user.user_id,
            analysis_type=analysis_type,
            period_start=period_start,
            period_end=period_end,
        )

        # Check if quota exceeded
        if used_count >= quota_limit.limit:
            quota_status = QuotaStatus(
                analysis_type=analysis_type,
                period=quota_limit.period,
                limit=quota_limit.limit,
                used=used_count,
                remaining=0,
                is_exceeded=True,
            )
            raise QuotaExceededError(quota_status)

        return current_user

    return check_quota


def get_quota_status(user_id: str, subscription_tier: str, analysis_type: str) -> QuotaStatus:
    """Get current quota status for a user and analysis type.

    Args:
        user_id: The user's ID.
        subscription_tier: The user's subscription tier.
        analysis_type: The type of analysis.

    Returns:
        QuotaStatus with current usage and limits.
    """
    quota_limit = get_quota_limit(subscription_tier, analysis_type)

    if quota_limit is None or quota_limit.is_unlimited:
        return QuotaStatus(
            analysis_type=analysis_type,
            period=QuotaPeriod.MONTHLY,
            limit=-1,
            used=0,
            remaining=-1,
            is_exceeded=False,
        )

    ai_usage_repo = get_ai_usage_repository()
    period_start, period_end = get_period_dates(quota_limit.period)

    used_count = ai_usage_repo.get_usage_count(
        user_id=user_id,
        analysis_type=analysis_type,
        period_start=period_start,
        period_end=period_end,
    )

    remaining = max(0, quota_limit.limit - used_count)

    return QuotaStatus(
        analysis_type=analysis_type,
        period=quota_limit.period,
        limit=quota_limit.limit,
        used=used_count,
        remaining=remaining,
        is_exceeded=used_count >= quota_limit.limit,
    )
