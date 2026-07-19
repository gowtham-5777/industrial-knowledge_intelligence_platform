"""In-process request metrics hooks (latency counters).

Foundation only — Prometheus / OTel export arrives in Phase 5 Monitoring.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RequestMetrics:
    """Thread-safe counters for HTTP request volume and latency."""

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    request_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    latency_buckets_ms: dict[str, int] = field(
        default_factory=lambda: {
            "le_50": 0,
            "le_100": 0,
            "le_250": 0,
            "le_500": 0,
            "le_1000": 0,
            "le_inf": 0,
        }
    )
    by_status: dict[str, int] = field(default_factory=dict)
    by_method_path: dict[str, int] = field(default_factory=dict)

    def record(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        latency_ms: float,
    ) -> None:
        """Record one completed HTTP request."""
        route_key = f"{method.upper()} {path}"
        status_key = str(status_code)
        with self._lock:
            self.request_count += 1
            self.total_latency_ms += latency_ms
            if latency_ms > self.max_latency_ms:
                self.max_latency_ms = latency_ms
            if status_code >= 500:
                self.error_count += 1
            self.by_status[status_key] = self.by_status.get(status_key, 0) + 1
            self.by_method_path[route_key] = self.by_method_path.get(route_key, 0) + 1
            self._bump_latency_bucket(latency_ms)

    def _bump_latency_bucket(self, latency_ms: float) -> None:
        if latency_ms <= 50:
            self.latency_buckets_ms["le_50"] += 1
        elif latency_ms <= 100:
            self.latency_buckets_ms["le_100"] += 1
        elif latency_ms <= 250:
            self.latency_buckets_ms["le_250"] += 1
        elif latency_ms <= 500:
            self.latency_buckets_ms["le_500"] += 1
        elif latency_ms <= 1000:
            self.latency_buckets_ms["le_1000"] += 1
        else:
            self.latency_buckets_ms["le_inf"] += 1

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable metrics snapshot."""
        with self._lock:
            avg = (
                self.total_latency_ms / self.request_count
                if self.request_count
                else 0.0
            )
            return {
                "request_count": self.request_count,
                "error_count": self.error_count,
                "total_latency_ms": round(self.total_latency_ms, 3),
                "avg_latency_ms": round(avg, 3),
                "max_latency_ms": round(self.max_latency_ms, 3),
                "latency_buckets_ms": dict(self.latency_buckets_ms),
                "by_status": dict(self.by_status),
                "by_method_path": dict(self.by_method_path),
            }

    def reset(self) -> None:
        """Clear all counters (tests)."""
        with self._lock:
            self.request_count = 0
            self.error_count = 0
            self.total_latency_ms = 0.0
            self.max_latency_ms = 0.0
            for key in self.latency_buckets_ms:
                self.latency_buckets_ms[key] = 0
            self.by_status.clear()
            self.by_method_path.clear()


_REQUEST_METRICS = RequestMetrics()


def get_request_metrics() -> RequestMetrics:
    """Process-wide HTTP metrics registry."""
    return _REQUEST_METRICS


class Timer:
    """Simple latency timer for service/pipeline hooks."""

    def __init__(self) -> None:
        self._started = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._started) * 1000.0
