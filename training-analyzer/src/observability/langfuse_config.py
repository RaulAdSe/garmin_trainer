"""Langfuse configuration and initialization.

Langfuse v3 provides:
- Full conversation flow tracing via observe decorator
- Individual tool execution spans
- Token usage and cost tracking
- User feedback and quality scores
- Session-based trace grouping

Note: Langfuse v3 uses OpenTelemetry for instrumentation instead of callbacks.
Use the observe decorator for automatic tracing.
"""
import logging
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LangfuseConfigError(Exception):
    """Raised when Langfuse configuration is invalid or missing."""
    pass


def is_langfuse_enabled() -> bool:
    """Check if Langfuse is enabled via environment variables.

    Returns:
        True if both LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set.
    """
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    return bool(public_key and secret_key)


# Alias for backwards compatibility
is_langfuse_configured = is_langfuse_enabled


def get_langfuse_callback(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    trace_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """Get a Langfuse callback handler for LangChain integration.

    Note: In Langfuse v3, the callback handler API has changed. This function
    now returns a context object that can be used for manual tracing.

    For automatic tracing, use the @observe decorator instead:

        from langfuse import observe

        @observe()
        async def my_function():
            # Automatically traced
            pass

    Args:
        session_id: Optional session ID to group related traces.
        user_id: Optional user ID for per-athlete tracking.
        trace_name: Optional name for the trace.
        tags: Optional list of tags for filtering traces.
        metadata: Optional metadata dict to attach to the trace.

    Returns:
        A trace context object if Langfuse is configured, None otherwise.
    """
    if not is_langfuse_enabled():
        logger.debug("Langfuse not configured: missing API keys")
        return None

    try:
        client = get_langfuse_client()
        if not client:
            return None

        # Create a trace context that can be used for manual instrumentation
        trace = client.trace(
            name=trace_name or "langchain_trace",
            session_id=session_id,
            user_id=user_id,
            tags=tags or [],
            metadata=metadata or {},
        )

        logger.debug(
            f"Created Langfuse trace: session={session_id}, "
            f"user={user_id}, name={trace_name}"
        )
        return trace

    except Exception as e:
        logger.warning(f"Failed to create Langfuse trace: {e}")
        return None


@lru_cache(maxsize=1)
def get_langfuse_client():
    """Get the Langfuse client for direct API access.

    Use this client for:
    - Creating custom traces and spans
    - Recording scores and feedback
    - Querying trace data
    - Manual instrumentation

    The client is cached as a singleton for efficiency.

    Returns:
        Langfuse client if properly configured, None otherwise.

    Example:
        >>> from observability import get_langfuse_client
        >>> client = get_langfuse_client()
        >>> if client:
        ...     trace = client.trace(name="custom_operation")
        ...     span = trace.span(name="step_1")
        ...     # ... do work ...
        ...     span.end()
    """
    try:
        from langfuse import Langfuse

        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        if not public_key or not secret_key:
            logger.debug("Langfuse not configured: missing API keys")
            return None

        client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )

        logger.info(f"Langfuse client initialized (host: {host})")
        return client

    except ImportError:
        logger.debug("Langfuse not installed - observability disabled")
        return None
    except Exception as e:
        logger.warning(f"Failed to initialize Langfuse client: {e}")
        return None


def flush_langfuse() -> None:
    """Flush any pending Langfuse data to ensure all traces are sent.

    Call this before application shutdown to ensure all trace data
    is transmitted to Langfuse. The flush is non-blocking if there's
    no pending data.
    """
    client = get_langfuse_client()
    if client:
        try:
            client.flush()
            logger.debug("Langfuse data flushed successfully")
        except Exception as e:
            logger.warning(f"Failed to flush Langfuse data: {e}")


def shutdown_langfuse() -> None:
    """Shutdown the Langfuse client gracefully.

    This flushes pending data and closes connections. Call this
    during application shutdown.
    """
    client = get_langfuse_client()
    if client:
        try:
            client.shutdown()
            logger.info("Langfuse client shutdown complete")
        except Exception as e:
            logger.warning(f"Error during Langfuse shutdown: {e}")

    # Clear the cached client
    get_langfuse_client.cache_clear()


# Convenience global handler (deprecated - use observe decorator instead)
langfuse_handler: Optional[Any] = None


def configure_handler(
    session_id: str,
    user_id: str,
    trace_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Optional[Any]:
    """Configure the global Langfuse handler for a request.

    Note: This is deprecated in Langfuse v3. Use the @observe decorator instead.

    Args:
        session_id: Session ID to group traces.
        user_id: User ID for per-athlete tracking.
        trace_name: Optional name for the trace.
        tags: Optional list of tags.

    Returns:
        The configured trace context.
    """
    global langfuse_handler
    langfuse_handler = get_langfuse_callback(
        session_id=session_id,
        user_id=user_id,
        trace_name=trace_name,
        tags=tags,
    )
    return langfuse_handler


def get_trace_url(trace_id: str) -> Optional[str]:
    """Get the URL to view a trace in the Langfuse UI.

    Args:
        trace_id: The trace ID to link to.

    Returns:
        URL to the trace in Langfuse, or None if not configured.
    """
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")

    if not public_key:
        return None

    return f"{host}/trace/{trace_id}"


def create_span(
    trace,
    name: str,
    metadata: Optional[Dict[str, Any]] = None,
    input_data: Optional[Any] = None,
):
    """Create a span within a trace.

    Args:
        trace: The parent trace object.
        name: Name of the span.
        metadata: Optional metadata dict.
        input_data: Optional input data for the span.

    Returns:
        The span object.
    """
    if trace is None:
        return None

    try:
        return trace.span(
            name=name,
            metadata=metadata or {},
            input=input_data,
        )
    except Exception as e:
        logger.warning(f"Failed to create span: {e}")
        return None


def end_span(span, output_data: Optional[Any] = None):
    """End a span with optional output data.

    Args:
        span: The span object to end.
        output_data: Optional output data for the span.
    """
    if span is None:
        return

    try:
        span.end(output=output_data)
    except Exception as e:
        logger.warning(f"Failed to end span: {e}")


def record_generation(
    trace,
    name: str,
    model: str,
    input_messages: List[Dict[str, Any]],
    output: str,
    usage: Optional[Dict[str, int]] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Record an LLM generation in the trace.

    Args:
        trace: The parent trace object.
        name: Name of the generation.
        model: Model name/id used.
        input_messages: Input messages sent to the LLM.
        output: Output text from the LLM.
        usage: Token usage dict with input/output/total.
        metadata: Optional metadata.

    Returns:
        The generation object.
    """
    if trace is None:
        return None

    try:
        return trace.generation(
            name=name,
            model=model,
            input=input_messages,
            output=output,
            usage=usage,
            metadata=metadata or {},
        )
    except Exception as e:
        logger.warning(f"Failed to record generation: {e}")
        return None
