"""Motor hierarchy repository (Phase 3)."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.assets import Asset
from app.db.models.motors import MotorAlias, MotorFamily, MotorModel, MotorUnit
from app.db.models.organization import ProductLine
from app.db.repositories.base import BaseRepository


class MotorModelRepository(BaseRepository[MotorModel]):
    model = MotorModel

    def get_by_id(self, model_id: str) -> MotorModel | None:
        stmt = (
            select(MotorModel)
            .where(MotorModel.id == model_id)
            .options(
                selectinload(MotorModel.family).selectinload(MotorFamily.product_line),
                selectinload(MotorModel.aliases),
                selectinload(MotorModel.units),
            )
        )
        return self.session.scalars(stmt).first()

    def get_by_code(self, code: str) -> MotorModel | None:
        stmt = (
            select(MotorModel)
            .where(MotorModel.code == code)
            .options(
                selectinload(MotorModel.family),
                selectinload(MotorModel.aliases),
            )
        )
        return self.session.scalars(stmt).first()

    def get_by_asset_id(self, asset_id: str) -> MotorModel | None:
        stmt = select(MotorModel).where(MotorModel.asset_id == asset_id)
        return self.session.scalars(stmt).first()

    def resolve_alias(self, alias: str) -> MotorModel | None:
        stmt = (
            select(MotorModel)
            .join(MotorAlias)
            .where(MotorAlias.alias == alias)
            .options(selectinload(MotorModel.aliases))
        )
        return self.session.scalars(stmt).first()

    def search(
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
    ) -> tuple[list[MotorModel], int]:
        stmt = select(MotorModel).options(
            selectinload(MotorModel.family),
            selectinload(MotorModel.aliases),
        )
        count_stmt = select(MotorModel)

        if q:
            like = f"%{q.strip()}%"
            filt = or_(
                MotorModel.code.ilike(like),
                MotorModel.name.ilike(like),
                MotorModel.frame_size.ilike(like),
            )
            stmt = stmt.where(filt)
            count_stmt = count_stmt.where(filt)
        if frame_size:
            stmt = stmt.where(MotorModel.frame_size == frame_size)
            count_stmt = count_stmt.where(MotorModel.frame_size == frame_size)
        if ie_class:
            stmt = stmt.where(MotorModel.ie_class == ie_class)
            count_stmt = count_stmt.where(MotorModel.ie_class == ie_class)
        if power_kw_min is not None:
            stmt = stmt.where(MotorModel.power_kw >= power_kw_min)
            count_stmt = count_stmt.where(MotorModel.power_kw >= power_kw_min)
        if power_kw_max is not None:
            stmt = stmt.where(MotorModel.power_kw <= power_kw_max)
            count_stmt = count_stmt.where(MotorModel.power_kw <= power_kw_max)
        if family_code:
            stmt = stmt.join(MotorFamily).where(MotorFamily.code == family_code)
            count_stmt = count_stmt.join(MotorFamily).where(
                MotorFamily.code == family_code
            )

        total = len(list(self.session.scalars(count_stmt).all()))
        rows = list(self.session.scalars(stmt.offset(offset).limit(limit)).all())
        return rows, total


class MotorFamilyRepository(BaseRepository[MotorFamily]):
    model = MotorFamily

    def get_by_code(
        self, code: str, *, product_line_id: str | None = None
    ) -> MotorFamily | None:
        stmt = select(MotorFamily).where(MotorFamily.code == code)
        if product_line_id:
            stmt = stmt.where(MotorFamily.product_line_id == product_line_id)
        return self.session.scalars(stmt).first()


def ensure_product_line(session: Session, code: str, name: str) -> ProductLine:
    existing = session.scalars(
        select(ProductLine).where(ProductLine.code == code)
    ).first()
    if existing is not None:
        return existing
    row = ProductLine(code=code, name=name, oem="ABB")
    session.add(row)
    session.flush()
    return row


def ensure_family(
    session: Session,
    *,
    product_line: ProductLine,
    code: str,
    name: str,
) -> MotorFamily:
    repo = MotorFamilyRepository(session)
    existing = repo.get_by_code(code, product_line_id=product_line.id)
    if existing is not None:
        return existing
    family = MotorFamily(
        code=code,
        name=name,
        product_line_id=product_line.id,
        description=f"Motor family {name}",
    )
    session.add(family)
    session.flush()
    return family


def ensure_motor_model(
    session: Session,
    *,
    code: str,
    name: str | None = None,
    family: MotorFamily | None = None,
    frame_size: str | None = None,
    power_kw: float | None = None,
    voltage: str | None = None,
    ie_class: str | None = None,
    poles: int | None = None,
    asset: Asset | None = None,
    extra_metadata: dict | None = None,
) -> MotorModel:
    """Idempotent MotorModel + optional Asset link."""
    repo = MotorModelRepository(session)
    existing = repo.get_by_code(code)
    if existing is not None:
        changed = False
        if frame_size and not existing.frame_size:
            existing.frame_size = frame_size
            changed = True
        if power_kw is not None and existing.power_kw is None:
            existing.power_kw = power_kw
            changed = True
        if voltage and not existing.voltage:
            existing.voltage = voltage
            changed = True
        if ie_class and not existing.ie_class:
            existing.ie_class = ie_class
            changed = True
        if poles is not None and existing.poles is None:
            existing.poles = poles
            changed = True
        if asset is not None and existing.asset_id is None:
            existing.asset_id = asset.id
            changed = True
        if extra_metadata:
            meta = dict(existing.extra_metadata or {})
            meta.update(extra_metadata)
            existing.extra_metadata = meta
            changed = True
        if changed:
            session.flush()
        return existing

    if family is None:
        raise ValueError("family is required when creating a new MotorModel")

    if asset is None:
        from app.db.repositories.assets import AssetRepository

        assets = AssetRepository(session)
        asset = assets.get_or_create_stub(
            asset_type="motor",
            name=name or code,
            asset_tag=f"motor:{code}",
            description="Registry motor asset",
        )

    model = MotorModel(
        code=code,
        name=name or code,
        family_id=family.id,
        asset_id=asset.id,
        frame_size=frame_size,
        power_kw=power_kw,
        voltage=voltage,
        ie_class=ie_class,
        poles=poles,
        extra_metadata=extra_metadata,
    )
    session.add(model)
    session.flush()
    return model


def ensure_alias(
    session: Session, *, model: MotorModel, alias: str, alias_type: str = "name"
) -> MotorAlias:
    existing = session.scalars(
        select(MotorAlias).where(
            MotorAlias.model_id == model.id, MotorAlias.alias == alias
        )
    ).first()
    if existing is not None:
        return existing
    row = MotorAlias(alias=alias, alias_type=alias_type, model_id=model.id)
    session.add(row)
    session.flush()
    return row


def ensure_unit(
    session: Session,
    *,
    model: MotorModel,
    serial_number: str,
    status: str = "active",
) -> MotorUnit:
    existing = session.scalars(
        select(MotorUnit).where(MotorUnit.serial_number == serial_number)
    ).first()
    if existing is not None:
        return existing
    unit = MotorUnit(
        serial_number=serial_number,
        status=status,
        model_id=model.id,
    )
    session.add(unit)
    session.flush()
    return unit
