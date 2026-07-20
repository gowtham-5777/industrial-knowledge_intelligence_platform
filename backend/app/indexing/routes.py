"""Indexing / parse / pipeline API routes (Milestones 2.1–2.9)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.citations.service import CitationService
from app.core.dependencies import (
    DbSessionDep,
    RequestIdDep,
    SettingsDep,
    StorageServiceDep,
)
from app.core.exceptions import AppError, ErrorCode
from app.core.responses import success_envelope
from app.indexing.chunk_service import ChunkService
from app.indexing.pipeline import DocumentIntelligencePipeline
from app.indexing.schemas import ParseRouteRequest, ParseRunRequest
from app.indexing.service import ParseService
from app.indexing.status_service import IndexingStatusService
from app.indexing.tier_router import describe_tier, select_parser_tier
from app.indexing.tiers import ParserTier, RoutingContext
from app.indexing.vector_service import VectorIndexService
from app.knowledge.retrieval import HybridRetrievalService

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


class PipelineRunRequest(BaseModel):
    document_id: str
    force_tier: str | None = None
    skip_parse: bool = False


class ChunkRunRequest(BaseModel):
    document_id: str


class IndexRunRequest(BaseModel):
    document_id: str
    force: bool = False


class RetrieveRequest(BaseModel):
    query: str
    limit: int = Field(default=8, ge=1, le=50)
    motor_type_code: str | None = None
    drawing_number: str | None = None
    doc_category: str | None = None
    asset_id: str | None = None
    persist_trace: bool = True


class VerifyCitationsRequest(BaseModel):
    text: str


class PriorityEnqueueRequest(BaseModel):
    document_ids: list[str] | None = None
    hero_only: bool = True
    limit: int = Field(default=20, ge=1, le=200)
    async_worker: bool = False


@router.post("/route", summary="Select parser tier for a document (dry-run)")
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


@router.post("/parse", summary="Run parse pipeline for a document (sync by default)")
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


@router.get("/jobs/{job_id}", summary="Get indexing / parse job status")
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


@router.post("/chunk", summary="Chunk a parsed document (Milestone 2.3)")
def run_chunk(
    body: ChunkRunRequest,
    session: DbSessionDep,
    request_id: RequestIdDep,
) -> dict:
    data = ChunkService(session).chunk_document(body.document_id)
    return success_envelope(data, request_id=request_id)


@router.get("/chunks/{document_id}", summary="List chunks for a document")
def list_chunks(
    document_id: str,
    session: DbSessionDep,
    request_id: RequestIdDep,
) -> dict:
    data = ChunkService(session).get_chunks(document_id)
    return success_envelope({"items": data}, request_id=request_id)


@router.post("/index", summary="Embed + upsert document chunks to Qdrant (2.4–2.5)")
def run_index(
    body: IndexRunRequest,
    session: DbSessionDep,
    settings: SettingsDep,
    request_id: RequestIdDep,
) -> dict:
    data = VectorIndexService(session, settings).index_document(
        body.document_id, force=body.force
    )
    return success_envelope(data, request_id=request_id)


@router.post("/pipeline", summary="Full parse→extract→chunk→index→graph pipeline")
def run_pipeline(
    body: PipelineRunRequest,
    session: DbSessionDep,
    storage: StorageServiceDep,
    settings: SettingsDep,
    request_id: RequestIdDep,
) -> dict:
    pipeline = DocumentIntelligencePipeline(session, storage, settings)
    data = pipeline.run(
        body.document_id,
        force_tier=body.force_tier,
        skip_parse=body.skip_parse,
    )
    return success_envelope(data, request_id=request_id)


@router.get("/status", summary="Indexing status aggregates for UI (Milestone 2.9)")
def indexing_status(session: DbSessionDep, request_id: RequestIdDep) -> dict:
    data = IndexingStatusService(session).status()
    return success_envelope(data, request_id=request_id)


@router.get(
    "/progress/stream",
    summary="SSE stream of indexing job progress (Milestone 5.4.3)",
)
def indexing_progress_sse(
    session: DbSessionDep,
    document_id: str | None = None,
    job_id: str | None = None,
):
    """Reliable progress events for UI — polls job row with heartbeat."""
    import json
    import time

    from fastapi.responses import StreamingResponse
    from sqlalchemy import select

    from app.db.models.processing import IndexingJob

    def _events():
        last_status = None
        # Cap stream duration for demo reliability
        for _ in range(60):
            stmt = select(IndexingJob).order_by(IndexingJob.updated_at.desc())
            if job_id:
                stmt = stmt.where(IndexingJob.id == job_id)
            elif document_id:
                stmt = stmt.where(IndexingJob.document_id == document_id)
            job = session.scalars(stmt.limit(1)).first()
            payload = {
                "job_id": job.id if job else None,
                "document_id": job.document_id if job else document_id,
                "status": job.status if job else "unknown",
                "attempts": job.attempts if job else 0,
                "error_message": job.error_message if job else None,
            }
            if payload["status"] != last_status:
                last_status = payload["status"]
                yield f"event: progress\ndata: {json.dumps(payload)}\n\n"
            else:
                yield f"event: heartbeat\ndata: {json.dumps({'ok': True})}\n\n"
            if job and job.status in ("completed", "failed"):
                yield f"event: done\ndata: {json.dumps(payload)}\n\n"
                break
            time.sleep(0.5)
            session.expire_all()

    return StreamingResponse(_events(), media_type="text/event-stream")


@router.get(
    "/priority-subset",
    summary="Hero motor + priority document selection (Milestone 2.9)",
)
def priority_subset(
    session: DbSessionDep,
    request_id: RequestIdDep,
    hero_only: bool = True,
    limit: int = Query(default=50, ge=1, le=500),
) -> dict:
    data = IndexingStatusService(session).select_priority_subset(
        hero_only=hero_only, limit=limit
    )
    return success_envelope({"items": data}, request_id=request_id)


@router.post(
    "/priority-enqueue",
    summary="Enqueue documents by adaptive priority order",
)
def priority_enqueue(
    body: PriorityEnqueueRequest,
    session: DbSessionDep,
    request_id: RequestIdDep,
) -> dict:
    data = IndexingStatusService(session).enqueue_priority(
        document_ids=body.document_ids,
        hero_only=body.hero_only,
        limit=body.limit,
        async_worker=body.async_worker,
    )
    return success_envelope(data, request_id=request_id)


@router.post(
    "/retrieve",
    summary="Hybrid retrieval (Milestone 2.7) + citations (2.8)",
)
def retrieve(
    body: RetrieveRequest,
    session: DbSessionDep,
    settings: SettingsDep,
    request_id: RequestIdDep,
    user=Depends(get_current_user),
) -> dict:
    retrieval = HybridRetrievalService(session, settings)
    result = retrieval.retrieve(
        body.query,
        limit=body.limit,
        motor_type_code=body.motor_type_code,
        drawing_number=body.drawing_number,
        doc_category=body.doc_category,
        asset_id=body.asset_id,
        user=user,
        apply_acl=True,
    )
    citations = CitationService(session)
    refs = citations.format_from_results(result["results"])
    trace_id = None
    confidence = None
    if body.persist_trace:
        trace = citations.persist_trace(
            query_text=body.query,
            results=result["results"],
            motor_type_code=body.motor_type_code,
            asset_id=body.asset_id,
            graph_path_strength=1.0 if body.motor_type_code else 0.0,
        )
        trace_id = trace.id
        confidence = trace.confidence
    result["citations"] = refs
    result["trace_id"] = trace_id
    result["confidence"] = confidence
    return success_envelope(result, request_id=request_id)


@router.post("/citations/verify", summary="Verify [doc_id:chunk_id] citations")
def verify_citations(
    body: VerifyCitationsRequest,
    session: DbSessionDep,
    request_id: RequestIdDep,
) -> dict:
    data = CitationService(session).verify(body.text)
    return success_envelope(data, request_id=request_id)
