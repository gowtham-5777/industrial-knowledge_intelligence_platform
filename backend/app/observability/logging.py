"""Structured JSON logging configuration and module logger helpers.

Convention: every module obtains a logger via ``get_logger(__name__)``.
Never use the builtin ``print`` in application code — Architecture §14.5.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.observability.context import get_job_id, get_request_id

_CONFIGURED = False
_STANDARD_RECORD_ATTRS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
        "taskName",
    }
)


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line (machine-parseable)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "message": record.getMessage(),
        }

        request_id = getattr(record, "request_id", None) or get_request_id()
        if request_id:
            payload["request_id"] = request_id

        job_id = getattr(record, "job_id", None) or get_job_id()
        if job_id:
            payload["job_id"] = job_id

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_ATTRS or key.startswith("_"):
                continue
            if key in payload:
                continue
            try:
                json.dumps(value)
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)

        return json.dumps(payload, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable fallback for local debugging (``LOG_JSON=false``)."""

    def format(self, record: logging.LogRecord) -> str:
        request_id = getattr(record, "request_id", None) or get_request_id() or "-"
        job_id = getattr(record, "job_id", None) or get_job_id()
        base = (
            f"{self.formatTime(record, self.datefmt)} "
            f"{record.levelname:<8} "
            f"[{request_id}] "
            f"{record.name}: {record.getMessage()}"
        )
        if job_id:
            base = f"{base} job_id={job_id}"
        if record.exc_info:
            base = f"{base}\n{self.formatException(record.exc_info)}"
        return base


class ContextFilter(logging.Filter):
    """Copy correlation IDs from contextvars onto each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(record, "request_id", None) is None:
            request_id = get_request_id()
            if request_id is not None:
                record.request_id = request_id  # type: ignore[attr-defined]
        if getattr(record, "job_id", None) is None:
            job_id = get_job_id()
            if job_id is not None:
                record.job_id = job_id  # type: ignore[attr-defined]
        return True


def get_logger(name: str) -> logging.Logger:
    """Return a module logger. Prefer ``get_logger(__name__)`` everywhere."""
    return logging.getLogger(name)


def configure_logging(
    *,
    level: str = "INFO",
    json_logs: bool = True,
    force: bool = False,
) -> None:
    """Configure root + uvicorn loggers once (idempotent unless ``force``)."""
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(_parse_level(level))

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(_parse_level(level))
    handler.addFilter(ContextFilter())
    handler.setFormatter(JsonFormatter() if json_logs else TextFormatter())
    root.addHandler(handler)

    # Align common third-party loggers with our format; quiet noisy ones.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    _CONFIGURED = True


def _parse_level(level: str) -> int:
    return getattr(logging, level.upper(), logging.INFO)


def reset_logging_state() -> None:
    """Test helper: allow re-configuration of the logging stack."""
    global _CONFIGURED
    _CONFIGURED = False
