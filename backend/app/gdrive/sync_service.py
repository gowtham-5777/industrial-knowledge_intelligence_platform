"""Corpus sync service — discovery, checkpoint, selective download."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import AppError, ErrorCode
from app.db.repositories.documents import DocumentCatalogRepository
from app.gdrive.local_client import LocalCorpusClient, file_md5
from app.gdrive.models import DiscoveredFile, SyncRunSummary
from app.gdrive.path_classify import normalize_rel_path
from app.gdrive.sync_state import SyncStateRepository
from app.storage.service import StorageService

# Architecture adaptive priority (folder keywords → lower score = higher priority)
_PRIORITY_KEYWORDS: tuple[tuple[str, int], ...] = (
    ("incident", 10),
    ("inspection", 10),
    ("test", 15),
    ("spare", 20),
    ("datasheet", 20),
    ("product description", 20),
    ("manual", 30),
    ("instruction", 30),
    ("maintenance", 40),
    ("safety", 50),
    ("regulation", 60),
    ("certif", 65),
    ("drawing", 70),
    ("sop", 80),
)


def priority_score(folder_path: str, name: str) -> int:
    hay = f"{folder_path}/{name}".lower()
    best = 1000
    for keyword, score in _PRIORITY_KEYWORDS:
        if keyword in hay:
            best = min(best, score)
    return best


class CorpusSyncService:
    """Local/Drive-shaped discovery into catalog + selective blob copy."""

    ROOT_FOLDER_ID = "local-corpus-root"

    def __init__(
        self,
        session: Session,
        settings: Settings,
        storage: StorageService,
    ) -> None:
        self.session = session
        self.settings = settings
        self.storage = storage
        self.catalog_repo = DocumentCatalogRepository(session)
        self.sync_repo = SyncStateRepository(session)
        self._client: LocalCorpusClient | None = None

    def _require_local_root(self) -> Path:
        root = (self.settings.corpus_local_root or "").strip()
        if not root:
            raise AppError(
                "CORPUS_LOCAL_ROOT is required when CORPUS_SOURCE=local",
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
            )
        return Path(root)

    def get_client(self) -> LocalCorpusClient:
        if self._client is None:
            if self.settings.corpus_source != "local":
                raise AppError(
                    "Only CORPUS_SOURCE=local is implemented in Milestone 1.6",
                    error_code=ErrorCode.VALIDATION_ERROR,
                    status_code=400,
                    details={"corpus_source": self.settings.corpus_source},
                )
            self._client = LocalCorpusClient(self._require_local_root())
            self._client.ensure_accessible()
        return self._client

    def auth_check(self) -> dict[str, Any]:
        """Milestone 1.6.1 — local corpus accessibility stands in for Drive auth."""
        client = self.get_client()
        return {
            "source": "local",
            "ok": True,
            "root": str(client.root),
        }

    def get_status(self) -> SyncRunSummary:
        client = self.get_client()
        state = self.sync_repo.get_or_create(self.ROOT_FOLDER_ID)
        meta = dict(state.extra_metadata or {})
        return SyncRunSummary(
            status=state.status,
            source="local",
            root=str(client.root),
            files_discovered=state.files_discovered,
            files_upserted=int(meta.get("files_upserted") or 0),
            files_downloaded=int(meta.get("files_downloaded") or 0),
            bytes_downloaded=int(meta.get("bytes_downloaded") or 0),
            cursor=state.page_token,
            last_error=state.last_error,
            last_sync_at=state.last_sync_at,
            extra=meta,
        )

    def run_discovery(
        self,
        *,
        resume: bool = True,
        max_batches: int | None = None,
    ) -> SyncRunSummary:
        client = self.get_client()
        state = self.sync_repo.get_or_create(self.ROOT_FOLDER_ID)
        self.sync_repo.mark_running(
            state,
            metadata={"phase": "discovery", "root": str(client.root)},
        )

        cursor = state.page_token if resume else None
        if not resume:
            state.page_token = None
            state.files_discovered = 0

        upserted = int((state.extra_metadata or {}).get("files_upserted") or 0)
        discovered_total = state.files_discovered
        batches = 0
        batch_size = self.settings.corpus_discovery_batch_size
        exhausted = False

        try:
            while True:
                batch = client.discover_batch(cursor=cursor, limit=batch_size)
                for item in batch.files:
                    self._upsert_discovered(item)
                    upserted += 1
                discovered_total = upserted
                cursor = batch.next_cursor
                exhausted = batch.exhausted
                self.sync_repo.update_progress(
                    state,
                    page_token=cursor,
                    files_discovered=discovered_total,
                    metadata={
                        "files_upserted": upserted,
                        "phase": "discovery",
                        "exhausted": exhausted,
                    },
                )
                self.session.commit()
                batches += 1
                if exhausted:
                    break
                if max_batches is not None and batches >= max_batches:
                    break

            if exhausted:
                self.sync_repo.mark_completed(
                    state,
                    files_discovered=discovered_total,
                    metadata={
                        "files_upserted": upserted,
                        "phase": "discovery",
                        "exhausted": True,
                    },
                )
            else:
                state.status = "paused"
                self.session.flush()
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            state = self.sync_repo.get_or_create(self.ROOT_FOLDER_ID)
            self.sync_repo.mark_failed(state, str(exc))
            self.session.commit()
            raise

        return self.get_status()

    def _upsert_discovered(self, item: DiscoveredFile) -> None:
        self.catalog_repo.upsert_discovery(
            drive_file_id=item.source_file_id,
            name=item.name,
            folder_path=item.folder_path,
            mime_type=item.mime_type,
            size_bytes=item.size_bytes,
            md5_checksum=item.content_fingerprint,
            doc_category=item.doc_category,
            doc_subtype=item.doc_subtype,
            drawing_number=item.drawing_number,
            motor_type_code=item.motor_type_code,
        )
        # Stash absolute path for selective download (1.6.6)
        row = self.catalog_repo.get_by_drive_file_id(item.source_file_id)
        if row is not None:
            meta = dict(row.extra_metadata or {})
            meta["absolute_path"] = item.absolute_path
            meta["asset_domain"] = item.asset_domain
            meta["source"] = "local"
            row.extra_metadata = meta
            self.session.flush()

    def selective_download(
        self,
        *,
        max_files: int | None = None,
        max_bytes: int | None = None,
        domain_filter: str | None = "Motors",
    ) -> SyncRunSummary:
        """Copy highest-priority catalog files into object storage (not full corpus)."""
        client = self.get_client()
        state = self.sync_repo.get_or_create(self.ROOT_FOLDER_ID)
        self.sync_repo.mark_running(
            state,
            metadata={"phase": "download", "root": str(client.root)},
        )

        max_files = max_files or self.settings.corpus_download_max_files
        max_bytes = max_bytes or self.settings.corpus_download_max_bytes

        from sqlalchemy import select

        from app.db.models.documents import DocumentCatalog

        stmt = select(DocumentCatalog)
        rows = list(self.session.scalars(stmt).all())
        candidates: list[tuple[int, DocumentCatalog]] = []
        for row in rows:
            meta = row.extra_metadata or {}
            domain = meta.get("asset_domain") or (
                (row.folder_path or "").split("/")[0] if row.folder_path else None
            )
            folder = (row.folder_path or "").replace("\\", "/")
            if domain_filter:
                needle = domain_filter.lower()
                domain_l = (domain or "").lower()
                if domain_l != needle and not folder.lower().startswith(needle):
                    continue
            score = priority_score(row.folder_path or "", row.name)
            candidates.append((score, row))

        candidates.sort(key=lambda item: (item[0], item[1].name))

        downloaded = 0
        bytes_copied = 0
        self.storage.ensure_ready()

        try:
            for _score, row in candidates:
                if downloaded >= max_files or bytes_copied >= max_bytes:
                    break
                meta = dict(row.extra_metadata or {})
                abs_path = meta.get("absolute_path")
                if not abs_path:
                    continue
                path = Path(str(abs_path))
                if not path.is_file():
                    continue
                size = int(row.size_bytes or path.stat().st_size)
                if bytes_copied + size > max_bytes and downloaded > 0:
                    break

                checksum = file_md5(path)
                rel_key = normalize_rel_path(
                    str(path.relative_to(client.root))
                    if str(path).startswith(str(client.root))
                    else path.name
                )
                storage_key = f"corpus/{rel_key}"
                content_type = row.mime_type or "application/octet-stream"
                with path.open("rb") as handle:
                    stored = self.storage.upload(
                        storage_key,
                        handle,
                        content_type=content_type,
                        size_bytes=size,
                        metadata={
                            "source_file_id": row.drive_file_id,
                            "md5": checksum,
                        },
                        skip_mime_validation=True,
                    )

                row.md5_checksum = checksum
                meta["storage_key"] = stored.key
                meta["storage_bucket"] = stored.bucket
                meta["downloaded"] = True
                row.extra_metadata = meta
                downloaded += 1
                bytes_copied += size

            meta_state = dict(state.extra_metadata or {})
            meta_state.update(
                {
                    "phase": "download",
                    "files_downloaded": downloaded,
                    "bytes_downloaded": bytes_copied,
                    "domain_filter": domain_filter,
                }
            )
            self.sync_repo.mark_completed(
                state,
                files_discovered=state.files_discovered,
                metadata=meta_state,
            )
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            state = self.sync_repo.get_or_create(self.ROOT_FOLDER_ID)
            self.sync_repo.mark_failed(state, str(exc))
            self.session.commit()
            raise

        return self.get_status()

    def start(
        self,
        *,
        mode: str = "discover",
        resume: bool = True,
        max_batches: int | None = None,
        max_download_files: int | None = None,
        domain_filter: str | None = "Motors",
    ) -> SyncRunSummary:
        mode_norm = mode.strip().lower()
        if mode_norm not in {"discover", "discover_and_download", "download"}:
            raise AppError(
                "Invalid sync mode",
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
                details={
                    "allowed": ["discover", "discover_and_download", "download"],
                },
            )

        _ = self.auth_check()
        summary = self.get_status()
        if mode_norm in {"discover", "discover_and_download"}:
            summary = self.run_discovery(resume=resume, max_batches=max_batches)
        if mode_norm in {"download", "discover_and_download"}:
            summary = self.selective_download(
                max_files=max_download_files,
                domain_filter=domain_filter,
            )
        return summary


def folder_id_for_root(root: str) -> str:
    digest = hashlib.sha256(normalize_rel_path(root).encode("utf-8")).hexdigest()[:24]
    return f"local:{digest}"
