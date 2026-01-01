"""Tests for token counting utilities."""

import pytest


class TestTokenCounter:
    """Test suite for token counting functions."""

    def test_count_tokens_simple_words(self):
        """Test token counting for simple words."""
        from src.utils.token_counter import count_tokens

        # "hello" is 1 token in cl100k_base
        assert count_tokens("hello") == 1

        # "hello world" is 2 tokens
        assert count_tokens("hello world") == 2

    def test_count_tokens_empty_string(self):
        """Test token counting for empty string."""
        from src.utils.token_counter import count_tokens

        assert count_tokens("") == 0

    def test_count_tokens_longer_text(self):
        """Test token counting for longer text."""
        from src.utils.token_counter import count_tokens

        # A typical sentence should have multiple tokens
        text = "The quick brown fox jumps over the lazy dog."
        tokens = count_tokens(text)

        # This sentence is typically 10 tokens
        assert tokens > 5
        assert tokens < 20

    def test_count_message_tokens_single_message(self):
        """Test counting tokens in a single message."""
        from src.utils.token_counter import count_message_tokens

        messages = [{"role": "user", "content": "hello"}]
        tokens = count_message_tokens(messages)

        # 1 token for "hello" + 4 overhead + 2 assistant priming = 7
        assert tokens == 7

    def test_count_message_tokens_multiple_messages(self):
        """Test counting tokens in multiple messages."""
        from src.utils.token_counter import count_message_tokens

        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]
        tokens = count_message_tokens(messages)

        # Each message has 4 token overhead, plus content tokens, plus 2 priming
        # Should be > 10 tokens
        assert tokens > 10

    def test_count_message_tokens_empty_list(self):
        """Test counting tokens for empty message list."""
        from src.utils.token_counter import count_message_tokens

        # Just the assistant priming tokens
        assert count_message_tokens([]) == 2

    def test_count_message_tokens_multimodal(self):
        """Test counting tokens for multimodal content."""
        from src.utils.token_counter import count_message_tokens

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "hello"},
                    {"type": "image", "url": "..."},  # Should be skipped
                ],
            }
        ]
        tokens = count_message_tokens(messages)

        # 1 token for "hello" + 4 overhead + 2 priming = 7
        assert tokens == 7

    def test_estimate_cost_sonnet(self):
        """Test cost estimation for Claude Sonnet."""
        from src.utils.token_counter import estimate_cost

        # 1000 input tokens + 500 output tokens
        cost = estimate_cost(1000, 500, "claude-sonnet-4-20250514")

        # Input: 1000/1M * $3 = $0.003
        # Output: 500/1M * $15 = $0.0075
        # Total: $0.0105
        assert abs(cost - 0.0105) < 0.0001

    def test_estimate_cost_opus(self):
        """Test cost estimation for Claude Opus."""
        from src.utils.token_counter import estimate_cost

        cost = estimate_cost(1000, 500, "claude-opus-4-20250514")

        # Input: 1000/1M * $15 = $0.015
        # Output: 500/1M * $75 = $0.0375
        # Total: $0.0525
        assert abs(cost - 0.0525) < 0.0001

    def test_estimate_cost_haiku(self):
        """Test cost estimation for Claude Haiku."""
        from src.utils.token_counter import estimate_cost

        cost = estimate_cost(1000, 500, "claude-haiku-3-5-20241022")

        # Input: 1000/1M * $0.25 = $0.00025
        # Output: 500/1M * $1.25 = $0.000625
        # Total: $0.000875
        assert abs(cost - 0.000875) < 0.0001

    def test_estimate_cost_unknown_model(self):
        """Test cost estimation falls back to Sonnet for unknown models."""
        from src.utils.token_counter import estimate_cost

        cost = estimate_cost(1000, 500, "unknown-model")

        # Should use Sonnet pricing
        assert abs(cost - 0.0105) < 0.0001

    def test_get_encoding_cached(self):
        """Test that encoding is cached."""
        from src.utils.token_counter import get_encoding

        encoding1 = get_encoding()
        encoding2 = get_encoding()

        # Should be the same object (cached)
        assert encoding1 is encoding2
