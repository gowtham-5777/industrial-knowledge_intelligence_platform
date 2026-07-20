"""Pydantic schemas for indexing / parse API (Milestone 2.1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ParseRouteRequest(BaseModel):
    document_id: str
    force_tier: str | None = None


class ParseRunRequest(BaseModel):
    document_id: str
    force_tier: str | None = None
    sync: bool = True


class ParseRouteOut(BaseModel):
    document_id: str
    tier: str
    handler: str
    mime_type: str | None = None
    doc_category: str | None = None
    doc_subtype: str | None = None
    filename: str | None = None
    folder_path: str | None = None


class IndexingJobOut(BaseModel):
    id: str
    job_type: str
    status: str
    priority: int
    attempts: int
    error_message: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    document_id: str | None = None
    catalog_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None


class ParseResultOut(BaseModel):
    id: str
    document_id: str
    document_version_id: str | None = None
    indexing_job_id: str | None = None
    tier: str
    parser_name: str
    status: str
    page_count: int
    full_text: str | None = None
    pages: list[dict[str, Any]] = Field(default_factory=list)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    parsed_at: datetime | None = None


class ParseRunOut(BaseModel):
    job: IndexingJobOut
    route: ParseRouteOut
    result: ParseResultOut | None = None
