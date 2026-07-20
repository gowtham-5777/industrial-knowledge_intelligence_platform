"""Immutable audit event writer + export (Milestone 5.2)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.system import AuditEvent
from app.observability import get_logger

_logger = get_logger(__name__)

# Architecture §11 covered actions
AUDIT_ACTIONS = frozenset(
    {
        "login",
        "document_upload",
        "document_view",
        "copilot_query",
        "copilot_response",
        "graph_edit",
        "export",
        "admin_action",
        "indexing_invalidate",
        "rate_limited",
    }
)


class AuditService:
    """Append-only audit writer. Never updates or deletes existing rows."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def write(
        self,
        action: str,
        *,
        actor_user_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            details=details or {},
        )
        self.session.add(event)
        self.session.flush()
        _logger.info(
            "audit_event",
            extra={
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "actor_user_id": actor_user_id,
            },
        )
        return event

    def list_events(
        self,
        *,
        action: str | None = None,
        actor_user_id: str | None = None,
        resource_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditEvent], int]:
        stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc())
        count_stmt = select(AuditEvent)
        if action:
            stmt = stmt.where(AuditEvent.action == action)
            count_stmt = count_stmt.where(AuditEvent.action == action)
        if actor_user_id:
            stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
            count_stmt = count_stmt.where(AuditEvent.actor_user_id == actor_user_id)
        if resource_type:
            stmt = stmt.where(AuditEvent.resource_type == resource_type)
            count_stmt = count_stmt.where(AuditEvent.resource_type == resource_type)
        total = len(list(self.session.scalars(count_stmt).all()))
        rows = list(self.session.scalars(stmt.offset(offset).limit(limit)).all())
        return rows, total

    def export_events(
        self,
        *,
        action: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        rows, _ = self.list_events(action=action, limit=limit, offset=0)
        return [
            {
                "id": r.id,
                "action": r.action,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "actor_user_id": r.actor_user_id,
                "ip_address": r.ip_address,
                "details": r.details,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]


def event_to_dict(event: AuditEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "action": event.action,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "actor_user_id": event.actor_user_id,
        "ip_address": event.ip_address,
        "details": event.details,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
