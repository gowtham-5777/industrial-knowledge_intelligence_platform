"""ORM model for persisted parse output (Milestone 2.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DocumentParseResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Structured parse output for a document version (pre-chunking)."""

    __tablename__ = "document_parse_results"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    document_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("document_versions.id"), nullable=True, index=True
    )
    indexing_job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("indexing_jobs.id"), nullable=True, index=True
    )
    tier: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    parser_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="succeeded", index=True
    )
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    pages: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    tables: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    warnings: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
