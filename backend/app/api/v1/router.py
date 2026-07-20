"""Versioned API router for ``/api/v1``."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.agents.compliance_routes import router as compliance_router
from app.agents.routes import router as copilot_router
from app.auth.dependencies import CurrentUserDep, get_current_user
from app.auth.routes import router as auth_router
from app.core.dependencies import RequestIdDep, SettingsDep
from app.core.responses import success_envelope
from app.dashboard.analytics_routes import router as analytics_router
from app.dashboard.routes import router as dashboard_router
from app.documents.routes import router as documents_router
from app.drawings.routes import router as drawings_router
from app.extraction.routes import router as extraction_router
from app.gdrive.routes import router as sync_router
from app.graph.routes import router as graph_router
from app.indexing.routes import router as indexing_router
from app.knowledge.routes import router as search_router
from app.motor360.routes import router as motor360_router
from app.motors.routes import router as motors_router
from app.reasoning.routes import router as reasoning_router

router = APIRouter()

# Public auth endpoints (login / refresh) + protected /me
router.include_router(auth_router)
# Corpus sync (local/Drive-shaped) — authenticated
router.include_router(sync_router)
# Document catalog + manual upload — authenticated
router.include_router(documents_router)
# Parse / OCR pipeline (Milestone 2.1) — authenticated
router.include_router(indexing_router)
# Metadata / entity extraction (Milestone 2.2) — authenticated
router.include_router(extraction_router)
# Motor registry + explorer (Phase 3.1–3.2) — authenticated
router.include_router(motors_router)
# Single-motor intelligence bundle (Phase 3) — authenticated
router.include_router(motor360_router)
# Drawing number cross-reference explorer (Phase 3) — authenticated
router.include_router(drawings_router)
# Unified entity search across motors/documents/drawings (Phase 3) — authenticated
router.include_router(search_router)
# Fleet dashboard KPIs (Phase 3) — authenticated
router.include_router(dashboard_router)
# React Flow subgraph projection (Phase 3) — authenticated
router.include_router(graph_router)
# Industrial Copilot + query router (Phase 4) — authenticated
router.include_router(copilot_router)
# Maintenance intelligence + RCA (Phase 4) — authenticated
router.include_router(reasoning_router)
# Compliance Intelligence Center (Phase 4) — authenticated
router.include_router(compliance_router)
# Fleet analytics (Phase 4) — authenticated
router.include_router(analytics_router)


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
