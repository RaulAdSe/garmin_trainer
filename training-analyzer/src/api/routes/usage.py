"""
AI Usage API routes for tracking and reporting AI costs.

Provides endpoints for:
- Usage summary for current period
- Usage history by day/week/month
- Usage breakdown by analysis type
- Current limits and remaining quota
- Cost estimation before running analysis
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import get_training_db, get_current_user, CurrentUser
from ..quota import QUOTA_LIMITS, QuotaPeriod
from ..middleware.quota import get_quota_status, get_period_dates


router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Models
# ============================================================================

class UsageSummaryResponse(BaseModel):
    """Summary of AI usage for a time period."""
    period_start: str
    period_end: str
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost_cents: float
    total_cost_formatted: str
    by_analysis_type: Dict[str, int]
    by_model: Dict[str, int]


class UsageHistoryEntry(BaseModel):
    """A single entry in usage history."""
    period: str
    requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_cents: float


class UsageHistoryResponse(BaseModel):
    """Response with usage history."""
    granularity: str
    days: int
    entries: List[UsageHistoryEntry]


class UsageByTypeEntry(BaseModel):
    """Usage breakdown for a single analysis type."""
    analysis_type: str
    requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_cents: float
    avg_duration_ms: float


class UsageByTypeResponse(BaseModel):
    """Response with usage breakdown by analysis type."""
    days: int
    entries: List[UsageByTypeEntry]


class UsageLimitsResponse(BaseModel):
    """Current usage limits and remaining quota."""
    user_id: str
    daily_request_limit: int
    daily_requests_used: int
    daily_requests_remaining: int
    daily_cost_limit_cents: int
    daily_cost_used_cents: float
    daily_cost_remaining_cents: float
    monthly_cost_limit_cents: int
    monthly_cost_used_cents: float
    monthly_cost_remaining_cents: float
    is_rate_limited: bool


class CostEstimateResponse(BaseModel):
    """Cost estimate for an analysis type."""
    analysis_type: str
    model_id: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_cents: float
    estimated_cost_formatted: str


class ModelPricingEntry(BaseModel):
    """Pricing for a single model."""
    model_id: str
    input_cost_per_million: float
    output_cost_per_million: float


class ModelPricingResponse(BaseModel):
    """Response with model pricing."""
    models: List[ModelPricingEntry]


class QuotaEntry(BaseModel):
    """Quota status for a single analysis type."""
    analysis_type: str
    period: str
    limit: int  # -1 means unlimited
    used: int
    remaining: int  # -1 means unlimited
    is_exceeded: bool


class QuotaStatusResponse(BaseModel):
    """Current quota status for all AI features."""
    subscription_tier: str
    quotas: List[QuotaEntry]


# ============================================================================
# Helper Functions
# ============================================================================

def get_ai_usage_repository():
    """Get the AI usage repository."""
    from ...db.repositories.ai_usage_repository import get_ai_usage_repository as get_repo
    return get_repo()


def format_cost(cost_cents: float) -> str:
    """Format a cost in cents for display."""
    from ...services.ai_cost_calculator import format_cost_display
    return format_cost_display(cost_cents)


# ============================================================================
# API Routes
# ============================================================================

@router.get("/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    start_date: Optional[str] = Query(
        None,
        description="Start date (YYYY-MM-DD), defaults to start of current month"
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date (YYYY-MM-DD), defaults to today"
    ),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get AI usage summary for the current period.

    Returns aggregated usage data including:
    - Total requests, tokens, and cost
    - Breakdown by analysis type
    - Breakdown by model

    By default, returns data for the current month.
    """
    user_id = current_user.id

    try:
        repo = get_ai_usage_repository()

        # Parse dates
        period_start = date.fromisoformat(start_date) if start_date else None
        period_end = date.fromisoformat(end_date) if end_date else None

        summary = repo.get_usage_summary(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
        )

        return UsageSummaryResponse(
            period_start=summary.period_start.isoformat(),
            period_end=summary.period_end.isoformat(),
            total_requests=summary.total_requests,
            total_input_tokens=summary.total_input_tokens,
            total_output_tokens=summary.total_output_tokens,
            total_tokens=summary.total_input_tokens + summary.total_output_tokens,
            total_cost_cents=summary.total_cost_cents,
            total_cost_formatted=format_cost(summary.total_cost_cents),
            by_analysis_type=summary.by_analysis_type,
            by_model=summary.by_model,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid date format. Please use YYYY-MM-DD.")
    except Exception as e:
        logger.error(f"Failed to get usage summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage summary. Please try again later.")


@router.get("/history", response_model=UsageHistoryResponse)
async def get_usage_history(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of days of history to retrieve"
    ),
    granularity: str = Query(
        default="day",
        description="Time granularity: day, week, or month"
    ),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get AI usage history grouped by time period.

    Returns usage data grouped by the specified granularity (day, week, or month).
    """
    user_id = current_user.id

    if granularity not in ("day", "week", "month"):
        raise HTTPException(
            status_code=400,
            detail="Granularity must be one of: day, week, month"
        )

    try:
        repo = get_ai_usage_repository()

        history = repo.get_usage_history(
            user_id=user_id,
            days=days,
            granularity=granularity,
        )

        entries = [
            UsageHistoryEntry(
                period=entry["period"],
                requests=entry["requests"],
                input_tokens=entry["input_tokens"],
                output_tokens=entry["output_tokens"],
                total_tokens=entry["total_tokens"],
                cost_cents=entry["cost_cents"],
            )
            for entry in history
        ]

        return UsageHistoryResponse(
            granularity=granularity,
            days=days,
            entries=entries,
        )

    except Exception as e:
        logger.error(f"Failed to get usage history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage history. Please try again later.")


@router.get("/by-type", response_model=UsageByTypeResponse)
async def get_usage_by_type(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description="Number of days of history to include"
    ),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get AI usage breakdown by analysis type.

    Returns usage data grouped by analysis type (workout_analysis, chat, etc.).
    """
    user_id = current_user.id

    try:
        repo = get_ai_usage_repository()

        by_type = repo.get_usage_by_type(
            user_id=user_id,
            days=days,
        )

        entries = [
            UsageByTypeEntry(
                analysis_type=entry["analysis_type"],
                requests=entry["requests"],
                input_tokens=entry["input_tokens"],
                output_tokens=entry["output_tokens"],
                total_tokens=entry["total_tokens"],
                cost_cents=entry["cost_cents"],
                avg_duration_ms=entry["avg_duration_ms"],
            )
            for entry in by_type
        ]

        return UsageByTypeResponse(
            days=days,
            entries=entries,
        )

    except Exception as e:
        logger.error(f"Failed to get usage by type: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage by type. Please try again later.")


@router.get("/limits", response_model=UsageLimitsResponse)
async def get_usage_limits(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get current usage limits and remaining quota.

    Returns the user's usage limits and how much of the quota has been used.
    """
    user_id = current_user.id

    try:
        repo = get_ai_usage_repository()

        # Default limits - these would typically come from user subscription
        limits = repo.get_usage_limits(
            user_id=user_id,
            daily_request_limit=100,
            daily_cost_limit_cents=500,  # $5/day
            monthly_cost_limit_cents=5000,  # $50/month
        )

        return UsageLimitsResponse(
            user_id=limits.user_id,
            daily_request_limit=limits.daily_request_limit,
            daily_requests_used=limits.current_daily_requests,
            daily_requests_remaining=max(0, limits.daily_request_limit - limits.current_daily_requests),
            daily_cost_limit_cents=limits.daily_cost_limit_cents,
            daily_cost_used_cents=limits.current_daily_cost_cents,
            daily_cost_remaining_cents=max(0, limits.daily_cost_limit_cents - limits.current_daily_cost_cents),
            monthly_cost_limit_cents=limits.monthly_cost_limit_cents,
            monthly_cost_used_cents=limits.current_monthly_cost_cents,
            monthly_cost_remaining_cents=max(0, limits.monthly_cost_limit_cents - limits.current_monthly_cost_cents),
            is_rate_limited=limits.is_rate_limited,
        )

    except Exception as e:
        logger.error(f"Failed to get usage limits: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage limits. Please try again later.")


@router.get("/estimate/{analysis_type}", response_model=CostEstimateResponse)
async def get_cost_estimate(
    analysis_type: str,
    model_id: str = Query(
        default="gpt-5-mini",
        description="Model to use for estimation"
    ),
):
    """
    Get cost estimate before running an analysis.

    Returns estimated token usage and cost based on historical averages
    for the given analysis type.
    """
    from ...services.ai_cost_calculator import estimate_cost, format_cost_display

    try:
        estimate = estimate_cost(analysis_type, model_id)

        return CostEstimateResponse(
            analysis_type=analysis_type,
            model_id=estimate.model_id,
            estimated_input_tokens=estimate.input_tokens,
            estimated_output_tokens=estimate.output_tokens,
            estimated_cost_cents=estimate.total_cost_cents,
            estimated_cost_formatted=format_cost_display(estimate.total_cost_cents),
        )

    except Exception as e:
        logger.error(f"Failed to get cost estimate: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cost estimate. Please try again later.")


@router.get("/pricing", response_model=ModelPricingResponse)
async def get_model_pricing():
    """
    Get pricing information for all available models.

    Returns the cost per million tokens for input and output for each model.
    """
    from ...services.ai_cost_calculator import get_all_model_pricing

    pricing = get_all_model_pricing()

    models = [
        ModelPricingEntry(
            model_id=model_id,
            input_cost_per_million=costs["input"],
            output_cost_per_million=costs["output"],
        )
        for model_id, costs in pricing.items()
    ]

    return ModelPricingResponse(models=models)


@router.get("/recent")
async def get_recent_usage(
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Number of recent entries to return"
    ),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get recent AI usage logs.

    Returns the most recent usage log entries for debugging and monitoring.
    """
    user_id = current_user.id

    try:
        repo = get_ai_usage_repository()

        logs = repo.get_recent_logs(
            user_id=user_id,
            limit=limit,
        )

        return {
            "count": len(logs),
            "logs": [
                {
                    "request_id": log.request_id,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                    "model_id": log.model_id,
                    "analysis_type": log.analysis_type,
                    "input_tokens": log.input_tokens,
                    "output_tokens": log.output_tokens,
                    "total_cost_cents": log.total_cost_cents,
                    "duration_ms": log.duration_ms,
                    "status": log.status,
                    "entity_type": log.entity_type,
                    "entity_id": log.entity_id,
                }
                for log in logs
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get recent usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recent usage. Please try again later.")


@router.get("/quota", response_model=QuotaStatusResponse)
async def get_quota(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get current quota status for all AI features.

    Returns the user's current usage and remaining quota for each
    analysis type based on their subscription tier.

    Quotas reset:
    - Daily quotas reset at midnight UTC
    - Monthly quotas reset on the 1st of each month
    """
    tier_limits = QUOTA_LIMITS.get(current_user.subscription_tier, QUOTA_LIMITS["free"])

    quotas = []
    for analysis_type, quota_limit in tier_limits.items():
        status = get_quota_status(
            user_id=current_user.user_id,
            subscription_tier=current_user.subscription_tier,
            analysis_type=analysis_type,
        )
        quotas.append(QuotaEntry(
            analysis_type=analysis_type,
            period=status.period.value,
            limit=status.limit,
            used=status.used,
            remaining=status.remaining,
            is_exceeded=status.is_exceeded,
        ))

    return QuotaStatusResponse(
        subscription_tier=current_user.subscription_tier,
        quotas=quotas,
    )
