"""Test anomaly RCA assistant — template 5-Why + similar reports (4.4)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.tools import AgentTools
from app.core.config import Settings, get_settings
from app.motors.documents import resolve_motor_model
from app.reasoning.maintenance import MaintenanceService


class WhyStep(BaseModel):
    level: int
    question: str
    answer: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class RcaOut(BaseModel):
    motor_id: str
    motor_code: str
    anomaly: dict[str, Any] | None = None
    five_why: list[WhyStep]
    similar_reports: list[dict[str, Any]] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    honesty_note: str | None = None


_WHY_TEMPLATES: list[tuple[str, str]] = [
    (
        "Why is the measured {parameter} outside the expected band?",
        "Latest {parameter} reading of {value} differs from the historical mean "
        "of {mean} by {deviation_pct}%.",
    ),
    (
        "Why did the test condition produce this reading?",
        "Evidence from indexed test / maintenance documents suggests a process or "
        "condition factor affecting {parameter} (see similar reports).",
    ),
    (
        "Why was this factor not caught earlier?",
        "Coverage gaps in continuous indexing or missing procedure evidence may "
        "have delayed detection for motor {motor_code}.",
    ),
    (
        "Why does the current evidence set look incomplete?",
        "{honesty}",
    ),
    (
        "Why does this matter operationally?",
        "Unresolved {parameter} drift can escalate into compliance or reliability "
        "risk; recommended actions below prioritize evidence gathering first.",
    ),
]


class RcaService:
    """Template-driven 5-Why RCA grounded in maintenance anomalies + retrieval."""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.maintenance = MaintenanceService(session)
        self.tools = AgentTools(session, self.settings)

    def analyze(
        self,
        motor_id: str,
        *,
        parameter: str | None = None,
    ) -> RcaOut:
        model = resolve_motor_model(self.session, motor_id)
        maint = self.maintenance.analyze(model.id)

        anomaly = None
        if maint.anomalies:
            if parameter:
                anomaly = next(
                    (
                        a.model_dump()
                        for a in maint.anomalies
                        if parameter.lower() in a.parameter.lower()
                    ),
                    maint.anomalies[0].model_dump(),
                )
            else:
                anomaly = maint.anomalies[0].model_dump()

        ctx = {
            "parameter": (anomaly or {}).get("parameter") or parameter or "performance",
            "value": (anomaly or {}).get("value") or "n/a",
            "mean": (anomaly or {}).get("mean") or "n/a",
            "deviation_pct": (anomaly or {}).get("deviation_pct") or 0,
            "motor_code": model.code,
            "honesty": (
                "Not all historical test reports are fully indexed yet — "
                "RCA is limited to available evidence."
                if maint.measurement_count < 3
                else "Multiple measurements are available for comparison."
            ),
        }

        five_why: list[WhyStep] = []
        for i, (q_tmpl, a_tmpl) in enumerate(_WHY_TEMPLATES, start=1):
            five_why.append(
                WhyStep(
                    level=i,
                    question=q_tmpl.format(**ctx),
                    answer=a_tmpl.format(**ctx),
                    evidence=[],
                )
            )

        search = self.tools.search_knowledge(
            f"{ctx['parameter']} anomaly test report similar cases {model.code}",
            motor_id=model.id,
            doc_category="test_report",
            limit=6,
        )
        similar = search.get("hits") or []
        if five_why:
            five_why[1].evidence = similar[:3]
            five_why[3].evidence = similar[:2]

        actions = [
            "Re-review latest performance test report against IEC 60034 limits.",
            "Confirm LOTO / maintenance SOP was applied before last intervention.",
            "Index remaining test reports for this motor "
            "to strengthen trend confidence.",
        ]
        if anomaly and anomaly.get("severity") == "high":
            actions.insert(
                0,
                f"Escalate {anomaly.get('parameter')} deviation "
                f"for reliability review.",
            )

        confidence = 0.55
        if anomaly:
            confidence += 0.15
        if similar:
            confidence += 0.1
        if maint.measurement_count >= 3:
            confidence += 0.1

        honesty = None
        if not anomaly:
            honesty = (
                "No rule-assisted anomaly detected — RCA workspace shows a "
                "template investigation path for the hero motor demo."
            )
            # Still provide a synthetic anchor so the UI is useful
            anomaly = {
                "parameter": parameter or "efficiency",
                "value": None,
                "mean": None,
                "deviation_pct": 0,
                "severity": "info",
                "rationale": "No anomaly flagged; exploratory RCA mode.",
            }

        return RcaOut(
            motor_id=model.id,
            motor_code=model.code,
            anomaly=anomaly,
            five_why=five_why,
            similar_reports=similar,
            recommended_actions=actions,
            confidence=round(min(confidence, 0.95), 3),
            honesty_note=honesty,
        )
