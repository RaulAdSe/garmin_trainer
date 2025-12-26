"""
LLM providers and model selection.

This module provides a unified interface for LLM interactions with:
- Multiple model types for different task complexities
- Automatic retry with exponential backoff
- Rate limit handling
- Proper error handling and custom exceptions
- Response caching support
"""

from enum import Enum
from typing import AsyncIterator, Callable, Dict, Optional, TypeVar, Any
import asyncio
import logging
import os
import threading
import time

from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError

from ..config import get_settings
from ..exceptions import (
    LLMServiceUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMResponseInvalidError,
    LLMError,
)


logger = logging.getLogger(__name__)

T = TypeVar("T")


class ModelType(Enum):
    """Model types for different task complexities."""

    FAST = "fast"    # GPT-5-nano for quick tasks
    SMART = "smart"  # GPT-5-mini for complex analysis


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        retryable_status_codes: Optional[set[int]] = None,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_status_codes = retryable_status_codes or {429, 500, 502, 503, 504}

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number."""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


class LLMMetrics:
    """Track LLM usage metrics."""

    def __init__(self) -> None:
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.retried_requests = 0
        self.total_tokens_input = 0
        self.total_tokens_output = 0
        self._last_request_time: Optional[float] = None
        self._request_times: list[float] = []

    def record_request(
        self,
        success: bool,
        retried: bool = False,
        input_tokens: int = 0,
        output_tokens: int = 0,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Record a request."""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        if retried:
            self.retried_requests += 1
        self.total_tokens_input += input_tokens
        self.total_tokens_output += output_tokens
        self._last_request_time = time.time()
        if duration_ms is not None:
            self._request_times.append(duration_ms)
            # Keep only last 100 request times
            if len(self._request_times) > 100:
                self._request_times = self._request_times[-100:]

    @property
    def avg_request_time_ms(self) -> float:
        """Average request time in milliseconds."""
        if not self._request_times:
            return 0.0
        return sum(self._request_times) / len(self._request_times)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "retried_requests": self.retried_requests,
            "total_tokens_input": self.total_tokens_input,
            "total_tokens_output": self.total_tokens_output,
            "avg_request_time_ms": round(self.avg_request_time_ms, 2),
        }


