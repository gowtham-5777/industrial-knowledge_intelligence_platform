"""Corpus ingestion — local filesystem (hackathon) with Drive-shaped contracts."""

from app.gdrive.routes import router as sync_router
from app.gdrive.sync_service import CorpusSyncService

__all__ = ["CorpusSyncService", "sync_router"]
