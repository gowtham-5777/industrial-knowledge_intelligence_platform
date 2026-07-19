"""Sync API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SyncStartRequest(BaseModel):
    mode: Literal["discover", "discover_and_download", "download"] = "discover"
    resume: bool = True
    max_batches: int | None = Field(
        default=None,
        ge=1,
        description="Optional cap on discovery batches (for smoke / resume tests).",
    )
    max_download_files: int | None = Field(default=None, ge=1)
    domain_filter: str | None = Field(
        default="Motors",
        description="Selective download domain filter (top-level folder name).",
    )


class SyncStatusData(BaseModel):
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
    extra: dict[str, Any] = Field(default_factory=dict)


class SyncAuthData(BaseModel):
    source: str
    ok: bool
    root: str
