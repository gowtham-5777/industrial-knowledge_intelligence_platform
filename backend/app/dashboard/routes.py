"""Fleet dashboard API routes (Phase 3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.core.dependencies import DbSessionDep, RequestIdDep
from app.core.responses import success_envelope
from app.dashboard.service import DashboardService

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/kpis", summary="Fleet-level KPI summary for the dashboard")
def get_kpis(session: DbSessionDep, request_id: RequestIdDep) -> dict:
    data = DashboardService(session).get_kpis()
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)
