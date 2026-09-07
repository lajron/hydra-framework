"""Re-measure the enterprise decision gates against the shipped v3 runtime.

`benchmark.py` holds the original comparative evidence: it scores prototype
routers, including the flat v2 and hierarchical alternatives that the engine
never shipped, so it stays as the record of why Option D was chosen.

This harness answers the separate question of whether the engine that actually
shipped still clears those gates. It materialises the same checked-in fixture
as a real Knowledge v3 tree on disk and drives
`hydra_engine.knowledge.routing`, the node validator, and the binding resolver
over it, so a routing regression in the engine shows up here rather than only
in a prototype that no longer reflects the code.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / ".hydra-framework/engine/src"))

from hydra_engine.knowledge.bindings import (  # noqa: E402
    bound_nodes_for_paths, load_bindings, record_accepted_fingerprint, verify_binding,
)
from hydra_engine.knowledge.nodes import validate_knowledge_nodes  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402
from hydra_engine.knowledge.node_catalog import discover_knowledge_nodes  # noqa: E402
from hydra_engine.knowledge.routing import route_nodes  # noqa: E402

FIXTURE = Path(__file__).with_name("enterprise-fixture.json")


@dataclass(frozen=True)
class _Document:
    path: str


@dataclass(frozen=True)
class _SearchResult:
    """The one attribute `route_nodes` reads off a search result.

    Hints come from the fixture rather than the live SQLite index so the gate
    stays deterministic and machine-independent. The index's own ranking is
    covered by the engine's unit tests; what this measures is how the shipped
    router combines keyword score with index position.
    """

    document: _Document


def _uid(logical_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"hydra-enterprise-fixture:{logical_id}"))


def _node_document(
    logical_id: str, *, kind: str, scope: str, keywords: list[str],
    routable: bool = True, binding: str = "",
) -> str:
    owners = 'owners:\n  team: "fixture"\n' if kind == "knowledge-space" else ""
    lines = [
        'schema: "hydra-framework.knowledge-node.v1"',
        f'node: "{logical_id}"',
        f'hydra_id: "hydra://{kind}/{logical_id}"',
        f'uid: "{_uid(logical_id)}"',
        "schema_version: 3",
        f'kind: "{kind}"',
        f'title: "{logical_id.rsplit("/", 1)[-1].replace("-", " ").title()}"',
        'status: "active"',
        f'scope: "{scope}"',
    ]
    body = "\n".join(lines) + "\n" + owners + "relations: []\nprovenance:\n  sources: []\n"
    body += f"routable: {'true' if routable else 'false'}\n"
    body += 'state: "./state.md"\noverview: "./overview.md"\n'
    if binding:
        body += f'binding: "{binding}"\n'
    body += "keywords:\n" + "".join(f'  - "{word}"\n' for word in keywords)
    return body


def materialize(fixture: dict, root: Path) -> ContextCompilerPaths:
    """Write the fixture as a real v3 tree: space, area, and leaf nodes."""
    hydra = root / ".hydra-framework"
    knowledge = hydra / "repo/knowledge"
    spaces_dir = knowledge / "spaces"
    spaces_dir.mkdir(parents=True)
    hints = fixture.get("indexed_hints", {})
    binding_for_node = {
        node_id: f"@fixture/area-{index:03d}"
        for index, (_prefix, node_id) in enumerate(sorted(fixture["bindings"].items()))
    }

    def write(directory: Path, logical_id: str, filename: str, **kwargs) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / filename).write_text(_node_document(logical_id, **kwargs), encoding="utf-8")
        (directory / "state.md").write_text(f"# {logical_id} state\n", encoding="utf-8")
        (directory / "overview.md").write_text(f"# {logical_id} overview\n", encoding="utf-8")

    (knowledge / "spaces.yaml").write_text(
        'schema: "hydra-framework.knowledge-spaces.v1"\n'
        "default_depth: 3\nmax_depth: 4\nspaces:\n"
        + "".join(f'  - "{space}"\n' for space in fixture["spaces"]),
        encoding="utf-8",
    )
    for space, data in fixture["spaces"].items():
        scope = data["scope"]
        write(spaces_dir / space, space, "space.yaml", kind="knowledge-space", scope=scope, keywords=[space])
        for area, slugs in data["areas"].items():
            area_id = f"{space}/{area}"
            write(spaces_dir / space / area, area_id, "node.yaml", kind="knowledge-node", scope=scope, keywords=[area])
            for slug in slugs:
                leaf_id = f"{space}/{area}/{slug}"
                keywords = [*slug.split("-"), *hints.get(leaf_id, [])]
                write(
                    spaces_dir / space / area / slug, leaf_id, "node.yaml",
                    kind="knowledge-node", scope=scope, keywords=keywords,
                    binding=binding_for_node.get(leaf_id, ""),
                )

    bindings_dir = knowledge / "bindings"
    bindings_dir.mkdir(parents=True)
    bindings_dir.joinpath("manifest.yaml").write_text(
        'schema: "hydra-framework.bindings-manifest.v1"\nfragments:\n  - "fixture.yaml"\n', encoding="utf-8"
    )
    entries = []
    for index, (prefix, node_id) in enumerate(sorted(fixture["bindings"].items())):
        target = root / prefix
        target.mkdir(parents=True, exist_ok=True)
        (target / "OWNERS").write_text(f"{node_id}\n", encoding="utf-8")
        entries.append(
            f"  area-{index:03d}:\n"
            f'    target: "{prefix.rstrip("/")}"\n'
            '    kind: "directory"\n'
            "    assertions:\n      contains:\n        - \"OWNERS\"\n"
        )
    bindings_dir.joinpath("fixture.yaml").write_text(
        'schema: "hydra-framework.bindings.v1"\nnamespace: "fixture"\nbindings:\n' + "".join(entries),
        encoding="utf-8",
    )
    result = ContextCompilerPaths(root=root, hydra=hydra)
    # A binding only drives path routing once its assertion fingerprint has
    # been reviewed, so the fixture accepts them the way an operator would.
    for binding in load_bindings(result).values():
        record_accepted_fingerprint(binding, verify_binding(binding, result).fingerprint, result)
    return result


def _hint_results(task: str, fixture: dict, paths: ContextCompilerPaths) -> tuple:
    """Fixture hints, ranked the way a search index would return them."""
    task_words = set(task.lower().replace("-", " ").split())
    scored: list[tuple[int, str]] = []
    for node_id, hints in fixture.get("indexed_hints", {}).items():
        overlap = sum(1 for hint in hints if set(hint.lower().split()) & task_words)
        if overlap:
            scored.append((overlap, node_id))
    scored.sort(key=lambda item: (-item[0], item[1]))
    spaces = paths.hydra / "repo/knowledge/spaces"
    return tuple(
        _SearchResult(_Document(str(spaces / Path(node_id) / "overview.md")))
        for _score, node_id in scored
    )


def retrieval_gate(fixture: dict, paths: ContextCompilerPaths, *, hints: bool = True, timings: bool = False) -> dict:
    recalls: list[float] = []
    precisions: list[float] = []
    pointer_tokens: list[int] = []
    ambiguities = 0
    false_positives = 0
    selected_total = 0
    elapsed: list[float] = []
    for workload in fixture["workloads"]:
        results = _hint_results(workload["task"], fixture, paths) if hints else ()
        start = time.perf_counter_ns()
        selections, warnings = route_nodes(workload["task"], [], "", paths, search_results=results)
        elapsed.append((time.perf_counter_ns() - start) / 1_000_000)
        selected = [selection.node.logical_id for selection in selections]
        expected = set(workload["expected"])
        hits = expected & set(selected)
        recalls.append(len(hits) / len(expected))
        precisions.append(len(hits) / len(selected) if selected else 0.0)
        pointer_tokens.append(sum((len(f"hydra://knowledge-node/{node_id}") + 3) // 4 for node_id in selected))
        ambiguities += int(any("ambiguous" in warning.lower() or "low margin" in warning.lower() for warning in warnings))
        false_positives += len(set(selected) - expected)
        selected_total += len(selected)
    count = len(fixture["workloads"])
    report = {
        "recall_at_3": round(statistics.mean(recalls), 4),
        "precision_at_3": round(statistics.mean(precisions), 4),
        "pointer_tokens_mean": round(statistics.mean(pointer_tokens), 2),
        "ambiguity_rate": round(ambiguities / count, 4),
        "false_positive_rate": round(false_positives / max(selected_total, 1), 4),
    }
    # Latency varies by machine, so it stays out of the diffable report unless
    # asked for. Everything else above is deterministic for a given fixture.
    if timings:
        report["latency_ms_p50"] = round(statistics.median(elapsed), 4)
        report["latency_ms_max"] = round(max(elapsed), 4)
    return report


def path_gate(fixture: dict, paths: ContextCompilerPaths) -> dict:
    bindings = load_bindings(paths)
    nodes = discover_knowledge_nodes(paths)
    for binding in bindings.values():
        status = verify_binding(binding, paths)
        if status.state != "verified":
            raise SystemExit(f"fixture binding is not verified: {binding.logical_name}: {status.errors}")
    useful = 0
    corrected = 0
    touched: list[int] = []
    for workload in fixture["workloads"]:
        provisional = {
            selection.node.logical_id
            for selection in route_nodes(
                workload["task"], [], "", paths,
                search_results=_hint_results(workload["task"], fixture, paths),
            )[0]
        }
        bound = set(bound_nodes_for_paths(workload["paths"], nodes, bindings, paths).values())
        expected = set(workload["expected"])
        if bound:
            useful += 1
        if not expected & provisional and expected & bound:
            corrected += 1
        touched.append(len(bound))
    count = len(fixture["workloads"])
    return {
        "workloads_with_useful_path": useful,
        "useful_path_rate": round(useful / count, 4),
        "cold_misses_corrected": corrected,
        "nodes_touched_mean": round(statistics.mean(touched), 2),
        "nodes_touched_max": max(touched),
    }


def run(path: Path = FIXTURE, *, timings: bool = False) -> dict:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        paths = materialize(fixture, Path(tmp))
        findings = validate_knowledge_nodes(paths)
        if findings:
            raise SystemExit(
                "materialised fixture is not a valid v3 tree:\n"
                + "\n".join(f"- {finding}" for finding in findings[:20])
            )
        return {
            "schema": "hydra-framework.knowledge-v3-engine-gates.v1",
            "measured": "shipped hydra_engine.knowledge runtime",
            "fixture": path.name,
            "node_validation_findings": 0,
            "retrieval": retrieval_gate(fixture, paths, timings=timings),
            # The index contribution, not node keywords, is what carries v3's
            # retrieval gain, so the README's claim stays re-runnable here.
            "retrieval_without_index_hints": retrieval_gate(fixture, paths, hints=False),
            "path_rerouting": path_gate(fixture, paths),
            "real_second_repository_gate": "pending",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--timings", action="store_true",
        help="Include machine-dependent latency, which makes the report non-diffable",
    )
    args = parser.parse_args()
    report = run(args.fixture, timings=args.timings)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
