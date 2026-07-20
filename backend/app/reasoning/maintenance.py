"""Maintenance intelligence — test metric trends + anomaly patterns (4.3)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.extraction import PerformanceTestReport, TestMeasurement
from app.motors.documents import get_linked_documents, resolve_motor_model


class TrendPoint(BaseModel):
    parameter: str
    unit: str | None = None
    values: list[float] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    mean: float | None = None
    latest: float | None = None


class AnomalyOut(BaseModel):
    parameter: str
    value: float
    mean: float
    deviation_pct: float
    severity: str
    document_id: str | None = None
    rationale: str


class MaintenanceOut(BaseModel):
    motor_id: str
    motor_code: str
    trends: list[TrendPoint]
    anomalies: list[AnomalyOut]
    report_count: int
    measurement_count: int


# Soft thresholds for rule-assisted anomaly detection (not ML)
_ANOMALY_RULES: dict[str, dict[str, Any]] = {
    "efficiency": {"max_drop_pct": 3.0, "direction": "below"},
    "temperature": {"max_rise_pct": 15.0, "direction": "above"},
    "vibration": {"max_rise_pct": 20.0, "direction": "above"},
}


class MaintenanceService:
    """Aggregate IEC test measurements into trends + rule anomalies."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def analyze(self, motor_id: str) -> MaintenanceOut:
        model = resolve_motor_model(self.session, motor_id)
        docs = get_linked_documents(self.session, model)
        doc_ids = [d.id for d in docs]

        reports = []
        measurements: list[TestMeasurement] = []
        if doc_ids:
            reports = list(
                self.session.scalars(
                    select(PerformanceTestReport).where(
                        PerformanceTestReport.document_id.in_(doc_ids)
                    )
                ).all()
            )
            measurements = list(
                self.session.scalars(
                    select(TestMeasurement).where(
                        TestMeasurement.document_id.in_(doc_ids)
                    )
                ).all()
            )

        by_param: dict[str, list[TestMeasurement]] = defaultdict(list)
        for m in measurements:
            if m.numeric_value is not None:
                by_param[m.parameter or "unknown"].append(m)

        trends: list[TrendPoint] = []
        anomalies: list[AnomalyOut] = []
        for parameter, rows in sorted(by_param.items()):
            values = [
                float(r.numeric_value) for r in rows if r.numeric_value is not None
            ]
            if not values:
                continue
            mean = sum(values) / len(values)
            unit = rows[0].unit
            trends.append(
                TrendPoint(
                    parameter=parameter,
                    unit=unit,
                    values=values,
                    documents=[r.document_id for r in rows],
                    mean=round(mean, 4),
                    latest=values[-1],
                )
            )
            anomalies.extend(self._detect_anomalies(parameter, values, mean, rows))

        return MaintenanceOut(
            motor_id=model.id,
            motor_code=model.code,
            trends=trends,
            anomalies=anomalies,
            report_count=len(reports),
            measurement_count=len(measurements),
        )

    def _detect_anomalies(
        self,
        parameter: str,
        values: list[float],
        mean: float,
        rows: list[TestMeasurement],
    ) -> list[AnomalyOut]:
        if mean == 0 or len(values) < 1:
            return []
        key = next(
            (k for k in _ANOMALY_RULES if k in parameter.lower()),
            None,
        )
        out: list[AnomalyOut] = []
        latest = values[-1]
        deviation_pct = abs(latest - mean) / abs(mean) * 100.0
        if key is None:
            # Generic: flag >25% deviation from mean
            if deviation_pct >= 25.0:
                out.append(
                    AnomalyOut(
                        parameter=parameter,
                        value=latest,
                        mean=round(mean, 4),
                        deviation_pct=round(deviation_pct, 2),
                        severity="medium",
                        document_id=rows[-1].document_id if rows else None,
                        rationale=(
                            f"{parameter} latest value {latest} deviates "
                            f"{deviation_pct:.1f}% from mean {mean:.3f}"
                        ),
                    )
                )
            return out

        rule = _ANOMALY_RULES[key]
        threshold = float(rule.get("max_drop_pct") or rule.get("max_rise_pct") or 15)
        direction = rule["direction"]
        triggered = False
        if direction == "below" and latest < mean and deviation_pct >= threshold:
            triggered = True
        if direction == "above" and latest > mean and deviation_pct >= threshold:
            triggered = True
        # Also flag single-point absolute rules when only one measurement
        if len(values) == 1 and key == "vibration" and latest > 4.5:
            triggered = True
            deviation_pct = max(deviation_pct, 20.0)

        if triggered:
            severity = "high" if deviation_pct >= threshold * 1.5 else "medium"
            out.append(
                AnomalyOut(
                    parameter=parameter,
                    value=latest,
                    mean=round(mean, 4),
                    deviation_pct=round(deviation_pct, 2),
                    severity=severity,
                    document_id=rows[-1].document_id if rows else None,
                    rationale=(
                        f"Rule-assisted anomaly on {parameter}: "
                        f"latest={latest}, mean={mean:.3f}, "
                        f"deviation={deviation_pct:.1f}% (threshold {threshold}%)"
                    ),
                )
            )
        return out
