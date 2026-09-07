"""Explicit score diagnostics for Knowledge v3 node routing."""

from __future__ import annotations

from hydra_engine.knowledge.nodes import discover_knowledge_nodes
from hydra_engine.knowledge.routing import context_terms, node_keyword_score


def route_prompt_match_diagnostics(prompt: str, paths) -> list[dict]:
    task_terms = frozenset(context_terms(prompt))
    entries = [
        {
            "node": node.logical_id,
            "title": node.title,
            "score": round(node_keyword_score(node, task_terms), 4),
        }
        for node in discover_knowledge_nodes(paths)
        if node.routable and node_keyword_score(node, task_terms) > 0
    ]
    return sorted(entries, key=lambda item: (-item["score"], item["node"]))
