"""Skeleton asset / drawing stub linking for catalog documents."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models.assets import Asset
from app.db.models.documents import Document
from app.db.models.drawings import DrawingNumber
from app.db.repositories.assets import AssetRepository
from app.db.repositories.documents import (
    DocumentAssetLinkRepository,
    DrawingNumberRepository,
)


@dataclass(slots=True)
class StubLinkResult:
    drawing: DrawingNumber | None = None
    assets: list[Asset] | None = None

    def __post_init__(self) -> None:
        if self.assets is None:
            self.assets = []


class StubLinker:
    """Create drawing-number + asset stubs and link them to a document."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.drawings = DrawingNumberRepository(session)
        self.assets = AssetRepository(session)
        self.asset_links = DocumentAssetLinkRepository(session)

    def link_document(
        self,
        document: Document,
        *,
        drawing_number: str | None = None,
        motor_type_code: str | None = None,
        asset_domain: str | None = None,
    ) -> StubLinkResult:
        result = StubLinkResult()

        if drawing_number:
            drawing = self.drawings.get_or_create_stub(drawing_number)
            self.drawings.link_document(
                document_id=document.id,
                drawing=drawing,
            )
            result.drawing = drawing
            # Drawing number also seeds a lightweight asset stub for explorer demos
            tag = f"drawing:{drawing.normalized}"
            asset = self.assets.get_or_create_stub(
                asset_type=_domain_to_asset_type(asset_domain),
                name=drawing.normalized,
                asset_tag=tag,
                description="Stub from drawing number",
            )
            self.asset_links.link(
                document_id=document.id,
                asset_id=asset.id,
                link_type="drawing_number",
            )
            result.assets.append(asset)

        if motor_type_code:
            tag = f"motor:{motor_type_code.strip()}"
            asset = self.assets.get_or_create_stub(
                asset_type="motor",
                name=motor_type_code.strip(),
                asset_tag=tag,
                description="Stub from motor type / pack folder",
            )
            self.asset_links.link(
                document_id=document.id,
                asset_id=asset.id,
                link_type="motor_type",
            )
            result.assets.append(asset)

        return result

    def ensure_drawing_stub(self, drawing_number: str) -> DrawingNumber:
        """Registry stub even before a Document row exists (discovery)."""
        return self.drawings.get_or_create_stub(drawing_number)

    def ensure_motor_stub(self, motor_type_code: str) -> Asset:
        tag = f"motor:{motor_type_code.strip()}"
        return self.assets.get_or_create_stub(
            asset_type="motor",
            name=motor_type_code.strip(),
            asset_tag=tag,
            description="Stub from discovery motor metadata",
        )


def _domain_to_asset_type(asset_domain: str | None) -> str:
    if not asset_domain:
        return "motor"
    key = asset_domain.strip().lower().rstrip("s")
    known = {
        "motor": "motor",
        "pump": "pump",
        "valve": "valve",
        "drive": "drive",
        "gearbox": "gearbox",
        "compressor": "compressor",
        "transformer": "transformer",
        "generator": "generator",
    }
    return known.get(key, "motor")
