"""Configuration settings for the Training Analyzer App."""

import os
from pathlib import Path
from functools import lru_cache

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

    # OpenAI
    openai_api_key: str = ""

    # Garmin Connect credentials
    garmin_email: str = ""
    garmin_password: str = ""

    # Model selection
    llm_model_fast: str = "gpt-4o-mini"  # For quick tasks
    llm_model_smart: str = "gpt-4o"  # For complex analysis

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
