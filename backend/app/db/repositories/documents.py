"""Document catalog repository."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.db.models.documents import DocumentCatalog
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
        self.session.flush()
        return existing

    def count(self) -> int:
        from sqlalchemy import func

        value = self.session.scalar(select(func.count()).select_from(DocumentCatalog))
        return int(value or 0)
