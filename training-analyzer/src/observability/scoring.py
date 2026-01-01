"""Quality scoring and usage tracking for agentic AI responses.

Scores track:
- Whether the agent used data tools vs asking unnecessary questions
- User satisfaction ratings
- Response quality metrics

Token usage tracking:
- Syncs Langfuse trace data to local quota system
- Provides monthly usage summaries
- Bridges observability with billing
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging
import uuid

logger = logging.getLogger(__name__)


def record_feedback(
    trace_id: str,
    rating: int,
    comment: Optional[str] = None,
) -> bool:
    """Record user feedback for a conversation trace.

    Args:
        trace_id: Langfuse trace ID
        rating: Rating from 1-5
        comment: Optional feedback comment

    Returns:
        True if recorded successfully, False otherwise
    """
    try:
        from .langfuse_config import get_langfuse_client

        client = get_langfuse_client()
        if not client:
            logger.warning("Langfuse not configured, feedback not recorded")
            return False

        client.score(
            trace_id=trace_id,
            name="user_rating",
            value=rating,
            comment=comment,
        )
        return True

    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        return False


# Questions the agent should NEVER ask (it has the data)
UNNECESSARY_QUESTIONS = [
    "what's your fitness level",
    "how many days per week do you train",
    "what's your max heart rate",
    "what's your current weekly mileage",
    "do you do strength training",
    "when do you usually run long",
    "what are your hr zones",
    "what's your resting heart rate",
    "what's your threshold pace",
    "how much have you been running",
]


def score_response_quality(
    trace_id: str,
    response: str,
    tools_used: List[str],
) -> dict:
    """Score an agent response for quality.

    Checks if the agent:
    1. Used data tools instead of asking questions
    2. Provided data-driven insights
    3. Didn't ask for info that's in the database

    Args:
        trace_id: Langfuse trace ID
        response: The agent's response text
        tools_used: List of tools the agent called

    Returns:
        Dict with scores and details
    """
    scores = {
        "data_driven": 1,  # 1 = good, 0 = bad
        "tools_used_count": len(tools_used),
        "unnecessary_questions": [],
    }

    response_lower = response.lower()

    # Check for unnecessary questions
    for question in UNNECESSARY_QUESTIONS:
        if question in response_lower:
            scores["data_driven"] = 0
            scores["unnecessary_questions"].append(question)

    # Score based on tool usage
    if len(tools_used) == 0 and "?" in response:
        # Agent asked questions without using tools first
        scores["data_driven"] = 0

    # Record to Langfuse
    try:
        from .langfuse_config import get_langfuse_client

        client = get_langfuse_client()
        if client:
            client.score(
                trace_id=trace_id,
                name="data_driven",
                value=scores["data_driven"],
                comment="Agent should use tools, not ask questions" if scores["data_driven"] == 0 else None,
            )

            client.score(
                trace_id=trace_id,
                name="tools_used",
                value=scores["tools_used_count"],
            )

    except Exception as e:
        logger.error(f"Failed to record quality scores: {e}")

    return scores


def get_monthly_token_usage(user_id: str) -> dict:
    """Get total tokens used by a user this month.

    Queries Langfuse for all traces by this user in the current month.

    Args:
        user_id: The user ID to check

    Returns:
        Dict with input_tokens, output_tokens, total_tokens
    """
    from datetime import datetime

    try:
        from .langfuse_config import get_langfuse_client

        client = get_langfuse_client()
        if not client:
            return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "error": "Langfuse not configured"}

        # Get first day of current month
        today = datetime.now()
        first_of_month = datetime(today.year, today.month, 1)

        # Langfuse API to get traces
        # Note: This is a simplified version. Actual implementation may need pagination.
        traces = client.get_traces(
            user_id=user_id,
            from_timestamp=first_of_month,
            to_timestamp=today,
        )

        total_input = 0
        total_output = 0

        for trace in traces.data:
            if trace.input_tokens:
                total_input += trace.input_tokens
            if trace.output_tokens:
                total_output += trace.output_tokens

        return {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "trace_count": len(traces.data),
        }

    except Exception as e:
        logger.error(f"Failed to get token usage: {e}")
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "error": str(e)}


def sync_langfuse_to_quota(
    user_id: str,
    trace_id: str,
    analysis_type: str,
    model_id: Optional[str] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    duration_ms: Optional[int] = None,
) -> bool:
    """Sync token usage from a Langfuse trace to the local quota system.

    This bridges Langfuse observability with the existing AI usage
    tracking and quota system. Call this after completing an AI
    operation to ensure usage is recorded in both systems.

    If token counts are not provided, attempts to fetch them from
    the Langfuse trace (requires trace to be flushed first).

    Args:
        user_id: The user who made the request.
        trace_id: The Langfuse trace ID to sync.
        analysis_type: Type of analysis (e.g., 'workout_analysis', 'chat').
        model_id: Optional model ID (defaults to 'gpt-5-mini').
        input_tokens: Number of input tokens (fetched from Langfuse if not provided).
        output_tokens: Number of output tokens (fetched from Langfuse if not provided).
        entity_type: Optional entity type (e.g., 'workout').
        entity_id: Optional entity ID.
        duration_ms: Request duration in milliseconds.

    Returns:
        True if sync was successful, False otherwise.

    Example:
        >>> # After an AI operation completes with LangChain callback
        >>> from observability import sync_langfuse_to_quota
        >>> sync_langfuse_to_quota(
        ...     user_id="athlete-123",
        ...     trace_id=handler.trace_id,
        ...     analysis_type="workout_analysis",
        ...     input_tokens=1500,
        ...     output_tokens=800,
        ...     entity_type="workout",
        ...     entity_id="workout-456",
        ... )
    """
    # Use provided values or try to fetch from Langfuse
    final_input_tokens = input_tokens or 0
    final_output_tokens = output_tokens or 0

    # If tokens not provided, try to get from Langfuse
    if input_tokens is None or output_tokens is None:
        try:
            from .langfuse_config import get_langfuse_client

            client = get_langfuse_client()
            if client:
                # Flush to ensure trace is available
                client.flush()

                trace = client.get_trace(trace_id)
                if trace:
                    # Sum up usage across all generations in the trace
                    for obs in getattr(trace, 'observations', []) or []:
                        usage = getattr(obs, 'usage', None)
                        if usage:
                            if input_tokens is None:
                                final_input_tokens += usage.get('input', 0) or 0
                            if output_tokens is None:
                                final_output_tokens += usage.get('output', 0) or 0

        except Exception as e:
            logger.warning(f"Failed to fetch token usage from Langfuse: {e}")

    # Default model if not specified
    if model_id is None:
        model_id = "gpt-5-mini"

    try:
        # Import here to avoid circular dependencies
        from ..db.repositories.ai_usage_repository import get_ai_usage_repository
        from ..services.ai_cost_calculator import calculate_cost

        repo = get_ai_usage_repository()

        # Calculate cost using our pricing
        total_cost = calculate_cost(
            model_id,
            final_input_tokens,
            final_output_tokens,
        )

        # Generate a unique request ID that includes the trace ID
        request_id = f"lf-{trace_id}-{uuid.uuid4().hex[:8]}"

        # Log to our usage system
        repo.log_usage(
            request_id=request_id,
            user_id=user_id,
            model_id=model_id,
            input_tokens=final_input_tokens,
            output_tokens=final_output_tokens,
            total_cost_cents=total_cost,
            analysis_type=analysis_type,
            duration_ms=duration_ms,
            entity_type=entity_type,
            entity_id=entity_id,
            status="completed",
        )

        logger.debug(
            f"Synced trace {trace_id} to quota: "
            f"{final_input_tokens + final_output_tokens} tokens, ${total_cost/100:.4f}"
        )
        return True

    except ImportError as e:
        logger.warning(f"AI usage repository not available: {e}")
        return False
    except Exception as e:
        logger.warning(f"Failed to sync Langfuse to quota: {e}")
        return False


def get_trace_usage_summary(trace_id: str) -> Dict[str, Any]:
    """Get a summary of token usage for a specific trace.

    Args:
        trace_id: The Langfuse trace ID.

    Returns:
        Dict with usage statistics including tokens, cost, and duration.
    """
    try:
        from .langfuse_config import get_langfuse_client

        client = get_langfuse_client()
        if not client:
            return {"error": "Langfuse not configured"}

        trace = client.get_trace(trace_id)
        if not trace:
            return {"error": "Trace not found"}

        input_tokens = 0
        output_tokens = 0
        total_cost = 0.0
        duration_ms = None

        # Calculate duration from trace timestamps
        if hasattr(trace, 'start_time') and hasattr(trace, 'end_time'):
            if trace.start_time and trace.end_time:
                duration_ms = int((trace.end_time - trace.start_time).total_seconds() * 1000)

        # Sum up usage across all generations
        for obs in getattr(trace, 'observations', []) or []:
            usage = getattr(obs, 'usage', None)
            if usage:
                input_tokens += usage.get('input', 0) or 0
                output_tokens += usage.get('output', 0) or 0

            cost = getattr(obs, 'calculated_total_cost', None)
            if cost:
                total_cost += cost

        return {
            "trace_id": trace_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "total_cost_usd": total_cost,
            "total_cost_cents": total_cost * 100,
            "duration_ms": duration_ms,
            "name": getattr(trace, 'name', None),
            "user_id": getattr(trace, 'user_id', None),
            "session_id": getattr(trace, 'session_id', None),
        }

    except Exception as e:
        logger.error(f"Failed to get trace usage summary: {e}")
        return {"error": str(e)}
