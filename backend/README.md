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
