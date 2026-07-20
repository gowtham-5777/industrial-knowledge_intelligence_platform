"""AI session / feedback tables (Architecture §12 — Phase 4)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CopilotSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Motor-scoped (or global) Industrial Copilot conversation."""

    __tablename__ = "copilot_sessions"

    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    motor_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("motor_models.id"), nullable=True, index=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True
    )
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    messages: Mapped[list[CopilotMessage]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="CopilotMessage.created_at",
    )


class CopilotMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Single turn in a copilot session."""

    __tablename__ = "copilot_messages"

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("copilot_sessions.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    citations: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieval_trace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("retrieval_traces.id"), nullable=True, index=True
    )
    tool_calls: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    session: Mapped[CopilotSession] = relationship(back_populates="messages")


class FeedbackRating(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """User feedback on a copilot answer (thumbs / score)."""

    __tablename__ = "feedback_ratings"

    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("copilot_sessions.id"), nullable=True, index=True
    )
    message_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("copilot_messages.id"), nullable=True, index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
