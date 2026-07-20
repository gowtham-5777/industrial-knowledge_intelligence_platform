"""Fleet dashboard KPI schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.health.scoring import HealthScoreOut


class DashboardKpisOut(BaseModel):
    catalog_count: int
    document_count: int
    indexed_count: int
    motor_count: int
    hero_motor_code: str | None = None
    hero_health: HealthScoreOut | None = None
    indexing_status: dict[str, Any] | None = None
