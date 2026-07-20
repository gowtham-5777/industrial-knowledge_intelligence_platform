"""Motor 360 aggregation bundle schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.graph.subgraph import SubgraphOut
from app.health.scoring import HealthScoreOut
from app.motors.schemas import MotorModelOut
from app.recommendations.schemas import RecommendationsOut
from app.summary.schemas import SummaryOut
from app.timeline.schemas import TimelineOut


class DocumentPanelItem(BaseModel):
    id: str
    title: str
    doc_category: str | None = None
    doc_subtype: str | None = None
    status: str
    drawing_number: str | None = None
    discovered_at: datetime | None = None


class DocumentPanel(BaseModel):
    category: str
    items: list[DocumentPanelItem] = Field(default_factory=list)


class RelatedAssetOut(BaseModel):
    id: str
    code: str
    name: str
    relation: str


class Motor360Out(BaseModel):
    motor: MotorModelOut
    documents: list[DocumentPanel] = Field(default_factory=list)
    summary: SummaryOut
    health: HealthScoreOut
    recommendations: RecommendationsOut
    timeline: TimelineOut
    related_assets: list[RelatedAssetOut] = Field(default_factory=list)
    subgraph: SubgraphOut
    drawing_numbers: list[str] = Field(default_factory=list)
