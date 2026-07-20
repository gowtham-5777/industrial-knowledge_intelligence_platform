"""Drawing number explorer API routes (Phase 3)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.core.dependencies import DbSessionDep, RequestIdDep
from app.core.responses import success_envelope
from app.drawings.explorer import DrawingExplorerService

router = APIRouter(
    prefix="/drawings",
    tags=["Drawings"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", summary="List / search drawing numbers")
def list_drawings(
    session: DbSessionDep,
    request_id: RequestIdDep,
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    data = DrawingExplorerService(session).list_drawings(q=q, limit=limit, offset=offset)
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)


@router.get(
    "/{drawing_number}",
    summary="Drawing cross-reference bundle (documents + linked motors/assets)",
)
def get_drawing(
    drawing_number: str,
    session: DbSessionDep,
    request_id: RequestIdDep,
) -> dict:
    data = DrawingExplorerService(session).get_drawing(drawing_number)
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)
