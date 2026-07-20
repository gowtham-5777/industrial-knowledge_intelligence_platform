"""End-to-end document intelligence pipeline orchestration."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.extraction.service import ExtractionService
from app.graph.sync import GraphSyncService
from app.indexing.chunk_service import ChunkService
from app.indexing.job_state import JobStatus, assert_transition
from app.indexing.repository import IndexingJobRepository
from app.indexing.service import ParseService
from app.indexing.vector_service import VectorIndexService
from app.observability import get_logger, set_job_id
from app.storage.service import StorageService

_logger = get_logger(__name__)


class DocumentIntelligencePipeline:
    """Parse → extract → chunk → embed/index → graph_sync → ready."""

    def __init__(
        self,
        session: Session,
        storage: StorageService,
        settings: Settings | None = None,
        *,
        parse_service: ParseService | None = None,
        extraction_service: ExtractionService | None = None,
        chunk_service: ChunkService | None = None,
        vector_service: VectorIndexService | None = None,
        graph_service: GraphSyncService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.storage = storage
        self.parse = parse_service or ParseService(session, storage, self.settings)
        self.extraction = extraction_service or ExtractionService(session)
        self.chunks = chunk_service or ChunkService(session)
        self.vectors = vector_service or VectorIndexService(session, self.settings)
        self.graph = graph_service or GraphSyncService(session, self.settings)
        self.jobs = IndexingJobRepository(session)

    def run(
        self,
        document_id: str,
        *,
        force_tier: str | None = None,
        skip_parse: bool = False,
    ) -> dict[str, Any]:
        job = self.jobs.create_parse_job(
            document_id=document_id,
            payload={"pipeline": "full", "force_tier": force_tier},
            priority=self._priority_for_document(document_id),
        )
        # Re-label as full pipeline job
        job.job_type = "full_pipeline"
        self.session.flush()
        set_job_id(job.id)

        stages: dict[str, Any] = {}
        try:
            self.jobs.transition(job, JobStatus.PARSING)
            if skip_parse:
                stages["parse"] = {"skipped": True}
                # Move to parsed without re-parse
                self.jobs.transition(job, JobStatus.PARSED)
            else:
                parse_out = self.parse.parse_document(
                    document_id, force_tier=force_tier, sync=True
                )
                # parse_document creates its own job; record summary on pipeline job
                stages["parse"] = {
                    "tier": parse_out.route.tier,
                    "status": parse_out.job.status,
                    "result_id": parse_out.result.id if parse_out.result else None,
                }
                # Align pipeline job to parsed (may already be parsing)
                if job.status == JobStatus.PARSING.value:
                    self.jobs.transition(job, JobStatus.PARSED)

            self.jobs.transition(job, JobStatus.EXTRACTING)
            stages["extract"] = self.extraction.extract_document(document_id)

            # Chunk is part of indexing preparation
            stages["chunk"] = self.chunks.chunk_document(document_id)

            self.jobs.transition(job, JobStatus.INDEXING)
            stages["index"] = self.vectors.index_document(document_id)

            self.jobs.transition(job, JobStatus.GRAPH_SYNC)
            stages["graph"] = self.graph.sync_document(document_id)

            self.jobs.transition(job, JobStatus.READY)
            _logger.info(
                "pipeline ready",
                extra={"document_id": document_id, "job_id": job.id},
            )
            return {
                "job_id": job.id,
                "document_id": document_id,
                "status": job.status,
                "stages": stages,
            }
        except Exception as exc:
            if job.status not in {JobStatus.FAILED.value, JobStatus.READY.value}:
                try:
                    # Best-effort fail transition from current state
                    from app.core.exceptions import AppError

                    try:
                        assert_transition(job.status, JobStatus.FAILED)
                        self.jobs.transition(
                            job, JobStatus.FAILED, error_message=str(exc)
                        )
                    except AppError:
                        job.status = JobStatus.FAILED.value
                        job.error_message = str(exc)
                        self.session.flush()
                except Exception:  # noqa: BLE001
                    pass
            _logger.exception(
                "pipeline failed",
                extra={"document_id": document_id, "job_id": job.id},
            )
            raise

    def _priority_for_document(self, document_id: str) -> int:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from app.db.models.documents import Document

        doc = self.session.scalars(
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.catalog_entry))
        ).first()
        category = None
        if doc and doc.catalog_entry:
            category = doc.catalog_entry.doc_category
        return priority_for_category(category)


# Adaptive priority — Architecture Continuous Intelligent Indexing
CATEGORY_PRIORITY: dict[str, int] = {
    "test_report": 10,
    "checklist": 15,
    "datasheet": 20,
    "certificate": 25,
    "manual": 30,
    "sop": 35,
    "maintenance": 40,
    "safety": 45,
    "regulation": 50,
    "sensor": 60,
    "work_order": 70,
    "drawing": 80,
    "drawing_dimension": 80,
    "drawing_outline": 80,
    "drawing_shaft": 80,
    "drawing_connection": 80,
    "drawing_mechanical": 80,
    "drawing_terminal": 80,
    "drawing_cad": 90,
}


def priority_for_category(category: str | None) -> int:
    if not category:
        return 100
    if category in CATEGORY_PRIORITY:
        return CATEGORY_PRIORITY[category]
    if category.startswith("drawing"):
        return 80
    return 100
