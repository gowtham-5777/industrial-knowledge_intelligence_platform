"""Request / job correlation context for structured logs."""

from __future__ import annotations

from contextvars import ContextVar

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_job_id: ContextVar[str | None] = ContextVar("job_id", default=None)


def get_request_id() -> str | None:
    """Return the correlation ID bound to the current async/task context."""
    return _request_id.get()


def set_request_id(request_id: str | None) -> None:
    """Bind (or clear) the request correlation ID for log enrichment."""
    _request_id.set(request_id)


def get_job_id() -> str | None:
    """Return the optional pipeline/job ID for the current context."""
    return _job_id.get()


def set_job_id(job_id: str | None) -> None:
    """Bind (or clear) a job ID for pipeline stage logging."""
    _job_id.set(job_id)


def clear_context() -> None:
    """Reset correlation fields (tests / after request)."""
    _request_id.set(None)
    _job_id.set(None)
