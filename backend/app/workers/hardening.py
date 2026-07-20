"""Worker hardening — DLQ, idempotency, retries (Milestone 5.4)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.processing import DeadLetterJob, IndexingJob
from app.observability import get_logger

_logger = get_logger(__name__)


def idempotency_key_for_pipeline(document_id: str, force_tier: str | None) -> str:
    return f"indexing.run_pipeline:{document_id}:{force_tier or 'auto'}"


def record_dead_letter(
    session: Session,
    *,
    task_name: str,
    payload: dict[str, Any] | None,
    error_message: str,
    attempts: int,
    document_id: str | None = None,
    idempotency_key: str | None = None,
) -> DeadLetterJob:
    row = DeadLetterJob(
        task_name=task_name,
        idempotency_key=idempotency_key,
        payload=payload,
        error_message=error_message[:4000] if error_message else None,
        attempts=attempts,
        status="open",
        document_id=document_id,
    )
    session.add(row)
    session.flush()
    _logger.error(
        "dead_letter_recorded",
        extra={
            "task_name": task_name,
            "document_id": document_id,
            "attempts": attempts,
        },
    )
    return row


def list_dead_letters(
    session: Session,
    *,
    status: str = "open",
    limit: int = 50,
) -> list[DeadLetterJob]:
    stmt = (
        select(DeadLetterJob)
        .where(DeadLetterJob.status == status)
        .order_by(DeadLetterJob.created_at.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt).all())


def mark_job_attempt(
    session: Session,
    *,
    document_id: str,
    job_type: str = "pipeline",
) -> IndexingJob:
    """Create or bump an indexing job attempt counter (idempotency audit)."""
    existing = session.scalars(
        select(IndexingJob)
        .where(
            IndexingJob.document_id == document_id,
            IndexingJob.job_type == job_type,
            IndexingJob.status.in_(("pending", "running")),
        )
        .order_by(IndexingJob.created_at.desc())
    ).first()
    if existing is not None:
        existing.attempts = (existing.attempts or 0) + 1
        existing.status = "running"
        existing.started_at = datetime.now(UTC)
        session.flush()
        return existing
    job = IndexingJob(
        job_type=job_type,
        status="running",
        attempts=1,
        document_id=document_id,
        started_at=datetime.now(UTC),
        payload={"idempotent": True},
    )
    session.add(job)
    session.flush()
    return job


def complete_job(
    session: Session,
    job: IndexingJob,
    *,
    ok: bool,
    error: str | None = None,
) -> None:
    job.status = "completed" if ok else "failed"
    job.finished_at = datetime.now(UTC)
    if error:
        job.error_message = error[:2000]
    session.flush()


class DriveRateLimiter:
    """Simple token-bucket for Drive / corpus sync (Milestone 5.4.2)."""

    def __init__(self, *, max_per_minute: int = 30) -> None:
        self.max_per_minute = max(1, max_per_minute)
        self._timestamps: list[float] = []

    def acquire(self) -> bool:
        import time

        now = time.monotonic()
        self._timestamps = [t for t in self._timestamps if now - t < 60.0]
        if len(self._timestamps) >= self.max_per_minute:
            return False
        self._timestamps.append(now)
        return True

    def wait_seconds(self) -> float:
        import time

        if not self._timestamps:
            return 0.0
        oldest = min(self._timestamps)
        return max(0.0, 60.0 - (time.monotonic() - oldest))
