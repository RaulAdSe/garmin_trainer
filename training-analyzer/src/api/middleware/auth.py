"""Authentication middleware for FastAPI.

Provides dependency injection for user authentication in API routes.
For local development - production uses Supabase Auth.
"""

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ...services.auth_service import (
    AuthService,
    InvalidTokenError,
    TokenExpiredError,
    get_auth_service,
)


# Security scheme for Bearer token authentication
security = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    """Represents the currently authenticated user.

    Attributes:
        user_id: Unique identifier for the user.
        email: User's email address.
        subscription_tier: User's subscription tier (default: 'free').
        is_admin: Whether the user has admin privileges.
    """

    user_id: str
    email: str
    subscription_tier: str = "free"
    is_admin: bool = False

    @property
    def id(self) -> str:
        """Alias for user_id for compatibility."""
        return self.user_id


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> CurrentUser:
    """FastAPI dependency to get the current authenticated user.

    Extracts the JWT token from the Authorization header, validates it,
    and returns a CurrentUser object with user information.

    Args:
        credentials: HTTP Bearer credentials from the Authorization header.
        auth_service: The authentication service for token validation.

    Returns:
        CurrentUser object with user information from the token.

    Raises:
        HTTPException (401): If no token is provided or token is invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = auth_service.verify_access_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        user_id=payload["sub"],
        email=payload["email"],
        subscription_tier=payload.get("subscription_tier", "free"),
        is_admin=payload.get("is_admin", False),
    )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> Optional[CurrentUser]:
    """FastAPI dependency to optionally get the current authenticated user.

    Similar to get_current_user, but returns None instead of raising an
    exception when authentication fails. Useful for endpoints that support
    both authenticated and anonymous access.

    Args:
        credentials: HTTP Bearer credentials from the Authorization header.
        auth_service: The authentication service for token validation.

    Returns:
        CurrentUser object if authenticated, None otherwise.
    """
    if credentials is None:
        return None

    token = credentials.credentials

    try:
        payload = auth_service.verify_access_token(token)
    except (TokenExpiredError, InvalidTokenError):
        return None

    return CurrentUser(
        user_id=payload["sub"],
        email=payload["email"],
        subscription_tier=payload.get("subscription_tier", "free"),
        is_admin=payload.get("is_admin", False),
    )


async def require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """FastAPI dependency to require admin privileges.

    Args:
        current_user: The currently authenticated user.

    Returns:
        CurrentUser object if user is an admin.

    Raises:
        HTTPException (403): If user is not an admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


async def require_subscription(
    required_tier: str = "pro",
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """FastAPI dependency factory to require a specific subscription tier.

    Args:
        required_tier: The minimum required subscription tier.
        current_user: The currently authenticated user.

    Returns:
        CurrentUser object if user has required subscription.

    Raises:
        HTTPException (402): If user's subscription tier is insufficient.
    """
    tier_levels = {"free": 0, "pro": 1, "enterprise": 2}

    user_level = tier_levels.get(current_user.subscription_tier, 0)
    required_level = tier_levels.get(required_tier, 0)

    if user_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"This feature requires a {required_tier} subscription. "
            f"Current tier: {current_user.subscription_tier}",
        )
    return current_user


def get_require_subscription(required_tier: str):
    """Create a dependency that requires a specific subscription tier.

    Args:
        required_tier: The minimum required subscription tier.

    Returns:
        A FastAPI dependency function.

    Example:
        @router.get("/premium-feature")
        async def premium_feature(
            current_user: CurrentUser = Depends(get_require_subscription("pro"))
        ):
            ...
    """

    async def dependency(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        return await require_subscription(required_tier, current_user)

    return dependency
