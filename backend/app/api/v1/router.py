"""Versioned API router for ``/api/v1``."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import CurrentUserDep, get_current_user
from app.auth.routes import router as auth_router
from app.core.dependencies import RequestIdDep, SettingsDep
from app.core.responses import success_envelope
from app.gdrive.routes import router as sync_router

router = APIRouter()

# Public auth endpoints (login / refresh) + protected /me
router.include_router(auth_router)
# Corpus sync (local/Drive-shaped) — authenticated
router.include_router(sync_router)


# Public smoke probe (unauthenticated)
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


# Protected surface — future domain routers mount here with auth required.
protected_router = APIRouter(
    dependencies=[Depends(get_current_user)],
    tags=["Protected"],
)


@protected_router.get(
    "/session/check",
    summary="Protected session check",
    description="Requires Bearer access token; used to verify auth middleware.",
)
def session_check(user: CurrentUserDep, request_id: RequestIdDep) -> dict:
    return success_envelope(
        {
            "authenticated": True,
            "user_id": user.id,
            "email": user.email,
        },
        request_id=request_id,
    )


router.include_router(protected_router)
