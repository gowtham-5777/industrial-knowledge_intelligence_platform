"""Indexing / parse API routes (Milestone 2.1)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.core.dependencies import (
    DbSessionDep,
    RequestIdDep,
    SettingsDep,
    StorageServiceDep,
)
from app.core.exceptions import AppError, ErrorCode
from app.core.responses import success_envelope
from app.indexing.schemas import ParseRouteRequest, ParseRunRequest
from app.indexing.service import ParseService
from app.indexing.tier_router import describe_tier, select_parser_tier
from app.indexing.tiers import ParserTier, RoutingContext

router = APIRouter(
    prefix="/indexing",
    tags=["Indexing"],
    dependencies=[Depends(get_current_user)],
)


def get_parse_service(
    session: DbSessionDep,
    storage: StorageServiceDep,
    settings: SettingsDep,
) -> ParseService:
    return ParseService(session, storage, settings)


ParseServiceDep = Annotated[ParseService, Depends(get_parse_service)]


@router.post(
    "/route",
    summary="Select parser tier for a document (dry-run)",
)
def route_parse(
    body: ParseRouteRequest,
    service: ParseServiceDep,
    request_id: RequestIdDep,
) -> dict:
    data = service.route_document(body.document_id, force_tier=body.force_tier)
    return success_envelope(data.model_dump(), request_id=request_id)


@router.get(
    "/route/preview",
    summary="Select parser tier from MIME / category (no document required)",
)
def route_preview(
    request_id: RequestIdDep,
    mime_type: str | None = None,
    doc_category: str | None = None,
    doc_subtype: str | None = None,
    folder_path: str | None = None,
    filename: str | None = None,
    force_tier: Annotated[str | None, Query()] = None,
) -> dict:
    forced: ParserTier | None = None
    if force_tier:
        try:
            forced = ParserTier(force_tier)
        except ValueError as exc:
            raise AppError(
                f"Unknown parser tier: {force_tier}",
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
            ) from exc
    ctx = RoutingContext(
        mime_type=mime_type,
        doc_category=doc_category,
        doc_subtype=doc_subtype,
        folder_path=folder_path,
        filename=filename,
        force_tier=forced,
    )
    tier = select_parser_tier(ctx)
    return success_envelope(
        {
            "tier": tier.value,
            "handler": describe_tier(tier),
            "mime_type": mime_type,
            "doc_category": doc_category,
            "doc_subtype": doc_subtype,
            "filename": filename,
            "folder_path": folder_path,
        },
        request_id=request_id,
    )


@router.post(
    "/parse",
    summary="Run parse pipeline for a document (sync by default)",
)
def run_parse(
    body: ParseRunRequest,
    service: ParseServiceDep,
    request_id: RequestIdDep,
) -> dict:
    data = service.parse_document(
        body.document_id,
        force_tier=body.force_tier,
        sync=body.sync,
    )
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)


@router.get(
    "/jobs/{job_id}",
    summary="Get indexing / parse job status",
)
def get_job(
    job_id: str,
    service: ParseServiceDep,
    request_id: RequestIdDep,
) -> dict:
    data = service.get_job(job_id)
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)


@router.get(
    "/parse-results/{document_id}",
    summary="Get latest parse result for a document",
)
def get_parse_result(
    document_id: str,
    service: ParseServiceDep,
    request_id: RequestIdDep,
) -> dict:
    data = service.get_parse_result(document_id)
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)
