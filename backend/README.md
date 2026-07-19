# Backend — Industrial Brain AI
#
# Install (from backend/):
#   python -m venv .venv
#   .venv\Scripts\activate          # Windows
#   # source .venv/bin/activate     # macOS / Linux
#   pip install -e ".[dev]"
#
# Copy env template from repo root:
#   copy ..\.env.example ..\.env    # Windows
#   # cp ../.env.example ../.env    # macOS / Linux
#
# Run API (Milestone 1.2+):
#   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
#
# Database (Milestone 1.3):
#   # Ensure DATABASE_URL points at PostgreSQL (or sqlite for local smoke)
#   alembic upgrade head
#   python -m app.db.seed_cli
#
# Auth (Milestone 1.4 — JWT seed):
#   POST /api/v1/auth/login   {"email","password"}
#   POST /api/v1/auth/refresh {"refresh_token"}
#   GET  /api/v1/auth/me      Authorization: Bearer <access>
#   Seeded users (after seed_cli):
#     admin@example.com / ChangeMeAdmin!       (SystemAdmin)
#     operator@example.com / ChangeMeOperator! (PlantOperator)
#
# Object storage (Milestone 1.5 — internal service, no public HTTP API yet):
#   STORAGE_BACKEND=local|minio|s3|azure
#   Local default writes under STORAGE_LOCAL_ROOT (.data/storage)
#   MinIO: set STORAGE_BACKEND=minio + endpoint/keys (Compose arrives in 1.9)
#   Azure: STORAGE_BACKEND=azure + AZURE_STORAGE_CONNECTION_STRING
#   from app.storage import get_storage_service
#   svc = get_storage_service()
#   svc.upload("docs/demo.pdf", b"%PDF...", content_type="application/pdf")
#
# Corpus sync (Milestone 1.6 — local filesystem source):
#   Set CORPUS_SOURCE=local and CORPUS_LOCAL_ROOT=<dataset path>
#   POST /api/v1/sync/start   Authorization: Bearer <access>
#        {"mode":"discover"|"download"|"discover_and_download"}
#   GET  /api/v1/sync/status
#   GET  /api/v1/sync/auth/check
#   Discovery is metadata-only; selective download copies priority Motors files
#   into object storage (does NOT copy the full multi-GB corpus).
#
# Probes:
#   GET /health
#   GET /ready
#   GET /api/v1/ping
#   OpenAPI UI: /docs
#
# Tooling:
#   ruff check .
#   black --check .
#   pytest
