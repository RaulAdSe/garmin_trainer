"""Tests for AuthService - JWT token generation, validation, and password hashing.

This module tests:
1. Access token creation and validation
2. Refresh token creation and validation
3. Token pair creation
4. Token expiration handling
5. Token type validation
6. Password hashing with bcrypt
7. Password verification
"""

import os
import pytest
import tempfile
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import jwt

from training_analyzer.services.auth_service import (
    AuthService,
    TokenPayload,
    TokenPair,
    AuthServiceError,
    TokenExpiredError,
    InvalidTokenError,
    get_auth_service,
    create_access_token,
    create_refresh_token,
    verify_token,
    hash_password,
    verify_password,
)


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock()
    # Use a 32+ character secret to satisfy validation requirements
    settings.jwt_secret_key = "test-secret-key-for-unit-testing-only-32chars"
    settings.jwt_algorithm = "HS256"
    settings.access_token_expire_minutes = 30
    settings.refresh_token_expire_days = 7
    return settings


@pytest.fixture
def auth_service(mock_settings):
    """Create AuthService with mock settings."""
    with patch("training_analyzer.services.auth_service.get_settings", return_value=mock_settings):
        return AuthService()


class TestAuthServiceInit:
    """Tests for AuthService initialization."""

    def test_init_with_settings(self, mock_settings):
        """Should initialize with settings values."""
        with patch("training_analyzer.services.auth_service.get_settings", return_value=mock_settings):
            service = AuthService()

            assert service._secret_key == mock_settings.jwt_secret_key
            assert service._algorithm == mock_settings.jwt_algorithm
            assert service._access_token_expire_minutes == mock_settings.access_token_expire_minutes
            assert service._refresh_token_expire_days == mock_settings.refresh_token_expire_days


