"""Local filesystem corpus client (Drive-shaped discovery without Google API)."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path

from app.core.exceptions import AppError, ErrorCode
from app.gdrive.models import DiscoveredFile, DiscoveryBatchResult
from app.gdrive.path_classify import (
    classify_path,
    extract_drawing_number,
    extract_motor_type_code,
    guess_mime_type,
    normalize_rel_path,
)


def stable_source_file_id(relative_path: str) -> str:
    """Stable idempotency key for a local file (fits document_catalog.drive_file_id)."""
    digest = hashlib.sha256(
        normalize_rel_path(relative_path).encode("utf-8")
    ).hexdigest()
    return f"local:{digest[:40]}"


def content_fingerprint(size_bytes: int, mtime_ns: int) -> str:
    """Fast change detector without hashing multi-GB files during discovery."""
    return f"fp:{size_bytes}:{mtime_ns}"


def file_md5(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


class LocalCorpusClient:
    """Walks a local industrial corpus root with cursor-based pagination."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self._cached_paths: list[str] | None = None

    def ensure_accessible(self) -> None:
        if not self.root.exists():
            raise AppError(
                "Corpus local root does not exist",
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
                details={"root": str(self.root)},
            )
        if not self.root.is_dir():
            raise AppError(
                "Corpus local root is not a directory",
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
                details={"root": str(self.root)},
            )

    def list_relative_files(self) -> list[str]:
        """Return sorted relative POSIX paths (cached for resume batches)."""
        if self._cached_paths is not None:
            return self._cached_paths
        self.ensure_accessible()
        paths: list[str] = []
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            name = path.name
            if name.startswith(".") or name in {"Thumbs.db", "desktop.ini"}:
                continue
            rel = normalize_rel_path(str(path.relative_to(self.root)))
            paths.append(rel)
        paths.sort()
        self._cached_paths = paths
        return paths

    def iter_relative_files(self) -> Iterator[str]:
        yield from self.list_relative_files()

    def discover_batch(
        self,
        *,
        cursor: str | None = None,
        limit: int = 500,
    ) -> DiscoveryBatchResult:
        """Return the next page of discovered files after ``cursor`` (exclusive)."""
        if limit < 1:
            raise AppError(
                "Discovery batch limit must be >= 1",
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
            )

        all_paths = self.list_relative_files()
        start_idx = 0
        if cursor:
            # Resume after the last successfully processed relative path
            for idx, rel in enumerate(all_paths):
                if rel == cursor:
                    start_idx = idx + 1
                    break
            else:
                # Cursor gone — resume after lexicographic predecessors
                for idx, rel in enumerate(all_paths):
                    if rel > cursor:
                        start_idx = idx
                        break
                else:
                    start_idx = len(all_paths)

        files: list[DiscoveredFile] = []
        last_seen: str | None = cursor
        end_idx = min(start_idx + limit, len(all_paths))
        for rel in all_paths[start_idx:end_idx]:
            absolute = self.root / Path(rel)
            try:
                stat = absolute.stat()
            except OSError:
                continue

            folder = normalize_rel_path(str(Path(rel).parent))
            if folder == ".":
                folder = ""
            asset_domain, doc_category, doc_subtype = classify_path(rel)
            name = Path(rel).name
            mtime_ns = int(
                getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))
            )
            discovered = DiscoveredFile(
                source_file_id=stable_source_file_id(rel),
                name=name,
                folder_path=folder,
                absolute_path=str(absolute),
                mime_type=guess_mime_type(name),
                size_bytes=int(stat.st_size),
                content_fingerprint=content_fingerprint(int(stat.st_size), mtime_ns),
                doc_category=doc_category,
                doc_subtype=doc_subtype,
                drawing_number=extract_drawing_number(name),
                motor_type_code=extract_motor_type_code(name, folder),
                asset_domain=asset_domain,
            )
            files.append(discovered)
            last_seen = rel

        exhausted = end_idx >= len(all_paths)
        return DiscoveryBatchResult(
            files=files,
            next_cursor=last_seen,
            exhausted=exhausted,
            scanned=len(files),
        )

    def resolve_absolute(self, relative_or_absolute: str) -> Path:
        path = Path(relative_or_absolute)
        if path.is_absolute():
            resolved = path.resolve()
        else:
            resolved = (self.root / path).resolve()
        if not str(resolved).startswith(str(self.root)):
            raise AppError(
                "Path escapes corpus root",
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
                details={"path": relative_or_absolute},
            )
        return resolved
