"""Storage service — validation + port orchestration."""

from __future__ import annotations

from typing import BinaryIO

from app.core.exceptions import AppError, ErrorCode
from app.storage.models import SignedUrl, StorageHealth, StoredObject
from app.storage.protocol import ObjectStoragePort
from app.storage.validation import (
    DEFAULT_ALLOWED_MIME_TYPES,
    DEFAULT_MAX_UPLOAD_BYTES,
    validate_content_type,
    validate_object_key,
    validate_size,
)


class StorageService:
    """Application-facing storage API used by Drive sync and document upload."""

    def __init__(
        self,
        port: ObjectStoragePort,
        *,
        max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
        allowed_mime_types: frozenset[str] | set[str] | None = None,
    ) -> None:
        self._port = port
        self._max_upload_bytes = max_upload_bytes
        self._allowed_mime_types = (
            frozenset(allowed_mime_types)
            if allowed_mime_types is not None
            else DEFAULT_ALLOWED_MIME_TYPES
        )

    @property
    def backend_name(self) -> str:
        return self._port.backend_name

    @property
    def bucket(self) -> str:
        return self._port.bucket

    def ensure_ready(self) -> None:
        self._port.ensure_bucket()

    def upload(
        self,
        key: str,
        data: BinaryIO | bytes,
        *,
        content_type: str,
        metadata: dict[str, str] | None = None,
        size_bytes: int | None = None,
        skip_mime_validation: bool = False,
    ) -> StoredObject:
        cleaned_key = validate_object_key(key)
        if isinstance(data, (bytes, bytearray)):
            payload: BinaryIO | bytes = bytes(data)
            measured = len(payload)
        else:
            # Prefer caller-provided size (streams) when available
            if size_bytes is None:
                payload_bytes = data.read()
                measured = len(payload_bytes)
                payload = payload_bytes
            else:
                measured = size_bytes
                payload = data

        validate_size(measured, max_bytes=self._max_upload_bytes)
        if skip_mime_validation:
            normalized_type = content_type or "application/octet-stream"
        else:
            normalized_type = validate_content_type(
                content_type,
                allowed=self._allowed_mime_types,
            )

        return self._port.upload(
            cleaned_key,
            payload,
            content_type=normalized_type,
            metadata=metadata,
        )

    def download(self, key: str) -> bytes:
        return self._port.download(validate_object_key(key))

    def delete(self, key: str) -> None:
        self._port.delete(validate_object_key(key))

    def exists(self, key: str) -> bool:
        return self._port.exists(validate_object_key(key))

    def generate_signed_url(
        self,
        key: str,
        *,
        method: str = "GET",
        expires_in: int = 3600,
        content_type: str | None = None,
    ) -> SignedUrl:
        cleaned_key = validate_object_key(key)
        http_method = method.upper()
        if http_method not in {"GET", "PUT"}:
            raise AppError(
                "Signed URL method must be GET or PUT",
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
                details={"method": method},
            )
        normalized_type = None
        if content_type and http_method == "PUT":
            normalized_type = validate_content_type(
                content_type,
                allowed=self._allowed_mime_types,
            )
        return self._port.generate_signed_url(
            cleaned_key,
            method=http_method,
            expires_in=expires_in,
            content_type=normalized_type,
        )

    def health_check(self) -> StorageHealth:
        return self._port.health_check()
