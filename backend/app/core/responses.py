"""Standard API response envelope: ``{ data, meta, errors }``."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorItem(BaseModel):
    """Machine-readable error entry inside the response envelope."""

    code: str = Field(..., description="Stable machine-readable error_code")
    message: str = Field(..., description="Human-readable error summary")
    details: Any | None = Field(default=None, description="Optional structured detail")


class ResponseMeta(BaseModel):
    """Response metadata attached to every envelope."""

    request_id: str | None = None
    timing_ms: float | None = None


class ApiEnvelope(BaseModel, Generic[T]):
    """Canonical response shape required by Architecture §13."""

    data: T | None = None
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    errors: list[ErrorItem] = Field(default_factory=list)


def success_envelope(
    data: Any,
    *,
    request_id: str | None = None,
    timing_ms: float | None = None,
) -> dict[str, Any]:
    """Build a success envelope dict suitable for JSONResponse / route returns."""
    return ApiEnvelope[Any](
        data=data,
        meta=ResponseMeta(request_id=request_id, timing_ms=timing_ms),
        errors=[],
    ).model_dump()


def error_envelope(
    *,
    code: str,
    message: str,
    details: Any | None = None,
    request_id: str | None = None,
    errors: list[ErrorItem] | None = None,
) -> dict[str, Any]:
    """Build an error envelope dict."""
    items = errors or [ErrorItem(code=code, message=message, details=details)]
    return ApiEnvelope[Any](
        data=None,
        meta=ResponseMeta(request_id=request_id),
        errors=items,
    ).model_dump()
