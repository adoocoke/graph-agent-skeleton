"""Keyword, semantic (BoW cosine), and hybrid (RRF) search over the graph."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .graph import SurvivorGraph

TOKEN_RE = re.compile(r"[a-z0-9_]+", re.I)


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "")]


def bag_of_words(text: str) -> Counter:
    return Counter(tokenize(text))


def cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[str]],
    k: int = 60,
) -> List[Tuple[str, float]]:
    """Classic RRF: score(d) = sum 1/(k + rank_i(d))."""
    scores: Dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))


class GraphSearch:
    def __init__(self, graph: SurvivorGraph) -> None:
        self.graph = graph
        self._docs = graph.indexable_docs()  # (id, type, text)
        self._bow = {doc_id: bag_of_words(text) for doc_id, _, text in self._docs}
        self._text = {doc_id: text for doc_id, _, text in self._docs}
        self._type = {doc_id: ntype for doc_id, ntype, _ in self._docs}

    def keyword_search(
        self,
        query: str,
        types: Optional[Sequence[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Exact / substring filter over node text and props."""
        tokens = tokenize(query)
        if not tokens:
            return []
        hits: List[Tuple[str, float, List[str]]] = []
        for doc_id, ntype, text in self._docs:
            if types and ntype not in types:
                continue
            matched = [t for t in tokens if t in text]
            if not matched:
                continue
            # Prefer more matched tokens + longer matches
            score = len(matched) / len(tokens) + 0.01 * sum(len(m) for m in matched)
            hits.append((doc_id, score, matched))
        hits.sort(key=lambda x: (-x[1], x[0]))
        return [self._format(doc_id, score, matched=m) for doc_id, score, m in hits[:limit]]

    def semantic_search(
        self,
        query: str,
        types: Optional[Sequence[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Token bag-of-words cosine similarity (tiny stand-in for embeddings)."""
        q = bag_of_words(query)
        if not q:
            return []
        hits: List[Tuple[str, float]] = []
        for doc_id, bow in self._bow.items():
            if types and self._type[doc_id] not in types:
                continue
            score = cosine(q, bow)
            if score > 0:
                hits.append((doc_id, score))
        hits.sort(key=lambda x: (-x[1], x[0]))
        return [self._format(doc_id, score) for doc_id, score in hits[:limit]]

    def hybrid_search(
        self,
        query: str,
        types: Optional[Sequence[str]] = None,
        limit: int = 10,
        rrf_k: int = 60,
    ) -> List[Dict[str, Any]]:
        """Reciprocal Rank Fusion of keyword + semantic rankings."""
        kw = self.keyword_search(query, types=types, limit=limit * 3)
        sem = self.semantic_search(query, types=types, limit=limit * 3)
        kw_ids = [h["id"] for h in kw]
        sem_ids = [h["id"] for h in sem]
        fused = reciprocal_rank_fusion([kw_ids, sem_ids], k=rrf_k)
        score_map = {doc_id: score for doc_id, score in fused}
        results = []
        for doc_id, score in fused[:limit]:
            item = self._format(doc_id, score)
            item["rrf_score"] = score
            item["in_keyword"] = doc_id in score_map and doc_id in kw_ids
            item["in_semantic"] = doc_id in sem_ids
            results.append(item)
        return results

    def _format(
        self,
        doc_id: str,
        score: float,
        matched: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        node = self.graph.get(doc_id)
        out: Dict[str, Any] = {
            "id": doc_id,
            "type": self._type.get(doc_id, "?"),
            "score": round(score, 4),
            "name": node.props.get("name", doc_id) if node else doc_id,
            "description": (node.props.get("description", "") if node else "")[:160],
        }
        if matched is not None:
            out["matched_tokens"] = matched
        if node and node.type == "Survivor":
            skills = [s.props.get("name", s.id) for s in self.graph.survivor_skills(doc_id)]
            biomes = [b.props.get("name", b.id) for b in self.graph.survivor_biomes(doc_id)]
            needs = [n.props.get("name", n.id) for n in self.graph.survivor_needs(doc_id)]
            out["skills"] = skills
            out["biomes"] = biomes
            out["needs"] = needs
        if node and node.type == "Skill":
            helpers = [
                s.props.get("name", s.id)
                for s in self.graph.survivors_with_skill(doc_id)
            ]
            treats = [
                n.props.get("name", n.id)
                for n in self.graph.neighbors(doc_id, "skill_treats_need")
            ]
            out["survivors"] = helpers
            out["treats"] = treats
        if node and node.type == "Need":
            treating = [
                s.props.get("name", s.id)
                for s in self.graph.skills_treating(doc_id)
            ]
            out["treated_by"] = treating
            out["urgency"] = node.props.get("urgency", "unknown")
        if node and node.type == "Biome":
            people = [
                s.props.get("name", s.id)
                for s in self.graph.survivors_in_biome(doc_id)
            ]
            out["survivors"] = people
        return out
