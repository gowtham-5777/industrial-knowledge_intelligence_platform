"""Storage domain value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class StoredObject:
    """Metadata for an object written to (or read from) blob storage."""

    key: str
    bucket: str
    content_type: str
    size_bytes: int
    etag: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    uploaded_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SignedUrl:
    """Time-limited URL for upload or download."""

    url: str
    method: str
    expires_in: int
    key: str
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StorageHealth:
    """Lightweight backend probe result."""

    backend: str
    bucket: str
    ok: bool
    detail: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)
