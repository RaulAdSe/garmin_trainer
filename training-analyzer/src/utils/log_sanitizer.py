"""Log sanitization filter to prevent credential/PII leakage in logs.

This module provides a logging filter that redacts sensitive information
before it is written to logs, preventing accidental exposure of:
- API keys (OpenAI, Strava, Stripe, etc.)
- Bearer tokens and authorization headers
- Passwords and secrets
- Email addresses
- Credit card numbers
- JWT tokens
- Fernet encryption keys

Usage:
    from utils.log_sanitizer import install_log_sanitizer

    # Apply to all loggers at application startup
    install_log_sanitizer()
"""

import logging
import re
from typing import Any


class LogSanitizationFilter(logging.Filter):
    """Logging filter that redacts sensitive information from log messages.

    This filter processes log records before they are emitted and redacts
    patterns that could expose credentials, PII, or other sensitive data.
    """

    # Patterns to redact with their replacement text
    # Order matters - more specific patterns should come before general ones
    PATTERNS: list[tuple[re.Pattern, str]] = [
        # Anthropic API keys (sk-ant-...) - must come before OpenAI pattern
        (re.compile(r'\bsk-ant-[a-zA-Z0-9-]{20,}'), '[REDACTED_ANTHROPIC_KEY]'),

        # OpenAI API keys (sk-...)
        (re.compile(r'\bsk-[a-zA-Z0-9]{20,}'), '[REDACTED_OPENAI_KEY]'),

        # Stripe keys (sk_live_, sk_test_, pk_live_, pk_test_) - must come before generic sk_ pattern
        (re.compile(r'\b[sp]k_(live|test)_[a-zA-Z0-9]{20,}'), '[REDACTED_STRIPE_KEY]'),

        # Generic secret keys with sk_ prefix
        (re.compile(r'\bsk_[a-zA-Z0-9_]{20,}'), '[REDACTED_SECRET_KEY]'),

        # Stripe webhook secrets (whsec_...)
        (re.compile(r'\bwhsec_[a-zA-Z0-9]{20,}'), '[REDACTED_STRIPE_WEBHOOK]'),

        # JWT tokens (three base64-encoded segments separated by dots) - before Bearer
        (re.compile(r'\beyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+'), '[REDACTED_JWT]'),

        # Bearer tokens in Authorization headers
        (re.compile(r'Bearer\s+[a-zA-Z0-9_\-\.]+', re.IGNORECASE), 'Bearer [REDACTED_TOKEN]'),

        # Authorization header values (generic)
        (re.compile(r'(Authorization["\']?\s*[:=]\s*["\']?)[^"\'&\s]+', re.IGNORECASE), r'\1[REDACTED]'),

        # Fernet keys (44 character base64 strings ending in =, supports URL-safe base64)
        # Note: \b word boundary doesn't work with + and / so we use lookahead/lookbehind
        (re.compile(r'(?<![A-Za-z0-9+/_=-])[A-Za-z0-9+/_-]{43}=(?![A-Za-z0-9+/_=-])'), '[REDACTED_FERNET_KEY]'),

        # Password fields in various formats
        (re.compile(r'(password["\']?\s*[:=]\s*["\']?)[^"\'&\s]+', re.IGNORECASE), r'\1[REDACTED]'),
        (re.compile(r'(passwd["\']?\s*[:=]\s*["\']?)[^"\'&\s]+', re.IGNORECASE), r'\1[REDACTED]'),
        (re.compile(r'(pwd["\']?\s*[:=]\s*["\']?)[^"\'&\s]+', re.IGNORECASE), r'\1[REDACTED]'),

        # Secret fields
        (re.compile(r'(secret["\']?\s*[:=]\s*["\']?)[^"\'&\s]+', re.IGNORECASE), r'\1[REDACTED]'),
        (re.compile(r'(api_key["\']?\s*[:=]\s*["\']?)[^"\'&\s]+', re.IGNORECASE), r'\1[REDACTED]'),
        (re.compile(r'(apikey["\']?\s*[:=]\s*["\']?)[^"\'&\s]+', re.IGNORECASE), r'\1[REDACTED]'),

        # Token fields
        (re.compile(r'(access_token["\']?\s*[:=]\s*["\']?)[^"\'&\s]+', re.IGNORECASE), r'\1[REDACTED]'),
        (re.compile(r'(refresh_token["\']?\s*[:=]\s*["\']?)[^"\'&\s]+', re.IGNORECASE), r'\1[REDACTED]'),
        (re.compile(r'(token["\']?\s*[:=]\s*["\']?)[^"\'&\s]+', re.IGNORECASE), r'\1[REDACTED]'),

        # Credit card numbers (13-19 digits, possibly with spaces/dashes)
        (re.compile(r'\b(?:\d[ -]*?){13,19}\b'), '[REDACTED_CARD]'),

        # Email addresses
        (re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'), '[REDACTED_EMAIL]'),

        # Garmin credentials pattern
        (re.compile(r'(garmin_password["\']?\s*[:=]\s*["\']?)[^"\'&\s]+', re.IGNORECASE), r'\1[REDACTED]'),
        (re.compile(r'(garmin_email["\']?\s*[:=]\s*["\']?)[^"\'&\s]+', re.IGNORECASE), r'\1[REDACTED]'),

        # Strava client secret
        (re.compile(r'(client_secret["\']?\s*[:=]\s*["\']?)[^"\'&\s]+', re.IGNORECASE), r'\1[REDACTED]'),

        # OAuth code (in URLs or params)
        (re.compile(r'(code["\']?\s*[:=]\s*["\']?)[a-zA-Z0-9_-]{20,}', re.IGNORECASE), r'\1[REDACTED]'),

        # Generic long hex strings that might be tokens (32+ chars)
        (re.compile(r'\b[a-fA-F0-9]{32,}\b'), '[REDACTED_HEX_TOKEN]'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and sanitize the log record.

        Args:
            record: The log record to process.

        Returns:
            True to allow the record to be logged (after sanitization).
        """
        # Sanitize the main message
        if record.msg:
            record.msg = self._sanitize(str(record.msg))

        # Sanitize args if they're strings
        if record.args:
            record.args = self._sanitize_args(record.args)

        return True

    def _sanitize(self, text: str) -> str:
        """Apply all sanitization patterns to the text.

        Args:
            text: The text to sanitize.

        Returns:
            The sanitized text with sensitive data redacted.
        """
        for pattern, replacement in self.PATTERNS:
            text = pattern.sub(replacement, text)
        return text

    def _sanitize_args(self, args: Any) -> Any:
        """Recursively sanitize log arguments.

        Args:
            args: The arguments to sanitize (can be tuple, list, dict, or str).

        Returns:
            The sanitized arguments.
        """
        if isinstance(args, str):
            return self._sanitize(args)
        elif isinstance(args, tuple):
            return tuple(self._sanitize_args(arg) for arg in args)
        elif isinstance(args, list):
            return [self._sanitize_args(arg) for arg in args]
        elif isinstance(args, dict):
            return {k: self._sanitize_args(v) for k, v in args.items()}
        else:
            # Convert to string and sanitize if it's a primitive type
            str_val = str(args)
            sanitized = self._sanitize(str_val)
            # Only return sanitized string if it changed, otherwise return original
            return sanitized if sanitized != str_val else args


def install_log_sanitizer(logger_name: str | None = None) -> None:
    """Install the log sanitization filter on loggers.

    Args:
        logger_name: If provided, install only on the named logger.
                    If None, install on the root logger to catch all logs.
    """
    sanitizer = LogSanitizationFilter()

    if logger_name:
        target_logger = logging.getLogger(logger_name)
        target_logger.addFilter(sanitizer)
    else:
        # Install on root logger
        root_logger = logging.getLogger()
        root_logger.addFilter(sanitizer)

        # Also install on all existing handlers
        for handler in root_logger.handlers:
            handler.addFilter(sanitizer)


def get_sanitization_filter() -> LogSanitizationFilter:
    """Get a new instance of the sanitization filter.

    Returns:
        A LogSanitizationFilter instance for custom use.
    """
    return LogSanitizationFilter()


def sanitize_string(text: str) -> str:
    """Sanitize a string without using the logging system.

    This is useful for sanitizing data before it's logged or
    for use in error messages that might be returned to clients.

    Args:
        text: The text to sanitize.

    Returns:
        The sanitized text with sensitive data redacted.
    """
    sanitizer = LogSanitizationFilter()
    return sanitizer._sanitize(text)
