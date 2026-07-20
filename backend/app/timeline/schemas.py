"""Motor lifecycle timeline schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TimelineEventOut(BaseModel):
    id: str
    event_type: str
    title: str
    description: str | None = None
    event_at: datetime
    is_estimated: bool
    document_id: str | None = None

    model_config = {"from_attributes": True}


class TimelineOut(BaseModel):
    motor_id: str
    items: list[TimelineEventOut]
    total: int
