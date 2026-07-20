"""Unified entity search API route (Phase 3)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.core.dependencies import DbSessionDep, RequestIdDep
from app.core.responses import success_envelope
from app.knowledge.search import UnifiedSearchService

router = APIRouter(
    tags=["Search"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/search",
    summary="Unified search across motors, documents, and drawing numbers",
)
def search(
    session: DbSessionDep,
    request_id: RequestIdDep,
    q: Annotated[str, Query(min_length=1)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> dict:
    data = UnifiedSearchService(session).search(q, limit=limit)
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)
