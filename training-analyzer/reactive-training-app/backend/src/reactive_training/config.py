"""Application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Database paths
    training_db_path: Path = Path("training.db")

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8001

    # Garmin
    garmin_max_sync_days: int = 365

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
