"""CLI: python -m graph_agent "Who can help with injuries?" """

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

from .harness import Harness
from .router import fanout_join_router
from .seed import build_seed_graph


def format_results(payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    if payload.get("via") == "harness":
        lines.append(
            f"Harness: on  | session_turns={payload.get('session_turns')} "
            f"| tools={','.join(payload.get('registered_tools') or [])}"
        )
    if not payload.get("ok", True):
        lines.append(f"Query : {payload.get('query')}")
        lines.append(f"Blocked: {payload.get('error')}")
        return "\n".join(lines)

    lines.append(f"Query : {payload['query']}")
    lines.append(f"Tool  : {payload['tool']}  ({payload['reason']})")
    lines.append("")
    lines.append("=== Search hits ===")
    results = payload.get("results") or []
    if not results:
        lines.append("  (no hits)")
    for i, hit in enumerate(results, 1):
        name = hit.get("name", hit.get("id"))
        lines.append(
            f"  {i}. [{hit.get('type')}] {name}  score={hit.get('score')}"
        )
        if hit.get("description"):
            lines.append(f"      {hit['description']}")
        extras = []
        for key in ("skills", "biomes", "needs", "survivors", "treats", "treated_by", "urgency"):
            if hit.get(key):
                extras.append(f"{key}={hit[key]}")
        if extras:
            lines.append("      " + "; ".join(extras))
        if hit.get("matched_tokens"):
            lines.append(f"      matched={hit['matched_tokens']}")

    enriched = payload.get("enriched") or []
    if enriched:
        lines.append("")
        lines.append("=== Rescue matches (fan-out join) ===")
        for i, m in enumerate(enriched, 1):
            biomes = ", ".join(m.get("biomes") or []) or "?"
            lines.append(
                f"  {i}. {m['survivor']} — skill={m['skill']} "
                f"treats need={m['need']} (urgency={m.get('urgency')}) "
                f"@ [{biomes}]"
            )
    return "\n".join(lines)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m graph_agent",
        description="Minimal Graph Agent: harness (tools+session+guardrails) + graph search",
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="Who can help with injuries?",
        help="Natural language query",
    )
    parser.add_argument(
        "--fanout",
        action="store_true",
        help="Run fanout_join_router demo instead of the harness",
    )
    parser.add_argument(
        "--biome",
        default=None,
        help="Optional biome filter for --fanout (e.g. mountain)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSON",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=8,
        help="Max search hits",
    )
    args = parser.parse_args(argv)

    graph = build_seed_graph()

    if args.fanout:
        payload = fanout_join_router(graph, need_query=args.query, biome=args.biome)
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(f"Fanout demo | need={payload['need_query']} | biome={payload['biome']}")
            print(f"Path: {payload['path']}")
            for i, m in enumerate(payload["matches"], 1):
                biomes = ", ".join(m.get("biomes") or [])
                print(
                    f"  {i}. {m['survivor']} / {m['skill']} → {m['need']} "
                    f"({m.get('urgency')}) @ {biomes}"
                )
        return 0

    harness = Harness(graph)
    payload = harness.run(args.query, limit=args.limit)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(format_results(payload))
    return 0 if payload.get("ok", True) else 2


if __name__ == "__main__":
    sys.exit(main())
