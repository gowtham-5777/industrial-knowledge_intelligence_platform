"""Versioned API router for ``/api/v1``."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import RequestIdDep, SettingsDep
from app.core.responses import success_envelope

router = APIRouter()


@router.get(
    "/ping",
    summary="API version ping",
    tags=["System"],
    description="Confirms the versioned API surface is mounted and responding.",
)
def ping(
    settings: SettingsDep,
    request_id: RequestIdDep,
) -> dict:
    return success_envelope(
        {
            "message": "pong",
            "api": settings.api_prefix,
            "environment": settings.app_env,
        },
        request_id=request_id,
    )
