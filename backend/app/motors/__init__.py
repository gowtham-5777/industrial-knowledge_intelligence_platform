"""Asset registry (motor hierarchy specialization)."""

from app.motors.routes import router
from app.motors.service import MotorRegistryService

__all__ = ["MotorRegistryService", "router"]
