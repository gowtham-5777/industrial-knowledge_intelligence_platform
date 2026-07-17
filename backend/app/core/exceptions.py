"""Typed application errors with machine-readable error codes."""

from __future__ import annotations

from typing import Any


class ErrorCode:
    """Stable error_code values (Architecture §13)."""

    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    ASSET_NOT_FOUND = "ASSET_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    INGESTION_FAILED = "INGESTION_FAILED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class AppError(Exception):
    """Base application error mapped to the standard response envelope."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = ErrorCode.INTERNAL_ERROR,
        status_code: int = 400,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    def __init__(
        self,
        message: str = "Resource not found",
        *,
        error_code: str = ErrorCode.NOT_FOUND,
        details: Any | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            status_code=404,
            details=details,
        )


class PermissionDeniedError(AppError):
    def __init__(
        self,
        message: str = "Permission denied",
        *,
        details: Any | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=ErrorCode.PERMISSION_DENIED,
            status_code=403,
            details=details,
        )
