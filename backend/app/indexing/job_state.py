"""Parse / indexing job state machine (Architecture §9 — parse stage).

Full pipeline (extracting → indexing → graph_sync → ready) lands in Milestone 2.9.
Milestone 2.1 owns: queued → parsing → parsed | failed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from app.core.exceptions import AppError, ErrorCode


class JobStatus(StrEnum):
    QUEUED = "queued"
    PARSING = "parsing"
    PARSED = "parsed"
    EXTRACTING = "extracting"
    INDEXING = "indexing"
    GRAPH_SYNC = "graph_sync"
    READY = "ready"
    FAILED = "failed"
    # Legacy default on IndexingJob model
    PENDING = "pending"


class DocumentParseStatus(StrEnum):
    """Document.status values introduced for the parse stage."""

    PARSING = "parsing"
    PARSED = "parsed"
    PARSE_FAILED = "parse_failed"
    PARSE_SKIPPED = "parse_skipped"  # T3 metadata-only


_ALLOWED_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.QUEUED: frozenset({JobStatus.PARSING, JobStatus.FAILED}),
    JobStatus.PENDING: frozenset(
        {JobStatus.QUEUED, JobStatus.PARSING, JobStatus.FAILED}
    ),
    JobStatus.PARSING: frozenset({JobStatus.PARSED, JobStatus.FAILED}),
    JobStatus.PARSED: frozenset(
        {JobStatus.EXTRACTING, JobStatus.READY, JobStatus.FAILED}
    ),
    JobStatus.EXTRACTING: frozenset({JobStatus.INDEXING, JobStatus.FAILED}),
    JobStatus.INDEXING: frozenset({JobStatus.GRAPH_SYNC, JobStatus.FAILED}),
    JobStatus.GRAPH_SYNC: frozenset({JobStatus.READY, JobStatus.FAILED}),
    JobStatus.READY: frozenset(),
    JobStatus.FAILED: frozenset({JobStatus.QUEUED}),  # allow retry re-queue
}


def assert_transition(current: str, nxt: JobStatus) -> None:
    try:
        cur = JobStatus(current)
    except ValueError as exc:
        raise AppError(
            f"Unknown job status: {current}",
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
        ) from exc
    allowed = _ALLOWED_TRANSITIONS.get(cur, frozenset())
    if nxt not in allowed:
        raise AppError(
            f"Invalid job transition {cur.value} → {nxt.value}",
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details={"from": cur.value, "to": nxt.value},
        )


def utc_now() -> datetime:
    return datetime.now(UTC)
