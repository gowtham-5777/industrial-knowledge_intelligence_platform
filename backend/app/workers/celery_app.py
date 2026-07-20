"""Celery worker bootstrap + indexing tasks (Milestone 2.9)."""

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
    )
    return app


celery_app = create_celery_app()


@celery_app.task(name="indexing.run_pipeline", bind=True, max_retries=2)
def run_pipeline_task(
    self, document_id: str, force_tier: str | None = None
) -> dict[str, Any]:
    """Async full document intelligence pipeline."""
    from app.core.config import clear_settings_cache, get_settings
    from app.db.session import get_session_factory
    from app.indexing.pipeline import DocumentIntelligencePipeline
    from app.storage.factory import build_storage_service

    clear_settings_cache()
    settings = get_settings()
    factory = get_session_factory()
    session = factory()
    try:
        storage = build_storage_service(settings)
        pipeline = DocumentIntelligencePipeline(session, storage, settings)
        result = pipeline.run(document_id, force_tier=force_tier)
        session.commit()
        return result
    except Exception as exc:
        session.rollback()
        raise self.retry(exc=exc, countdown=30) from exc
    finally:
        session.close()


@celery_app.task(name="indexing.embed_incremental")
def embed_incremental_task(limit: int = 100) -> dict[str, Any]:
    from app.core.config import get_settings
    from app.db.session import get_session_factory
    from app.indexing.embedding_service import EmbeddingService

    factory = get_session_factory()
    session = factory()
    try:
        service = EmbeddingService(session, get_settings())
        result = service.embed_incremental(limit=limit)
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
