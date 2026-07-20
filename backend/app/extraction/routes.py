"""Extraction API schemas and routes (Milestone 2.2)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.core.dependencies import DbSessionDep, RequestIdDep
from app.core.responses import success_envelope
from app.extraction.service import ExtractionService

router = APIRouter(
    prefix="/extraction",
    tags=["Extraction"],
    dependencies=[Depends(get_current_user)],
)


class ExtractRunRequest(BaseModel):
    document_id: str


def get_extraction_service(session: DbSessionDep) -> ExtractionService:
    return ExtractionService(session)


ExtractionServiceDep = Annotated[ExtractionService, Depends(get_extraction_service)]


@router.post("/run", summary="Run metadata / entity extraction for a document")
def run_extraction(
    body: ExtractRunRequest,
    service: ExtractionServiceDep,
    request_id: RequestIdDep,
) -> dict:
    data = service.extract_document(body.document_id)
    return success_envelope(data, request_id=request_id)


@router.get(
    "/candidates/{document_id}",
    summary="List extraction candidates for a document",
)
def list_candidates(
    document_id: str,
    service: ExtractionServiceDep,
    request_id: RequestIdDep,
) -> dict:
    return success_envelope(
        {"items": service.get_candidates(document_id)},
        request_id=request_id,
    )


@router.get(
    "/measurements/{document_id}",
    summary="List test measurements for a document",
)
def list_measurements(
    document_id: str,
    service: ExtractionServiceDep,
    request_id: RequestIdDep,
) -> dict:
    return success_envelope(
        {"items": service.get_measurements(document_id)},
        request_id=request_id,
    )


@router.get("/review-queue", summary="Open extraction review queue")
def review_queue(
    service: ExtractionServiceDep,
    request_id: RequestIdDep,
    limit: int = 100,
) -> dict:
    return success_envelope(
        {"items": service.list_review_queue(limit=limit)},
        request_id=request_id,
    )
