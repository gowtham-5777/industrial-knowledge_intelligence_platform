"""In-process sliding-window rate limiter (Milestone 5.6.1)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.exceptions import ErrorCode
from app.core.responses import error_envelope
from app.observability import get_logger
from app.observability.context import get_request_id

_logger = get_logger(__name__)


class SlidingWindowRateLimiter:
    """Per-key request counters over a fixed window."""

    def __init__(self, *, limit: int, window_seconds: float) -> None:
        self.limit = max(1, limit)
        self.window_seconds = max(1.0, window_seconds)
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> tuple[bool, dict[str, Any]]:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            remaining = self.limit - len(bucket)
            if remaining <= 0:
                retry_after = max(1, int(self.window_seconds - (now - bucket[0])))
                return False, {
                    "limit": self.limit,
                    "remaining": 0,
                    "retry_after": retry_after,
                }
            bucket.append(now)
            return True, {
                "limit": self.limit,
                "remaining": remaining - 1,
                "retry_after": 0,
            }

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_LIMITER: SlidingWindowRateLimiter | None = None


def get_rate_limiter(
    *, limit: int = 120, window_seconds: float = 60.0
) -> SlidingWindowRateLimiter:
    global _LIMITER
    if _LIMITER is None:
        _LIMITER = SlidingWindowRateLimiter(
            limit=limit, window_seconds=window_seconds
        )
    return _LIMITER


def reset_rate_limiter() -> None:
    global _LIMITER
    if _LIMITER is not None:
        _LIMITER.reset()
    _LIMITER = None


class RateLimitMiddleware:
    """Reject excess requests with HTTP 429 + envelope body."""

    # Paths exempt from rate limiting (probes)
    EXEMPT_PREFIXES = ("/health", "/ready", "/docs", "/redoc", "/openapi.json")

    def __init__(
        self,
        app: ASGIApp,
        *,
        limit: int = 120,
        window_seconds: float = 60.0,
        enabled: bool = True,
    ) -> None:
        self.app = app
        self.enabled = enabled
        self.limiter = get_rate_limiter(limit=limit, window_seconds=window_seconds)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")
        if any(path.startswith(p) for p in self.EXEMPT_PREFIXES):
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        client_host = request.client.host if request.client else "unknown"
        auth = request.headers.get("authorization") or ""
        # Prefer authenticated identity when present
        key = f"ip:{client_host}"
        if auth.lower().startswith("bearer ") and len(auth) > 20:
            key = f"tok:{auth[7:23]}"

        allowed, meta = self.limiter.allow(key)
        if not allowed:
            _logger.warning(
                "rate_limit_exceeded",
                extra={"key": key, "path": path, **meta},
            )
            body = error_envelope(
                code=ErrorCode.VALIDATION_ERROR,
                message="Rate limit exceeded",
                details=meta,
                request_id=get_request_id(),
            )
            # Use a distinct code string for clients
            body["errors"][0]["code"] = "RATE_LIMITED"
            response = JSONResponse(
                status_code=429,
                content=body,
                headers={"Retry-After": str(meta.get("retry_after") or 60)},
            )
            await response(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append(
                    (b"x-ratelimit-limit", str(meta["limit"]).encode("latin-1"))
                )
                headers.append(
                    (
                        b"x-ratelimit-remaining",
                        str(meta["remaining"]).encode("latin-1"),
                    )
                )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)
