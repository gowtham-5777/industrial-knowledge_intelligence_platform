"""Asset 360 aggregation API (single-asset intelligence bundle)."""

from app.motor360.routes import router
from app.motor360.service import Motor360Service

__all__ = ["Motor360Service", "router"]
