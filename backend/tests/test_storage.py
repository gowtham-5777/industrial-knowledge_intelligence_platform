"""Object storage unit tests for Milestone 1.5."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.core.config import Settings, clear_settings_cache
from app.core.exceptions import AppError, ErrorCode, NotFoundError
from app.storage.factory import build_storage_service, clear_storage_cache
from app.storage.service import StorageService
from app.storage.validation import (
    validate_content_type,
    validate_object_key,
    validate_size,
)


@pytest.fixture()
def storage(tmp_path: Path) -> StorageService:
    settings = Settings(
        storage_backend="local",
        storage_local_root=str(tmp_path / "blobs"),
        storage_bucket="test-bucket",
        storage_max_upload_bytes=1024,
        app_env="test",
    )
    return build_storage_service(settings)


def test_upload_download_roundtrip(storage: StorageService) -> None:
    payload = b"%PDF-1.4 demo content"
    stored = storage.upload(
        "documents/demo.pdf",
        payload,
        content_type="application/pdf",
        metadata={"source": "unit-test"},
    )
    assert stored.key == "documents/demo.pdf"
    assert stored.bucket == "test-bucket"
    assert stored.size_bytes == len(payload)
    assert stored.content_type == "application/pdf"
    assert storage.exists("documents/demo.pdf")
    assert storage.download("documents/demo.pdf") == payload


def test_signed_url_get(storage: StorageService) -> None:
    storage.upload("a/b.txt", b"hello", content_type="text/plain")
    signed = storage.generate_signed_url("a/b.txt", method="GET", expires_in=120)
    assert signed.method == "GET"
    assert signed.expires_in == 120
    assert signed.key == "a/b.txt"
    assert signed.url.startswith("local://test-bucket/a/b.txt?")


def test_reject_disallowed_mime(storage: StorageService) -> None:
    with pytest.raises(AppError) as exc_info:
        storage.upload(
            "evil.exe",
            b"MZ",
            content_type="application/x-msdownload",
        )
    assert exc_info.value.error_code == ErrorCode.VALIDATION_ERROR


def test_reject_oversized_upload(storage: StorageService) -> None:
    with pytest.raises(AppError) as exc_info:
        storage.upload(
            "big.pdf",
            b"x" * 2048,
            content_type="application/pdf",
        )
    assert exc_info.value.error_code == ErrorCode.VALIDATION_ERROR


def test_path_traversal_rejected(storage: StorageService) -> None:
    with pytest.raises(AppError):
        storage.upload("../escape.pdf", b"x", content_type="application/pdf")


def test_download_missing_raises(storage: StorageService) -> None:
    with pytest.raises(NotFoundError):
        storage.download("missing/file.pdf")


def test_delete_idempotent(storage: StorageService) -> None:
    storage.upload("gone.pdf", b"%PDF", content_type="application/pdf")
    storage.delete("gone.pdf")
    assert not storage.exists("gone.pdf")
    storage.delete("gone.pdf")  # no raise


def test_health_check_ok(storage: StorageService) -> None:
    health = storage.health_check()
    assert health.ok is True
    assert health.backend == "local"
    assert health.bucket == "test-bucket"


def test_factory_unsupported_backend() -> None:
    settings = Settings.model_construct(
        storage_backend="ftp",
        storage_bucket="x",
        storage_endpoint="localhost",
        storage_access_key="a",
        storage_secret_key="b",
        storage_use_ssl=False,
        storage_region="us-east-1",
        storage_local_root=".data/storage",
        azure_storage_connection_string="",
        azure_storage_container="x",
        storage_max_upload_bytes=1024,
        storage_allowed_mime_types="",
    )
    with pytest.raises(AppError) as exc_info:
        build_storage_service(settings)
    assert exc_info.value.error_code == ErrorCode.VALIDATION_ERROR


def test_validation_helpers() -> None:
    assert validate_content_type("application/pdf; charset=binary") == "application/pdf"
    assert validate_size(10, max_bytes=100) == 10
    assert validate_object_key("/docs/a.pdf") == "docs/a.pdf"
    with pytest.raises(AppError):
        validate_size(200, max_bytes=100)
    with pytest.raises(AppError):
        validate_object_key("")


def test_settings_wire_storage_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("STORAGE_BUCKET", "env-bucket")
    monkeypatch.setenv("STORAGE_MAX_UPLOAD_BYTES", "2048")
    monkeypatch.setenv("STORAGE_ALLOWED_MIME_TYPES", "application/pdf, text/plain")
    clear_settings_cache()
    clear_storage_cache()
    from app.core.config import get_settings

    settings = get_settings()
    assert settings.storage_backend == "local"
    assert settings.storage_bucket == "env-bucket"
    assert settings.storage_max_upload_bytes == 2048
    assert settings.storage_allowed_mime_types_set == frozenset(
        {"application/pdf", "text/plain"}
    )
    clear_settings_cache()
    clear_storage_cache()
