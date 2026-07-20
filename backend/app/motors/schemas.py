"""Motor registry / explorer Pydantic schemas (Phase 3)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AssetTypeOut(BaseModel):
    asset_type: str
    count: int


class ProductLineOut(BaseModel):
    id: str
    code: str
    name: str
    oem: str | None = None


class MotorFamilyOut(BaseModel):
    id: str
    code: str
    name: str
    product_line_id: str


class MotorAliasOut(BaseModel):
    alias: str
    alias_type: str


class MotorUnitOut(BaseModel):
    id: str
    serial_number: str
    status: str


class MotorModelOut(BaseModel):
    id: str
    code: str
    name: str
    frame_size: str | None = None
    power_kw: float | None = None
    voltage: str | None = None
    ie_class: str | None = None
    poles: int | None = None
    mounting: str | None = None
    cooling: str | None = None
    asset_id: str | None = None
    family_id: str
    family_code: str | None = None
    product_line_code: str | None = None
    aliases: list[MotorAliasOut] = Field(default_factory=list)
    is_hero: bool = False
    is_supporting: bool = False
    metadata: dict[str, Any] | None = None


class MotorListOut(BaseModel):
    items: list[MotorModelOut]
    total: int
    limit: int
    offset: int


class MotorEnrichRequest(BaseModel):
    frame_size: str | None = None
    power_kw: float | None = None
    voltage: str | None = None
    ie_class: str | None = None
    poles: int | None = None
    mounting: str | None = None
    cooling: str | None = None
    name: str | None = None
    aliases: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None


class HeroMotorsOut(BaseModel):
    hero: MotorModelOut
    supporting: list[MotorModelOut]
    confirmed_at: datetime | None = None


class AliasResolveOut(BaseModel):
    query: str
    matched: MotorModelOut | None = None
