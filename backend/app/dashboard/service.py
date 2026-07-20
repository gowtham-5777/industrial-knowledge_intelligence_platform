"""Fleet dashboard KPI aggregation (Phase 3)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.dashboard.schemas import DashboardKpisOut
from app.db.models.documents import Document
from app.db.models.motors import MotorModel
from app.db.repositories.documents import DocumentCatalogRepository, DocumentRepository
from app.health.scoring import HealthScoringService
from app.indexing.status_service import IndexingStatusService
from app.motors.documents import resolve_motor_model
from app.motors.hero import HERO_MOTOR_CODE
from app.observability import get_logger

_logger = get_logger(__name__)

_INDEXED_STATUSES = ("ready", "parsed", "indexed")


class DashboardService:
    """Aggregate catalog/document/motor/indexing counters for the fleet view."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.catalog_repo = DocumentCatalogRepository(session)
        self.document_repo = DocumentRepository(session)

    def get_kpis(self) -> DashboardKpisOut:
        catalog_count = self.catalog_repo.count()
        document_count = self.document_repo.count()
        indexed_count = (
            self.session.scalar(
                select(func.count())
                .select_from(Document)
                .where(Document.status.in_(_INDEXED_STATUSES))
            )
            or 0
        )
        motor_count = (
            self.session.scalar(select(func.count()).select_from(MotorModel)) or 0
        )

        hero_health = None
        try:
            hero_model = resolve_motor_model(self.session, HERO_MOTOR_CODE)
            hero_health = HealthScoringService(self.session).get_latest(hero_model.id)
        except Exception as exc:  # noqa: BLE001
            _logger.info(
                "hero motor health unavailable for dashboard",
                extra={"error": str(exc)},
            )

        try:
            indexing_status = IndexingStatusService(self.session).status()
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "indexing status unavailable for dashboard",
                extra={"error": str(exc)},
            )
            indexing_status = None

        return DashboardKpisOut(
            catalog_count=catalog_count,
            document_count=document_count,
            indexed_count=int(indexed_count),
            motor_count=int(motor_count),
            hero_motor_code=HERO_MOTOR_CODE,
            hero_health=hero_health,
            indexing_status=indexing_status,
        )
