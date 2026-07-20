"""ORM models for document chunks and embedding registry (Milestones 2.3–2.4)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DocumentChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Chunked document segment ready for embedding / retrieval."""

    __tablename__ = "document_chunks"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    document_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("document_versions.id"), nullable=True, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    parent_section: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_category: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    doc_subtype: Mapped[str | None] = mapped_column(String(64), nullable=True)
    drive_file_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    drawing_numbers: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    motor_models: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    embedding_model_version: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    qdrant_point_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="chunked", index=True
    )
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
    )


class EmbeddingRegistry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Registry of embedding model versions used in the pipeline."""

    __tablename__ = "embedding_registry"

    model_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="openai")
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )


class RetrievalTrace(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted hybrid retrieval trace for citation / provenance (2.8)."""

    __tablename__ = "retrieval_traces"

    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    asset_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    motor_type_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    result_chunk_ids: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    citation_refs: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    scores: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    pipeline: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
