"""API middleware modules."""

from .auth import (
    CurrentUser,
    get_current_user,
    get_optional_user,
)
from .rate_limit import (
    limiter,
    get_rate_limit_key,
    RATE_LIMIT_AI,
    RATE_LIMIT_STANDARD,
)
from .quota import (
    require_quota,
    get_quota_status,
    QuotaExceededError,
    FeatureDisabledError,
)
from .security_headers import SecurityHeadersMiddleware

__all__ = [
    "CurrentUser",
    "get_current_user",
    "get_optional_user",
    "limiter",
    "get_rate_limit_key",
    "RATE_LIMIT_AI",
    "RATE_LIMIT_STANDARD",
    "require_quota",
    "get_quota_status",
    "QuotaExceededError",
    "FeatureDisabledError",
    "SecurityHeadersMiddleware",
]
