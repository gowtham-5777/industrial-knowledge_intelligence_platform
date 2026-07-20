"""Shared Copilot / agent tools wrapping Phase 2–3 services (Milestone 4.2)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.compliance_engine import ComplianceEngine
from app.citations.service import CitationService, format_citation
from app.core.config import Settings, get_settings
from app.db.models.extraction import PerformanceTestReport, TestMeasurement
from app.graph.subgraph import GraphSubgraphService
from app.knowledge.retrieval import HybridRetrievalService
from app.motor360.service import Motor360Service
from app.motors.documents import get_linked_documents, resolve_motor_model
from app.observability import get_logger
from app.timeline.service import TimelineService

_logger = get_logger(__name__)

ToolFn = Callable[..., dict[str, Any]]


class AgentTools:
    """Deterministic tool surface for LangGraph nodes."""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.motor360 = Motor360Service(session)
        self.timeline = TimelineService(session)
        self.retrieval = HybridRetrievalService(session, self.settings)
        self.citations = CitationService(session)
        self.graph = GraphSubgraphService(session)
        self.compliance = ComplianceEngine(session)

    def get_motor_360(self, motor_id: str) -> dict[str, Any]:
        try:
            bundle = self.motor360.get_bundle(motor_id)
            motor = bundle.get("motor") or {}
            return {
                "ok": True,
                "motor": {
                    "id": motor.get("id"),
                    "code": motor.get("code"),
                    "name": motor.get("name"),
                    "frame_size": motor.get("frame_size"),
                    "power_kw": motor.get("power_kw"),
                    "voltage": motor.get("voltage"),
                    "ie_class": motor.get("ie_class"),
                },
                "health": bundle.get("health"),
                "summary": bundle.get("summary"),
                "document_counts": {
                    k: len(v) if isinstance(v, list) else 0
                    for k, v in (bundle.get("documents") or {}).items()
                },
            }
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "tool_get_motor_360_failed", extra={"error": str(exc)}
            )
            return {"ok": False, "error": str(exc)}

    def get_motor_timeline(self, motor_id: str) -> dict[str, Any]:
        try:
            out = self.timeline.list_events(motor_id)
            events = out.model_dump() if hasattr(out, "model_dump") else out
            return {"ok": True, "timeline": events}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_test_history(self, motor_id: str) -> dict[str, Any]:
        try:
            model = resolve_motor_model(self.session, motor_id)
            docs = get_linked_documents(self.session, model)
            doc_ids = [d.id for d in docs]
            if not doc_ids:
                return {"ok": True, "reports": [], "measurements": []}

            reports = list(
                self.session.scalars(
                    select(PerformanceTestReport).where(
                        PerformanceTestReport.document_id.in_(doc_ids)
                    )
                ).all()
            )
            report_ids = [r.id for r in reports]
            measurements: list[TestMeasurement] = []
            if report_ids:
                measurements = list(
                    self.session.scalars(
                        select(TestMeasurement)
                        .where(TestMeasurement.report_id.in_(report_ids))
                        .order_by(TestMeasurement.parameter.asc())
                    ).all()
                )
            # Also pull measurements linked directly by document
            more = list(
                self.session.scalars(
                    select(TestMeasurement).where(
                        TestMeasurement.document_id.in_(doc_ids)
                    )
                ).all()
            )
            seen = {m.id for m in measurements}
            for m in more:
                if m.id not in seen:
                    measurements.append(m)

            return {
                "ok": True,
                "motor_code": model.code,
                "reports": [
                    {
                        "id": r.id,
                        "document_id": r.document_id,
                        "standard": r.standard,
                        "serial_number": r.serial_number,
                        "drawing_number": r.drawing_number,
                    }
                    for r in reports
                ],
                "measurements": [
                    {
                        "parameter": m.parameter,
                        "unit": m.unit,
                        "rated_value": m.rated_value,
                        "measured_value": m.measured_value,
                        "numeric_value": m.numeric_value,
                        "document_id": m.document_id,
                        "page": m.page,
                    }
                    for m in measurements[:40]
                ],
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def get_compliance_status(self, motor_id: str) -> dict[str, Any]:
        try:
            return {"ok": True, **self.compliance.assess_motor(motor_id)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def search_knowledge(
        self,
        query: str,
        *,
        motor_id: str | None = None,
        drawing_number: str | None = None,
        doc_category: str | None = None,
        limit: int = 8,
    ) -> dict[str, Any]:
        motor_code = None
        asset_id = None
        if motor_id:
            try:
                model = resolve_motor_model(self.session, motor_id)
                motor_code = model.code
                asset_id = model.asset_id
            except Exception:  # noqa: BLE001
                pass
        try:
            result = self.retrieval.retrieve(
                query,
                limit=limit,
                motor_type_code=motor_code,
                drawing_number=drawing_number,
                doc_category=doc_category,
                asset_id=asset_id,
            )
            hits = result.get("results") or result.get("items") or []
            citations = []
            for item in hits:
                doc_id = item.get("document_id")
                chunk_id = item.get("chunk_id") or item.get("id")
                if doc_id and chunk_id:
                    citations.append(
                        {
                            "citation": format_citation(str(doc_id), str(chunk_id)),
                            "document_id": doc_id,
                            "chunk_id": chunk_id,
                            "text": (
                                item.get("text") or item.get("parent_section") or ""
                            )[:400],
                            "score": item.get("rerank_score") or item.get("score"),
                            "doc_category": item.get("doc_category"),
                        }
                    )
            trace = self.citations.persist_trace(
                query_text=query,
                results=hits,
                motor_type_code=motor_code,
                asset_id=asset_id,
            )
            return {
                "ok": True,
                "hits": citations,
                "retrieval_trace_id": getattr(trace, "id", None),
            }
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "tool_search_knowledge_failed", extra={"error": str(exc)}
            )
            # Soft degrade: linked document titles only
            titles: list[dict[str, Any]] = []
            if motor_id:
                try:
                    model = resolve_motor_model(self.session, motor_id)
                    for doc in get_linked_documents(self.session, model)[:8]:
                        titles.append(
                            {
                                "document_id": doc.id,
                                "title": doc.title,
                                "doc_type": doc.doc_type,
                                "citation": None,
                                "text": doc.title,
                            }
                        )
                except Exception:  # noqa: BLE001
                    pass
            return {"ok": True, "hits": titles, "degraded": True, "error": str(exc)}

    def traverse_motor_graph(self, motor_id: str) -> dict[str, Any]:
        try:
            subgraph = self.graph.build(motor_id)
            payload = (
                subgraph.model_dump() if hasattr(subgraph, "model_dump") else subgraph
            )
            return {"ok": True, "subgraph": payload}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def dispatch(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        mapping: dict[str, ToolFn] = {
            "get_motor_360": self.get_motor_360,
            "get_motor_timeline": self.get_motor_timeline,
            "get_test_history": self.get_test_history,
            "get_compliance_status": self.get_compliance_status,
            "search_knowledge": self.search_knowledge,
            "traverse_motor_graph": self.traverse_motor_graph,
        }
        fn = mapping.get(tool_name)
        if fn is None:
            return {"ok": False, "error": f"unknown tool: {tool_name}"}
        return fn(**kwargs)
