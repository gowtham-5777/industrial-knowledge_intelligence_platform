"""Shared query helpers: motor <-> document/drawing/asset relationships.

Centralizes the joins used by timeline, summary, health, recommendations,
and motor360 so each intelligence service does not re-derive the same
motor-to-document linkage logic.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.db.models.documents import Document, DocumentAssetLink, DocumentCatalog
from app.db.models.drawings import DocumentDrawingLink, DrawingNumber
from app.db.models.motors import MotorModel
from app.db.repositories.motors import MotorModelRepository


def resolve_motor_model(session: Session, motor_id: str) -> MotorModel:
    """Resolve a motor by primary-key id first, falling back to its code."""
    repo = MotorModelRepository(session)
    model = repo.get_by_id(motor_id) or repo.get_by_code(motor_id)
    if model is None:
        raise NotFoundError(
            f"Motor not found: {motor_id}",
            error_code="ASSET_NOT_FOUND",
        )
    return model


def get_linked_documents(session: Session, model: MotorModel) -> list[Document]:
    """Documents linked via asset OR catalog motor_type_code."""
    docs: list[Document] = []
    seen: set[str] = set()
    if model.asset_id:
        stmt = (
            select(Document)
            .join(DocumentAssetLink, DocumentAssetLink.document_id == Document.id)
            .where(DocumentAssetLink.asset_id == model.asset_id)
            .options(selectinload(Document.catalog_entry))
            .order_by(Document.created_at.asc())
        )
        for doc in session.scalars(stmt).all():
            docs.append(doc)
            seen.add(doc.id)
    more = session.scalars(
        select(Document)
        .join(Document.catalog_entry)
        .where(DocumentCatalog.motor_type_code == model.code)
        .options(selectinload(Document.catalog_entry))
    ).all()
    for doc in more:
        if doc.id not in seen:
            docs.append(doc)
    return docs


def get_catalog_entries_for_code(session: Session, code: str) -> list[DocumentCatalog]:
    """Discovery-pass catalog rows matching the motor's type code (no Document yet)."""
    stmt = (
        select(DocumentCatalog)
        .where(DocumentCatalog.motor_type_code == code)
        .order_by(DocumentCatalog.discovered_at.asc())
    )
    return list(session.scalars(stmt).all())


def get_drawing_numbers_for_motor(
    session: Session, model: MotorModel
) -> list[DrawingNumber]:
    """Distinct DrawingNumber rows referenced by the motor's linked documents."""
    documents = get_linked_documents(session, model)
    doc_ids = [d.id for d in documents]
    catalog_numbers = {
        d.catalog_entry.drawing_number
        for d in documents
        if d.catalog_entry and d.catalog_entry.drawing_number
    }
    if not doc_ids and not catalog_numbers:
        return []
    seen: dict[str, DrawingNumber] = {}
    if doc_ids:
        stmt = (
            select(DrawingNumber)
            .join(
                DocumentDrawingLink,
                DocumentDrawingLink.drawing_number_id == DrawingNumber.id,
            )
            .where(DocumentDrawingLink.document_id.in_(doc_ids))
        )
        for row in session.scalars(stmt).all():
            seen[row.id] = row
    if catalog_numbers:
        stmt = select(DrawingNumber).where(
            DrawingNumber.normalized.in_({n.upper() for n in catalog_numbers})
        )
        for row in session.scalars(stmt).all():
            seen[row.id] = row
    return list(seen.values())


def get_related_motor_models(
    session: Session, model: MotorModel, *, limit: int = 10
) -> list[MotorModel]:
    """Other motors sharing the same family or a drawing number with this motor."""
    related: dict[str, MotorModel] = {}

    if model.family_id:
        stmt = (
            select(MotorModel)
            .where(MotorModel.family_id == model.family_id)
            .where(MotorModel.id != model.id)
            .options(selectinload(MotorModel.family))
            .limit(limit)
        )
        for row in session.scalars(stmt).all():
            related[row.id] = row

    drawings = get_drawing_numbers_for_motor(session, model)
    if drawings:
        drawing_ids = [d.id for d in drawings]
        doc_ids_stmt = select(DocumentDrawingLink.document_id).where(
            DocumentDrawingLink.drawing_number_id.in_(drawing_ids)
        )
        doc_ids = [r for r in session.scalars(doc_ids_stmt).all()]
        if doc_ids:
            asset_ids_stmt = select(DocumentAssetLink.asset_id).where(
                DocumentAssetLink.document_id.in_(doc_ids)
            )
            asset_ids = {
                a for a in session.scalars(asset_ids_stmt).all() if a != model.asset_id
            }
            if asset_ids:
                stmt = (
                    select(MotorModel)
                    .where(MotorModel.asset_id.in_(asset_ids))
                    .where(MotorModel.id != model.id)
                    .options(selectinload(MotorModel.family))
                    .limit(limit)
                )
                for row in session.scalars(stmt).all():
                    related[row.id] = row

    return list(related.values())[:limit]
