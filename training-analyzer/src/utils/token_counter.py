"""Token counting utilities using tiktoken.

Provides accurate token counting for Claude models using the cl100k_base encoding.
Falls back to character-based approximation if tiktoken is unavailable.
"""

import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Claude uses cl100k_base encoding (same as GPT-4)
ENCODING_NAME = "cl100k_base"


@lru_cache(maxsize=1)
def get_encoding():
    """Get the tiktoken encoding (cached).

    Returns:
        tiktoken.Encoding or None if unavailable
    """
    try:
        import tiktoken

        return tiktoken.get_encoding(ENCODING_NAME)
    except ImportError:
        logger.warning("tiktoken not installed, using character-based approximation")
        return None
    except Exception as e:
        logger.warning(f"Failed to load tiktoken encoding: {e}")
        return None


def count_tokens(text: str) -> int:
    """Count tokens in a string using tiktoken.

    Args:
        text: The text to count tokens in

    Returns:
        Number of tokens in the text
    """
    if not text:
        return 0

    encoding = get_encoding()
    if encoding is None:
        # Fallback to approximation
        return len(text) // 4

    try:
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"Error encoding text: {e}")
        return len(text) // 4


def count_message_tokens(messages: List[Dict[str, Any]]) -> int:
    """Count tokens in a list of chat messages.

    Accounts for message overhead (role tokens, delimiters).

    Args:
        messages: List of message dicts with 'role' and 'content' keys

    Returns:
        Total token count including overhead
    """
    total = 0

    for msg in messages:
        # Each message has overhead for role tokens
        # <|im_start|>role\n ... <|im_end|>\n
        total += 4

        content = msg.get("content", "")
        if isinstance(content, str):
            total += count_tokens(content)
        elif isinstance(content, list):
            # Handle multimodal content
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    total += count_tokens(part.get("text", ""))

    # Assistant priming tokens
    total += 2

    return total


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "claude-sonnet-4-20250514",
) -> float:
    """Estimate cost in USD based on token counts.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model ID for pricing lookup

    Returns:
        Estimated cost in USD
    """
    # Pricing per 1M tokens (as of 2025)
    PRICING = {
        # Anthropic Claude
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
        "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
        "claude-haiku-3-5-20241022": {"input": 0.25, "output": 1.25},
        # OpenAI GPT-5 (2025)
        "gpt-5": {"input": 1.25, "output": 10.0},
        "gpt-5-mini": {"input": 0.25, "output": 2.0},      # Great for agentic tasks
        "gpt-5-nano": {"input": 0.05, "output": 0.40},     # Ultra cheap for simple tasks
        # OpenAI GPT-4o (legacy)
        "gpt-4o": {"input": 2.5, "output": 10.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    }

    # Default to gpt-5-mini pricing if unknown
    prices = PRICING.get(model, PRICING["gpt-5-mini"])
    input_cost = (input_tokens / 1_000_000) * prices["input"]
    output_cost = (output_tokens / 1_000_000) * prices["output"]

    return input_cost + output_cost
