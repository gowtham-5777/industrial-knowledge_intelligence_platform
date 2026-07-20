"""Explainable health/risk score (deterministic Python rules).

Note: ``health/routes.py`` is the unversioned HTTP liveness/readiness probe
surface mounted directly in ``main.py`` — unrelated to motor health scoring.
"""

from app.health.scoring import HealthScoringService

__all__ = ["HealthScoringService"]
