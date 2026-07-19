"""HTTP middleware: request ID correlation, timing, access logs, metrics.

Implemented as pure ASGI middleware (not BaseHTTPMiddleware) so FastAPI
exception handlers remain reachable for route errors.
"""

from __future__ import annotations

import time
import uuid

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.observability.context import (
    clear_context,
    set_request_id,
)
from app.observability.context import (
    get_request_id as current_request_id,
)
from app.observability.logging import get_logger
from app.observability.metrics import get_request_metrics

REQUEST_ID_HEADER = "X-Request-ID"
PROCESS_TIME_HEADER = "X-Process-Time"
REQUEST_ID_STATE_KEY = "request_id"
PROCESS_TIME_STATE_KEY = "process_time_ms"

_access_logger = get_logger("app.access")


def get_request_id(request: Request) -> str | None:
    """Read request ID previously attached by RequestIdMiddleware."""
    return getattr(request.state, REQUEST_ID_STATE_KEY, None)


def _header_value(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return value.decode("latin-1")
    return None


class RequestIdMiddleware:
    """Ensure every request/response carries an ``X-Request-ID``.

    Also binds the ID into a contextvar so structured logs include
    ``request_id`` without threading it through every call site.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _header_value(scope, b"x-request-id") or str(uuid.uuid4())
        request = Request(scope)
        setattr(request.state, REQUEST_ID_STATE_KEY, request_id)
        set_request_id(request_id)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            clear_context()


class TimingMiddleware:
    """Measure duration, emit access log, and record latency metrics."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()
        status_code_holder = {"code": 500}

        async def send_with_timing(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_code_holder["code"] = int(message.get("status", 500))
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                request = Request(scope)
                setattr(request.state, PROCESS_TIME_STATE_KEY, elapsed_ms)
                headers = list(message.get("headers", []))
                timing = f"{elapsed_ms / 1000.0:.6f}".encode("latin-1")
                headers.append((b"x-process-time", timing))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_timing)
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            method = scope.get("method", "GET")
            path = scope.get("path", "/")
            status = status_code_holder["code"]
            get_request_metrics().record(
                method=method,
                path=path,
                status_code=status,
                latency_ms=elapsed_ms,
            )
            extra: dict = {
                "http_method": method,
                "http_path": path,
                "http_status": status,
                "latency_ms": round(elapsed_ms, 3),
            }
            rid = current_request_id()
            if rid:
                extra["request_id"] = rid
            _access_logger.info("request completed", extra=extra)
