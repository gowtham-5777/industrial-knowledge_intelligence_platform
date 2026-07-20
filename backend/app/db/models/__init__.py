"""ORM models for the PostgreSQL system of record (Architecture §12)."""

from app.db.models.ai import CopilotMessage, CopilotSession, FeedbackRating
from app.db.models.assets import Asset
from app.db.models.chunks import DocumentChunk, EmbeddingRegistry, RetrievalTrace
from app.db.models.compliance import (
    Certification,
    ComplianceEvidence,
    ComplianceRequirement,
    Regulation,
)
from app.db.models.documents import (
    Document,
    DocumentAcl,
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
from app.db.models.processing import DeadLetterJob, GdriveSyncState, IndexingJob
from app.db.models.system import AuditEvent, Role, User, UserRole

__all__ = [
    "Asset",
    "AuditEvent",
    "Certification",
    "ComplianceEvidence",
    "ComplianceRequirement",
    "CopilotMessage",
    "CopilotSession",
    "DeadLetterJob",
    "Document",
    "DocumentAcl",
    "DocumentAssetLink",
    "DocumentCatalog",
    "DocumentChunk",
    "DocumentDrawingLink",
    "DocumentParseResult",
    "DocumentVersion",
    "DrawingNumber",
    "EmbeddingRegistry",
    "ExtractionCandidate",
    "FeedbackRating",
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
    "Regulation",
    "RetrievalTrace",
    "ReviewQueueItem",
    "Role",
    "TestMeasurement",
    "User",
    "UserRole",
]
