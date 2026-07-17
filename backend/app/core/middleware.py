"""HTTP middleware: request ID correlation and process timing.

Implemented as pure ASGI middleware (not BaseHTTPMiddleware) so FastAPI
exception handlers remain reachable for route errors.
"""

from __future__ import annotations

import time
import uuid

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
PROCESS_TIME_HEADER = "X-Process-Time"
REQUEST_ID_STATE_KEY = "request_id"
PROCESS_TIME_STATE_KEY = "process_time_ms"


def get_request_id(request: Request) -> str | None:
    """Read request ID previously attached by RequestIdMiddleware."""
    return getattr(request.state, REQUEST_ID_STATE_KEY, None)


def _header_value(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return value.decode("latin-1")
    return None


class RequestIdMiddleware:
    """Ensure every request/response carries an ``X-Request-ID``."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _header_value(scope, b"x-request-id") or str(uuid.uuid4())
        request = Request(scope)
        setattr(request.state, REQUEST_ID_STATE_KEY, request_id)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_request_id)


class TimingMiddleware:
    """Measure request duration and expose ``X-Process-Time`` (seconds)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()

        async def send_with_timing(message: Message) -> None:
            if message["type"] == "http.response.start":
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                request = Request(scope)
                setattr(request.state, PROCESS_TIME_STATE_KEY, elapsed_ms)
                headers = list(message.get("headers", []))
                timing = f"{elapsed_ms / 1000.0:.6f}".encode("latin-1")
                headers.append((b"x-process-time", timing))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_timing)
