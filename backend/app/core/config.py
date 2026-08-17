"""Centralized, validated application settings.

This is the only module allowed to read the environment. Everything else takes
its configuration from the `settings` singleton exported at the bottom.
"""

import json
from typing import Annotated, Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # SQLAlchemy connection string. The container mounts ./data, hence the path.
    DATABASE_URL: str = "sqlite:///./data/itsm.db"

    # Base URL of the Ollama server exposing /api/chat.
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Model tag the agent pipeline asks Ollama for.
    OLLAMA_MODEL: str = "llama3.2"

    # Per-request timeout for a single Ollama call, in seconds.
    OLLAMA_TIMEOUT_SECONDS: float = 60.0

    # Extra attempts after the first one, for timeouts and connection errors only.
    OLLAMA_MAX_RETRIES: int = 2

    # First backoff delay in seconds; doubles on every retry.
    OLLAMA_RETRY_BACKOFF_SECONDS: float = 0.5

    # Origins allowed by the CORS middleware; defaults to local frontend origins.
    # NoDecode keeps pydantic-settings from JSON-decoding the raw env value, so
    # the validator below can also accept a plain comma-separated list.
    CORS_ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # Verbosity for application logging. Not wired into logging config yet.
    LOG_LEVEL: str = "INFO"

    # Deployment environment name, e.g. development / staging / production.
    APP_ENV: str = "development"

    # Dev-only escape hatch: create missing tables from the ORM models at startup.
    # Off by default because Alembic owns the schema (see backend/MIGRATIONS.md).
    AUTO_CREATE_SCHEMA: bool = False

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, value: Any) -> Any:
        """Accept either a JSON array or a plain comma-separated list."""
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                return json.loads(text)
            return [item.strip() for item in text.split(",") if item.strip()]
        return value

    @field_validator("CORS_ALLOWED_ORIGINS")
    @classmethod
    def reject_wildcard_origins(cls, value: list[str]) -> list[str]:
        """Wildcard origins are invalid with allow_credentials=True (see main.py)."""
        if "*" in value:
            raise ValueError(
                "CORS_ALLOWED_ORIGINS cannot contain '*' when allow_credentials is True."
            )
        return value


settings = Settings()
