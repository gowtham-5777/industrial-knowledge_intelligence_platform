"""Asset-agnostic registry (Architecture §12)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.documents import DocumentAssetLink
    from app.db.models.organization import Plant


class Asset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Generic industrial asset registry row."""

    __tablename__ = "assets"

    asset_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_tag: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    plant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("plants.id"), nullable=True, index=True
    )
    product_line_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("product_lines.id"), nullable=True, index=True
    )

    plant: Mapped[Plant | None] = relationship(back_populates="assets")
    document_links: Mapped[list[DocumentAssetLink]] = relationship(
        back_populates="asset"
    )
