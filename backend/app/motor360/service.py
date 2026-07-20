"""Single-asset intelligence bundle aggregation (Phase 3)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.graph.subgraph import GraphSubgraphService
from app.health.scoring import HealthScoringService
from app.motor360.schemas import (
    DocumentPanel,
    DocumentPanelItem,
    Motor360Out,
    RelatedAssetOut,
)
from app.motors.documents import (
    get_drawing_numbers_for_motor,
    get_linked_documents,
    get_related_motor_models,
    resolve_motor_model,
)
from app.motors.service import MotorRegistryService
from app.observability import get_logger
from app.recommendations.service import RecommendationService
from app.summary.service import SummaryService
from app.timeline.service import TimelineService

_logger = get_logger(__name__)


class Motor360Service:
    """Aggregate registry + intelligence services into one response bundle."""

    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    def get_bundle(self, motor_id: str, *, refresh: bool = False) -> Motor360Out:
        model = resolve_motor_model(self.session, motor_id)

        motor_out = MotorRegistryService(self.session).get_motor(model.id)
        documents = self._document_panels(model.id)

        summary = SummaryService(self.session, self.settings).generate(
            model.id, force=refresh
        )
        health = (
            HealthScoringService(self.session).compute(model.id)
            if refresh
            else HealthScoringService(self.session).get_or_compute(model.id)
        )
        recommendations = RecommendationService(self.session, self.settings).generate(
            model.id, force=refresh
        )
        timeline = (
            TimelineService(self.session).build_timeline(model.id)
            if refresh
            else TimelineService(self.session).list_events(model.id)
        )
        related_assets = self._related_assets(model)
        subgraph = GraphSubgraphService(self.session).build(model.id)
        drawing_numbers = [
            d.drawing_number for d in get_drawing_numbers_for_motor(self.session, model)
        ]

        _logger.info(
            "motor360 bundle assembled",
            extra={"motor_id": model.id, "refresh": refresh},
        )
        return Motor360Out(
            motor=motor_out,
            documents=documents,
            summary=summary,
            health=health,
            recommendations=recommendations,
            timeline=timeline,
            related_assets=related_assets,
            subgraph=subgraph,
            drawing_numbers=drawing_numbers,
        )

    def _document_panels(self, motor_id: str) -> list[DocumentPanel]:
        model = resolve_motor_model(self.session, motor_id)
        documents = get_linked_documents(self.session, model)
        grouped: dict[str, list[DocumentPanelItem]] = {}
        for doc in documents:
            catalog = doc.catalog_entry
            category = (
                catalog.doc_category if catalog else doc.doc_type
            ) or "uncategorized"
            grouped.setdefault(category, []).append(
                DocumentPanelItem(
                    id=doc.id,
                    title=doc.title,
                    doc_category=category,
                    doc_subtype=catalog.doc_subtype if catalog else None,
                    status=doc.status,
                    drawing_number=catalog.drawing_number if catalog else None,
                    discovered_at=catalog.discovered_at if catalog else None,
                )
            )
        return [
            DocumentPanel(category=category, items=items)
            for category, items in sorted(grouped.items())
        ]

    def _related_assets(self, model) -> list[RelatedAssetOut]:  # noqa: ANN001
        related = get_related_motor_models(self.session, model, limit=8)
        out: list[RelatedAssetOut] = []
        for other in related:
            relation = (
                "same_family"
                if other.family_id == model.family_id
                else "shares_drawing"
            )
            out.append(
                RelatedAssetOut(
                    id=other.id,
                    code=other.code,
                    name=other.name,
                    relation=relation,
                )
            )
        return out
