"""Document catalog, upload, and secondary library APIs."""

from app.documents.routes import router as documents_router
from app.documents.service import DocumentCatalogService

__all__ = ["DocumentCatalogService", "documents_router"]
