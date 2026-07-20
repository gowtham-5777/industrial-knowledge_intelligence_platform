"""Citation formatter, resolver, and retrieval traces (Milestone 2.8)."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.chunks import DocumentChunk, RetrievalTrace
from app.db.repositories.base import BaseRepository

_CITATION_RE = re.compile(
    r"\[(?P<doc>[0-9a-fA-F\-]{36}):(?P<chunk>[0-9a-fA-F\-]{36})\]"
)


def format_citation(document_id: str, chunk_id: str) -> str:
    """Architecture citation format: [doc_id:chunk_id]."""
    return f"[{document_id}:{chunk_id}]"


def extract_citations(text: str) -> list[tuple[str, str]]:
    return [
        (m.group("doc"), m.group("chunk")) for m in _CITATION_RE.finditer(text or "")
    ]


class RetrievalTraceRepository(BaseRepository[RetrievalTrace]):
    model = RetrievalTrace


class CitationService:
    """Format / verify citations and persist retrieval traces."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.traces = RetrievalTraceRepository(session)

    def format_from_results(self, results: list[dict[str, Any]]) -> list[str]:
        refs = []
        for item in results:
            doc_id = item.get("document_id")
            chunk_id = item.get("chunk_id")
            if doc_id and chunk_id:
                refs.append(format_citation(str(doc_id), str(chunk_id)))
        return refs

    def verify(self, text: str) -> dict[str, Any]:
        citations = extract_citations(text)
        resolved = []
        missing = []
        for doc_id, chunk_id in citations:
            chunk = self.session.get(DocumentChunk, chunk_id)
            if chunk is None or chunk.document_id != doc_id:
                missing.append(format_citation(doc_id, chunk_id))
            else:
                resolved.append(
                    {
                        "citation": format_citation(doc_id, chunk_id),
                        "chunk_id": chunk_id,
                        "document_id": doc_id,
                        "section_path": chunk.section_path,
                        "page": chunk.page,
                        "ok": True,
                    }
                )
        coverage = len(resolved) / len(citations) if citations else 1.0
        return {
            "citations": citations,
            "resolved": resolved,
            "missing": missing,
            "coverage": coverage,
            "valid": len(missing) == 0,
        }

    def confidence_inputs(
        self,
        *,
        retrieval_scores: list[float],
        citation_coverage: float,
        graph_path_strength: float = 0.0,
    ) -> dict[str, Any]:
        avg_retrieval = (
            sum(retrieval_scores) / len(retrieval_scores) if retrieval_scores else 0.0
        )
        confidence = (
            0.5 * avg_retrieval
            + 0.35 * citation_coverage
            + 0.15 * max(0.0, min(1.0, graph_path_strength))
        )
        return {
            "avg_retrieval_score": avg_retrieval,
            "citation_coverage": citation_coverage,
            "graph_path_strength": graph_path_strength,
            "confidence": round(confidence, 4),
        }

    def persist_trace(
        self,
        *,
        query_text: str,
        results: list[dict[str, Any]],
        motor_type_code: str | None = None,
        asset_id: str | None = None,
        pipeline: str = "hybrid",
        graph_path_strength: float = 0.0,
    ) -> RetrievalTrace:
        citations = self.format_from_results(results)
        verification = self.verify(" ".join(citations))
        scores = [
            float(r.get("rerank_score") or r.get("score") or 0.0) for r in results
        ]
        conf = self.confidence_inputs(
            retrieval_scores=scores,
            citation_coverage=float(verification["coverage"]),
            graph_path_strength=graph_path_strength,
        )
        row = RetrievalTrace(
            query_text=query_text,
            asset_id=asset_id,
            motor_type_code=motor_type_code,
            result_chunk_ids=[r.get("chunk_id") for r in results],
            citation_refs=citations,
            scores={"per_result": scores, **conf},
            confidence=conf["confidence"],
            pipeline=pipeline,
            extra_metadata={"verification": verification},
        )
        self.session.add(row)
        self.session.flush()
        return row

    def get_trace(self, trace_id: str) -> RetrievalTrace | None:
        return self.session.get(RetrievalTrace, trace_id)
