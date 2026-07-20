"""T2 — Docling fallback stub (uses PyMuPDF when Docling is unavailable)."""

from __future__ import annotations

from app.indexing.handlers.pymupdf_handler import PyMuPdfHandler
from app.indexing.models import ParseOutput
from app.indexing.tiers import ParserTier, RoutingContext


class DoclingFallbackHandler:
    """Architecture T2: Docling when present; otherwise PyMuPDF substitute.

    Full Docling integration is deferred to on-prem production path. For the
    hackathon stack we keep the tier selectable and fall back to T0 handlers
    so Azure quota failures on manuals remain recoverable.
    """

    tier = ParserTier.T2
    name = "docling-fallback"

    def __init__(self, pdf_handler: PyMuPdfHandler | None = None) -> None:
        self._pdf = pdf_handler or PyMuPdfHandler()

    def parse(self, content: bytes, *, ctx: RoutingContext) -> ParseOutput:
        try:
            import docling  # type: ignore[import-not-found]  # noqa: F401

            # Placeholder for future DoclingDocument conversion
            raise ImportError("docling pipeline not wired in hackathon build")
        except ImportError:
            output = self._pdf.parse(content, ctx=ctx)
            output.tier = self.tier.value
            output.parser_name = f"{self.name}->pymupdf"
            output.warnings = list(output.warnings) + [
                "Docling unavailable; used PyMuPDF fallback"
            ]
            return output
