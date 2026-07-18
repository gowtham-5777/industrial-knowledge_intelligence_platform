"""Local filesystem object storage (dev / unit tests)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import BinaryIO
from urllib.parse import quote

from app.core.exceptions import AppError, ErrorCode, NotFoundError
from app.storage.io_utils import read_bytes
from app.storage.models import SignedUrl, StorageHealth, StoredObject


class LocalObjectStorage:
    """Stores objects under a local directory tree (no MinIO required)."""

    def __init__(self, root: str | Path, bucket: str) -> None:
        self._root = Path(root)
        self._bucket = bucket
        self._bucket_dir = self._root / bucket
        self._meta_dir = self._bucket_dir / ".meta"

    @property
    def backend_name(self) -> str:
        return "local"

    @property
    def bucket(self) -> str:
        return self._bucket

    def ensure_bucket(self) -> None:
        self._bucket_dir.mkdir(parents=True, exist_ok=True)
        self._meta_dir.mkdir(parents=True, exist_ok=True)

    def _object_path(self, key: str) -> Path:
        path = (self._bucket_dir / key).resolve()
        if not str(path).startswith(str(self._bucket_dir.resolve())):
            raise AppError(
                "Invalid object key path",
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
                details={"key": key},
            )
        return path

    def _meta_path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._meta_dir / f"{digest}.json"

    def upload(
        self,
        key: str,
        data: BinaryIO | bytes,
        *,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> StoredObject:
        self.ensure_bucket()
        payload = read_bytes(data)
        path = self._object_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        etag = hashlib.md5(payload, usedforsecurity=False).hexdigest()
        uploaded_at = datetime.now(UTC)
        meta = {
            "key": key,
            "content_type": content_type,
            "size_bytes": len(payload),
            "etag": etag,
            "metadata": metadata or {},
            "uploaded_at": uploaded_at.isoformat(),
        }
        self._meta_path(key).write_text(json.dumps(meta), encoding="utf-8")
        return StoredObject(
            key=key,
            bucket=self._bucket,
            content_type=content_type,
            size_bytes=len(payload),
            etag=etag,
            metadata=dict(metadata or {}),
            uploaded_at=uploaded_at,
        )

    def download(self, key: str) -> bytes:
        path = self._object_path(key)
        if not path.is_file():
            raise NotFoundError(
                "Object not found",
                details={"key": key, "bucket": self._bucket},
            )
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._object_path(key)
        if path.is_file():
            path.unlink()
        meta = self._meta_path(key)
        if meta.is_file():
            meta.unlink()

    def exists(self, key: str) -> bool:
        return self._object_path(key).is_file()

    def generate_signed_url(
        self,
        key: str,
        *,
        method: str = "GET",
        expires_in: int = 3600,
        content_type: str | None = None,
    ) -> SignedUrl:
        if not self.exists(key) and method.upper() == "GET":
            raise NotFoundError(
                "Object not found",
                details={"key": key, "bucket": self._bucket},
            )
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
        # Synthetic URL — local backend has no HTTP gateway until Milestone 1.9
        url = (
            f"local://{self._bucket}/{quote(key, safe='/')}"
            f"?expires={int(expires_at.timestamp())}&method={method.upper()}"
        )
        headers: dict[str, str] = {}
        if content_type and method.upper() in {"PUT", "POST"}:
            headers["Content-Type"] = content_type
        return SignedUrl(
            url=url,
            method=method.upper(),
            expires_in=expires_in,
            key=key,
            headers=headers,
        )

    def health_check(self) -> StorageHealth:
        try:
            self.ensure_bucket()
            probe = self._bucket_dir / ".healthcheck"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return StorageHealth(
                backend=self.backend_name,
                bucket=self._bucket,
                ok=True,
                extras={"root": str(self._root.resolve())},
            )
        except OSError as exc:
            return StorageHealth(
                backend=self.backend_name,
                bucket=self._bucket,
                ok=False,
                detail=str(exc),
            )
