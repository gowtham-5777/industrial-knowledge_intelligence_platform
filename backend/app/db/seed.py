"""Seed hooks for baseline SoR data (idempotent)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.organization import ProductLine
from app.db.models.system import Role

ABB_LV_MOTORS_CODE = "ABB_LV_MOTORS"
ABB_LV_MOTORS_NAME = "ABB Low Voltage Motors"

DEFAULT_ROLES: tuple[tuple[str, str, str], ...] = (
    ("PlantOperator", "Plant Operator", "Read assets, docs, copilot (own plant)"),
    ("MaintenanceEngineer", "Maintenance Engineer", "Assets + maintenance workflows"),
    ("QualityEngineer", "Quality Engineer", "Quality and test evidence"),
    ("ComplianceOfficer", "Compliance Officer", "Compliance and certifications"),
    ("SystemAdmin", "System Admin", "Full administrative access"),
)


def seed_product_line(session: Session) -> ProductLine:
    """Ensure the ABB LV Motors product line placeholder exists."""
    existing = session.scalars(
        select(ProductLine).where(ProductLine.code == ABB_LV_MOTORS_CODE)
    ).first()
    if existing is not None:
        return existing

    row = ProductLine(
        code=ABB_LV_MOTORS_CODE,
        name=ABB_LV_MOTORS_NAME,
        oem="ABB",
        description="Hackathon hero product line placeholder for ABB LV Motors corpus.",
    )
    session.add(row)
    session.flush()
    return row


def seed_roles(session: Session) -> list[Role]:
    """Ensure Architecture RBAC role stubs exist (auth wiring in Milestone 1.4)."""
    created: list[Role] = []
    for code, name, description in DEFAULT_ROLES:
        existing = session.scalars(select(Role).where(Role.code == code)).first()
        if existing is not None:
            created.append(existing)
            continue
        role = Role(code=code, name=name, description=description)
        session.add(role)
        created.append(role)
    session.flush()
    return created


def run_seed(session: Session) -> dict[str, str]:
    """Run all seed hooks; returns a small status map."""
    product_line = seed_product_line(session)
    roles = seed_roles(session)
    return {
        "product_line": product_line.code,
        "roles_count": str(len(roles)),
    }
