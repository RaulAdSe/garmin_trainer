"""LangChain tools for the agentic AI coach.

This module provides:
1. Query tools - Read-only tools for fetching training data
2. Action tools - Tools that take actions (create plans, design workouts, etc.)
3. Tool metadata - Human-friendly status messages for streaming UI
4. Retry utilities - Retry decorators and circuit breakers for handling transient failures
"""

# Query tools (read-only data access)
from .query_tools import (
    query_workouts,
    query_wellness,
    get_athlete_profile,
    get_training_patterns,
    get_fitness_metrics,
    get_garmin_data,
    compare_workouts,
)

# Tool metadata for human-friendly status messages
from .tool_metadata import (
    TOOL_STATUS_MESSAGES,
    get_tool_start_message,
    get_tool_end_message,
    ToolStatusEmitter,
    get_status_emitter,
)

# Retry utilities for handling transient failures
from .retry import (
    # Decorators
    with_retry,
    with_retry_async,
    # Configuration
    ToolRetryConfig,
    DEFAULT_RETRY_CONFIG,
    # Exception types
    RetryableError,
    NonRetryableError,
    CircuitOpenError,
    # Exception classification
    is_retryable,
    RETRYABLE_EXCEPTIONS,
    NON_RETRYABLE_EXCEPTIONS,
    # Circuit breaker
    CircuitBreaker,
    get_circuit_breaker,
    reset_all_circuit_breakers,
    # Metrics
    RetryMetrics,
    get_retry_metrics,
    get_all_retry_metrics,
    reset_retry_metrics,
    # Langfuse integration
    log_retry_metrics_to_langfuse,
)

# Convenience list for query tools
QUERY_TOOLS = [
    query_workouts,
    query_wellness,
    get_athlete_profile,
    get_training_patterns,
    get_fitness_metrics,
    get_garmin_data,
    compare_workouts,
]


def get_query_tools():
    """Get all query tools for use in LangChain agents."""
    return QUERY_TOOLS

# Action tools (create, modify, design)
from .action_tools import (
    create_training_plan,
    design_workout,
    log_note,
    set_goal,
    ACTION_TOOLS,
    get_action_tools,
)

__all__ = [
    # Query tools
    "query_workouts",
    "query_wellness",
    "get_athlete_profile",
    "get_training_patterns",
    "get_fitness_metrics",
    "get_garmin_data",
    "compare_workouts",
    "QUERY_TOOLS",
    "get_query_tools",
    # Action tools
    "create_training_plan",
    "design_workout",
    "log_note",
    "set_goal",
    "ACTION_TOOLS",
    "get_action_tools",
    # Tool metadata for streaming status
    "TOOL_STATUS_MESSAGES",
    "get_tool_start_message",
    "get_tool_end_message",
    "ToolStatusEmitter",
    "get_status_emitter",
    # Retry utilities
    "with_retry",
    "with_retry_async",
    "ToolRetryConfig",
    "DEFAULT_RETRY_CONFIG",
    "RetryableError",
    "NonRetryableError",
    "CircuitOpenError",
    "is_retryable",
    "RETRYABLE_EXCEPTIONS",
    "NON_RETRYABLE_EXCEPTIONS",
    "CircuitBreaker",
    "get_circuit_breaker",
    "reset_all_circuit_breakers",
    "RetryMetrics",
    "get_retry_metrics",
    "get_all_retry_metrics",
    "reset_retry_metrics",
    "log_retry_metrics_to_langfuse",
]
