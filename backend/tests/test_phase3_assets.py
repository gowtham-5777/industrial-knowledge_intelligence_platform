"""Phase 3 Asset Intelligence tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.db.base import Base
from app.db.models.documents import Document, DocumentAssetLink, DocumentCatalog
from app.health.scoring import HealthScoringService
from app.motor360.service import Motor360Service
from app.motors.hero import HERO_MOTOR_CODE
from app.motors.service import MotorRegistryService
from app.recommendations.service import RecommendationService
from app.summary.service import SummaryService
from app.timeline.service import TimelineService
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def session(tmp_path: Path) -> Session:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'phase3.db'}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as s:
        yield s


def _seed_hero_with_docs(session: Session) -> str:
    registry = MotorRegistryService(session)
    registry.confirm_hero_set()
    motor = registry.models.get_by_code(HERO_MOTOR_CODE)
    assert motor is not None
    catalog = DocumentCatalog(
        drive_file_id="drive-hero-1",
        name="Hero Test Report.pdf",
        doc_category="test_report",
        motor_type_code=HERO_MOTOR_CODE,
        drawing_number="3GZF123456",
    )
    session.add(catalog)
    session.flush()
    doc = Document(
        title="Hero Test Report.pdf",
        doc_type="test_report",
        status="ready",
        catalog_id=catalog.id,
    )
    session.add(doc)
    session.flush()
    if motor.asset_id:
        session.add(
            DocumentAssetLink(
                document_id=doc.id,
                asset_id=motor.asset_id,
                link_type="motor_type",
            )
        )
    cat2 = DocumentCatalog(
        drive_file_id="drive-hero-2",
        name="Hero Datasheet.pdf",
        doc_category="datasheet",
        motor_type_code=HERO_MOTOR_CODE,
    )
    session.add(cat2)
    session.flush()
    doc2 = Document(
        title="Hero Datasheet.pdf",
        doc_type="datasheet",
        status="ready",
        catalog_id=cat2.id,
    )
    session.add(doc2)
    session.flush()
    if motor.asset_id:
        session.add(
            DocumentAssetLink(
                document_id=doc2.id,
                asset_id=motor.asset_id,
                link_type="motor_type",
            )
        )
    session.commit()
    return motor.id


def test_confirm_hero_set(session: Session) -> None:
    registry = MotorRegistryService(session)
    data = registry.confirm_hero_set()
    session.commit()
    assert data.hero.code == HERO_MOTOR_CODE
    assert len(data.supporting) == 4
    listed = registry.search_motors(limit=20)
    assert listed.total >= 5


def test_alias_resolve(session: Session) -> None:
    registry = MotorRegistryService(session)
    registry.confirm_hero_set()
    session.commit()
    matched = registry.resolve_alias("M3BP 160MLA4")
    assert matched is not None
    assert matched.code == HERO_MOTOR_CODE


def test_health_timeline_summary_recs(session: Session) -> None:
    motor_id = _seed_hero_with_docs(session)
    health = HealthScoringService(session).compute(motor_id)
    assert 0 <= health.score <= 100
    assert health.risk_level in {"low", "medium", "high"}
    assert health.evidence

    events = TimelineService(session).build_timeline(motor_id)
    assert events.total >= 1

    summary = SummaryService(session).generate(motor_id, force=True)
    assert summary.overview

    recs = RecommendationService(session).generate(motor_id, force=True)
    assert len(recs.items) >= 3
    assert recs.items[0].citations is not None
    session.commit()


def test_motor360_bundle(session: Session) -> None:
    motor_id = _seed_hero_with_docs(session)
    bundle = Motor360Service(session).get_bundle(motor_id)
    session.commit()
    assert bundle.motor.code == HERO_MOTOR_CODE
    assert bundle.health is not None
    assert bundle.summary is not None
    assert bundle.summary.overview
    assert bundle.documents is not None
    assert bundle.subgraph.nodes
    assert len(bundle.recommendations.items) >= 1
