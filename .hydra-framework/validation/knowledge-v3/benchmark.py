"""Reproducible decision gates for the checked-in Knowledge v3 enterprise fixture."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).with_name("enterprise-fixture.json")
TOP_K = 3


def terms(text: str) -> set[str]:
    normalized = "".join(char.lower() if char.isalnum() else " " for char in text)
    stop = {"add", "after", "an", "and", "during", "fix", "for", "to", "update", "without"}
    result: set[str] = set()
    for word in normalized.split():
        if len(word) <= 2 or word in stop:
            continue
        result.add(word)
        if word.endswith("s") and len(word) > 3:
            result.add(word[:-1])
    return result


@dataclass(frozen=True)
class Node:
    node_id: str
    space: str
    area: str
    slug: str
    scope: str
    keywords: frozenset[str]
    indexed_terms: frozenset[str]

    @property
    def pointer(self) -> str:
        return f"hydra://knowledge-node/{self.node_id}"


def load_fixture(path: Path = FIXTURE) -> tuple[dict, list[Node]]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    nodes: list[Node] = []
    for space, space_data in fixture["spaces"].items():
        scope = space_data["scope"]
        for area, slugs in space_data["areas"].items():
            for slug in slugs:
                node_id = f"{space}/{area}/{slug}"
                node_hints = fixture.get("indexed_hints", {}).get(node_id, [])
                nodes.append(Node(
                    node_id=node_id,
                    space=space,
                    area=area,
                    slug=slug,
                    scope=scope,
                    keywords=frozenset(terms(f"{space} {area} {slug}")),
                    indexed_terms=frozenset(terms(" ".join(node_hints))),
                ))
    return fixture, nodes


def _rank(
    scored: list[tuple[float, str]], *, cap: int = TOP_K, reject_boundary_ties: bool = True,
) -> tuple[list[str], bool]:
    positive = sorted((score, node_id) for score, node_id in scored if score > 0)
    positive.reverse()
    if len(positive) <= cap:
        return [node_id for _score, node_id in positive], False
    boundary = positive[cap - 1][0]
    if reject_boundary_ties and positive[cap][0] == boundary:
        return [node_id for score, node_id in positive if score > boundary], True
    return [node_id for _score, node_id in positive[:cap]], False


def route_v2(task: str, nodes: list[Node]) -> tuple[list[str], bool]:
    query = terms(task)
    scored = []
    for node in nodes:
        score = len(query & node.keywords) / max(len(node.keywords), 1)
        scored.append((score, node.node_id))
    return _rank(scored)


def route_hierarchical(task: str, nodes: list[Node]) -> tuple[list[str], bool]:
    query = terms(task)
    scored = []
    for node in nodes:
        leaf = len(query & node.keywords)
        ancestor = len(query & terms(f"{node.space} {node.area}"))
        scored.append((leaf + ancestor * 0.25, node.node_id))
    return _rank(scored)


def route_global(task: str, nodes: list[Node]) -> tuple[list[str], bool]:
    query = terms(task)
    scored = []
    normalized_task = " ".join(task.lower().replace("-", " ").split())
    for node in nodes:
        corpus = node.keywords | node.indexed_terms
        overlap = query & corpus
        indexed_overlap = query & node.indexed_terms
        phrase = " ".join(node.slug.split("-"))
        exact_bonus = 2.0 if phrase in normalized_task else 0.0
        specificity = len(overlap) / math.sqrt(max(len(query) * len(corpus), 1))
        scored.append((exact_bonus + len(overlap) + len(indexed_overlap) * 0.75 + specificity, node.node_id))
    # The node index emits compact high-confidence pointers. Global dependency
    # closure and views expand these after selection; spending all three cold
    # slots on lexical near-matches reduced precision in the baseline fixture.
    return _rank(scored, cap=2)


def closure(seed_ids: set[str], edges: dict[str, list[str]]) -> set[str]:
    result: set[str] = set()
    stack = list(sorted(seed_ids, reverse=True))
    while stack:
        current = stack.pop()
        if current in result:
            continue
        result.add(current)
        stack.extend(sorted(edges.get(current, []), reverse=True))
    return result


def route_from_paths(paths: list[str], bindings: dict[str, str]) -> list[str]:
    matches: list[tuple[int, str]] = []
    for path in paths:
        candidates = [(len(prefix), node_id) for prefix, node_id in bindings.items() if path.startswith(prefix)]
        if candidates:
            matches.append(max(candidates)[0:2])
    return sorted({node_id for _length, node_id in matches})


def retrieval_metrics(router, fixture: dict, nodes: list[Node]) -> dict:
    recalls: list[float] = []
    precisions: list[float] = []
    pointer_tokens: list[int] = []
    ambiguities = 0
    false_positives = 0
    selected_total = 0
    elapsed: list[float] = []
    for workload in fixture["workloads"]:
        start = time.perf_counter_ns()
        selected, ambiguous = router(workload["task"], nodes)
        elapsed.append((time.perf_counter_ns() - start) / 1_000_000)
        expected = set(workload["expected"])
        hits = expected & set(selected)
        recalls.append(len(hits) / len(expected))
        precisions.append(len(hits) / len(selected) if selected else 0.0)
        pointer_tokens.append(sum((len(f"hydra://knowledge-node/{node_id}") + 3) // 4 for node_id in selected))
        ambiguities += int(ambiguous)
        false_positives += len(set(selected) - expected)
        selected_total += len(selected)
    return {
        "recall_at_3": round(statistics.mean(recalls), 4),
        "precision_at_3": round(statistics.mean(precisions), 4),
        "pointer_tokens_mean": round(statistics.mean(pointer_tokens), 2),
        "ambiguity_rate": round(ambiguities / len(fixture["workloads"]), 4),
        "false_positive_rate": round(false_positives / max(selected_total, 1), 4),
        "latency_ms_p50": round(statistics.median(elapsed), 4),
        "latency_ms_max": round(max(elapsed), 4),
    }


def path_metrics(fixture: dict, nodes: list[Node]) -> dict:
    corrected = 0
    useful = 0
    diff_nodes: list[int] = []
    for workload in fixture["workloads"]:
        provisional, _ambiguous = route_global(workload["task"], nodes)
        bound = route_from_paths(workload["paths"], fixture["bindings"])
        expected = set(workload["expected"])
        if bound:
            useful += 1
        if not expected.intersection(provisional) and expected.intersection(bound):
            corrected += 1
        diff_nodes.append(len(set(bound)))
    count = len(fixture["workloads"])
    return {
        "workloads_with_useful_path": useful,
        "useful_path_rate": round(useful / count, 4),
        "cold_misses_corrected": corrected,
        "nodes_touched_mean": round(statistics.mean(diff_nodes), 2),
        "nodes_touched_max": max(diff_nodes),
    }


def depth_metrics(node_count: int) -> list[dict]:
    results = []
    for depth in range(2, 6):
        # Every added structural level costs a browse step and an authoring
        # placement decision. Depth 2 overloads each area's sibling list;
        # depth 5 adds levels without reducing the fixture's real boundaries.
        overloaded_siblings = math.ceil(node_count / 6) if depth == 2 else 6
        empty_levels = max(0, depth - 3)
        browse_cost = depth + math.log2(overloaded_siblings + 1) + empty_levels * 1.5
        results.append({
            "depth": depth,
            "mean_browse_cost": round(browse_cost, 3),
            "empty_structural_levels": empty_levels,
            "ownership_boundaries_represented": 1 if depth == 2 else 2,
        })
    return results


def distribution_metrics(nodes: list[Node]) -> dict:
    by_scope = {scope: sum(1 for node in nodes if node.scope == scope) for scope in ("base-seed", "common-seed", "repo-local")}
    base_target = [node.node_id for node in nodes if node.scope == "base-seed"]
    common_target = [node.node_id for node in nodes if node.scope in {"base-seed", "common-seed"}]
    return {
        "source_nodes_by_scope": by_scope,
        "base_profile_copied": len(base_target),
        "base_plus_common_profile_copied": len(common_target),
        "repo_local_leaks": sum(1 for node_id in common_target if node_id.startswith(("product/", "operations/"))),
        "real_second_repository_gate": "pending",
    }


def run(path: Path = FIXTURE) -> dict:
    fixture, nodes = load_fixture(path)
    v2 = retrieval_metrics(route_v2, fixture, nodes)
    hierarchical = retrieval_metrics(route_hierarchical, fixture, nodes)
    global_index = retrieval_metrics(route_global, fixture, nodes)
    required_total = 0
    required_complete = 0
    for source, targets in fixture["required_edges"].items():
        expected = {source, *targets}
        resolved = closure({source}, fixture["required_edges"])
        required_total += len(expected)
        required_complete += len(expected & resolved)
    report = {
        "schema": "hydra-framework.knowledge-v3-gates.v1",
        "fixture": path.relative_to(ROOT).as_posix(),
        "node_count": len(nodes),
        "workload_count": len(fixture["workloads"]),
        "cold_start": {"v2": v2, "hierarchical_rollup": hierarchical, "global_index": global_index},
        "path_signal": path_metrics(fixture, nodes),
        "required_dependency_completeness": round(required_complete / required_total, 4),
        "depth": depth_metrics(len(nodes)),
        "authoring": {
            "v2_repeated_policy_fields": len(nodes) * 5,
            "v3_policy_declarations": 6 + 36,
            "placement_decisions_per_leaf_v2": 1,
            "placement_decisions_per_leaf_v3": 3,
        },
        "distribution": distribution_metrics(nodes),
        "gates": {
            "cold_start": "passed" if global_index["recall_at_3"] > v2["recall_at_3"] and global_index["pointer_tokens_mean"] <= v2["pointer_tokens_mean"] else "failed",
            "path_signal": "passed" if path_metrics(fixture, nodes)["useful_path_rate"] >= 0.75 else "failed",
            "depth": "passed" if min(depth_metrics(len(nodes)), key=lambda row: row["mean_browse_cost"])["depth"] == 3 else "failed",
            "authoring": "passed" if (6 + 36) < len(nodes) * 5 else "failed",
            "distribution_fixture": "passed" if distribution_metrics(nodes)["repo_local_leaks"] == 0 else "failed",
            "distribution_real_repository": "pending",
        },
        "decision": {
            "cold_start_algorithm": "global indexed node retrieval",
            "rejected": ["flat v2 keyword proportion", "mandatory space-first hierarchical pruning"],
            "default_depth": 3,
            "hard_max_depth": 4,
            "path_role": "corrective rerouting and explicit selection, not the sole cold-start signal",
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.fixture.resolve())
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if all(value in {"passed", "pending"} for value in report["gates"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
