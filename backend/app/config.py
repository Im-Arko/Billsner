"""Application configuration via environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
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

    # Database (MariaDB / local development)
    # Use port 3307 when MariaDB runs via `docker compose up -d mariadb`
    DATABASE_URL: str = (
        "mysql+aiomysql://billuser:billpass@localhost:3307/billanalyser"
    )
    DATABASE_SYNC_URL: str = (
        "mysql+pymysql://billuser:billpass@localhost:3307/billanalyser"
    )

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # File uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: set[str] = {"jpg", "jpeg", "png", "pdf"}

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # LLM
    LLM_PROVIDER: Literal["", "groq", "ollama"] = ""
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str  | None = None
    OLLAMA_BASE_URL: str | None = None
    OLLAMA_MODEL: str | None = None
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_PARSER_TIMEOUT_SECONDS: int = 15

    # Vector store
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    DUPLICATE_SIMILARITY_THRESHOLD: float = 0.85

    # Background task safety
    BILL_PROCESSING_TIMEOUT_SECONDS: int = 590
    DB_OPERATION_TIMEOUT_SECONDS: int = 30

    # OCR
    POPPLER_PATH: str | None = None
    TESSERACT_CMD: str | None = None
    OCR_MIN_CONFIDENCE: float = 0.3

    # Rate limiting
    RATE_LIMIT: str = "100/minute"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod", "false", "0", "no", "off"}:
                return False
            if normalized in {"debug", "development", "dev", "true", "1", "yes", "on"}:
                return True
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
