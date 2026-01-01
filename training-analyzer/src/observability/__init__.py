"""Langfuse observability integration for the agentic AI coach.

This module provides:
- Langfuse tracing for LLM calls and agent executions
- Quality scoring for AI responses
- Token usage tracking integrated with quota system
- User feedback collection
"""

from .langfuse_config import (
    get_langfuse_callback,
    get_langfuse_client,
    langfuse_handler,
    configure_handler,
    is_langfuse_enabled,
    flush_langfuse,
    shutdown_langfuse,
    get_trace_url,
)
from .scoring import (
    record_feedback,
    score_response_quality,
    get_monthly_token_usage,
    sync_langfuse_to_quota,
    get_trace_usage_summary,
    UNNECESSARY_QUESTIONS,
)

__all__ = [
    # Langfuse configuration
    "get_langfuse_callback",
    "get_langfuse_client",
    "langfuse_handler",
    "configure_handler",
    "is_langfuse_enabled",
    "flush_langfuse",
    "shutdown_langfuse",
    "get_trace_url",
    # Scoring and feedback
    "record_feedback",
    "score_response_quality",
    "get_monthly_token_usage",
    "sync_langfuse_to_quota",
    "get_trace_usage_summary",
    "UNNECESSARY_QUESTIONS",
]
