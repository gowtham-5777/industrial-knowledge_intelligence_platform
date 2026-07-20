"""Deterministic, explainable motor health/risk scoring (Phase 3).

Pure Python weighted rules — no LLM calls. ``routes.py`` in this package is
the unversioned HTTP liveness/readiness surface and is intentionally left
untouched; this module is wired into the ``motor360`` bundle and can be
called directly by any service that needs a health score.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.extraction import TestMeasurement
from app.db.models.motors import MotorHealthScore, MotorModel
from app.motors.documents import get_linked_documents, resolve_motor_model
from app.observability import get_logger

_logger = get_logger(__name__)

_SPEC_FIELDS: tuple[str, ...] = (
    "frame_size",
    "power_kw",
    "voltage",
    "ie_class",
    "poles",
    "mounting",
    "cooling",
)

_TEST_REPORT_CATEGORIES = {"test_report", "checklist"}
_CERTIFICATION_CATEGORIES = {"certificate", "regulation"}
_MANUAL_CATEGORIES = {"manual", "sop"}

# Weights sum to 100.
_WEIGHTS: dict[str, float] = {
    "datasheet": 20.0,
    "test_report": 20.0,
    "certification": 15.0,
    "manual_or_sop": 10.0,
    "drawing": 10.0,
    "spec_completeness": 15.0,
    "measurements_in_range": 10.0,
}

_MEASUREMENT_TOLERANCE = 0.10  # 10% deviation from rated value is acceptable


class EvidenceItem(BaseModel):
    factor: str
    passed: bool
    weight: float
    points: float
    text: str
    document_ids: list[str] = []


class HealthScoreOut(BaseModel):
    motor_id: str
    score: float
    risk_level: str
    evidence: list[EvidenceItem]
    computed_at: datetime


def _numeric(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def _risk_level(score: float) -> str:
    if score >= 80:
        return "low"
    if score >= 50:
        return "medium"
    return "high"


class HealthScoringService:
    """Weighted deterministic health score with cited evidence."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def compute(self, motor_id: str) -> HealthScoreOut:
        model = resolve_motor_model(self.session, motor_id)
        documents = get_linked_documents(self.session, model)

        categories: dict[str, list[Any]] = {}
        for doc in documents:
            category = (
                doc.catalog_entry.doc_category if doc.catalog_entry else doc.doc_type
            )
            categories.setdefault(category or "uncategorized", []).append(doc)

        evidence: list[EvidenceItem] = []
        total = 0.0

        total += self._score_category(
            evidence,
            factor="datasheet",
            weight=_WEIGHTS["datasheet"],
            docs=categories.get("datasheet", []),
            passed_text="Datasheet on file with rated specifications.",
            missing_text="No datasheet indexed for this motor.",
        )
        total += self._score_category(
            evidence,
            factor="test_report",
            weight=_WEIGHTS["test_report"],
            docs=[
                d
                for cat, ds in categories.items()
                if cat in _TEST_REPORT_CATEGORIES
                for d in ds
            ],
            passed_text="Performance/IEC test report on file.",
            missing_text="No test report or checklist indexed.",
        )
        total += self._score_category(
            evidence,
            factor="certification",
            weight=_WEIGHTS["certification"],
            docs=[
                d
                for cat, ds in categories.items()
                if cat in _CERTIFICATION_CATEGORIES
                for d in ds
            ],
            passed_text="Certification/compliance document on file.",
            missing_text="No certification or regulatory document indexed.",
        )
        total += self._score_category(
            evidence,
            factor="manual_or_sop",
            weight=_WEIGHTS["manual_or_sop"],
            docs=[
                d
                for cat, ds in categories.items()
                if cat in _MANUAL_CATEGORIES
                for d in ds
            ],
            passed_text="Manual or SOP available for safe operation/maintenance.",
            missing_text="No manual or SOP indexed.",
        )
        total += self._score_category(
            evidence,
            factor="drawing",
            weight=_WEIGHTS["drawing"],
            docs=[
                d
                for cat, ds in categories.items()
                if cat.startswith("drawing")
                for d in ds
            ],
            passed_text="Engineering drawing(s) on file.",
            missing_text="No engineering drawing indexed.",
        )

        completeness_points, completeness_evidence = self._score_spec_completeness(
            model
        )
        total += completeness_points
        evidence.append(completeness_evidence)

        measurement_points, measurement_evidence = self._score_measurements(documents)
        total += measurement_points
        evidence.append(measurement_evidence)

        score = round(min(100.0, max(0.0, total)), 2)
        computed_at = datetime.now(UTC)

        row = MotorHealthScore(
            score=score,
            risk_level=_risk_level(score),
            reasoning=[e.model_dump() for e in evidence],
            computed_at=computed_at,
            model_id=model.id,
        )
        self.session.add(row)
        self.session.commit()
        _logger.info(
            "health score computed",
            extra={"motor_id": model.id, "score": score, "risk_level": row.risk_level},
        )
        return HealthScoreOut(
            motor_id=model.id,
            score=score,
            risk_level=row.risk_level,
            evidence=evidence,
            computed_at=computed_at,
        )

    def get_latest(self, motor_id: str) -> HealthScoreOut | None:
        model = resolve_motor_model(self.session, motor_id)
        stmt = (
            select(MotorHealthScore)
            .where(MotorHealthScore.model_id == model.id)
            .order_by(MotorHealthScore.computed_at.desc())
            .limit(1)
        )
        row = self.session.scalars(stmt).first()
        if row is None:
            return None
        evidence = [EvidenceItem.model_validate(e) for e in (row.reasoning or [])]
        return HealthScoreOut(
            motor_id=model.id,
            score=row.score,
            risk_level=row.risk_level,
            evidence=evidence,
            computed_at=row.computed_at,
        )

    def get_or_compute(self, motor_id: str) -> HealthScoreOut:
        existing = self.get_latest(motor_id)
        if existing is not None:
            return existing
        return self.compute(motor_id)

    @staticmethod
    def _score_category(
        evidence: list[EvidenceItem],
        *,
        factor: str,
        weight: float,
        docs: list[Any],
        passed_text: str,
        missing_text: str,
    ) -> float:
        passed = bool(docs)
        points = weight if passed else 0.0
        evidence.append(
            EvidenceItem(
                factor=factor,
                passed=passed,
                weight=weight,
                points=points,
                text=passed_text if passed else missing_text,
                document_ids=[d.id for d in docs],
            )
        )
        return points

    @staticmethod
    def _score_spec_completeness(model: MotorModel) -> tuple[float, EvidenceItem]:
        present = [f for f in _SPEC_FIELDS if getattr(model, f, None) is not None]
        fraction = len(present) / len(_SPEC_FIELDS)
        points = round(_WEIGHTS["spec_completeness"] * fraction, 2)
        missing = [f for f in _SPEC_FIELDS if f not in present]
        text = f"Specification completeness {len(present)}/{len(_SPEC_FIELDS)}." + (
            f" Missing: {', '.join(missing)}." if missing else " All key specs present."
        )
        return points, EvidenceItem(
            factor="spec_completeness",
            passed=fraction >= 0.5,
            weight=_WEIGHTS["spec_completeness"],
            points=points,
            text=text,
            document_ids=[],
        )

    @staticmethod
    def _score_measurements(documents: list[Any]) -> tuple[float, EvidenceItem]:
        doc_ids = [d.id for d in documents]
        if not doc_ids:
            return 0.0, EvidenceItem(
                factor="measurements_in_range",
                passed=False,
                weight=_WEIGHTS["measurements_in_range"],
                points=0.0,
                text="No test measurements available to evaluate.",
                document_ids=[],
            )

        # Deferred import avoids a hard dependency for callers that only need docs.
        from sqlalchemy.orm import object_session

        session = object_session(documents[0])
        measurements = list(
            session.scalars(
                select(TestMeasurement).where(TestMeasurement.document_id.in_(doc_ids))
            ).all()
        )
        if not measurements:
            return 0.0, EvidenceItem(
                factor="measurements_in_range",
                passed=False,
                weight=_WEIGHTS["measurements_in_range"],
                points=0.0,
                text="No test measurements available to evaluate.",
                document_ids=[],
            )

        determinate = 0
        in_range = 0
        for m in measurements:
            rated = _numeric(m.rated_value)
            measured = (
                m.numeric_value
                if m.numeric_value is not None
                else _numeric(m.measured_value)
            )
            if rated is None or measured is None or rated == 0:
                continue
            determinate += 1
            deviation = abs(measured - rated) / abs(rated)
            if deviation <= _MEASUREMENT_TOLERANCE:
                in_range += 1

        if determinate == 0:
            return 0.0, EvidenceItem(
                factor="measurements_in_range",
                passed=False,
                weight=_WEIGHTS["measurements_in_range"],
                points=0.0,
                text=(
                    f"{len(measurements)} measurement(s) found but rated/measured "
                    "values could not be compared."
                ),
                document_ids=list({m.document_id for m in measurements}),
            )

        fraction = in_range / determinate
        points = round(_WEIGHTS["measurements_in_range"] * fraction, 2)
        return points, EvidenceItem(
            factor="measurements_in_range",
            passed=fraction >= 0.8,
            weight=_WEIGHTS["measurements_in_range"],
            points=points,
            text=(
                f"{in_range}/{determinate} measurements within "
                f"{int(_MEASUREMENT_TOLERANCE * 100)}% of rated value."
            ),
            document_ids=list({m.document_id for m in measurements}),
        )
