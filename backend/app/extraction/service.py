"""Extraction persistence + orchestration (Milestone 2.2)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.db.models.documents import Document
from app.db.models.extraction import (
    ExtractionCandidate,
    PerformanceTestReport,
    ReviewQueueItem,
    TestMeasurement,
)
from app.db.models.parsing import DocumentParseResult
from app.db.repositories.base import BaseRepository
from app.documents.linking import StubLinker
from app.extraction.extractors import ExtractionBundle, run_extractors
from app.observability import get_logger

_logger = get_logger(__name__)

REVIEW_CONFIDENCE_THRESHOLD = 0.7


class ExtractionCandidateRepository(BaseRepository[ExtractionCandidate]):
    model = ExtractionCandidate

    def list_for_document(self, document_id: str) -> list[ExtractionCandidate]:
        stmt = (
            select(ExtractionCandidate)
            .where(ExtractionCandidate.document_id == document_id)
            .order_by(ExtractionCandidate.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())


class ReviewQueueRepository(BaseRepository[ReviewQueueItem]):
    model = ReviewQueueItem

    def list_open(self, *, limit: int = 100) -> list[ReviewQueueItem]:
        stmt = (
            select(ReviewQueueItem)
            .where(ReviewQueueItem.status == "open")
            .order_by(ReviewQueueItem.priority.asc(), ReviewQueueItem.created_at.asc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())


class TestMeasurementRepository(BaseRepository[TestMeasurement]):
    model = TestMeasurement

    def list_for_document(self, document_id: str) -> list[TestMeasurement]:
        stmt = select(TestMeasurement).where(TestMeasurement.document_id == document_id)
        return list(self.session.scalars(stmt).all())


class ExtractionService:
    """Run extractors against the latest parse result and persist candidates."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.candidates = ExtractionCandidateRepository(session)
        self.review = ReviewQueueRepository(session)
        self.measurements = TestMeasurementRepository(session)
        self.linker = StubLinker(session)

    def extract_document(self, document_id: str) -> dict[str, Any]:
        document = self._get_document(document_id)
        parse = self._latest_parse(document_id)
        catalog = document.catalog_entry

        filename = catalog.name if catalog else document.title
        folder_path = catalog.folder_path if catalog else ""
        doc_category = (
            catalog.doc_category
            if catalog and catalog.doc_category
            else document.doc_type
        )
        full_text = (parse.full_text if parse else "") or ""
        tables = list((parse.tables if parse else None) or [])
        if not full_text and parse and parse.pages:
            full_text = "\n\n".join(
                str(p.get("text") or "") for p in parse.pages if isinstance(p, dict)
            )

        bundle = run_extractors(
            filename=filename or "",
            folder_path=folder_path or "",
            full_text=full_text,
            tables=tables,
            doc_category=doc_category,
        )

        # Clear previous candidates / measurements for re-run idempotency
        self._clear_previous(document_id)

        saved_candidates = self._persist_candidates(
            document_id=document.id,
            parse_result_id=parse.id if parse else None,
            bundle=bundle,
        )
        report, saved_measurements = self._persist_measurements(
            document=document,
            bundle=bundle,
            doc_category=doc_category,
        )

        # Enrich stubs from high-confidence drawing / motor entities
        drawing = next(
            (
                c.normalized_value or c.value
                for c in saved_candidates
                if c.entity_type == "drawing_number" and c.confidence >= 0.75
            ),
            catalog.drawing_number if catalog else None,
        )
        motor = next(
            (
                c.normalized_value or c.value
                for c in saved_candidates
                if c.entity_type == "motor_type_code" and c.confidence >= 0.75
            ),
            catalog.motor_type_code if catalog else None,
        )
        if catalog:
            if drawing and not catalog.drawing_number:
                catalog.drawing_number = drawing
            if motor and not catalog.motor_type_code:
                catalog.motor_type_code = motor
        self.linker.link_document(
            document,
            drawing_number=drawing,
            motor_type_code=motor,
            asset_domain=None,
        )

        document.status = "extracted"
        self.session.flush()

        _logger.info(
            "extraction complete",
            extra={
                "document_id": document.id,
                "candidate_count": len(saved_candidates),
                "measurement_count": len(saved_measurements),
            },
        )

        return {
            "document_id": document.id,
            "candidate_count": len(saved_candidates),
            "measurement_count": len(saved_measurements),
            "review_queued": sum(
                1 for c in saved_candidates if c.status == "needs_review"
            ),
            "report_id": report.id if report else None,
            "candidates": [self._candidate_dict(c) for c in saved_candidates],
            "measurements": [self._measurement_dict(m) for m in saved_measurements],
        }

    def get_candidates(self, document_id: str) -> list[dict[str, Any]]:
        return [
            self._candidate_dict(c)
            for c in self.candidates.list_for_document(document_id)
        ]

    def get_measurements(self, document_id: str) -> list[dict[str, Any]]:
        return [
            self._measurement_dict(m)
            for m in self.measurements.list_for_document(document_id)
        ]

    def list_review_queue(self, *, limit: int = 100) -> list[dict[str, Any]]:
        items = self.review.list_open(limit=limit)
        out: list[dict[str, Any]] = []
        for item in items:
            out.append(
                {
                    "id": item.id,
                    "candidate_id": item.candidate_id,
                    "document_id": item.document_id,
                    "priority": item.priority,
                    "status": item.status,
                    "reason": item.reason,
                    "created_at": item.created_at,
                }
            )
        return out

    def _persist_candidates(
        self,
        *,
        document_id: str,
        parse_result_id: str | None,
        bundle: ExtractionBundle,
    ) -> list[ExtractionCandidate]:
        saved: list[ExtractionCandidate] = []
        for entity in bundle.entities:
            status = "accepted"
            if entity.confidence < REVIEW_CONFIDENCE_THRESHOLD:
                status = "needs_review"
            row = ExtractionCandidate(
                document_id=document_id,
                parse_result_id=parse_result_id,
                entity_type=entity.entity_type,
                value=entity.value,
                normalized_value=entity.normalized_value,
                confidence=entity.confidence,
                status=status,
                source=entity.source,
                page=entity.page,
                payload=entity.payload or {},
            )
            self.session.add(row)
            self.session.flush()
            if status == "needs_review":
                self.session.add(
                    ReviewQueueItem(
                        candidate_id=row.id,
                        document_id=document_id,
                        priority=int((1.0 - entity.confidence) * 100),
                        status="open",
                        reason=f"confidence {entity.confidence:.2f} below threshold",
                    )
                )
            saved.append(row)
        self.session.flush()
        return saved

    def _persist_measurements(
        self,
        *,
        document: Document,
        bundle: ExtractionBundle,
        doc_category: str | None,
    ) -> tuple[PerformanceTestReport | None, list[TestMeasurement]]:
        if not bundle.measurements and doc_category not in {"test_report", "checklist"}:
            return None, []

        catalog = document.catalog_entry
        report = PerformanceTestReport(
            document_id=document.id,
            motor_type_code=catalog.motor_type_code if catalog else None,
            drawing_number=catalog.drawing_number if catalog else None,
            standard=bundle.standard,
            serial_number=bundle.serial_number,
            status="extracted",
            extra_metadata={"measurement_count": len(bundle.measurements)},
        )
        self.session.add(report)
        self.session.flush()

        saved: list[TestMeasurement] = []
        for m in bundle.measurements:
            row = TestMeasurement(
                report_id=report.id,
                document_id=document.id,
                parameter=m.parameter,
                unit=m.unit,
                rated_value=m.rated_value,
                measured_value=m.measured_value,
                numeric_value=m.numeric_value,
                page=m.page,
                source_table_index=m.source_table_index,
                extra_metadata={"confidence": m.confidence},
            )
            self.session.add(row)
            saved.append(row)
        self.session.flush()
        return report, saved

    def _clear_previous(self, document_id: str) -> None:
        existing = self.candidates.list_for_document(document_id)
        for cand in existing:
            q = self.session.scalars(
                select(ReviewQueueItem).where(ReviewQueueItem.candidate_id == cand.id)
            ).first()
            if q:
                self.session.delete(q)
            self.session.delete(cand)

        report = self.session.scalars(
            select(PerformanceTestReport).where(
                PerformanceTestReport.document_id == document_id
            )
        ).first()
        if report:
            for m in self.measurements.list_for_document(document_id):
                self.session.delete(m)
            self.session.delete(report)
        self.session.flush()

    def _get_document(self, document_id: str) -> Document:
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.catalog_entry))
        )
        document = self.session.scalars(stmt).first()
        if document is None:
            raise NotFoundError(
                "Document not found", details={"document_id": document_id}
            )
        return document

    def _latest_parse(self, document_id: str) -> DocumentParseResult | None:
        stmt = (
            select(DocumentParseResult)
            .where(DocumentParseResult.document_id == document_id)
            .order_by(DocumentParseResult.created_at.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    @staticmethod
    def _candidate_dict(row: ExtractionCandidate) -> dict[str, Any]:
        return {
            "id": row.id,
            "document_id": row.document_id,
            "entity_type": row.entity_type,
            "value": row.value,
            "normalized_value": row.normalized_value,
            "confidence": row.confidence,
            "status": row.status,
            "source": row.source,
            "page": row.page,
            "payload": dict(row.payload or {}),
        }

    @staticmethod
    def _measurement_dict(row: TestMeasurement) -> dict[str, Any]:
        return {
            "id": row.id,
            "document_id": row.document_id,
            "report_id": row.report_id,
            "parameter": row.parameter,
            "unit": row.unit,
            "rated_value": row.rated_value,
            "measured_value": row.measured_value,
            "numeric_value": row.numeric_value,
            "page": row.page,
        }
