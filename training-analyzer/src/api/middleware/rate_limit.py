"""Rate limiting middleware for FastAPI.

Uses slowapi to implement rate limiting with support for
authenticated users (by user_id) and anonymous users (by IP).
"""

from typing import Optional

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_rate_limit_key(request: Request) -> str:
    """Get the rate limit key for a request.

    Uses user_id if authenticated (from request state), otherwise falls back
    to the client's IP address.

    Args:
        request: The FastAPI request object.

    Returns:
        A string key for rate limiting (user_id or IP address).
    """
    # Check if user is authenticated (set by auth middleware)
    user: Optional[object] = getattr(request.state, "user", None)
    if user is not None:
        user_id = getattr(user, "user_id", None)
        if user_id:
            return f"user:{user_id}"

    # Fall back to IP address for anonymous requests
    return f"ip:{get_remote_address(request)}"


# Create the limiter instance with the custom key function
limiter = Limiter(key_func=get_rate_limit_key)


# Rate limit constants for different endpoint types
RATE_LIMIT_AI = "10/minute"  # AI endpoints (analysis, chat)
RATE_LIMIT_STANDARD = "60/minute"  # Standard endpoints
