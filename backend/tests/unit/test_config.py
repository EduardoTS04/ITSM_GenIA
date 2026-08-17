"""Unit tests for the centralized Settings object.

`_env_file=None` keeps these deterministic: a developer's real backend/.env must
not change the outcome.
"""

import pytest

from app.core.config import Settings, settings

ENV_VARS = [
    "DATABASE_URL", "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_TIMEOUT_SECONDS",
    "OLLAMA_MAX_RETRIES", "OLLAMA_RETRY_BACKOFF_SECONDS",
    "CORS_ALLOWED_ORIGINS", "LOG_LEVEL", "APP_ENV", "AUTO_CREATE_SCHEMA",
]


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_defaults_match_the_previous_inline_values(clean_env):
    fresh = Settings(_env_file=None)

    assert fresh.DATABASE_URL == "sqlite:///./data/itsm.db"
    assert fresh.OLLAMA_BASE_URL == "http://localhost:11434"
    assert fresh.OLLAMA_MODEL == "llama3.2"
    assert fresh.OLLAMA_TIMEOUT_SECONDS == 60.0
    assert fresh.OLLAMA_MAX_RETRIES == 2
    assert fresh.OLLAMA_RETRY_BACKOFF_SECONDS == 0.5
    assert fresh.CORS_ALLOWED_ORIGINS == ["http://localhost:5173", "http://localhost:3000"]
    assert fresh.LOG_LEVEL == "INFO"
    assert fresh.APP_ENV == "development"
    # Off by default: Alembic owns the schema, not the app.
    assert fresh.AUTO_CREATE_SCHEMA is False


def test_no_setting_is_required(clean_env):
    """Every field has a default, so an env-less container still boots."""
    assert Settings(_env_file=None) is not None


@pytest.mark.parametrize("name,value", [
    ("DATABASE_URL", "sqlite:////app/data/itsm.db"),
    ("OLLAMA_BASE_URL", "http://host.docker.internal:11434"),
    ("OLLAMA_MODEL", "mistral-small"),
    ("LOG_LEVEL", "DEBUG"),
    ("APP_ENV", "production"),
])
def test_environment_overrides_the_default(clean_env, monkeypatch, name, value):
    monkeypatch.setenv(name, value)

    assert getattr(Settings(_env_file=None), name) == value


@pytest.mark.parametrize("name,raw,expected", [
    ("OLLAMA_TIMEOUT_SECONDS", "5", 5.0),
    ("OLLAMA_MAX_RETRIES", "0", 0),
    ("OLLAMA_RETRY_BACKOFF_SECONDS", "1.5", 1.5),
])
def test_ollama_client_knobs_are_coerced_to_numbers(clean_env, monkeypatch, name, raw, expected):
    monkeypatch.setenv(name, raw)

    value = getattr(Settings(_env_file=None), name)

    assert value == expected
    assert isinstance(value, type(expected))


@pytest.mark.parametrize("raw,expected", [("true", True), ("1", True), ("false", False), ("0", False)])
def test_auto_create_schema_accepts_the_usual_boolean_spellings(clean_env, monkeypatch, raw, expected):
    monkeypatch.setenv("AUTO_CREATE_SCHEMA", raw)

    assert Settings(_env_file=None).AUTO_CREATE_SCHEMA is expected


def test_env_var_names_are_case_insensitive(clean_env, monkeypatch):
    monkeypatch.setenv("database_url", "sqlite:///./other.db")

    assert Settings(_env_file=None).DATABASE_URL == "sqlite:///./other.db"


def test_docker_compose_values_are_accepted(clean_env, monkeypatch):
    """The exact values docker-compose.yml passes must still validate."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:////app/data/itsm.db")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")

    fresh = Settings(_env_file=None)

    assert fresh.DATABASE_URL == "sqlite:////app/data/itsm.db"
    assert fresh.OLLAMA_BASE_URL == "http://host.docker.internal:11434"


# ── CORS list parsing ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("*", ["*"]),
    ("http://localhost:5173", ["http://localhost:5173"]),
    ("http://localhost:5173,https://itsm.example.com", ["http://localhost:5173", "https://itsm.example.com"]),
    (" http://a , http://b ", ["http://a", "http://b"]),
    ('["http://a", "http://b"]', ["http://a", "http://b"]),
])
def test_cors_origins_accept_comma_separated_and_json(clean_env, monkeypatch, raw, expected):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", raw)

    assert Settings(_env_file=None).CORS_ALLOWED_ORIGINS == expected


# ── Singleton ──────────────────────────────────────────────────────────────────

def test_module_exposes_a_ready_to_use_singleton():
    assert isinstance(settings, Settings)
    assert settings.OLLAMA_MODEL == "llama3.2"
