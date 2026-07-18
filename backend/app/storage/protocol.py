"""Object storage port (hexagonal adapter boundary)."""

from __future__ import annotations

from typing import BinaryIO, Protocol, runtime_checkable

from app.storage.models import SignedUrl, StorageHealth, StoredObject


@runtime_checkable
class ObjectStoragePort(Protocol):
    """Backend-agnostic blob operations used by Drive sync and uploads."""

    @property
    def backend_name(self) -> str: ...

    @property
    def bucket(self) -> str: ...

    def ensure_bucket(self) -> None:
        """Create the configured bucket/container if it does not exist."""

    def upload(
        self,
        key: str,
        data: BinaryIO | bytes,
        *,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> StoredObject: ...

    def download(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...

    def exists(self, key: str) -> bool: ...

    def generate_signed_url(
        self,
        key: str,
        *,
        method: str = "GET",
        expires_in: int = 3600,
        content_type: str | None = None,
    ) -> SignedUrl: ...

    def health_check(self) -> StorageHealth: ...
