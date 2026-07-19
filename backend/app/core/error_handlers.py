"""Global FastAPI exception handlers → ``{ data, meta, errors }``."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError, ErrorCode
from app.core.middleware import REQUEST_ID_HEADER, get_request_id
from app.core.responses import ErrorItem, error_envelope
from app.observability import get_logger

_logger = get_logger(__name__)


def _request_id_from(request: Request) -> str | None:
    return get_request_id(request) or request.headers.get(REQUEST_ID_HEADER)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach typed exception handlers that always return the API envelope."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        _logger.warning(
            "application error",
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "http_path": request.url.path,
            },
        )
        body = error_envelope(
            code=exc.error_code,
            message=exc.message,
            details=exc.details,
            request_id=_request_id_from(request),
        )
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        items = [
            ErrorItem(
                code=ErrorCode.VALIDATION_ERROR,
                message="Request validation failed",
                details=error,
            )
            for error in exc.errors()
        ]
        body = error_envelope(
            code=ErrorCode.VALIDATION_ERROR,
            message="Request validation failed",
            request_id=_request_id_from(request),
            errors=items,
        )
        return JSONResponse(status_code=422, content=body)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        if exc.status_code == 404:
            code = ErrorCode.NOT_FOUND
        else:
            code = ErrorCode.INTERNAL_ERROR
        if exc.status_code == 403:
            code = ErrorCode.PERMISSION_DENIED
        elif exc.status_code == 503:
            code = ErrorCode.SERVICE_UNAVAILABLE
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        body = error_envelope(
            code=code,
            message=detail,
            request_id=_request_id_from(request),
        )
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        _logger.exception(
            "unhandled exception",
            extra={
                "http_path": request.url.path,
                "exc_type": type(exc).__name__,
            },
        )
        body = error_envelope(
            code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred",
            details={"type": type(exc).__name__},
            request_id=_request_id_from(request),
        )
        return JSONResponse(status_code=500, content=body)
