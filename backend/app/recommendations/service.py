"""Template-based recommendation engine (Phase 3).

Hackathon-scoped: recommendation *cards* are template-driven (install /
safety / compliance / maintenance) so they never hallucinate, and each card
carries citations back to indexed documents when available via
``HybridRetrievalService``. No LangGraph dependency is required.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models.documents import Document
from app.db.models.motors import MotorModel, MotorRecommendation
from app.knowledge.retrieval import HybridRetrievalService
from app.motors.documents import get_linked_documents, resolve_motor_model
from app.observability import get_logger
from app.recommendations.schemas import CitationRef, RecommendationOut, RecommendationsOut

_logger = get_logger(__name__)

_MODEL_VERSION = "template:v1"

_CATEGORY_DOC_TYPES: dict[str, set[str]] = {
    "install": {
        "datasheet",
        "drawing",
        "drawing_outline",
        "drawing_dimension",
        "drawing_mechanical",
        "drawing_connection",
        "drawing_terminal",
    },
    "safety": {"safety", "sop"},
    "compliance": {"certificate", "regulation"},
    "maintenance": {"maintenance", "manual", "sop", "test_report", "checklist", "work_order"},
}


class RecommendationService:
    """Generate, cache, and refresh recommendation cards for a motor."""

    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    def generate(self, motor_id: str, *, force: bool = False) -> RecommendationsOut:
        model = resolve_motor_model(self.session, motor_id)

        if not force:
            cached = self._get_cached(model.id)
            if cached is not None:
                return cached
        return self.refresh(model.id)

    def refresh(self, motor_id: str) -> RecommendationsOut:
        """Force regeneration and re-cache."""
        model = resolve_motor_model(self.session, motor_id)
        documents = get_linked_documents(self.session, model)
        docs_by_category = self._group_by_category(documents)
        chunk_hits = self._retrieve_context(model)

        items = [
            self._install_card(model, docs_by_category, chunk_hits),
            self._safety_card(model, docs_by_category, chunk_hits),
            self._compliance_card(model, docs_by_category, chunk_hits),
            self._maintenance_card(model, docs_by_category, chunk_hits),
        ]

        generated_at = datetime.now(timezone.utc)
        result = RecommendationsOut(
            motor_id=model.id,
            items=items,
            generated_at=generated_at,
            model_version=_MODEL_VERSION,
            cached=False,
        )
        self._persist(model, result)
        _logger.info(
            "recommendations generated",
            extra={"motor_id": model.id, "count": len(items)},
        )
        return result

    def _get_cached(self, model_id: str) -> RecommendationsOut | None:
        stmt = (
            select(MotorRecommendation)
            .where(MotorRecommendation.model_id == model_id)
            .order_by(MotorRecommendation.generated_at.desc())
            .limit(1)
        )
        row = self.session.scalars(stmt).first()
        if row is None:
            return None
        payload = row.recommendations
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (ValueError, TypeError):
                return None
        return RecommendationsOut(
            motor_id=model_id,
            items=[RecommendationOut.model_validate(i) for i in payload],
            generated_at=row.generated_at,
            model_version=row.model_version,
            cached=True,
        )

    def _persist(self, model: MotorModel, result: RecommendationsOut) -> None:
        row = MotorRecommendation(
            recommendations=[i.model_dump() for i in result.items],
            generated_at=result.generated_at,
            model_version=result.model_version,
            model_id=model.id,
        )
        self.session.add(row)
        self.session.commit()

    @staticmethod
    def _group_by_category(documents: list[Document]) -> dict[str, list[Document]]:
        grouped: dict[str, list[Document]] = {}
        for doc in documents:
            category = (doc.catalog_entry.doc_category if doc.catalog_entry else doc.doc_type) or "uncategorized"
            grouped.setdefault(category, []).append(doc)
        return grouped

    def _retrieve_context(self, model: MotorModel) -> list[dict[str, Any]]:
        try:
            retrieval = HybridRetrievalService(self.session, self.settings)
            result = retrieval.retrieve(
                f"{model.name} installation safety compliance maintenance guidance",
                limit=10,
                motor_type_code=model.code,
            )
            return result.get("results", [])
        except Exception as exc:  # noqa: BLE001
            # See SummaryService._gather_citations: roll back so template
            # recommendations can still be persisted without citations.
            self.session.rollback()
            _logger.warning(
                "retrieval unavailable for recommendation citations",
                extra={"motor_id": model.id, "error": str(exc)},
            )
            return []

    def _citations_for(
        self,
        category: str,
        docs_by_category: dict[str, list[Document]],
        chunk_hits: list[dict[str, Any]],
    ) -> list[CitationRef]:
        wanted_types = _CATEGORY_DOC_TYPES.get(category, set())
        relevant_doc_ids = {
            d.id for cat, docs in docs_by_category.items() if cat in wanted_types for d in docs
        }
        citations: list[CitationRef] = []
        for hit in chunk_hits:
            doc_id = hit.get("document_id")
            doc_category = hit.get("doc_category") or ""
            if doc_id and (doc_id in relevant_doc_ids or doc_category in wanted_types):
                citations.append(CitationRef(doc_id=doc_id, chunk_id=hit.get("chunk_id")))
        if citations:
            return citations[:3]
        if relevant_doc_ids:
            return [CitationRef(doc_id=doc_id) for doc_id in list(relevant_doc_ids)[:3]]
        return []

    def _install_card(
        self,
        model: MotorModel,
        docs_by_category: dict[str, list[Document]],
        chunk_hits: list[dict[str, Any]],
    ) -> RecommendationOut:
        citations = self._citations_for("install", docs_by_category, chunk_hits)
        mounting = model.mounting or "the specified mounting configuration"
        cooling = model.cooling or "the specified cooling method"
        rationale = (
            f"Confirm mounting orientation matches {mounting} and cooling arrangement "
            f"({cooling}) before commissioning {model.name}."
        )
        if not citations:
            rationale += " No installation drawing/datasheet indexed — verify against nameplate."
        return RecommendationOut(
            title="Verify mounting & cooling arrangement before commissioning",
            category="install",
            rationale=rationale,
            confidence=0.85 if citations else 0.4,
            citations=citations,
        )

    def _safety_card(
        self,
        model: MotorModel,
        docs_by_category: dict[str, list[Document]],
        chunk_hits: list[dict[str, Any]],
    ) -> RecommendationOut:
        citations = self._citations_for("safety", docs_by_category, chunk_hits)
        voltage = model.voltage or "the rated voltage"
        rationale = (
            f"Apply lockout/tagout and de-energize at {voltage} before opening the "
            f"terminal box or performing maintenance on {model.name}."
        )
        if not citations:
            rationale += " No dedicated safety document indexed — apply site LOTO standard procedure."
        return RecommendationOut(
            title="Lockout/tagout before electrical work",
            category="safety",
            rationale=rationale,
            confidence=0.85 if citations else 0.5,
            citations=citations,
        )

    def _compliance_card(
        self,
        model: MotorModel,
        docs_by_category: dict[str, list[Document]],
        chunk_hits: list[dict[str, Any]],
    ) -> RecommendationOut:
        citations = self._citations_for("compliance", docs_by_category, chunk_hits)
        ie_class = model.ie_class or "an unspecified efficiency class"
        rationale = (
            f"Motor is rated {ie_class}; confirm certification remains valid and matches "
            "site energy-efficiency regulations (e.g. IEC 60034-30-1)."
        )
        if not citations:
            rationale += " No certification document indexed — request current certificate."
        return RecommendationOut(
            title="Confirm efficiency certification is current",
            category="compliance",
            rationale=rationale,
            confidence=0.8 if citations else 0.35,
            citations=citations,
        )

    def _maintenance_card(
        self,
        model: MotorModel,
        docs_by_category: dict[str, list[Document]],
        chunk_hits: list[dict[str, Any]],
    ) -> RecommendationOut:
        citations = self._citations_for("maintenance", docs_by_category, chunk_hits)
        rationale = (
            f"Schedule periodic bearing/vibration inspection for {model.name} per the "
            "manufacturer maintenance SOP and test-report baseline values."
        )
        if not citations:
            rationale += " No maintenance SOP or test report indexed — use generic IE-motor maintenance interval."
        return RecommendationOut(
            title="Schedule periodic bearing & vibration inspection",
            category="maintenance",
            rationale=rationale,
            confidence=0.8 if citations else 0.4,
            citations=citations,
        )
