"""Health and readiness endpoints (unversioned operational probes)."""

from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app import __version__
from app.core.dependencies import SettingsDep
from app.core.exceptions import ErrorCode
from app.core.middleware import get_request_id
from app.core.responses import error_envelope, success_envelope
from app.db.session import check_database_connection

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Liveness probe",
    description="Returns OK when the process is running and can serve HTTP.",
)
def health(request: Request, settings: SettingsDep) -> dict:
    return success_envelope(
        {
            "status": "ok",
            "service": settings.app_name,
            "version": __version__,
            "environment": settings.app_env,
        },
        request_id=get_request_id(request),
    )


@router.get(
    "/ready",
    summary="Readiness probe",
    response_model=None,
    description=(
        "Returns ready when configuration is loaded. "
        "In production, PostgreSQL connectivity is required."
    ),
)
def ready(request: Request, settings: SettingsDep) -> JSONResponse | dict:
    request_id = get_request_id(request)
    db_ok = check_database_connection()
    checks = {
        "settings": "ok",
        "api_prefix": settings.api_prefix,
        "database": "ok" if db_ok else "unavailable",
    }

    insecure_jwt = settings.jwt_secret.startswith("change-me")
    insecure_db = "change-me" in settings.database_url
    production_blocked = settings.app_env == "production" and (
        insecure_jwt or insecure_db or not db_ok
    )
    if production_blocked:
        body = error_envelope(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Service is not ready",
            details={"checks": checks},
            request_id=request_id,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=body,
        )

    return success_envelope(
        {"status": "ready", "checks": checks},
        request_id=request_id,
    )
