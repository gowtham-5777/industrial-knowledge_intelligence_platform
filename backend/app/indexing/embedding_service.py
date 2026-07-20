"""Embedding job service — versioned batch/incremental embed (Milestone 2.4)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ErrorCode, NotFoundError
from app.db.models.chunks import DocumentChunk, EmbeddingRegistry
from app.db.repositories.base import BaseRepository
from app.indexing.embeddings import EmbeddingProvider, get_embedding_provider
from app.observability import get_logger

_logger = get_logger(__name__)


class EmbeddingRegistryRepository(BaseRepository[EmbeddingRegistry]):
    model = EmbeddingRegistry

    def upsert_active(
        self,
        *,
        model_name: str,
        model_version: str,
        provider: str,
        dimensions: int,
    ) -> EmbeddingRegistry:
        row = self.session.scalars(
            select(EmbeddingRegistry).where(
                EmbeddingRegistry.model_version == model_version
            )
        ).first()
        if row is None:
            row = EmbeddingRegistry(
                model_name=model_name,
                model_version=model_version,
                provider=provider,
                dimensions=dimensions,
                is_active=True,
            )
            self.session.add(row)
        else:
            row.is_active = True
            row.dimensions = dimensions
        # Deactivate others
        for other in self.session.scalars(select(EmbeddingRegistry)).all():
            if other.model_version != model_version:
                other.is_active = False
        self.session.flush()
        return row


class EmbeddingService:
    """Embed document chunks and store embedding_model_version."""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        *,
        provider: EmbeddingProvider | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.provider = provider or get_embedding_provider(self.settings)
        self.registry = EmbeddingRegistryRepository(session)

    def embed_document(
        self,
        document_id: str,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        chunks = list(
            self.session.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.chunk_index.asc())
            ).all()
        )
        if not chunks:
            raise NotFoundError(
                "No chunks found for document — run chunking first",
                details={"document_id": document_id},
            )

        pending = [
            c
            for c in chunks
            if force or c.embedding_model_version != self.provider.model_version
        ]
        if not pending:
            return {
                "document_id": document_id,
                "embedded_count": 0,
                "skipped": len(chunks),
                "model_version": self.provider.model_version,
                "vectors": [],
            }

        texts = [c.text for c in pending]
        try:
            vectors = self.provider.embed_texts(texts)
        except AppError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                f"Embedding failed: {exc}",
                error_code=ErrorCode.INGESTION_FAILED,
                status_code=500,
                details={"document_id": document_id},
            ) from exc

        if len(vectors) != len(pending):
            raise AppError(
                "Embedding provider returned unexpected vector count",
                error_code=ErrorCode.INGESTION_FAILED,
                status_code=500,
            )

        self.registry.upsert_active(
            model_name=self.provider.model_name,
            model_version=self.provider.model_version,
            provider=self.provider.provider,
            dimensions=self.provider.dimensions,
        )

        for chunk, vector in zip(pending, vectors, strict=True):
            chunk.embedding_model_version = self.provider.model_version
            chunk.status = "embedded"
            meta = dict(chunk.extra_metadata or {})
            meta["embedding_dim"] = len(vector)
            # Keep a short fingerprint only — full vectors live in Qdrant
            meta["embedding_norm"] = round(sum(v * v for v in vector) ** 0.5, 6)
            chunk.extra_metadata = meta

        self.session.flush()
        _logger.info(
            "document embedded",
            extra={
                "document_id": document_id,
                "embedded_count": len(pending),
                "model_version": self.provider.model_version,
            },
        )
        return {
            "document_id": document_id,
            "embedded_count": len(pending),
            "skipped": len(chunks) - len(pending),
            "model_version": self.provider.model_version,
            "dimensions": self.provider.dimensions,
            "chunk_ids": [c.id for c in pending],
            "vectors": vectors,  # callers (Qdrant upsert) may consume then drop
        }

    def embed_incremental(self, *, limit: int = 100) -> dict[str, Any]:
        """Embed chunks missing the active model version."""
        stmt = (
            select(DocumentChunk)
            .where(
                (DocumentChunk.embedding_model_version.is_(None))
                | (DocumentChunk.embedding_model_version != self.provider.model_version)
            )
            .order_by(DocumentChunk.created_at.asc())
            .limit(limit)
        )
        chunks = list(self.session.scalars(stmt).all())
        by_doc: dict[str, list[DocumentChunk]] = {}
        for chunk in chunks:
            by_doc.setdefault(chunk.document_id, []).append(chunk)

        results = []
        for doc_id in by_doc:
            results.append(self.embed_document(doc_id))
        return {
            "documents": len(results),
            "embedded_chunks": sum(r["embedded_count"] for r in results),
            "model_version": self.provider.model_version,
        }
