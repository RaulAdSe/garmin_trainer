"""Configuration settings for the Reactive Training App."""

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # OpenAI
    openai_api_key: str = ""

    # Model selection
    llm_model_fast: str = "gpt-5-nano"  # For quick tasks
    llm_model_smart: str = "gpt-5-mini"  # For complex analysis

    # Database paths (relative to project root)
    project_root: Path = Path(__file__).parent.parent.parent.parent.parent
    training_db_path: Path | None = None
    wellness_db_path: Path | None = None
    n8n_db_path: Path | None = None

    def model_post_init(self, __context) -> None:
        """Set default database paths after initialization."""
        if self.training_db_path is None:
            self.training_db_path = self.project_root / "training-analyzer" / "training.db"
        if self.wellness_db_path is None:
            self.wellness_db_path = self.project_root / "whoop-dashboard" / "wellness.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
