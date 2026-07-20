"""Multi-hop retrieval plans for Architecture §16 demo questions (Milestone 4.7)."""

from __future__ import annotations

import re
from typing import Any

_DEMO_PLANS: list[dict[str, Any]] = [
    {
        "id": "demo_efficiency_temp",
        "pattern": re.compile(
            r"efficiency.*(temp|temperature)|temperature rise|latest test report",
            re.I,
        ),
        "tools": ["get_test_history", "search_knowledge", "get_motor_360"],
        "search_query": "efficiency temperature rise IEC 60034 test report",
        "doc_category": "test_report",
    },
    {
        "id": "demo_loto",
        "pattern": re.compile(
            r"loto|lockout|tagout|before maintain",
            re.I,
        ),
        "tools": ["search_knowledge", "get_compliance_status", "get_motor_timeline"],
        "search_query": "LOTO lockout tagout procedure before motor maintenance",
        "doc_category": "safety",
    },
    {
        "id": "demo_atex",
        "pattern": re.compile(
            r"atex|certification.*regulation|which regulation",
            re.I,
        ),
        "tools": ["get_compliance_status", "search_knowledge", "get_motor_360"],
        "search_query": "ATEX certification regulation explosive atmosphere",
        "doc_category": "certificate",
    },
]


class MultiHopPlanner:
    """Select ordered tool + retrieval plans for known multi-hop demo questions."""

    def plan_for(
        self, query: str, *, intent: str | None = None
    ) -> dict[str, Any] | None:
        text = query or ""
        for plan in _DEMO_PLANS:
            if plan["pattern"].search(text):
                return {
                    "id": plan["id"],
                    "tools": list(plan["tools"]),
                    "search_query": plan["search_query"],
                    "doc_category": plan.get("doc_category"),
                    "intent_hint": intent,
                }
        return None

    def list_plans(self) -> list[dict[str, Any]]:
        return [
            {
                "id": p["id"],
                "tools": p["tools"],
                "search_query": p["search_query"],
                "doc_category": p.get("doc_category"),
            }
            for p in _DEMO_PLANS
        ]
