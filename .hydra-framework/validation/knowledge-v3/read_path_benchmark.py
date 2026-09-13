"""P13/P15 clean-read benchmark: disposable Git fixtures, a correctness gate,
then the four section 8 clean-read latency gates (engine/CLI x 1k/10k) for
the FTS5-narrowed knowledge read path
(`hydra_engine.knowledge.search_index`/`lexical_index`/`index_cache`).

This is the harness `2026-09-13-bounded-knowledge-retrieval` Phase 4 requires.
Deliberately outside `.hydra-framework/engine/src` and `.../tests/unit`, so it
is not subject to that package's architecture caps -- the same convention
`benchmark.py` and `write_path_benchmark.py` in this directory already use.

Usage:
    python3 read_path_benchmark.py machine-info --out FILE
    python3 read_path_benchmark.py gate --size N --out FILE
    python3 read_path_benchmark.py bench --harness {engine,cli} --size N --out FILE
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ENGINE_SRC = REPO_ROOT / ".hydra-framework" / "engine" / "src"
ENGINE_TEST_UNIT = REPO_ROOT / ".hydra-framework" / "engine" / "tests" / "unit"
HYDRA_SHIM = REPO_ROOT / ".hydra-framework" / "scripts" / "hydra.py"
sys.path.insert(0, str(ENGINE_SRC))
sys.path.insert(0, str(ENGINE_TEST_UNIT))

from hydra_engine.knowledge import index_cache, search_index  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402
from v3_fixtures import write_node, write_unit  # noqa: E402

SPACE = "benchmark"
NODE = "benchmark/selected"
SELECTED_NAME = "unit-00000"
QUERY = "SEED00000AAAAA"
WARMUPS = 5
SAMPLES = 30
GATES_MS = {
    ("engine", 1000): {"p50": 50.0, "p95": 100.0},
    ("engine", 10000): {"p50": 50.0, "p95": 100.0},
    ("cli", 1000): {"p50": 300.0, "p95": 400.0},
    ("cli", 10000): {"p50": 300.0, "p95": 400.0},
}


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def git_commit_all(root: Path) -> None:
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "benchmark@example.invalid"],
        ["git", "config", "user.name", "Benchmark"],
        ["git", "add", "-A"],
        ["git", "commit", "-q", "-m", "fixture"],
    ):
        _run(command, root)


def build_fixture(root: Path, size: int) -> tuple[ContextCompilerPaths, ObjectLocations, Path]:
    """Build one disposable governed tree: the checkpointed engine source and
    shim, one `benchmark/selected` node, and `size` units, exactly one of
    which (`unit-00000`) carries the searched marker."""
    root.mkdir(parents=True, exist_ok=True)
    hydra = root / ".hydra-framework"
    shutil.copytree(ENGINE_SRC, hydra / "engine" / "src")
    (hydra / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(HYDRA_SHIM, hydra / "scripts" / "hydra.py")
    (root / "AI_SYSTEM.md").write_text("# Benchmark fixture\n", encoding="utf-8")

    paths = ContextCompilerPaths(root=root, hydra=hydra)
    write_node(paths, SPACE, keywords=())
    write_node(paths, NODE, keywords=("benchmark",))
    for index in range(size):
        write_unit(
            paths, NODE, f"unit-{index:05d}",
            body=f"Benchmark unit body. Marker: SEED{index:05d}AAAAA.\n",
        )
    git_commit_all(root)

    local = root / ".hydra-framework.local"
    resolver_paths = ObjectLocations(root, hydra, local, "tasks/personal", hydra / "cognition/graph/registry.yaml")
    return paths, resolver_paths, local


def _engine_search(paths, resolver_paths, local):
    return search_index.search(QUERY, paths=paths, resolver_paths=resolver_paths, local=local, limit=5)


def _assert_selected_engine(results) -> None:
    assert results, "engine search returned no results"
    assert any(SELECTED_NAME in result.document.path for result in results), \
        f"expected {SELECTED_NAME} among results, got {[r.document.path for r in results]}"


def _cli_search(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(root / ".hydra-framework/scripts/hydra.py"), "knowledge-search", QUERY],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    )


def _assert_selected_cli(completed: subprocess.CompletedProcess) -> None:
    stdout = completed.stdout.decode("utf-8", "replace")
    assert SELECTED_NAME in stdout, f"expected {SELECTED_NAME} in CLI output, got: {stdout[:2000]}"


# ---------------------------------------------------------------------------
# Correctness gate
# ---------------------------------------------------------------------------


def run_gate(size: int) -> dict:
    log: list[str] = []
    with tempfile.TemporaryDirectory(prefix=f"p13-read-gate-{size}-") as tmp:
        root = Path(tmp) / "repo"
        paths, resolver_paths, local = build_fixture(root, size)
        count, features = search_index.build_index(paths, resolver_paths, local, ())
        assert count >= size, f"expected at least {size} documents, got {count}"
        assert features.trigram, "benchmark host must support the trigram tokenizer to exercise the narrowed path"
        mode = search_index.lexical_mode(local)
        assert mode == "fts5-trigram", f"expected fts5-trigram mode after build, got {mode}"
        log.append(f"build: {count} documents, lexical mode={mode}")

        results, _features, source = _engine_search(paths, resolver_paths, local)
        assert source == "sqlite", f"engine gate: expected sqlite source, got {source}"
        _assert_selected_engine(results)
        log.append("engine gate: clean Fresh read answered from sqlite and found the selected unit")

        completed = _cli_search(root)
        _assert_selected_cli(completed)
        log.append("CLI gate: `knowledge-search` subprocess found the selected unit")
    return {"size": size, "passed": True, "log": log}


# ---------------------------------------------------------------------------
# Timed benchmark series
# ---------------------------------------------------------------------------


def summarize(samples_ms: list[float]) -> dict:
    ordered = sorted(samples_ms)
    n = len(ordered)
    assert n == SAMPLES, n
    p50 = (ordered[14] + ordered[15]) / 2
    p95 = ordered[28]
    return {"p50_ms": p50, "p95_ms": p95, "samples_ms": ordered}


def _load_checkpoint(out: Path, size: int, harness: str) -> dict:
    if out.exists():
        try:
            data = json.loads(out.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"warmups_done": False, "samples_ms": []}
        if data.get("size") == size and data.get("harness") == harness and not data.get("complete"):
            return {"warmups_done": bool(data.get("warmups_done")), "samples_ms": list(data.get("samples_ms", []))}
    return {"warmups_done": False, "samples_ms": []}


def _save_checkpoint(out: Path, size: int, harness: str, checkpoint: dict) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"size": size, "harness": harness, "complete": False, **checkpoint}, indent=2), encoding="utf-8")


def timed_engine_series(paths, resolver_paths, local, *, out: Path, size: int, checkpoint: dict) -> list[float]:
    samples: list[float] = list(checkpoint["samples_ms"])
    warmups_remaining = 0 if checkpoint["warmups_done"] else WARMUPS
    for _ in range(warmups_remaining):
        results, _features, source = _engine_search(paths, resolver_paths, local)
        assert source == "sqlite", f"engine warmup: expected sqlite source, got {source}"
        _assert_selected_engine(results)
    _save_checkpoint(out, size, "engine", {"warmups_done": True, "samples_ms": samples})
    while len(samples) < SAMPLES:
        start = time.perf_counter_ns()
        results, _features, source = _engine_search(paths, resolver_paths, local)
        elapsed_ms = (time.perf_counter_ns() - start) / 1e6
        assert source == "sqlite", f"engine sample {len(samples)}: expected sqlite source, got {source}"
        _assert_selected_engine(results)
        samples.append(elapsed_ms)
        _save_checkpoint(out, size, "engine", {"warmups_done": True, "samples_ms": samples})
    return samples


def timed_cli_series(root: Path, *, out: Path, size: int, checkpoint: dict) -> list[float]:
    samples: list[float] = list(checkpoint["samples_ms"])
    warmups_remaining = 0 if checkpoint["warmups_done"] else WARMUPS
    for _ in range(warmups_remaining):
        _assert_selected_cli(_cli_search(root))
    _save_checkpoint(out, size, "cli", {"warmups_done": True, "samples_ms": samples})
    while len(samples) < SAMPLES:
        start = time.perf_counter_ns()
        completed = _cli_search(root)
        elapsed_ms = (time.perf_counter_ns() - start) / 1e6
        _assert_selected_cli(completed)
        samples.append(elapsed_ms)
        _save_checkpoint(out, size, "cli", {"warmups_done": True, "samples_ms": samples})
    return samples


def run_bench(size: int, harness: str, out: Path) -> dict:
    checkpoint = _load_checkpoint(out, size, harness)
    with tempfile.TemporaryDirectory(prefix=f"p13-read-bench-{harness}-{size}-") as tmp:
        root = Path(tmp) / "repo"
        paths, resolver_paths, local = build_fixture(root, size)
        search_index.build_index(paths, resolver_paths, local, ())
        if harness == "engine":
            samples = timed_engine_series(paths, resolver_paths, local, out=out, size=size, checkpoint=checkpoint)
        elif harness == "cli":
            samples = timed_cli_series(root, out=out, size=size, checkpoint=checkpoint)
        else:
            raise ValueError(harness)
    summary = summarize(samples)
    gates = GATES_MS[(harness, size)]
    summary.update({
        "size": size, "harness": harness, "warmups": WARMUPS, "samples": SAMPLES,
        "gate_p50_ms": gates["p50"], "gate_p95_ms": gates["p95"],
        "verdict": "met" if summary["p50_ms"] <= gates["p50"] and summary["p95_ms"] <= gates["p95"] else "missed",
        "complete": True,
    })
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    gate_p = sub.add_parser("gate")
    gate_p.add_argument("--size", type=int, required=True)
    gate_p.add_argument("--out", type=Path, required=True)

    bench_p = sub.add_parser("bench")
    bench_p.add_argument("--size", type=int, required=True)
    bench_p.add_argument("--harness", choices=("engine", "cli"), required=True)
    bench_p.add_argument("--out", type=Path, required=True)

    args = parser.parse_args()
    try:
        if args.command == "gate":
            result = run_gate(args.size)
        elif args.command == "bench":
            result = run_bench(args.size, args.harness, args.out)
        else:
            raise ValueError(args.command)
    except Exception as error:  # noqa: BLE001 - report, do not silently exit
        if args.command != "bench":
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps({"passed": False, "error": str(error), "traceback": traceback.format_exc()}, indent=2), encoding="utf-8")
        print(f"FAILED: {error}", file=sys.stderr)
        traceback.print_exc()
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("log", "samples_ms")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
