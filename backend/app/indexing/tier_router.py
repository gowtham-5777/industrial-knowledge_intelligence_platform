"""Parser router by MIME type and folder / category tier (Architecture §5)."""

from __future__ import annotations

from pathlib import PurePosixPath

from app.indexing.tiers import (
    CAD_EXTENSIONS,
    NATIVE_TEXT_MIME_TYPES,
    PDF_MIME_TYPES,
    REGULATION_CATEGORIES,
    T0_CATEGORIES,
    T1_CATEGORIES,
    T3_CATEGORIES,
    T4_CATEGORIES,
    ParserTier,
    RoutingContext,
)


def select_parser_tier(ctx: RoutingContext) -> ParserTier:
    """Select the Architecture §5 parser tier for a document.

    Precedence:
    1. Explicit ``force_tier``
    2. CAD extension / T3 category → metadata-only
    3. Native XML/CSV/HTML MIME (regulations) → T0b
    4. Test reports / checklists → T1 (Azure DI)
    5. Drawing categories → T4
    6. Digital PDF categories → T0
    7. Regulations PDF under regulations folder → T1 if PDF else T0b
    8. Default PDF → T0; unknown binary → T3
    """
    if ctx.force_tier is not None:
        return ctx.force_tier

    mime = (ctx.mime_type or "").strip().lower()
    category = (ctx.doc_category or "").strip().lower() or None
    subtype = (ctx.doc_subtype or "").strip().lower() or None
    folder = (ctx.folder_path or "").replace("\\", "/").lower()
    filename = ctx.filename or ""
    ext = PurePosixPath(filename).suffix.lower()

    if category in T3_CATEGORIES or ext in CAD_EXTENSIONS:
        return ParserTier.T3

    if "cad_models" in folder or "3d_drawings" in folder:
        return ParserTier.T3

    if mime in NATIVE_TEXT_MIME_TYPES or ext in {".xml", ".csv", ".html", ".htm"}:
        return ParserTier.T0B

    if category in T1_CATEGORIES or subtype in T1_CATEGORIES:
        return ParserTier.T1

    if "incident" in folder or "inspection" in folder or "test" in folder:
        if mime in PDF_MIME_TYPES or ext == ".pdf":
            return ParserTier.T1

    if category in T4_CATEGORIES or (subtype and subtype in T4_CATEGORIES):
        return ParserTier.T4

    if any(
        token in folder
        for token in (
            "dimension_drawings",
            "outline_drawings",
            "shaft_drawings",
            "connection_diagrams",
            "mechanical_drawings",
            "terminal_box",
        )
    ):
        return ParserTier.T4

    if category in REGULATION_CATEGORIES or "regulations" in folder:
        if mime in PDF_MIME_TYPES or ext == ".pdf":
            return ParserTier.T0
        return ParserTier.T0B

    if category in T0_CATEGORIES:
        return ParserTier.T0

    if mime in PDF_MIME_TYPES or ext == ".pdf":
        return ParserTier.T0

    # Unknown binaries — avoid expensive OCR
    return ParserTier.T3


def describe_tier(tier: ParserTier) -> str:
    """Human-readable handler description for API / logs."""
    return {
        ParserTier.T0: "PyMuPDF + pdfplumber",
        ParserTier.T0B: "Native XML/CSV/HTML",
        ParserTier.T1: "Azure Document Intelligence (prebuilt-layout)",
        ParserTier.T2: "Docling fallback (PyMuPDF substitute when unavailable)",
        ParserTier.T3: "Metadata-only (no text extraction)",
        ParserTier.T4: "Filename + first-page OCR",
    }[tier]
