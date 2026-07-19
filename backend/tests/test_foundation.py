"""API tests for Milestone 1.2 backend foundation."""

from __future__ import annotations

import pytest
from app.core.config import Settings, clear_settings_cache
from app.core.exceptions import ErrorCode, NotFoundError
from app.db.session import clear_engine_cache
from app.main import create_app
from fastapi.testclient import TestClient
from pydantic import ValidationError


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv(
        "DATABASE_URL",
        "sqlite:///:memory:",
    )
    clear_settings_cache()
    clear_engine_cache()
    app = create_app(Settings(app_env="test", database_url="sqlite:///:memory:"))
    with TestClient(app) as test_client:
        yield test_client
    clear_settings_cache()
    clear_engine_cache()


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert body["errors"] == []
    assert "meta" in body
    assert response.headers.get("X-Request-ID")
    assert response.headers.get("X-Process-Time")


def test_ready_ok(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ready"
    assert body["data"]["checks"]["settings"] == "ok"


def test_api_v1_ping(client: TestClient) -> None:
    response = client.get("/api/v1/ping")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["message"] == "pong"
    assert body["data"]["api"] == "/api/v1"
    assert body["errors"] == []


def test_openapi_docs_available(client: TestClient) -> None:
    docs = client.get("/docs")
    assert docs.status_code == 200
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    schema = openapi.json()
    assert schema["info"]["title"] == "Industrial Brain AI"
    paths = schema["paths"]
    assert "/health" in paths
    assert "/ready" in paths
    assert "/api/v1/ping" in paths


def test_request_id_echo(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "test-req-123"})
    assert response.headers["X-Request-ID"] == "test-req-123"
    assert response.json()["meta"]["request_id"] == "test-req-123"


def test_app_error_envelope(client: TestClient) -> None:
    @client.app.get("/api/v1/_boom")
    def _boom() -> None:
        raise NotFoundError(
            "Motor not found",
            error_code=ErrorCode.ASSET_NOT_FOUND,
            details={"asset_id": "m-1"},
        )

    response = client.get("/api/v1/_boom")
    assert response.status_code == 404
    body = response.json()
    assert body["data"] is None
    assert body["errors"][0]["code"] == "ASSET_NOT_FOUND"
    assert body["errors"][0]["message"] == "Motor not found"


def test_validation_error_envelope(client: TestClient) -> None:
    @client.app.get("/api/v1/_validate/{item_id}")
    def _validate(item_id: int) -> dict:
        return {"item_id": item_id}

    response = client.get("/api/v1/_validate/not-an-int")
    assert response.status_code == 422
    body = response.json()
    assert body["data"] is None
    assert body["errors"]
    assert body["errors"][0]["code"] == "VALIDATION_ERROR"


def test_production_settings_fail_fast() -> None:
    clear_settings_cache()
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(
            app_env="production",
            jwt_secret="change-me-to-a-long-random-string",
            database_url="postgresql+psycopg://u:change-me@localhost/db",
        )
    clear_settings_cache()


def test_production_settings_accept_secure_secrets() -> None:
    clear_settings_cache()
    settings = Settings(
        app_env="production",
        jwt_secret="a-sufficiently-long-production-secret",
        database_url="postgresql+psycopg://u:real-secret@localhost/db",
    )
    assert settings.is_production
    clear_settings_cache()


def test_unhandled_error_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    clear_settings_cache()
    app = create_app(Settings(app_env="test"))

    @app.get("/api/v1/_crash")
    def _crash() -> None:
        raise RuntimeError("unexpected")

    # TestClient re-raises unhandled exceptions by default; disable to assert envelope.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/_crash")
    assert response.status_code == 500
    body = response.json()
    assert body["errors"][0]["code"] == ErrorCode.INTERNAL_ERROR
    assert body["data"] is None
    clear_settings_cache()
