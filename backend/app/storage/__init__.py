"""Object storage port and adapters (Azure Blob / MinIO / local)."""

from app.storage.factory import get_object_storage, get_storage_service
from app.storage.protocol import ObjectStoragePort
from app.storage.service import StorageService

__all__ = [
    "ObjectStoragePort",
    "StorageService",
    "get_object_storage",
    "get_storage_service",
]
