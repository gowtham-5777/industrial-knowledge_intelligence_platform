"""FastAPI Depends providers for shared infrastructure."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.core.middleware import get_request_id


def provide_settings() -> Generator[Settings, None, None]:
    """Yield cached application settings (Depends-friendly wrapper)."""
    yield get_settings()


def provide_request_id(request: Request) -> str | None:
    """Expose the correlation request ID to route handlers."""
    return get_request_id(request)


SettingsDep = Annotated[Settings, Depends(provide_settings)]
RequestIdDep = Annotated[str | None, Depends(provide_request_id)]
