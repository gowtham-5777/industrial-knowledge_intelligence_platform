"""Unified search across motors, documents, and drawing numbers (Phase 3).

Lightweight entity search (registry + catalog metadata) — distinct from
``HybridRetrievalService`` which searches indexed chunk content for RAG.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.repositories.documents import DocumentCatalogRepository
from app.db.repositories.motors import MotorModelRepository
from app.drawings.explorer import DrawingExplorerService


class MotorHit(BaseModel):
    id: str
    code: str
    name: str
    frame_size: str | None = None
    power_kw: float | None = None
    type: str = "motor"


class DocumentHit(BaseModel):
    id: str
    name: str
    doc_category: str | None = None
    drawing_number: str | None = None
    motor_type_code: str | None = None
    type: str = "document"


class DrawingHit(BaseModel):
    id: str
    drawing_number: str
    document_count: int = 0
    type: str = "drawing"


class SearchResultsOut(BaseModel):
    query: str
    motors: list[MotorHit] = Field(default_factory=list)
    documents: list[DocumentHit] = Field(default_factory=list)
    drawings: list[DrawingHit] = Field(default_factory=list)
    total: int = 0


class UnifiedSearchService:
    """Fan out a single query string across the registry + catalog."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.motors = MotorModelRepository(session)
        self.catalog = DocumentCatalogRepository(session)
        self.drawings = DrawingExplorerService(session)

    def search(self, q: str, *, limit: int = 10) -> SearchResultsOut:
        query = q.strip()
        if not query:
            return SearchResultsOut(
                query=q, motors=[], documents=[], drawings=[], total=0
            )

        motor_rows, _ = self.motors.search(q=query, limit=limit)
        motors = [
            MotorHit(
                id=m.id,
                code=m.code,
                name=m.name,
                frame_size=m.frame_size,
                power_kw=m.power_kw,
            )
            for m in motor_rows
        ]

        catalog_rows = self.catalog.list_filtered(q=query, limit=limit)
        documents = [
            DocumentHit(
                id=c.id,
                name=c.name,
                doc_category=c.doc_category,
                drawing_number=c.drawing_number,
                motor_type_code=c.motor_type_code,
            )
            for c in catalog_rows
        ]

        drawing_results = self.drawings.list_drawings(q=query, limit=limit)
        drawings = [
            DrawingHit(
                id=d.id,
                drawing_number=d.drawing_number,
                document_count=d.document_count,
            )
            for d in drawing_results.items
        ]

        return SearchResultsOut(
            query=query,
            motors=motors,
            documents=documents,
            drawings=drawings,
            total=len(motors) + len(documents) + len(drawings),
        )
