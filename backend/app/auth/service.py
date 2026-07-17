"""Authentication service — JWT seed users (Architecture hackathon path)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.schemas import RoleOut, TokenPair, UserOut
from app.auth.security import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.config import Settings
from app.core.exceptions import AppError, ErrorCode, PermissionDeniedError
from app.db.models.system import AuditEvent, Role, User, UserRole


class AuthService:
    """Owns auth domain logic; repositories stay SQL-only."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def get_user_by_email(self, email: str) -> User | None:
        stmt = (
            select(User)
            .where(User.email == email.lower())
            .options(selectinload(User.roles).selectinload(UserRole.role))
        )
        return self.session.scalars(stmt).first()

    def get_user_by_id(self, user_id: str) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles).selectinload(UserRole.role))
        )
        return self.session.scalars(stmt).first()

    def authenticate(self, email: str, password: str) -> User:
        user = self.get_user_by_email(email)
        if user is None or not user.hashed_password:
            raise AppError(
                "Invalid email or password",
                error_code=ErrorCode.PERMISSION_DENIED,
                status_code=401,
            )
        if not user.is_active:
            raise PermissionDeniedError("User account is inactive")
        if not verify_password(password, user.hashed_password):
            raise AppError(
                "Invalid email or password",
                error_code=ErrorCode.PERMISSION_DENIED,
                status_code=401,
            )
        return user

    def issue_tokens(self, user: User) -> TokenPair:
        role_codes = [link.role.code for link in user.roles if link.role is not None]
        access = create_token(
            subject=user.id,
            token_type="access",
            settings=self.settings,
            extra_claims={"email": user.email, "roles": role_codes},
        )
        refresh = create_token(
            subject=user.id,
            token_type="refresh",
            settings=self.settings,
        )
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=self.settings.jwt_access_token_expire_minutes * 60,
        )

    def login(self, email: str, password: str, *, ip_address: str | None) -> TokenPair:
        user = self.authenticate(email, password)
        user.last_login_at = datetime.now(UTC)
        self.session.add(
            AuditEvent(
                action="login",
                resource_type="user",
                resource_id=user.id,
                actor_user_id=user.id,
                ip_address=ip_address,
                details={"email": user.email},
            )
        )
        self.session.flush()
        return self.issue_tokens(user)

    def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = decode_token(refresh_token, self.settings)
        except Exception as exc:
            raise AppError(
                "Invalid or expired refresh token",
                error_code=ErrorCode.PERMISSION_DENIED,
                status_code=401,
                details={"type": type(exc).__name__},
            ) from exc

        if payload.get("type") != "refresh":
            raise AppError(
                "Invalid refresh token type",
                error_code=ErrorCode.PERMISSION_DENIED,
                status_code=401,
            )

        user_id = payload.get("sub")
        if not user_id:
            raise AppError(
                "Invalid refresh token subject",
                error_code=ErrorCode.PERMISSION_DENIED,
                status_code=401,
            )

        user = self.get_user_by_id(str(user_id))
        if user is None or not user.is_active:
            raise PermissionDeniedError("User not found or inactive")
        return self.issue_tokens(user)

    def to_user_out(self, user: User) -> UserOut:
        roles = [
            RoleOut(code=link.role.code, name=link.role.name)
            for link in user.roles
            if link.role is not None
        ]
        return UserOut(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            roles=roles,
        )


def ensure_user_with_role(
    session: Session,
    *,
    email: str,
    display_name: str,
    password: str,
    role_code: str,
) -> User:
    """Idempotent seed helper for demo users."""
    email_norm = email.lower()
    existing = session.scalars(select(User).where(User.email == email_norm)).first()
    role = session.scalars(select(Role).where(Role.code == role_code)).first()
    if role is None:
        raise ValueError(f"Role {role_code} must be seeded before users")

    if existing is None:
        user = User(
            email=email_norm,
            display_name=display_name,
            hashed_password=hash_password(password),
            is_active=True,
        )
        session.add(user)
        session.flush()
    else:
        user = existing
        if not user.hashed_password:
            user.hashed_password = hash_password(password)

    link = session.scalars(
        select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
        )
    ).first()
    if link is None:
        session.add(UserRole(user_id=user.id, role_id=role.id))
        session.flush()
    return user
