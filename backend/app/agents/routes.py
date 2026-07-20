"""Copilot + query router API routes (Milestones 4.1–4.2)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.agents.copilot import CopilotService
from app.agents.schemas import (
    ChatRequest,
    FeedbackRequest,
    RouteRequest,
    SessionCreateRequest,
)
from app.auth.dependencies import CurrentUserDep, get_current_user
from app.core.dependencies import DbSessionDep, RequestIdDep
from app.core.responses import success_envelope

router = APIRouter(
    prefix="/copilot",
    tags=["Copilot"],
    dependencies=[Depends(get_current_user)],
)


def get_copilot_service(session: DbSessionDep) -> CopilotService:
    return CopilotService(session)


CopilotDep = Annotated[CopilotService, Depends(get_copilot_service)]


@router.post("/sessions", summary="Create a Copilot session")
def create_session(
    body: SessionCreateRequest,
    service: CopilotDep,
    user: CurrentUserDep,
    request_id: RequestIdDep,
) -> dict:
    data = service.create_session(
        motor_id=body.motor_id,
        user_id=user.id,
        title=body.title,
    )
    return success_envelope(data.model_dump(), request_id=request_id)


@router.get("/sessions/{session_id}", summary="Get Copilot session + messages")
def get_session(
    session_id: str,
    service: CopilotDep,
    request_id: RequestIdDep,
) -> dict:
    data = service.get_session(session_id)
    return success_envelope(data.model_dump(), request_id=request_id)


@router.post("/route", summary="Classify query intent + link entities")
def route_query(
    body: RouteRequest,
    service: CopilotDep,
    request_id: RequestIdDep,
) -> dict:
    data = service.route_query(body)
    return success_envelope(data.model_dump(), request_id=request_id)


@router.post("/chat", summary="Industrial Copilot chat (JSON or SSE)")
def chat(
    body: ChatRequest,
    service: CopilotDep,
    user: CurrentUserDep,
    request_id: RequestIdDep,
):
    if body.stream:
        generator = service.chat_sse(body, user_id=user.id)
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Request-Id": request_id or "",
                "X-Accel-Buffering": "no",
            },
        )
    data = service.chat(body, user_id=user.id)
    return success_envelope(data.model_dump(), request_id=request_id)


@router.post("/feedback", summary="Store Copilot answer feedback")
def feedback(
    body: FeedbackRequest,
    service: CopilotDep,
    user: CurrentUserDep,
    request_id: RequestIdDep,
) -> dict:
    data = service.submit_feedback(body, user_id=user.id)
    return success_envelope(data.model_dump(), request_id=request_id)
