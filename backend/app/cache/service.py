"""Redis-backed cache with in-process fallback (Milestone 5.3)."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any

from app.core.config import Settings, get_settings
from app.observability import get_logger

_logger = get_logger(__name__)

# Cache key prefixes
PREFIX_MOTOR360 = "motor360:"
PREFIX_SUMMARY = "summary:"
PREFIX_HEALTH = "health:"
PREFIX_RECS = "recs:"


class _MemoryStore:
    """Thread-safe TTL dict used when Redis is unavailable."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, tuple[float, str]] = {}

    def get(self, key: str) -> str | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires, value = item
            if expires and expires < time.time():
                del self._data[key]
                return None
            return value

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        expires = time.time() + ttl_seconds if ttl_seconds > 0 else 0.0
        with self._lock:
            self._data[key] = (expires, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def delete_prefix(self, prefix: str) -> int:
        with self._lock:
            keys = [k for k in self._data if k.startswith(prefix)]
            for k in keys:
                del self._data[k]
            return len(keys)


_MEMORY = _MemoryStore()
_REDIS_CLIENT: Any | None = None
_REDIS_FAILED = False


def _get_redis(settings: Settings):
    global _REDIS_CLIENT, _REDIS_FAILED
    if _REDIS_FAILED:
        return None
    if _REDIS_CLIENT is not None:
        return _REDIS_CLIENT
    try:
        import redis

        client = redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        _REDIS_CLIENT = client
        return client
    except Exception as exc:  # noqa: BLE001
        _REDIS_FAILED = True
        _logger.warning(
            "redis_cache_unavailable_using_memory",
            extra={"error": str(exc)},
        )
        return None


def reset_cache_clients() -> None:
    """Test helper — clear Redis client singleton and memory store."""
    global _REDIS_CLIENT, _REDIS_FAILED
    _REDIS_CLIENT = None
    _REDIS_FAILED = False
    _MEMORY.delete_prefix("")


class CacheService:
    """JSON cache for expensive Aggregate / intelligence payloads."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.default_ttl = getattr(self.settings, "cache_ttl_seconds", 300)

    def get_json(self, key: str) -> Any | None:
        raw = self._get_raw(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def set_json(self, key: str, value: Any, *, ttl: int | None = None) -> None:
        ttl_seconds = ttl if ttl is not None else self.default_ttl
        payload = json.dumps(value, default=str)
        self._set_raw(key, payload, ttl_seconds)

    def delete(self, key: str) -> None:
        client = _get_redis(self.settings)
        if client is not None:
            try:
                client.delete(key)
            except Exception as exc:  # noqa: BLE001
                _logger.warning("cache_delete_failed", extra={"error": str(exc)})
        _MEMORY.delete(key)

    def invalidate_motor(self, motor_id: str) -> None:
        """Drop Asset 360 + related caches for a motor."""
        for prefix in (PREFIX_MOTOR360, PREFIX_SUMMARY, PREFIX_HEALTH, PREFIX_RECS):
            self.delete(f"{prefix}{motor_id}")
        _logger.info("cache_invalidated_motor", extra={"motor_id": motor_id})

    def invalidate_all_motor360(self) -> int:
        client = _get_redis(self.settings)
        count = 0
        if client is not None:
            try:
                for key in client.scan_iter(match=f"{PREFIX_MOTOR360}*"):
                    client.delete(key)
                    count += 1
            except Exception as exc:  # noqa: BLE001
                _logger.warning(
                    "cache_invalidate_scan_failed", extra={"error": str(exc)}
                )
        count += _MEMORY.delete_prefix(PREFIX_MOTOR360)
        return count

    def _get_raw(self, key: str) -> str | None:
        client = _get_redis(self.settings)
        if client is not None:
            try:
                value = client.get(key)
                if value is not None:
                    return value
            except Exception as exc:  # noqa: BLE001
                _logger.warning("cache_get_failed", extra={"error": str(exc)})
        return _MEMORY.get(key)

    def _set_raw(self, key: str, value: str, ttl: int) -> None:
        client = _get_redis(self.settings)
        if client is not None:
            try:
                client.setex(key, ttl, value)
                return
            except Exception as exc:  # noqa: BLE001
                _logger.warning("cache_set_failed", extra={"error": str(exc)})
        _MEMORY.set(key, value, ttl)


def motor360_cache_key(motor_id: str) -> str:
    return f"{PREFIX_MOTOR360}{motor_id}"


def content_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
