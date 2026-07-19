"""Path-based doc category / subtype hints (re-exports documents.classification)."""

from app.documents.classification import (
    classify_document,
    classify_path,
    extract_drawing_number,
    extract_motor_type_code,
    guess_mime_type,
    normalize_rel_path,
)

__all__ = [
    "classify_document",
    "classify_path",
    "extract_drawing_number",
    "extract_motor_type_code",
    "guess_mime_type",
    "normalize_rel_path",
]
