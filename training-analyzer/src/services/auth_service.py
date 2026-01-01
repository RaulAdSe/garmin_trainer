"""Authentication service for JWT token management and password hashing.

This module provides local development authentication utilities.
In production, Supabase Auth handles authentication.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from pydantic import BaseModel

from ..config import get_settings


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    sub: str  # user_id
    email: str
    exp: datetime
    iat: datetime
    type: str  # "access" or "refresh"


class TokenPair(BaseModel):
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class AuthServiceError(Exception):
    """Base exception for auth service errors."""

    pass


class TokenExpiredError(AuthServiceError):
    """Raised when a token has expired."""

    pass


class InvalidTokenError(AuthServiceError):
    """Raised when a token is invalid."""

    pass


class AuthService:
    """Service for handling authentication operations.

    Provides JWT token creation/validation and password hashing.
    For local development - production uses Supabase Auth.
    """

    def __init__(self) -> None:
        """Initialize auth service with settings."""
        settings = get_settings()
        self._secret_key = settings.jwt_secret_key
        self._algorithm = settings.jwt_algorithm
        self._access_token_expire_minutes = settings.access_token_expire_minutes
        self._refresh_token_expire_days = settings.refresh_token_expire_days

    def create_access_token(
        self,
        user_id: str,
        email: str,
        additional_claims: dict[str, Any] | None = None,
    ) -> str:
        """Create a JWT access token.

        Args:
            user_id: The user's unique identifier.
            email: The user's email address.
            additional_claims: Optional additional claims to include in the token.

        Returns:
            Encoded JWT access token string.
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self._access_token_expire_minutes)

        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": now,
            "type": "access",
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """Create a JWT refresh token.

        Args:
            user_id: The user's unique identifier.

        Returns:
            Encoded JWT refresh token string.
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self._refresh_token_expire_days)

        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": now,
            "type": "refresh",
        }

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_token_pair(
        self,
        user_id: str,
        email: str,
        additional_claims: dict[str, Any] | None = None,
    ) -> TokenPair:
        """Create both access and refresh tokens.

        Args:
            user_id: The user's unique identifier.
            email: The user's email address.
            additional_claims: Optional additional claims for the access token.

        Returns:
            TokenPair containing access and refresh tokens.
        """
        access_token = self.create_access_token(user_id, email, additional_claims)
        refresh_token = self.create_refresh_token(user_id)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._access_token_expire_minutes * 60,
        )

    def verify_token(self, token: str, expected_type: str | None = None) -> dict[str, Any]:
        """Verify and decode a JWT token.

        Args:
            token: The JWT token string to verify.
            expected_type: Optional expected token type ("access" or "refresh").

        Returns:
            Decoded token payload as a dictionary.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid or type mismatch.
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )

            if expected_type and payload.get("type") != expected_type:
                raise InvalidTokenError(
                    f"Expected token type '{expected_type}', got '{payload.get('type')}'"
                )

            return payload

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {e}")

    def verify_access_token(self, token: str) -> dict[str, Any]:
        """Verify an access token.

        Args:
            token: The JWT access token to verify.

        Returns:
            Decoded token payload.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid.
        """
        return self.verify_token(token, expected_type="access")

    def verify_refresh_token(self, token: str) -> dict[str, Any]:
        """Verify a refresh token.

        Args:
            token: The JWT refresh token to verify.

        Returns:
            Decoded token payload.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid.
        """
        return self.verify_token(token, expected_type="refresh")

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: The plaintext password to hash.

        Returns:
            The bcrypt hash as a string.
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify a password against a bcrypt hash.

        Args:
            password: The plaintext password to verify.
            hashed_password: The bcrypt hash to compare against.

        Returns:
            True if the password matches, False otherwise.
        """
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except Exception:
            return False


# Module-level convenience functions
_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    """Get or create the auth service singleton."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


def create_access_token(user_id: str, email: str) -> str:
    """Create a JWT access token.

    Args:
        user_id: The user's unique identifier.
        email: The user's email address.

    Returns:
        Encoded JWT access token string.
    """
    return get_auth_service().create_access_token(user_id, email)


def create_refresh_token(user_id: str) -> str:
    """Create a JWT refresh token.

    Args:
        user_id: The user's unique identifier.

    Returns:
        Encoded JWT refresh token string.
    """
    return get_auth_service().create_refresh_token(user_id)


def verify_token(token: str) -> dict[str, Any]:
    """Verify and decode a JWT token.

    Args:
        token: The JWT token string to verify.

    Returns:
        Decoded token payload as a dictionary.

    Raises:
        TokenExpiredError: If the token has expired.
        InvalidTokenError: If the token is invalid.
    """
    return get_auth_service().verify_token(token)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        The bcrypt hash as a string.
    """
    return AuthService.hash_password(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash.

    Args:
        password: The plaintext password to verify.
        hashed_password: The bcrypt hash to compare against.

    Returns:
        True if the password matches, False otherwise.
    """
    return AuthService.verify_password(password, hashed_password)
