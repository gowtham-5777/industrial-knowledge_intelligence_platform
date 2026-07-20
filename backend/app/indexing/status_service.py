"""Priority queue + indexing status helpers (Milestone 2.9)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.chunks import DocumentChunk
from app.db.models.documents import Document, DocumentCatalog
from app.db.models.processing import IndexingJob
from app.indexing.pipeline import CATEGORY_PRIORITY, priority_for_category
from app.observability import get_logger

_logger = get_logger(__name__)

HERO_MOTOR_FOLDER_TOKEN = "Low_Voltage_Motor - 001"


class IndexingStatusService:
    """Aggregate discovered / processing / indexed counts for UI."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def status(self) -> dict[str, Any]:
        catalog_total = (
            self.session.scalar(select(func.count()).select_from(DocumentCatalog)) or 0
        )
        documents_total = (
            self.session.scalar(select(func.count()).select_from(Document)) or 0
        )
        by_status_rows = self.session.execute(
            select(Document.status, func.count()).group_by(Document.status)
        ).all()
        by_status = {row[0]: row[1] for row in by_status_rows}

        jobs_rows = self.session.execute(
            select(IndexingJob.status, func.count()).group_by(IndexingJob.status)
        ).all()
        jobs_by_status = {row[0]: row[1] for row in jobs_rows}

        chunk_count = (
            self.session.scalar(select(func.count()).select_from(DocumentChunk)) or 0
        )
        indexed_chunks = (
            self.session.scalar(
                select(func.count())
                .select_from(DocumentChunk)
                .where(DocumentChunk.status == "indexed")
            )
            or 0
        )

        return {
            "catalog_discovered": catalog_total,
            "documents": documents_total,
            "documents_by_status": by_status,
            "jobs_by_status": jobs_by_status,
            "chunks": chunk_count,
            "chunks_indexed": indexed_chunks,
            "processing": jobs_by_status.get("parsing", 0)
            + jobs_by_status.get("extracting", 0)
            + jobs_by_status.get("indexing", 0)
            + jobs_by_status.get("graph_sync", 0),
            "ready": by_status.get("ready", 0) + jobs_by_status.get("ready", 0),
        }

    def select_priority_subset(
        self,
        *,
        hero_only: bool = True,
        limit: int = 50,
        categories: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Select hero-motor (and optional category) documents for indexing."""
        stmt = (
            select(Document)
            .options(selectinload(Document.catalog_entry))
            .join(DocumentCatalog, Document.catalog_id == DocumentCatalog.id)
        )
        if hero_only:
            stmt = stmt.where(
                DocumentCatalog.folder_path.ilike(f"%{HERO_MOTOR_FOLDER_TOKEN}%")
            )
        if categories:
            stmt = stmt.where(DocumentCatalog.doc_category.in_(categories))

        docs = list(self.session.scalars(stmt.limit(limit * 5)).all())

        def sort_key(doc: Document) -> tuple[int, str]:
            cat = doc.catalog_entry.doc_category if doc.catalog_entry else None
            return (priority_for_category(cat), doc.title or "")

        docs.sort(key=sort_key)
        selected = docs[:limit]
        return [
            {
                "document_id": d.id,
                "title": d.title,
                "status": d.status,
                "doc_category": (
                    d.catalog_entry.doc_category if d.catalog_entry else None
                ),
                "priority": priority_for_category(
                    d.catalog_entry.doc_category if d.catalog_entry else None
                ),
                "folder_path": d.catalog_entry.folder_path if d.catalog_entry else None,
                "drawing_number": (
                    d.catalog_entry.drawing_number if d.catalog_entry else None
                ),
                "motor_type_code": (
                    d.catalog_entry.motor_type_code if d.catalog_entry else None
                ),
            }
            for d in selected
        ]

    def enqueue_priority(
        self,
        *,
        document_ids: list[str] | None = None,
        hero_only: bool = True,
        limit: int = 20,
        async_worker: bool = False,
    ) -> dict[str, Any]:
        """Queue documents by adaptive priority (test reports first)."""
        if document_ids:
            targets = [{"document_id": i, "priority": 50} for i in document_ids]
        else:
            targets = self.select_priority_subset(hero_only=hero_only, limit=limit)

        # Sort by priority ascending (lower = sooner)
        targets.sort(key=lambda x: x.get("priority", 100))

        queued: list[dict[str, Any]] = []
        if async_worker:
            try:
                from app.workers.celery_app import run_pipeline_task

                for item in targets:
                    async_result = run_pipeline_task.delay(item["document_id"])
                    queued.append(
                        {
                            "document_id": item["document_id"],
                            "task_id": async_result.id,
                            "priority": item.get("priority"),
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                _logger.warning(
                    "celery enqueue failed; returning planned order only",
                    extra={"error": str(exc)},
                )
                queued = [
                    {
                        "document_id": item["document_id"],
                        "priority": item.get("priority"),
                        "planned": True,
                    }
                    for item in targets
                ]
        else:
            queued = [
                {
                    "document_id": item["document_id"],
                    "priority": item.get("priority"),
                    "planned": True,
                }
                for item in targets
            ]

        return {
            "queued": queued,
            "order_proof": [q["document_id"] for q in queued],
            "priority_map": CATEGORY_PRIORITY,
        }
