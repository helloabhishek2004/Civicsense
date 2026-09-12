from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/civicsense"

    # API Configuration
    API_ENV: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Security & Limits
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8081",
        "http://localhost:19006",
    ]
    MAX_PAYLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    UPLOADS_DIR: str = "uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
