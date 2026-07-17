"""Auth API routes: login, refresh, me."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.auth.dependencies import AuthServiceDep, CurrentUserDep
from app.auth.schemas import LoginRequest, RefreshRequest, TokenPair, UserOut
from app.core.dependencies import RequestIdDep
from app.core.responses import success_envelope

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    summary="Login with email/password (JWT seed provider)",
)
def login(
    body: LoginRequest,
    request: Request,
    auth: AuthServiceDep,
    request_id: RequestIdDep,
) -> dict:
    tokens: TokenPair = auth.login(
        body.email,
        body.password,
        ip_address=request.client.host if request.client else None,
    )
    return success_envelope(tokens.model_dump(), request_id=request_id)


@router.post(
    "/refresh",
    summary="Refresh access token",
)
def refresh(
    body: RefreshRequest,
    auth: AuthServiceDep,
    request_id: RequestIdDep,
) -> dict:
    tokens = auth.refresh(body.refresh_token)
    return success_envelope(tokens.model_dump(), request_id=request_id)


@router.get(
    "/me",
    summary="Current authenticated user",
)
def me(
    user: CurrentUserDep,
    auth: AuthServiceDep,
    request_id: RequestIdDep,
) -> dict:
    profile: UserOut = auth.to_user_out(user)
    return success_envelope(profile.model_dump(), request_id=request_id)
