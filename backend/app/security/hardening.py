"""Security helpers — upload sanitization, secrets hygiene, prompt guards."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from app.core.config import Settings
from app.core.exceptions import AppError, ErrorCode
from app.storage.validation import (
    DEFAULT_ALLOWED_MIME_TYPES,
    normalize_content_type,
    validate_content_type,
    validate_size,
)

# Dangerous filename characters / double extensions often used in polyglots
_UNSAFE_FILENAME = re.compile(r"[<>:\"|?*\x00-\x1f]|[/\\]{2,}")
_EXECUTABLE_EXT = frozenset(
    {
        ".exe",
        ".bat",
        ".cmd",
        ".com",
        ".msi",
        ".scr",
        ".js",
        ".vbs",
        ".ps1",
        ".sh",
        ".dll",
    }
)


def sanitize_upload_filename(filename: str) -> str:
    name = (filename or "upload.bin").strip().replace("\\", "/")
    name = PurePosixPath(name).name  # drop any path segments
    name = _UNSAFE_FILENAME.sub("_", name)
    name = name.lstrip(".")
    if not name:
        name = "upload.bin"
    if len(name) > 200:
        stem = PurePosixPath(name).stem[:180]
        suffix = PurePosixPath(name).suffix[:20]
        name = f"{stem}{suffix}"
    return name


def assert_safe_upload(
    *,
    filename: str,
    content: bytes,
    content_type: str | None,
    max_bytes: int,
    allowed_mimes: frozenset[str] | None = None,
) -> tuple[str, str]:
    """MIME + size + filename sanitization for uploads (Milestone 5.6.2)."""
    safe_name = sanitize_upload_filename(filename)
    suffix = PurePosixPath(safe_name).suffix.lower()
    if suffix in _EXECUTABLE_EXT:
        raise AppError(
            "Executable uploads are not allowed",
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details={"filename": safe_name, "extension": suffix},
        )
    # Reject empty / suspiciously tiny payloads with executable magic
    if content[:2] == b"MZ":
        raise AppError(
            "Upload content looks like a Windows executable",
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
        )
    validate_size(len(content), max_bytes=max_bytes)
    allowed = allowed_mimes or DEFAULT_ALLOWED_MIME_TYPES
    mime = validate_content_type(content_type, allowed=allowed)
    # Prefer extension-aligned MIME when client sends octet-stream
    if mime == "application/octet-stream" and suffix == ".pdf":
        mime = "application/pdf"
    return safe_name, normalize_content_type(mime)


def secrets_hygiene_report(settings: Settings) -> dict:
    """Non-destructive check that placeholder secrets are not used in prod."""
    issues: list[str] = []
    warnings: list[str] = []
    if settings.jwt_secret.startswith("change-me"):
        issues.append("JWT_SECRET uses placeholder")
    if "change-me" in settings.database_url:
        issues.append("DATABASE_URL uses placeholder")
    if settings.neo4j_password.startswith("change-me"):
        warnings.append("NEO4J_PASSWORD uses placeholder")
    if settings.app_env == "production" and (
        "*" in settings.cors_origins or not settings.cors_origin_list
    ):
        issues.append("CORS_ORIGINS must be locked to explicit frontend origin(s)")
    if settings.app_env == "production" and len(settings.cors_origin_list) == 0:
        issues.append("CORS_ORIGINS is empty")
    return {
        "environment": settings.app_env,
        "ok": len(issues) == 0 or settings.app_env != "production",
        "issues": issues,
        "warnings": warnings,
        "cors_origins": settings.cors_origin_list,
    }
