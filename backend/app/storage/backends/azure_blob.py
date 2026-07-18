"""Azure Blob Storage adapter."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import BinaryIO

from azure.core.exceptions import AzureError, ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    ContentSettings,
    generate_blob_sas,
)

from app.core.exceptions import AppError, ErrorCode, NotFoundError
from app.storage.io_utils import read_bytes
from app.storage.models import SignedUrl, StorageHealth, StoredObject


class AzureBlobObjectStorage:
    """Azure Blob Storage adapter (cloud demo path)."""

    def __init__(
        self,
        *,
        connection_string: str,
        container: str,
    ) -> None:
        if not connection_string.strip():
            raise AppError(
                "AZURE_STORAGE_CONNECTION_STRING is required for azure backend",
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
            )
        self._container = container
        self._service = BlobServiceClient.from_connection_string(connection_string)
        self._account_name = self._service.account_name
        # Credential may be account key from connection string
        self._credential = self._service.credential

    @property
    def backend_name(self) -> str:
        return "azure"

    @property
    def bucket(self) -> str:
        return self._container

    def ensure_bucket(self) -> None:
        container = self._service.get_container_client(self._container)
        try:
            container.get_container_properties()
            return
        except ResourceNotFoundError:
            pass
        try:
            self._service.create_container(self._container)
        except ResourceExistsError:
            return
        except AzureError as exc:
            raise AppError(
                "Failed to ensure Azure container",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                status_code=503,
                details={"container": self._container, "error": str(exc)},
            ) from exc

    def upload(
        self,
        key: str,
        data: BinaryIO | bytes,
        *,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> StoredObject:
        payload = read_bytes(data)
        blob = self._service.get_blob_client(container=self._container, blob=key)
        try:
            result = blob.upload_blob(
                payload,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
                metadata=metadata,
            )
        except AzureError as exc:
            raise AppError(
                "Failed to upload object to Azure Blob",
                error_code=ErrorCode.INGESTION_FAILED,
                status_code=502,
                details={"key": key, "error": str(exc)},
            ) from exc

        etag = getattr(result, "etag", None)
        if isinstance(etag, str):
            etag = etag.strip('"')
        return StoredObject(
            key=key,
            bucket=self._container,
            content_type=content_type,
            size_bytes=len(payload),
            etag=etag,
            metadata=dict(metadata or {}),
            uploaded_at=datetime.now(UTC),
        )

    def download(self, key: str) -> bytes:
        blob = self._service.get_blob_client(container=self._container, blob=key)
        try:
            return blob.download_blob().readall()
        except ResourceNotFoundError as exc:
            raise NotFoundError(
                "Object not found",
                details={"key": key, "bucket": self._container},
            ) from exc
        except AzureError as exc:
            raise AppError(
                "Failed to download object from Azure Blob",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                status_code=503,
                details={"key": key, "error": str(exc)},
            ) from exc

    def delete(self, key: str) -> None:
        blob = self._service.get_blob_client(container=self._container, blob=key)
        try:
            blob.delete_blob()
        except ResourceNotFoundError:
            return
        except AzureError as exc:
            raise AppError(
                "Failed to delete Azure blob",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                status_code=503,
                details={"key": key, "error": str(exc)},
            ) from exc

    def exists(self, key: str) -> bool:
        blob = self._service.get_blob_client(container=self._container, blob=key)
        try:
            blob.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False
        except AzureError as exc:
            raise AppError(
                "Failed to check Azure blob existence",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                status_code=503,
                details={"key": key, "error": str(exc)},
            ) from exc

    def generate_signed_url(
        self,
        key: str,
        *,
        method: str = "GET",
        expires_in: int = 3600,
        content_type: str | None = None,
    ) -> SignedUrl:
        http_method = method.upper()
        account_key = getattr(self._credential, "account_key", None)
        if not self._account_name or not account_key:
            raise AppError(
                "Azure SAS requires account name and key in connection string",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                status_code=503,
            )

        permissions = (
            BlobSasPermissions(read=True)
            if http_method == "GET"
            else BlobSasPermissions(write=True, create=True)
        )
        expiry = datetime.now(UTC) + timedelta(seconds=expires_in)
        try:
            sas = generate_blob_sas(
                account_name=self._account_name,
                container_name=self._container,
                blob_name=key,
                account_key=account_key,
                permission=permissions,
                expiry=expiry,
                content_type=content_type if http_method == "PUT" else None,
            )
        except (AzureError, ValueError, TypeError) as exc:
            raise AppError(
                "Failed to generate Azure SAS URL",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                status_code=503,
                details={"key": key, "error": str(exc)},
            ) from exc

        blob = self._service.get_blob_client(container=self._container, blob=key)
        url = f"{blob.url}?{sas}"
        headers: dict[str, str] = {}
        if http_method == "PUT" and content_type:
            headers["Content-Type"] = content_type
        return SignedUrl(
            url=url,
            method=http_method,
            expires_in=expires_in,
            key=key,
            headers=headers,
        )

    def health_check(self) -> StorageHealth:
        try:
            self.ensure_bucket()
            return StorageHealth(
                backend=self.backend_name,
                bucket=self._container,
                ok=True,
            )
        except Exception as exc:  # noqa: BLE001
            return StorageHealth(
                backend=self.backend_name,
                bucket=self._container,
                ok=False,
                detail=str(exc),
            )
