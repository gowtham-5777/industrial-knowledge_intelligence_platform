"""Auth API tests for Milestone 1.4."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import app.db.models  # noqa: F401
import pytest
from app.core.config import clear_settings_cache
from app.db.base import Base
from app.db.seed import run_seed
from app.db.session import clear_engine_cache, get_db
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture()
def auth_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "auth.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-for-milestone-1-4")
    clear_settings_cache()
    clear_engine_cache()

    engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    session = factory()
    run_seed(session)
    session.commit()
    session.close()

    def _override_db() -> Generator[Session, None, None]:
        db = factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    engine.dispose()
    clear_settings_cache()
    clear_engine_cache()


def test_login_success(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@example.com",
            "password": "ChangeMeAdmin!",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["errors"] == []
    assert body["data"]["access_token"]
    assert body["data"]["refresh_token"]
    assert body["data"]["token_type"] == "bearer"


def test_login_failure(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@example.com",
            "password": "wrong-password",
        },
    )
    assert response.status_code == 401
    body = response.json()
    assert body["data"] is None
    assert body["errors"][0]["code"] == "PERMISSION_DENIED"


def test_me_and_protected_route(auth_client: TestClient) -> None:
    login = auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": "operator@example.com",
            "password": "ChangeMeOperator!",
        },
    )
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = auth_client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    profile = me.json()["data"]
    assert profile["email"] == "operator@example.com"
    assert any(r["code"] == "PlantOperator" for r in profile["roles"])

    denied = auth_client.get("/api/v1/auth/me")
    assert denied.status_code == 401

    check = auth_client.get("/api/v1/session/check", headers=headers)
    assert check.status_code == 200
    assert check.json()["data"]["authenticated"] is True

    blocked = auth_client.get("/api/v1/session/check")
    assert blocked.status_code == 401


def test_refresh_token(auth_client: TestClient) -> None:
    login = auth_client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@example.com",
            "password": "ChangeMeAdmin!",
        },
    )
    refresh = login.json()["data"]["refresh_token"]
    response = auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert response.status_code == 200
    assert response.json()["data"]["access_token"]
