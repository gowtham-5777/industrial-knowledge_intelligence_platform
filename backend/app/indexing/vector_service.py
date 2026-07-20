"""Upsert embedded chunks into Qdrant (Milestone 2.5)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.db.models.chunks import DocumentChunk
from app.indexing.embedding_service import EmbeddingService
from app.indexing.qdrant_index import InMemoryQdrantIndex, QdrantIndex
from app.observability import get_logger

_logger = get_logger(__name__)


def _point_id(chunk_id: str) -> str:
    """Qdrant accepts UUID strings."""
    try:
        return str(UUID(chunk_id))
    except ValueError:
        # Deterministic UUID5-like fallback from hex digest
        import hashlib

        digest = hashlib.md5(chunk_id.encode("utf-8")).hexdigest()
        return str(UUID(digest))


class VectorIndexService:
    """Embed (if needed) + upsert / delete / reindex in Qdrant."""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        *,
        index: QdrantIndex | InMemoryQdrantIndex | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.embeddings = embedding_service or EmbeddingService(session, self.settings)
        if index is not None:
            self.index = index
        elif self.settings.app_env == "test":
            self.index = InMemoryQdrantIndex(
                dimensions=self.embeddings.provider.dimensions
            )
        else:
            try:
                self.index = QdrantIndex(self.settings)
                self.index.ensure_collection()
            except Exception as exc:  # noqa: BLE001
                _logger.warning(
                    "qdrant unavailable; using in-memory index",
                    extra={"error": str(exc)},
                )
                self.index = InMemoryQdrantIndex(
                    dimensions=self.embeddings.provider.dimensions
                )

    def index_document(
        self, document_id: str, *, force: bool = False
    ) -> dict[str, Any]:
        embed_result = self.embeddings.embed_document(document_id, force=force)
        vectors = embed_result.get("vectors") or []
        chunk_ids = embed_result.get("chunk_ids") or []

        chunks = list(
            self.session.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.chunk_index.asc())
            ).all()
        )
        if not chunks:
            raise NotFoundError(
                "No chunks to index",
                details={"document_id": document_id},
            )

        # Map newly embedded vectors; if skipped, re-embed forced for upsert
        vector_by_id: dict[str, list[float]] = {}
        if vectors and chunk_ids:
            vector_by_id = dict(zip(chunk_ids, vectors, strict=True))
        elif force or not vectors:
            embed_result = self.embeddings.embed_document(document_id, force=True)
            vector_by_id = dict(
                zip(
                    embed_result.get("chunk_ids") or [],
                    embed_result.get("vectors") or [],
                    strict=True,
                )
            )

        self.index.delete_by_document(document_id)
        points: list[dict[str, Any]] = []
        for chunk in chunks:
            vector = vector_by_id.get(chunk.id)
            if vector is None:
                # Incremental: embed single missing chunk
                single = self.embeddings.provider.embed_texts([chunk.text])[0]
                vector = single
                chunk.embedding_model_version = self.embeddings.provider.model_version
                chunk.status = "embedded"
            point_id = _point_id(chunk.id)
            payload = {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "doc_category": chunk.doc_category,
                "doc_subtype": chunk.doc_subtype,
                "drive_file_id": chunk.drive_file_id,
                "drawing_numbers": list(chunk.drawing_numbers or []),
                "motor_models": list(chunk.motor_models or []),
                "page": chunk.page,
                "section_path": chunk.section_path,
                "parent_section": chunk.parent_section,
                "text": chunk.text[:2000],
                "embedding_model_version": chunk.embedding_model_version,
            }
            points.append({"id": point_id, "vector": vector, "payload": payload})
            chunk.qdrant_point_id = point_id
            chunk.status = "indexed"

        upserted = self.index.upsert_points(points)
        self.session.flush()
        _logger.info(
            "qdrant upsert complete",
            extra={"document_id": document_id, "points": upserted},
        )
        return {
            "document_id": document_id,
            "upserted": upserted,
            "model_version": self.embeddings.provider.model_version,
            "collection": getattr(self.index, "collection", "unknown"),
        }

    def search(
        self,
        query: str,
        *,
        limit: int = 8,
        document_id: str | None = None,
        doc_category: str | None = None,
        drawing_number: str | None = None,
        motor_model: str | None = None,
        asset_id: str | None = None,
    ) -> list[dict[str, Any]]:
        vector = self.embeddings.provider.embed_texts([query])[0]
        return self.index.search(
            vector,
            limit=limit,
            document_id=document_id,
            doc_category=doc_category,
            drawing_number=drawing_number,
            motor_model=motor_model,
            asset_id=asset_id,
        )

    def delete_document(self, document_id: str) -> None:
        self.index.delete_by_document(document_id)
        chunks = self.session.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        ).all()
        for chunk in chunks:
            chunk.qdrant_point_id = None
            if chunk.status == "indexed":
                chunk.status = "embedded"
        self.session.flush()
