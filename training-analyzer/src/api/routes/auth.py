"""Authentication API routes.

Provides endpoints for user registration, login, token refresh, and user info.
For local development - production uses Supabase Auth.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from ..middleware.auth import CurrentUser, get_current_user
from ..middleware.rate_limit import limiter
from ...services.auth_service import (
    AuthService,
    InvalidTokenError,
    TokenExpiredError,
    TokenPair,
    get_auth_service,
    hash_password,
    verify_password,
)
from ...services.feature_gate import (
    get_feature_gate_service,
)


router = APIRouter(prefix="/auth", tags=["auth"])


# In-memory user store for local development
# In production, this would be replaced with database queries
_users: dict[str, dict] = {}


def _init_dev_user() -> None:
    """Initialize a default dev user for local development."""
    from datetime import datetime, timezone
    dev_user_id = "dev-user-123"
    if dev_user_id not in _users:
        _users[dev_user_id] = {
            "id": dev_user_id,
            "email": "dev@example.com",
            "password_hash": hash_password("devpassword123"),
            "display_name": "Dev User",
            "subscription_tier": "pro",
            "is_admin": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }


# Initialize dev user on module load
_init_dev_user()


# Request/Response Models
class RegisterRequest(BaseModel):
    """Request model for user registration."""

    email: EmailStr
    password: str = Field(min_length=8, description="Password must be at least 8 characters")
    display_name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    """Request model for user login."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Request model for token refresh."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """Response model for user information."""

    id: str
    email: str
    display_name: str | None
    subscription_tier: str
    is_admin: bool
    created_at: str


class UsageResponse(BaseModel):
    """Response model for feature usage information."""

    feature: str
    current_usage: int
    limit: int | None
    period: str
    remaining: int | None
    is_limited: bool


class MeResponse(BaseModel):
    """Response model for current user information with usage."""

    user: UserResponse
    usage: dict[str, UsageResponse]


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register(
    request: Request,
    register_request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Register a new user account.

    Creates a new user with the provided email and password,
    and returns authentication tokens.

    Note: This is for local development. In production, Supabase Auth handles registration.
    """
    # Check if user already exists
    email_lower = register_request.email.lower()
    for user in _users.values():
        if user["email"].lower() == email_lower:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )

    # Create new user
    user_id = str(uuid.uuid4())
    password_hash = hash_password(register_request.password)

    user = {
        "id": user_id,
        "email": email_lower,
        "password_hash": password_hash,
        "display_name": register_request.display_name,
        "subscription_tier": "free",
        "is_admin": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    _users[user_id] = user

    # Generate tokens
    token_pair = auth_service.create_token_pair(
        user_id=user_id,
        email=user["email"],
        additional_claims={"subscription_tier": user["subscription_tier"]},
    )

    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    login_request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate a user and return tokens.

    Validates the provided email and password, and returns
    access and refresh tokens if successful.

    Note: This is for local development. In production, Supabase Auth handles login.
    """
    # Find user by email
    email_lower = login_request.email.lower()
    user = None
    for u in _users.values():
        if u["email"].lower() == email_lower:
            user = u
            break

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    if not verify_password(login_request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Generate tokens
    token_pair = auth_service.create_token_pair(
        user_id=user["id"],
        email=user["email"],
        additional_claims={
            "subscription_tier": user["subscription_tier"],
            "is_admin": user["is_admin"],
        },
    )

    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh(
    request: Request,
    refresh_request: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Refresh an access token using a refresh token.

    Takes a valid refresh token and returns a new access token
    and optionally a new refresh token.
    """
    try:
        payload = auth_service.verify_refresh_token(refresh_request.refresh_token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please log in again.",
        )
    except InvalidTokenError as e:
        import logging
        logging.getLogger(__name__).error(f"Invalid refresh token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token. Please log in again.",
        )

    user_id = payload["sub"]

    # Get user from store
    user = _users.get(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Generate new tokens
    token_pair = auth_service.create_token_pair(
        user_id=user["id"],
        email=user["email"],
        additional_claims={
            "subscription_tier": user["subscription_tier"],
            "is_admin": user["is_admin"],
        },
    )

    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
    )


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
) -> MeResponse:
    """Get information about the currently authenticated user.

    Returns user profile information and current feature usage.
    """
    # Get user from store
    user = _users.get(current_user.user_id)

    if user is None:
        # If user is not in local store (e.g., token from previous session),
        # create a minimal user response from token data
        user = {
            "id": current_user.user_id,
            "email": current_user.email,
            "display_name": None,
            "subscription_tier": current_user.subscription_tier,
            "is_admin": current_user.is_admin,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    # Get usage summary
    feature_gate = get_feature_gate_service()
    usage_summary = feature_gate.get_usage_summary(
        user_id=current_user.user_id,
        subscription_tier=current_user.subscription_tier,
    )

    usage_response = {}
    for feature_name, summary in usage_summary.items():
        usage_response[feature_name] = UsageResponse(
            feature=feature_name,
            current_usage=summary.current_usage,
            limit=summary.limit,
            period=summary.period,
            remaining=summary.remaining,
            is_limited=summary.is_limited,
        )

    return MeResponse(
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            display_name=user.get("display_name"),
            subscription_tier=user["subscription_tier"],
            is_admin=user["is_admin"],
            created_at=user["created_at"],
        ),
        usage=usage_response,
    )


@router.get("/features")
async def get_features(
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Get feature availability for the current user's subscription tier.

    Returns information about which features are available and their limits.
    """
    feature_gate = get_feature_gate_service()
    return {
        "subscription_tier": current_user.subscription_tier,
        "features": feature_gate.get_feature_availability(current_user.subscription_tier),
    }
