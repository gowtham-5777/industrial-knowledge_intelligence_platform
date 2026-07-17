"""Auth FastAPI dependencies (Bearer JWT → current user)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.security import decode_token
from app.auth.service import AuthService
from app.core.dependencies import DbSessionDep, SettingsDep
from app.core.exceptions import AppError, ErrorCode, PermissionDeniedError
from app.db.models.system import User

_bearer = HTTPBearer(auto_error=False)


def get_auth_service(session: DbSessionDep, settings: SettingsDep) -> AuthService:
    return AuthService(session, settings)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: SettingsDep,
    auth: AuthServiceDep,
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(
            "Not authenticated",
            error_code=ErrorCode.PERMISSION_DENIED,
            status_code=401,
        )
    try:
        payload = decode_token(credentials.credentials, settings)
    except Exception as exc:
        raise AppError(
            "Invalid or expired access token",
            error_code=ErrorCode.PERMISSION_DENIED,
            status_code=401,
            details={"type": type(exc).__name__},
        ) from exc

    if payload.get("type") != "access":
        raise AppError(
            "Invalid access token type",
            error_code=ErrorCode.PERMISSION_DENIED,
            status_code=401,
        )

    user_id = payload.get("sub")
    if not user_id:
        raise AppError(
            "Invalid access token subject",
            error_code=ErrorCode.PERMISSION_DENIED,
            status_code=401,
        )

    user = auth.get_user_by_id(str(user_id))
    if user is None or not user.is_active:
        raise PermissionDeniedError("User not found or inactive")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_roles(*role_codes: str):
    """Dependency factory for role checks (used by later milestones)."""

    def _checker(user: CurrentUserDep) -> User:
        codes = {link.role.code for link in user.roles if link.role is not None}
        if not codes.intersection(role_codes):
            raise PermissionDeniedError(
                "Insufficient role",
                details={"required": list(role_codes)},
            )
        return user

    return _checker
