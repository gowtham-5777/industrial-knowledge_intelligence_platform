"""Parse orchestration service (Milestone 2.1)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ErrorCode, NotFoundError
from app.db.models.documents import Document
from app.indexing.handlers import HandlerRegistry
from app.indexing.handlers.azure_di_handler import AzureDocumentIntelligenceHandler
from app.indexing.job_state import DocumentParseStatus, JobStatus, utc_now
from app.indexing.models import ParseOutput
from app.indexing.repository import DocumentParseResultRepository, IndexingJobRepository
from app.indexing.schemas import (
    IndexingJobOut,
    ParseResultOut,
    ParseRouteOut,
    ParseRunOut,
)
from app.indexing.tier_router import describe_tier, select_parser_tier
from app.indexing.tiers import ParserTier, RoutingContext
from app.observability import get_logger, set_job_id
from app.storage.service import StorageService

_logger = get_logger(__name__)


class ParseService:
    """Route → download → parse → persist, with indexing job state machine."""

    def __init__(
        self,
        session: Session,
        storage: StorageService,
        settings: Settings | None = None,
        *,
        registry: HandlerRegistry | None = None,
        azure_handler: AzureDocumentIntelligenceHandler | None = None,
    ) -> None:
        self.session = session
        self.storage = storage
        self.settings = settings or get_settings()
        self.jobs = IndexingJobRepository(session)
        self.results = DocumentParseResultRepository(session)
        self.registry = registry or HandlerRegistry(
            self.settings, azure_handler=azure_handler
        )

    def route_document(
        self,
        document_id: str,
        *,
        force_tier: str | None = None,
    ) -> ParseRouteOut:
        document = self._get_document(document_id)
        ctx = self._routing_context(document, force_tier=force_tier)
        tier = select_parser_tier(ctx)
        return ParseRouteOut(
            document_id=document.id,
            tier=tier.value,
            handler=describe_tier(tier),
            mime_type=ctx.mime_type,
            doc_category=ctx.doc_category,
            doc_subtype=ctx.doc_subtype,
            filename=ctx.filename,
            folder_path=ctx.folder_path,
        )

    def parse_document(
        self,
        document_id: str,
        *,
        force_tier: str | None = None,
        sync: bool = True,
    ) -> ParseRunOut:
        document = self._get_document(document_id)
        ctx = self._routing_context(document, force_tier=force_tier)
        tier = select_parser_tier(ctx)

        job = self.jobs.create_parse_job(
            document_id=document.id,
            catalog_id=document.catalog_id,
            payload={
                "tier": tier.value,
                "mime_type": ctx.mime_type,
                "doc_category": ctx.doc_category,
                "filename": ctx.filename,
            },
        )
        set_job_id(job.id)
        _logger.info(
            "parse job queued",
            extra={"document_id": document.id, "tier": tier.value, "job_id": job.id},
        )

        if not sync:
            return ParseRunOut(
                job=self._job_out(job),
                route=ParseRouteOut(
                    document_id=document.id,
                    tier=tier.value,
                    handler=describe_tier(tier),
                    mime_type=ctx.mime_type,
                    doc_category=ctx.doc_category,
                    doc_subtype=ctx.doc_subtype,
                    filename=ctx.filename,
                    folder_path=ctx.folder_path,
                ),
                result=None,
            )

        return self._execute_parse(document, job, ctx, tier)

    def get_job(self, job_id: str) -> IndexingJobOut:
        job = self.jobs.get(job_id)
        if job is None:
            raise NotFoundError("Indexing job not found", details={"job_id": job_id})
        return self._job_out(job)

    def get_parse_result(self, document_id: str) -> ParseResultOut:
        row = self.results.get_latest_for_document(document_id)
        if row is None:
            raise NotFoundError(
                "Parse result not found",
                details={"document_id": document_id},
            )
        return self._result_out(row)

    def _execute_parse(
        self,
        document: Document,
        job: Any,
        ctx: RoutingContext,
        tier: ParserTier,
    ) -> ParseRunOut:
        self.jobs.transition(job, JobStatus.PARSING)
        document.status = DocumentParseStatus.PARSING.value
        self.session.flush()

        try:
            content = self._load_bytes(document)
            if tier == ParserTier.T1 and not self._azure_configured():
                if self.settings.parse_fallback_without_azure:
                    _logger.warning(
                        "azure di unavailable; falling back to T2",
                        extra={"document_id": document.id},
                    )
                    tier = ParserTier.T2
                    ctx = RoutingContext(
                        mime_type=ctx.mime_type,
                        doc_category=ctx.doc_category,
                        doc_subtype=ctx.doc_subtype,
                        folder_path=ctx.folder_path,
                        filename=ctx.filename,
                        force_tier=ParserTier.T2,
                    )
                else:
                    raise AppError(
                        "Azure Document Intelligence is required for T1 parse",
                        error_code=ErrorCode.SERVICE_UNAVAILABLE,
                        status_code=503,
                    )

            handler = self.registry.get(tier)
            output: ParseOutput = handler.parse(content, ctx=ctx)
            result_row = self._persist_result(document, job.id, output)

            if output.skipped:
                document.status = DocumentParseStatus.PARSE_SKIPPED.value
            else:
                document.status = DocumentParseStatus.PARSED.value

            self.jobs.transition(
                job,
                JobStatus.PARSED,
                payload_update={
                    "tier": output.tier,
                    "parser_name": output.parser_name,
                    "page_count": output.page_count,
                    "table_count": len(output.tables),
                    "skipped": output.skipped,
                },
            )
            self.session.flush()

            return ParseRunOut(
                job=self._job_out(job),
                route=ParseRouteOut(
                    document_id=document.id,
                    tier=output.tier,
                    handler=output.parser_name,
                    mime_type=ctx.mime_type,
                    doc_category=ctx.doc_category,
                    doc_subtype=ctx.doc_subtype,
                    filename=ctx.filename,
                    folder_path=ctx.folder_path,
                ),
                result=self._result_out(result_row),
            )
        except Exception as exc:
            document.status = DocumentParseStatus.PARSE_FAILED.value
            self.jobs.transition(
                job,
                JobStatus.FAILED,
                error_message=str(exc),
            )
            self.session.flush()
            _logger.exception(
                "parse job failed",
                extra={"document_id": document.id, "job_id": job.id},
            )
            if isinstance(exc, AppError):
                raise
            raise AppError(
                f"Parse failed: {exc}",
                error_code=ErrorCode.INGESTION_FAILED,
                status_code=500,
                details={"document_id": document.id, "job_id": job.id},
            ) from exc

    def _persist_result(
        self,
        document: Document,
        job_id: str,
        output: ParseOutput,
    ):
        version_id = None
        if document.versions:
            latest = max(document.versions, key=lambda v: v.version)
            version_id = latest.id

        status = "skipped" if output.skipped else "succeeded"
        return self.results.create_result(
            document_id=document.id,
            document_version_id=version_id,
            indexing_job_id=job_id,
            tier=output.tier,
            parser_name=output.parser_name,
            status=status,
            page_count=output.page_count,
            full_text=output.ensure_full_text() or None,
            pages=[p.to_dict() for p in output.pages],
            tables=[t.to_dict() for t in output.tables],
            warnings=list(output.warnings),
            extra_metadata=dict(output.metadata),
            parsed_at=utc_now(),
        )

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
                "Document not found",
                details={"document_id": document_id},
            )
        return document

    def _routing_context(
        self,
        document: Document,
        *,
        force_tier: str | None,
    ) -> RoutingContext:
        catalog = document.catalog_entry
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

        mime = catalog.mime_type if catalog else None
        filename = catalog.name if catalog else document.title
        return RoutingContext(
            mime_type=mime,
            doc_category=(
                catalog.doc_category
                if catalog and catalog.doc_category
                else document.doc_type
            ),
            doc_subtype=catalog.doc_subtype if catalog else None,
            folder_path=catalog.folder_path if catalog else None,
            filename=filename,
            force_tier=forced,
        )

    def _load_bytes(self, document: Document) -> bytes:
        key = self._storage_key(document)
        if not key:
            return b""
        try:
            return self.storage.download(key)
        except Exception as exc:
            raise AppError(
                f"Failed to download document bytes: {exc}",
                error_code=ErrorCode.INGESTION_FAILED,
                status_code=500,
                details={"storage_key": key},
            ) from exc

    def _storage_key(self, document: Document) -> str | None:
        catalog = document.catalog_entry
        if catalog and catalog.extra_metadata:
            key = catalog.extra_metadata.get("storage_key")
            if key:
                return str(key)
        uri = document.storage_uri
        if not uri:
            return None
        bucket = self.storage.bucket
        prefix = f"{bucket}/"
        if uri.startswith(prefix):
            return uri[len(prefix) :]
        if "/" in uri:
            return uri.split("/", 1)[1]
        return uri

    def _azure_configured(self) -> bool:
        return bool(
            (self.settings.azure_document_intelligence_endpoint or "").strip()
            and (self.settings.azure_document_intelligence_key or "").strip()
        )

    def _job_out(self, job: Any) -> IndexingJobOut:
        return IndexingJobOut(
            id=job.id,
            job_type=job.job_type,
            status=job.status,
            priority=job.priority,
            attempts=job.attempts,
            error_message=job.error_message,
            payload=dict(job.payload or {}),
            document_id=job.document_id,
            catalog_id=job.catalog_id,
            started_at=job.started_at,
            finished_at=job.finished_at,
            created_at=getattr(job, "created_at", None),
        )

    def _result_out(self, row: Any) -> ParseResultOut:
        return ParseResultOut(
            id=row.id,
            document_id=row.document_id,
            document_version_id=row.document_version_id,
            indexing_job_id=row.indexing_job_id,
            tier=row.tier,
            parser_name=row.parser_name,
            status=row.status,
            page_count=row.page_count,
            full_text=row.full_text,
            pages=list(row.pages or []),
            tables=list(row.tables or []),
            warnings=list(row.warnings or []),
            metadata=dict(row.extra_metadata or {}),
            error_message=row.error_message,
            parsed_at=row.parsed_at,
        )
