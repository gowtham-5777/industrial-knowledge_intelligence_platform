"""Hybrid retrieval engine (Milestone 2.7)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models.chunks import DocumentChunk
from app.graph.sync import GraphSyncService
from app.indexing.vector_service import VectorIndexService
from app.observability import get_logger

_logger = get_logger(__name__)


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    *,
    k: int = 60,
) -> list[tuple[str, float]]:
    """RRF: score = Σ 1 / (k + rank)."""
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, item_id in enumerate(ranked, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def simple_rerank(
    query: str,
    candidates: list[dict[str, Any]],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Lightweight lexical reranker (no external cross-encoder dependency)."""
    tokens = {t.lower() for t in query.split() if len(t) > 2}
    scored: list[tuple[float, dict[str, Any]]] = []
    for item in candidates:
        text = (item.get("text") or item.get("parent_section") or "").lower()
        overlap = sum(1 for t in tokens if t in text)
        base = float(item.get("score") or 0.0)
        scored.append((base + 0.05 * overlap, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for score, item in scored[:limit]:
        enriched = dict(item)
        enriched["rerank_score"] = score
        out.append(enriched)
    return out


class HybridRetrievalService:
    """Parallel vector + keyword + graph expansion → RRF → parent promotion → rerank."""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        *,
        vector_service: VectorIndexService | None = None,
        graph_service: GraphSyncService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.vectors = vector_service or VectorIndexService(session, self.settings)
        self.graph = graph_service or GraphSyncService(session, self.settings)

    def retrieve(
        self,
        query: str,
        *,
        limit: int = 8,
        motor_type_code: str | None = None,
        drawing_number: str | None = None,
        doc_category: str | None = None,
        asset_id: str | None = None,
        user: Any | None = None,
        apply_acl: bool = True,
    ) -> dict[str, Any]:
        # NOTE: only channels that never touch ``self.session`` (vector/graph —
        # embedding + Qdrant + Neo4j calls) run on background threads. The
        # SQLAlchemy ``Session`` is not thread-safe, so the keyword-search
        # channel (which queries ``self.session`` directly) runs synchronously
        # on the calling thread to avoid corrupting an in-progress transaction.
        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_vector = pool.submit(
                self.vectors.search,
                query,
                limit=limit * 2,
                doc_category=doc_category,
                drawing_number=drawing_number,
                motor_model=motor_type_code,
                asset_id=asset_id,
            )
            fut_graph = pool.submit(
                self._graph_expand,
                motor_type_code=motor_type_code,
                drawing_number=drawing_number,
            )
            keyword_hits = self._keyword_search(
                query,
                limit=limit * 2,
                motor_type_code=motor_type_code,
                drawing_number=drawing_number,
                doc_category=doc_category,
            )
            vector_hits = fut_vector.result()
            graph_doc_ids = fut_graph.result()

        vector_ids = [
            (h.get("payload") or {}).get("chunk_id") or h.get("id") for h in vector_hits
        ]
        keyword_ids = [h["chunk_id"] for h in keyword_hits]
        graph_chunk_ids = self._chunks_for_documents(graph_doc_ids, limit=limit * 2)

        fused = reciprocal_rank_fusion(
            [
                [i for i in vector_ids if i],
                [i for i in keyword_ids if i],
                [i for i in graph_chunk_ids if i],
            ]
        )

        chunk_map = self._load_chunks([cid for cid, _ in fused[: limit * 3]])
        candidates: list[dict[str, Any]] = []
        for chunk_id, rrf_score in fused:
            chunk = chunk_map.get(chunk_id)
            if not chunk:
                continue
            candidates.append(
                {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "text": chunk.text,
                    "parent_section": chunk.parent_section,
                    "section_path": chunk.section_path,
                    "page": chunk.page,
                    "doc_category": chunk.doc_category,
                    "drawing_numbers": list(chunk.drawing_numbers or []),
                    "motor_models": list(chunk.motor_models or []),
                    "score": rrf_score,
                    "citation": f"[{chunk.document_id}:{chunk.id}]",
                }
            )

        # Parent document promotion — prefer parent_section text for citation context
        for item in candidates:
            if (
                item.get("parent_section")
                and item["parent_section"] not in item["text"]
            ):
                item["promoted_context"] = item["parent_section"]

        reranked = simple_rerank(query, candidates, limit=limit)

        # Milestone 5.1.2 — ACL filter before LLM sees content
        if apply_acl and user is not None:
            from app.auth.acl import DocumentAclFilter

            reranked = DocumentAclFilter(self.session).filter_retrieval_results(
                reranked, user=user
            )

        context = self._assemble_context(reranked)

        _logger.info(
            "hybrid retrieval complete",
            extra={
                "query_len": len(query),
                "vector_hits": len(vector_hits),
                "keyword_hits": len(keyword_hits),
                "results": len(reranked),
            },
        )
        return {
            "query": query,
            "results": reranked,
            "context": context,
            "channels": {
                "vector": len(vector_hits),
                "keyword": len(keyword_hits),
                "graph_docs": len(graph_doc_ids),
            },
        }

    def _keyword_search(
        self,
        query: str,
        *,
        limit: int,
        motor_type_code: str | None,
        drawing_number: str | None,
        doc_category: str | None,
    ) -> list[dict[str, Any]]:
        from sqlalchemy import and_

        tokens = [t for t in query.split() if len(t) > 2][:8]
        stmt = select(DocumentChunk)
        clauses = []
        if doc_category:
            clauses.append(DocumentChunk.doc_category == doc_category)
        if tokens:
            clauses.append(or_(*[DocumentChunk.text.ilike(f"%{t}%") for t in tokens]))
        if clauses:
            stmt = stmt.where(and_(*clauses))
        stmt = stmt.limit(limit * 3)
        rows = list(self.session.scalars(stmt).all())
        out = []
        for row in rows:
            if motor_type_code and motor_type_code not in (row.motor_models or []):
                if motor_type_code.lower() not in (row.text or "").lower():
                    continue
            if drawing_number and drawing_number not in (row.drawing_numbers or []):
                if drawing_number.lower() not in (row.text or "").lower():
                    continue
            out.append(
                {
                    "chunk_id": row.id,
                    "document_id": row.document_id,
                    "text": row.text,
                }
            )
        return out[:limit]

    def _graph_expand(
        self,
        *,
        motor_type_code: str | None,
        drawing_number: str | None,
    ) -> list[str]:
        if not motor_type_code:
            return []
        neighborhood = self.graph.neighborhood(motor_type_code)
        doc_ids = [
            d.get("id")
            for d in neighborhood.get("documents") or []
            if d and d.get("id")
        ]
        if drawing_number:
            # Prefer docs mentioning drawing
            filtered = [
                d.get("id")
                for d in neighborhood.get("documents") or []
                if drawing_number in str(d)
            ]
            if filtered:
                return [i for i in filtered if i]
        return [i for i in doc_ids if i]

    def _chunks_for_documents(
        self, document_ids: list[str], *, limit: int
    ) -> list[str]:
        if not document_ids:
            return []
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id.in_(document_ids))
            .order_by(DocumentChunk.chunk_index.asc())
            .limit(limit)
        )
        return [c.id for c in self.session.scalars(stmt).all()]

    def _load_chunks(self, chunk_ids: list[str]) -> dict[str, DocumentChunk]:
        if not chunk_ids:
            return {}
        rows = self.session.scalars(
            select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))
        ).all()
        return {r.id: r for r in rows}

    @staticmethod
    def _assemble_context(results: list[dict[str, Any]]) -> str:
        # Milestone 5.6.3 — isolate retrieved text from system instructions
        from app.security.prompt_guard import assemble_isolated_context

        return assemble_isolated_context(results)
