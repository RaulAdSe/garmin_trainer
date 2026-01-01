"""
AI Cost Calculator for tracking and estimating LLM costs.

Provides pricing information for different models and calculates
costs based on token usage.
"""

from enum import Enum
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


# Model pricing in cents per million tokens
# Based on hypothetical GPT-5 pricing (adjust as needed)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # Fast model - gpt-5-nano
    "gpt-5-nano": {
        "input": 15.0,    # $0.15 per 1M input tokens
        "output": 60.0,   # $0.60 per 1M output tokens
    },
    # Smart model - gpt-5-mini
    "gpt-5-mini": {
        "input": 75.0,    # $0.75 per 1M input tokens
        "output": 300.0,  # $3.00 per 1M output tokens
    },
    # Premium model - gpt-4o
    "gpt-4o": {
        "input": 250.0,   # $2.50 per 1M input tokens
        "output": 1000.0, # $10.00 per 1M output tokens
    },
    # Legacy fallbacks
    "gpt-4o-mini": {
        "input": 15.0,
        "output": 60.0,
    },
    "gpt-4-turbo": {
        "input": 1000.0,
        "output": 3000.0,
    },
}

# Average token usage by analysis type (for estimation)
# Format: (avg_input_tokens, avg_output_tokens)
ANALYSIS_TYPE_AVERAGES: Dict[str, Tuple[int, int]] = {
    "workout_analysis": (2500, 1500),  # Detailed workout analysis
    "chat": (800, 500),                # Single chat message
    "plan_generation": (3000, 2000),   # Training plan creation
    "quick_summary": (500, 100),       # Quick workout summary
    "intent_classification": (200, 50), # Intent detection
    "workout_design": (1500, 1000),    # AI workout design
    "coach_response": (1000, 600),     # Coach agent response
    "trend_analysis": (2000, 1000),    # Multi-workout trend
    "race_readiness": (1500, 800),     # Race preparation assessment
}


class AnalysisType(str, Enum):
    """Types of AI analysis operations."""
    WORKOUT_ANALYSIS = "workout_analysis"
    CHAT = "chat"
    PLAN_GENERATION = "plan_generation"
    QUICK_SUMMARY = "quick_summary"
    INTENT_CLASSIFICATION = "intent_classification"
    WORKOUT_DESIGN = "workout_design"
    COACH_RESPONSE = "coach_response"
    TREND_ANALYSIS = "trend_analysis"
    RACE_READINESS = "race_readiness"


@dataclass
class CostBreakdown:
    """Breakdown of AI usage costs."""
    input_cost_cents: float
    output_cost_cents: float
    total_cost_cents: float
    input_tokens: int
    output_tokens: int
    model_id: str


def calculate_cost(
    model_id: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """
    Calculate the cost in cents for a given token usage.

    Args:
        model_id: The model identifier (e.g., 'gpt-5-mini')
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens

    Returns:
        Total cost in cents
    """
    pricing = MODEL_PRICING.get(model_id)
    if not pricing:
        # Fallback to gpt-5-mini pricing if unknown model
        pricing = MODEL_PRICING["gpt-5-mini"]

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost


def calculate_cost_breakdown(
    model_id: str,
    input_tokens: int,
    output_tokens: int,
) -> CostBreakdown:
    """
    Calculate detailed cost breakdown for token usage.

    Args:
        model_id: The model identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        CostBreakdown with detailed cost information
    """
    pricing = MODEL_PRICING.get(model_id, MODEL_PRICING["gpt-5-mini"])

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    return CostBreakdown(
        input_cost_cents=input_cost,
        output_cost_cents=output_cost,
        total_cost_cents=input_cost + output_cost,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model_id=model_id,
    )


def estimate_cost(
    analysis_type: str,
    model_id: str = "gpt-5-mini",
) -> CostBreakdown:
    """
    Estimate the cost for an analysis type based on historical averages.

    Args:
        analysis_type: Type of analysis (e.g., 'workout_analysis', 'chat')
        model_id: The model to use for estimation

    Returns:
        CostBreakdown with estimated costs
    """
    # Get average tokens for this analysis type
    averages = ANALYSIS_TYPE_AVERAGES.get(
        analysis_type,
        (1000, 500),  # Default averages
    )
    avg_input, avg_output = averages

    return calculate_cost_breakdown(model_id, avg_input, avg_output)


def get_model_pricing(model_id: str) -> Optional[Dict[str, float]]:
    """
    Get the pricing for a specific model.

    Args:
        model_id: The model identifier

    Returns:
        Pricing dict with 'input' and 'output' keys (cents per million tokens),
        or None if model not found
    """
    return MODEL_PRICING.get(model_id)


def get_all_model_pricing() -> Dict[str, Dict[str, float]]:
    """Get pricing for all known models."""
    return MODEL_PRICING.copy()


def format_cost_display(cost_cents: float) -> str:
    """
    Format a cost in cents for display.

    Args:
        cost_cents: Cost in cents

    Returns:
        Formatted string (e.g., "$0.05" or "$1.23")
    """
    dollars = cost_cents / 100
    if dollars < 0.01:
        return f"${dollars:.4f}"
    elif dollars < 1:
        return f"${dollars:.2f}"
    else:
        return f"${dollars:.2f}"


def calculate_monthly_estimate(
    daily_analyses: int = 5,
    daily_chats: int = 10,
    model_id: str = "gpt-5-mini",
) -> Dict[str, float]:
    """
    Calculate estimated monthly costs based on usage patterns.

    Args:
        daily_analyses: Average daily workout analyses
        daily_chats: Average daily chat messages
        model_id: The model to use

    Returns:
        Dict with cost estimates
    """
    analysis_cost = estimate_cost("workout_analysis", model_id)
    chat_cost = estimate_cost("chat", model_id)

    daily_cost = (
        (daily_analyses * analysis_cost.total_cost_cents) +
        (daily_chats * chat_cost.total_cost_cents)
    )

    return {
        "daily_cost_cents": daily_cost,
        "weekly_cost_cents": daily_cost * 7,
        "monthly_cost_cents": daily_cost * 30,
        "daily_analyses": daily_analyses,
        "daily_chats": daily_chats,
        "model": model_id,
    }
