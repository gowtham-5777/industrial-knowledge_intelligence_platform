"""Pydantic schemas for Industrial Copilot / query router APIs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RouteRequest(BaseModel):
    query: str = Field(..., min_length=1)
    motor_id: str | None = None


class LinkedEntitiesOut(BaseModel):
    motor_id: str | None = None
    motor_code: str | None = None
    serial_number: str | None = None
    drawing_number: str | None = None
    aliases_matched: list[str] = Field(default_factory=list)


class RouteResponse(BaseModel):
    intent: str
    confidence: float
    entities: LinkedEntitiesOut
    tools: list[str] = Field(default_factory=list)
    model_tier: str = "fast"
    rationale: str = ""


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    motor_id: str | None = None
    stream: bool = False


class ChatResponse(BaseModel):
    session_id: str
    message_id: str
    answer: str
    intent: str | None = None
    confidence: float | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    reasoning: str | None = None
    verified: bool = False
    degraded: bool = False
    route: dict[str, Any] | None = None


class SessionCreateRequest(BaseModel):
    motor_id: str | None = None
    title: str | None = None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    intent: str | None = None
    confidence: float | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    reasoning: str | None = None
    created_at: str | None = None


class SessionOut(BaseModel):
    id: str
    motor_id: str | None = None
    title: str | None = None
    status: str
    messages: list[MessageOut] = Field(default_factory=list)
    created_at: str | None = None


class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    session_id: str | None = None
    message_id: str | None = None
    comment: str | None = None


class FeedbackOut(BaseModel):
    id: str
    session_id: str | None = None
    message_id: str | None = None
    rating: int
    comment: str | None = None
