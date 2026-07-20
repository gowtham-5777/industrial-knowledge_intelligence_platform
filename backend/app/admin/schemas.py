"""Admin schemas — users, roles, audit (Milestone 5.1.3 / 5.2)."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class AdminRoleOut(BaseModel):
    id: str
    code: str
    name: str
    description: str | None = None


class AdminUserOut(BaseModel):
    id: str
    email: str
    display_name: str
    is_active: bool
    roles: list[AdminRoleOut]


class CreateUserRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role_codes: list[str] = Field(default_factory=list)
    is_active: bool = True


class UpdateUserRolesRequest(BaseModel):
    role_codes: list[str] = Field(default_factory=list)


class SetUserActiveRequest(BaseModel):
    is_active: bool


class AuditEventOut(BaseModel):
    id: str
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    actor_user_id: str | None = None
    ip_address: str | None = None
    details: dict | None = None
    created_at: str | None = None


class AuditListOut(BaseModel):
    items: list[AuditEventOut]
    total: int
    limit: int
    offset: int


class AuditExportOut(BaseModel):
    events: list[AuditEventOut]
    count: int
