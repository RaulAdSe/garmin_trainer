"""Configuration settings for the trAIner App."""

import os
from pathlib import Path
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


# Path calculations:
# __file__ = training-analyzer/src/config.py
# .parent = training-analyzer/src/
# .parent.parent = training-analyzer/
# .parent.parent.parent = garmin_insights/ (project root)
PACKAGE_ROOT = Path(__file__).parent.parent  # training-analyzer/
PROJECT_ROOT = PACKAGE_ROOT.parent  # garmin_insights/


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"]
    cors_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_headers: list[str] = ["Authorization", "Content-Type", "Accept"]

    # OpenAI
    openai_api_key: str = ""

    # Garmin Connect credentials
    garmin_email: str = ""
    garmin_password: str = ""

    # Model selection
    llm_model_fast: str = "gpt-5-nano"  # For quick tasks
    llm_model_smart: str = "gpt-5-mini"  # For complex analysis

    # Strava OAuth settings
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_redirect_uri: str = "http://localhost:3000/auth/strava/callback"
    strava_webhook_verify_token: str = ""

    # Stripe payment settings
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id_pro_monthly: str = ""
    stripe_price_id_pro_yearly: str = ""

    # Credential encryption for Garmin auto-sync
    # Generate a Fernet key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
    credential_encryption_key: str = Field(
        default="",
        description=(
            "Fernet encryption key for securing stored Garmin credentials. "
            "Must be a valid base64-encoded 32-byte key (44 characters). "
            "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        ),
    )

    # Garmin auto-sync settings
    garmin_sync_enabled: bool = True
    garmin_sync_hour: int = 6  # UTC hour for daily sync (6 AM)

    # Data retention settings (in days)
    retention_sessions_days: int = 30  # Expired user sessions
    retention_ai_usage_logs_days: int = 90  # AI usage logs
    retention_sync_history_days: int = 90  # Garmin sync history
    retention_activity_data_days: int = 730  # Activity data (2 years, 0 = keep forever)
    retention_cleanup_enabled: bool = True  # Enable automatic cleanup
    retention_cleanup_hour: int = 3  # UTC hour for daily cleanup (3 AM)

    # Privacy settings (GDPR compliance)
    # IP address logging in user sessions - can be disabled for GDPR compliance
    # When disabled, IP addresses will not be stored in user_sessions table
    privacy_log_ip_addresses: bool = True

    # Security headers settings
    # Enable HSTS only in production (requires HTTPS)
    security_enable_hsts: bool = False
    security_hsts_max_age: int = 31536000  # 1 year in seconds
    security_hsts_include_subdomains: bool = True
    security_hsts_preload: bool = False
    # Content Security Policy - restrictive default for API
    # Override for different environments if needed
    security_csp: str = "default-src 'none'; frame-ancestors 'none'"

    # JWT Authentication settings (for local dev - production uses Supabase Auth)
    # Generate a secure secret with: python -c 'import secrets; print(secrets.token_urlsafe(32))'
    jwt_secret_key: str = Field(
        ...,
        description=(
            "JWT secret key for signing tokens. Must be at least 32 characters. "
            "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        ),
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        """Validate JWT secret key is secure.

        Checks:
        1. Not the default insecure value
        2. At least 32 characters long
        3. Sufficient entropy (at least 10 unique characters)
        """
        if v == "dev-secret-key-change-in-production":
            raise ValueError(
                "JWT secret key cannot be the default insecure value. "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        if len(v) < 32:
            raise ValueError(
                f"JWT secret key must be at least 32 characters (got {len(v)}). "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        # Entropy check: require at least 10 unique characters
        # This prevents low-entropy keys like "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        min_unique_chars = 10
        unique_chars = len(set(v))
        if unique_chars < min_unique_chars:
            raise ValueError(
                f"JWT secret key has insufficient entropy: only {unique_chars} unique characters "
                f"(minimum {min_unique_chars} required). A secure key should have high character diversity. "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        return v

    @field_validator("credential_encryption_key")
    @classmethod
    def validate_credential_encryption_key(cls, v: str) -> str:
        """Validate Fernet encryption key format if provided."""
        import base64

        if not v:
            # Empty string is allowed - encryption service handles missing key errors
            return v

        # Fernet keys are base64-encoded 32-byte keys, resulting in 44 characters
        if len(v) != 44:
            raise ValueError(
                f"Credential encryption key must be exactly 44 characters (got {len(v)}). "
                "Generate a valid Fernet key with: "
                "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        # Validate it's valid base64 and decodes to 32 bytes
        try:
            decoded = base64.urlsafe_b64decode(v)
            if len(decoded) != 32:
                raise ValueError(
                    f"Credential encryption key must decode to 32 bytes (got {len(decoded)}). "
                    "Generate a valid Fernet key with: "
                    "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(
                f"Credential encryption key is not valid base64: {e}. "
                "Generate a valid Fernet key with: "
                "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            ) from e

        return v

    # Database paths
    project_root: Path = PROJECT_ROOT
    training_db_path: Path | None = None
    wellness_db_path: Path | None = None
    n8n_db_path: Path | None = None

    def model_post_init(self, __context) -> None:
        """Set default database paths after initialization."""
        if self.training_db_path is None:
            self.training_db_path = PACKAGE_ROOT / "training.db"
        if self.wellness_db_path is None:
            self.wellness_db_path = self.project_root / "whoop-dashboard" / "wellness.db"

    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
