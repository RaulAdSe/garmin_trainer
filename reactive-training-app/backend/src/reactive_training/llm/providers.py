"""LLM providers and model selection."""

from enum import Enum
from typing import AsyncIterator, Optional
import os

from openai import AsyncOpenAI

from ..config import get_settings


class ModelType(Enum):
    """Model types for different task complexities."""
    FAST = "fast"    # GPT-5-nano for quick tasks
    SMART = "smart"  # GPT-5-mini for complex analysis


class LLMClient:
    """Unified LLM client with model routing."""

    def __init__(self):
        settings = get_settings()
        api_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model_map = {
            ModelType.FAST: settings.llm_model_fast,   # gpt-5-nano
            ModelType.SMART: settings.llm_model_smart, # gpt-5-mini
        }

    def _get_model(self, model_type: ModelType) -> str:
        """Get the model ID for a model type."""
        return self.model_map.get(model_type, self.model_map[ModelType.SMART])

    async def completion(
        self,
        system: str,
        user: str,
        model: ModelType = ModelType.SMART,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        """
        Get a completion from the LLM.

        Args:
            system: System prompt
            user: User message
            model: Model type to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            The assistant's response text
        """
        response = await self.client.chat.completions.create(
            model=self._get_model(model),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return response.choices[0].message.content or ""

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
                yield chunk.choices[0].delta.content


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get the LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
