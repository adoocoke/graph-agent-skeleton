"""Minimal Agent Harness: tools + session + guardrails around the router.

In Graph Engineering vocabulary:
  Harness = scaffolding around the model/agent (tools, memory/session, guardrails).
  Loop    = one agent repeating reason→act→observe (we approximate with run()).
  Graph   = multi-node orchestration (see fanout_join_router / graph edges).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .graph import SurvivorGraph
from .router import AgentRouter, choose_tool
from .search import GraphSearch


ToolFn = Callable[..., Any]


@dataclass
class Turn:
    role: str  # "user" | "assistant" | "system"
    content: str
    meta: Dict[str, Any] = field(default_factory=dict)


class Session:
    """In-memory conversation / turn history (toy Memory)."""

    def __init__(self) -> None:
        self.turns: List[Turn] = []

    def add(self, role: str, content: str, **meta: Any) -> Turn:
        turn = Turn(role=role, content=content, meta=dict(meta))
        self.turns.append(turn)
        return turn

    def __len__(self) -> int:
        return len(self.turns)

    def as_dicts(self) -> List[Dict[str, Any]]:
        return [
            {"role": t.role, "content": t.content, "meta": t.meta} for t in self.turns
        ]


class ToolRegistry:
    """Register and call named tools (thin ADK-style tool surface)."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolFn] = {}
        self._docs: Dict[str, str] = {}

    def register(self, name: str, fn: ToolFn, doc: str = "") -> None:
        self._tools[name] = fn
        self._docs[name] = doc or (fn.__doc__ or "").strip()

    def list(self) -> List[Dict[str, str]]:
        return [{"name": n, "doc": self._docs.get(n, "")} for n in sorted(self._tools)]

    def call(self, name: str, **kwargs: Any) -> Any:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name](**kwargs)

    def names(self) -> List[str]:
        return sorted(self._tools)


@dataclass
class GuardrailResult:
    ok: bool
    reason: str = ""


class Guardrails:
    """Simple input/tool-call guardrails."""

    def __init__(
        self,
        max_query_chars: int = 500,
        max_tool_calls_per_turn: int = 3,
        blocked_words: Optional[List[str]] = None,
    ) -> None:
        self.max_query_chars = max_query_chars
        self.max_tool_calls_per_turn = max_tool_calls_per_turn
        self.blocked_words = [w.lower() for w in (blocked_words or [])]

    def check_query(self, query: str) -> GuardrailResult:
        q = (query or "").strip()
        if not q:
            return GuardrailResult(False, "empty query rejected")
        if len(q) > self.max_query_chars:
            return GuardrailResult(
                False, f"query too long (>{self.max_query_chars} chars)"
            )
        lower = q.lower()
        for w in self.blocked_words:
            if w and w in lower:
                return GuardrailResult(False, f"blocked term: {w}")
        return GuardrailResult(True)

    def check_tool_budget(self, calls_so_far: int) -> GuardrailResult:
        if calls_so_far >= self.max_tool_calls_per_turn:
            return GuardrailResult(
                False,
                f"max tool calls per turn ({self.max_tool_calls_per_turn}) reached",
            )
        return GuardrailResult(True)


class Harness:
    """Tools + session + guardrails wrapping AgentRouter / GraphSearch."""

    def __init__(
        self,
        graph: SurvivorGraph,
        *,
        session: Optional[Session] = None,
        guardrails: Optional[Guardrails] = None,
    ) -> None:
        self.graph = graph
        self.session = session or Session()
        self.guardrails = guardrails or Guardrails()
        self.router = AgentRouter(graph)
        self.search = GraphSearch(graph)
        self.tools = ToolRegistry()
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        self.tools.register(
            "keyword_search",
            lambda query, limit=8: self.search.keyword_search(query, limit=limit),
            "Exact / substring keyword filter over graph nodes",
        )
        self.tools.register(
            "semantic_search",
            lambda query, limit=8: self.search.semantic_search(query, limit=limit),
            "BoW cosine semantic search over node text",
        )
        self.tools.register(
            "hybrid_search",
            lambda query, limit=8: self.search.hybrid_search(query, limit=limit),
            "Keyword + semantic fused with Reciprocal Rank Fusion (RRF)",
        )

    def run(self, query: str, limit: int = 8) -> Dict[str, Any]:
        """One harness turn: guardrails → route → tool → session."""
        gate = self.guardrails.check_query(query)
        if not gate.ok:
            self.session.add("user", query, rejected=True, reason=gate.reason)
            self.session.add("assistant", gate.reason, ok=False)
            return {
                "via": "harness",
                "ok": False,
                "error": gate.reason,
                "query": query,
                "session_turns": len(self.session),
                "registered_tools": self.tools.names(),
            }

        self.session.add("user", query)
        tool_calls = 0

        budget = self.guardrails.check_tool_budget(tool_calls)
        if not budget.ok:
            payload = {
                "via": "harness",
                "ok": False,
                "error": budget.reason,
                "query": query,
                "session_turns": len(self.session),
            }
            self.session.add("assistant", budget.reason, ok=False)
            return payload

        # Prefer full router (includes rescue enrichment); still count as one tool path.
        tool_name, reason = choose_tool(query)
        result = self.router.run(query, limit=limit)
        tool_calls += 1

        payload: Dict[str, Any] = {
            "via": "harness",
            "ok": True,
            "query": result["query"],
            "tool": result["tool"],
            "reason": result["reason"],
            "results": result["results"],
            "enriched": result.get("enriched") or [],
            "session_turns": len(self.session) + 1,  # after assistant turn below
            "tool_calls_this_turn": tool_calls,
            "registered_tools": self.tools.names(),
            "routed_as": tool_name,
            "route_reason": reason,
        }
        summary = (
            f"tool={result['tool']} hits={len(result['results'])} "
            f"rescue={len(result.get('enriched') or [])}"
        )
        self.session.add(
            "assistant",
            summary,
            ok=True,
            tool=result["tool"],
            hits=len(result["results"]),
        )
        payload["session_turns"] = len(self.session)
        return payload
