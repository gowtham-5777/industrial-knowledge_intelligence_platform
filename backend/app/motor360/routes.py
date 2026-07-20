"""Motor 360 single-asset intelligence bundle API (Phase 3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.core.dependencies import DbSessionDep, RequestIdDep
from app.core.responses import success_envelope
from app.motor360.service import Motor360Service

router = APIRouter(
    prefix="/motor360",
    tags=["Motor360"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/{motor_id}",
    summary="Full single-motor intelligence bundle (specs, docs, AI summary, "
    "health, recommendations, timeline, related assets, graph)",
)
def get_motor_360(
    motor_id: str,
    session: DbSessionDep,
    request_id: RequestIdDep,
    refresh: bool = False,
) -> dict:
    data = Motor360Service(session).get_bundle(motor_id, refresh=refresh)
    session.commit()
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)
