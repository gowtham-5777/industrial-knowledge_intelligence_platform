"""Document catalog & upload API routes (Milestone 1.7)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.auth.dependencies import get_current_user
from app.core.dependencies import DbSessionDep, RequestIdDep, StorageServiceDep
from app.core.exceptions import AppError, ErrorCode
from app.core.responses import success_envelope
from app.documents.service import DocumentCatalogService

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
    dependencies=[Depends(get_current_user)],
)


def get_document_service(
    session: DbSessionDep,
    storage: StorageServiceDep,
) -> DocumentCatalogService:
    return DocumentCatalogService(session, storage)


DocumentServiceDep = Annotated[
    DocumentCatalogService,
    Depends(get_document_service),
]


@router.get(
    "/catalog/stats",
    summary="Document catalog counts (discovery scale signal)",
)
def catalog_stats(
    service: DocumentServiceDep,
    request_id: RequestIdDep,
    doc_category: str | None = None,
    drawing_number: str | None = None,
    q: str | None = None,
) -> dict:
    data = service.catalog_stats(
        doc_category=doc_category,
        drawing_number=drawing_number,
        q=q,
    )
    return success_envelope(data.model_dump(), request_id=request_id)


@router.get(
    "/catalog",
    summary="List document catalog entries (discovery metadata)",
)
def list_catalog(
    service: DocumentServiceDep,
    request_id: RequestIdDep,
    doc_category: str | None = None,
    drawing_number: str | None = None,
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    data = service.list_catalog(
        doc_category=doc_category,
        drawing_number=drawing_number,
        q=q,
        limit=limit,
        offset=offset,
    )
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)


@router.get(
    "/catalog/{catalog_id}",
    summary="Get one catalog entry",
)
def get_catalog(
    catalog_id: str,
    service: DocumentServiceDep,
    request_id: RequestIdDep,
) -> dict:
    data = service.get_catalog(catalog_id)
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)


@router.get(
    "",
    summary="List ingested documents",
)
def list_documents(
    service: DocumentServiceDep,
    request_id: RequestIdDep,
    status: str | None = None,
    doc_type: str | None = None,
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    data = service.list_documents(
        status=status,
        doc_type=doc_type,
        q=q,
        limit=limit,
        offset=offset,
    )
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)


@router.post(
    "/upload",
    summary="Manual upload (PDF / DOCX / XLSX / images)",
)
async def upload_document(
    service: DocumentServiceDep,
    request_id: RequestIdDep,
    file: Annotated[UploadFile, File()],
    folder_path: Annotated[str | None, Form()] = None,
    title: Annotated[str | None, Form()] = None,
) -> dict:
    payload = await file.read()
    if not payload:
        raise AppError(
            "Uploaded file is empty",
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
        )
    result = service.upload_manual(
        filename=file.filename or "upload.bin",
        content=payload,
        content_type=file.content_type,
        folder_path=folder_path,
        title=title,
    )
    return success_envelope(result.model_dump(mode="json"), request_id=request_id)


@router.get(
    "/{document_id}",
    summary="Get document with versions and stub links",
)
def get_document(
    document_id: str,
    service: DocumentServiceDep,
    request_id: RequestIdDep,
) -> dict:
    data = service.get_document(document_id)
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)
