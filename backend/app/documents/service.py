"""Document catalog & upload application service (Milestone 1.7)."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppError, ErrorCode, NotFoundError
from app.db.models.documents import Document, DocumentAssetLink, DocumentCatalog
from app.db.models.drawings import DocumentDrawingLink, DrawingNumber
from app.db.repositories.documents import DocumentCatalogRepository, DocumentRepository
from app.documents.classification import (
    MANUAL_UPLOAD_MIME_TYPES,
    ClassificationResult,
    classify_document,
    guess_mime_type,
)
from app.documents.linking import StubLinker
from app.documents.schemas import (
    CatalogItemOut,
    CatalogListOut,
    CatalogStatsOut,
    DocumentListOut,
    DocumentOut,
    DocumentVersionOut,
    LinkedAssetOut,
    LinkedDrawingOut,
    UploadResultOut,
)
from app.storage.service import StorageService
from app.storage.validation import validate_content_type


class DocumentCatalogService:
    """Catalog upsert (discovery) + list/get + manual upload orchestration."""

    def __init__(self, session: Session, storage: StorageService) -> None:
        self.session = session
        self.storage = storage
        self.catalog_repo = DocumentCatalogRepository(session)
        self.document_repo = DocumentRepository(session)
        self.linker = StubLinker(session)

    # --- 1.7.1 Catalog upsert from discovery ---

    def upsert_from_discovery(
        self,
        *,
        drive_file_id: str,
        name: str,
        folder_path: str | None = None,
        mime_type: str | None = None,
        size_bytes: int | None = None,
        md5_checksum: str | None = None,
        absolute_path: str | None = None,
        source: str = "local",
        classify: bool = True,
        link_registry_stubs: bool = True,
    ) -> DocumentCatalog:
        classification: ClassificationResult | None = None
        if classify:
            classification = classify_document(name=name, folder_path=folder_path)

        meta: dict[str, Any] = {"source": source}
        if absolute_path:
            meta["absolute_path"] = absolute_path
        if classification and classification.asset_domain:
            meta["asset_domain"] = classification.asset_domain

        row = self.catalog_repo.upsert_discovery(
            drive_file_id=drive_file_id,
            name=name,
            folder_path=folder_path,
            mime_type=mime_type or guess_mime_type(name),
            size_bytes=size_bytes,
            md5_checksum=md5_checksum,
            doc_category=classification.doc_category if classification else None,
            doc_subtype=classification.doc_subtype if classification else None,
            drawing_number=classification.drawing_number if classification else None,
            motor_type_code=classification.motor_type_code if classification else None,
            extra_metadata=meta,
        )

        if link_registry_stubs and classification:
            if classification.drawing_number:
                self.linker.ensure_drawing_stub(classification.drawing_number)
            if classification.motor_type_code:
                self.linker.ensure_motor_stub(classification.motor_type_code)

        return row

    # --- 1.7.3 Catalog list/get ---

    def catalog_stats(
        self,
        *,
        doc_category: str | None = None,
        drawing_number: str | None = None,
        q: str | None = None,
    ) -> CatalogStatsOut:
        return CatalogStatsOut(
            total=self.catalog_repo.count(),
            filtered=self.catalog_repo.count(
                doc_category=doc_category,
                drawing_number=drawing_number,
                q=q,
            ),
        )

    def list_catalog(
        self,
        *,
        doc_category: str | None = None,
        drawing_number: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> CatalogListOut:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        rows = self.catalog_repo.list_filtered(
            doc_category=doc_category,
            drawing_number=drawing_number,
            q=q,
            limit=limit,
            offset=offset,
        )
        total = self.catalog_repo.count(
            doc_category=doc_category,
            drawing_number=drawing_number,
            q=q,
        )
        return CatalogListOut(
            items=[self._catalog_out(r) for r in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_catalog(self, catalog_id: str) -> CatalogItemOut:
        row = self.catalog_repo.get(catalog_id)
        if row is None:
            raise NotFoundError(
                "Catalog entry not found",
                details={"id": catalog_id},
            )
        return self._catalog_out(row)

    # --- Documents list/get ---

    def list_documents(
        self,
        *,
        status: str | None = None,
        doc_type: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> DocumentListOut:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        rows = self.document_repo.list_filtered(
            status=status,
            doc_type=doc_type,
            q=q,
            limit=limit,
            offset=offset,
        )
        total = self.document_repo.count(status=status, doc_type=doc_type, q=q)
        return DocumentListOut(
            items=[self._document_out(d, include_links=False) for d in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_document(self, document_id: str) -> DocumentOut:
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(
                selectinload(Document.versions),
                selectinload(Document.catalog_entry),
                selectinload(Document.asset_links).selectinload(
                    DocumentAssetLink.asset
                ),
            )
        )
        document = self.session.scalars(stmt).first()
        if document is None:
            raise NotFoundError(
                "Document not found",
                details={"id": document_id},
            )
        return self._document_out(document, include_links=True)

    # --- 1.7.2 Manual upload ---

    def upload_manual(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str | None = None,
        folder_path: str | None = None,
        title: str | None = None,
    ) -> UploadResultOut:
        safe_name = _safe_filename(filename)
        if not safe_name:
            raise AppError(
                "Filename is required",
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
            )

        guessed = (
            content_type or guess_mime_type(safe_name) or "application/octet-stream"
        )
        normalized = validate_content_type(
            guessed,
            allowed=MANUAL_UPLOAD_MIME_TYPES,
        )

        classification = classify_document(name=safe_name, folder_path=folder_path)
        checksum = hashlib.md5(content, usedforsecurity=False).hexdigest()
        upload_id = str(uuid.uuid4())
        drive_file_id = f"upload:{upload_id}"
        day = datetime.now(UTC).strftime("%Y/%m/%d")
        storage_key = f"uploads/{day}/{upload_id}_{safe_name}"

        self.storage.ensure_ready()
        stored = self.storage.upload(
            storage_key,
            content,
            content_type=normalized,
            metadata={
                "source": "manual_upload",
                "original_filename": safe_name,
                "md5": checksum,
            },
        )

        meta: dict[str, Any] = {
            "source": "manual_upload",
            "storage_key": stored.key,
            "storage_bucket": stored.bucket,
            "uploaded": True,
        }
        if classification.asset_domain:
            meta["asset_domain"] = classification.asset_domain

        catalog = self.catalog_repo.upsert_discovery(
            drive_file_id=drive_file_id,
            name=safe_name,
            folder_path=folder_path,
            mime_type=normalized,
            size_bytes=len(content),
            md5_checksum=checksum,
            doc_category=classification.doc_category,
            doc_subtype=classification.doc_subtype,
            drawing_number=classification.drawing_number,
            motor_type_code=classification.motor_type_code,
            extra_metadata=meta,
        )

        storage_uri = f"{stored.bucket}/{stored.key}"
        document = self.document_repo.create_with_version(
            title=title or safe_name,
            storage_uri=storage_uri,
            checksum=checksum,
            doc_type=classification.doc_category,
            status="uploaded",
            catalog_id=catalog.id,
        )

        # 1.7.5 Asset / drawing stub linking
        self.linker.link_document(
            document,
            drawing_number=classification.drawing_number,
            motor_type_code=classification.motor_type_code,
            asset_domain=classification.asset_domain,
        )
        self.session.flush()

        return UploadResultOut(
            document=self.get_document(document.id),
            catalog=self._catalog_out(catalog),
            storage_key=stored.key,
            bucket=stored.bucket,
        )

    def _catalog_out(self, row: DocumentCatalog) -> CatalogItemOut:
        return CatalogItemOut(
            id=row.id,
            drive_file_id=row.drive_file_id,
            name=row.name,
            folder_path=row.folder_path,
            mime_type=row.mime_type,
            size_bytes=row.size_bytes,
            md5_checksum=row.md5_checksum,
            doc_category=row.doc_category,
            doc_subtype=row.doc_subtype,
            drawing_number=row.drawing_number,
            motor_type_code=row.motor_type_code,
            discovered_at=row.discovered_at,
            metadata=dict(row.extra_metadata or {}),
        )

    def _document_out(
        self,
        document: Document,
        *,
        include_links: bool,
    ) -> DocumentOut:
        versions = [
            DocumentVersionOut(
                id=v.id,
                version=v.version,
                storage_uri=v.storage_uri,
                checksum=v.checksum,
            )
            for v in (document.versions or [])
        ]
        linked_assets: list[LinkedAssetOut] = []
        linked_drawings: list[LinkedDrawingOut] = []
        catalog_out: CatalogItemOut | None = None

        if document.catalog_entry is not None:
            catalog_out = self._catalog_out(document.catalog_entry)

        if include_links:
            for link in document.asset_links or []:
                asset = link.asset
                if asset is None:
                    continue
                linked_assets.append(
                    LinkedAssetOut(
                        id=asset.id,
                        asset_type=asset.asset_type,
                        name=asset.name,
                        asset_tag=asset.asset_tag,
                        status=asset.status,
                        link_type=link.link_type,
                    )
                )
            drawing_links = self.session.scalars(
                select(DocumentDrawingLink)
                .where(DocumentDrawingLink.document_id == document.id)
                .options(selectinload(DocumentDrawingLink.drawing))
            ).all()
            for dlink in drawing_links:
                drawing: DrawingNumber | None = dlink.drawing
                if drawing is None:
                    continue
                linked_drawings.append(
                    LinkedDrawingOut(
                        id=drawing.id,
                        drawing_number=drawing.drawing_number,
                        normalized=drawing.normalized,
                    )
                )

        return DocumentOut(
            id=document.id,
            title=document.title,
            doc_type=document.doc_type,
            status=document.status,
            storage_uri=document.storage_uri,
            catalog_id=document.catalog_id,
            created_at=getattr(document, "created_at", None),
            versions=versions,
            linked_assets=linked_assets,
            linked_drawings=linked_drawings,
            catalog=catalog_out,
        )


def _safe_filename(name: str) -> str:
    cleaned = name.strip().replace("\\", "/").split("/")[-1]
    cleaned = re.sub(r"[^\w.\- ()\[\]]+", "_", cleaned)
    return cleaned[:240]
