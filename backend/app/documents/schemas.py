"""Document catalog & upload API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CatalogItemOut(BaseModel):
    id: str
    drive_file_id: str
    name: str
    folder_path: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    md5_checksum: str | None = None
    doc_category: str | None = None
    doc_subtype: str | None = None
    drawing_number: str | None = None
    motor_type_code: str | None = None
    discovered_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class CatalogStatsOut(BaseModel):
    total: int
    filtered: int


class CatalogListOut(BaseModel):
    items: list[CatalogItemOut]
    total: int
    limit: int
    offset: int


class DocumentVersionOut(BaseModel):
    id: str
    version: int
    storage_uri: str
    checksum: str | None = None

    model_config = {"from_attributes": True}


class LinkedAssetOut(BaseModel):
    id: str
    asset_type: str
    name: str
    asset_tag: str | None = None
    status: str
    link_type: str


class LinkedDrawingOut(BaseModel):
    id: str
    drawing_number: str
    normalized: str


class DocumentOut(BaseModel):
    id: str
    title: str
    doc_type: str | None = None
    status: str
    storage_uri: str | None = None
    catalog_id: str | None = None
    created_at: datetime | None = None
    versions: list[DocumentVersionOut] = Field(default_factory=list)
    linked_assets: list[LinkedAssetOut] = Field(default_factory=list)
    linked_drawings: list[LinkedDrawingOut] = Field(default_factory=list)
    catalog: CatalogItemOut | None = None

    model_config = {"from_attributes": True}


class DocumentListOut(BaseModel):
    items: list[DocumentOut]
    total: int
    limit: int
    offset: int


class UploadResultOut(BaseModel):
    document: DocumentOut
    catalog: CatalogItemOut
    storage_key: str
    bucket: str
