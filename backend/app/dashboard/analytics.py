"""Fleet coverage + indexing velocity analytics (Milestone 4.6)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.documents import Document, DocumentCatalog
from app.db.models.motors import MotorModel
from app.db.models.processing import IndexingJob


class DomainStat(BaseModel):
    domain: str
    catalog_count: int
    ingested_count: int


class VelocityPoint(BaseModel):
    day: str
    jobs_completed: int
    jobs_failed: int = 0


class AnalyticsOut(BaseModel):
    catalog_total: int
    documents_total: int
    indexed_ready: int
    motor_models: int
    coverage_pct: float
    domains: list[DomainStat] = Field(default_factory=list)
    velocity: list[VelocityPoint] = Field(default_factory=list)
    jobs_by_status: dict[str, int] = Field(default_factory=dict)
    generated_at: str


class AnalyticsService:
    """Fleet coverage and continuous indexing velocity."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def snapshot(self) -> AnalyticsOut:
        catalog_total = (
            self.session.scalar(select(func.count()).select_from(DocumentCatalog)) or 0
        )
        documents_total = (
            self.session.scalar(select(func.count()).select_from(Document)) or 0
        )
        indexed_ready = (
            self.session.scalar(
                select(func.count())
                .select_from(Document)
                .where(Document.status.in_(["ready", "indexed"]))
            )
            or 0
        )
        motor_models = (
            self.session.scalar(select(func.count()).select_from(MotorModel)) or 0
        )

        # Domain breakdown from catalog doc_category prefixes / folders
        domain_rows = self.session.execute(
            select(
                DocumentCatalog.doc_category,
                func.count(DocumentCatalog.id),
            ).group_by(DocumentCatalog.doc_category)
        ).all()
        domains: list[DomainStat] = []
        for category, count in domain_rows:
            domain = (category or "unknown").split("/")[0] or "unknown"
            # ingested with matching category via documents join approximation
            ingested = (
                self.session.scalar(
                    select(func.count())
                    .select_from(Document)
                    .join(DocumentCatalog, Document.catalog_id == DocumentCatalog.id)
                    .where(DocumentCatalog.doc_category == category)
                )
                or 0
            )
            domains.append(
                DomainStat(
                    domain=str(domain),
                    catalog_count=int(count),
                    ingested_count=int(ingested),
                )
            )

        # Merge duplicate domain keys
        merged: dict[str, DomainStat] = {}
        for d in domains:
            if d.domain not in merged:
                merged[d.domain] = d
            else:
                prev = merged[d.domain]
                merged[d.domain] = DomainStat(
                    domain=d.domain,
                    catalog_count=prev.catalog_count + d.catalog_count,
                    ingested_count=prev.ingested_count + d.ingested_count,
                )

        status_rows = self.session.execute(
            select(IndexingJob.status, func.count(IndexingJob.id)).group_by(
                IndexingJob.status
            )
        ).all()
        jobs_by_status = {str(s or "unknown"): int(c) for s, c in status_rows}

        velocity = self._velocity_last_days(7)
        coverage = (
            round(100.0 * indexed_ready / catalog_total, 2) if catalog_total else 0.0
        )

        return AnalyticsOut(
            catalog_total=int(catalog_total),
            documents_total=int(documents_total),
            indexed_ready=int(indexed_ready),
            motor_models=int(motor_models),
            coverage_pct=coverage,
            domains=sorted(merged.values(), key=lambda x: -x.catalog_count)[:12],
            velocity=velocity,
            jobs_by_status=jobs_by_status,
            generated_at=datetime.now(UTC).isoformat(),
        )

    def _velocity_last_days(self, days: int) -> list[VelocityPoint]:
        since = datetime.now(UTC) - timedelta(days=days)
        rows = self.session.scalars(
            select(IndexingJob).where(IndexingJob.created_at >= since)
        ).all()
        buckets: dict[str, dict[str, int]] = {}
        for job in rows:
            day = (job.created_at or since).strftime("%Y-%m-%d")
            bucket = buckets.setdefault(day, {"completed": 0, "failed": 0})
            status = (job.status or "").lower()
            if status in {"completed", "ready", "success", "indexed"}:
                bucket["completed"] += 1
            elif status in {"failed", "error"}:
                bucket["failed"] += 1
        # Fill empty days
        out: list[VelocityPoint] = []
        for i in range(days - 1, -1, -1):
            day = (datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
            b = buckets.get(day, {"completed": 0, "failed": 0})
            out.append(
                VelocityPoint(
                    day=day,
                    jobs_completed=b["completed"],
                    jobs_failed=b["failed"],
                )
            )
        return out
