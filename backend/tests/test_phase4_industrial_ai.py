"""Phase 4 Industrial AI tests — router, copilot, maintenance, compliance, analytics."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.agents.compliance_engine import ComplianceEngine
from app.agents.copilot import CopilotService
from app.agents.multi_hop import MultiHopPlanner
from app.agents.router import QueryIntent, QueryRouter
from app.agents.schemas import ChatRequest, FeedbackRequest
from app.agents.verify import NumericClaimVerifier
from app.dashboard.analytics import AnalyticsService
from app.db.base import Base
from app.db.models.documents import Document, DocumentAssetLink, DocumentCatalog
from app.db.models.extraction import PerformanceTestReport, TestMeasurement
from app.motors.hero import HERO_MOTOR_CODE
from app.motors.service import MotorRegistryService
from app.reasoning.maintenance import MaintenanceService
from app.reasoning.rca import RcaService
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def session(tmp_path: Path) -> Session:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'phase4.db'}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as s:
        yield s


def _seed_hero(session: Session) -> str:
    registry = MotorRegistryService(session)
    registry.confirm_hero_set()
    motor = registry.models.get_by_code(HERO_MOTOR_CODE)
    assert motor is not None

    catalog = DocumentCatalog(
        drive_file_id="drive-p4-test",
        name="Hero IEC Test Report.pdf",
        doc_category="test_report",
        motor_type_code=HERO_MOTOR_CODE,
        drawing_number="3GZF999001",
    )
    session.add(catalog)
    session.flush()
    doc = Document(
        title="Hero IEC Test Report.pdf",
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

    safety = DocumentCatalog(
        drive_file_id="drive-p4-loto",
        name="LOTO Lockout Tagout Procedure.pdf",
        doc_category="safety",
        motor_type_code=HERO_MOTOR_CODE,
    )
    session.add(safety)
    session.flush()
    safety_doc = Document(
        title="LOTO Lockout Tagout Procedure.pdf",
        doc_type="safety",
        status="ready",
        catalog_id=safety.id,
    )
    session.add(safety_doc)
    session.flush()
    if motor.asset_id:
        session.add(
            DocumentAssetLink(
                document_id=safety_doc.id,
                asset_id=motor.asset_id,
                link_type="motor_type",
            )
        )

    cert = DocumentCatalog(
        drive_file_id="drive-p4-atex",
        name="ATEX Certificate Ex.pdf",
        doc_category="certificate",
        motor_type_code=HERO_MOTOR_CODE,
    )
    session.add(cert)
    session.flush()
    cert_doc = Document(
        title="ATEX Certificate Ex.pdf",
        doc_type="certificate",
        status="ready",
        catalog_id=cert.id,
    )
    session.add(cert_doc)
    session.flush()
    if motor.asset_id:
        session.add(
            DocumentAssetLink(
                document_id=cert_doc.id,
                asset_id=motor.asset_id,
                link_type="motor_type",
            )
        )

    report = PerformanceTestReport(
        document_id=doc.id,
        motor_type_code=HERO_MOTOR_CODE,
        standard="IEC 60034",
        status="extracted",
    )
    session.add(report)
    session.flush()
    session.add(
        TestMeasurement(
            report_id=report.id,
            document_id=doc.id,
            parameter="efficiency",
            unit="%",
            measured_value="94.2",
            numeric_value=94.2,
        )
    )
    session.add(
        TestMeasurement(
            report_id=report.id,
            document_id=doc.id,
            parameter="temperature_rise",
            unit="K",
            measured_value="72",
            numeric_value=72.0,
        )
    )
    session.commit()
    return motor.id


def test_query_router_intents(session: Session) -> None:
    motor_id = _seed_hero(session)
    router = QueryRouter(session)

    drawing = router.route("Show documents for drawing 3GZF999001", motor_id=motor_id)
    assert drawing.intent == QueryIntent.DRAWING_CROSS_REF
    assert drawing.entities.drawing_number == "3GZF999001"

    test_q = router.route(
        "What is the efficiency and temperature rise for this motor?",
        motor_id=motor_id,
    )
    assert test_q.intent == QueryIntent.TEST_REPORT_HISTORY
    assert "get_test_history" in test_q.tools

    loto = router.route(
        "What LOTO procedure applies before maintaining this motor?",
        motor_id=motor_id,
    )
    assert loto.intent == QueryIntent.PROCEDURE

    atex = router.route(
        "What ATEX certifications does this motor have and which regulation?",
        motor_id=motor_id,
    )
    assert atex.intent == QueryIntent.COMPLIANCE


def test_copilot_chat_and_feedback(session: Session) -> None:
    motor_id = _seed_hero(session)
    service = CopilotService(session)
    response = service.chat(
        ChatRequest(
            message=(
                "What is the efficiency and temperature rise for this motor "
                "per its latest test report?"
            ),
            motor_id=motor_id,
        )
    )
    assert response.session_id
    assert response.message_id
    assert "94.2" in response.answer or "efficiency" in response.answer.lower()
    assert response.intent == QueryIntent.TEST_REPORT_HISTORY.value

    fb = service.submit_feedback(
        FeedbackRequest(
            rating=5,
            session_id=response.session_id,
            message_id=response.message_id,
            comment="demo",
        )
    )
    assert fb.rating == 5
    assert fb.id


def test_maintenance_rca_compliance_analytics(session: Session) -> None:
    motor_id = _seed_hero(session)

    maint = MaintenanceService(session).analyze(motor_id)
    assert maint.measurement_count >= 2
    assert any(t.parameter == "efficiency" for t in maint.trends)

    rca = RcaService(session).analyze(motor_id)
    assert len(rca.five_why) == 5
    assert rca.motor_id == motor_id

    compliance = ComplianceEngine(session).assess_motor(motor_id)
    assert compliance["total"] >= 4
    assert compliance["met"] >= 2
    assert compliance["coverage"] > 0

    analytics = AnalyticsService(session).snapshot()
    assert analytics.motor_models >= 1
    assert analytics.documents_total >= 1
    assert len(analytics.velocity) == 7


def test_multi_hop_and_numeric_verify(session: Session) -> None:
    motor_id = _seed_hero(session)
    planner = MultiHopPlanner()
    plan = planner.plan_for(
        "What is the efficiency and temperature rise for this motor "
        "per its latest test report?"
    )
    assert plan is not None
    assert plan["id"] == "demo_efficiency_temp"
    assert "get_test_history" in plan["tools"]

    verifier = NumericClaimVerifier(session)
    checks = verifier.verify_answer(
        "Efficiency 94.2 % and temperature rise 72 K per test report.",
        motor_id=motor_id,
    )
    assert checks
    assert all(c.get("ok") for c in checks if not c.get("skipped"))
