"""Template-based recommendation engine schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CitationRef(BaseModel):
    doc_id: str
    chunk_id: str | None = None


class RecommendationOut(BaseModel):
    title: str
    category: str
    rationale: str
    confidence: float
    citations: list[CitationRef] = Field(default_factory=list)


class RecommendationsOut(BaseModel):
    motor_id: str
    items: list[RecommendationOut]
    generated_at: datetime
    model_version: str | None = None
    cached: bool = False
