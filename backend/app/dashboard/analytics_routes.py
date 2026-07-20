"""Analytics API routes (Milestone 4.6)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.core.dependencies import DbSessionDep, RequestIdDep
from app.core.responses import success_envelope
from app.dashboard.analytics import AnalyticsService

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
    dependencies=[Depends(get_current_user)],
)


def get_analytics(session: DbSessionDep) -> AnalyticsService:
    return AnalyticsService(session)


AnalyticsDep = Annotated[AnalyticsService, Depends(get_analytics)]


@router.get("", summary="Fleet coverage + indexing velocity")
def analytics_snapshot(service: AnalyticsDep, request_id: RequestIdDep) -> dict:
    data = service.snapshot()
    return success_envelope(data.model_dump(), request_id=request_id)
