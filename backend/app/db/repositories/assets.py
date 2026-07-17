"""Asset registry repository."""

from __future__ import annotations

from sqlalchemy import select

from app.db.models.assets import Asset
from app.db.repositories.base import BaseRepository


class AssetRepository(BaseRepository[Asset]):
    model = Asset

    def get_by_tag(self, asset_tag: str) -> Asset | None:
        stmt = select(Asset).where(Asset.asset_tag == asset_tag)
        return self.session.scalars(stmt).first()

    def list_by_type(
        self, asset_type: str, *, limit: int = 100, offset: int = 0
    ) -> list[Asset]:
        stmt = (
            select(Asset)
            .where(Asset.asset_type == asset_type)
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def create(
        self,
        *,
        asset_type: str,
        name: str,
        asset_tag: str | None = None,
        plant_id: str | None = None,
        product_line_id: str | None = None,
        status: str = "active",
        description: str | None = None,
    ) -> Asset:
        asset = Asset(
            asset_type=asset_type,
            name=name,
            asset_tag=asset_tag,
            plant_id=plant_id,
            product_line_id=product_line_id,
            status=status,
            description=description,
        )
        return self.add(asset)
