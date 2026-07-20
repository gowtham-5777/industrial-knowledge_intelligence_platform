"""ORM models for the PostgreSQL system of record (Architecture §12)."""

from app.db.models.assets import Asset
from app.db.models.chunks import DocumentChunk, EmbeddingRegistry, RetrievalTrace
from app.db.models.documents import (
    Document,
    DocumentAssetLink,
    DocumentCatalog,
    DocumentVersion,
)
from app.db.models.drawings import DocumentDrawingLink, DrawingNumber
from app.db.models.extraction import (
    ExtractionCandidate,
    PerformanceTestReport,
    ReviewQueueItem,
    TestMeasurement,
)
from app.db.models.motors import (
    MotorAiSummary,
    MotorAlias,
    MotorFamily,
    MotorHealthScore,
    MotorModel,
    MotorRecommendation,
    MotorTimelineEvent,
    MotorUnit,
)
from app.db.models.organization import Plant, ProductLine
from app.db.models.parsing import DocumentParseResult
from app.db.models.processing import GdriveSyncState, IndexingJob
from app.db.models.system import AuditEvent, Role, User, UserRole

__all__ = [
    "Asset",
    "AuditEvent",
    "Document",
    "DocumentAssetLink",
    "DocumentCatalog",
    "DocumentChunk",
    "DocumentDrawingLink",
    "DocumentParseResult",
    "DocumentVersion",
    "DrawingNumber",
    "EmbeddingRegistry",
    "ExtractionCandidate",
    "GdriveSyncState",
    "IndexingJob",
    "MotorAiSummary",
    "MotorAlias",
    "MotorFamily",
    "MotorHealthScore",
    "MotorModel",
    "MotorRecommendation",
    "MotorTimelineEvent",
    "MotorUnit",
    "PerformanceTestReport",
    "Plant",
    "ProductLine",
    "RetrievalTrace",
    "ReviewQueueItem",
    "Role",
    "TestMeasurement",
    "User",
    "UserRole",
]
