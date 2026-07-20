"""In-memory parse result contracts (handlers → service)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ParsedTable:
    """One extracted table (Azure DI / pdfplumber)."""

    page: int
    rows: list[list[str]]
    markdown: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "page": self.page,
            "rows": self.rows,
            "markdown": self.markdown,
            "source": self.source,
        }


@dataclass(slots=True)
class ParsedPage:
    """Text extracted from a single page / section."""

    page: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"page": self.page, "text": self.text}


@dataclass(slots=True)
class ParseOutput:
    """Normalized handler output before persistence."""

    tier: str
    parser_name: str
    pages: list[ParsedPage] = field(default_factory=list)
    tables: list[ParsedTable] = field(default_factory=list)
    full_text: str = ""
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    skipped: bool = False

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def ensure_full_text(self) -> str:
        if self.full_text:
            return self.full_text
        self.full_text = "\n\n".join(p.text for p in self.pages if p.text).strip()
        return self.full_text