class LLMClient:
    """
    Unified LLM client with model routing, retry logic, and error handling.

    Features:
    - Multiple model types for different task complexities
    - Automatic retry with exponential backoff
    - Rate limit handling
    - Request metrics tracking
    - Proper error handling with custom exceptions
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        retry_config: Optional[RetryConfig] = None,
    ) -> None:
        """
        Initialize the LLM client.

        Args:
            api_key: OpenAI API key (defaults to env var or settings)
            retry_config: Configuration for retry behavior
        """
        settings = get_settings()
        api_key = api_key or settings.openai_api_key or os.environ.get("OPENAI_API_KEY")

        if not api_key:
            raise LLMServiceUnavailableError(
                message="OPENAI_API_KEY not configured",
                details={"configuration_missing": "openai_api_key"},
            )

        self.client = AsyncOpenAI(api_key=api_key)
        self.model_map = {
            ModelType.FAST: settings.llm_model_fast,   # gpt-5-nano
            ModelType.SMART: settings.llm_model_smart,  # gpt-5-mini
        }
        self.retry_config = retry_config or RetryConfig()
        self.metrics = LLMMetrics()
        self._logger = logger

    def _get_model(self, model_type: ModelType) -> str:
        """Get the model ID for a model type."""
        return self.model_map.get(model_type, self.model_map[ModelType.SMART])

    async def _execute_with_retry(
        self,
        operation: Callable[[], T],
        operation_name: str = "LLM request",
    ) -> T:
        """
        Execute an operation with retry logic.

        Args:
            operation: Async callable to execute
            operation_name: Name for logging

        Returns:
            The operation result

        Raises:
            LLMError: On unrecoverable failure
        """
        last_exception: Optional[Exception] = None
        retried = False

        for attempt in range(self.retry_config.max_retries + 1):
            start_time = time.time()

            try:
                result = await operation()
                duration_ms = (time.time() - start_time) * 1000
                self.metrics.record_request(
                    success=True,
                    retried=retried,
                    duration_ms=duration_ms,
                )
                return result

            except RateLimitError as e:
                last_exception = e
                retried = True
                retry_after = getattr(e, "retry_after", None)

                if attempt < self.retry_config.max_retries:
                    delay = retry_after if retry_after else self.retry_config.get_delay(attempt)
                    self._logger.warning(
                        f"{operation_name} rate limited. "
                        f"Retry {attempt + 1}/{self.retry_config.max_retries} "
                        f"in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                else:
                    self.metrics.record_request(success=False, retried=True)
                    raise LLMRateLimitError(
                        retry_after=int(delay) if retry_after else None,
                    )

            except APIConnectionError as e:
                last_exception = e
                retried = True

                if attempt < self.retry_config.max_retries:
                    delay = self.retry_config.get_delay(attempt)
                    self._logger.warning(
                        f"{operation_name} connection error. "
                        f"Retry {attempt + 1}/{self.retry_config.max_retries} "
                        f"in {delay:.1f}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    self.metrics.record_request(success=False, retried=True)
                    raise LLMServiceUnavailableError(
                        message=f"Connection to LLM service failed: {e}",
                    )

            except APIError as e:
                last_exception = e
                status = getattr(e, "status_code", 500)

                if status in self.retry_config.retryable_status_codes:
                    retried = True
                    if attempt < self.retry_config.max_retries:
                        delay = self.retry_config.get_delay(attempt)
                        self._logger.warning(
                            f"{operation_name} API error (status {status}). "
                            f"Retry {attempt + 1}/{self.retry_config.max_retries} "
                            f"in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                    else:
                        self.metrics.record_request(success=False, retried=True)
                        raise LLMServiceUnavailableError(
                            message=f"LLM API error after retries: {e}",
                            details={"status_code": status},
                        )
                else:
                    self.metrics.record_request(success=False, retried=retried)
                    raise LLMError(
                        message=f"LLM API error: {e}",
                        details={"status_code": status},
                    )

            except asyncio.TimeoutError as e:
                last_exception = e
                self.metrics.record_request(success=False, retried=retried)
                raise LLMTimeoutError()

            except Exception as e:
                last_exception = e
                self.metrics.record_request(success=False, retried=retried)
                self._logger.error(f"Unexpected error in {operation_name}: {e}")
                raise LLMError(message=f"Unexpected LLM error: {e}")

        # Should not reach here, but just in case
        self.metrics.record_request(success=False, retried=True)
        raise LLMError(message=f"Operation failed after all retries: {last_exception}")

    async def completion(
        self,
        system: str,
        user: str,
        model: ModelType = ModelType.SMART,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout: Optional[float] = 60.0,
    ) -> str:
        """
        Get a completion from the LLM.

        Args:
            system: System prompt
            user: User message
            model: Model type to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            timeout: Request timeout in seconds

        Returns:
            The assistant's response text

        Raises:
            LLMError: On failure
        """
        async def _make_request() -> str:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self._get_model(model),
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                ),
                timeout=timeout,
            )
            content = response.choices[0].message.content
            if content is None:
                raise LLMResponseInvalidError(message="Empty response from LLM")
            return content

        return await self._execute_with_retry(_make_request, "completion")

    async def completion_json(
        self,
        system: str,
        user: str,
        model: ModelType = ModelType.SMART,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout: Optional[float] = 60.0,
    ) -> Dict[str, Any]:
        """
        Get a JSON completion from the LLM using JSON mode.

        This method forces the LLM to return valid JSON output by setting
        response_format={"type": "json_object"}.

        Args:
            system: System prompt (must mention JSON in the prompt)
            user: User message
            model: Model type to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            timeout: Request timeout in seconds

        Returns:
            The parsed JSON response as a dictionary

        Raises:
            LLMError: On failure
            LLMResponseInvalidError: If response is not valid JSON
        """
        import json

        async def _make_request() -> Dict[str, Any]:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self._get_model(model),
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                ),
                timeout=timeout,
            )
            content = response.choices[0].message.content
            if content is None:
                raise LLMResponseInvalidError(message="Empty response from LLM")
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                raise LLMResponseInvalidError(
                    message=f"Invalid JSON response from LLM: {e}",
                    details={"raw_content": content[:500]},
                )

        return await self._execute_with_retry(_make_request, "completion_json")

    def get_model_name(self, model_type: ModelType = ModelType.SMART) -> str:
        """
        Get the model name for a given model type.

        Args:
            model_type: The model type to get the name for

        Returns:
            The model name string (e.g., "gpt-5-mini")
        """
        return self._get_model(model_type)

    async def stream_completion(
        self,
        system: str,
        user: str,
        model: ModelType = ModelType.SMART,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """
        Stream a completion from the LLM.

        Args:
            system: System prompt
            user: User message
            model: Model type to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Yields:
            Chunks of the assistant's response
        """
        start_time = time.time()
        chunks_yielded = 0

        try:
            stream = await self.client.chat.completions.create(
                model=self._get_model(model),
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    chunks_yielded += 1
                    yield chunk.choices[0].delta.content

            duration_ms = (time.time() - start_time) * 1000
            self.metrics.record_request(
                success=True,
                duration_ms=duration_ms,
            )

        except RateLimitError as e:
            self.metrics.record_request(success=False)
            raise LLMRateLimitError()
        except APIConnectionError as e:
            self.metrics.record_request(success=False)
            raise LLMServiceUnavailableError(message=str(e))
        except Exception as e:
            self.metrics.record_request(success=False)
            self._logger.error(f"Stream error: {e}")
            raise LLMError(message=f"Streaming error: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return self.metrics.to_dict()


# Singleton instance with thread-safe locking
_llm_client: Optional[LLMClient] = None
_llm_client_sync_lock = threading.Lock()
_llm_client_async_lock = asyncio.Lock()


def get_llm_client() -> LLMClient:
    """
    Get the LLM client singleton (thread-safe).

    Uses a threading.Lock to prevent race conditions when multiple
    threads try to initialize the client simultaneously.

    Returns:
        The LLM client instance
    """
    global _llm_client
    # Double-checked locking pattern for thread safety
    if _llm_client is None:
        with _llm_client_sync_lock:
            # Check again inside the lock in case another thread initialized it
            if _llm_client is None:
                _llm_client = LLMClient()
    return _llm_client


async def get_llm_client_async() -> LLMClient:
    """
    Get the LLM client singleton (async-safe).

    Uses an asyncio.Lock to prevent race conditions when multiple
    async tasks try to initialize the client simultaneously.

    Returns:
        The LLM client instance
    """
    global _llm_client
    # Double-checked locking pattern for async safety
    if _llm_client is None:
        async with _llm_client_async_lock:
            # Check again inside the lock in case another task initialized it
            if _llm_client is None:
                _llm_client = LLMClient()
    return _llm_client


def reset_llm_client() -> None:
    """Reset the LLM client singleton (for testing)."""
    global _llm_client
    with _llm_client_sync_lock:
        _llm_client = None
