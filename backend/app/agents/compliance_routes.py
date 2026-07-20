"""Compliance Intelligence Center APIs (Milestone 4.5)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.agents.compliance_engine import ComplianceEngine
from app.auth.dependencies import get_current_user
from app.core.dependencies import DbSessionDep, RequestIdDep
from app.core.responses import success_envelope

router = APIRouter(
    prefix="/compliance",
    tags=["Compliance"],
    dependencies=[Depends(get_current_user)],
)


def get_engine(session: DbSessionDep) -> ComplianceEngine:
    return ComplianceEngine(session)


EngineDep = Annotated[ComplianceEngine, Depends(get_engine)]


@router.get("/requirements", summary="List compliance checklist requirements")
def list_requirements(engine: EngineDep, request_id: RequestIdDep) -> dict:
    items = engine.list_requirements()
    return success_envelope({"items": items}, request_id=request_id)


@router.get("/motors/{motor_id}", summary="Compliance assessment for a motor")
def assess_motor(
    motor_id: str,
    engine: EngineDep,
    request_id: RequestIdDep,
) -> dict:
    data = engine.assess_motor(motor_id)
    return success_envelope(data, request_id=request_id)


@router.post(
    "/motors/{motor_id}/refresh",
    summary="Re-run compliance gap detection for a motor",
)
def refresh_motor(
    motor_id: str,
    engine: EngineDep,
    request_id: RequestIdDep,
) -> dict:
    data = engine.assess_motor(motor_id)
    return success_envelope(data, request_id=request_id)
