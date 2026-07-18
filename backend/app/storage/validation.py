"""MIME type and upload size validation for object storage."""

from __future__ import annotations

from app.core.exceptions import AppError, ErrorCode

# Architecture §11 / §7 — PDF, DOCX, XLSX, images (+ light text formats for regs)
DEFAULT_ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/tiff",
        "text/plain",
        "text/csv",
        "text/html",
        "application/xml",
        "text/xml",
        "application/json",
        "application/octet-stream",
    }
)

# 100 MiB default cap — selective Wave downloads stay under this for most docs
DEFAULT_MAX_UPLOAD_BYTES = 100 * 1024 * 1024


def normalize_content_type(content_type: str | None) -> str:
    if not content_type or not content_type.strip():
        return "application/octet-stream"
    # Strip parameters such as charset=
    return content_type.split(";", 1)[0].strip().lower()


def validate_content_type(
    content_type: str | None,
    *,
    allowed: frozenset[str] | set[str] | None = None,
) -> str:
    normalized = normalize_content_type(content_type)
    allowed_set = (
        frozenset(allowed) if allowed is not None else DEFAULT_ALLOWED_MIME_TYPES
    )
    if normalized not in allowed_set:
        raise AppError(
            "Content type is not allowed for upload",
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details={
                "content_type": normalized,
                "allowed": sorted(allowed_set),
            },
        )
    return normalized


def validate_size(
    size_bytes: int,
    *,
    max_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
) -> int:
    if size_bytes < 0:
        raise AppError(
            "Object size cannot be negative",
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details={"size_bytes": size_bytes},
        )
    if size_bytes > max_bytes:
        raise AppError(
            "Object exceeds maximum allowed size",
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details={"size_bytes": size_bytes, "max_bytes": max_bytes},
        )
    return size_bytes


def validate_object_key(key: str) -> str:
    cleaned = key.strip().lstrip("/")
    if not cleaned:
        raise AppError(
            "Object key is required",
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
        )
    if ".." in cleaned.split("/"):
        raise AppError(
            "Object key must not contain path traversal segments",
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details={"key": key},
        )
    if len(cleaned) > 1024:
        raise AppError(
            "Object key is too long",
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details={"max_length": 1024},
        )
    return cleaned
