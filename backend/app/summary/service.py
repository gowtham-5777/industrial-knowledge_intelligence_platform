"""AI asset summary generation + cache (Phase 3).

Deterministic template summary from registry specs + linked document
inventory by default. When ``OPENAI_API_KEY`` is configured (and the app is
not running in ``test`` mode) the deterministic overview is optionally
rewritten by an LLM for a more natural narrative — the structured fields
(key_specs, knowledge_gaps, citations) always come from verifiable data, and
generation never fails if the LLM call is unavailable.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models.motors import MotorAiSummary, MotorModel
from app.knowledge.retrieval import HybridRetrievalService
from app.motors.documents import get_linked_documents, resolve_motor_model
from app.observability import get_logger
from app.summary.schemas import KeySpecOut, SummaryOut

_logger = get_logger(__name__)

_TEMPLATE_MODEL_VERSION = "template:v1"
_LLM_MODEL_VERSION = "openai:gpt-4o-mini"

_SPEC_LABELS: tuple[tuple[str, str, str], ...] = (
    ("frame_size", "Frame size", "{}"),
    ("power_kw", "Power", "{} kW"),
    ("voltage", "Voltage", "{}"),
    ("ie_class", "Efficiency class", "{}"),
    ("poles", "Poles", "{}"),
    ("mounting", "Mounting", "{}"),
    ("cooling", "Cooling", "{}"),
)

_EXPECTED_CATEGORIES: dict[str, str] = {
    "datasheet": "Datasheet",
    "test_report": "Test report",
    "certificate": "Certification",
    "manual": "Manual",
    "drawing": "Engineering drawing",
}

_NO_KNOWLEDGE_NOTE = (
    "Not available in indexed knowledge — this summary is based only on "
    "structured registry fields; no indexed document excerpts were found."
)


class SummaryService:
    """Generate and cache the AI asset summary for a motor."""

    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    def generate(self, motor_id: str, *, force: bool = False) -> SummaryOut:
        model = resolve_motor_model(self.session, motor_id)

        if not force:
            cached = self._get_cached(model.id)
            if cached is not None:
                return cached

        documents = get_linked_documents(self.session, model)
        key_specs = self._build_key_specs(model)
        gaps: list[str] = []

        for field_name, label, _fmt in _SPEC_LABELS:
            if getattr(model, field_name, None) is None:
                gaps.append(f"{label} not available in indexed knowledge")

        categories_present = {
            (d.catalog_entry.doc_category if d.catalog_entry else d.doc_type) or ""
            for d in documents
        }
        has_drawing = any(c.startswith("drawing") for c in categories_present)
        for category, label in _EXPECTED_CATEGORIES.items():
            if category == "drawing":
                if not has_drawing:
                    gaps.append(f"{label} not available in indexed knowledge")
                continue
            if category not in categories_present:
                gaps.append(f"{label} not available in indexed knowledge")

        citations, context = self._gather_citations(model)
        doc_inventory = self._doc_inventory(documents)

        overview = self._deterministic_overview(model, key_specs, doc_inventory)
        model_version = _TEMPLATE_MODEL_VERSION
        if self.settings.openai_api_key and self.settings.app_env != "test":
            llm_overview = self._llm_overview(model, key_specs, doc_inventory, context)
            if llm_overview:
                overview = llm_overview
                model_version = _LLM_MODEL_VERSION

        honesty_note = (
            _NO_KNOWLEDGE_NOTE
            if not citations
            else (
                f"Grounded in {len(citations)} indexed document citation(s); "
                "specification fields come from the asset registry."
            )
        )

        generated_at = datetime.now(UTC)
        source_doc_ids = list({d.id for d in documents})
        summary = SummaryOut(
            motor_id=model.id,
            overview=overview,
            key_specs=key_specs,
            knowledge_gaps=gaps,
            citations=citations,
            honesty_note=honesty_note,
            generated_at=generated_at,
            model_version=model_version,
            source_doc_ids=source_doc_ids,
            cached=False,
        )
        self._persist(model, summary)
        _logger.info(
            "motor summary generated",
            extra={
                "motor_id": model.id,
                "model_version": model_version,
                "citations": len(citations),
                "gaps": len(gaps),
            },
        )
        return summary

    def _get_cached(self, model_id: str) -> SummaryOut | None:
        stmt = (
            select(MotorAiSummary)
            .where(MotorAiSummary.model_id == model_id)
            .order_by(MotorAiSummary.generated_at.desc())
            .limit(1)
        )
        row = self.session.scalars(stmt).first()
        if row is None:
            return None
        try:
            payload = json.loads(row.summary_text)
        except (ValueError, TypeError):
            return None
        payload["cached"] = True
        payload["generated_at"] = row.generated_at
        payload["model_version"] = row.model_version
        payload["source_doc_ids"] = row.source_doc_ids or []
        return SummaryOut.model_validate(payload)

    def _persist(self, model: MotorModel, summary: SummaryOut) -> None:
        row = MotorAiSummary(
            summary_text=summary.model_dump_json(),
            source_doc_ids=summary.source_doc_ids,
            model_version=summary.model_version,
            generated_at=summary.generated_at,
            model_id=model.id,
        )
        self.session.add(row)
        self.session.flush()

    @staticmethod
    def _build_key_specs(model: MotorModel) -> list[KeySpecOut]:
        specs: list[KeySpecOut] = []
        for field_name, label, fmt in _SPEC_LABELS:
            value = getattr(model, field_name, None)
            if value is not None:
                specs.append(KeySpecOut(label=label, value=fmt.format(value)))
        return specs

    @staticmethod
    def _doc_inventory(documents: list[Any]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for d in documents:
            category = (
                d.catalog_entry.doc_category if d.catalog_entry else d.doc_type
            ) or "uncategorized"
            counts[category] = counts.get(category, 0) + 1
        return counts

    def _gather_citations(self, model: MotorModel) -> tuple[list[str], str]:
        try:
            retrieval = HybridRetrievalService(self.session, self.settings)
            result = retrieval.retrieve(
                f"{model.name} {model.code} specifications overview",
                limit=5,
                motor_type_code=model.code,
            )
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "retrieval unavailable for summary citations",
                extra={"motor_id": model.id, "error": str(exc)},
            )
            return [], ""
        citations = [
            r.get("citation") for r in result.get("results", []) if r.get("citation")
        ]
        return citations, result.get("context", "")

    @staticmethod
    def _deterministic_overview(
        model: MotorModel,
        key_specs: list[KeySpecOut],
        doc_inventory: dict[str, int],
    ) -> str:
        spec_text = "; ".join(f"{s.label}: {s.value}" for s in key_specs) or (
            "no structured specifications indexed"
        )
        if doc_inventory:
            doc_text = ", ".join(f"{v} {k}" for k, v in sorted(doc_inventory.items()))
        else:
            doc_text = "no linked documents indexed"
        return (
            f"{model.name} ({model.code}) — {spec_text}. "
            f"Knowledge base coverage: {doc_text}."
        )

    def _llm_overview(
        self,
        model: MotorModel,
        key_specs: list[KeySpecOut],
        doc_inventory: dict[str, int],
        context: str,
    ) -> str | None:
        try:
            from openai import OpenAI
        except ImportError:
            return None
        api_key = (self.settings.openai_api_key or "").strip()
        if not api_key:
            return None
        try:
            client = OpenAI(api_key=api_key)
            spec_lines = "\n".join(f"- {s.label}: {s.value}" for s in key_specs)
            doc_lines = "\n".join(
                f"- {v} {k} document(s)" for k, v in doc_inventory.items()
            )
            prompt = (
                "Write a concise 2-3 sentence factual overview of this "
                "industrial motor "
                "for a maintenance engineer. Only use the facts given below — do not "
                "invent specifications, dates, or capabilities.\n\n"
                f"Motor: {model.name} ({model.code})\n"
                f"Specifications:\n{spec_lines or '- none indexed'}\n"
                f"Indexed documents:\n{doc_lines or '- none indexed'}\n"
                f"Relevant excerpts:\n{context[:1500] if context else 'none'}"
            )
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=200,
            )
            text = (response.choices[0].message.content or "").strip()
            return text or None
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "llm overview generation failed; using deterministic template",
                extra={"motor_id": model.id, "error": str(exc)},
            )
            return None
