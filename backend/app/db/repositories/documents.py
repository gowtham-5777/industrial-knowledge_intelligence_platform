"""Document catalog / document repositories (Milestone 1.7)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, or_, select

from app.db.models.documents import (
    Document,
    DocumentAssetLink,
    DocumentCatalog,
    DocumentVersion,
)
from app.db.models.drawings import DocumentDrawingLink, DrawingNumber
from app.db.repositories.base import BaseRepository


class DocumentCatalogRepository(BaseRepository[DocumentCatalog]):
    model = DocumentCatalog

    def get_by_drive_file_id(self, drive_file_id: str) -> DocumentCatalog | None:
        stmt = select(DocumentCatalog).where(
            DocumentCatalog.drive_file_id == drive_file_id
        )
        return self.session.scalars(stmt).first()

    def upsert_discovery(
        self,
        *,
        drive_file_id: str,
        name: str,
        folder_path: str | None = None,
        mime_type: str | None = None,
        size_bytes: int | None = None,
        md5_checksum: str | None = None,
        doc_category: str | None = None,
        doc_subtype: str | None = None,
        drawing_number: str | None = None,
        motor_type_code: str | None = None,
        extra_metadata: dict | None = None,
    ) -> DocumentCatalog:
        existing = self.get_by_drive_file_id(drive_file_id)
        if existing is None:
            row = DocumentCatalog(
                drive_file_id=drive_file_id,
                name=name,
                folder_path=folder_path,
                mime_type=mime_type,
                size_bytes=size_bytes,
                md5_checksum=md5_checksum,
                doc_category=doc_category,
                doc_subtype=doc_subtype,
                drawing_number=drawing_number,
                motor_type_code=motor_type_code,
                discovered_at=datetime.now(UTC),
                extra_metadata=extra_metadata,
            )
            return self.add(row)

        existing.name = name
        existing.folder_path = folder_path
        existing.mime_type = mime_type
        existing.size_bytes = size_bytes
        existing.md5_checksum = md5_checksum
        existing.doc_category = doc_category
        existing.doc_subtype = doc_subtype
        existing.drawing_number = drawing_number
        existing.motor_type_code = motor_type_code
        if extra_metadata is not None:
            merged = dict(existing.extra_metadata or {})
            merged.update(extra_metadata)
            existing.extra_metadata = merged
        self.session.flush()
        return existing

    def count(
        self,
        *,
        doc_category: str | None = None,
        drawing_number: str | None = None,
        q: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(DocumentCatalog)
        stmt = self._apply_filters(
            stmt,
            doc_category=doc_category,
            drawing_number=drawing_number,
            q=q,
        )
        value = self.session.scalar(stmt)
        return int(value or 0)

    def list_filtered(
        self,
        *,
        doc_category: str | None = None,
        drawing_number: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DocumentCatalog]:
        stmt = select(DocumentCatalog).order_by(DocumentCatalog.created_at.desc())
        stmt = self._apply_filters(
            stmt,
            doc_category=doc_category,
            drawing_number=drawing_number,
            q=q,
        )
        stmt = stmt.offset(offset).limit(limit)
        return list(self.session.scalars(stmt).all())

    def _apply_filters(self, stmt, *, doc_category, drawing_number, q):  # noqa: ANN001
        if doc_category:
            stmt = stmt.where(DocumentCatalog.doc_category == doc_category)
        if drawing_number:
            stmt = stmt.where(DocumentCatalog.drawing_number == drawing_number)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(
                    DocumentCatalog.name.ilike(like),
                    DocumentCatalog.folder_path.ilike(like),
                    DocumentCatalog.motor_type_code.ilike(like),
                )
            )
        return stmt


class DocumentRepository(BaseRepository[Document]):
    model = Document

    def list_filtered(
        self,
        *,
        status: str | None = None,
        doc_type: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:
        stmt = select(Document).order_by(Document.created_at.desc())
        if status:
            stmt = stmt.where(Document.status == status)
        if doc_type:
            stmt = stmt.where(Document.doc_type == doc_type)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(Document.title.ilike(like))
        stmt = stmt.offset(offset).limit(limit)
        return list(self.session.scalars(stmt).all())

    def count(
        self,
        *,
        status: str | None = None,
        doc_type: str | None = None,
        q: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(Document)
        if status:
            stmt = stmt.where(Document.status == status)
        if doc_type:
            stmt = stmt.where(Document.doc_type == doc_type)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(Document.title.ilike(like))
        value = self.session.scalar(stmt)
        return int(value or 0)

    def create_with_version(
        self,
        *,
        title: str,
        storage_uri: str,
        checksum: str | None = None,
        doc_type: str | None = None,
        status: str = "uploaded",
        catalog_id: str | None = None,
    ) -> Document:
        document = Document(
            title=title,
            doc_type=doc_type,
            status=status,
            storage_uri=storage_uri,
            catalog_id=catalog_id,
        )
        self.add(document)
        version = DocumentVersion(
            version=1,
            storage_uri=storage_uri,
            checksum=checksum,
            document_id=document.id,
        )
        self.session.add(version)
        self.session.flush()
        return document


class DrawingNumberRepository(BaseRepository[DrawingNumber]):
    model = DrawingNumber

    def get_by_number(self, drawing_number: str) -> DrawingNumber | None:
        normalized = drawing_number.strip().upper()
        stmt = select(DrawingNumber).where(DrawingNumber.normalized == normalized)
        return self.session.scalars(stmt).first()

    def get_or_create_stub(self, drawing_number: str) -> DrawingNumber:
        normalized = drawing_number.strip().upper()
        existing = self.get_by_number(normalized)
        if existing is not None:
            return existing
        row = DrawingNumber(
            drawing_number=normalized,
            normalized=normalized,
            description="stub",
        )
        return self.add(row)

    def link_document(
        self,
        *,
        document_id: str,
        drawing: DrawingNumber,
        sheet_id: str | None = None,
    ) -> DocumentDrawingLink:
        stmt = select(DocumentDrawingLink).where(
            DocumentDrawingLink.document_id == document_id,
            DocumentDrawingLink.drawing_number_id == drawing.id,
        )
        existing = self.session.scalars(stmt).first()
        if existing is not None:
            return existing
        link = DocumentDrawingLink(
            document_id=document_id,
            drawing_number_id=drawing.id,
            sheet_id=sheet_id,
        )
        self.session.add(link)
        self.session.flush()
        return link


class DocumentAssetLinkRepository(BaseRepository[DocumentAssetLink]):
    model = DocumentAssetLink

    def link(
        self,
        *,
        document_id: str,
        asset_id: str,
        link_type: str = "related",
    ) -> DocumentAssetLink:
        stmt = select(DocumentAssetLink).where(
            DocumentAssetLink.document_id == document_id,
            DocumentAssetLink.asset_id == asset_id,
            DocumentAssetLink.link_type == link_type,
        )
        existing = self.session.scalars(stmt).first()
        if existing is not None:
            return existing
        link = DocumentAssetLink(
            document_id=document_id,
            asset_id=asset_id,
            link_type=link_type,
        )
        return self.add(link)
