"""In-memory survivor knowledge graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class Node:
    id: str
    type: str  # Survivor | Skill | Need | Biome
    props: Dict[str, Any] = field(default_factory=dict)

    def text_blob(self) -> str:
        parts = [self.id, self.type]
        for k, v in self.props.items():
            parts.append(f"{k}:{v}")
        return " ".join(str(p) for p in parts)


@dataclass
class Edge:
    src: str
    rel: str  # has_skill | in_biome | has_need | skill_treats_need
    dst: str
    props: Dict[str, Any] = field(default_factory=dict)


class SurvivorGraph:
    """Simple directed multi-relational graph kept entirely in memory."""

    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._adj: Dict[str, List[Edge]] = {}
        self._rev: Dict[str, List[Edge]] = {}

    def add_node(self, node_id: str, ntype: str, **props: Any) -> Node:
        node = Node(id=node_id, type=ntype, props=props)
        self.nodes[node_id] = node
        self._adj.setdefault(node_id, [])
        self._rev.setdefault(node_id, [])
        return node

    def add_edge(self, src: str, rel: str, dst: str, **props: Any) -> Edge:
        if src not in self.nodes or dst not in self.nodes:
            raise KeyError(f"Missing node for edge {src} -[{rel}]-> {dst}")
        edge = Edge(src=src, rel=rel, dst=dst, props=props)
        self.edges.append(edge)
        self._adj[src].append(edge)
        self._rev[dst].append(edge)
        return edge

    def get(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    def by_type(self, ntype: str) -> List[Node]:
        return [n for n in self.nodes.values() if n.type == ntype]

    def out_edges(self, node_id: str, rel: Optional[str] = None) -> List[Edge]:
        edges = self._adj.get(node_id, [])
        if rel is None:
            return list(edges)
        return [e for e in edges if e.rel == rel]

    def in_edges(self, node_id: str, rel: Optional[str] = None) -> List[Edge]:
        edges = self._rev.get(node_id, [])
        if rel is None:
            return list(edges)
        return [e for e in edges if e.rel == rel]

    def neighbors(self, node_id: str, rel: Optional[str] = None) -> List[Node]:
        return [self.nodes[e.dst] for e in self.out_edges(node_id, rel)]

    def reverse_neighbors(self, node_id: str, rel: Optional[str] = None) -> List[Node]:
        return [self.nodes[e.src] for e in self.in_edges(node_id, rel)]

    def survivors_with_skill(self, skill_id: str) -> List[Node]:
        return self.reverse_neighbors(skill_id, "has_skill")

    def skills_treating(self, need_id: str) -> List[Node]:
        return self.reverse_neighbors(need_id, "skill_treats_need")

    def survivors_in_biome(self, biome_id: str) -> List[Node]:
        return self.reverse_neighbors(biome_id, "in_biome")

    def survivor_skills(self, survivor_id: str) -> List[Node]:
        return self.neighbors(survivor_id, "has_skill")

    def survivor_needs(self, survivor_id: str) -> List[Node]:
        return self.neighbors(survivor_id, "has_need")

    def survivor_biomes(self, survivor_id: str) -> List[Node]:
        return self.neighbors(survivor_id, "in_biome")

    def indexable_docs(self) -> List[Tuple[str, str, str]]:
        """Return (node_id, type, searchable_text) for skills and needs."""
        docs: List[Tuple[str, str, str]] = []
        for n in self.nodes.values():
            if n.type in ("Skill", "Need", "Biome", "Survivor"):
                text = " ".join(
                    [
                        n.id,
                        n.type,
                        n.props.get("name", ""),
                        n.props.get("description", ""),
                        n.props.get("aliases", ""),
                        n.props.get("keywords", ""),
                        n.props.get("urgency", ""),
                        n.props.get("region", ""),
                    ]
                )
                docs.append((n.id, n.type, text.lower()))
        return docs

    def rescue_matches(
        self,
        need_keywords: Optional[Set[str]] = None,
        biome_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fan-out join: needs <- skill_treats_need <- skills <- has_skill <- survivors
        optionally filtered by biome.
        """
        need_keywords = need_keywords or set()
        results: List[Dict[str, Any]] = []
        for need in self.by_type("Need"):
            blob = need.text_blob().lower()
            if need_keywords and not any(k.lower() in blob for k in need_keywords):
                continue
            treating = self.skills_treating(need.id)
            for skill in treating:
                helpers = self.survivors_with_skill(skill.id)
                for helper in helpers:
                    biomes = self.survivor_biomes(helper.id)
                    biome_ids = [b.id for b in biomes]
                    biome_names = [b.props.get("name", b.id) for b in biomes]
                    if biome_filter:
                        bf = biome_filter.lower()
                        if not any(
                            bf in bid.lower() or bf in name.lower()
                            for bid, name in zip(biome_ids, biome_names)
                        ):
                            continue
                    results.append(
                        {
                            "survivor": helper.props.get("name", helper.id),
                            "survivor_id": helper.id,
                            "skill": skill.props.get("name", skill.id),
                            "skill_id": skill.id,
                            "need": need.props.get("name", need.id),
                            "need_id": need.id,
                            "urgency": need.props.get("urgency", "unknown"),
                            "biomes": biome_names,
                        }
                    )
        return results
