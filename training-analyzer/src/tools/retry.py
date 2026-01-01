"""Retry logic and circuit breaker for tool calls.

This module provides retry decorators for handling transient failures in
tool calls (database issues, API timeouts, etc.) gracefully.

Features:
- Exponential backoff with configurable delays
- Retryable exception filtering (don't retry validation errors)
- Circuit breaker pattern to prevent hammering failing services
- Metrics tracking for observability (Langfuse integration)

Usage:
    from tools.retry import with_retry, RetryableError

    @with_retry(max_retries=2, base_delay=0.5)
    def my_tool_function():
        # Database/API call that might fail transiently
        pass

Design Constraints:
- Max total retry time < 5 seconds per tool call
- Don't retry validation errors (wrong params)
- DO retry: database connection errors, timeouts, transient API failures
"""

import logging
import sqlite3
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Optional, Set, Tuple, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# Exception Classifications
# ============================================================================

# Exceptions that should be retried (transient failures)
RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    # Database errors
    sqlite3.OperationalError,  # Database locked, disk I/O error, etc.
    sqlite3.DatabaseError,  # Corruption, malformed database
    # Network/API errors (if httpx or requests are used)
    ConnectionError,
    TimeoutError,
    OSError,  # Network-related OS errors
)

# Exceptions that should NOT be retried (permanent failures)
NON_RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    # Validation errors
    ValueError,
    TypeError,
    KeyError,
    # Programming errors
    sqlite3.ProgrammingError,  # SQL syntax error, wrong API usage
    sqlite3.IntegrityError,  # Constraint violation
    AttributeError,
    # Import errors
    ImportError,
    ModuleNotFoundError,
)


class RetryableError(Exception):
    """Explicitly mark an error as retryable.

    Wrap any exception in this to force retry behavior:
        raise RetryableError("Transient failure") from original_error
    """

    pass


class NonRetryableError(Exception):
    """Explicitly mark an error as non-retryable.

    Wrap any exception in this to prevent retry behavior:
        raise NonRetryableError("Permanent failure") from original_error
    """

    pass


def is_retryable(exception: Exception) -> bool:
    """Determine if an exception should be retried.

    Args:
        exception: The exception to check.

    Returns:
        True if the exception is transient and should be retried.
    """
    # Explicitly marked exceptions
    if isinstance(exception, RetryableError):
        return True
    if isinstance(exception, NonRetryableError):
        return False

    # Check against known non-retryable exceptions first
    if isinstance(exception, NON_RETRYABLE_EXCEPTIONS):
        return False

    # Check against known retryable exceptions
    if isinstance(exception, RETRYABLE_EXCEPTIONS):
        return True

    # For unknown exceptions, check the message for hints
    error_msg = str(exception).lower()
    retryable_hints = [
        "timeout",
        "connection",
        "temporarily",
        "retry",
        "unavailable",
        "busy",
        "locked",
        "network",
        "socket",
    ]
    non_retryable_hints = [
        "invalid",
        "not found",
        "permission",
        "forbidden",
        "unauthorized",
        "syntax",
        "missing",
        "required",
    ]

    # Check for retryable hints
    if any(hint in error_msg for hint in retryable_hints):
        return True

    # Check for non-retryable hints
    if any(hint in error_msg for hint in non_retryable_hints):
        return False

    # Default: don't retry unknown exceptions
    return False


# ============================================================================
# Retry Configuration
# ============================================================================


@dataclass
class ToolRetryConfig:
    """Configuration for tool retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (default 2).
        base_delay: Initial delay between retries in seconds (default 0.5).
        max_delay: Maximum delay between retries in seconds (default 2.0).
        exponential_backoff: Whether to use exponential backoff (default True).
        jitter: Whether to add random jitter to delays (default True).
        max_total_time: Maximum total time for all retries in seconds (default 5.0).
        retryable_exceptions: Tuple of exception types to retry.
    """

    max_retries: int = 2
    base_delay: float = 0.5
    max_delay: float = 2.0
    exponential_backoff: bool = True
    jitter: bool = True
    max_total_time: float = 5.0  # Max 5 seconds total as per requirements
    retryable_exceptions: Tuple[Type[Exception], ...] = RETRYABLE_EXCEPTIONS


# Default configuration instance
DEFAULT_RETRY_CONFIG = ToolRetryConfig()


# ============================================================================
# Retry Metrics
# ============================================================================


