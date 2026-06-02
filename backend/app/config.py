"""Application configuration via environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "Expense Bill Analyzer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database (MariaDB)
    DATABASE_URL: str = (
        "mysql+aiomysql://billuser:billpass@mariadb:3306/billanalyser"
    )
    DATABASE_SYNC_URL: str = (
        "mysql+pymysql://billuser:billpass@mariadb:3306/billanalyser"
    )

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # File uploads
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: set[str] = {"jpg", "jpeg", "png", "pdf"}

    # Redis / Celery
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # LLM
    LLM_PROVIDER: Literal["openai", "ollama"] = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.2"

    # Vector store
    CHROMA_PERSIST_DIR: str = "/app/data/chroma"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    DUPLICATE_SIMILARITY_THRESHOLD: float = 0.85

    # OCR
    TESSERACT_CMD: str = "/usr/bin/tesseract"
    OCR_MIN_CONFIDENCE: float = 0.3

    # Rate limiting
    RATE_LIMIT: str = "100/minute"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
