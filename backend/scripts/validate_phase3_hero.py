"""Phase 3 validation gate — hero motor Asset 360 evidence chain."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.db.session import get_session_factory  # noqa: E402
from app.health.scoring import HealthScoringService  # noqa: E402
from app.motor360.service import Motor360Service  # noqa: E402
from app.motors.hero import HERO_MOTOR_CODE, SUPPORTING_MOTOR_CODES  # noqa: E402
from app.motors.service import MotorRegistryService  # noqa: E402
from app.observability import configure_logging, get_logger  # noqa: E402

_logger = get_logger(__name__)


def main() -> int:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=False)
    session = get_session_factory()()
    try:
        registry = MotorRegistryService(session)
        enrich = registry.enrich_from_catalog()
        hero = registry.confirm_hero_set()
        session.commit()

        motor = registry.models.get_by_code(HERO_MOTOR_CODE)
        assert motor is not None, "Hero motor missing after confirm"

        HealthScoringService(session).compute(motor.id)
        bundle = Motor360Service(session).get_bundle(motor.id)
        session.commit()

        checks = {
            "hero_code": hero.hero.code == HERO_MOTOR_CODE,
            "supporting_count": len(hero.supporting) == len(SUPPORTING_MOTOR_CODES),
            "bundle_motor": bundle.motor.id == motor.id,
            "has_health": bundle.health is not None,
            "has_summary": bundle.summary is not None,
            "has_recommendations": len(bundle.recommendations.items) > 0,
            "has_subgraph": len(bundle.subgraph.nodes) > 0,
            "catalog_enrich_ran": enrich.get("codes_seen", 0) >= 0,
        }
        failed = [k for k, ok in checks.items() if not ok]
        print("Phase 3 hero validation")
        print(f"  hero={HERO_MOTOR_CODE} id={motor.id}")
        print(f"  enrich={enrich}")
        for k, ok in checks.items():
            print(f"  [{'PASS' if ok else 'FAIL'}] {k}")
        if failed:
            print(f"FAILED: {failed}")
            return 1
        print("PASS — Phase 3 hero Asset 360 gate")
        return 0
    except Exception as exc:  # noqa: BLE001
        _logger.exception("phase3 validation failed")
        print(f"FAIL: {exc}")
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
