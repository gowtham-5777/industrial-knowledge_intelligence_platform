"""Drawing number explorer API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DrawingListItemOut(BaseModel):
    id: str
    drawing_number: str
    normalized: str
    description: str | None = None
    document_count: int = 0


class DrawingListOut(BaseModel):
    items: list[DrawingListItemOut]
    total: int
    limit: int
    offset: int


class DrawingDocumentOut(BaseModel):
    id: str
    title: str
    doc_category: str | None = None
    status: str
    sheet_id: str | None = None


class DrawingLinkedMotorOut(BaseModel):
    id: str
    code: str
    name: str


class DrawingLinkedAssetOut(BaseModel):
    id: str
    asset_type: str
    name: str
    asset_tag: str | None = None


class DrawingCrossRefOut(BaseModel):
    id: str
    drawing_number: str
    normalized: str
    description: str | None = None
    documents: list[DrawingDocumentOut] = Field(default_factory=list)
    linked_motors: list[DrawingLinkedMotorOut] = Field(default_factory=list)
    linked_assets: list[DrawingLinkedAssetOut] = Field(default_factory=list)
