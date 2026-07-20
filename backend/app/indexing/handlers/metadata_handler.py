"""T3 — metadata-only path for CAD / 3D (no content extraction)."""

from __future__ import annotations

from pathlib import PurePosixPath

from app.documents.classification import extract_drawing_number, extract_motor_type_code
from app.indexing.models import ParseOutput
from app.indexing.tiers import ParserTier, RoutingContext


class MetadataOnlyHandler:
    """Skip blob text extraction; retain filename / drawing metadata only."""

    tier = ParserTier.T3
    name = "metadata-only"

    def parse(self, content: bytes, *, ctx: RoutingContext) -> ParseOutput:
        filename = ctx.filename or ""
        drawing = extract_drawing_number(filename)
        motor = extract_motor_type_code(filename, ctx.folder_path or "")
        return ParseOutput(
            tier=self.tier.value,
            parser_name=self.name,
            pages=[],
            tables=[],
            full_text="",
            skipped=True,
            warnings=["CAD/3D content parse skipped (Architecture T3)"],
            metadata={
                "filename": filename,
                "extension": PurePosixPath(filename).suffix.lower(),
                "size_bytes": len(content),
                "drawing_number": drawing,
                "motor_type_code": motor,
                "folder_path": ctx.folder_path,
                "doc_category": ctx.doc_category,
                "doc_subtype": ctx.doc_subtype,
            },
        )
