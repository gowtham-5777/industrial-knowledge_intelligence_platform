"""CLI entrypoint: python -m app.db.seed_cli"""

from __future__ import annotations

from app.core.config import clear_settings_cache, get_settings
from app.db.seed import run_seed
from app.db.session import clear_engine_cache, get_session_factory
from app.observability import configure_logging, get_logger

_logger = get_logger(__name__)


def main() -> None:
    clear_settings_cache()
    clear_engine_cache()
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.log_json)
    session = get_session_factory()()
    try:
        result = run_seed(session)
        session.commit()
        _logger.info(
            "seed complete",
            extra={"app_env": settings.app_env, "seed_result": result},
        )
    except Exception:
        session.rollback()
        _logger.exception("seed failed")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
