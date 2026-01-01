"""Tests for log sanitization filter.

Tests verify that sensitive data patterns are properly redacted
from log messages to prevent credential/PII leakage.
"""

import logging
import pytest
from io import StringIO

from src.utils.log_sanitizer import (
    LogSanitizationFilter,
    install_log_sanitizer,
    get_sanitization_filter,
    sanitize_string,
)


class TestLogSanitizationFilter:
    """Test cases for LogSanitizationFilter."""

    @pytest.fixture
    def sanitizer(self) -> LogSanitizationFilter:
        """Create a sanitization filter instance."""
        return LogSanitizationFilter()

    # --- API Key Tests ---

    def test_redacts_openai_api_key(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that OpenAI API keys are redacted."""
        text = "Using API key sk-1234567890abcdefghijklmnopqrstuvwxyz"
        result = sanitizer._sanitize(text)
        assert "sk-1234567890" not in result
        assert "[REDACTED_OPENAI_KEY]" in result

    def test_redacts_anthropic_api_key(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that Anthropic API keys are redacted."""
        text = "Using API key sk-ant-api03-1234567890abcdefghijklmnopqrstuvwxyz"
        result = sanitizer._sanitize(text)
        assert "sk-ant-api03" not in result
        assert "[REDACTED_ANTHROPIC_KEY]" in result

    def test_redacts_stripe_live_key(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that Stripe live secret keys are redacted."""
        # Using clearly fake key pattern to avoid GitHub secret scanning
        text = "Stripe key: sk_live_" + "X" * 24
        result = sanitizer._sanitize(text)
        assert "sk_live_" not in result
        assert "[REDACTED_STRIPE_KEY]" in result

    def test_redacts_stripe_test_key(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that Stripe test secret keys are redacted."""
        # Using clearly fake key pattern to avoid GitHub secret scanning
        text = "Stripe key: sk_test_" + "X" * 24
        result = sanitizer._sanitize(text)
        assert "sk_test_" not in result
        assert "[REDACTED_STRIPE_KEY]" in result

    def test_redacts_stripe_webhook_secret(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that Stripe webhook secrets are redacted."""
        # When used with "secret:", the secret pattern matches first
        text = "whsec_1234567890abcdefghijklmnopqrstuvwxyz"
        result = sanitizer._sanitize(text)
        assert "whsec_1234567890" not in result
        assert "[REDACTED_STRIPE_WEBHOOK]" in result

    # --- Bearer Token Tests ---

    def test_redacts_bearer_token(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that Bearer tokens are redacted."""
        # Without "Authorization:" prefix to avoid that pattern matching first
        text = "Bearer some_access_token_12345"
        result = sanitizer._sanitize(text)
        assert "some_access_token_12345" not in result
        assert "Bearer [REDACTED_TOKEN]" in result

    def test_redacts_bearer_token_case_insensitive(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that Bearer tokens are redacted regardless of case."""
        text = "BEARER some_token_value_here"
        result = sanitizer._sanitize(text)
        assert "some_token_value_here" not in result
        assert "Bearer [REDACTED_TOKEN]" in result

    # --- JWT Token Tests ---

    def test_redacts_jwt_token(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that JWT tokens are redacted."""
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        text = f"JWT: {jwt}"
        result = sanitizer._sanitize(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "[REDACTED_JWT]" in result

    # --- Password Tests ---

    def test_redacts_password_field(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that password fields are redacted."""
        text = "password=mysecretpassword123"
        result = sanitizer._sanitize(text)
        assert "mysecretpassword123" not in result
        assert "password=[REDACTED]" in result

    def test_redacts_password_in_json(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that passwords in JSON-like strings are redacted."""
        text = '{"password": "secret123"}'
        result = sanitizer._sanitize(text)
        assert "secret123" not in result
        assert "[REDACTED]" in result

    def test_redacts_passwd_field(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that passwd fields are redacted."""
        text = "passwd=mysecretpassword"
        result = sanitizer._sanitize(text)
        assert "mysecretpassword" not in result
        assert "passwd=[REDACTED]" in result

    # --- Token Field Tests ---

    def test_redacts_access_token_field(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that access_token fields are redacted."""
        text = "access_token=abc123def456ghi789"
        result = sanitizer._sanitize(text)
        assert "abc123def456ghi789" not in result
        assert "access_token=[REDACTED]" in result

    def test_redacts_refresh_token_field(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that refresh_token fields are redacted."""
        text = "refresh_token=xyz789abc123"
        result = sanitizer._sanitize(text)
        assert "xyz789abc123" not in result
        assert "refresh_token=[REDACTED]" in result

    # --- Email Tests ---

    def test_redacts_email_address(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that email addresses are redacted."""
        text = "User email: john.doe@example.com logged in"
        result = sanitizer._sanitize(text)
        assert "john.doe@example.com" not in result
        assert "[REDACTED_EMAIL]" in result

    def test_redacts_multiple_emails(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that multiple email addresses are redacted."""
        text = "Sending to user1@test.com and user2@example.org"
        result = sanitizer._sanitize(text)
        assert "user1@test.com" not in result
        assert "user2@example.org" not in result
        assert result.count("[REDACTED_EMAIL]") == 2

    # --- Credit Card Tests ---

    def test_redacts_credit_card_number(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that credit card numbers are redacted."""
        text = "Card: 4111111111111111"
        result = sanitizer._sanitize(text)
        assert "4111111111111111" not in result
        assert "[REDACTED_CARD]" in result

    def test_redacts_credit_card_with_spaces(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that credit cards with spaces are redacted."""
        text = "Card: 4111 1111 1111 1111"
        result = sanitizer._sanitize(text)
        assert "4111 1111 1111 1111" not in result
        assert "[REDACTED_CARD]" in result

    def test_redacts_credit_card_with_dashes(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that credit cards with dashes are redacted."""
        text = "Card: 4111-1111-1111-1111"
        result = sanitizer._sanitize(text)
        assert "4111-1111-1111-1111" not in result
        assert "[REDACTED_CARD]" in result

    # --- Fernet Key Tests ---

    def test_redacts_fernet_key(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that Fernet encryption keys are redacted."""
        # A valid Fernet key is 44 characters, base64 encoded (standard base64)
        fernet_key = "ZmDfcTF7+60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
        text = f"Using key: {fernet_key}"
        result = sanitizer._sanitize(text)
        assert fernet_key not in result
        assert "[REDACTED_FERNET_KEY]" in result

    def test_redacts_fernet_key_urlsafe(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that URL-safe Fernet encryption keys are redacted."""
        # URL-safe base64 uses - and _ instead of + and /
        fernet_key = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
        text = f"Using key: {fernet_key}"
        result = sanitizer._sanitize(text)
        assert fernet_key not in result
        assert "[REDACTED_FERNET_KEY]" in result

    # --- Garmin Credential Tests ---

    def test_redacts_garmin_password(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that Garmin passwords are redacted."""
        text = "garmin_password=mysecretgarminpwd"
        result = sanitizer._sanitize(text)
        assert "mysecretgarminpwd" not in result
        assert "garmin_password=[REDACTED]" in result

    def test_redacts_garmin_email(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that Garmin emails are redacted."""
        text = "garmin_email=user@garmin.com"
        result = sanitizer._sanitize(text)
        # Both patterns should match - garmin_email pattern and email pattern
        assert "user@garmin.com" not in result

    # --- Client Secret Tests ---

    def test_redacts_client_secret(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that OAuth client secrets are redacted."""
        text = "client_secret=abcdef123456789ghijklmnop"
        result = sanitizer._sanitize(text)
        assert "abcdef123456789ghijklmnop" not in result
        assert "client_secret=[REDACTED]" in result

    # --- OAuth Code Tests ---

    def test_redacts_oauth_code(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that OAuth authorization codes are redacted."""
        text = "code=abcdef1234567890ghijklmnopqrstuvwxyz"
        result = sanitizer._sanitize(text)
        assert "abcdef1234567890ghijklmnopqrstuvwxyz" not in result
        assert "code=[REDACTED]" in result

    # --- Hex Token Tests ---

    def test_redacts_long_hex_strings(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that long hex strings (potential tokens) are redacted."""
        hex_token = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"  # 32 chars
        text = f"Session id: {hex_token}"
        result = sanitizer._sanitize(text)
        assert hex_token not in result
        assert "[REDACTED_HEX_TOKEN]" in result

    # --- Mixed Content Tests ---

    def test_preserves_non_sensitive_content(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that non-sensitive content is preserved."""
        text = "User completed 5km run in 25 minutes"
        result = sanitizer._sanitize(text)
        assert result == text

    def test_handles_mixed_content(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that mixed content is properly handled."""
        text = "User john@example.com ran 5km with API key sk-12345678901234567890"
        result = sanitizer._sanitize(text)
        assert "5km" in result  # Preserved
        assert "john@example.com" not in result  # Redacted
        assert "sk-12345678901234567890" not in result  # Redacted

    def test_handles_empty_string(self, sanitizer: LogSanitizationFilter) -> None:
        """Test that empty strings are handled."""
        result = sanitizer._sanitize("")
        assert result == ""


class TestLogSanitizationFilterWithLogging:
    """Test log sanitization in actual logging context."""

    @pytest.fixture
    def log_capture(self) -> tuple[logging.Logger, StringIO]:
        """Set up a logger with a string buffer handler."""
        logger = logging.getLogger("test_sanitizer")
        logger.setLevel(logging.DEBUG)

        # Clear existing handlers
        logger.handlers = []

        # Create string buffer for capturing logs
        buffer = StringIO()
        handler = logging.StreamHandler(buffer)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter("%(message)s"))

        # Add sanitization filter
        sanitizer = LogSanitizationFilter()
        handler.addFilter(sanitizer)

        logger.addHandler(handler)

        return logger, buffer

    def test_filter_sanitizes_log_message(
        self, log_capture: tuple[logging.Logger, StringIO]
    ) -> None:
        """Test that log messages are sanitized."""
        logger, buffer = log_capture

        logger.info("Using API key sk-1234567890abcdefghij")
        output = buffer.getvalue()

        assert "sk-1234567890" not in output
        assert "[REDACTED_OPENAI_KEY]" in output

    def test_filter_sanitizes_log_with_format_args(
        self, log_capture: tuple[logging.Logger, StringIO]
    ) -> None:
        """Test that log format arguments are sanitized."""
        logger, buffer = log_capture

        logger.info("Email: %s", "user@example.com")
        output = buffer.getvalue()

        assert "user@example.com" not in output
        assert "[REDACTED_EMAIL]" in output

    def test_filter_sanitizes_multiple_args(
        self, log_capture: tuple[logging.Logger, StringIO]
    ) -> None:
        """Test that multiple format arguments are sanitized."""
        logger, buffer = log_capture

        logger.info(
            "User %s authenticated with token %s",
            "admin@company.com",
            "sk-secrettoken1234567890"
        )
        output = buffer.getvalue()

        assert "admin@company.com" not in output
        assert "sk-secrettoken" not in output


class TestSanitizeString:
    """Test the standalone sanitize_string function."""

    def test_sanitizes_api_key(self) -> None:
        """Test that sanitize_string works for API keys."""
        text = "API key: sk-1234567890abcdefghijklmnop"
        result = sanitize_string(text)
        assert "sk-1234567890" not in result
        assert "[REDACTED_OPENAI_KEY]" in result

    def test_sanitizes_email(self) -> None:
        """Test that sanitize_string works for emails."""
        text = "Contact: user@domain.com"
        result = sanitize_string(text)
        assert "user@domain.com" not in result
        assert "[REDACTED_EMAIL]" in result


class TestInstallLogSanitizer:
    """Test the install_log_sanitizer function."""

    def test_installs_on_root_logger(self) -> None:
        """Test that sanitizer is installed on root logger."""
        # Get root logger state before
        root_logger = logging.getLogger()
        initial_filter_count = len(root_logger.filters)

        # Install sanitizer
        install_log_sanitizer()

        # Should have one more filter
        assert len(root_logger.filters) == initial_filter_count + 1

        # Clean up - remove the filter we added
        for f in root_logger.filters:
            if isinstance(f, LogSanitizationFilter):
                root_logger.removeFilter(f)
                break

    def test_installs_on_named_logger(self) -> None:
        """Test that sanitizer is installed on named logger."""
        test_logger = logging.getLogger("test_named_logger")
        initial_filter_count = len(test_logger.filters)

        install_log_sanitizer("test_named_logger")

        assert len(test_logger.filters) == initial_filter_count + 1

        # Clean up
        for f in test_logger.filters:
            if isinstance(f, LogSanitizationFilter):
                test_logger.removeFilter(f)
                break


class TestGetSanitizationFilter:
    """Test the get_sanitization_filter function."""

    def test_returns_filter_instance(self) -> None:
        """Test that function returns a LogSanitizationFilter instance."""
        filter_instance = get_sanitization_filter()
        assert isinstance(filter_instance, LogSanitizationFilter)

    def test_returns_new_instance_each_call(self) -> None:
        """Test that each call returns a new instance."""
        filter1 = get_sanitization_filter()
        filter2 = get_sanitization_filter()
        assert filter1 is not filter2
