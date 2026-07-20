"""Asset lifecycle timeline builder (Phase 3)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models.motors import MotorModel, MotorTimelineEvent
from app.motors.documents import (
    get_catalog_entries_for_code,
    get_linked_documents,
    resolve_motor_model,
)
from app.observability import get_logger
from app.timeline.schemas import TimelineEventOut, TimelineOut

_logger = get_logger(__name__)

_CATEGORY_LABELS: dict[str, str] = {
    "datasheet": "Datasheet",
    "test_report": "Test report",
    "checklist": "Checklist",
    "certificate": "Certification",
    "manual": "Manual",
    "sop": "SOP",
    "drawing": "Drawing",
    "drawing_dimension": "Dimension drawing",
    "drawing_outline": "Outline drawing",
    "drawing_cad": "CAD model",
    "drawing_shaft": "Shaft drawing",
    "drawing_connection": "Connection diagram",
    "drawing_mechanical": "Mechanical drawing",
    "drawing_terminal": "Terminal box drawing",
    "regulation": "Regulation",
    "safety": "Safety document",
    "sensor": "Sensor document",
    "maintenance": "Maintenance record",
    "work_order": "Work order",
    "asset_register": "Asset register entry",
}


def _label(category: str | None) -> str:
    if not category:
        return "Document"
    return _CATEGORY_LABELS.get(category, category.replace("_", " ").title())


def _ensure_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class TimelineService:
    """Builds and serves the lifecycle timeline for a single motor."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def build_timeline(self, motor_id: str) -> TimelineOut:
        model = resolve_motor_model(self.session, motor_id)
        self._rebuild(model)
        self.session.commit()
        _logger.info(
            "timeline rebuilt",
            extra={"motor_id": model.id, "motor_code": model.code},
        )
        return self.list_events(model.id)

    def list_events(self, motor_id: str) -> TimelineOut:
        model = resolve_motor_model(self.session, motor_id)
        stmt = (
            select(MotorTimelineEvent)
            .where(MotorTimelineEvent.model_id == model.id)
            .order_by(MotorTimelineEvent.event_at.asc())
        )
        rows = list(self.session.scalars(stmt).all())
        if not rows:
            # Idempotent: build on first read so the timeline is never empty.
            self._rebuild(model)
            self.session.commit()
            rows = list(self.session.scalars(stmt).all())
        return TimelineOut(
            motor_id=model.id,
            items=[TimelineEventOut.model_validate(r) for r in rows],
            total=len(rows),
        )

    def _rebuild(self, model: MotorModel) -> None:
        """Idempotent rebuild: clear this motor's events, then re-derive them."""
        self.session.execute(
            delete(MotorTimelineEvent).where(MotorTimelineEvent.model_id == model.id)
        )

        events: list[MotorTimelineEvent] = []

        registered_at = _ensure_aware(model.created_at) or datetime.now(UTC)
        events.append(
            MotorTimelineEvent(
                event_type="motor_registered",
                title=f"{model.name} registered in asset registry",
                description=f"Motor code {model.code} added to the registry.",
                event_at=registered_at,
                is_estimated=False,
                document_id=None,
                model_id=model.id,
            )
        )

        documents = get_linked_documents(self.session, model)
        covered_catalog_ids: set[str] = set()
        for document in documents:
            catalog = document.catalog_entry
            if catalog is not None:
                covered_catalog_ids.add(catalog.id)
            category = catalog.doc_category if catalog else document.doc_type
            event_at = (
                (_ensure_aware(catalog.discovered_at) if catalog else None)
                or _ensure_aware(document.created_at)
                or datetime.now(UTC)
            )
            is_estimated = not (catalog and catalog.discovered_at)
            events.append(
                MotorTimelineEvent(
                    event_type=category or "document",
                    title=f"{_label(category)} added: {document.title}",
                    description=(
                        f"Document status: {document.status}."
                        + (
                            f" Drawing {catalog.drawing_number}."
                            if catalog and catalog.drawing_number
                            else ""
                        )
                    ),
                    event_at=event_at,
                    is_estimated=is_estimated,
                    document_id=document.id,
                    model_id=model.id,
                )
            )

        catalog_entries = get_catalog_entries_for_code(self.session, model.code)
        for catalog in catalog_entries:
            if catalog.id in covered_catalog_ids:
                continue
            event_at = (
                _ensure_aware(catalog.discovered_at)
                or _ensure_aware(catalog.created_at)
                or datetime.now(UTC)
            )
            events.append(
                MotorTimelineEvent(
                    event_type=f"discovered_{catalog.doc_category or 'document'}",
                    title=f"{_label(catalog.doc_category)} discovered: {catalog.name}",
                    description=(
                        "Catalog discovery only — not yet ingested as a document."
                    ),
                    event_at=event_at,
                    is_estimated=True,
                    document_id=None,
                    model_id=model.id,
                )
            )

        events.sort(key=lambda e: e.event_at)
        for event in events:
            self.session.add(event)
