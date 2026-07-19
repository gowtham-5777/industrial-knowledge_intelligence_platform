"""Corpus sync domain value objects (local or Drive-shaped)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class DiscoveredFile:
    """One discovery-pass file (metadata only — no content loaded)."""

    source_file_id: str
    name: str
    folder_path: str
    absolute_path: str
    mime_type: str | None
    size_bytes: int
    content_fingerprint: str
    doc_category: str | None = None
    doc_subtype: str | None = None
    drawing_number: str | None = None
    motor_type_code: str | None = None
    asset_domain: str | None = None


@dataclass(slots=True)
class DiscoveryBatchResult:
    files: list[DiscoveredFile] = field(default_factory=list)
    next_cursor: str | None = None
    exhausted: bool = False
    scanned: int = 0


@dataclass(slots=True)
class SyncRunSummary:
    status: str
    source: str
    root: str
    files_discovered: int
    files_upserted: int
    files_downloaded: int
    bytes_downloaded: int
    cursor: str | None = None
    last_error: str | None = None
    last_sync_at: datetime | None = None
    extra: dict[str, Any] = field(default_factory=dict)