@dataclass
class RetryMetrics:
    """Metrics for retry attempts.

    Used for observability and debugging.
    """

    tool_name: str
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    total_retry_time_ms: float = 0.0
    last_error: Optional[str] = None
    errors_by_type: dict = field(default_factory=dict)

    def record_attempt(
        self,
        success: bool,
        attempt_number: int,
        duration_ms: float,
        error: Optional[Exception] = None,
    ) -> None:
        """Record a retry attempt."""
        self.total_attempts += 1
        self.total_retry_time_ms += duration_ms

        if success:
            self.successful_attempts += 1
        else:
            self.failed_attempts += 1
            if error:
                self.last_error = str(error)
                error_type = type(error).__name__
                self.errors_by_type[error_type] = (
                    self.errors_by_type.get(error_type, 0) + 1
                )

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/tracing."""
        return {
            "tool_name": self.tool_name,
            "total_attempts": self.total_attempts,
            "successful_attempts": self.successful_attempts,
            "failed_attempts": self.failed_attempts,
            "total_retry_time_ms": round(self.total_retry_time_ms, 2),
            "last_error": self.last_error,
            "errors_by_type": self.errors_by_type,
        }


# Global metrics storage (thread-safe for single-threaded async)
_retry_metrics: dict[str, RetryMetrics] = {}


def get_retry_metrics(tool_name: str) -> RetryMetrics:
    """Get or create retry metrics for a tool."""
    if tool_name not in _retry_metrics:
        _retry_metrics[tool_name] = RetryMetrics(tool_name=tool_name)
    return _retry_metrics[tool_name]


def get_all_retry_metrics() -> dict[str, dict]:
    """Get all retry metrics for observability."""
    return {name: metrics.to_dict() for name, metrics in _retry_metrics.items()}


def reset_retry_metrics() -> None:
    """Reset all retry metrics (for testing)."""
    _retry_metrics.clear()


# ============================================================================
# Circuit Breaker Pattern
# ============================================================================


@dataclass
class CircuitBreaker:
    """Circuit breaker to prevent repeated calls to failing services.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failing, requests are rejected immediately
    - HALF_OPEN: Testing if service recovered, limited requests allowed

    Attributes:
        failure_threshold: Number of failures before opening circuit (default 3).
        reset_timeout: Seconds to wait before trying again (default 30.0).
        half_open_max_calls: Max calls allowed in half-open state (default 1).
    """

    failure_threshold: int = 3
    reset_timeout: float = 30.0
    half_open_max_calls: int = 1

    # Internal state
    failure_count: int = field(default=0, init=False)
    last_failure_time: Optional[float] = field(default=None, init=False)
    state: str = field(default="closed", init=False)
    half_open_calls: int = field(default=0, init=False)

    def can_execute(self) -> bool:
        """Check if a request can be executed.

        Returns:
            True if the circuit allows the request.
        """
        if self.state == "closed":
            return True

        if self.state == "open":
            # Check if reset timeout has passed
            if self.last_failure_time is not None:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.reset_timeout:
                    self.state = "half_open"
                    self.half_open_calls = 0
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                    return True
            return False

        if self.state == "half_open":
            # Allow limited calls in half-open state
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False

        return True

    def record_success(self) -> None:
        """Record a successful call."""
        if self.state == "half_open":
            # Success in half-open means service recovered
            self.state = "closed"
            self.failure_count = 0
            self.half_open_calls = 0
            logger.info("Circuit breaker CLOSED - service recovered")
        elif self.state == "closed":
            # Reset failure count on success
            self.failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == "half_open":
            # Failure in half-open means service still failing
            self.state = "open"
            logger.warning("Circuit breaker OPEN - service still failing")
        elif self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"Circuit breaker OPEN after {self.failure_count} failures"
            )

    def reset(self) -> None:
        """Reset the circuit breaker state."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"
        self.half_open_calls = 0

    def get_state(self) -> dict:
        """Get current state for debugging."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "failure_threshold": self.failure_threshold,
            "reset_timeout": self.reset_timeout,
        }


# Global circuit breakers per tool
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    tool_name: str,
    failure_threshold: int = 3,
    reset_timeout: float = 30.0,
) -> CircuitBreaker:
    """Get or create a circuit breaker for a tool."""
    if tool_name not in _circuit_breakers:
        _circuit_breakers[tool_name] = CircuitBreaker(
            failure_threshold=failure_threshold,
            reset_timeout=reset_timeout,
        )
    return _circuit_breakers[tool_name]


def reset_all_circuit_breakers() -> None:
    """Reset all circuit breakers (for testing)."""
    for cb in _circuit_breakers.values():
        cb.reset()
    _circuit_breakers.clear()


# ============================================================================
# Retry Decorator
# ============================================================================


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open and rejects the call."""

    pass


