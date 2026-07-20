"""T4 — filename metadata + first-page OCR / text for drawings."""

from __future__ import annotations

from pathlib import PurePosixPath

from app.documents.classification import extract_drawing_number, extract_motor_type_code
from app.indexing.handlers.azure_di_handler import AzureDocumentIntelligenceHandler
from app.indexing.handlers.pymupdf_handler import PyMuPdfHandler
from app.indexing.models import ParsedPage, ParseOutput
from app.indexing.tiers import ParserTier, RoutingContext
from app.observability import get_logger

_logger = get_logger(__name__)


class FirstPageOcrHandler:
    """Drawings at scale: keep drawing number from filename; OCR page 1 only."""

    tier = ParserTier.T4
    name = "first-page-ocr"

    def __init__(
        self,
        *,
        azure: AzureDocumentIntelligenceHandler | None = None,
        pdf: PyMuPdfHandler | None = None,
        prefer_azure: bool = False,
    ) -> None:
        self._azure = azure
        self._pdf = pdf or PyMuPdfHandler()
        self._prefer_azure = prefer_azure

    def parse(self, content: bytes, *, ctx: RoutingContext) -> ParseOutput:
        filename = ctx.filename or ""
        drawing = extract_drawing_number(filename)
        motor = extract_motor_type_code(filename, ctx.folder_path or "")
        warnings: list[str] = []
        pages: list[ParsedPage] = []
        parser_used = "filename-only"

        ext = PurePosixPath(filename).suffix.lower()
        mime = (ctx.mime_type or "").lower()
        is_pdf = ext == ".pdf" or "pdf" in mime

        if is_pdf and content:
            try:
                if self._prefer_azure and self._azure is not None:
                    full = self._azure.parse(content, ctx=ctx)
                    if full.pages:
                        pages = [full.pages[0]]
                        parser_used = f"{self._azure.name}:first-page"
                else:
                    full = self._pdf.parse(content, ctx=ctx)
                    if full.pages:
                        pages = [ParsedPage(page=1, text=full.pages[0].text)]
                        parser_used = "pymupdf:first-page"
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"first-page extract failed: {exc}")
                _logger.warning(
                    "first-page extract failed",
                    extra={"doc_filename": filename, "error": str(exc)},
                )

        text = pages[0].text if pages else ""
        return ParseOutput(
            tier=self.tier.value,
            parser_name=self.name,
            pages=pages,
            full_text=text,
            warnings=warnings,
            metadata={
                "filename": filename,
                "drawing_number": drawing,
                "motor_type_code": motor,
                "first_page_parser": parser_used,
                "doc_subtype": ctx.doc_subtype,
            },
        )
