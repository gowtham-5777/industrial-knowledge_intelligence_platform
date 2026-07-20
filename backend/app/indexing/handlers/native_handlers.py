"""T0b — native XML / CSV / HTML parsers for regulations."""

from __future__ import annotations

import csv
import io
import re
from html.parser import HTMLParser
from xml.etree import ElementTree

from app.indexing.models import ParsedPage, ParseOutput
from app.indexing.tiers import ParserTier, RoutingContext


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._skip = False
        if tag in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "br"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self._chunks.append(data.strip())

    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", " ".join(self._chunks)).strip()


class NativeFormatHandler:
    """Parse regulations-style XML, CSV, and HTML without the PDF pipeline."""

    tier = ParserTier.T0B
    name = "native-xml-csv-html"

    def parse(self, content: bytes, *, ctx: RoutingContext) -> ParseOutput:
        mime = (ctx.mime_type or "").lower()
        name = (ctx.filename or "").lower()

        if "csv" in mime or name.endswith(".csv"):
            text = self._parse_csv(content)
            kind = "csv"
        elif "html" in mime or name.endswith((".html", ".htm")):
            text = self._parse_html(content)
            kind = "html"
        else:
            text = self._parse_xml(content)
            kind = "xml"

        page = ParsedPage(page=1, text=text)
        output = ParseOutput(
            tier=self.tier.value,
            parser_name=self.name,
            pages=[page],
            full_text=text,
            metadata={"format": kind, "char_count": len(text)},
        )
        return output

    def _parse_csv(self, content: bytes) -> str:
        text = content.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return ""
        lines = [", ".join(row) for row in rows]
        return "\n".join(lines)

    def _parse_html(self, content: bytes) -> str:
        extractor = _HTMLTextExtractor()
        extractor.feed(content.decode("utf-8", errors="replace"))
        return extractor.text()

    def _parse_xml(self, content: bytes) -> str:
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            return content.decode("utf-8", errors="replace").strip()

        parts: list[str] = []

        def walk(node: ElementTree.Element, path: str = "") -> None:
            tag = node.tag.split("}")[-1] if "}" in node.tag else node.tag
            current = f"{path}/{tag}" if path else tag
            text = (node.text or "").strip()
            if text:
                parts.append(f"{current}: {text}")
            for child in list(node):
                walk(child, current)

        walk(root)
        return "\n".join(parts)
