"""Ops monitoring endpoints — metrics, DLQ, secrets hygiene (Milestone 5.5)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.auth.dependencies import require_roles
from app.core.dependencies import DbSessionDep, RequestIdDep, SettingsDep
from app.core.responses import success_envelope
from app.db.models.processing import DeadLetterJob, IndexingJob
from app.observability.metrics import get_request_metrics
from app.security.hardening import secrets_hygiene_report
from app.workers.hardening import list_dead_letters

router = APIRouter(prefix="/ops", tags=["Ops"])

OpsReaders = Depends(require_roles("SystemAdmin", "PlantManager", "Auditor"))


@router.get(
    "/metrics",
    summary="API latency + volume metrics snapshot",
    dependencies=[OpsReaders],
)
def metrics_snapshot(request_id: RequestIdDep) -> dict:
    snap = get_request_metrics().snapshot()
    return success_envelope(snap, request_id=request_id)


@router.get(
    "/metrics/prometheus",
    summary="Prometheus text exposition (subset)",
    dependencies=[OpsReaders],
)
def metrics_prometheus(request_id: RequestIdDep) -> dict:
    snap = get_request_metrics().snapshot()
    lines = [
        "# HELP industrial_brain_http_requests_total Total HTTP requests",
        "# TYPE industrial_brain_http_requests_total counter",
        f"industrial_brain_http_requests_total {snap['request_count']}",
        "# HELP industrial_brain_http_errors_total Total HTTP 5xx",
        "# TYPE industrial_brain_http_errors_total counter",
        f"industrial_brain_http_errors_total {snap['error_count']}",
        "# HELP industrial_brain_http_latency_ms_avg Average latency ms",
        "# TYPE industrial_brain_http_latency_ms_avg gauge",
        f"industrial_brain_http_latency_ms_avg {snap['avg_latency_ms']}",
        "# HELP industrial_brain_http_latency_ms_max Max latency ms",
        "# TYPE industrial_brain_http_latency_ms_max gauge",
        f"industrial_brain_http_latency_ms_max {snap['max_latency_ms']}",
    ]
    return success_envelope(
        {"format": "prometheus_text", "body": "\n".join(lines) + "\n"},
        request_id=request_id,
    )


@router.get(
    "/queue",
    summary="Indexing job queue depth + DLQ counts",
    dependencies=[OpsReaders],
)
def queue_depth(session: DbSessionDep, request_id: RequestIdDep) -> dict:
    pending = session.scalar(
        select(func.count())
        .select_from(IndexingJob)
        .where(IndexingJob.status.in_(("pending", "running")))
    )
    failed = session.scalar(
        select(func.count())
        .select_from(IndexingJob)
        .where(IndexingJob.status == "failed")
    )
    completed = session.scalar(
        select(func.count())
        .select_from(IndexingJob)
        .where(IndexingJob.status == "completed")
    )
    dlq_open = session.scalar(
        select(func.count())
        .select_from(DeadLetterJob)
        .where(DeadLetterJob.status == "open")
    )
    # Indexing velocity: completed in last lookback via finished jobs
    data = {
        "queue_depth": int(pending or 0),
        "failed_jobs": int(failed or 0),
        "completed_jobs": int(completed or 0),
        "dead_letter_open": int(dlq_open or 0),
        "indexing_velocity": {
            "completed_total": int(completed or 0),
            "unit": "jobs",
        },
    }
    return success_envelope(data, request_id=request_id)


@router.get(
    "/dead-letters",
    summary="List dead-letter jobs",
    dependencies=[OpsReaders],
)
def dead_letters(
    session: DbSessionDep,
    request_id: RequestIdDep,
    status: str = "open",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict:
    rows = list_dead_letters(session, status=status, limit=limit)
    items: list[dict[str, Any]] = [
        {
            "id": r.id,
            "task_name": r.task_name,
            "idempotency_key": r.idempotency_key,
            "error_message": r.error_message,
            "attempts": r.attempts,
            "status": r.status,
            "document_id": r.document_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return success_envelope(
        {"items": items, "count": len(items)},
        request_id=request_id,
    )


@router.get(
    "/health-dashboard",
    summary="Ops health dashboard payload",
    dependencies=[OpsReaders],
)
def health_dashboard(
    session: DbSessionDep,
    settings: SettingsDep,
    request_id: RequestIdDep,
) -> dict:
    metrics = get_request_metrics().snapshot()
    pending = session.scalar(
        select(func.count())
        .select_from(IndexingJob)
        .where(IndexingJob.status.in_(("pending", "running")))
    )
    dlq = session.scalar(
        select(func.count())
        .select_from(DeadLetterJob)
        .where(DeadLetterJob.status == "open")
    )
    hygiene = secrets_hygiene_report(settings)
    data = {
        "api": {
            "request_count": metrics["request_count"],
            "error_count": metrics["error_count"],
            "avg_latency_ms": metrics["avg_latency_ms"],
            "max_latency_ms": metrics["max_latency_ms"],
        },
        "workers": {
            "queue_depth": int(pending or 0),
            "dead_letter_open": int(dlq or 0),
        },
        "security": hygiene,
        "status": (
            "degraded"
            if metrics["error_count"] > 0 or int(dlq or 0) > 0
            else "healthy"
        ),
    }
    return success_envelope(data, request_id=request_id)


@router.get(
    "/secrets-hygiene",
    summary="Secrets / CORS hygiene check",
    dependencies=[Depends(require_roles("SystemAdmin"))],
)
def secrets_check(settings: SettingsDep, request_id: RequestIdDep) -> dict:
    return success_envelope(secrets_hygiene_report(settings), request_id=request_id)
