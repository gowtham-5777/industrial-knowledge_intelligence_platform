"""Tests for Milestone 2.1 — Parsing & OCR pipeline."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from types import SimpleNamespace

import app.db.models  # noqa: F401
import pytest
from app.core.config import Settings, clear_settings_cache
from app.core.exceptions import AppError
from app.db.base import Base
from app.db.models.documents import Document, DocumentCatalog, DocumentVersion
from app.db.session import clear_engine_cache
from app.indexing.handlers.azure_di_handler import (
    StubAzureLayoutHandler,
    _table_to_rows,
)
from app.indexing.handlers.metadata_handler import MetadataOnlyHandler
from app.indexing.handlers.native_handlers import NativeFormatHandler
from app.indexing.handlers.pymupdf_handler import PyMuPdfHandler
from app.indexing.job_state import JobStatus, assert_transition
from app.indexing.service import ParseService
from app.indexing.tier_router import select_parser_tier
from app.indexing.tiers import ParserTier, RoutingContext
from app.main import create_app
from app.storage.backends.local import LocalObjectStorage
from app.storage.service import StorageService
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture()
def db_session(tmp_path: Path) -> Generator[Session, None, None]:
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'parse.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def storage(tmp_path: Path) -> StorageService:
    root = tmp_path / "storage"
    root.mkdir()
    port = LocalObjectStorage(root=str(root), bucket="test-bucket")
    return StorageService(port)


def _make_pdf_bytes(text: str = "Motor datasheet M3BP") -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def test_router_selects_t1_for_test_reports() -> None:
    tier = select_parser_tier(
        RoutingContext(
            mime_type="application/pdf",
            doc_category="test_report",
            filename="IEC60034_report.pdf",
        )
    )
    assert tier == ParserTier.T1


def test_router_selects_t0_for_datasheets() -> None:
    tier = select_parser_tier(
        RoutingContext(
            mime_type="application/pdf",
            doc_category="datasheet",
            filename="M3BP_datasheet.pdf",
        )
    )
    assert tier == ParserTier.T0


def test_router_selects_t0b_for_regulation_xml() -> None:
    tier = select_parser_tier(
        RoutingContext(
            mime_type="application/xml",
            doc_category="regulation",
            filename="iec.xml",
            folder_path="Motors/Regulations",
        )
    )
    assert tier == ParserTier.T0B


def test_router_selects_t3_for_cad() -> None:
    tier = select_parser_tier(
        RoutingContext(
            mime_type="application/octet-stream",
            doc_category="drawing_cad",
            filename="part.step",
            folder_path="Motors/CAD_Models_and_3D_Drawings",
        )
    )
    assert tier == ParserTier.T3


def test_router_selects_t4_for_dimension_drawings() -> None:
    tier = select_parser_tier(
        RoutingContext(
            mime_type="application/pdf",
            doc_category="drawing_dimension",
            filename="3GZF123456_A1.pdf",
        )
    )
    assert tier == ParserTier.T4


def test_job_state_machine_allows_parse_path() -> None:
    assert_transition(JobStatus.QUEUED.value, JobStatus.PARSING)
    assert_transition(JobStatus.PARSING.value, JobStatus.PARSED)
    with pytest.raises(AppError):
        assert_transition(JobStatus.QUEUED.value, JobStatus.PARSED)


def test_pymupdf_handler_extracts_text() -> None:
    handler = PyMuPdfHandler()
    content = _make_pdf_bytes("Efficiency IE3 frame 160")
    out = handler.parse(
        content,
        ctx=RoutingContext(filename="sheet.pdf", mime_type="application/pdf"),
    )
    assert out.tier == "T0"
    assert out.page_count >= 1
    assert "Efficiency" in out.full_text or "Efficiency" in out.pages[0].text


def test_native_xml_handler() -> None:
    handler = NativeFormatHandler()
    xml = (
        b'<?xml version="1.0"?>'
        b'<regulation><clause id="4.1">Temp rise limits</clause></regulation>'
    )
    out = handler.parse(
        xml,
        ctx=RoutingContext(
            mime_type="application/xml",
            filename="reg.xml",
            doc_category="regulation",
        ),
    )
    assert out.tier == "T0b"
    assert "Temp rise" in out.full_text


def test_native_csv_handler() -> None:
    handler = NativeFormatHandler()
    csv_bytes = b"requirement_id,domain,text\nR-1,safety,Lockout required\n"
    out = handler.parse(
        csv_bytes,
        ctx=RoutingContext(mime_type="text/csv", filename="regs.csv"),
    )
    assert "Lockout" in out.full_text


def test_metadata_only_skips_content() -> None:
    handler = MetadataOnlyHandler()
    out = handler.parse(
        b"binary-cad-bytes",
        ctx=RoutingContext(
            filename="3GZF999999.step",
            doc_category="drawing_cad",
            folder_path="Motors/CAD_Models_and_3D_Drawings",
        ),
    )
    assert out.skipped is True
    assert out.full_text == ""
    assert out.metadata.get("drawing_number") == "3GZF999999"


def test_azure_di_extracts_test_report_table() -> None:
    """DoD: Azure DI extracts a test-report table (stubbed layout result)."""
    table = SimpleNamespace(
        row_count=3,
        column_count=4,
        bounding_regions=[SimpleNamespace(page_number=1)],
        cells=[
            SimpleNamespace(row_index=0, column_index=0, content="Parameter"),
            SimpleNamespace(row_index=0, column_index=1, content="Unit"),
            SimpleNamespace(row_index=0, column_index=2, content="Rated"),
            SimpleNamespace(row_index=0, column_index=3, content="Measured"),
            SimpleNamespace(row_index=1, column_index=0, content="Efficiency"),
            SimpleNamespace(row_index=1, column_index=1, content="%"),
            SimpleNamespace(row_index=1, column_index=2, content="95.5"),
            SimpleNamespace(row_index=1, column_index=3, content="95.2"),
            SimpleNamespace(row_index=2, column_index=0, content="Power factor"),
            SimpleNamespace(row_index=2, column_index=1, content="-"),
            SimpleNamespace(row_index=2, column_index=2, content="0.88"),
            SimpleNamespace(row_index=2, column_index=3, content="0.87"),
        ],
    )
    result = SimpleNamespace(
        pages=[
            SimpleNamespace(
                page_number=1,
                lines=[SimpleNamespace(content="IEC 60034 Performance Test")],
            )
        ],
        tables=[table],
        content="IEC 60034 Performance Test",
    )
    handler = StubAzureLayoutHandler(result)
    out = handler.parse(
        b"%PDF-fake",
        ctx=RoutingContext(
            mime_type="application/pdf",
            doc_category="test_report",
            filename="test.pdf",
        ),
    )
    assert out.tier == "T1"
    assert len(out.tables) == 1
    rows = out.tables[0].rows
    assert rows[0][0] == "Parameter"
    assert rows[1][0] == "Efficiency"
    assert "95.2" in rows[1]
    assert "Efficiency" in out.tables[0].markdown
    assert _table_to_rows(table)[2][0] == "Power factor"


def test_parse_service_end_to_end_t0(
    db_session: Session, storage: StorageService
) -> None:
    clear_settings_cache()
    pdf = _make_pdf_bytes("Datasheet frame 160MLA4")
    stored = storage.upload(
        "uploads/demo.pdf",
        pdf,
        content_type="application/pdf",
    )
    catalog = DocumentCatalog(
        drive_file_id="upload:demo",
        name="demo.pdf",
        folder_path="Motors/Spare_Parts_or_Product_Descriptions",
        mime_type="application/pdf",
        doc_category="datasheet",
        extra_metadata={"storage_key": stored.key, "storage_bucket": stored.bucket},
    )
    db_session.add(catalog)
    db_session.flush()
    document = Document(
        title="demo.pdf",
        doc_type="datasheet",
        status="uploaded",
        storage_uri=f"{stored.bucket}/{stored.key}",
        catalog_id=catalog.id,
    )
    db_session.add(document)
    db_session.flush()
    db_session.add(
        DocumentVersion(
            version=1,
            storage_uri=document.storage_uri or "",
            document_id=document.id,
        )
    )
    db_session.flush()

    settings = Settings(
        app_env="test",
        database_url="sqlite:///:memory:",
        parse_fallback_without_azure=True,
    )
    service = ParseService(db_session, storage, settings)
    run = service.parse_document(document.id)
    assert run.job.status == JobStatus.PARSED.value
    assert run.result is not None
    assert run.result.tier == "T0"
    assert run.result.page_count >= 1
    assert document.status == "parsed"


def test_parse_service_t3_metadata_only(
    db_session: Session, storage: StorageService
) -> None:
    catalog = DocumentCatalog(
        drive_file_id="cad:1",
        name="3GZF111111.dwg",
        folder_path="Motors/CAD_Models_and_3D_Drawings",
        mime_type="application/octet-stream",
        doc_category="drawing_cad",
        extra_metadata={},
    )
    db_session.add(catalog)
    db_session.flush()
    document = Document(
        title="3GZF111111.dwg",
        doc_type="drawing_cad",
        status="discovered",
        catalog_id=catalog.id,
    )
    db_session.add(document)
    db_session.flush()

    service = ParseService(
        db_session,
        storage,
        Settings(app_env="test", database_url="sqlite:///:memory:"),
    )
    run = service.parse_document(document.id)
    assert run.result is not None
    assert run.result.tier == "T3"
    assert run.result.status == "skipped"
    assert document.status == "parse_skipped"


@pytest.fixture()
def api_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "api.db"
    storage_root = tmp_path / "api-storage"
    storage_root.mkdir()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(storage_root))
    monkeypatch.setenv("JWT_SECRET", "test-secret-for-parse-api")
    clear_settings_cache()
    clear_engine_cache()

    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    engine.dispose()

    app = create_app(
        Settings(
            app_env="test",
            database_url=f"sqlite:///{db_path.as_posix()}",
            storage_backend="local",
            storage_local_root=str(storage_root),
            jwt_secret="test-secret-for-parse-api",
            parse_fallback_without_azure=True,
        )
    )
    with TestClient(app) as client:
        yield client
    clear_settings_cache()
    clear_engine_cache()


def test_route_preview_api(api_client: TestClient) -> None:
    # Need auth — use seed user if available, or skip login path
    from app.db.seed import run_seed
    from app.db.session import get_session_factory

    session = get_session_factory()()
    try:
        run_seed(session)
        session.commit()
    finally:
        session.close()

    login = api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "ChangeMeAdmin!"},
    )
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = api_client.get(
        "/api/v1/indexing/route/preview",
        params={
            "mime_type": "application/pdf",
            "doc_category": "test_report",
            "filename": "report.pdf",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["tier"] == "T1"
