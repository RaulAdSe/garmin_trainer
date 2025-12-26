"""
Base classes for external integrations.

Provides common OAuth flow and integration patterns.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
import secrets


class IntegrationError(Exception):
    """Base exception for integration errors."""
    
    def __init__(self, message: str, provider: str = "", code: Optional[str] = None):
        self.provider = provider
        self.code = code
        super().__init__(message)


class OAuthError(IntegrationError):
    """OAuth-specific error."""
    pass


class RateLimitError(IntegrationError):
    """Rate limit exceeded."""
    
    def __init__(
        self,
        message: str,
        provider: str,
        retry_after: Optional[int] = None,
    ):
        self.retry_after = retry_after
        super().__init__(message, provider, "rate_limit")


class AuthenticationError(IntegrationError):
    """Authentication failed or expired."""
    pass


@dataclass
class OAuthCredentials:
    """
    OAuth credentials for an integration.
    """
    provider: str
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    token_type: str = "Bearer"
    scope: Optional[str] = None
    
    # User info from provider
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        # Add 5 minute buffer
        return datetime.now() >= (self.expires_at - timedelta(minutes=5))
    
    @property
    def needs_refresh(self) -> bool:
        """Check if token needs refresh."""
        return self.is_expired and self.refresh_token is not None
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "provider": self.provider,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "token_type": self.token_type,
            "scope": self.scope,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "OAuthCredentials":
        """Deserialize from dictionary."""
        return cls(
            provider=data["provider"],
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            token_type=data.get("token_type", "Bearer"),
            scope=data.get("scope"),
            user_id=data.get("user_id"),
            user_name=data.get("user_name"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
        )


class OAuthFlow(ABC):
    """
    Abstract base class for OAuth 2.0 flows.
    """
    
    provider: str = "base"
    authorize_url: str = ""
    token_url: str = ""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scope: Optional[str] = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope
        self._state: Optional[str] = None
    
    def generate_state(self) -> str:
        """Generate a random state token for CSRF protection."""
        self._state = secrets.token_urlsafe(32)
        return self._state
    
    def validate_state(self, state: str) -> bool:
        """Validate the state token."""
        return self._state is not None and secrets.compare_digest(self._state, state)
    
    @abstractmethod
    def get_authorization_url(self) -> str:
        """
        Get the authorization URL to redirect user to.
        
        Returns:
            Full authorization URL with query parameters.
        """
        pass
    
    @abstractmethod
    async def exchange_code(self, code: str) -> OAuthCredentials:
        """
        Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from callback.
        
        Returns:
            OAuth credentials with access and refresh tokens.
        """
        pass
    
    @abstractmethod
    async def refresh_token(self, credentials: OAuthCredentials) -> OAuthCredentials:
        """
        Refresh an expired access token.
        
        Args:
            credentials: Existing credentials with refresh token.
        
        Returns:
            Updated credentials with new access token.
        """
        pass


class IntegrationClient(ABC):
    """
    Abstract base class for integration API clients.
    """
    
    provider: str = "base"
    base_url: str = ""
    
    def __init__(self, credentials: OAuthCredentials):
        self.credentials = credentials
    
    @property
    def is_authenticated(self) -> bool:
        """Check if client has valid credentials."""
        return self.credentials is not None and not self.credentials.is_expired
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers for API requests."""
        return {
            "Authorization": f"{self.credentials.token_type} {self.credentials.access_token}",
        }
    
    @abstractmethod
    async def get_user_profile(self) -> Dict[str, Any]:
        """Get the authenticated user's profile."""
        pass
    
    @abstractmethod
    async def get_activities(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get user's activities within a date range."""
        pass

