"""Document catalog & upload tests for Milestone 1.7."""

from __future__ import annotations

from collections.abc import Generator
from io import BytesIO
from pathlib import Path

import app.db.models  # noqa: F401
import pytest
from app.core.config import clear_settings_cache
from app.db.base import Base
from app.db.seed import run_seed
from app.db.session import clear_engine_cache, get_db
from app.documents.classification import classify_document, extract_drawing_number
from app.main import create_app
from app.storage.factory import clear_storage_cache
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture()
def docs_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "docs.db"
    storage_root = tmp_path / "blob"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-for-milestone-1-7")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(storage_root))
    monkeypatch.setenv("CORPUS_SOURCE", "local")
    monkeypatch.setenv("CORPUS_LOCAL_ROOT", str(tmp_path / "empty_corpus"))
    (tmp_path / "empty_corpus").mkdir()
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
        yield client

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


def test_classify_document_path_and_drawing() -> None:
    result = classify_document(
        name="3GZF1234567_outline.pdf",
        folder_path=(
            "Motors/Low_Voltage_Motor - 001/Low_Voltage_Motor/"
            "drawing/Dimension_Drawings"
        ),
    )
    assert result.asset_domain == "Motors"
    assert result.doc_category == "drawing"
    assert result.doc_subtype == "drawing_dimension"
    assert result.drawing_number == "3GZF1234567"
    assert extract_drawing_number("3AXD0000123456_sheet.pdf") == "3AXD0000123456"


def test_upload_list_get_and_stub_links(docs_env: TestClient) -> None:
    client = docs_env
    headers = _login(client)

    denied = client.get("/api/v1/documents/catalog")
    assert denied.status_code == 401

    files = {
        "file": (
            "3GZF9998887_M3BP_test.pdf",
            BytesIO(b"%PDF-1.4 upload body"),
            "application/pdf",
        )
    }
    data = {
        "folder_path": (
            "Motors/Low_Voltage_Motor - 001/Low_Voltage_Motor/" "incident or inspection"
        ),
        "title": "Hero motor test report",
    }
    uploaded = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files=files,
        data=data,
    )
    assert uploaded.status_code == 200, uploaded.text
    body = uploaded.json()["data"]
    assert body["storage_key"].startswith("uploads/")
    assert body["catalog"]["doc_category"] == "test_report"
    assert body["catalog"]["drawing_number"] == "3GZF9998887"
    assert body["document"]["status"] == "uploaded"
    assert body["document"]["linked_drawings"]
    assert body["document"]["linked_drawings"][0]["drawing_number"] == "3GZF9998887"
    assert any(
        a["link_type"] in {"drawing_number", "motor_type"}
        for a in body["document"]["linked_assets"]
    )

    doc_id = body["document"]["id"]
    catalog_id = body["catalog"]["id"]

    listed = client.get("/api/v1/documents", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] >= 1

    got = client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert got.status_code == 200
    assert got.json()["data"]["id"] == doc_id
    assert got.json()["data"]["versions"]

    catalog = client.get("/api/v1/documents/catalog", headers=headers)
    assert catalog.status_code == 200
    assert catalog.json()["data"]["total"] >= 1

    stats = client.get("/api/v1/documents/catalog/stats", headers=headers)
    assert stats.status_code == 200
    assert stats.json()["data"]["total"] >= 1

    one = client.get(f"/api/v1/documents/catalog/{catalog_id}", headers=headers)
    assert one.status_code == 200
    assert one.json()["data"]["id"] == catalog_id

    filtered = client.get(
        "/api/v1/documents/catalog",
        headers=headers,
        params={"drawing_number": "3GZF9998887"},
    )
    assert filtered.status_code == 200
    assert filtered.json()["data"]["total"] == 1


def test_reject_disallowed_upload_mime(docs_env: TestClient) -> None:
    client = docs_env
    headers = _login(client)
    files = {
        "file": ("evil.exe", BytesIO(b"MZ"), "application/x-msdownload"),
    }
    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files=files,
    )
    assert response.status_code == 400


def test_discovery_upsert_via_catalog_service(
    docs_env: TestClient, tmp_path: Path
) -> None:
    """1.7.1 — discovery upsert classifies and seeds registry stubs."""
    from app.core.config import get_settings
    from app.db.models.assets import Asset
    from app.db.models.drawings import DrawingNumber
    from app.db.session import get_engine
    from app.documents.service import DocumentCatalogService
    from app.storage.factory import build_storage_service

    clear_storage_cache()
    settings = get_settings()
    storage = build_storage_service(settings)
    engine = get_engine()
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        service = DocumentCatalogService(session, storage)
        row = service.upsert_from_discovery(
            drive_file_id="local:test-discovery-1",
            name="3GZF1112223_report.pdf",
            folder_path=(
                "Motors/Low_Voltage_Motor - 001/Low_Voltage_Motor/"
                "incident or inspection"
            ),
            mime_type="application/pdf",
            size_bytes=12,
            md5_checksum="fp:12:1",
            absolute_path=str(tmp_path / "x.pdf"),
        )
        session.commit()
        assert row.doc_category == "test_report"
        assert row.drawing_number == "3GZF1112223"
        drawing = session.scalars(
            select(DrawingNumber).where(DrawingNumber.normalized == "3GZF1112223")
        ).first()
        assert drawing is not None
        motor = session.scalars(
            select(Asset).where(Asset.asset_tag == "motor:Low_Voltage_Motor - 001")
        ).first()
        assert motor is not None
        assert motor.status == "stub"
    finally:
        session.close()
