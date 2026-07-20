"""Path / filename classification for document catalog (Milestone 1.7)."""

from __future__ import annotations

import mimetypes
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

# Architecture discovery extracts category/subtype from folder path
_CATEGORY_ALIASES: dict[str, str] = {
    "drawing": "drawing",
    "drawings": "drawing",
    "incident or inspection": "test_report",
    "incident_or_inspection": "test_report",
    "instructions and manuals": "manual",
    "instructions_and_manuals": "manual",
    "maintenance": "maintenance",
    "regulations": "regulation",
    "safety": "safety",
    "sensors": "sensor",
    "sop_s": "sop",
    "sops": "sop",
    "spare parts or product descriptions": "datasheet",
    "spare_parts_or_product_descriptions": "datasheet",
    "work_orders": "work_order",
    "08_work_orders": "work_order",
    "asset_register": "asset_register",
    "cad_models_and_3d_drawings": "drawing_cad",
    "dimension_drawings": "drawing_dimension",
    "outline_drawings": "drawing_outline",
    "shaft_drawings": "drawing_shaft",
    "connection_diagrams": "drawing_connection",
    "mechanical_drawings": "drawing_mechanical",
    "terminal_box_drawings": "drawing_terminal",
    "certificates": "certificate",
    "certification": "certificate",
    "certifications": "certificate",
}

# Architecture § drawing linker: 3GZF/3GZC…, 9AKK…, 3AXD…
_DRAWING_RE = re.compile(
    r"(?i)(" r"3GZ[A-Z0-9]{6,}(?:-[A-Z0-9]+)?" r"|9AKK[A-Z0-9]{6,}" r"|3AXD\d{9,}" r")",
)

# Sheet references on multi-sheet drawings (A1 / A2 / A3)
_SHEET_RE = re.compile(r"(?i)(?:^|[_\-\s.])(A[123])(?:[_\-\s.]|$)")

_MOTOR_CODE_RE = re.compile(
    r"\b(M3BP|M2BA|M3AA|ACS\d{3}|ACQ\d{3}|ACH\d{3}|Low_Voltage_Motor(?:\s*-\s*\d+)?)\b",
    re.IGNORECASE,
)

# Manual upload API — Architecture PDF / DOCX / XLSX / images
MANUAL_UPLOAD_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/tiff",
    }
)


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    asset_domain: str | None
    doc_category: str | None
    doc_subtype: str | None
    drawing_number: str | None
    motor_type_code: str | None


def normalize_rel_path(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def classify_path(relative_path: str) -> tuple[str | None, str | None, str | None]:
    """Return (asset_domain, doc_category, doc_subtype) from relative path."""
    parts = [p for p in normalize_rel_path(relative_path).split("/") if p]
    if not parts:
        return None, None, None

    asset_domain = parts[0]
    category: str | None = None
    subtype: str | None = None

    for part in parts[1:]:
        key = part.strip().lower()
        mapped = _CATEGORY_ALIASES.get(key)
        if mapped:
            if category is None:
                category = mapped
            else:
                subtype = mapped
                break

    if subtype is None and len(parts) >= 2:
        last = parts[-2].strip().lower()
        if last in _CATEGORY_ALIASES and _CATEGORY_ALIASES[last] != category:
            subtype = _CATEGORY_ALIASES[last]

    return asset_domain, category, subtype


def guess_mime_type(filename: str) -> str | None:
    mime, _ = mimetypes.guess_type(filename)
    return mime


def extract_drawing_number(filename: str) -> str | None:
    match = _DRAWING_RE.search(filename)
    if not match:
        return None
    return match.group(1).upper().replace(" ", "")


def extract_sheet_id(filename: str) -> str | None:
    """Return A1/A2/A3 sheet token when present in the filename."""
    match = _SHEET_RE.search(filename)
    return match.group(1).upper() if match else None


def extract_all_drawing_numbers(text: str) -> list[str]:
    """Deduplicated drawing numbers found in filename or body text."""
    found: list[str] = []
    seen: set[str] = set()
    for match in _DRAWING_RE.finditer(text or ""):
        value = match.group(1).upper().replace(" ", "")
        if value not in seen:
            seen.add(value)
            found.append(value)
    return found


def extract_motor_type_code(filename: str, folder_path: str = "") -> str | None:
    haystack = f"{folder_path}/{filename}"
    match = _MOTOR_CODE_RE.search(haystack)
    if match:
        return re.sub(r"\s+", " ", match.group(1).strip())
    for part in PurePosixPath(normalize_rel_path(folder_path or "")).parts:
        lower = part.lower()
        if "motor" in lower and "-" in part:
            return part.strip()
    return None


def classify_document(
    *,
    name: str,
    folder_path: str | None = None,
) -> ClassificationResult:
    """Full classification payload for catalog upsert / upload."""
    folder = normalize_rel_path(folder_path or "")
    relative = f"{folder}/{name}" if folder else name
    asset_domain, doc_category, doc_subtype = classify_path(relative)
    return ClassificationResult(
        asset_domain=asset_domain,
        doc_category=doc_category,
        doc_subtype=doc_subtype,
        drawing_number=extract_drawing_number(name),
        motor_type_code=extract_motor_type_code(name, folder),
    )
