"""Doc-type-aware chunkers (Milestone 2.3 — Architecture §5)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ChunkDraft:
    text: str
    chunk_index: int
    page: int | None = None
    section_path: str | None = None
    parent_section: str | None = None
    token_count: int | None = None
    extra_metadata: dict[str, Any] = field(default_factory=dict)


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token) for sizing."""
    return max(1, len(text) // 4) if text else 0


def _split_overlap(
    text: str, *, max_tokens: int = 768, overlap_ratio: float = 0.1
) -> list[str]:
    if not text.strip():
        return []
    max_chars = max_tokens * 4
    overlap_chars = int(max_chars * overlap_ratio)
    if len(text) <= max_chars:
        return [text.strip()]

    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        # Prefer break on paragraph / sentence
        if end < len(text):
            window = text[start:end]
            break_at = max(window.rfind("\n\n"), window.rfind("\n"), window.rfind(". "))
            if break_at > max_chars * 0.4:
                end = start + break_at + 1
        chunk = text[start:end].strip()
        if chunk:
            parts.append(chunk)
        if end >= len(text):
            break
        start = max(0, end - overlap_chars)
    return parts


def chunk_test_report(
    *,
    full_text: str,
    tables: list[dict[str, Any]],
    pages: list[dict[str, Any]],
) -> list[ChunkDraft]:
    """One chunk per measurement table section; preserve markdown tables."""
    drafts: list[ChunkDraft] = []
    index = 0
    for table in tables or []:
        rows = table.get("rows") or []
        md = table.get("markdown") or ""
        if not md and rows:
            md = "\n".join(" | ".join(str(c) for c in row) for row in rows)
        if not md.strip():
            continue
        page = table.get("page")
        text = f"Test measurement table (page {page or '?'}):\n{md}"
        drafts.append(
            ChunkDraft(
                text=text,
                chunk_index=index,
                page=page,
                section_path=f"table/{index}",
                parent_section="Test measurements",
                token_count=estimate_tokens(text),
                extra_metadata={"kind": "table"},
            )
        )
        index += 1

    if not drafts and full_text.strip():
        for i, part in enumerate(_split_overlap(full_text)):
            drafts.append(
                ChunkDraft(
                    text=part,
                    chunk_index=i,
                    page=1,
                    section_path=f"body/{i}",
                    parent_section="Test report body",
                    token_count=estimate_tokens(part),
                )
            )
    elif pages and not drafts:
        for page in pages:
            text = str(page.get("text") or "").strip()
            if not text:
                continue
            drafts.append(
                ChunkDraft(
                    text=text,
                    chunk_index=index,
                    page=page.get("page"),
                    section_path=f"page/{page.get('page')}",
                    parent_section="Test report page",
                    token_count=estimate_tokens(text),
                )
            )
            index += 1
    return drafts


_SECTION_RE = re.compile(
    r"(?m)^(?:#{1,3}\s+|(?:\d+(?:\.\d+)*)\s+|([A-Z][A-Za-z0-9 /&-]{3,80})$)",
)


def chunk_datasheet(full_text: str) -> list[ChunkDraft]:
    """Chunk by spec-like sections when headings exist; else overlap windows."""
    sections = _split_by_headings(full_text, default_parent="Datasheet")
    if len(sections) <= 1:
        return [
            ChunkDraft(
                text=part,
                chunk_index=i,
                section_path=f"datasheet/{i}",
                parent_section="Datasheet",
                token_count=estimate_tokens(part),
            )
            for i, part in enumerate(_split_overlap(full_text))
        ]
    drafts: list[ChunkDraft] = []
    idx = 0
    for title, body in sections:
        for part in _split_overlap(body, max_tokens=768):
            drafts.append(
                ChunkDraft(
                    text=f"{title}\n{part}" if title else part,
                    chunk_index=idx,
                    section_path=title or f"section/{idx}",
                    parent_section=title or "Datasheet",
                    token_count=estimate_tokens(part),
                )
            )
            idx += 1
    return drafts


def chunk_manual(full_text: str) -> list[ChunkDraft]:
    """Chunk by numbered procedure steps when present."""
    step_re = re.compile(r"(?m)(?:^|\n)\s*((?:\d+[\).]|Step\s+\d+)[^\n]*)")
    parts = step_re.split(full_text)
    if len(parts) < 3:
        return [
            ChunkDraft(
                text=p,
                chunk_index=i,
                section_path=f"manual/{i}",
                parent_section="Manual",
                token_count=estimate_tokens(p),
            )
            for i, p in enumerate(_split_overlap(full_text))
        ]

    drafts: list[ChunkDraft] = []
    idx = 0
    # parts: [preamble, step1_title, step1_body, step2_title, ...]
    preamble = parts[0].strip()
    if preamble:
        for p in _split_overlap(preamble):
            drafts.append(
                ChunkDraft(
                    text=p,
                    chunk_index=idx,
                    section_path="manual/preamble",
                    parent_section="Manual preamble",
                    token_count=estimate_tokens(p),
                )
            )
            idx += 1
    i = 1
    while i < len(parts) - 1:
        title = parts[i].strip()
        body = parts[i + 1].strip()
        text = f"{title}\n{body}".strip()
        for p in _split_overlap(text, max_tokens=640):
            drafts.append(
                ChunkDraft(
                    text=p,
                    chunk_index=idx,
                    section_path=title[:120],
                    parent_section=title,
                    token_count=estimate_tokens(p),
                )
            )
            idx += 1
        i += 2
    return drafts


def chunk_regulation(full_text: str) -> list[ChunkDraft]:
    """Chunk by clause / section ID markers."""
    clause_re = re.compile(
        r"(?m)^(?:(?P<id>\(?[a-z0-9]+\)|[0-9]+(?:\.[0-9]+)+)\s+|(?P<head>§\s*[0-9.]+))"
    )
    sections = _split_by_regex_markers(full_text, clause_re)
    if len(sections) <= 1:
        return [
            ChunkDraft(
                text=p,
                chunk_index=i,
                section_path=f"regulation/{i}",
                parent_section="Regulation",
                token_count=estimate_tokens(p),
            )
            for i, p in enumerate(_split_overlap(full_text, max_tokens=900))
        ]
    drafts: list[ChunkDraft] = []
    for i, (title, body) in enumerate(sections):
        text = f"{title}\n{body}".strip() if title else body
        for j, part in enumerate(_split_overlap(text, max_tokens=900)):
            drafts.append(
                ChunkDraft(
                    text=part,
                    chunk_index=len(drafts),
                    section_path=title or f"clause/{i}.{j}",
                    parent_section=title or "Regulation",
                    token_count=estimate_tokens(part),
                )
            )
    return drafts


def chunk_drawing(
    *,
    full_text: str,
    drawing_number: str | None,
    sheet_id: str | None,
) -> list[ChunkDraft]:
    """OCR / first-page text blocks for drawings."""
    meta = []
    if drawing_number:
        meta.append(f"Drawing: {drawing_number}")
    if sheet_id:
        meta.append(f"Sheet: {sheet_id}")
    header = " | ".join(meta)
    body = full_text.strip() or "(metadata-only drawing; no OCR text)"
    text = f"{header}\n{body}" if header else body
    return [
        ChunkDraft(
            text=text,
            chunk_index=0,
            page=1,
            section_path="drawing/first-page",
            parent_section=header or "Drawing",
            token_count=estimate_tokens(text),
            extra_metadata={"drawing_number": drawing_number, "sheet_id": sheet_id},
        )
    ]


def chunk_generic(full_text: str) -> list[ChunkDraft]:
    return [
        ChunkDraft(
            text=p,
            chunk_index=i,
            section_path=f"body/{i}",
            parent_section="Document",
            token_count=estimate_tokens(p),
        )
        for i, p in enumerate(_split_overlap(full_text or ""))
    ]


def chunk_document(
    *,
    doc_category: str | None,
    full_text: str,
    tables: list[dict[str, Any]] | None = None,
    pages: list[dict[str, Any]] | None = None,
    drawing_number: str | None = None,
    sheet_id: str | None = None,
) -> list[ChunkDraft]:
    """Select Architecture-tuned chunker by document category."""
    category = (doc_category or "").lower()
    tables = tables or []
    pages = pages or []

    if category in {"test_report", "checklist"}:
        return chunk_test_report(full_text=full_text, tables=tables, pages=pages)
    if category in {"datasheet", "certificate", "asset_register"}:
        return chunk_datasheet(full_text)
    if category in {"manual", "sop", "maintenance", "safety", "work_order"}:
        return chunk_manual(full_text)
    if category in {"regulation"}:
        return chunk_regulation(full_text)
    if category.startswith("drawing"):
        return chunk_drawing(
            full_text=full_text,
            drawing_number=drawing_number,
            sheet_id=sheet_id,
        )
    return chunk_generic(full_text)


def _split_by_headings(text: str, *, default_parent: str) -> list[tuple[str, str]]:
    lines = (text or "").splitlines()
    sections: list[tuple[str, str]] = []
    current_title = default_parent
    buf: list[str] = []
    heading_re = re.compile(
        r"^(?:#{1,3}\s+(.+)|(\d+(?:\.\d+)*)\s+(.+)|([A-Z][A-Z0-9 /&-]{4,80}))$"
    )
    for line in lines:
        m = heading_re.match(line.strip())
        if m and len(line.strip()) < 100:
            if buf:
                sections.append((current_title, "\n".join(buf).strip()))
                buf = []
            current_title = next(g for g in m.groups() if g)
        else:
            buf.append(line)
    if buf:
        sections.append((current_title, "\n".join(buf).strip()))
    return [(t, b) for t, b in sections if b]


def _split_by_regex_markers(
    text: str, pattern: re.Pattern[str]
) -> list[tuple[str, str]]:
    matches = list(pattern.finditer(text or ""))
    if not matches:
        return [("", text or "")]
    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.append(("preamble", preamble))
    for i, match in enumerate(matches):
        title = match.group(0).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append((title[:120], body))
    return sections
