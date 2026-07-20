"""Document catalog, documents, versions, and asset links."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.assets import Asset


class DocumentCatalog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Discovery-pass catalog row (Drive listing; may not be fully ingested)."""

    __tablename__ = "document_catalog"

    drive_file_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    folder_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    md5_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    doc_category: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    doc_subtype: Mapped[str | None] = mapped_column(String(64), nullable=True)
    drawing_number: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    motor_type_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    discovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    documents: Mapped[list[Document]] = relationship(back_populates="catalog_entry")


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Ingested document (system of record for content lifecycle)."""

    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    doc_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="discovered", index=True
    )
    storage_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    catalog_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("document_catalog.id"), nullable=True, index=True
    )

    catalog_entry: Mapped[DocumentCatalog | None] = relationship(
        back_populates="documents"
    )
    versions: Mapped[list[DocumentVersion]] = relationship(back_populates="document")
    asset_links: Mapped[list[DocumentAssetLink]] = relationship(
        back_populates="document"
    )
    acl: Mapped[DocumentAcl | None] = relationship(
        back_populates="document", uselist=False
    )


class DocumentVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_versions"

    version: Mapped[int] = mapped_column(nullable=False, default=1)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )

    document: Mapped[Document] = relationship(back_populates="versions")

    __table_args__ = (
        UniqueConstraint("document_id", "version", name="uq_document_version"),
    )


class DocumentAssetLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Many-to-many link between documents and assets."""

    __tablename__ = "document_asset_links"

    link_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="related"
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assets.id"), nullable=False, index=True
    )

    document: Mapped[Document] = relationship(back_populates="asset_links")
    asset: Mapped[Asset] = relationship(back_populates="document_links")

    __table_args__ = (
        UniqueConstraint(
            "document_id", "asset_id", "link_type", name="uq_document_asset_link"
        ),
    )


class DocumentAcl(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Document-level ACL (Architecture §11) — filter before retrieval/LLM."""

    __tablename__ = "document_acl"

    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    plant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("plants.id"), nullable=True, index=True
    )
    classification: Mapped[str] = mapped_column(
        String(32), nullable=False, default="internal", index=True
    )
    allowed_roles: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    document: Mapped[Document] = relationship(back_populates="acl")
