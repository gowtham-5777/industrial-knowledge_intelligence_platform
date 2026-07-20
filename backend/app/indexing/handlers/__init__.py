"""Parser handler registry."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.indexing.handlers.azure_di_handler import AzureDocumentIntelligenceHandler
from app.indexing.handlers.docling_fallback import DoclingFallbackHandler
from app.indexing.handlers.first_page_handler import FirstPageOcrHandler
from app.indexing.handlers.metadata_handler import MetadataOnlyHandler
from app.indexing.handlers.native_handlers import NativeFormatHandler
from app.indexing.handlers.pymupdf_handler import PyMuPdfHandler
from app.indexing.tiers import ParserTier


class HandlerRegistry:
    """Map parser tiers to concrete handlers."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        azure_handler: AzureDocumentIntelligenceHandler | None = None,
    ) -> None:
        cfg = settings or get_settings()
        azure = azure_handler or AzureDocumentIntelligenceHandler(cfg)
        self._handlers = {
            ParserTier.T0: PyMuPdfHandler(),
            ParserTier.T0B: NativeFormatHandler(),
            ParserTier.T1: azure,
            ParserTier.T2: DoclingFallbackHandler(),
            ParserTier.T3: MetadataOnlyHandler(),
            ParserTier.T4: FirstPageOcrHandler(azure=azure, prefer_azure=False),
        }

    def get(self, tier: ParserTier):
        return self._handlers[tier]
