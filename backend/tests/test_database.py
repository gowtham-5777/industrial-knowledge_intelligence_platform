"""Database / repository tests for Milestone 1.3."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import app.db.models  # noqa: F401
import pytest
from alembic import command
from alembic.config import Config
from app.core.config import clear_settings_cache
from app.db.base import Base
from app.db.models import DocumentCatalog, ProductLine
from app.db.repositories.assets import AssetRepository
from app.db.repositories.documents import DocumentCatalogRepository
from app.db.seed import ABB_LV_MOTORS_CODE, run_seed
from app.db.session import clear_engine_cache
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture()
def db_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[Session, None, None]:
    db_path = tmp_path / "test.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ENV", "test")
    clear_settings_cache()
    clear_engine_cache()

    engine = create_engine(url, connect_args={"check_same_thread": False})
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
        clear_settings_cache()
        clear_engine_cache()


def test_asset_repository_crud(db_session: Session) -> None:
    repo = AssetRepository(db_session)
    created = repo.create(
        asset_type="motor",
        name="M3BP 160MLA4",
        asset_tag="MOTOR-001",
    )
    assert created.id
    fetched = repo.get(created.id)
    assert fetched is not None
    assert fetched.asset_type == "motor"
    assert repo.get_by_tag("MOTOR-001") is not None
    assert len(repo.list_by_type("motor")) == 1


def test_document_catalog_upsert(db_session: Session) -> None:
    repo = DocumentCatalogRepository(db_session)
    first = repo.upsert_discovery(
        drive_file_id="drive-abc",
        name="test-report.pdf",
        doc_category="test_report",
        drawing_number="3GZF123",
    )
    second = repo.upsert_discovery(
        drive_file_id="drive-abc",
        name="test-report-v2.pdf",
        doc_category="test_report",
        drawing_number="3GZF123",
    )
    assert first.id == second.id
    assert second.name == "test-report-v2.pdf"
    assert repo.count() == 1
    assert isinstance(repo.get(first.id), DocumentCatalog)


def test_seed_product_line_idempotent(db_session: Session) -> None:
    from sqlalchemy import select

    first = run_seed(db_session)
    second = run_seed(db_session)
    assert first["product_line"] == ABB_LV_MOTORS_CODE
    assert second["product_line"] == ABB_LV_MOTORS_CODE
    rows = list(
        db_session.scalars(
            select(ProductLine).where(ProductLine.code == ABB_LV_MOTORS_CODE)
        ).all()
    )
    assert len(rows) == 1


def test_alembic_upgrade_downgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "migrate.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ENV", "test")
    clear_settings_cache()
    clear_engine_cache()

    backend_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)

    command.upgrade(cfg, "head")
    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    assert "assets" in tables
    assert "document_catalog" in tables
    assert "motor_models" in tables
    assert "indexing_jobs" in tables
    assert "alembic_version" in tables

    command.downgrade(cfg, "base")
    remaining = set(inspect(engine).get_table_names())
    assert "assets" not in remaining
    assert "document_catalog" not in remaining
    assert "motor_models" not in remaining

    command.upgrade(cfg, "head")
    restored = set(inspect(engine).get_table_names())
    assert "assets" in restored
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    engine.dispose()
    clear_settings_cache()
    clear_engine_cache()
