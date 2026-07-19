"""Corpus sync tests for Milestone 1.6 (local source)."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import app.db.models  # noqa: F401
import pytest
from app.core.config import clear_settings_cache
from app.db.base import Base
from app.db.seed import run_seed
from app.db.session import clear_engine_cache, get_db
from app.gdrive.local_client import LocalCorpusClient, stable_source_file_id
from app.gdrive.path_classify import classify_path, extract_drawing_number
from app.main import create_app
from app.storage.factory import build_storage_service, clear_storage_cache
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture()
def mini_corpus(tmp_path: Path) -> Path:
    root = tmp_path / "corpus"
    motor_dir = (
        root
        / "Motors"
        / "Low_Voltage_Motor - 001"
        / "Low_Voltage_Motor"
        / "incident or inspection"
    )
    motor_dir.mkdir(parents=True)
    (motor_dir / "3GZF1234567_test_report.pdf").write_bytes(b"%PDF-1.4 mini report")
    manual_dir = (
        root
        / "Motors"
        / "Low_Voltage_Motor - 001"
        / "Low_Voltage_Motor"
        / "Instructions And Manuals"
    )
    manual_dir.mkdir(parents=True)
    (manual_dir / "install_guide.pdf").write_bytes(b"%PDF-1.4 manual")
    drawing_dir = (
        root
        / "Motors"
        / "Low_Voltage_Motor - 001"
        / "Low_Voltage_Motor"
        / "drawing"
        / "Dimension_Drawings"
    )
    drawing_dir.mkdir(parents=True)
    (drawing_dir / "outline.pdf").write_bytes(b"%PDF-1.4 drawing")
    valves = root / "Valves" / "docs"
    valves.mkdir(parents=True)
    (valves / "valve_note.txt").write_text("valve", encoding="utf-8")
    return root


@pytest.fixture()
def sync_env(
    tmp_path: Path, mini_corpus: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[tuple[TestClient, Path], None, None]:
    db_path = tmp_path / "sync.db"
    storage_root = tmp_path / "blob"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-for-milestone-1-6")
    monkeypatch.setenv("CORPUS_SOURCE", "local")
    monkeypatch.setenv("CORPUS_LOCAL_ROOT", str(mini_corpus))
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(storage_root))
    monkeypatch.setenv("CORPUS_DISCOVERY_BATCH_SIZE", "2")
    monkeypatch.setenv("CORPUS_DOWNLOAD_MAX_FILES", "2")
    clear_settings_cache()
    clear_engine_cache()
    clear_storage_cache()

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
        yield client, mini_corpus

    app.dependency_overrides.clear()
    engine.dispose()
    clear_settings_cache()
    clear_engine_cache()
    clear_storage_cache()


def _login(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "ChangeMeAdmin!"},
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_path_classify_and_drawing() -> None:
    path = (
        "Motors/Low_Voltage_Motor - 001/Low_Voltage_Motor/"
        "drawing/Dimension_Drawings/a.pdf"
    )
    domain, category, subtype = classify_path(path)
    assert domain == "Motors"
    assert category == "drawing"
    assert extract_drawing_number("3GZF1234567_test_report.pdf") == "3GZF1234567"


def test_local_client_batch_resume(mini_corpus: Path) -> None:
    client = LocalCorpusClient(mini_corpus)
    first = client.discover_batch(limit=2)
    assert len(first.files) == 2
    assert first.exhausted is False
    second = client.discover_batch(cursor=first.next_cursor, limit=10)
    assert second.exhausted is True
    ids = {f.source_file_id for f in first.files + second.files}
    assert len(ids) == 4
    assert stable_source_file_id(first.files[0].folder_path + "/" + first.files[0].name)


def test_sync_auth_status_and_discovery(sync_env: tuple[TestClient, Path]) -> None:
    client, _root = sync_env
    headers = _login(client)

    auth = client.get("/api/v1/sync/auth/check", headers=headers)
    assert auth.status_code == 200
    assert auth.json()["data"]["ok"] is True
    assert auth.json()["data"]["source"] == "local"

    denied = client.get("/api/v1/sync/status")
    assert denied.status_code == 401

    # Partial discovery (max_batches=1 with batch size 2)
    started = client.post(
        "/api/v1/sync/start",
        headers=headers,
        json={"mode": "discover", "resume": False, "max_batches": 1},
    )
    assert started.status_code == 200
    body = started.json()["data"]
    assert body["files_discovered"] == 2
    assert body["status"] in {"paused", "completed", "running"}

    # Resume to completion
    finished = client.post(
        "/api/v1/sync/start",
        headers=headers,
        json={"mode": "discover", "resume": True},
    )
    assert finished.status_code == 200
    assert finished.json()["data"]["files_discovered"] == 4
    assert finished.json()["data"]["status"] == "completed"

    status = client.get("/api/v1/sync/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["data"]["files_upserted"] == 4


def test_selective_download_to_storage(
    sync_env: tuple[TestClient, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, root = sync_env
    headers = _login(client)
    client.post(
        "/api/v1/sync/start",
        headers=headers,
        json={"mode": "discover", "resume": False},
    )
    downloaded = client.post(
        "/api/v1/sync/start",
        headers=headers,
        json={
            "mode": "download",
            "domain_filter": "Motors",
            "max_download_files": 2,
        },
    )
    assert downloaded.status_code == 200
    data = downloaded.json()["data"]
    assert data["files_downloaded"] == 2
    assert data["bytes_downloaded"] > 0

    # Storage should contain objects
    from app.core.config import get_settings

    clear_storage_cache()
    settings = get_settings()
    storage = build_storage_service(settings)
    # At least one corpus key exists under local backend root
    bucket_dir = Path(settings.storage_local_root) / settings.storage_bucket
    files = list(bucket_dir.rglob("*")) if bucket_dir.exists() else []
    assert any(p.is_file() and p.name.endswith(".pdf") for p in files)
    assert storage.health_check().ok is True
    _ = root
