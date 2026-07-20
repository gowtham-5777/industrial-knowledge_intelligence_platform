"""Numeric claim verification against test_measurements (Milestone 4.7)."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.extraction import TestMeasurement
from app.motors.documents import get_linked_documents, resolve_motor_model
from app.observability import get_logger

_logger = get_logger(__name__)

_NUMBER_RE = re.compile(
    r"(?P<label>efficiency|temperature\s*rise|temp(?:erature)?\s*rise|vibration|"
    r"power\s*factor|voltage|current|speed|power)"
    r"[^\d%]{0,24}"
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>%|kW|V|A|rpm|K|°C|C)?",
    re.IGNORECASE,
)

_PARAM_ALIASES: dict[str, tuple[str, ...]] = {
    "efficiency": ("efficiency", "eff"),
    "temperature rise": ("temp", "temperature", "rise", "dt"),
    "temp rise": ("temp", "temperature", "rise"),
    "vibration": ("vibration", "vib"),
    "power factor": ("power factor", "pf", "cos"),
    "voltage": ("voltage", "v"),
    "current": ("current", "amp"),
    "speed": ("speed", "rpm"),
    "power": ("power", "kw"),
}


class NumericClaimVerifier:
    """Ensure numeric claims in answers align with structured measurements."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def verify_answer(
        self,
        answer: str,
        *,
        motor_id: str | None = None,
        tolerance: float = 0.05,
    ) -> list[dict[str, Any]]:
        claims = list(_NUMBER_RE.finditer(answer or ""))
        if not claims or not motor_id:
            return []

        measurements = self._load_measurements(motor_id)
        if not measurements:
            return [
                {
                    "claim": m.group(0),
                    "ok": True,
                    "skipped": True,
                    "reason": "no structured measurements to verify against",
                }
                for m in claims
            ]

        results: list[dict[str, Any]] = []
        for match in claims:
            label = re.sub(r"\s+", " ", match.group("label").lower())
            value = float(match.group("value"))
            unit = (match.group("unit") or "").lower()
            aliases = _PARAM_ALIASES.get(label, (label,))
            candidates = [
                m
                for m in measurements
                if any(a in (m.parameter or "").lower() for a in aliases)
            ]
            if not candidates:
                results.append(
                    {
                        "claim": match.group(0),
                        "ok": True,
                        "skipped": True,
                        "reason": f"no measurement for {label}",
                    }
                )
                continue

            best = candidates[0]
            expected = best.numeric_value
            if expected is None and best.measured_value:
                try:
                    expected = float(
                        re.search(r"\d+(?:\.\d+)?", best.measured_value).group(0)  # type: ignore[union-attr]
                    )
                except Exception:  # noqa: BLE001
                    expected = None

            if expected is None:
                results.append(
                    {
                        "claim": match.group(0),
                        "ok": True,
                        "skipped": True,
                        "reason": "measurement not numeric",
                    }
                )
                continue

            rel = abs(value - expected) / max(abs(expected), 1e-6)
            ok = rel <= tolerance or abs(value - expected) < 0.5
            results.append(
                {
                    "claim": match.group(0),
                    "label": label,
                    "claimed_value": value,
                    "unit": unit,
                    "expected_value": expected,
                    "parameter": best.parameter,
                    "document_id": best.document_id,
                    "ok": ok,
                    "relative_error": round(rel, 4),
                }
            )
        return results

    def _load_measurements(self, motor_id: str) -> list[TestMeasurement]:
        try:
            model = resolve_motor_model(self.session, motor_id)
            docs = get_linked_documents(self.session, model)
            doc_ids = [d.id for d in docs]
            if not doc_ids:
                return []
            return list(
                self.session.scalars(
                    select(TestMeasurement).where(
                        TestMeasurement.document_id.in_(doc_ids)
                    )
                ).all()
            )
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "numeric_verify_load_failed", extra={"error": str(exc)}
            )
            return []
