"""Chunk persistence service (Milestone 2.3)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.db.models.chunks import DocumentChunk
from app.db.models.documents import Document
from app.db.models.parsing import DocumentParseResult
from app.db.repositories.base import BaseRepository
from app.documents.classification import extract_sheet_id
from app.extraction.extractors import extract_all_drawing_numbers
from app.indexing.chunkers import chunk_document
from app.observability import get_logger

_logger = get_logger(__name__)


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    model = DocumentChunk

    def list_for_document(self, document_id: str) -> list[DocumentChunk]:
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        return list(self.session.scalars(stmt).all())

    def delete_for_document(self, document_id: str) -> None:
        self.session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        self.session.flush()


class ChunkService:
    """Build Architecture §5 chunks from parse results and persist them."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.chunks = DocumentChunkRepository(session)

    def chunk_document(self, document_id: str) -> dict[str, Any]:
        document = self._get_document(document_id)
        parse = self._latest_parse(document_id)
        catalog = document.catalog_entry

        full_text = (parse.full_text if parse else "") or ""
        tables = list((parse.tables if parse else None) or [])
        pages = list((parse.pages if parse else None) or [])
        doc_category = (
            catalog.doc_category
            if catalog and catalog.doc_category
            else document.doc_type
        )
        filename = catalog.name if catalog else document.title
        drawing_number = catalog.drawing_number if catalog else None
        if not drawing_number and filename:
            nums = extract_all_drawing_numbers(filename)
            drawing_number = nums[0] if nums else None
        sheet_id = extract_sheet_id(filename or "") if filename else None

        drafts = chunk_document(
            doc_category=doc_category,
            full_text=full_text,
            tables=tables,
            pages=pages,
            drawing_number=drawing_number,
            sheet_id=sheet_id,
        )
        if not drafts and full_text.strip():
            drafts = chunk_document(
                doc_category=None,
                full_text=full_text,
            )

        self.chunks.delete_for_document(document.id)
        version_id = None
        if document.versions:
            version_id = max(document.versions, key=lambda v: v.version).id

        drawing_numbers = []
        if drawing_number:
            drawing_numbers.append(drawing_number)
        drawing_numbers.extend(
            n
            for n in extract_all_drawing_numbers(full_text)
            if n not in drawing_numbers
        )
        motor_models = []
        if catalog and catalog.motor_type_code:
            motor_models.append(catalog.motor_type_code)

        saved: list[DocumentChunk] = []
        for draft in drafts:
            row = DocumentChunk(
                document_id=document.id,
                document_version_id=version_id,
                chunk_index=draft.chunk_index,
                text=draft.text,
                token_count=draft.token_count,
                page=draft.page,
                section_path=draft.section_path,
                parent_section=draft.parent_section,
                doc_category=doc_category,
                doc_subtype=catalog.doc_subtype if catalog else None,
                drive_file_id=catalog.drive_file_id if catalog else None,
                drawing_numbers=drawing_numbers or None,
                motor_models=motor_models or None,
                status="chunked",
                extra_metadata=dict(draft.extra_metadata or {}),
            )
            self.session.add(row)
            saved.append(row)

        document.status = "chunked"
        self.session.flush()
        _logger.info(
            "chunking complete",
            extra={"document_id": document.id, "chunk_count": len(saved)},
        )
        return {
            "document_id": document.id,
            "chunk_count": len(saved),
            "chunks": [self._chunk_dict(c) for c in saved],
        }

    def get_chunks(self, document_id: str) -> list[dict[str, Any]]:
        return [self._chunk_dict(c) for c in self.chunks.list_for_document(document_id)]

    def _get_document(self, document_id: str) -> Document:
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(
                selectinload(Document.catalog_entry),
                selectinload(Document.versions),
            )
        )
        document = self.session.scalars(stmt).first()
        if document is None:
            raise NotFoundError(
                "Document not found", details={"document_id": document_id}
            )
        return document

    def _latest_parse(self, document_id: str) -> DocumentParseResult | None:
        stmt = (
            select(DocumentParseResult)
            .where(DocumentParseResult.document_id == document_id)
            .order_by(DocumentParseResult.created_at.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    @staticmethod
    def _chunk_dict(row: DocumentChunk) -> dict[str, Any]:
        return {
            "id": row.id,
            "document_id": row.document_id,
            "chunk_index": row.chunk_index,
            "text": row.text,
            "token_count": row.token_count,
            "page": row.page,
            "section_path": row.section_path,
            "parent_section": row.parent_section,
            "doc_category": row.doc_category,
            "drawing_numbers": list(row.drawing_numbers or []),
            "motor_models": list(row.motor_models or []),
            "embedding_model_version": row.embedding_model_version,
            "status": row.status,
        }
