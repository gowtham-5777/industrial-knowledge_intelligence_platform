"""S3-compatible object storage (MinIO / AWS S3)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.exceptions import AppError, ErrorCode, NotFoundError
from app.storage.io_utils import read_bytes
from app.storage.models import SignedUrl, StorageHealth, StoredObject


class S3CompatibleObjectStorage:
    """MinIO / S3 adapter using boto3."""

    def __init__(
        self,
        *,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        use_ssl: bool = False,
        region: str = "us-east-1",
        backend_name: str = "minio",
    ) -> None:
        endpoint_url = endpoint
        if endpoint and not endpoint.startswith("http"):
            scheme = "https" if use_ssl else "http"
            endpoint_url = f"{scheme}://{endpoint}"

        self._bucket = bucket
        self._backend_name = backend_name
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url or None,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    @property
    def backend_name(self) -> str:
        return self._backend_name

    @property
    def bucket(self) -> str:
        return self._bucket

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            try:
                self._client.create_bucket(Bucket=self._bucket)
            except ClientError as exc:
                raise AppError(
                    "Failed to create storage bucket",
                    error_code=ErrorCode.SERVICE_UNAVAILABLE,
                    status_code=503,
                    details={"bucket": self._bucket, "error": str(exc)},
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
        extra: dict[str, Any] = {"ContentType": content_type}
        if metadata:
            extra["Metadata"] = metadata
        try:
            response = self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=payload,
                **extra,
            )
        except ClientError as exc:
            raise AppError(
                "Failed to upload object",
                error_code=ErrorCode.INGESTION_FAILED,
                status_code=502,
                details={"key": key, "error": str(exc)},
            ) from exc

        etag = response.get("ETag", "").strip('"') or None
        return StoredObject(
            key=key,
            bucket=self._bucket,
            content_type=content_type,
            size_bytes=len(payload),
            etag=etag,
            metadata=dict(metadata or {}),
            uploaded_at=datetime.now(UTC),
        )

    def download(self, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in {"404", "NoSuchKey", "NotFound"}:
                raise NotFoundError(
                    "Object not found",
                    details={"key": key, "bucket": self._bucket},
                ) from exc
            raise AppError(
                "Failed to download object",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                status_code=503,
                details={"key": key, "error": str(exc)},
            ) from exc
        return response["Body"].read()

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            raise AppError(
                "Failed to delete object",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                status_code=503,
                details={"key": key, "error": str(exc)},
            ) from exc

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in {"404", "NoSuchKey", "NotFound", "404 Not Found"}:
                return False
            # Some S3-compatible servers return 404 HTTP status without Code
            http_status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if http_status == 404:
                return False
            raise AppError(
                "Failed to check object existence",
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
        client_method = "get_object" if http_method == "GET" else "put_object"
        params: dict[str, Any] = {"Bucket": self._bucket, "Key": key}
        headers: dict[str, str] = {}
        if http_method == "PUT" and content_type:
            params["ContentType"] = content_type
            headers["Content-Type"] = content_type
        try:
            url = self._client.generate_presigned_url(
                ClientMethod=client_method,
                Params=params,
                ExpiresIn=expires_in,
                HttpMethod=http_method,
            )
        except ClientError as exc:
            raise AppError(
                "Failed to generate signed URL",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                status_code=503,
                details={"key": key, "error": str(exc)},
            ) from exc
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
                bucket=self._bucket,
                ok=True,
            )
        except Exception as exc:  # noqa: BLE001 — health must never raise
            return StorageHealth(
                backend=self.backend_name,
                bucket=self._bucket,
                ok=False,
                detail=str(exc),
            )
