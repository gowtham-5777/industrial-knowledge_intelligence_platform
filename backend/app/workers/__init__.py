"""Workers package — Celery tasks for continuous indexing."""

from app.workers.celery_app import celery_app, embed_incremental_task, run_pipeline_task

__all__ = ["celery_app", "embed_incremental_task", "run_pipeline_task"]
