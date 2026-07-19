"""Corpus sync API routes (local source for Milestone 1.6)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.core.dependencies import DbSessionDep, RequestIdDep, SettingsDep
from app.core.responses import success_envelope
from app.gdrive.schemas import SyncAuthData, SyncStartRequest, SyncStatusData
from app.gdrive.sync_service import CorpusSyncService
from app.storage.factory import get_storage_service

router = APIRouter(
    prefix="/sync",
    tags=["Sync"],
    dependencies=[Depends(get_current_user)],
)


def get_corpus_sync_service(
    session: DbSessionDep,
    settings: SettingsDep,
) -> CorpusSyncService:
    return CorpusSyncService(session, settings, get_storage_service())


CorpusSyncServiceDep = Annotated[CorpusSyncService, Depends(get_corpus_sync_service)]


@router.get(
    "/auth/check",
    summary="Verify corpus source credentials / local root access",
)
def sync_auth_check(
    sync: CorpusSyncServiceDep,
    request_id: RequestIdDep,
) -> dict:
    data = SyncAuthData.model_validate(sync.auth_check())
    return success_envelope(data.model_dump(), request_id=request_id)


@router.get(
    "/status",
    summary="Corpus sync status (discovery + selective download)",
)
def sync_status(
    sync: CorpusSyncServiceDep,
    request_id: RequestIdDep,
) -> dict:
    summary = sync.get_status()
    data = SyncStatusData(
        status=summary.status,
        source=summary.source,
        root=summary.root,
        files_discovered=summary.files_discovered,
        files_upserted=summary.files_upserted,
        files_downloaded=summary.files_downloaded,
        bytes_downloaded=summary.bytes_downloaded,
        cursor=summary.cursor,
        last_error=summary.last_error,
        last_sync_at=summary.last_sync_at,
        extra=summary.extra,
    )
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)


@router.post(
    "/start",
    summary="Start discovery and/or selective download into object storage",
)
def sync_start(
    body: SyncStartRequest,
    sync: CorpusSyncServiceDep,
    request_id: RequestIdDep,
) -> dict:
    summary = sync.start(
        mode=body.mode,
        resume=body.resume,
        max_batches=body.max_batches,
        max_download_files=body.max_download_files,
        domain_filter=body.domain_filter,
    )
    data = SyncStatusData(
        status=summary.status,
        source=summary.source,
        root=summary.root,
        files_discovered=summary.files_discovered,
        files_upserted=summary.files_upserted,
        files_downloaded=summary.files_downloaded,
        bytes_downloaded=summary.bytes_downloaded,
        cursor=summary.cursor,
        last_error=summary.last_error,
        last_sync_at=summary.last_sync_at,
        extra=summary.extra,
    )
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)
