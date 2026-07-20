"""Industrial Copilot session / chat / feedback service (Milestone 4.2)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.audit.service import AuditService
from app.agents.graph import CopilotGraph
from app.agents.router import QueryRouter
from app.agents.schemas import (
    ChatRequest,
    ChatResponse,
    FeedbackOut,
    FeedbackRequest,
    MessageOut,
    RouteRequest,
    RouteResponse,
    SessionOut,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.db.models.ai import CopilotMessage, CopilotSession, FeedbackRating
from app.observability import get_logger

_logger = get_logger(__name__)


class CopilotService:
    """Orchestrates sessions, routing, LangGraph answers, and feedback."""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.router = QueryRouter(session, self.settings)
        self.graph = CopilotGraph(session, self.settings)

    def create_session(
        self,
        *,
        motor_id: str | None = None,
        user_id: str | None = None,
        title: str | None = None,
    ) -> SessionOut:
        row = CopilotSession(
            motor_id=motor_id,
            user_id=user_id,
            title=title or ("Motor Copilot" if motor_id else "Industrial Copilot"),
            status="active",
        )
        self.session.add(row)
        self._checkpoint()
        return self._session_out(row)

    def get_session(self, session_id: str) -> SessionOut:
        row = self._get_session(session_id)
        return self._session_out(row)

    def route_query(self, body: RouteRequest) -> RouteResponse:
        result = self.router.route(body.query, motor_id=body.motor_id)
        return RouteResponse(**result.model_dump())

    def chat(self, body: ChatRequest, *, user_id: str | None = None) -> ChatResponse:
        sess = self._resolve_session(body, user_id=user_id)
        session_id = sess.id
        motor_id = body.motor_id or sess.motor_id

        user_msg = CopilotMessage(
            session_id=session_id,
            role="user",
            content=body.message,
        )
        self.session.add(user_msg)
        # Commit before tool orchestration — hybrid retrieval / summary may
        # rollback on missing OpenAI/Qdrant and would otherwise erase the turn.
        self._checkpoint()

        AuditService(self.session).write(
            "copilot_query",
            actor_user_id=user_id,
            resource_type="copilot_session",
            resource_id=session_id,
            details={"message_len": len(body.message), "motor_id": motor_id},
        )
        self._checkpoint()

        state = self.graph.run(body.message, motor_id=motor_id)
        answer = state.get("answer") or "Not available in indexed knowledge."
        assistant = CopilotMessage(
            session_id=session_id,
            role="assistant",
            content=answer,
            intent=(state.get("route") or {}).get("intent"),
            confidence=state.get("confidence"),
            citations=state.get("citations"),
            reasoning=state.get("reasoning"),
            retrieval_trace_id=state.get("retrieval_trace_id"),
            tool_calls=[
                {"tool": k, "ok": (v or {}).get("ok")}
                for k, v in (state.get("tool_results") or {}).items()
                if isinstance(v, dict)
            ],
            extra_metadata={
                "verified": state.get("verified"),
                "numeric_checks": state.get("numeric_checks"),
                "degraded": state.get("degraded"),
                "route": state.get("route"),
            },
        )
        self.session.add(assistant)
        self._checkpoint()

        AuditService(self.session).write(
            "copilot_response",
            actor_user_id=user_id,
            resource_type="copilot_message",
            resource_id=assistant.id,
            details={
                "session_id": session_id,
                "verified": bool(state.get("verified")),
                "citation_count": len(assistant.citations or []),
            },
        )
        self._checkpoint()

        return ChatResponse(
            session_id=session_id,
            message_id=assistant.id,
            answer=answer,
            intent=assistant.intent,
            confidence=assistant.confidence,
            citations=assistant.citations or [],
            reasoning=assistant.reasoning,
            verified=bool(state.get("verified")),
            degraded=bool(state.get("degraded")),
            route=state.get("route"),
        )

    def chat_sse(
        self,
        body: ChatRequest,
        *,
        user_id: str | None = None,
    ) -> Iterator[str]:
        """Yield SSE events for progressive Copilot UX."""
        yield _sse("status", {"stage": "routing"})
        sess = self._resolve_session(body, user_id=user_id)
        session_id = sess.id
        motor_id = body.motor_id or sess.motor_id
        route = self.router.route(body.message, motor_id=motor_id)
        yield _sse("route", route.model_dump())

        user_msg = CopilotMessage(
            session_id=session_id,
            role="user",
            content=body.message,
        )
        self.session.add(user_msg)
        self._checkpoint()

        yield _sse("status", {"stage": "tools", "tools": route.tools})
        state = self.graph.run(
            body.message, motor_id=motor_id or route.entities.motor_id
        )
        yield _sse(
            "tools",
            {
                "tools": list((state.get("tool_results") or {}).keys()),
                "degraded": state.get("degraded"),
            },
        )

        answer = state.get("answer") or "Not available in indexed knowledge."
        # Stream answer in chunks for UX
        chunk_size = 48
        for i in range(0, len(answer), chunk_size):
            yield _sse("token", {"text": answer[i : i + chunk_size]})

        assistant = CopilotMessage(
            session_id=session_id,
            role="assistant",
            content=answer,
            intent=(state.get("route") or {}).get("intent"),
            confidence=state.get("confidence"),
            citations=state.get("citations"),
            reasoning=state.get("reasoning"),
            retrieval_trace_id=state.get("retrieval_trace_id"),
            tool_calls=[
                {"tool": k, "ok": (v or {}).get("ok")}
                for k, v in (state.get("tool_results") or {}).items()
                if isinstance(v, dict)
            ],
            extra_metadata={
                "verified": state.get("verified"),
                "numeric_checks": state.get("numeric_checks"),
                "degraded": state.get("degraded"),
                "route": state.get("route"),
            },
        )
        self.session.add(assistant)
        self._checkpoint()

        yield _sse(
            "final",
            ChatResponse(
                session_id=session_id,
                message_id=assistant.id,
                answer=answer,
                intent=assistant.intent,
                confidence=assistant.confidence,
                citations=assistant.citations or [],
                reasoning=assistant.reasoning,
                verified=bool(state.get("verified")),
                degraded=bool(state.get("degraded")),
                route=state.get("route"),
            ).model_dump(),
        )
        yield _sse("done", {"ok": True})

    def _checkpoint(self) -> None:
        """Persist current unit of work so later tool rollbacks cannot erase it."""
        self.session.flush()
        self.session.commit()

    def submit_feedback(
        self,
        body: FeedbackRequest,
        *,
        user_id: str | None = None,
    ) -> FeedbackOut:
        if body.session_id:
            # Soft-check — feedback should still store even if session was pruned
            try:
                self._get_session(body.session_id)
            except NotFoundError:
                _logger.warning(
                    "feedback_session_missing",
                    extra={"session_id": body.session_id},
                )
        row = FeedbackRating(
            session_id=body.session_id,
            message_id=body.message_id,
            user_id=user_id,
            rating=body.rating,
            comment=body.comment,
        )
        self.session.add(row)
        self._checkpoint()
        return FeedbackOut(
            id=row.id,
            session_id=row.session_id,
            message_id=row.message_id,
            rating=row.rating,
            comment=row.comment,
        )

    def _resolve_session(
        self,
        body: ChatRequest,
        *,
        user_id: str | None,
    ) -> CopilotSession:
        if body.session_id:
            return self._get_session(body.session_id)
        row = CopilotSession(
            motor_id=body.motor_id,
            user_id=user_id,
            title="Motor Copilot" if body.motor_id else "Industrial Copilot",
            status="active",
        )
        self.session.add(row)
        self._checkpoint()
        return row

    def _get_session(self, session_id: str) -> CopilotSession:
        row = self.session.scalars(
            select(CopilotSession)
            .where(CopilotSession.id == session_id)
            .options(selectinload(CopilotSession.messages))
        ).first()
        if row is None:
            raise NotFoundError(
                f"Copilot session not found: {session_id}",
                error_code="SESSION_NOT_FOUND",
            )
        return row

    def _session_out(self, row: CopilotSession) -> SessionOut:
        messages = [
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                intent=m.intent,
                confidence=m.confidence,
                citations=m.citations or [],
                reasoning=m.reasoning,
                created_at=m.created_at.isoformat() if m.created_at else None,
            )
            for m in (row.messages or [])
        ]
        return SessionOut(
            id=row.id,
            motor_id=row.motor_id,
            title=row.title,
            status=row.status,
            messages=messages,
            created_at=row.created_at.isoformat() if row.created_at else None,
        )


def _sse(event: str, data: Any) -> str:
    payload = json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"
