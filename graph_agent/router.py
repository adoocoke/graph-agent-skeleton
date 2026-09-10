"""Tiny heuristic agent router + optional fanout join demo."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .graph import SurvivorGraph
from .search import GraphSearch, tokenize

LOCATION_WORDS = {
    "mountain",
    "mountains",
    "alpine",
    "ridge",
    "fossilized",
    "fossils",
    "wetland",
    "wetlands",
    "marsh",
    "coast",
    "shore",
    "beach",
    "biome",
    "region",
    "location",
    "where",
    "nearby",
    "northern",
    "southern",
    "eastern",
}

CONCEPT_WORDS = {
    "heal",
    "healing",
    "injury",
    "injuries",
    "injured",
    "burn",
    "burns",
    "bleed",
    "bleeding",
    "fracture",
    "infection",
    "medicine",
    "medical",
    "doctor",
    "aid",
    "first",
    "trauma",
    "wound",
    "wounds",
    "hypothermia",
    "cold",
    "fever",
    "herbal",
    "herbalism",
    "skill",
    "skills",
    "need",
    "needs",
    "treat",
    "help",
    "rescue",
    "care",
}

EXACT_HINTS = {
    "named",
    "exact",
    "id",
    "filter",
    "has_skill",
    "in_biome",
    "has_need",
    "skill_treats_need",
    "dr.",
    "elena",
    "frost",
    "keyword",
}


def choose_tool(query: str) -> Tuple[str, str]:
    """Heuristics:
    - conceptual → semantic
    - location + concept → hybrid
    - exact filter → keyword
    """
    tokens = set(tokenize(query))
    q_lower = query.lower()
    has_location = bool(tokens & LOCATION_WORDS) or any(
        w in q_lower for w in ("mountain", "fossilized", "wetland", "coast")
    )
    has_concept = bool(tokens & CONCEPT_WORDS)
    has_exact = bool(tokens & EXACT_HINTS) or bool(
        re.search(r"\b(id:|name=|survivor:|skill:|need:|biome:)\b", q_lower)
    )

    if has_exact and not (has_location and has_concept):
        return "keyword_search", "exact/filter cues → keyword"
    if has_location and has_concept:
        return "hybrid_search", "location + concept → hybrid (RRF)"
    if has_concept:
        return "semantic_search", "conceptual query → semantic (BoW cosine)"
    if has_location:
        return "hybrid_search", "location-heavy → hybrid"
    # Default: semantic for open questions, keyword for short filters
    if len(tokens) <= 2:
        return "keyword_search", "short query → keyword"
    return "semantic_search", "open-ended → semantic"


class AgentRouter:
    def __init__(self, graph: SurvivorGraph) -> None:
        self.graph = graph
        self.search = GraphSearch(graph)

    def run(self, query: str, limit: int = 8) -> Dict[str, Any]:
        tool, reason = choose_tool(query)
        if tool == "keyword_search":
            hits = self.search.keyword_search(query, limit=limit)
        elif tool == "hybrid_search":
            hits = self.search.hybrid_search(query, limit=limit)
        else:
            hits = self.search.semantic_search(query, limit=limit)

        enriched = self._enrich_for_help(query, hits)
        return {
            "query": query,
            "tool": tool,
            "reason": reason,
            "results": hits,
            "enriched": enriched,
        }

    def _enrich_for_help(
        self, query: str, hits: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """If the question is about helping injuries, surface rescue matches."""
        tokens = set(tokenize(query))
        helpish = tokens & {
            "help",
            "injuries",
            "injury",
            "injured",
            "burns",
            "burn",
            "heal",
            "healing",
            "rescue",
            "who",
            "treat",
            "care",
        }
        if not helpish:
            return []

        need_keys = tokens & {
            "burns",
            "burn",
            "bleeding",
            "fracture",
            "infection",
            "hypothermia",
            "injuries",
            "injury",
            "wound",
            "wounds",
        }
        # Map injury-ish words to need keywords for fanout
        mapped = set()
        for t in need_keys:
            if t in ("injuries", "injury", "wound", "wounds"):
                mapped.update({"burns", "bleeding", "injury"})
            elif t in ("burn", "burns"):
                mapped.add("burns")
            else:
                mapped.add(t)
        if not mapped:
            mapped = {"burns", "bleeding", "injury"}

        biome_filter: Optional[str] = None
        for loc in ("mountain", "fossilized", "wetland", "coast", "alpine"):
            if loc in tokens or loc in query.lower():
                biome_filter = loc
                break

        matches = self.graph.rescue_matches(
            need_keywords=mapped or None,
            biome_filter=biome_filter,
        )
        # Dedupe by survivor+skill+need
        seen = set()
        uniq = []
        for m in matches:
            key = (m["survivor_id"], m["skill_id"], m["need_id"])
            if key in seen:
                continue
            seen.add(key)
            uniq.append(m)
        return uniq[:12]


def fanout_join_router(
    graph: SurvivorGraph,
    need_query: str = "burns",
    biome: Optional[str] = None,
) -> Dict[str, Any]:
    """Demo: fan-out join for rescue matching (need → skill → survivor [× biome])."""
    tokens = set(tokenize(need_query))
    matches = graph.rescue_matches(need_keywords=tokens or {"burns"}, biome_filter=biome)
    return {
        "demo": "fanout_join_router",
        "need_query": need_query,
        "biome": biome,
        "path": "Need <- skill_treats_need <- Skill <- has_skill <- Survivor (+ in_biome)",
        "matches": matches,
    }
