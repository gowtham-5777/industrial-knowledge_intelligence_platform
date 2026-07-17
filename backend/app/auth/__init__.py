"""Authentication and RBAC (hackathon: JWT seed users)."""

from app.auth.dependencies import CurrentUserDep, get_current_user, require_roles
from app.auth.routes import router as auth_router

__all__ = [
    "CurrentUserDep",
    "auth_router",
    "get_current_user",
    "require_roles",
]
