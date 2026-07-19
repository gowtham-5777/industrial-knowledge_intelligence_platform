#!/bin/sh
# Wait for Postgres, migrate, optionally seed, then exec the API process.
set -eu

echo "[api-entrypoint] Waiting for PostgreSQL…"
python - <<'PY'
import os
import sys
import time

from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL")
if not url:
    print("DATABASE_URL is required", file=sys.stderr)
    sys.exit(1)

deadline = time.time() + 120
last_error = None
while time.time() < deadline:
    try:
        engine = create_engine(url, connect_args={"connect_timeout": 3})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        print("[api-entrypoint] PostgreSQL is ready")
        break
    except Exception as exc:  # noqa: BLE001 — retry until deadline
        last_error = exc
        time.sleep(2)
else:
    print(f"[api-entrypoint] PostgreSQL not ready: {last_error}", file=sys.stderr)
    sys.exit(1)
PY

echo "[api-entrypoint] Running Alembic migrations…"
alembic upgrade head

if [ "${SEED_ON_START:-true}" = "true" ]; then
  echo "[api-entrypoint] Seeding baseline roles/users…"
  python -m app.db.seed_cli
fi

echo "[api-entrypoint] Starting: $*"
exec "$@"
