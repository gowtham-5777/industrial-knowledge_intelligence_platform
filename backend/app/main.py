"""Application entrypoint skeleton for Industrial Brain AI.

Full middleware, API versioning, and health/readiness endpoints arrive in Milestone 1.2.
"""

from fastapi import FastAPI

app = FastAPI(
    title="Industrial Brain AI",
    version="0.1.0",
    description="Industrial Knowledge Intelligence Platform",
)
