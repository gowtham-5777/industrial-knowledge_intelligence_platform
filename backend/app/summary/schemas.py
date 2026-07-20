"""AI asset summary schemas — structured, citation-backed, honest-by-default."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class KeySpecOut(BaseModel):
    label: str
    value: str


class SummaryOut(BaseModel):
    motor_id: str
    overview: str
    key_specs: list[KeySpecOut] = Field(default_factory=list)
    knowledge_gaps: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    honesty_note: str
    generated_at: datetime
    model_version: str | None = None
    source_doc_ids: list[str] = Field(default_factory=list)
    cached: bool = False
