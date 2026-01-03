"""
LLM providers and model selection.

This module provides a unified interface for LLM interactions with:
- Multiple model types for different task complexities
- Automatic retry with exponential backoff
- Rate limit handling
- Proper error handling and custom exceptions
- Response caching support
- AI usage tracking and cost logging
"""

from enum import Enum
from typing import AsyncIterator, Callable, Dict, Optional, TypeVar, Any, Tuple
import asyncio
import logging
import os
import threading
import time
import uuid

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
    - AI usage tracking with cost logging
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
        self._usage_repo = None  # Lazy-loaded

    def _get_usage_repo(self):
        """Get the AI usage repository (lazy loaded)."""
        if self._usage_repo is None:
            try:
                from ..db.repositories.ai_usage_repository import get_ai_usage_repository
                self._usage_repo = get_ai_usage_repository()
            except Exception as e:
                self._logger.warning(f"Failed to initialize AI usage repository: {e}")
                self._usage_repo = None
        return self._usage_repo

    def _log_usage(
        self,
        model_id: str,
        model_type: Optional[str],
        input_tokens: int,
        output_tokens: int,
        duration_ms: int,
        analysis_type: str,
        user_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        status: str = "completed",
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log AI usage to the database.

        Args:
            model_id: The model used
            model_type: 'fast' or 'smart'
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            duration_ms: Request duration in milliseconds
            analysis_type: Type of analysis (e.g., 'workout_analysis', 'chat')
            user_id: User who made the request (optional)
            entity_type: Type of entity (e.g., 'workout')
            entity_id: ID of the entity
            status: Request status
            error_message: Error message if failed
        """
        repo = self._get_usage_repo()
        if repo is None:
            return

        try:
            from ..services.ai_cost_calculator import calculate_cost
            total_cost = calculate_cost(model_id, input_tokens, output_tokens)

            repo.log_usage(
                request_id=str(uuid.uuid4()),
                user_id=user_id,
                model_id=model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_cost_cents=total_cost,
                analysis_type=analysis_type,
                duration_ms=duration_ms,
                model_type=model_type,
                entity_type=entity_type,
                entity_id=entity_id,
                status=status,
                error_message=error_message,
            )
        except Exception as e:
            self._logger.warning(f"Failed to log AI usage: {e}")

    def _get_model(self, model_type: ModelType) -> str:
        """Get the model ID for a model type."""
        return self.model_map.get(model_type, self.model_map[ModelType.SMART])

    def _try_repair_truncated_json(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to repair truncated JSON by closing unclosed brackets/braces.

        This is useful when the LLM response is truncated due to max_tokens limit.
        The method tries to close any unclosed JSON structures to make it parseable.

        Args:
            content: The truncated JSON string

        Returns:
            Parsed JSON dictionary if repair successful, None otherwise
        """
        import json
        import re

        if not content or not content.strip():
            return None

        content = content.strip()

        # First, try parsing as-is (maybe it's actually complete)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to repair by closing unclosed structures
        # Count open brackets and braces
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')

        # Check if we're inside a string (unclosed quote)
        # Simple heuristic: count quotes
        quote_count = content.count('"') - content.count('\\"')
        in_string = quote_count % 2 == 1

        repaired = content

        # If inside a string, close it
        if in_string:
            repaired += '"'

        # Close arrays first, then objects (reverse order of typical nesting)
        repaired += ']' * open_brackets
        repaired += '}' * open_braces

        try:
            result = json.loads(repaired)
            return result
        except json.JSONDecodeError:
            pass

        # More aggressive repair: try to find the last valid JSON object
        # by progressively removing characters from the end and closing
        for trim_amount in range(1, min(200, len(content))):
            trimmed = content[:-trim_amount].strip()
            if not trimmed:
                break

            # Recalculate after trimming
            open_braces = trimmed.count('{') - trimmed.count('}')
            open_brackets = trimmed.count('[') - trimmed.count(']')
            quote_count = trimmed.count('"') - trimmed.count('\\"')
            in_string = quote_count % 2 == 1

            repaired = trimmed
            if in_string:
                repaired += '"'
            repaired += ']' * open_brackets
            repaired += '}' * open_braces

            try:
                result = json.loads(repaired)
                # Validate it's a dict (not just a valid JSON primitive)
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                continue

        return None

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
        user_id: Optional[str] = None,
        analysis_type: str = "general",
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
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
            user_id: User ID for usage tracking (optional)
            analysis_type: Type of analysis for usage tracking
            entity_type: Type of entity being analyzed (e.g., 'workout')
            entity_id: ID of the entity being analyzed

        Returns:
            The assistant's response text

        Raises:
            LLMError: On failure
        """
        start_time = time.time()
        model_name = self._get_model(model)
        input_tokens = 0
        output_tokens = 0

        async def _make_request() -> Tuple[str, int, int]:
            nonlocal input_tokens, output_tokens
            is_gpt5 = "gpt-5" in model_name
            # GPT-5 models use max_completion_tokens instead of max_tokens
            token_param = "max_completion_tokens" if is_gpt5 else "max_tokens"
            # GPT-5 models only support temperature=1
            temp_param = {} if is_gpt5 else {"temperature": temperature}

            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    **{token_param: max_tokens},
                    **temp_param,
                ),
                timeout=timeout,
            )

            # Extract token usage
            if response.usage:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

            content = response.choices[0].message.content
            if content is None:
                raise LLMResponseInvalidError(message="Empty response from LLM")
            return content

        try:
            result = await self._execute_with_retry(_make_request, "completion")
            duration_ms = int((time.time() - start_time) * 1000)

            # Log usage
            self._log_usage(
                model_id=model_name,
                model_type=model.value,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                analysis_type=analysis_type,
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                status="completed",
            )

            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self._log_usage(
                model_id=model_name,
                model_type=model.value,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                analysis_type=analysis_type,
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                status="failed",
                error_message=str(e),
            )
            raise

    async def completion_json(
        self,
        system: str,
        user: str,
        model: ModelType = ModelType.SMART,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        timeout: Optional[float] = 60.0,
        user_id: Optional[str] = None,
        analysis_type: str = "general",
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
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
            user_id: User ID for usage tracking (optional)
            analysis_type: Type of analysis for usage tracking
            entity_type: Type of entity being analyzed (e.g., 'workout')
            entity_id: ID of the entity being analyzed

        Returns:
            The parsed JSON response as a dictionary

        Raises:
            LLMError: On failure
            LLMResponseInvalidError: If response is not valid JSON
        """
        import json

        start_time = time.time()
        model_name = self._get_model(model)
        input_tokens = 0
        output_tokens = 0

        async def _make_request() -> Dict[str, Any]:
            nonlocal input_tokens, output_tokens
            is_gpt5 = "gpt-5" in model_name
            # GPT-5 models use max_completion_tokens instead of max_tokens
            token_param = "max_completion_tokens" if is_gpt5 else "max_tokens"
            # GPT-5 models only support temperature=1
            temp_param = {} if is_gpt5 else {"temperature": temperature}

            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    **{token_param: max_tokens},
                    **temp_param,
                    response_format={"type": "json_object"},
                ),
                timeout=timeout,
            )

            # Extract token usage
            if response.usage:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            # Handle truncated responses (finish_reason: length)
            if finish_reason == "length":
                self._logger.warning(
                    f"LLM response truncated (max_tokens={max_tokens}, "
                    f"output_tokens={output_tokens}). Consider increasing max_tokens."
                )
                # Try to salvage truncated JSON by attempting repairs
                if content:
                    repaired_json = self._try_repair_truncated_json(content)
                    if repaired_json is not None:
                        self._logger.info("Successfully repaired truncated JSON response")
                        return repaired_json
                # If repair failed, raise with helpful error
                raise LLMResponseInvalidError(
                    message=f"Response truncated (max_tokens={max_tokens} limit reached). "
                            f"Used {output_tokens} tokens. Increase max_tokens or simplify the prompt.",
                    details={
                        "finish_reason": finish_reason,
                        "max_tokens": max_tokens,
                        "output_tokens": output_tokens,
                        "truncated_content": content[:500] if content else None,
                    }
                )

            if content is None or content.strip() == "":
                raise LLMResponseInvalidError(
                    message=f"Empty response from LLM (finish_reason: {finish_reason})",
                    details={"finish_reason": finish_reason}
                )
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                raise LLMResponseInvalidError(
                    message=f"Invalid JSON response from LLM: {e}",
                    details={"raw_content": content[:500]},
                )

        try:
            result = await self._execute_with_retry(_make_request, "completion_json")
            duration_ms = int((time.time() - start_time) * 1000)

            # Log usage
            self._log_usage(
                model_id=model_name,
                model_type=model.value,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                analysis_type=analysis_type,
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                status="completed",
            )

            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self._log_usage(
                model_id=model_name,
                model_type=model.value,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                analysis_type=analysis_type,
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                status="failed",
                error_message=str(e),
            )
            raise

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
        user_id: Optional[str] = None,
        analysis_type: str = "general",
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Stream a completion from the LLM.

        Args:
            system: System prompt
            user: User message
            model: Model type to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            user_id: User ID for usage tracking (optional)
            analysis_type: Type of analysis for usage tracking
            entity_type: Type of entity being analyzed (e.g., 'workout')
            entity_id: ID of the entity being analyzed

        Yields:
            Chunks of the assistant's response
        """
        start_time = time.time()
        chunks_yielded = 0
        total_content = ""
        model_name = self._get_model(model)

        try:
            is_gpt5 = "gpt-5" in model_name
            # GPT-5 models use max_completion_tokens instead of max_tokens
            token_param = "max_completion_tokens" if is_gpt5 else "max_tokens"
            # GPT-5 models only support temperature=1
            temp_param = {} if is_gpt5 else {"temperature": temperature}

            stream = await self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                **{token_param: max_tokens},
                **temp_param,
                stream=True,
                stream_options={"include_usage": True},
            )

            input_tokens = 0
            output_tokens = 0

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    chunks_yielded += 1
                    content = chunk.choices[0].delta.content
                    total_content += content
                    yield content

                # Get usage from the final chunk (when stream_options includes usage)
                if hasattr(chunk, 'usage') and chunk.usage:
                    input_tokens = chunk.usage.prompt_tokens
                    output_tokens = chunk.usage.completion_tokens

            duration_ms = int((time.time() - start_time) * 1000)
            self.metrics.record_request(
                success=True,
                duration_ms=duration_ms,
            )

            # Estimate tokens if not provided (streaming doesn't always include usage)
            if output_tokens == 0:
                # Rough estimate: 4 chars per token
                output_tokens = len(total_content) // 4
            if input_tokens == 0:
                input_tokens = (len(system) + len(user)) // 4

            # Log usage
            self._log_usage(
                model_id=model_name,
                model_type=model.value,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                analysis_type=analysis_type,
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                status="completed",
            )

        except RateLimitError as e:
            self.metrics.record_request(success=False)
            duration_ms = int((time.time() - start_time) * 1000)
            self._log_usage(
                model_id=model_name,
                model_type=model.value,
                input_tokens=0,
                output_tokens=0,
                duration_ms=duration_ms,
                analysis_type=analysis_type,
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                status="failed",
                error_message="Rate limit exceeded",
            )
            raise LLMRateLimitError()
        except APIConnectionError as e:
            self.metrics.record_request(success=False)
            duration_ms = int((time.time() - start_time) * 1000)
            self._log_usage(
                model_id=model_name,
                model_type=model.value,
                input_tokens=0,
                output_tokens=0,
                duration_ms=duration_ms,
                analysis_type=analysis_type,
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                status="failed",
                error_message=str(e),
            )
            raise LLMServiceUnavailableError(message=str(e))
        except Exception as e:
            self.metrics.record_request(success=False)
            self._logger.error(f"Stream error: {e}")
            duration_ms = int((time.time() - start_time) * 1000)
            self._log_usage(
                model_id=model_name,
                model_type=model.value,
                input_tokens=0,
                output_tokens=0,
                duration_ms=duration_ms,
                analysis_type=analysis_type,
                user_id=user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                status="failed",
                error_message=str(e),
            )
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
