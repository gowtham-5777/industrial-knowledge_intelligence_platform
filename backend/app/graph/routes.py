"""Graph projection API routes (Phase 3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.core.dependencies import DbSessionDep, RequestIdDep
from app.core.responses import success_envelope
from app.graph.subgraph import GraphSubgraphService

router = APIRouter(
    prefix="/graph",
    tags=["Graph"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/motors/{motor_id}/subgraph",
    summary="React Flow node/edge subgraph centered on a motor",
)
def motor_subgraph(
    motor_id: str, session: DbSessionDep, request_id: RequestIdDep
) -> dict:
    data = GraphSubgraphService(session).build(motor_id)
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)
