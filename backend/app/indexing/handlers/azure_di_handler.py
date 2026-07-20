"""T1 — Azure AI Document Intelligence prebuilt-layout handler."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, ErrorCode
from app.indexing.handlers.table_utils import rows_to_markdown
from app.indexing.models import ParsedPage, ParsedTable, ParseOutput
from app.indexing.tiers import ParserTier, RoutingContext
from app.observability import get_logger

_logger = get_logger(__name__)


def _cell_text(cell: Any) -> str:
    content = getattr(cell, "content", None)
    if content is not None:
        return str(content).strip()
    return str(cell).strip() if cell is not None else ""


def _table_to_rows(table: Any) -> list[list[str]]:
    """Normalize Azure DI table cells into a dense row matrix."""
    row_count = int(getattr(table, "row_count", 0) or 0)
    col_count = int(getattr(table, "column_count", 0) or 0)
    cells = list(getattr(table, "cells", None) or [])
    if row_count <= 0 or col_count <= 0:
        # Infer from cells
        for cell in cells:
            row_count = max(row_count, int(getattr(cell, "row_index", 0)) + 1)
            col_count = max(col_count, int(getattr(cell, "column_index", 0)) + 1)
    if row_count <= 0 or col_count <= 0:
        return []

    grid = [["" for _ in range(col_count)] for _ in range(row_count)]
    for cell in cells:
        r = int(getattr(cell, "row_index", 0))
        c = int(getattr(cell, "column_index", 0))
        if 0 <= r < row_count and 0 <= c < col_count:
            grid[r][c] = _cell_text(cell)
    return grid


class AzureDocumentIntelligenceHandler:
    """Azure DI ``prebuilt-layout`` — primary path for IEC test-report tables."""

    tier = ParserTier.T1
    name = "azure-document-intelligence"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: Any | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client

    def parse(self, content: bytes, *, ctx: RoutingContext) -> ParseOutput:
        result = self._analyze_layout(content)
        pages = self._pages_from_result(result)
        tables = self._tables_from_result(result)
        output = ParseOutput(
            tier=self.tier.value,
            parser_name=self.name,
            pages=pages,
            tables=tables,
            metadata={
                "model": "prebuilt-layout",
                "table_count": len(tables),
                "page_count": len(pages),
            },
        )
        output.ensure_full_text()
        _logger.info(
            "azure di layout complete",
            extra={
                "doc_filename": ctx.filename,
                "table_count": len(tables),
                "page_count": len(pages),
            },
        )
        return output

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        endpoint = (self._settings.azure_document_intelligence_endpoint or "").strip()
        key = (self._settings.azure_document_intelligence_key or "").strip()
        if not endpoint or not key:
            raise AppError(
                "Azure Document Intelligence is not configured "
                "(AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT / KEY)",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                status_code=503,
            )

        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
        except ImportError as exc:  # pragma: no cover
            raise AppError(
                "azure-ai-documentintelligence package is not installed",
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                status_code=503,
            ) from exc

        self._client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key),
        )
        return self._client

    def _analyze_layout(self, content: bytes) -> Any:
        client = self._get_client()
        # SDK surface: begin_analyze_document(model_id, body=..., content_type=...)
        poller = client.begin_analyze_document(
            "prebuilt-layout",
            body=content,
            content_type="application/octet-stream",
        )
        return poller.result()

    def _pages_from_result(self, result: Any) -> list[ParsedPage]:
        pages: list[ParsedPage] = []
        for page in list(getattr(result, "pages", None) or []):
            page_number = int(getattr(page, "page_number", len(pages) + 1))
            lines = list(getattr(page, "lines", None) or [])
            texts = []
            for line in lines:
                content = getattr(line, "content", None)
                if content:
                    texts.append(str(content))
            pages.append(ParsedPage(page=page_number, text="\n".join(texts).strip()))

        # Prefer content blocks when pages lack line text
        if not any(p.text for p in pages):
            content = getattr(result, "content", None)
            if content:
                pages = [ParsedPage(page=1, text=str(content).strip())]
        return pages

    def _tables_from_result(self, result: Any) -> list[ParsedTable]:
        tables: list[ParsedTable] = []
        for table in list(getattr(result, "tables", None) or []):
            rows = _table_to_rows(table)
            if not rows:
                continue
            # Bounding regions → page
            page = 1
            regions = list(getattr(table, "bounding_regions", None) or [])
            if regions:
                page = int(getattr(regions[0], "page_number", 1) or 1)
            tables.append(
                ParsedTable(
                    page=page,
                    rows=rows,
                    markdown=rows_to_markdown(rows),
                    source="azure-di",
                )
            )
        return tables


class StubAzureLayoutHandler(AzureDocumentIntelligenceHandler):
    """Test double: synthesizes a layout result with an IEC-style table."""

    name = "azure-document-intelligence-stub"

    def __init__(self, result: Any) -> None:
        super().__init__(client=object())
        self._stub_result = result

    def _analyze_layout(self, content: bytes) -> Any:  # noqa: ARG002
        return self._stub_result
