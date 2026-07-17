"""Drawing number cross-reference tables."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.documents import Document


class DrawingNumber(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "drawing_numbers"

    drawing_number: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    normalized: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)

    document_links: Mapped[list[DocumentDrawingLink]] = relationship(
        back_populates="drawing"
    )


class DocumentDrawingLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_drawing_links"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    drawing_number_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drawing_numbers.id"), nullable=False, index=True
    )
    sheet_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    drawing: Mapped[DrawingNumber] = relationship(back_populates="document_links")
    document: Mapped[Document] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "drawing_number_id",
            name="uq_document_drawing_link",
        ),
    )