def with_retry(
    max_retries: int = 2,
    base_delay: float = 0.5,
    max_delay: float = 2.0,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    use_circuit_breaker: bool = False,
    circuit_failure_threshold: int = 3,
    circuit_reset_timeout: float = 30.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to add retry logic to tool functions.

    Args:
        max_retries: Maximum retry attempts (default 2, so 3 total attempts).
        base_delay: Initial delay between retries in seconds (default 0.5).
        max_delay: Maximum delay cap in seconds (default 2.0).
        retryable_exceptions: Tuple of exceptions to retry. If None, uses
            the is_retryable() function for intelligent classification.
        use_circuit_breaker: Whether to use circuit breaker pattern.
        circuit_failure_threshold: Failures before opening circuit.
        circuit_reset_timeout: Seconds before retrying after circuit opens.

    Returns:
        Decorated function with retry logic.

    Example:
        @with_retry(max_retries=2, base_delay=0.5)
        def query_database():
            return db.execute("SELECT * FROM workouts")

        # With circuit breaker
        @with_retry(max_retries=2, use_circuit_breaker=True)
        def call_external_api():
            return api.get_data()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            tool_name = func.__name__
            metrics = get_retry_metrics(tool_name)
            circuit_breaker = None

            if use_circuit_breaker:
                circuit_breaker = get_circuit_breaker(
                    tool_name,
                    failure_threshold=circuit_failure_threshold,
                    reset_timeout=circuit_reset_timeout,
                )
                if not circuit_breaker.can_execute():
                    logger.warning(
                        f"Circuit breaker OPEN for {tool_name} - rejecting call"
                    )
                    raise CircuitOpenError(
                        f"Service {tool_name} is temporarily unavailable. "
                        f"Please try again in {circuit_reset_timeout} seconds."
                    )

            last_exception: Optional[Exception] = None
            start_time = time.time()
            max_total_time = 5.0  # Hard limit: 5 seconds total

            for attempt in range(max_retries + 1):
                attempt_start = time.time()

                try:
                    result = func(*args, **kwargs)

                    # Record success
                    duration_ms = (time.time() - attempt_start) * 1000
                    metrics.record_attempt(True, attempt, duration_ms)

                    if circuit_breaker:
                        circuit_breaker.record_success()

                    if attempt > 0:
                        logger.info(
                            f"Tool {tool_name} succeeded after {attempt + 1} attempts"
                        )

                    return result

                except Exception as e:
                    last_exception = e
                    duration_ms = (time.time() - attempt_start) * 1000
                    metrics.record_attempt(False, attempt, duration_ms, e)

                    # Check if we should retry this exception
                    should_retry = False
                    if retryable_exceptions:
                        should_retry = isinstance(e, retryable_exceptions)
                    else:
                        should_retry = is_retryable(e)

                    # Check time limit
                    elapsed = time.time() - start_time
                    if elapsed >= max_total_time:
                        logger.error(
                            f"Tool {tool_name} exceeded max total time "
                            f"({max_total_time}s) after {attempt + 1} attempts"
                        )
                        should_retry = False

                    if attempt < max_retries and should_retry:
                        # Calculate delay with exponential backoff
                        delay = base_delay * (2**attempt)
                        delay = min(delay, max_delay)

                        # Ensure we don't exceed total time limit
                        remaining = max_total_time - elapsed
                        if delay > remaining:
                            delay = max(0, remaining - 0.1)

                        if delay > 0:
                            logger.warning(
                                f"Tool {tool_name} failed (attempt {attempt + 1}/{max_retries + 1}): "
                                f"{type(e).__name__}: {e}. Retrying in {delay:.2f}s..."
                            )
                            time.sleep(delay)
                    else:
                        # Log final failure
                        if should_retry:
                            logger.error(
                                f"Tool {tool_name} failed after {attempt + 1} attempts: "
                                f"{type(e).__name__}: {e}"
                            )
                        else:
                            logger.error(
                                f"Tool {tool_name} failed with non-retryable error: "
                                f"{type(e).__name__}: {e}"
                            )

                        if circuit_breaker:
                            circuit_breaker.record_failure()

                        raise

            # Should not reach here, but just in case
            if last_exception:
                if circuit_breaker:
                    circuit_breaker.record_failure()
                raise last_exception

            # This should never happen
            raise RuntimeError(f"Tool {tool_name} failed with no exception captured")

        return wrapper

    return decorator


def with_retry_async(
    max_retries: int = 2,
    base_delay: float = 0.5,
    max_delay: float = 2.0,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    use_circuit_breaker: bool = False,
    circuit_failure_threshold: int = 3,
    circuit_reset_timeout: float = 30.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Async version of with_retry decorator.

    Same parameters as with_retry but for async functions.

    Example:
        @with_retry_async(max_retries=2, base_delay=0.5)
        async def query_database_async():
            return await db.execute_async("SELECT * FROM workouts")
    """
    import asyncio

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            tool_name = func.__name__
            metrics = get_retry_metrics(tool_name)
            circuit_breaker = None

            if use_circuit_breaker:
                circuit_breaker = get_circuit_breaker(
                    tool_name,
                    failure_threshold=circuit_failure_threshold,
                    reset_timeout=circuit_reset_timeout,
                )
                if not circuit_breaker.can_execute():
                    logger.warning(
                        f"Circuit breaker OPEN for {tool_name} - rejecting call"
                    )
                    raise CircuitOpenError(
                        f"Service {tool_name} is temporarily unavailable. "
                        f"Please try again in {circuit_reset_timeout} seconds."
                    )

            last_exception: Optional[Exception] = None
            start_time = time.time()
            max_total_time = 5.0  # Hard limit: 5 seconds total

            for attempt in range(max_retries + 1):
                attempt_start = time.time()

                try:
                    result = await func(*args, **kwargs)

                    # Record success
                    duration_ms = (time.time() - attempt_start) * 1000
                    metrics.record_attempt(True, attempt, duration_ms)

                    if circuit_breaker:
                        circuit_breaker.record_success()

                    if attempt > 0:
                        logger.info(
                            f"Tool {tool_name} succeeded after {attempt + 1} attempts"
                        )

                    return result

                except Exception as e:
                    last_exception = e
                    duration_ms = (time.time() - attempt_start) * 1000
                    metrics.record_attempt(False, attempt, duration_ms, e)

                    # Check if we should retry this exception
                    should_retry = False
                    if retryable_exceptions:
                        should_retry = isinstance(e, retryable_exceptions)
                    else:
                        should_retry = is_retryable(e)

                    # Check time limit
                    elapsed = time.time() - start_time
                    if elapsed >= max_total_time:
                        logger.error(
                            f"Tool {tool_name} exceeded max total time "
                            f"({max_total_time}s) after {attempt + 1} attempts"
                        )
                        should_retry = False

                    if attempt < max_retries and should_retry:
                        # Calculate delay with exponential backoff
                        delay = base_delay * (2**attempt)
                        delay = min(delay, max_delay)

                        # Ensure we don't exceed total time limit
                        remaining = max_total_time - elapsed
                        if delay > remaining:
                            delay = max(0, remaining - 0.1)

                        if delay > 0:
                            logger.warning(
                                f"Tool {tool_name} failed (attempt {attempt + 1}/{max_retries + 1}): "
                                f"{type(e).__name__}: {e}. Retrying in {delay:.2f}s..."
                            )
                            await asyncio.sleep(delay)
                    else:
                        # Log final failure
                        if should_retry:
                            logger.error(
                                f"Tool {tool_name} failed after {attempt + 1} attempts: "
                                f"{type(e).__name__}: {e}"
                            )
                        else:
                            logger.error(
                                f"Tool {tool_name} failed with non-retryable error: "
                                f"{type(e).__name__}: {e}"
                            )

                        if circuit_breaker:
                            circuit_breaker.record_failure()

                        raise

            # Should not reach here, but just in case
            if last_exception:
                if circuit_breaker:
                    circuit_breaker.record_failure()
                raise last_exception

            # This should never happen
            raise RuntimeError(f"Tool {tool_name} failed with no exception captured")

        return wrapper

    return decorator


# ============================================================================
# Langfuse Integration
# ============================================================================


def log_retry_metrics_to_langfuse(trace, tool_name: str) -> None:
    """Log retry metrics to Langfuse for observability.

    Args:
        trace: Langfuse trace object.
        tool_name: Name of the tool to log metrics for.
    """
    if trace is None:
        return

    metrics = get_retry_metrics(tool_name)
    if metrics.total_attempts == 0:
        return

    try:
        from ..observability.langfuse_config import create_span, end_span

        span = create_span(
            trace,
            name=f"{tool_name}_retry_metrics",
            metadata=metrics.to_dict(),
        )
        if span:
            end_span(span, output_data={"logged": True})
    except Exception as e:
        logger.debug(f"Failed to log retry metrics to Langfuse: {e}")


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Decorators
    "with_retry",
    "with_retry_async",
    # Configuration
    "ToolRetryConfig",
    "DEFAULT_RETRY_CONFIG",
    # Exception types
    "RetryableError",
    "NonRetryableError",
    "CircuitOpenError",
    # Exception classification
    "is_retryable",
    "RETRYABLE_EXCEPTIONS",
    "NON_RETRYABLE_EXCEPTIONS",
    # Circuit breaker
    "CircuitBreaker",
    "get_circuit_breaker",
    "reset_all_circuit_breakers",
    # Metrics
    "RetryMetrics",
    "get_retry_metrics",
    "get_all_retry_metrics",
    "reset_retry_metrics",
    # Langfuse integration
    "log_retry_metrics_to_langfuse",
]
