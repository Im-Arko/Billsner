"""Application configuration via environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "Expense Bill Analyzer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Embedded database: no database server is required.
    DATABASE_URL: str = f"sqlite+aiosqlite:///{(DATA_DIR / 'billanalyser.db').as_posix()}"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # File uploads
    UPLOAD_DIR: str = str(BACKEND_DIR / "uploads")
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: set[str] = {"jpg", "jpeg", "png", "pdf"}

    # LLM
    LLM_PROVIDER: Literal["groq"] = "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_PARSER_TIMEOUT_SECONDS: int = 15

    # Embedded text similarity index; no downloaded model is required.
    SEARCH_INDEX_PATH: str = str(DATA_DIR / "search.db")
    DUPLICATE_SIMILARITY_THRESHOLD: float = 0.85

    # Background task safety
    BILL_PROCESSING_TIMEOUT_SECONDS: int = 590
    DB_OPERATION_TIMEOUT_SECONDS: int = 30
    WORKER_POLL_SECONDS: float = 1.0

    # OCR
    POPPLER_PATH: str | None = None
    TESSERACT_CMD: str | None = None
    OCR_MIN_CONFIDENCE: float = 0.3

    # Rate limiting
    RATE_LIMIT: str = "100/minute"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def resolve_database_path(cls, value: str) -> str:
        prefix = "sqlite+aiosqlite:///"
        if value.startswith(prefix) and value[len(prefix):] != ":memory:":
            path = Path(value[len(prefix):])
            if not path.is_absolute():
                value = prefix + (BACKEND_DIR / path).resolve().as_posix()
        return value

    @field_validator("UPLOAD_DIR", "SEARCH_INDEX_PATH", mode="before")
    @classmethod
    def resolve_local_path(cls, value: str) -> str:
        path = Path(value)
        return str(path if path.is_absolute() else (BACKEND_DIR / path).resolve())

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
