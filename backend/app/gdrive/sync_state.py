"""Sync state repository for corpus discovery checkpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.processing import GdriveSyncState


class SyncStateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_folder_id(self, folder_id: str) -> GdriveSyncState | None:
        stmt = select(GdriveSyncState).where(GdriveSyncState.folder_id == folder_id)
        return self.session.scalars(stmt).first()

    def get_or_create(self, folder_id: str) -> GdriveSyncState:
        existing = self.get_by_folder_id(folder_id)
        if existing is not None:
            return existing
        row = GdriveSyncState(folder_id=folder_id, status="idle", files_discovered=0)
        self.session.add(row)
        self.session.flush()
        return row

    def mark_running(
        self,
        state: GdriveSyncState,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> GdriveSyncState:
        state.status = "running"
        state.last_error = None
        if metadata:
            state.extra_metadata = {**(state.extra_metadata or {}), **metadata}
        self.session.flush()
        return state

    def update_progress(
        self,
        state: GdriveSyncState,
        *,
        page_token: str | None,
        files_discovered: int,
        metadata: dict[str, Any] | None = None,
    ) -> GdriveSyncState:
        state.page_token = page_token
        state.files_discovered = files_discovered
        if metadata:
            state.extra_metadata = {**(state.extra_metadata or {}), **metadata}
        self.session.flush()
        return state

    def mark_completed(
        self,
        state: GdriveSyncState,
        *,
        files_discovered: int,
        metadata: dict[str, Any] | None = None,
    ) -> GdriveSyncState:
        state.status = "completed"
        state.files_discovered = files_discovered
        state.last_sync_at = datetime.now(UTC)
        state.last_error = None
        if metadata:
            state.extra_metadata = {**(state.extra_metadata or {}), **metadata}
        self.session.flush()
        return state

    def mark_failed(self, state: GdriveSyncState, error: str) -> GdriveSyncState:
        state.status = "failed"
        state.last_error = error
        state.last_sync_at = datetime.now(UTC)
        self.session.flush()
        return state
