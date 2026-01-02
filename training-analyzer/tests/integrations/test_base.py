"""Tests for integration base classes."""

import pytest
from datetime import datetime, timedelta
from training_analyzer.integrations.base import (
    AuthenticationError,
    IntegrationError,
    OAuthCredentials,
    RateLimitError,
)


class TestIntegrationError:
    """Tests for IntegrationError."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = IntegrationError("Something went wrong")

        assert str(error) == "Something went wrong"
        assert error.provider == ""
        assert error.code is None

    def test_error_with_provider(self):
        """Test error with provider info."""
        error = IntegrationError(
            "API call failed",
            provider="strava",
            code="api_error",
        )

        assert error.provider == "strava"
        assert error.code == "api_error"


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_rate_limit_error(self):
        """Test rate limit error."""
        error = RateLimitError(
            "Rate limit exceeded",
            provider="strava",
            retry_after=900,
        )

        assert error.provider == "strava"
        assert error.code == "rate_limit"
        assert error.retry_after == 900


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_auth_error(self):
        """Test authentication error."""
        error = AuthenticationError("Token expired", "garmin")

        assert error.provider == "garmin"
        assert "Token expired" in str(error)


class TestOAuthCredentials:
    """Tests for OAuthCredentials."""

    def test_basic_credentials(self):
        """Test basic credentials creation."""
        creds = OAuthCredentials(
            provider="strava",
            access_token="test_token",
        )

        assert creds.provider == "strava"
        assert creds.access_token == "test_token"
        assert creds.token_type == "Bearer"

    def test_full_credentials(self):
        """Test credentials with all fields."""
        expires = datetime.now() + timedelta(hours=6)

        creds = OAuthCredentials(
            provider="strava",
            access_token="access_token",
            refresh_token="refresh_token",
            expires_at=expires,
            token_type="Bearer",
            scope="read_all,activity:read",
            user_id="12345",
            user_name="Test User",
        )

        assert creds.refresh_token == "refresh_token"
        assert creds.expires_at == expires
        assert creds.scope == "read_all,activity:read"
        assert creds.user_id == "12345"

    def test_is_expired_no_expiry(self):
        """Test is_expired with no expiry set."""
        creds = OAuthCredentials(
            provider="test",
            access_token="token",
        )

        assert creds.is_expired is False

    def test_is_expired_future(self):
        """Test is_expired with future expiry."""
        creds = OAuthCredentials(
            provider="test",
            access_token="token",
            expires_at=datetime.now() + timedelta(hours=6),
        )

        assert creds.is_expired is False

    def test_is_expired_past(self):
        """Test is_expired with past expiry."""
        creds = OAuthCredentials(
            provider="test",
            access_token="token",
            expires_at=datetime.now() - timedelta(hours=1),
        )

        assert creds.is_expired is True

    def test_is_expired_within_buffer(self):
        """Test is_expired within 5 minute buffer."""
        creds = OAuthCredentials(
            provider="test",
            access_token="token",
            expires_at=datetime.now() + timedelta(minutes=3),  # Within 5 min buffer
        )

        assert creds.is_expired is True

    def test_needs_refresh_with_token(self):
        """Test needs_refresh with refresh token."""
        creds = OAuthCredentials(
            provider="test",
            access_token="token",
            refresh_token="refresh",
            expires_at=datetime.now() - timedelta(hours=1),
        )

        assert creds.needs_refresh is True

    def test_needs_refresh_no_token(self):
        """Test needs_refresh without refresh token."""
        creds = OAuthCredentials(
            provider="test",
            access_token="token",
            expires_at=datetime.now() - timedelta(hours=1),
        )

        assert creds.needs_refresh is False

    def test_to_dict(self):
        """Test serialization to dict."""
        creds = OAuthCredentials(
            provider="strava",
            access_token="access",
            refresh_token="refresh",
            expires_at=datetime(2024, 1, 15, 12, 0),
            user_id="123",
            user_name="Test",
        )

        data = creds.to_dict()

        assert data["provider"] == "strava"
        assert data["access_token"] == "access"
        assert data["refresh_token"] == "refresh"
        assert data["expires_at"] == "2024-01-15T12:00:00"
        assert data["user_id"] == "123"

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "provider": "garmin",
            "access_token": "token",
            "refresh_token": "refresh",
            "expires_at": "2024-01-15T12:00:00",
            "token_type": "Bearer",
            "scope": "read",
            "user_id": "456",
            "user_name": "User",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-10T00:00:00",
        }

        creds = OAuthCredentials.from_dict(data)

        assert creds.provider == "garmin"
        assert creds.access_token == "token"
        assert creds.refresh_token == "refresh"
        assert creds.expires_at == datetime(2024, 1, 15, 12, 0)
        assert creds.user_id == "456"

    def test_from_dict_minimal(self):
        """Test deserialization from minimal dict."""
        data = {
            "provider": "test",
            "access_token": "token",
        }

        creds = OAuthCredentials.from_dict(data)

        assert creds.provider == "test"
        assert creds.access_token == "token"
        assert creds.refresh_token is None
        assert creds.expires_at is None



