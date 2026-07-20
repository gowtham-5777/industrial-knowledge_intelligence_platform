"""Parser tier constants and routing inputs (Architecture §5)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ParserTier(StrEnum):
    """Hackathon tiered OCR / parsing pipeline."""

    T0 = "T0"  # PyMuPDF + pdfplumber — digital PDFs
    T0B = "T0b"  # Native XML/CSV/HTML — regulations
    T1 = "T1"  # Azure DI prebuilt-layout — test reports / checklists
    T2 = "T2"  # Docling fallback (Azure quota / manuals)
    T3 = "T3"  # Metadata-only — CAD / 3D
    T4 = "T4"  # Filename + first-page OCR — drawings at scale


# Categories that prefer Azure DI layout (high-value tables)
T1_CATEGORIES: frozenset[str] = frozenset(
    {
        "test_report",
        "checklist",
    }
)

# Digital PDF categories handled by native PDF text extractors
T0_CATEGORIES: frozenset[str] = frozenset(
    {
        "datasheet",
        "manual",
        "safety",
        "maintenance",
        "sop",
        "sensor",
        "work_order",
        "certificate",
        "asset_register",
    }
)

# CAD / 3D — never deep-parse content
T3_CATEGORIES: frozenset[str] = frozenset(
    {
        "drawing_cad",
    }
)

# Drawing subtypes that get first-page OCR only
T4_CATEGORIES: frozenset[str] = frozenset(
    {
        "drawing",
        "drawing_dimension",
        "drawing_outline",
        "drawing_shaft",
        "drawing_connection",
        "drawing_mechanical",
        "drawing_terminal",
    }
)

REGULATION_CATEGORIES: frozenset[str] = frozenset({"regulation"})

NATIVE_TEXT_MIME_TYPES: frozenset[str] = frozenset(
    {
        "text/xml",
        "application/xml",
        "text/csv",
        "application/csv",
        "text/html",
        "application/xhtml+xml",
        "text/plain",
    }
)

CAD_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".dwg",
        ".dxf",
        ".step",
        ".stp",
        ".iges",
        ".igs",
        ".sat",
        ".x_t",
        ".x_b",
        ".prt",
        ".asm",
        ".sldprt",
        ".sldasm",
        ".catpart",
        ".catproduct",
        ".3ds",
        ".obj",
        ".stl",
        ".jt",
    }
)

PDF_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "application/x-pdf",
    }
)


@dataclass(frozen=True, slots=True)
class RoutingContext:
    """Inputs for the MIME / folder-tier parser router."""

    mime_type: str | None = None
    doc_category: str | None = None
    doc_subtype: str | None = None
    folder_path: str | None = None
    filename: str | None = None
    force_tier: ParserTier | None = None
