"""Drawing number cross-reference explorer (Phase 3)."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.db.models.assets import Asset
from app.db.models.documents import Document, DocumentAssetLink
from app.db.models.drawings import DocumentDrawingLink, DrawingNumber
from app.db.models.motors import MotorModel
from app.db.repositories.documents import DrawingNumberRepository
from app.drawings.schemas import (
    DrawingCrossRefOut,
    DrawingDocumentOut,
    DrawingLinkedAssetOut,
    DrawingLinkedMotorOut,
    DrawingListItemOut,
    DrawingListOut,
)


class DrawingExplorerService:
    """List/search drawing numbers and build their cross-reference bundle."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.drawings = DrawingNumberRepository(session)

    def list_drawings(
        self,
        *,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> DrawingListOut:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        stmt = select(DrawingNumber).options(selectinload(DrawingNumber.document_links))
        count_stmt = select(DrawingNumber)
        if q:
            like = f"%{q.strip()}%"
            filt = or_(
                DrawingNumber.drawing_number.ilike(like),
                DrawingNumber.description.ilike(like),
            )
            stmt = stmt.where(filt)
            count_stmt = count_stmt.where(filt)

        total = len(list(self.session.scalars(count_stmt).all()))
        stmt = stmt.order_by(DrawingNumber.drawing_number.asc()).offset(offset).limit(limit)
        rows = list(self.session.scalars(stmt).all())
        items = [
            DrawingListItemOut(
                id=row.id,
                drawing_number=row.drawing_number,
                normalized=row.normalized,
                description=row.description,
                document_count=len(row.document_links or []),
            )
            for row in rows
        ]
        return DrawingListOut(items=items, total=total, limit=limit, offset=offset)

    def get_drawing(self, drawing_number: str) -> DrawingCrossRefOut:
        drawing = self.drawings.get_by_number(drawing_number)
        if drawing is None:
            raise NotFoundError(
                f"Drawing number not found: {drawing_number}",
                error_code="ASSET_NOT_FOUND",
            )

        links = list(
            self.session.scalars(
                select(DocumentDrawingLink)
                .where(DocumentDrawingLink.drawing_number_id == drawing.id)
                .options(selectinload(DocumentDrawingLink.document))
            ).all()
        )
        document_ids = [link.document_id for link in links]
        sheet_by_doc = {link.document_id: link.sheet_id for link in links}

        documents: list[DrawingDocumentOut] = []
        if document_ids:
            doc_rows = self.session.scalars(
                select(Document).where(Document.id.in_(document_ids))
            ).all()
            for doc in doc_rows:
                documents.append(
                    DrawingDocumentOut(
                        id=doc.id,
                        title=doc.title,
                        doc_category=doc.doc_type,
                        status=doc.status,
                        sheet_id=sheet_by_doc.get(doc.id),
                    )
                )

        linked_motors: list[DrawingLinkedMotorOut] = []
        linked_assets: list[DrawingLinkedAssetOut] = []
        if document_ids:
            asset_link_rows = self.session.scalars(
                select(DocumentAssetLink).where(
                    DocumentAssetLink.document_id.in_(document_ids)
                )
            ).all()
            asset_ids = {link.asset_id for link in asset_link_rows}
            if asset_ids:
                assets = self.session.scalars(
                    select(Asset).where(Asset.id.in_(asset_ids))
                ).all()
                for asset in assets:
                    linked_assets.append(
                        DrawingLinkedAssetOut(
                            id=asset.id,
                            asset_type=asset.asset_type,
                            name=asset.name,
                            asset_tag=asset.asset_tag,
                        )
                    )
                motors = self.session.scalars(
                    select(MotorModel).where(MotorModel.asset_id.in_(asset_ids))
                ).all()
                for motor in motors:
                    linked_motors.append(
                        DrawingLinkedMotorOut(id=motor.id, code=motor.code, name=motor.name)
                    )

        return DrawingCrossRefOut(
            id=drawing.id,
            drawing_number=drawing.drawing_number,
            normalized=drawing.normalized,
            description=drawing.description,
            documents=documents,
            linked_motors=linked_motors,
            linked_assets=linked_assets,
        )
