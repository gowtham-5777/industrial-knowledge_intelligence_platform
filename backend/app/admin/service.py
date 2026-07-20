"""Admin user/role management (Milestone 5.1.3)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.admin.schemas import AdminRoleOut, AdminUserOut
from app.audit.service import AuditService
from app.auth.security import hash_password
from app.core.exceptions import AppError, ErrorCode, NotFoundError
from app.db.models.system import Role, User, UserRole


class AdminService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.audit = AuditService(session)

    def list_roles(self) -> list[AdminRoleOut]:
        rows = list(self.session.scalars(select(Role).order_by(Role.code)).all())
        return [
            AdminRoleOut(
                id=r.id, code=r.code, name=r.name, description=r.description
            )
            for r in rows
        ]

    def list_users(self) -> list[AdminUserOut]:
        rows = list(
            self.session.scalars(
                select(User)
                .options(selectinload(User.roles).selectinload(UserRole.role))
                .order_by(User.email)
            ).all()
        )
        return [self._to_user_out(u) for u in rows]

    def get_user(self, user_id: str) -> AdminUserOut:
        user = self._load_user(user_id)
        return self._to_user_out(user)

    def create_user(
        self,
        *,
        email: str,
        display_name: str,
        password: str,
        role_codes: list[str],
        is_active: bool,
        actor_user_id: str,
        ip_address: str | None = None,
    ) -> AdminUserOut:
        email_norm = email.lower().strip()
        existing = self.session.scalars(
            select(User).where(User.email == email_norm)
        ).first()
        if existing is not None:
            raise AppError(
                "User email already exists",
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
            )
        user = User(
            email=email_norm,
            display_name=display_name.strip(),
            hashed_password=hash_password(password),
            is_active=is_active,
        )
        self.session.add(user)
        self.session.flush()
        self._replace_roles(user, role_codes)
        self.audit.write(
            "admin_action",
            actor_user_id=actor_user_id,
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            details={"op": "create_user", "email": email_norm, "roles": role_codes},
        )
        self.session.flush()
        return self._to_user_out(self._load_user(user.id))

    def set_user_roles(
        self,
        user_id: str,
        role_codes: list[str],
        *,
        actor_user_id: str,
        ip_address: str | None = None,
    ) -> AdminUserOut:
        user = self._load_user(user_id)
        self._replace_roles(user, role_codes)
        self.audit.write(
            "admin_action",
            actor_user_id=actor_user_id,
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            details={"op": "set_roles", "roles": role_codes},
        )
        self.session.flush()
        return self._to_user_out(self._load_user(user.id))

    def set_user_active(
        self,
        user_id: str,
        is_active: bool,
        *,
        actor_user_id: str,
        ip_address: str | None = None,
    ) -> AdminUserOut:
        user = self._load_user(user_id)
        user.is_active = is_active
        self.audit.write(
            "admin_action",
            actor_user_id=actor_user_id,
            resource_type="user",
            resource_id=user.id,
            ip_address=ip_address,
            details={"op": "set_active", "is_active": is_active},
        )
        self.session.flush()
        return self._to_user_out(user)

    def _replace_roles(self, user: User, role_codes: list[str]) -> None:
        codes = sorted({c.strip() for c in role_codes if c and c.strip()})
        roles = list(
            self.session.scalars(select(Role).where(Role.code.in_(codes))).all()
        )
        found = {r.code for r in roles}
        missing = set(codes) - found
        if missing:
            raise AppError(
                "Unknown role code(s)",
                error_code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
                details={"missing": sorted(missing)},
            )
        for link in list(user.roles):
            self.session.delete(link)
        self.session.flush()
        for role in roles:
            self.session.add(UserRole(user_id=user.id, role_id=role.id))
        self.session.flush()

    def _load_user(self, user_id: str) -> User:
        user = self.session.scalars(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles).selectinload(UserRole.role))
        ).first()
        if user is None:
            raise NotFoundError("User not found")
        return user

    @staticmethod
    def _to_user_out(user: User) -> AdminUserOut:
        roles = [
            AdminRoleOut(
                id=link.role.id,
                code=link.role.code,
                name=link.role.name,
                description=link.role.description,
            )
            for link in user.roles
            if link.role is not None
        ]
        return AdminUserOut(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            roles=roles,
        )
