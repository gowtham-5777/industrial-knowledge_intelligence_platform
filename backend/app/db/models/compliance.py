"""Compliance requirements / evidence tables (Architecture §12 — Phase 4)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Regulation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """External regulation / standard (e.g. IEC 60034, ATEX)."""

    __tablename__ = "regulations"

    code: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    requirements: Mapped[list[ComplianceRequirement]] = relationship(
        back_populates="regulation"
    )


class ComplianceRequirement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Checklist requirement that must be evidenced for an asset class."""

    __tablename__ = "compliance_requirements"

    regulation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("regulations.id"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="motor", index=True
    )
    evidence_doc_categories: Mapped[list[Any] | None] = mapped_column(
        JSON, nullable=True
    )
    evidence_keywords: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    severity: Mapped[str] = mapped_column(
        String(32), nullable=False, default="medium", index=True
    )
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    regulation: Mapped[Regulation | None] = relationship(back_populates="requirements")
    evidence: Mapped[list[ComplianceEvidence]] = relationship(
        back_populates="requirement"
    )


class Certification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Certification record linked to a motor / document."""

    __tablename__ = "certifications"

    motor_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("motor_models.id"), nullable=True, index=True
    )
    document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cert_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True
    )
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )


class ComplianceEvidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Link between a requirement and supporting document evidence."""

    __tablename__ = "compliance_evidence"

    requirement_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("compliance_requirements.id"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=True, index=True
    )
    motor_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("motor_models.id"), nullable=True, index=True
    )
    certification_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("certifications.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="matched", index=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    requirement: Mapped[ComplianceRequirement] = relationship(back_populates="evidence")

    __table_args__ = (
        UniqueConstraint(
            "requirement_id",
            "document_id",
            "motor_id",
            name="uq_compliance_evidence_req_doc_motor",
        ),
    )
