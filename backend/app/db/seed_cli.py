"""CLI entrypoint: python -m app.db.seed_cli"""

from __future__ import annotations

from app.core.config import clear_settings_cache, get_settings
from app.db.seed import run_seed
from app.db.session import clear_engine_cache, get_session_factory


def main() -> None:
    clear_settings_cache()
    clear_engine_cache()
    settings = get_settings()
    session = get_session_factory()()
    try:
        result = run_seed(session)
        session.commit()
        print(f"Seed complete ({settings.app_env}): {result}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
