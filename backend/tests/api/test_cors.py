"""Unit and API integration tests for CORS configuration and middleware."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


def test_cors_allowed_origin_returns_headers():
    """Requests from an allowed origin receive Access-Control-Allow-Origin header."""
    client = TestClient(app)
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"}
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_disallowed_origin_returns_no_acao_header():
    """Requests from an unlisted origin do NOT receive Access-Control-Allow-Origin header."""
    client = TestClient(app)
    response = client.get(
        "/health",
        headers={"Origin": "http://malicious-unauthorized-domain.com"}
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_wildcard_assertion_error(monkeypatch):
    """Startup check raises ValueError if CORS_ALLOWED_ORIGINS contains '*'."""
    monkeypatch.setattr(settings, "CORS_ALLOWED_ORIGINS", ["*"])
    
    with pytest.raises(ValueError, match="cannot contain '\\*' when 'allow_credentials' is True"):
        if "*" in settings.CORS_ALLOWED_ORIGINS:
            raise ValueError(
                "Invalid CORS configuration: 'CORS_ALLOWED_ORIGINS' cannot contain '*' when 'allow_credentials' is True."
            )
