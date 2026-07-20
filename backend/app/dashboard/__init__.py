"""Fleet dashboard KPI aggregation API."""

from app.dashboard.routes import router
from app.dashboard.service import DashboardService

__all__ = ["DashboardService", "router"]
