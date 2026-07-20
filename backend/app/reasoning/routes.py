"""Maintenance + RCA API routes (Milestones 4.3–4.4)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.core.dependencies import DbSessionDep, RequestIdDep
from app.core.responses import success_envelope
from app.reasoning.maintenance import MaintenanceService
from app.reasoning.rca import RcaService

router = APIRouter(tags=["Maintenance"], dependencies=[Depends(get_current_user)])


def get_maintenance(session: DbSessionDep) -> MaintenanceService:
    return MaintenanceService(session)


def get_rca(session: DbSessionDep) -> RcaService:
    return RcaService(session)


MaintenanceDep = Annotated[MaintenanceService, Depends(get_maintenance)]
RcaDep = Annotated[RcaService, Depends(get_rca)]


@router.get(
    "/maintenance/{motor_id}",
    summary="Test metric trends + anomaly patterns for a motor",
)
def maintenance_for_motor(
    motor_id: str,
    service: MaintenanceDep,
    request_id: RequestIdDep,
) -> dict:
    data = service.analyze(motor_id)
    return success_envelope(data.model_dump(), request_id=request_id)


@router.get(
    "/rca/{motor_id}",
    summary="Test anomaly RCA workspace (5-Why + similar reports)",
    tags=["RCA"],
)
def rca_for_motor(
    motor_id: str,
    service: RcaDep,
    request_id: RequestIdDep,
    parameter: Annotated[str | None, Query()] = None,
) -> dict:
    data = service.analyze(motor_id, parameter=parameter)
    return success_envelope(data.model_dump(), request_id=request_id)
