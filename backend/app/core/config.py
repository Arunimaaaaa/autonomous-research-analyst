from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Autonomous Research Analyst"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # API Security
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "dev-insecure-key-change-in-production"

    # Google Gemini LLM
    GEMINI_API_KEY: Optional[str] = None
    DEFAULT_LLM_MODEL: str = "gemini-1.5-flash"
    DEFAULT_EMBEDDING_MODEL: str = "models/text-embedding-004"

    # Database
    # Defaults to SQLite async for hassle-free local development
    DATABASE_URL: str = "sqlite+aiosqlite:///./research_analyst.db"

    # SEC Edgar
    SEC_EDGAR_USER_AGENT: str = "ResearchAnalyst sample@domain.com"

    # Artifacts & Storage
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    ARTIFACTS_DIR: Path = BASE_DIR / "artifacts"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure artifacts directory exists
settings.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
