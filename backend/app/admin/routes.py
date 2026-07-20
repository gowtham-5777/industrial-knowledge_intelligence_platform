"""Admin + audit API routes (Milestones 5.1.3 / 5.2)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.admin.schemas import (
    AuditEventOut,
    AuditExportOut,
    AuditListOut,
    CreateUserRequest,
    SetUserActiveRequest,
    UpdateUserRolesRequest,
)
from app.admin.service import AdminService
from app.audit.service import AuditService, event_to_dict
from app.auth.dependencies import CurrentUserDep, require_roles
from app.core.dependencies import DbSessionDep, RequestIdDep
from app.core.responses import success_envelope

router = APIRouter(prefix="/admin", tags=["Admin"])


def get_admin_service(session: DbSessionDep) -> AdminService:
    return AdminService(session)


def get_audit_service(session: DbSessionDep) -> AuditService:
    return AuditService(session)


AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]

AdminOnly = Depends(require_roles("SystemAdmin"))
AuditReaders = Depends(require_roles("SystemAdmin", "Auditor", "ComplianceOfficer"))


@router.get(
    "/roles",
    summary="List RBAC roles",
    dependencies=[AdminOnly],
)
def list_roles(
    service: AdminServiceDep,
    request_id: RequestIdDep,
) -> dict:
    return success_envelope(
        [r.model_dump() for r in service.list_roles()],
        request_id=request_id,
    )


@router.get(
    "/users",
    summary="List users",
    dependencies=[AdminOnly],
)
def list_users(
    service: AdminServiceDep,
    request_id: RequestIdDep,
) -> dict:
    return success_envelope(
        [u.model_dump() for u in service.list_users()],
        request_id=request_id,
    )


@router.post(
    "/users",
    summary="Create user",
    dependencies=[AdminOnly],
)
def create_user(
    body: CreateUserRequest,
    service: AdminServiceDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> dict:
    created = service.create_user(
        email=str(body.email),
        display_name=body.display_name,
        password=body.password,
        role_codes=body.role_codes,
        is_active=body.is_active,
        actor_user_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    return success_envelope(created.model_dump(), request_id=request_id)


@router.put(
    "/users/{user_id}/roles",
    summary="Replace user roles",
    dependencies=[AdminOnly],
)
def set_user_roles(
    user_id: str,
    body: UpdateUserRolesRequest,
    service: AdminServiceDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> dict:
    updated = service.set_user_roles(
        user_id,
        body.role_codes,
        actor_user_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    return success_envelope(updated.model_dump(), request_id=request_id)


@router.put(
    "/users/{user_id}/active",
    summary="Activate / deactivate user",
    dependencies=[AdminOnly],
)
def set_user_active(
    user_id: str,
    body: SetUserActiveRequest,
    service: AdminServiceDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> dict:
    updated = service.set_user_active(
        user_id,
        body.is_active,
        actor_user_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    return success_envelope(updated.model_dump(), request_id=request_id)


@router.get(
    "/audit",
    summary="List audit events",
    dependencies=[AuditReaders],
)
def list_audit(
    audit: AuditServiceDep,
    request_id: RequestIdDep,
    action: str | None = None,
    actor_user_id: str | None = None,
    resource_type: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    rows, total = audit.list_events(
        action=action,
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        limit=limit,
        offset=offset,
    )
    out = AuditListOut(
        items=[AuditEventOut(**event_to_dict(r)) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
    return success_envelope(out.model_dump(), request_id=request_id)


@router.get(
    "/audit/export",
    summary="Export audit events (Compliance / Auditor)",
    dependencies=[AuditReaders],
)
def export_audit(
    audit: AuditServiceDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
    action: str | None = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
) -> dict:
    events = audit.export_events(action=action, limit=limit)
    audit.write(
        "export",
        actor_user_id=user.id,
        resource_type="audit_events",
        ip_address=request.client.host if request.client else None,
        details={"count": len(events), "action_filter": action},
    )
    out = AuditExportOut(
        events=[AuditEventOut(**e) for e in events],
        count=len(events),
    )
    return success_envelope(out.model_dump(), request_id=request_id)
