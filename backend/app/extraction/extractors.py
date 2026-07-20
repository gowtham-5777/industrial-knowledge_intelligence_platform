"""Regex / table entity extractors (Milestone 2.2)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.documents.classification import (
    extract_all_drawing_numbers,
    extract_drawing_number,
    extract_motor_type_code,
    extract_sheet_id,
)

# Spec field patterns (datasheets / manuals)
_FRAME_RE = re.compile(
    r"(?i)\b(?:frame(?:\s*size)?|IEC\s*frame)\s*[:=]?\s*([0-9]{2,3}[A-Z]{0,3})",
)
_POWER_RE = re.compile(
    r"(?i)\b(?:rated\s*)?(?:power|output)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*(kW|hp)\b",
)
_VOLTAGE_RE = re.compile(
    r"(?i)\b(?:rated\s*)?voltage\s*[:=]?\s*([0-9]{2,4}(?:\s*/\s*[0-9]{2,4})?)\s*V\b",
)
_IE_CLASS_RE = re.compile(r"(?i)\b(IE[1-5])\b")
_POLES_RE = re.compile(r"(?i)\b([2-8])\s*-?\s*pole\b")
_EFFICIENCY_RE = re.compile(
    r"(?i)\befficiency\b[^0-9%]{0,20}([0-9]{2,3}(?:\.[0-9]+)?)\s*%?",
)
_PF_RE = re.compile(
    r"(?i)\b(?:power\s*factor|cos\s*φ|pf)\b[^0-9]{0,20}(0\.[0-9]{1,3}|[0-9]\.[0-9]{1,3})",
)
_TEMP_RISE_RE = re.compile(
    r"(?i)\b(?:temp(?:erature)?\s*rise|Δθ)\b[^0-9]{0,20}([0-9]{1,3}(?:\.[0-9]+)?)\s*K?",
)
_VIBRATION_RE = re.compile(
    r"(?i)\bvibration\b[^0-9]{0,30}([0-9]+(?:\.[0-9]+)?)\s*(mm/s|µm|um)?",
)
_IEC_STD_RE = re.compile(r"(?i)\b(IEC\s*60034(?:-[0-9]+)?)\b")
_CERT_RE = re.compile(
    r"(?i)\b(ATEX|IECEX|UL|CSA|CE|CCC|EAC|ISO\s*9001|ISO\s*14001)\b",
)
_SERIAL_RE = re.compile(
    r"(?i)\b(?:serial(?:\s*no\.?| number)?|s/n)\s*[:=]?\s*([A-Z0-9\-/]{4,})\b",
)

_MEASUREMENT_ALIASES: dict[str, str] = {
    "efficiency": "efficiency",
    "η": "efficiency",
    "power factor": "power_factor",
    "pf": "power_factor",
    "cos φ": "power_factor",
    "cos phi": "power_factor",
    "temp rise": "temp_rise",
    "temperature rise": "temp_rise",
    "Δθ": "temp_rise",
    "vibration": "vibration",
    "voltage": "voltage",
    "current": "current",
    "speed": "speed",
    "torque": "torque",
    "power": "power",
    "frequency": "frequency",
}


@dataclass(slots=True)
class ExtractedEntity:
    entity_type: str
    value: str
    normalized_value: str | None = None
    confidence: float = 0.8
    source: str = "regex"
    page: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExtractedMeasurement:
    parameter: str
    unit: str | None
    rated_value: str | None
    measured_value: str | None
    numeric_value: float | None
    page: int | None = None
    source_table_index: int | None = None
    confidence: float = 0.85


@dataclass(slots=True)
class ExtractionBundle:
    entities: list[ExtractedEntity] = field(default_factory=list)
    measurements: list[ExtractedMeasurement] = field(default_factory=list)
    standard: str | None = None
    serial_number: str | None = None


def _norm_param(cell: str) -> str | None:
    key = re.sub(r"\s+", " ", (cell or "").strip().lower())
    if not key:
        return None
    if key in _MEASUREMENT_ALIASES:
        return _MEASUREMENT_ALIASES[key]
    for alias, canonical in _MEASUREMENT_ALIASES.items():
        if alias in key:
            return canonical
    return None


def _to_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", raw.replace(",", "."))
    if not cleaned or cleaned in {".", "-", "-."}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_drawing_entities(
    *,
    filename: str,
    text: str = "",
    folder_path: str = "",
) -> list[ExtractedEntity]:
    """2.2.1 — drawing numbers (3GZF/9AKK/…) + optional sheet id."""
    entities: list[ExtractedEntity] = []
    primary = extract_drawing_number(filename)
    numbers = extract_all_drawing_numbers(f"{filename}\n{text}")
    if primary and primary not in numbers:
        numbers.insert(0, primary)

    for number in numbers:
        conf = 0.95 if number == primary else 0.75
        entities.append(
            ExtractedEntity(
                entity_type="drawing_number",
                value=number,
                normalized_value=number,
                confidence=conf,
                source="filename" if number == primary else "text",
                payload={"folder_path": folder_path or None},
            )
        )

    sheet = extract_sheet_id(filename)
    if sheet:
        entities.append(
            ExtractedEntity(
                entity_type="sheet_id",
                value=sheet,
                normalized_value=sheet,
                confidence=0.9,
                source="filename",
            )
        )
    return entities


def extract_motor_spec_fields(
    text: str, *, filename: str = "", folder_path: str = ""
) -> list[ExtractedEntity]:
    """2.2.2 — motor type / frame / power / voltage / IE class."""
    entities: list[ExtractedEntity] = []
    motor = extract_motor_type_code(filename, folder_path)
    if motor:
        entities.append(
            ExtractedEntity(
                entity_type="motor_type_code",
                value=motor,
                normalized_value=motor,
                confidence=0.9,
                source="filename",
            )
        )

    haystack = text or ""
    patterns: list[tuple[str, re.Pattern[str], float]] = [
        ("frame_size", _FRAME_RE, 0.85),
        ("power", _POWER_RE, 0.85),
        ("voltage", _VOLTAGE_RE, 0.8),
        ("ie_class", _IE_CLASS_RE, 0.9),
        ("poles", _POLES_RE, 0.8),
    ]
    for entity_type, pattern, conf in patterns:
        match = pattern.search(haystack)
        if not match:
            continue
        if entity_type == "power":
            value = f"{match.group(1)} {match.group(2)}"
            payload = {"numeric": _to_float(match.group(1)), "unit": match.group(2)}
        else:
            value = match.group(1)
            payload = {}
        entities.append(
            ExtractedEntity(
                entity_type=entity_type,
                value=value,
                normalized_value=(
                    value.upper() if entity_type in {"ie_class"} else value
                ),
                confidence=conf,
                source="text",
                payload=payload,
            )
        )
    return entities


def extract_certification_fields(text: str) -> list[ExtractedEntity]:
    """2.2.4 — certification / regulation markers."""
    entities: list[ExtractedEntity] = []
    seen: set[str] = set()
    for match in _CERT_RE.finditer(text or ""):
        value = re.sub(r"\s+", " ", match.group(1).upper().strip())
        if value in seen:
            continue
        seen.add(value)
        entities.append(
            ExtractedEntity(
                entity_type="certification",
                value=value,
                normalized_value=value,
                confidence=0.8,
                source="text",
            )
        )
    iec = _IEC_STD_RE.search(text or "")
    if iec:
        value = re.sub(r"\s+", " ", iec.group(1).upper())
        entities.append(
            ExtractedEntity(
                entity_type="regulation_standard",
                value=value,
                normalized_value=value,
                confidence=0.85,
                source="text",
            )
        )
    return entities


def extract_measurements_from_tables(
    tables: list[dict[str, Any]],
) -> list[ExtractedMeasurement]:
    """2.2.3 — IEC-style measurement rows from parsed tables."""
    results: list[ExtractedMeasurement] = []
    for table_index, table in enumerate(tables or []):
        rows = table.get("rows") or []
        page = table.get("page")
        if not rows:
            continue
        header = [str(c).strip().lower() for c in rows[0]]
        # Detect column roles
        param_idx = 0
        unit_idx = None
        rated_idx = None
        measured_idx = None
        for i, cell in enumerate(header):
            if any(t in cell for t in ("parameter", "quantity", "item", "description")):
                param_idx = i
            elif "unit" in cell:
                unit_idx = i
            elif any(t in cell for t in ("rated", "nominal", "guaranteed")):
                rated_idx = i
            elif any(t in cell for t in ("measured", "actual", "test", "result")):
                measured_idx = i

        # Single-column fallback: Parameter | Value
        if measured_idx is None and len(header) >= 2:
            measured_idx = len(header) - 1

        for row in rows[1:]:
            if not row:
                continue
            cells = ["" if c is None else str(c).strip() for c in row]
            if param_idx >= len(cells):
                continue
            param = _norm_param(cells[param_idx])
            if not param:
                continue
            unit = (
                cells[unit_idx]
                if unit_idx is not None and unit_idx < len(cells)
                else None
            )
            rated = (
                cells[rated_idx]
                if rated_idx is not None and rated_idx < len(cells)
                else None
            )
            measured = (
                cells[measured_idx]
                if measured_idx is not None and measured_idx < len(cells)
                else None
            )
            numeric = _to_float(measured) if measured else _to_float(rated)
            results.append(
                ExtractedMeasurement(
                    parameter=param,
                    unit=unit or None,
                    rated_value=rated or None,
                    measured_value=measured or None,
                    numeric_value=numeric,
                    page=page,
                    source_table_index=table_index,
                )
            )
    return results


def extract_measurements_from_text(text: str) -> list[ExtractedMeasurement]:
    """Fallback measurement extraction from free text when tables are empty."""
    results: list[ExtractedMeasurement] = []
    for param, pattern, unit in (
        ("efficiency", _EFFICIENCY_RE, "%"),
        ("power_factor", _PF_RE, None),
        ("temp_rise", _TEMP_RISE_RE, "K"),
        ("vibration", _VIBRATION_RE, "mm/s"),
    ):
        match = pattern.search(text or "")
        if not match:
            continue
        raw = match.group(1)
        unit_override = None
        if param == "vibration" and match.lastindex and match.lastindex >= 2:
            unit_override = match.group(2)
        results.append(
            ExtractedMeasurement(
                parameter=param,
                unit=unit_override or unit,
                rated_value=None,
                measured_value=raw,
                numeric_value=_to_float(raw),
                confidence=0.65,
            )
        )
    return results


def run_extractors(
    *,
    filename: str,
    folder_path: str = "",
    full_text: str = "",
    tables: list[dict[str, Any]] | None = None,
    doc_category: str | None = None,
) -> ExtractionBundle:
    """Run all Milestone 2.2 extractors and return a unified bundle."""
    text = full_text or ""
    entities: list[ExtractedEntity] = []
    entities.extend(
        extract_drawing_entities(filename=filename, text=text, folder_path=folder_path)
    )
    entities.extend(
        extract_motor_spec_fields(text, filename=filename, folder_path=folder_path)
    )
    entities.extend(extract_certification_fields(text))

    measurements = extract_measurements_from_tables(tables or [])
    if not measurements and (
        doc_category in {"test_report", "checklist"} or "test" in (doc_category or "")
    ):
        measurements = extract_measurements_from_text(text)
    elif not measurements:
        # Soft text scan for datasheets too
        soft = extract_measurements_from_text(text)
        measurements.extend(soft)

    standard = None
    serial = None
    iec = _IEC_STD_RE.search(text)
    if iec:
        standard = re.sub(r"\s+", " ", iec.group(1).upper())
    serial_match = _SERIAL_RE.search(text)
    if serial_match:
        serial = serial_match.group(1).upper()
        entities.append(
            ExtractedEntity(
                entity_type="serial_number",
                value=serial,
                normalized_value=serial,
                confidence=0.7,
                source="text",
            )
        )

    return ExtractionBundle(
        entities=entities,
        measurements=measurements,
        standard=standard,
        serial_number=serial,
    )
