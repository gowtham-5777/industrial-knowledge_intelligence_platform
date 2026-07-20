"""Motor registry & explorer API routes (Milestones 3.1–3.2)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.core.dependencies import DbSessionDep, RequestIdDep
from app.core.responses import success_envelope
from app.motors.schemas import MotorEnrichRequest
from app.motors.service import MotorRegistryService

router = APIRouter(
    prefix="/motors",
    tags=["Motors"],
    dependencies=[Depends(get_current_user)],
)


def get_motor_service(session: DbSessionDep) -> MotorRegistryService:
    return MotorRegistryService(session)


MotorServiceDep = Annotated[MotorRegistryService, Depends(get_motor_service)]


@router.get(
    "/asset-types",
    summary="List asset type discriminator counts",
)
def list_asset_types(service: MotorServiceDep, request_id: RequestIdDep) -> dict:
    data = [t.model_dump() for t in service.list_asset_types()]
    return success_envelope({"items": data}, request_id=request_id)


@router.get(
    "/assets",
    summary="List assets (optional asset_type filter)",
)
def list_assets(
    service: MotorServiceDep,
    request_id: RequestIdDep,
    asset_type: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    items = service.list_assets(asset_type=asset_type, limit=limit, offset=offset)
    return success_envelope(
        {"items": items, "limit": limit, "offset": offset},
        request_id=request_id,
    )


@router.get(
    "",
    summary="List / search / filter motors",
)
def list_motors(
    service: MotorServiceDep,
    request_id: RequestIdDep,
    q: str | None = None,
    frame_size: str | None = None,
    power_kw_min: float | None = None,
    power_kw_max: float | None = None,
    ie_class: str | None = None,
    family_code: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    data = service.search_motors(
        q=q,
        frame_size=frame_size,
        power_kw_min=power_kw_min,
        power_kw_max=power_kw_max,
        ie_class=ie_class,
        family_code=family_code,
        limit=limit,
        offset=offset,
    )
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)


@router.get(
    "/aliases/resolve",
    summary="Resolve motor by alias or type code",
)
def resolve_alias(
    service: MotorServiceDep,
    request_id: RequestIdDep,
    q: Annotated[str, Query(min_length=1)],
) -> dict:
    matched = service.resolve_alias(q)
    return success_envelope(
        {
            "query": q,
            "matched": matched.model_dump(mode="json") if matched else None,
        },
        request_id=request_id,
    )


@router.post(
    "/enrich-from-catalog",
    summary="Catalog-driven motor stub enrichment",
)
def enrich_from_catalog(service: MotorServiceDep, request_id: RequestIdDep) -> dict:
    data = service.enrich_from_catalog()
    service.session.commit()
    return success_envelope(data, request_id=request_id)


@router.post(
    "/hero/confirm",
    summary="Select/confirm hero motor + 4 supporting motors",
)
def confirm_hero(service: MotorServiceDep, request_id: RequestIdDep) -> dict:
    data = service.confirm_hero_set()
    service.session.commit()
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)


@router.get(
    "/hero",
    summary="Get confirmed hero + supporting motors",
)
def get_hero(service: MotorServiceDep, request_id: RequestIdDep) -> dict:
    # Ensure set exists (idempotent)
    data = service.confirm_hero_set()
    service.session.commit()
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)


@router.get(
    "/{motor_id}",
    summary="Get motor model by id or code",
)
def get_motor(
    motor_id: str, service: MotorServiceDep, request_id: RequestIdDep
) -> dict:
    data = service.get_motor(motor_id)
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)


@router.patch(
    "/{motor_id}",
    summary="Enrich motor model fields / aliases",
)
def enrich_motor(
    motor_id: str,
    payload: MotorEnrichRequest,
    service: MotorServiceDep,
    request_id: RequestIdDep,
) -> dict:
    data = service.enrich_motor(motor_id, payload)
    service.session.commit()
    return success_envelope(data.model_dump(mode="json"), request_id=request_id)
