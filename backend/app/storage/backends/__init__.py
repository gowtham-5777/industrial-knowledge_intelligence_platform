"""Object storage backend adapters."""

from app.storage.backends.azure_blob import AzureBlobObjectStorage
from app.storage.backends.local import LocalObjectStorage
from app.storage.backends.s3_compatible import S3CompatibleObjectStorage

__all__ = [
    "AzureBlobObjectStorage",
    "LocalObjectStorage",
    "S3CompatibleObjectStorage",
]
