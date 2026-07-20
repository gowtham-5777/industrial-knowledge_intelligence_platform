"""Celery worker bootstrap + hardened indexing tasks (Milestones 2.9 / 5.4)."""

from __future__ import annotations

from typing import Any

from celery import Celery

from app.core.config import get_settings


def create_celery_app() -> Celery:
    settings = get_settings()
    app = Celery(
        "industrial_brain",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_default_retry_delay=30,
    )
    return app


celery_app = create_celery_app()


@celery_app.task(
    name="indexing.run_pipeline",
    bind=True,
    max_retries=3,
)
def run_pipeline_task(
    self, document_id: str, force_tier: str | None = None
) -> dict[str, Any]:
    """Async full document intelligence pipeline with DLQ + idempotency audit."""
    from app.cache import CacheService
    from app.core.config import clear_settings_cache, get_settings
    from app.db.models.processing import IndexingJob
    from app.db.session import get_session_factory
    from app.indexing.pipeline import DocumentIntelligencePipeline
    from app.storage.factory import build_storage_service
    from app.workers.hardening import (
        complete_job,
        idempotency_key_for_pipeline,
        mark_job_attempt,
        record_dead_letter,
    )

    clear_settings_cache()
    settings = get_settings()
    factory = get_session_factory()
    session = factory()
    job_id: str | None = None
    idem_key = idempotency_key_for_pipeline(document_id, force_tier)
    try:
        job = mark_job_attempt(session, document_id=document_id)
        job_id = job.id
        session.commit()

        storage = build_storage_service(settings)
        pipeline = DocumentIntelligencePipeline(session, storage, settings)
        result = pipeline.run(document_id, force_tier=force_tier)
        job_row = session.get(IndexingJob, job_id)
        if job_row is not None:
            complete_job(session, job_row, ok=True)
        session.commit()

        try:
            CacheService(settings).invalidate_all_motor360()
        except Exception:  # noqa: BLE001
            pass
        return result
    except Exception as exc:
        session.rollback()
        attempts = (self.request.retries or 0) + 1
        max_retries = self.max_retries if self.max_retries is not None else 3
        fail_session = factory()
        try:
            if job_id:
                job_row = fail_session.get(IndexingJob, job_id)
                if job_row is not None:
                    complete_job(
                        fail_session, job_row, ok=False, error=str(exc)
                    )
            if attempts > max_retries:
                record_dead_letter(
                    fail_session,
                    task_name="indexing.run_pipeline",
                    payload={
                        "document_id": document_id,
                        "force_tier": force_tier,
                    },
                    error_message=str(exc),
                    attempts=attempts,
                    document_id=document_id,
                    idempotency_key=idem_key,
                )
                fail_session.commit()
                raise
            fail_session.commit()
        finally:
            fail_session.close()
        raise self.retry(exc=exc, countdown=min(30 * attempts, 120)) from exc
    finally:
        session.close()


@celery_app.task(name="indexing.embed_incremental", bind=True, max_retries=2)
def embed_incremental_task(self, limit: int = 100) -> dict[str, Any]:
    from app.core.config import get_settings
    from app.db.session import get_session_factory
    from app.indexing.embedding_service import EmbeddingService
    from app.workers.hardening import record_dead_letter

    factory = get_session_factory()
    session = factory()
    try:
        service = EmbeddingService(session, get_settings())
        result = service.embed_incremental(limit=limit)
        session.commit()
        return result
    except Exception as exc:
        session.rollback()
        attempts = (self.request.retries or 0) + 1
        max_retries = self.max_retries if self.max_retries is not None else 2
        if attempts > max_retries:
            fail_session = factory()
            try:
                record_dead_letter(
                    fail_session,
                    task_name="indexing.embed_incremental",
                    payload={"limit": limit},
                    error_message=str(exc),
                    attempts=attempts,
                    idempotency_key=f"embed_incremental:{limit}",
                )
                fail_session.commit()
            finally:
                fail_session.close()
            raise
        raise self.retry(exc=exc, countdown=30) from exc
    finally:
        session.close()
