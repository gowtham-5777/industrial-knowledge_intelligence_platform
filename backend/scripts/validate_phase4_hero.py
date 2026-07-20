"""Phase 4 validation gate — hero motor Industrial AI smoke checks."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("APP_ENV", "test")

from app.agents.compliance_engine import ComplianceEngine  # noqa: E402
from app.agents.copilot import CopilotService  # noqa: E402
from app.agents.router import QueryIntent, QueryRouter  # noqa: E402
from app.agents.schemas import ChatRequest, FeedbackRequest  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.models.documents import (  # noqa: E402
    Document,
    DocumentAssetLink,
    DocumentCatalog,
)
from app.db.models.extraction import (  # noqa: E402
    PerformanceTestReport,
    TestMeasurement,
)
from app.motors.hero import HERO_MOTOR_CODE  # noqa: E402
from app.motors.service import MotorRegistryService  # noqa: E402
from app.reasoning.maintenance import MaintenanceService  # noqa: E402
from app.reasoning.rca import RcaService  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

DEMO_QUESTIONS = [
    (
        (
            "What is the efficiency and temperature rise for this motor "
            "per its latest test report?"
        ),
        QueryIntent.TEST_REPORT_HISTORY,
    ),
    (
        "What LOTO procedure applies before maintaining this motor?",
        QueryIntent.PROCEDURE,
    ),
    (
        (
            "What ATEX certifications does this motor have and which "
            "regulation do they satisfy?"
        ),
        QueryIntent.COMPLIANCE,
    ),
]


def _seed(session) -> str:
    registry = MotorRegistryService(session)
    registry.confirm_hero_set()
    motor = registry.models.get_by_code(HERO_MOTOR_CODE)
    assert motor is not None

    docs = [
        ("test_report", "Hero Test Report.pdf", "drive-v4-1"),
        ("safety", "LOTO Procedure.pdf", "drive-v4-2"),
        ("certificate", "ATEX Certificate.pdf", "drive-v4-3"),
        ("datasheet", "Hero Datasheet.pdf", "drive-v4-4"),
    ]
    test_doc_id = None
    for category, title, drive_id in docs:
        cat = DocumentCatalog(
            drive_file_id=drive_id,
            name=title,
            doc_category=category,
            motor_type_code=HERO_MOTOR_CODE,
        )
        session.add(cat)
        session.flush()
        doc = Document(
            title=title,
            doc_type=category,
            status="ready",
            catalog_id=cat.id,
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
        if category == "test_report":
            test_doc_id = doc.id

    assert test_doc_id
    report = PerformanceTestReport(
        document_id=test_doc_id,
        motor_type_code=HERO_MOTOR_CODE,
        standard="IEC 60034",
        status="extracted",
    )
    session.add(report)
    session.flush()
    session.add(
        TestMeasurement(
            report_id=report.id,
            document_id=test_doc_id,
            parameter="efficiency",
            unit="%",
            measured_value="94.2",
            numeric_value=94.2,
        )
    )
    session.add(
        TestMeasurement(
            report_id=report.id,
            document_id=test_doc_id,
            parameter="temperature_rise",
            unit="K",
            measured_value="72",
            numeric_value=72.0,
        )
    )
    session.commit()
    return motor.id


def main() -> int:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()

    print("Phase 4 validation — seeding hero motor…")
    motor_id = _seed(session)
    router = QueryRouter(session)
    copilot = CopilotService(session)

    print("Checking Architecture §16 demo questions…")
    for question, expected_intent in DEMO_QUESTIONS:
        route = router.route(question, motor_id=motor_id)
        assert route.intent == expected_intent, (question, route.intent)
        answer = copilot.chat(ChatRequest(message=question, motor_id=motor_id))
        assert answer.answer.strip(), question
        assert answer.citations is not None
        print(f"  OK [{route.intent}] {question[:64]}…")
        fb = copilot.submit_feedback(
            FeedbackRequest(
                rating=5,
                session_id=answer.session_id,
                message_id=answer.message_id,
            )
        )
        assert fb.id

    # SSE smoke (consume events)
    print("Checking SSE stream…")
    events = list(
        copilot.chat_sse(
            ChatRequest(
                message=DEMO_QUESTIONS[0][0],
                motor_id=motor_id,
                stream=True,
            )
        )
    )
    assert any("event: final" in e for e in events)
    assert any("event: done" in e for e in events)
    print("  OK SSE final+done")

    print("Checking maintenance + compliance…")
    maint = MaintenanceService(session).analyze(motor_id)
    assert maint.measurement_count >= 2
    rca = RcaService(session).analyze(motor_id)
    assert len(rca.five_why) == 5
    compliance = ComplianceEngine(session).assess_motor(motor_id)
    assert compliance["met"] >= 1
    print(
        f"  OK trends={len(maint.trends)} anomalies={len(maint.anomalies)} "
        f"compliance={compliance['coverage']}"
    )

    print("Phase 4 validation gate PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
