"""Parser handler protocol."""

from __future__ import annotations

from typing import Protocol

from app.indexing.models import ParseOutput
from app.indexing.tiers import ParserTier, RoutingContext


class ParserHandler(Protocol):
    """Callable parser for a selected tier."""

    tier: ParserTier
    name: str

    def parse(
        self,
        content: bytes,
        *,
        ctx: RoutingContext,
    ) -> ParseOutput: ...
