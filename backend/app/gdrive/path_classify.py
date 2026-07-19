"""Path-based doc category / subtype hints from corpus folder layout."""

from __future__ import annotations

import mimetypes
import re
from pathlib import PurePosixPath

# Architecture discovery extracts category/subtype from folder path (full rules in 1.7)
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
}

_DRAWING_RE = re.compile(
    r"(?i)(3GZ[A-Z0-9]{6,}|3AXD\d{9,}[A-Z0-9_-]*)",
)

_MOTOR_CODE_RE = re.compile(
    r"\b(M3BP|M2BA|M3AA|ACS\d{3}|ACQ\d{3}|ACH\d{3})\b",
    re.IGNORECASE,
)


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
        # e.g. drawing/CAD_Models_and_3D_Drawings → subtype from last folder
        last = parts[-2].strip().lower() if len(parts) >= 2 else ""
        if last in _CATEGORY_ALIASES and _CATEGORY_ALIASES[last] != category:
            subtype = _CATEGORY_ALIASES[last]

    return asset_domain, category, subtype


def guess_mime_type(filename: str) -> str | None:
    mime, _ = mimetypes.guess_type(filename)
    return mime


def extract_drawing_number(filename: str) -> str | None:
    match = _DRAWING_RE.search(filename)
    return match.group(1).upper() if match else None


def extract_motor_type_code(filename: str, folder_path: str) -> str | None:
    haystack = f"{folder_path}/{filename}"
    match = _MOTOR_CODE_RE.search(haystack)
    if match:
        return match.group(1).upper()
    # Motor pack folders: Low_Voltage_Motor - 001
    for part in PurePosixPath(normalize_rel_path(folder_path)).parts:
        if "motor" in part.lower() and "-" in part:
            return part.strip()
    return None
