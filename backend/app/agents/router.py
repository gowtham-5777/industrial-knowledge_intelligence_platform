"""Query intent classification + entity linking (Milestone 4.1)."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.repositories.motors import MotorModelRepository
from app.observability import get_logger

_logger = get_logger(__name__)

# Drawing-number patterns common in ABB LV motors corpus
_DRAWING_RE = re.compile(
    r"\b((?:3GZF|9AKK|3GAA|3GAB)[A-Z0-9\-]{4,})\b",
    re.IGNORECASE,
)
_SERIAL_RE = re.compile(r"\b(?:S/?N|serial)[:\s#]*([A-Z0-9\-]{5,})\b", re.IGNORECASE)
_MODEL_RE = re.compile(
    r"\b(M3BP\s?\d{3}[A-Z0-9]+|Low_Voltage_Motor-\d{3})\b",
    re.IGNORECASE,
)


class QueryIntent(StrEnum):
    MOTOR_LOOKUP = "MotorLookup"
    TEST_REPORT_HISTORY = "TestReportHistory"
    PROCEDURE = "Procedure"
    RCA = "RCA"
    COMPLIANCE = "Compliance"
    DRAWING_CROSS_REF = "DrawingCrossRef"
    OPEN_DOMAIN = "OpenDomain"


class LinkedEntities(BaseModel):
    motor_id: str | None = None
    motor_code: str | None = None
    serial_number: str | None = None
    drawing_number: str | None = None
    aliases_matched: list[str] = Field(default_factory=list)


class RouteResult(BaseModel):
    intent: QueryIntent
    confidence: float
    entities: LinkedEntities
    tools: list[str] = Field(default_factory=list)
    model_tier: str = "fast"  # fast | premium
    rationale: str = ""


_INTENT_PATTERNS: list[tuple[QueryIntent, tuple[str, ...], list[str], str]] = [
    (
        QueryIntent.DRAWING_CROSS_REF,
        ("drawing", "3gzf", "9akk", "cross-ref", "cross ref", "dwg"),
        ["search_knowledge", "traverse_motor_graph", "get_motor_360"],
        "fast",
    ),
    (
        QueryIntent.TEST_REPORT_HISTORY,
        (
            "efficiency",
            "temperature rise",
            "temp rise",
            "vibration",
            "test report",
            "measurement",
            "iec 60034",
            "power factor",
        ),
        ["get_test_history", "search_knowledge", "get_motor_360"],
        "fast",
    ),
    (
        QueryIntent.PROCEDURE,
        (
            "loto",
            "lockout",
            "tagout",
            "sop",
            "procedure",
            "installation",
            "maintain",
            "maintenance step",
            "before maintaining",
        ),
        ["search_knowledge", "get_motor_timeline", "get_motor_360"],
        "fast",
    ),
    (
        QueryIntent.COMPLIANCE,
        (
            "atex",
            "certification",
            "certificate",
            "regulation",
            "compliance",
            "ce mark",
            "directive",
        ),
        ["get_compliance_status", "search_knowledge", "get_motor_360"],
        "premium",
    ),
    (
        QueryIntent.RCA,
        (
            "root cause",
            "why did",
            "anomaly",
            "failed",
            "failure",
            "rca",
            "5 why",
            "five why",
        ),
        ["get_test_history", "search_knowledge", "get_compliance_status"],
        "premium",
    ),
    (
        QueryIntent.MOTOR_LOOKUP,
        ("what is this motor", "specs", "frame size", "rated power", "model"),
        ["get_motor_360", "get_motor_timeline"],
        "fast",
    ),
]

_INTENT_TOOL_MAP: dict[QueryIntent, list[str]] = {
    intent: tools for intent, _kw, tools, _tier in _INTENT_PATTERNS
}
_INTENT_TOOL_MAP[QueryIntent.OPEN_DOMAIN] = [
    "search_knowledge",
    "get_motor_360",
    "traverse_motor_graph",
]


class QueryRouter:
    """Classify NL queries and link motor / drawing / serial entities."""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.motors = MotorModelRepository(session)

    def route(
        self,
        query: str,
        *,
        motor_id: str | None = None,
    ) -> RouteResult:
        entities = self.link_entities(query, motor_id=motor_id)
        intent, confidence, rationale = self.classify(query)
        tools = list(
            _INTENT_TOOL_MAP.get(intent, _INTENT_TOOL_MAP[QueryIntent.OPEN_DOMAIN])
        )
        tier = (
            "premium" if intent in {QueryIntent.RCA, QueryIntent.COMPLIANCE} else "fast"
        )

        # Optional fast-model confirmation when confidence is borderline
        if confidence < 0.55 and self._fast_model_available():
            llm_intent = self._llm_classify(query)
            if llm_intent is not None:
                intent = llm_intent
                confidence = max(confidence, 0.7)
                rationale = f"{rationale}; confirmed by fast model"
                tools = list(_INTENT_TOOL_MAP.get(intent, tools))
                tier = (
                    "premium"
                    if intent in {QueryIntent.RCA, QueryIntent.COMPLIANCE}
                    else "fast"
                )

        return RouteResult(
            intent=intent,
            confidence=round(confidence, 3),
            entities=entities,
            tools=tools,
            model_tier=tier,
            rationale=rationale,
        )

    def classify(self, query: str) -> tuple[QueryIntent, float, str]:
        text = (query or "").lower().strip()
        if not text:
            return QueryIntent.OPEN_DOMAIN, 0.3, "empty query"

        if _DRAWING_RE.search(query or ""):
            return (
                QueryIntent.DRAWING_CROSS_REF,
                0.92,
                "drawing-number pattern detected",
            )

        best: QueryIntent | None = None
        best_hits = 0
        best_kw = ""
        for intent, keywords, _tools, _tier in _INTENT_PATTERNS:
            hits = sum(1 for kw in keywords if kw in text)
            if hits > best_hits:
                best = intent
                best_hits = hits
                best_kw = next(kw for kw in keywords if kw in text)

        if best is None or best_hits == 0:
            return QueryIntent.OPEN_DOMAIN, 0.45, "no strong keyword match"

        confidence = min(0.55 + 0.15 * best_hits, 0.95)
        return best, confidence, f"matched '{best_kw}' (+{best_hits - 1} more)"

    def link_entities(
        self,
        query: str,
        *,
        motor_id: str | None = None,
    ) -> LinkedEntities:
        entities = LinkedEntities()
        q = query or ""

        drawing = _DRAWING_RE.search(q)
        if drawing:
            entities.drawing_number = drawing.group(1).upper()

        serial = _SERIAL_RE.search(q)
        if serial:
            entities.serial_number = serial.group(1).upper()

        model_m = _MODEL_RE.search(q)
        if model_m:
            code = model_m.group(1).replace(" ", "").upper()
            if code.startswith("LOW_VOLTAGE"):
                # preserve original casing for Low_Voltage_Motor-NNN
                code = model_m.group(1)
            entities.motor_code = code
            entities.aliases_matched.append(model_m.group(1))

        if motor_id:
            motor = self.motors.get_by_id(motor_id) or self.motors.get_by_code(motor_id)
            if motor:
                entities.motor_id = motor.id
                entities.motor_code = motor.code
                return entities

        # Alias / code resolution from free text tokens
        tokens = re.findall(r"[A-Za-z0-9_\-]{4,}", q)
        for token in tokens:
            resolved = self.motors.resolve_alias(token) or self.motors.get_by_code(
                token
            )
            if resolved is not None:
                entities.motor_id = resolved.id
                entities.motor_code = resolved.code
                entities.aliases_matched.append(token)
                break

        if entities.motor_code and not entities.motor_id:
            motor = self.motors.get_by_code(entities.motor_code)
            if motor:
                entities.motor_id = motor.id

        return entities

    def _fast_model_available(self) -> bool:
        return bool(
            (self.settings.google_api_key or self.settings.openai_api_key)
            and self.settings.app_env != "test"
        )

    def _llm_classify(self, query: str) -> QueryIntent | None:
        """Optional fast-model routing (Gemini Flash or OpenAI mini)."""
        labels = ", ".join(i.value for i in QueryIntent)
        prompt = (
            "Classify the industrial engineering question into exactly one intent "
            f"from: {labels}. Reply with only the intent name.\n\nQuestion: {query}"
        )
        try:
            if self.settings.openai_api_key:
                from openai import OpenAI

                client = OpenAI(api_key=self.settings.openai_api_key)
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=20,
                )
                raw = (resp.choices[0].message.content or "").strip()
                return (
                    QueryIntent(raw) if raw in {i.value for i in QueryIntent} else None
                )
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "fast_model_classify_failed", extra={"error": str(exc)}
            )
        return None

    def to_dict(self, result: RouteResult) -> dict[str, Any]:
        return result.model_dump()
