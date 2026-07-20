"""LangGraph Industrial Copilot agent (Milestone 4.2)."""

from __future__ import annotations

import json
from typing import Any, TypedDict

from sqlalchemy.orm import Session

from app.agents.multi_hop import MultiHopPlanner
from app.agents.router import QueryRouter
from app.agents.tools import AgentTools
from app.agents.verify import NumericClaimVerifier
from app.citations.service import CitationService
from app.core.config import Settings, get_settings
from app.observability import get_logger

_logger = get_logger(__name__)


class CopilotState(TypedDict, total=False):
    query: str
    motor_id: str | None
    route: dict[str, Any]
    tool_results: dict[str, Any]
    answer: str
    reasoning: str
    citations: list[dict[str, Any]]
    confidence: float
    retrieval_trace_id: str | None
    verified: bool
    numeric_checks: list[dict[str, Any]]
    degraded: bool


class CopilotGraph:
    """LangGraph StateGraph: route → tools → synthesize → verify."""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.router = QueryRouter(session, self.settings)
        self.tools = AgentTools(session, self.settings)
        self.verifier = NumericClaimVerifier(session)
        self.planner = MultiHopPlanner()
        self.citations = CitationService(session)
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:
        try:
            from langgraph.graph import END, StateGraph
        except ImportError:
            _logger.warning("langgraph_unavailable_using_linear_fallback")
            return None

        graph = StateGraph(CopilotState)
        graph.add_node("route", self._node_route)
        graph.add_node("tools", self._node_tools)
        graph.add_node("synthesize", self._node_synthesize)
        graph.add_node("verify", self._node_verify)
        graph.set_entry_point("route")
        graph.add_edge("route", "tools")
        graph.add_edge("tools", "synthesize")
        graph.add_edge("synthesize", "verify")
        graph.add_edge("verify", END)
        return graph.compile()

    def run(
        self,
        query: str,
        *,
        motor_id: str | None = None,
    ) -> CopilotState:
        initial: CopilotState = {
            "query": query,
            "motor_id": motor_id,
            "tool_results": {},
            "citations": [],
            "confidence": 0.0,
            "degraded": False,
            "verified": False,
        }
        if self._graph is not None:
            return self._graph.invoke(initial)  # type: ignore[no-any-return]

        # Linear fallback without langgraph installed
        state = dict(initial)
        state.update(self._node_route(state))  # type: ignore[arg-type]
        state.update(self._node_tools(state))  # type: ignore[arg-type]
        state.update(self._node_synthesize(state))  # type: ignore[arg-type]
        state.update(self._node_verify(state))  # type: ignore[arg-type]
        return state  # type: ignore[return-value]

    def _node_route(self, state: CopilotState) -> dict[str, Any]:
        route = self.router.route(state["query"], motor_id=state.get("motor_id"))
        motor_id = state.get("motor_id") or route.entities.motor_id
        return {
            "route": route.model_dump(),
            "motor_id": motor_id,
        }

    def _node_tools(self, state: CopilotState) -> dict[str, Any]:
        route_data = state.get("route") or {}
        intent = route_data.get("intent", "OpenDomain")
        tools = list(route_data.get("tools") or ["search_knowledge", "get_motor_360"])
        motor_id = state.get("motor_id")
        entities = route_data.get("entities") or {}
        drawing = entities.get("drawing_number")

        # Multi-hop plan may add/reorder tools for demo questions
        plan = self.planner.plan_for(state["query"], intent=intent)
        if plan:
            tools = plan["tools"]

        results: dict[str, Any] = {}
        for name in tools:
            kwargs: dict[str, Any] = {}
            if name in {
                "get_motor_360",
                "get_motor_timeline",
                "get_test_history",
                "get_compliance_status",
                "traverse_motor_graph",
            }:
                if not motor_id:
                    results[name] = {"ok": False, "error": "motor_id required"}
                    continue
                kwargs["motor_id"] = motor_id
            elif name == "search_knowledge":
                kwargs["query"] = plan["search_query"] if plan else state["query"]
                kwargs["motor_id"] = motor_id
                kwargs["drawing_number"] = drawing
                if plan and plan.get("doc_category"):
                    kwargs["doc_category"] = plan["doc_category"]
            results[name] = self.tools.dispatch(name, **kwargs)

        return {"tool_results": results}

    def _node_synthesize(self, state: CopilotState) -> dict[str, Any]:
        tool_results = state.get("tool_results") or {}
        citations = self._collect_citations(tool_results)
        answer, reasoning, degraded = self._build_answer(state, citations)

        if (
            not degraded
            and self.settings.openai_api_key
            and self.settings.app_env != "test"
        ):
            llm = self._llm_synthesize(state, citations, tool_results)
            if llm:
                answer, reasoning = llm

        scores = [
            float(c.get("score") or 0.5)
            for c in citations
            if c.get("score") is not None
        ]
        coverage = 1.0 if citations else 0.35
        conf = self.citations.confidence_inputs(
            retrieval_scores=scores or [0.4],
            citation_coverage=coverage,
        )["confidence"]

        trace_id = None
        for tr in tool_results.values():
            if isinstance(tr, dict) and tr.get("retrieval_trace_id"):
                trace_id = tr["retrieval_trace_id"]
                break

        return {
            "answer": answer,
            "reasoning": reasoning,
            "citations": citations,
            "confidence": conf,
            "retrieval_trace_id": trace_id,
            "degraded": degraded,
        }

    def _node_verify(self, state: CopilotState) -> dict[str, Any]:
        from app.security.prompt_guard import verify_answer_citations

        motor_id = state.get("motor_id")
        answer = state.get("answer") or ""
        citations = state.get("citations") or []
        cite_check = verify_answer_citations(answer, citations)
        if cite_check.get("footer") and not cite_check.get("ok"):
            answer = f"{answer}{cite_check['footer']}"

        checks = self.verifier.verify_answer(answer, motor_id=motor_id)
        verified = all(c.get("ok", True) for c in checks) if checks else True
        if citations and not cite_check.get("ok"):
            verified = False
        confidence = float(state.get("confidence") or 0.5)
        if checks and not verified:
            confidence = min(confidence, 0.45)
            answer = (
                f"{answer}\n\n"
                "Note: one or more numeric claims could not be verified against "
                "structured test measurements — treat those values as provisional."
            )
        elif checks and verified:
            confidence = min(1.0, confidence + 0.05)
        return {
            "answer": answer,
            "verified": verified,
            "numeric_checks": checks,
            "confidence": round(confidence, 3),
        }

    def _collect_citations(self, tool_results: dict[str, Any]) -> list[dict[str, Any]]:
        citations: list[dict[str, Any]] = []
        seen: set[str] = set()
        for payload in tool_results.values():
            if not isinstance(payload, dict):
                continue
            for hit in payload.get("hits") or []:
                key = hit.get("citation") or hit.get("document_id")
                if not key or key in seen:
                    continue
                seen.add(str(key))
                citations.append(hit)
            for m in payload.get("measurements") or []:
                doc_id = m.get("document_id")
                if not doc_id or doc_id in seen:
                    continue
                seen.add(doc_id)
                citations.append(
                    {
                        "document_id": doc_id,
                        "chunk_id": None,
                        "citation": f"[{doc_id}:measurement]",
                        "text": (
                            f"{m.get('parameter')}="
                            f"{m.get('measured_value') or m.get('numeric_value')} "
                            f"{m.get('unit') or ''}"
                        ).strip(),
                        "score": 0.9,
                    }
                )
            for item in (payload.get("items") or [])[:5]:
                ev = item.get("evidence") if isinstance(item, dict) else None
                if not ev:
                    continue
                doc_id = ev.get("document_id")
                if doc_id and doc_id not in seen:
                    seen.add(doc_id)
                    citations.append(
                        {
                            "document_id": doc_id,
                            "title": ev.get("title"),
                            "text": item.get("title"),
                            "score": ev.get("confidence", 0.7),
                        }
                    )
        return citations[:12]

    def _build_answer(
        self,
        state: CopilotState,
        citations: list[dict[str, Any]],
    ) -> tuple[str, str, bool]:
        """Deterministic synthesis — always available without LLM."""
        route = state.get("route") or {}
        intent = route.get("intent", "OpenDomain")
        tools = state.get("tool_results") or {}
        parts: list[str] = []
        reasoning_bits: list[str] = []
        degraded = False

        if intent == "TestReportHistory" or "get_test_history" in tools:
            hist = tools.get("get_test_history") or {}
            measurements = hist.get("measurements") or []
            if measurements:
                eff = next(
                    (
                        m
                        for m in measurements
                        if "efficien" in (m.get("parameter") or "").lower()
                    ),
                    None,
                )
                temp = next(
                    (
                        m
                        for m in measurements
                        if "temp" in (m.get("parameter") or "").lower()
                        or "rise" in (m.get("parameter") or "").lower()
                    ),
                    None,
                )
                lines = []
                if eff:
                    lines.append(
                        f"Efficiency: "
                        f"{eff.get('measured_value') or eff.get('numeric_value')} "
                        f"{eff.get('unit') or ''}".strip()
                    )
                if temp:
                    lines.append(
                        f"Temperature rise: "
                        f"{temp.get('measured_value') or temp.get('numeric_value')} "
                        f"{temp.get('unit') or ''}".strip()
                    )
                if not lines:
                    for m in measurements[:5]:
                        lines.append(
                            f"{m.get('parameter')}: "
                            f"{m.get('measured_value') or m.get('numeric_value')} "
                            f"{m.get('unit') or ''}".strip()
                        )
                parts.append(
                    "From structured test measurements for this motor:\n- "
                    + "\n- ".join(lines)
                )
                reasoning_bits.append("Used get_test_history structured measurements.")
            else:
                parts.append(
                    "No structured test measurements are indexed for this motor yet."
                )
                degraded = True

        if intent == "Procedure" or "search_knowledge" in tools:
            search = tools.get("search_knowledge") or {}
            hits = search.get("hits") or []
            loto_hits = [
                h
                for h in hits
                if any(
                    k in (h.get("text") or "").lower()
                    or k in (h.get("title") or "").lower()
                    or k in (h.get("doc_category") or "").lower()
                    for k in ("loto", "lockout", "tagout", "procedure", "safety")
                )
            ] or hits[:3]
            if loto_hits and intent in {"Procedure", "OpenDomain", "Compliance"}:
                snippets = []
                for h in loto_hits[:3]:
                    cite = h.get("citation") or (
                        f"[{h.get('document_id')}]" if h.get("document_id") else ""
                    )
                    text = (h.get("text") or h.get("title") or "").strip()
                    if text:
                        snippets.append(f"{text[:280]} {cite}".strip())
                if snippets and intent == "Procedure":
                    parts.append(
                        "Applicable procedure evidence:\n- " + "\n- ".join(snippets)
                    )
                    reasoning_bits.append(
                        "Retrieved procedure / safety knowledge chunks."
                    )

        if intent == "Compliance" or "get_compliance_status" in tools:
            comp = tools.get("get_compliance_status") or {}
            items = comp.get("items") or []
            if items:
                met = [i for i in items if i.get("status") == "met"]
                gaps = comp.get("gaps") or []
                lines = [
                    f"{i['title']}: evidenced"
                    + (
                        f" via doc {i['evidence']['document_id']}"
                        if i.get("evidence")
                        else ""
                    )
                    for i in met[:5]
                ]
                if lines:
                    parts.append(
                        "Compliance evidence for this motor:\n- " + "\n- ".join(lines)
                    )
                if gaps:
                    parts.append(
                        "Open gaps: "
                        + ", ".join(
                            g.get("title") or g.get("requirement_code")
                            for g in gaps[:5]
                        )
                    )
                reasoning_bits.append(
                    f"Python compliance checklist coverage={comp.get('coverage')}"
                )

        if intent == "MotorLookup" or "get_motor_360" in tools:
            m360 = tools.get("get_motor_360") or {}
            motor = m360.get("motor") or {}
            if motor.get("code"):
                parts.append(
                    f"Motor {motor.get('name') or motor.get('code')}: "
                    f"frame {motor.get('frame_size')}, "
                    f"{motor.get('power_kw')} kW, "
                    f"{motor.get('voltage')}, "
                    f"{motor.get('ie_class')}."
                )
                reasoning_bits.append("Used Motor 360 registry specs.")

        if intent == "DrawingCrossRef":
            search = tools.get("search_knowledge") or {}
            graph = tools.get("traverse_motor_graph") or {}
            hits = search.get("hits") or []
            if hits:
                parts.append(
                    "Drawing cross-reference hits:\n- "
                    + "\n- ".join(
                        (h.get("text") or h.get("title") or str(h.get("document_id")))[
                            :200
                        ]
                        for h in hits[:4]
                    )
                )
            elif graph.get("ok"):
                parts.append("Graph neighborhood retrieved for this motor/drawing.")
            else:
                parts.append("No drawing cross-reference evidence found yet.")
                degraded = True

        if not parts:
            search = tools.get("search_knowledge") or {}
            hits = search.get("hits") or []
            if hits:
                parts.append(
                    "Retrieved industrial knowledge:\n- "
                    + "\n- ".join(
                        (h.get("text") or h.get("title") or "")[:240] for h in hits[:4]
                    )
                )
                reasoning_bits.append("Fallback OpenDomain synthesis from retrieval.")
            else:
                parts.append(
                    "Not available in indexed knowledge for the current motor scope."
                )
                degraded = True
                reasoning_bits.append("No tool evidence; honest empty response.")

        # Attach citation markers when available
        cite_suffix = ""
        marked = [c for c in citations if c.get("citation")]
        if marked:
            cite_suffix = "\n\nCitations: " + " ".join(
                c["citation"] for c in marked[:6]
            )

        answer = "\n\n".join(parts) + cite_suffix
        reasoning = "; ".join(reasoning_bits) or f"Intent={intent}"
        return answer, reasoning, degraded

    def _llm_synthesize(
        self,
        state: CopilotState,
        citations: list[dict[str, Any]],
        tool_results: dict[str, Any],
    ) -> tuple[str, str] | None:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.settings.openai_api_key)
            context = {
                "intent": (state.get("route") or {}).get("intent"),
                "motor_id": state.get("motor_id"),
                "citations": citations[:8],
                "tool_results": _compact_tools(tool_results),
            }
            prompt = (
                "You are Industrial Brain AI Copilot. Answer the engineer using ONLY "
                "the provided tool evidence. Cite sources as [doc_id:chunk_id] when "
                "available. If evidence is missing, say "
                "'Not available in indexed knowledge'. "
                "Return JSON with keys answer, reasoning.\n\n"
                f"Question: {state['query']}\n"
                f"Evidence JSON: {json.dumps(context, default=str)[:12000]}"
            )
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content or "{}"
            data = json.loads(raw)
            answer = str(data.get("answer") or "").strip()
            reasoning = str(data.get("reasoning") or "").strip()
            if answer:
                return answer, reasoning or "LLM synthesis over tool evidence"
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "copilot_llm_synthesize_failed", extra={"error": str(exc)}
            )
        return None


def _compact_tools(tool_results: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in tool_results.items():
        if not isinstance(v, dict):
            continue
        compact = {kk: vv for kk, vv in v.items() if kk != "subgraph"}
        if "measurements" in compact and isinstance(compact["measurements"], list):
            compact["measurements"] = compact["measurements"][:15]
        if "hits" in compact and isinstance(compact["hits"], list):
            compact["hits"] = compact["hits"][:6]
        out[k] = compact
    return out
