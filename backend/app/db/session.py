"""Engine and session factory for the PostgreSQL system of record."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Create a cached SQLAlchemy engine from settings."""
    settings = get_settings()
    connect_args: dict = {}
    url = settings.database_url
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    elif url.startswith("postgresql"):
        # Avoid multi-minute hangs when Postgres is down (tests /ready probe)
        connect_args["connect_timeout"] = 3
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped DB session."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database_connection() -> bool:
    """Return True when the database accepts a simple connectivity probe."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def clear_engine_cache() -> None:
    """Dispose and clear cached engine/session factory (tests)."""
    try:
        get_engine().dispose()
    except Exception:
        pass
    get_engine.cache_clear()
    get_session_factory.cache_clear()
