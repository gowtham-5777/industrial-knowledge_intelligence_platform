"""Build object storage backends and services from settings."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ErrorCode
from app.storage.backends.azure_blob import AzureBlobObjectStorage
from app.storage.backends.local import LocalObjectStorage
from app.storage.backends.s3_compatible import S3CompatibleObjectStorage
from app.storage.protocol import ObjectStoragePort
from app.storage.service import StorageService
from app.storage.validation import DEFAULT_ALLOWED_MIME_TYPES


def build_object_storage(settings: Settings) -> ObjectStoragePort:
    backend = settings.storage_backend.lower().strip()

    if backend == "local":
        return LocalObjectStorage(
            root=settings.storage_local_root,
            bucket=settings.storage_bucket,
        )

    if backend in {"minio", "s3"}:
        return S3CompatibleObjectStorage(
            endpoint=settings.storage_endpoint,
            access_key=settings.storage_access_key,
            secret_key=settings.storage_secret_key,
            bucket=settings.storage_bucket,
            use_ssl=settings.storage_use_ssl,
            region=settings.storage_region,
            backend_name=backend,
        )

    if backend == "azure":
        return AzureBlobObjectStorage(
            connection_string=settings.azure_storage_connection_string,
            container=settings.azure_storage_container or settings.storage_bucket,
        )

    raise AppError(
        f"Unsupported STORAGE_BACKEND: {settings.storage_backend}",
        error_code=ErrorCode.VALIDATION_ERROR,
        status_code=400,
        details={"allowed": ["local", "minio", "s3", "azure"]},
    )


def build_storage_service(settings: Settings) -> StorageService:
    allowed = settings.storage_allowed_mime_types_set or DEFAULT_ALLOWED_MIME_TYPES
    return StorageService(
        build_object_storage(settings),
        max_upload_bytes=settings.storage_max_upload_bytes,
        allowed_mime_types=allowed,
    )


@lru_cache
def get_object_storage() -> ObjectStoragePort:
    return build_object_storage(get_settings())


@lru_cache
def get_storage_service() -> StorageService:
    return build_storage_service(get_settings())


def clear_storage_cache() -> None:
    """Clear cached storage singletons (tests / settings reload)."""
    get_object_storage.cache_clear()
    get_storage_service.cache_clear()
