"""Seed hooks for baseline SoR data (idempotent)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.service import ensure_user_with_role
from app.db.models.organization import ProductLine
from app.db.models.system import Role

ABB_LV_MOTORS_CODE = "ABB_LV_MOTORS"
ABB_LV_MOTORS_NAME = "ABB Low Voltage Motors"

# Architecture §11 RBAC roles (+ QualityEngineer kept from earlier seed for continuity)
DEFAULT_ROLES: tuple[tuple[str, str, str], ...] = (
    ("PlantOperator", "Plant Operator", "Read assets, docs, copilot (own plant)"),
    (
        "MaintenanceEngineer",
        "Maintenance Engineer",
        "Upload docs, confirm extractions, maintenance workflows",
    ),
    (
        "ReliabilityEngineer",
        "Reliability Engineer",
        "RCA workspace, graph edit suggestions",
    ),
    ("QualityEngineer", "Quality Engineer", "Quality and test evidence"),
    (
        "ComplianceOfficer",
        "Compliance Officer",
        "Compliance dashboard, audit exports",
    ),
    ("PlantManager", "Plant Manager", "Executive dashboard, cross-area read"),
    ("SystemAdmin", "System Admin", "Full admin, user management"),
    ("Auditor", "Auditor", "Read-only + audit logs"),
)

# Demo users for hackathon JWT seed auth (change passwords in real deployments)
SEED_USERS: tuple[tuple[str, str, str, str], ...] = (
    (
        "admin@example.com",
        "System Admin",
        "ChangeMeAdmin!",
        "SystemAdmin",
    ),
    (
        "operator@example.com",
        "Plant Operator",
        "ChangeMeOperator!",
        "PlantOperator",
    ),
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
    """Ensure Architecture RBAC role rows exist."""
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


def seed_users(session: Session) -> list[str]:
    """Ensure JWT seed demo users exist with role links."""
    emails: list[str] = []
    for email, display_name, password, role_code in SEED_USERS:
        user = ensure_user_with_role(
            session,
            email=email,
            display_name=display_name,
            password=password,
            role_code=role_code,
        )
        emails.append(user.email)
    return emails


def run_seed(session: Session) -> dict[str, str]:
    """Run all seed hooks; returns a small status map."""
    product_line = seed_product_line(session)
    roles = seed_roles(session)
    users = seed_users(session)
    return {
        "product_line": product_line.code,
        "roles_count": str(len(roles)),
        "users_count": str(len(users)),
    }
