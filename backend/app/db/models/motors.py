"""Motor specialization tables (hero domain for hackathon)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.organization import ProductLine


class MotorFamily(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "motor_families"

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_line_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("product_lines.id"), nullable=False, index=True
    )

    product_line: Mapped[ProductLine] = relationship(back_populates="motor_families")
    models: Mapped[list[MotorModel]] = relationship(back_populates="family")

    __table_args__ = (
        UniqueConstraint("product_line_id", "code", name="uq_motor_family_line_code"),
    )


class MotorModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "motor_models"

    code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    frame_size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    voltage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ie_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    poles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mounting: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cooling: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    family_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("motor_families.id"), nullable=False, index=True
    )
    asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assets.id"), nullable=True, unique=True
    )

    family: Mapped[MotorFamily] = relationship(back_populates="models")
    units: Mapped[list[MotorUnit]] = relationship(back_populates="model")
    aliases: Mapped[list[MotorAlias]] = relationship(back_populates="model")
    health_scores: Mapped[list[MotorHealthScore]] = relationship(back_populates="model")
    ai_summaries: Mapped[list[MotorAiSummary]] = relationship(back_populates="model")
    recommendations: Mapped[list[MotorRecommendation]] = relationship(
        back_populates="model"
    )
    timeline_events: Mapped[list[MotorTimelineEvent]] = relationship(
        back_populates="model"
    )

    __table_args__ = (
        UniqueConstraint("family_id", "code", name="uq_motor_model_family_code"),
    )


class MotorUnit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "motor_units"

    serial_number: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    commissioned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    model_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("motor_models.id"), nullable=False, index=True
    )
    asset_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assets.id"), nullable=True, unique=True
    )

    model: Mapped[MotorModel] = relationship(back_populates="units")


class MotorAlias(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "motor_aliases"

    alias: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    alias_type: Mapped[str] = mapped_column(String(64), nullable=False, default="name")
    model_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("motor_models.id"), nullable=False, index=True
    )

    model: Mapped[MotorModel] = relationship(back_populates="aliases")

    __table_args__ = (
        UniqueConstraint("model_id", "alias", name="uq_motor_alias_model_alias"),
    )


class MotorHealthScore(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "motor_health_scores"

    score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    reasoning: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    model_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("motor_models.id"), nullable=False, index=True
    )

    model: Mapped[MotorModel] = relationship(back_populates="health_scores")


class MotorAiSummary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "motor_ai_summaries"

    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_doc_ids: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    model_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("motor_models.id"), nullable=False, index=True
    )

    model: Mapped[MotorModel] = relationship(back_populates="ai_summaries")


class MotorRecommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "motor_recommendations"

    recommendations: Mapped[list[Any] | dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("motor_models.id"), nullable=False, index=True
    )

    model: Mapped[MotorModel] = relationship(back_populates="recommendations")


class MotorTimelineEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "motor_timeline_events"

    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    is_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=True
    )
    model_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("motor_models.id"), nullable=False, index=True
    )

    model: Mapped[MotorModel] = relationship(back_populates="timeline_events")