class TestAccessTokenCreation:
    """Tests for access token creation."""

    def test_create_access_token(self, auth_service):
        """Should create valid access token."""
        token = auth_service.create_access_token(
            user_id="user-123",
            email="test@example.com",
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_access_token_contains_claims(self, auth_service):
        """Access token should contain expected claims."""
        token = auth_service.create_access_token(
            user_id="user-123",
            email="test@example.com",
        )

        # Decode without verification to check claims
        payload = jwt.decode(
            token,
            options={"verify_signature": False},
        )

        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_access_token_with_additional_claims(self, auth_service):
        """Access token should include additional claims."""
        token = auth_service.create_access_token(
            user_id="user-123",
            email="test@example.com",
            additional_claims={"role": "admin", "tier": "pro"},
        )

        payload = jwt.decode(
            token,
            options={"verify_signature": False},
        )

        assert payload["role"] == "admin"
        assert payload["tier"] == "pro"

    def test_access_token_expiration(self, auth_service, mock_settings):
        """Access token should have correct expiration."""
        before = datetime.now(timezone.utc)
        token = auth_service.create_access_token(
            user_id="user-123",
            email="test@example.com",
        )
        after = datetime.now(timezone.utc)

        payload = jwt.decode(
            token,
            options={"verify_signature": False},
        )

        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_exp_min = before + timedelta(minutes=mock_settings.access_token_expire_minutes)
        expected_exp_max = after + timedelta(minutes=mock_settings.access_token_expire_minutes) + timedelta(seconds=1)

        # Allow 1 second tolerance for timing
        assert expected_exp_min - timedelta(seconds=1) <= exp <= expected_exp_max


class TestRefreshTokenCreation:
    """Tests for refresh token creation."""

    def test_create_refresh_token(self, auth_service):
        """Should create valid refresh token."""
        token = auth_service.create_refresh_token(user_id="user-123")

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_refresh_token_contains_claims(self, auth_service):
        """Refresh token should contain expected claims."""
        token = auth_service.create_refresh_token(user_id="user-123")

        payload = jwt.decode(
            token,
            options={"verify_signature": False},
        )

        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload
        # Refresh token should NOT contain email
        assert "email" not in payload

    def test_refresh_token_expiration(self, auth_service, mock_settings):
        """Refresh token should have correct expiration."""
        before = datetime.now(timezone.utc)
        token = auth_service.create_refresh_token(user_id="user-123")
        after = datetime.now(timezone.utc)

        payload = jwt.decode(
            token,
            options={"verify_signature": False},
        )

        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_exp_min = before + timedelta(days=mock_settings.refresh_token_expire_days)
        expected_exp_max = after + timedelta(days=mock_settings.refresh_token_expire_days) + timedelta(seconds=1)

        # Allow 1 second tolerance for timing
        assert expected_exp_min - timedelta(seconds=1) <= exp <= expected_exp_max


class TestTokenPairCreation:
    """Tests for token pair creation."""

    def test_create_token_pair(self, auth_service):
        """Should create both access and refresh tokens."""
        token_pair = auth_service.create_token_pair(
            user_id="user-123",
            email="test@example.com",
        )

        assert isinstance(token_pair, TokenPair)
        assert token_pair.access_token is not None
        assert token_pair.refresh_token is not None
        assert token_pair.token_type == "bearer"

    def test_token_pair_expires_in(self, auth_service, mock_settings):
        """Token pair should have correct expires_in value."""
        token_pair = auth_service.create_token_pair(
            user_id="user-123",
            email="test@example.com",
        )

        expected_expires_in = mock_settings.access_token_expire_minutes * 60
        assert token_pair.expires_in == expected_expires_in

    def test_token_pair_with_additional_claims(self, auth_service):
        """Token pair should pass additional claims to access token."""
        token_pair = auth_service.create_token_pair(
            user_id="user-123",
            email="test@example.com",
            additional_claims={"custom": "value"},
        )

        payload = jwt.decode(
            token_pair.access_token,
            options={"verify_signature": False},
        )

        assert payload["custom"] == "value"


class TestTokenVerification:
    """Tests for token verification."""

    def test_verify_valid_token(self, auth_service):
        """Should verify and decode valid token."""
        token = auth_service.create_access_token(
            user_id="user-123",
            email="test@example.com",
        )

        payload = auth_service.verify_token(token)

        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"

    def test_verify_token_with_expected_type(self, auth_service):
        """Should verify token type when expected_type provided."""
        access_token = auth_service.create_access_token(
            user_id="user-123",
            email="test@example.com",
        )

        # Should succeed for correct type
        payload = auth_service.verify_token(access_token, expected_type="access")
        assert payload["type"] == "access"

    def test_verify_token_wrong_type_raises(self, auth_service):
        """Should raise InvalidTokenError for wrong token type."""
        access_token = auth_service.create_access_token(
            user_id="user-123",
            email="test@example.com",
        )

        with pytest.raises(InvalidTokenError) as exc_info:
            auth_service.verify_token(access_token, expected_type="refresh")

        assert "Expected token type 'refresh'" in str(exc_info.value)

    def test_verify_access_token(self, auth_service):
        """verify_access_token should verify access tokens."""
        token = auth_service.create_access_token(
            user_id="user-123",
            email="test@example.com",
        )

        payload = auth_service.verify_access_token(token)
        assert payload["type"] == "access"

    def test_verify_access_token_rejects_refresh(self, auth_service):
        """verify_access_token should reject refresh tokens."""
        refresh_token = auth_service.create_refresh_token(user_id="user-123")

        with pytest.raises(InvalidTokenError):
            auth_service.verify_access_token(refresh_token)

    def test_verify_refresh_token(self, auth_service):
        """verify_refresh_token should verify refresh tokens."""
        token = auth_service.create_refresh_token(user_id="user-123")

        payload = auth_service.verify_refresh_token(token)
        assert payload["type"] == "refresh"

    def test_verify_refresh_token_rejects_access(self, auth_service):
        """verify_refresh_token should reject access tokens."""
        access_token = auth_service.create_access_token(
            user_id="user-123",
            email="test@example.com",
        )

        with pytest.raises(InvalidTokenError):
            auth_service.verify_refresh_token(access_token)


class TestTokenExpiration:
    """Tests for token expiration handling."""

    def test_expired_token_raises(self, mock_settings):
        """Should raise TokenExpiredError for expired token."""
        # Create service with very short expiration
        mock_settings.access_token_expire_minutes = 0  # Immediate expiration

        with patch("training_analyzer.services.auth_service.get_settings", return_value=mock_settings):
            service = AuthService()
            token = service.create_access_token(
                user_id="user-123",
                email="test@example.com",
            )

        # Token should be immediately expired
        time.sleep(0.1)  # Small delay to ensure expiration

        with pytest.raises(TokenExpiredError) as exc_info:
            service.verify_token(token)

        assert "Token has expired" in str(exc_info.value)


class TestInvalidTokenHandling:
    """Tests for invalid token handling."""

    def test_invalid_token_raises(self, auth_service):
        """Should raise InvalidTokenError for invalid token."""
        with pytest.raises(InvalidTokenError):
            auth_service.verify_token("invalid-token-string")

    def test_malformed_token_raises(self, auth_service):
        """Should raise InvalidTokenError for malformed token."""
        with pytest.raises(InvalidTokenError):
            auth_service.verify_token("not.a.valid.jwt.token")

    def test_wrong_signature_raises(self, auth_service):
        """Should raise InvalidTokenError for wrong signature."""
        # Create token with different secret
        wrong_token = jwt.encode(
            {"sub": "user-123", "type": "access"},
            "wrong-secret",
            algorithm="HS256",
        )

        with pytest.raises(InvalidTokenError):
            auth_service.verify_token(wrong_token)


class TestPasswordHashing:
    """Tests for password hashing functionality."""

    def test_hash_password(self):
        """Should hash password with bcrypt."""
        password = "secure_password_123"
        hashed = AuthService.hash_password(password)

        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_hash_password_unique(self):
        """Each hash should be unique (due to salt)."""
        password = "same_password"
        hash1 = AuthService.hash_password(password)
        hash2 = AuthService.hash_password(password)

        assert hash1 != hash2  # Different salts

    def test_verify_password_correct(self):
        """Should verify correct password."""
        password = "correct_password"
        hashed = AuthService.hash_password(password)

        assert AuthService.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Should reject incorrect password."""
        password = "correct_password"
        hashed = AuthService.hash_password(password)

        assert AuthService.verify_password("wrong_password", hashed) is False

    def test_verify_password_invalid_hash(self):
        """Should return False for invalid hash format."""
        result = AuthService.verify_password("password", "not-a-bcrypt-hash")
        assert result is False

    def test_verify_password_empty_password(self):
        """Should handle empty password."""
        hashed = AuthService.hash_password("password")
        result = AuthService.verify_password("", hashed)
        assert result is False


class TestDataclasses:
    """Tests for auth service dataclasses."""

    def test_token_payload_structure(self):
        """TokenPayload should have all required fields."""
        now = datetime.now(timezone.utc)
        payload = TokenPayload(
            sub="user-123",
            email="test@example.com",
            exp=now + timedelta(hours=1),
            iat=now,
            type="access",
        )

        assert payload.sub == "user-123"
        assert payload.email == "test@example.com"
        assert payload.type == "access"

    def test_token_pair_structure(self):
        """TokenPair should have all required fields."""
        token_pair = TokenPair(
            access_token="access.token.here",
            refresh_token="refresh.token.here",
            expires_in=1800,
        )

        assert token_pair.access_token == "access.token.here"
        assert token_pair.refresh_token == "refresh.token.here"
        assert token_pair.token_type == "bearer"
        assert token_pair.expires_in == 1800


class TestExceptions:
    """Tests for auth service exceptions."""

    def test_auth_service_error_hierarchy(self):
        """Exceptions should have correct hierarchy."""
        assert issubclass(TokenExpiredError, AuthServiceError)
        assert issubclass(InvalidTokenError, AuthServiceError)

    def test_token_expired_error_message(self):
        """TokenExpiredError should have descriptive message."""
        error = TokenExpiredError("Custom message")
        assert str(error) == "Custom message"

    def test_invalid_token_error_message(self):
        """InvalidTokenError should have descriptive message."""
        error = InvalidTokenError("Invalid token details")
        assert str(error) == "Invalid token details"


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_get_auth_service_singleton(self, monkeypatch):
        """get_auth_service should return singleton."""
        from training_analyzer.services import auth_service as auth_module

        # Reset singleton
        monkeypatch.setattr(auth_module, "_auth_service", None)

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.jwt_secret_key = "test-secret-key-for-unit-testing-only-32chars"
        mock_settings.jwt_algorithm = "HS256"
        mock_settings.access_token_expire_minutes = 30
        mock_settings.refresh_token_expire_days = 7

        with patch("training_analyzer.services.auth_service.get_settings", return_value=mock_settings):
            service1 = get_auth_service()
            service2 = get_auth_service()

            assert service1 is service2

        # Cleanup
        monkeypatch.setattr(auth_module, "_auth_service", None)

    def test_convenience_create_access_token(self, monkeypatch):
        """Module-level create_access_token should work."""
        from training_analyzer.services import auth_service as auth_module

        monkeypatch.setattr(auth_module, "_auth_service", None)

        mock_settings = MagicMock()
        mock_settings.jwt_secret_key = "test-secret-key-for-unit-testing-only-32chars"
        mock_settings.jwt_algorithm = "HS256"
        mock_settings.access_token_expire_minutes = 30
        mock_settings.refresh_token_expire_days = 7

        with patch("training_analyzer.services.auth_service.get_settings", return_value=mock_settings):
            token = create_access_token("user-123", "test@example.com")
            assert token is not None

        monkeypatch.setattr(auth_module, "_auth_service", None)

    def test_convenience_create_refresh_token(self, monkeypatch):
        """Module-level create_refresh_token should work."""
        from training_analyzer.services import auth_service as auth_module

        monkeypatch.setattr(auth_module, "_auth_service", None)

        mock_settings = MagicMock()
        mock_settings.jwt_secret_key = "test-secret-key-for-unit-testing-only-32chars"
        mock_settings.jwt_algorithm = "HS256"
        mock_settings.access_token_expire_minutes = 30
        mock_settings.refresh_token_expire_days = 7

        with patch("training_analyzer.services.auth_service.get_settings", return_value=mock_settings):
            token = create_refresh_token("user-123")
            assert token is not None

        monkeypatch.setattr(auth_module, "_auth_service", None)

    def test_convenience_verify_token(self, monkeypatch):
        """Module-level verify_token should work."""
        from training_analyzer.services import auth_service as auth_module

        monkeypatch.setattr(auth_module, "_auth_service", None)

        mock_settings = MagicMock()
        mock_settings.jwt_secret_key = "test-secret-key-for-unit-testing-only-32chars"
        mock_settings.jwt_algorithm = "HS256"
        mock_settings.access_token_expire_minutes = 30
        mock_settings.refresh_token_expire_days = 7

        with patch("training_analyzer.services.auth_service.get_settings", return_value=mock_settings):
            token = create_access_token("user-123", "test@example.com")
            payload = verify_token(token)
            assert payload["sub"] == "user-123"

        monkeypatch.setattr(auth_module, "_auth_service", None)

    def test_convenience_hash_password(self):
        """Module-level hash_password should work."""
        hashed = hash_password("password123")
        assert hashed.startswith("$2b$")

    def test_convenience_verify_password(self):
        """Module-level verify_password should work."""
        hashed = hash_password("password123")
        assert verify_password("password123", hashed) is True
        assert verify_password("wrong", hashed) is False
