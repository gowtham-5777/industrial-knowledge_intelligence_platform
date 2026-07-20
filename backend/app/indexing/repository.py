"""Indexing job + parse-result persistence helpers."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.db.models.parsing import DocumentParseResult
from app.db.models.processing import IndexingJob
from app.db.repositories.base import BaseRepository
from app.indexing.job_state import JobStatus, assert_transition, utc_now


class IndexingJobRepository(BaseRepository[IndexingJob]):
    model = IndexingJob

    def create_parse_job(
        self,
        *,
        document_id: str,
        catalog_id: str | None = None,
        priority: int = 50,
        payload: dict[str, Any] | None = None,
    ) -> IndexingJob:
        job = IndexingJob(
            job_type="parse",
            status=JobStatus.QUEUED.value,
            priority=priority,
            attempts=0,
            payload=payload or {},
            document_id=document_id,
            catalog_id=catalog_id,
        )
        self.session.add(job)
        self.session.flush()
        return job

    def transition(
        self,
        job: IndexingJob,
        status: JobStatus,
        *,
        error_message: str | None = None,
        payload_update: dict[str, Any] | None = None,
    ) -> IndexingJob:
        assert_transition(job.status, status)
        job.status = status.value
        if status == JobStatus.PARSING:
            job.started_at = utc_now()
            job.attempts = int(job.attempts or 0) + 1
        if status in {JobStatus.PARSED, JobStatus.FAILED, JobStatus.READY}:
            job.finished_at = utc_now()
        if error_message is not None:
            job.error_message = error_message
        if payload_update:
            merged = dict(job.payload or {})
            merged.update(payload_update)
            job.payload = merged
        self.session.flush()
        return job


class DocumentParseResultRepository(BaseRepository[DocumentParseResult]):
    model = DocumentParseResult

    def get_latest_for_document(self, document_id: str) -> DocumentParseResult | None:
        stmt = (
            select(DocumentParseResult)
            .where(DocumentParseResult.document_id == document_id)
            .order_by(DocumentParseResult.created_at.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def create_result(self, **kwargs: Any) -> DocumentParseResult:
        row = DocumentParseResult(**kwargs)
        self.session.add(row)
        self.session.flush()
        return row
