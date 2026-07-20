"""ORM models for entity extraction (Milestone 2.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ExtractionCandidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Proposed entity extracted from a document / parse result."""

    __tablename__ = "extraction_candidates"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    document_chunk_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    parse_result_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("document_parse_results.id"), nullable=True, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[str | None] = mapped_column(String(512), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class ReviewQueueItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Human review queue for low-confidence extraction candidates."""

    __tablename__ = "review_queue"

    candidate_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("extraction_candidates.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="open", index=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PerformanceTestReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Parsed performance / IEC test report header."""

    __tablename__ = "performance_test_reports"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, unique=True, index=True
    )
    motor_type_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    drawing_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    standard: Mapped[str | None] = mapped_column(String(128), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="extracted", index=True
    )
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )


class TestMeasurement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Structured IEC / performance test measurement row."""

    __tablename__ = "test_measurements"

    report_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("performance_test_reports.id"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    parameter: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rated_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    measured_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    numeric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_table_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
