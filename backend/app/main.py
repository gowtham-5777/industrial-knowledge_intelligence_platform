"""FastAPI application factory and ASGI entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.error_handlers import register_exception_handlers
from app.core.middleware import RequestIdMiddleware, TimingMiddleware
from app.health.routes import router as health_router

OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "Liveness and readiness probes for orchestration.",
    },
    {
        "name": "System",
        "description": "Versioned system utilities under `/api/v1`.",
    },
    {
        "name": "Auth",
        "description": "JWT seed authentication (login, refresh, me).",
    },
    {
        "name": "Protected",
        "description": "Routes that require a Bearer access token.",
    },
    {
        "name": "Sync",
        "description": "Corpus discovery + selective download (local or Drive-shaped).",
    },
]


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    cfg = settings or get_settings()

    app = FastAPI(
        title=cfg.app_name,
        version=__version__,
        description=(
            "Industrial Brain AI — Industrial Knowledge Intelligence Platform. "
            "REST API uses a consistent `{ data, meta, errors }` envelope "
            "(Architecture §13)."
        ),
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.state.settings = cfg

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )
    # Starlette applies middleware in reverse add order; request ID should wrap timing.
    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix=cfg.api_prefix)

    return app


app = create_app()
