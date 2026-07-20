"""Asset registry + motor explorer service (Milestones 3.1–3.2)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.models.assets import Asset
from app.db.models.documents import DocumentCatalog
from app.db.models.motors import MotorModel
from app.db.repositories.assets import AssetRepository
from app.db.repositories.motors import (
    MotorModelRepository,
    ensure_alias,
    ensure_family,
    ensure_motor_model,
    ensure_product_line,
    ensure_unit,
)
from app.db.seed import ABB_LV_MOTORS_CODE, ABB_LV_MOTORS_NAME
from app.motors.hero import (
    DEFAULT_FAMILY_CODE,
    DEFAULT_FAMILY_NAME,
    HERO_MOTOR_CODE,
    HERO_SPEC_HINTS,
    SUPPORTING_MOTOR_CODES,
)
from app.motors.schemas import (
    AssetTypeOut,
    HeroMotorsOut,
    MotorAliasOut,
    MotorEnrichRequest,
    MotorListOut,
    MotorModelOut,
)
from app.observability import get_logger

_logger = get_logger(__name__)


class MotorRegistryService:
    """Asset-agnostic registry specialized for motor hierarchy."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.models = MotorModelRepository(session)
        self.assets = AssetRepository(session)

    def list_asset_types(self) -> list[AssetTypeOut]:
        stmt = (
            select(Asset.asset_type, func.count())
            .group_by(Asset.asset_type)
            .order_by(Asset.asset_type)
        )
        rows = self.session.execute(stmt).all()
        return [AssetTypeOut(asset_type=t, count=int(c)) for t, c in rows]

    def list_assets(
        self, *, asset_type: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        stmt = select(Asset)
        if asset_type:
            stmt = stmt.where(Asset.asset_type == asset_type)
        stmt = stmt.offset(offset).limit(limit)
        return [
            {
                "id": a.id,
                "asset_type": a.asset_type,
                "name": a.name,
                "asset_tag": a.asset_tag,
                "status": a.status,
            }
            for a in self.session.scalars(stmt).all()
        ]

    def search_motors(
        self,
        *,
        q: str | None = None,
        frame_size: str | None = None,
        power_kw_min: float | None = None,
        power_kw_max: float | None = None,
        ie_class: str | None = None,
        family_code: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> MotorListOut:
        rows, total = self.models.search(
            q=q,
            frame_size=frame_size,
            power_kw_min=power_kw_min,
            power_kw_max=power_kw_max,
            ie_class=ie_class,
            family_code=family_code,
            limit=limit,
            offset=offset,
        )
        return MotorListOut(
            items=[self._to_out(m) for m in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_motor(self, motor_id: str) -> MotorModelOut:
        model = self.models.get_by_id(motor_id)
        if model is None:
            # Allow lookup by code as convenience
            model = self.models.get_by_code(motor_id)
        if model is None:
            raise NotFoundError(
                f"Motor not found: {motor_id}",
                error_code="ASSET_NOT_FOUND",
            )
        return self._to_out(model)

    def resolve_alias(self, alias: str) -> MotorModelOut | None:
        model = self.models.resolve_alias(alias)
        if model is None:
            model = self.models.get_by_code(alias)
        return self._to_out(model) if model else None

    def enrich_motor(self, motor_id: str, payload: MotorEnrichRequest) -> MotorModelOut:
        model = self.models.get_by_id(motor_id) or self.models.get_by_code(motor_id)
        if model is None:
            raise NotFoundError(
                f"Motor not found: {motor_id}",
                error_code="ASSET_NOT_FOUND",
            )
        if payload.name:
            model.name = payload.name
        if payload.frame_size is not None:
            model.frame_size = payload.frame_size
        if payload.power_kw is not None:
            model.power_kw = payload.power_kw
        if payload.voltage is not None:
            model.voltage = payload.voltage
        if payload.ie_class is not None:
            model.ie_class = payload.ie_class
        if payload.poles is not None:
            model.poles = payload.poles
        if payload.mounting is not None:
            model.mounting = payload.mounting
        if payload.cooling is not None:
            model.cooling = payload.cooling
        if payload.metadata:
            meta = dict(model.extra_metadata or {})
            meta.update(payload.metadata)
            model.extra_metadata = meta
        for alias in payload.aliases:
            ensure_alias(self.session, model=model, alias=alias)
        # Promote stub asset to active when enriched
        if model.asset_id:
            asset = self.assets.get(model.asset_id)
            if asset is not None and asset.status == "stub":
                asset.status = "active"
        self.session.flush()
        return self._to_out(model)

    def enrich_from_catalog(self) -> dict[str, Any]:
        """Create/update motor stubs from distinct catalog motor_type_code values."""
        codes = list(
            self.session.scalars(
                select(DocumentCatalog.motor_type_code)
                .where(DocumentCatalog.motor_type_code.is_not(None))
                .distinct()
            ).all()
        )
        product_line = ensure_product_line(
            self.session, ABB_LV_MOTORS_CODE, ABB_LV_MOTORS_NAME
        )
        family = ensure_family(
            self.session,
            product_line=product_line,
            code=DEFAULT_FAMILY_CODE,
            name=DEFAULT_FAMILY_NAME,
        )
        created = 0
        updated = 0
        for raw in codes:
            if not raw or not str(raw).strip():
                continue
            code = str(raw).strip()
            before = self.models.get_by_code(code)
            hints = HERO_SPEC_HINTS.get(code, {})
            ensure_motor_model(
                self.session,
                code=code,
                name=hints.get("name") or code,
                family=family,
                frame_size=hints.get("frame_size"),
                power_kw=hints.get("power_kw"),
                voltage=hints.get("voltage"),
                ie_class=hints.get("ie_class"),
                poles=hints.get("poles"),
                extra_metadata={"source": "catalog_enrichment"},
            )
            if before is None:
                created += 1
            else:
                updated += 1
        self.session.flush()
        _logger.info(
            "catalog motor enrichment complete",
            extra={"created_count": created, "updated_count": updated, "codes": len(codes)},
        )
        return {"codes_seen": len(codes), "created": created, "updated": updated}

    def confirm_hero_set(self) -> HeroMotorsOut:
        """Ensure hero + 4 supporting motors exist and are marked in metadata."""
        product_line = ensure_product_line(
            self.session, ABB_LV_MOTORS_CODE, ABB_LV_MOTORS_NAME
        )
        family = ensure_family(
            self.session,
            product_line=product_line,
            code=DEFAULT_FAMILY_CODE,
            name=DEFAULT_FAMILY_NAME,
        )
        confirmed_at = datetime.now(UTC)
        all_codes = (HERO_MOTOR_CODE, *SUPPORTING_MOTOR_CODES)
        outs: list[MotorModelOut] = []
        for code in all_codes:
            hints = HERO_SPEC_HINTS.get(code, {})
            aliases = list(hints.get("aliases") or [code])
            model = ensure_motor_model(
                self.session,
                code=code,
                name=hints.get("name") or code,
                family=family,
                frame_size=hints.get("frame_size"),
                power_kw=hints.get("power_kw"),
                voltage=hints.get("voltage"),
                ie_class=hints.get("ie_class"),
                poles=hints.get("poles"),
                extra_metadata={
                    "source": "hero_selection",
                    "is_hero": code == HERO_MOTOR_CODE,
                    "is_supporting": code in SUPPORTING_MOTOR_CODES,
                    "confirmed_at": confirmed_at.isoformat(),
                    "cooling": hints.get("cooling"),
                },
            )
            if hints.get("cooling") and not model.cooling:
                model.cooling = hints["cooling"]
            for alias in aliases:
                ensure_alias(self.session, model=model, alias=str(alias))
            if code == HERO_MOTOR_CODE:
                ensure_unit(
                    self.session,
                    model=model,
                    serial_number=f"HERO-{code}-SN001",
                )
            outs.append(self._to_out(model))
        self.session.flush()
        hero = next(m for m in outs if m.code == HERO_MOTOR_CODE)
        supporting = [m for m in outs if m.code != HERO_MOTOR_CODE]
        return HeroMotorsOut(
            hero=hero, supporting=supporting, confirmed_at=confirmed_at
        )

    def _to_out(self, model: MotorModel) -> MotorModelOut:
        family_code = None
        product_line_code = None
        if model.family is not None:
            family_code = model.family.code
            if model.family.product_line is not None:
                product_line_code = model.family.product_line.code
        meta = dict(model.extra_metadata or {})
        return MotorModelOut(
            id=model.id,
            code=model.code,
            name=model.name,
            frame_size=model.frame_size,
            power_kw=model.power_kw,
            voltage=model.voltage,
            ie_class=model.ie_class,
            poles=model.poles,
            mounting=model.mounting,
            cooling=model.cooling,
            asset_id=model.asset_id,
            family_id=model.family_id,
            family_code=family_code,
            product_line_code=product_line_code,
            aliases=[
                MotorAliasOut(alias=a.alias, alias_type=a.alias_type)
                for a in (model.aliases or [])
            ],
            is_hero=bool(meta.get("is_hero")) or model.code == HERO_MOTOR_CODE,
            is_supporting=bool(meta.get("is_supporting"))
            or model.code in SUPPORTING_MOTOR_CODES,
            metadata=meta or None,
        )
