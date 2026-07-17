"""Organization tables: product lines and plants."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.assets import Asset
    from app.db.models.motors import MotorFamily


class ProductLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """OEM product line (e.g. ABB Low Voltage Motors)."""

    __tablename__ = "product_lines"

    code: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    oem: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    motor_families: Mapped[list[MotorFamily]] = relationship(
        back_populates="product_line"
    )


class Plant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Logical plant / site placeholder."""

    __tablename__ = "plants"

    code: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    assets: Mapped[list[Asset]] = relationship(back_populates="plant")
