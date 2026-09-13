"""P12 write-path benchmark: disposable Git fixtures, correctness gates, then
timed full-rebuild / single-document-incremental series for the persistent-WAL
knowledge index (`hydra_engine.knowledge.index_cache`/`search_index`).

This is the harness Phase 5 of
`.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-13-scalable-incremental-knowledge-index.md`
(see D19) requires be retained and reproducible. It is deliberately outside
`.hydra-framework/engine/src` and `.../tests/unit`, so it is not subject to
that package's architecture caps -- the same convention `benchmark.py` and
`engine_gates.py` in this directory already use.

Usage:
    python3 write_path_benchmark.py machine-info --out FILE
    python3 write_path_benchmark.py gate --size N --out FILE
    python3 write_path_benchmark.py bench --size N --op {rebuild,incremental} --out FILE

Every subcommand builds its own fresh disposable fixture under a `mktemp -d`
outside this checkout and removes it on exit.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
ENGINE_SRC = REPO_ROOT / ".hydra-framework" / "engine" / "src"
ENGINE_TEST_UNIT = REPO_ROOT / ".hydra-framework" / "engine" / "tests" / "unit"
HYDRA_SHIM = REPO_ROOT / ".hydra-framework" / "scripts" / "hydra.py"
sys.path.insert(0, str(ENGINE_SRC))
sys.path.insert(0, str(ENGINE_TEST_UNIT))

from hydra_engine.knowledge import context_providers, index_cache, search_index  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402
from hydra_engine.ports import sqlite_db  # noqa: E402
from v3_fixtures import write_node, write_unit  # noqa: E402

SPACE = "benchmark"
NODE = "benchmark/selected"
SELECTED_NAME = "unit-00000"
VICTIM_NAME = "unit-00001"
WARMUPS = 5
SAMPLES = 30
GATE_FULL_REBUILD_P95_MS = 5000.0
GATE_INCREMENTAL_P95_MS = 100.0
MUTATION_KINDS = (
    "unstaged_modify",
    "staged_modify",
    "add",
    "delete",
    "rename_stable_id",
    "rename_changed_id",
)


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


# ---------------------------------------------------------------------------
# Fixture construction
# ---------------------------------------------------------------------------


def build_fixture(root: Path, size: int) -> tuple[ContextCompilerPaths, ObjectLocations, Path, str]:
    """Build one disposable governed tree: the checkpointed engine source and
    shim, a minimal manifest, one `benchmark/selected` node, and `size` units.
    """
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
    selected_id = f"hydra://knowledge-unit/{NODE}/{SELECTED_NAME}"
    return paths, resolver_paths, local, selected_id


def unit_path(paths: ContextCompilerPaths, name: str) -> Path:
    return paths.hydra / "repo/knowledge/spaces" / NODE / "units" / f"{name}.md"


# ---------------------------------------------------------------------------
# Provider invocation
# ---------------------------------------------------------------------------


def provider_request(paths: ContextCompilerPaths, resolver_paths: ObjectLocations, selected_id: str) -> context_providers.ProviderRequest:
    return context_providers.ProviderRequest(
        task="", paths=paths, resolver_paths=resolver_paths,
        object_seed_ids=frozenset({selected_id}), chars_per_token=4,
        family_cap=context_providers.DEFAULT_FAMILY_CANDIDATE_CAP,
        node_values=(NODE,),
    )


def run_provider_and_capture_source(paths, resolver_paths, selected_id) -> tuple[context_providers.ProviderOutput, str]:
    from hydra_engine.knowledge import context_support
    sources: list[str] = []
    real_search = context_support.search
    real_search_for_context_provider = context_support.search_for_context_provider

    def _spy(*args, **kwargs):
        results, features, source = real_search(*args, **kwargs)
        sources.append(source)
        return results, features, source

    def _spy_for_context_provider(*args, **kwargs):
        results, features, source, stamp = real_search_for_context_provider(*args, **kwargs)
        sources.append(source)
        return results, features, source, stamp

    with (
        mock.patch("hydra_engine.knowledge.context_providers.context_support.search", side_effect=_spy),
        mock.patch(
            "hydra_engine.knowledge.context_providers.context_support.search_for_context_provider",
            side_effect=_spy_for_context_provider,
        ),
    ):
        output = context_providers.run_context_providers(
            provider_request(paths, resolver_paths, selected_id), include_families=("Knowledge",),
        )
    return output, (sources[-1] if sources else "unknown")


def assert_selected(output: context_providers.ProviderOutput, selected_id: str) -> None:
    assert output.nodes, "no node selected"
    assert output.nodes[0]["node"] == NODE, f"expected node {NODE}, got {output.nodes[0]}"
    unit_sources = {c["source"] for c in output.candidates if c["kind"] == "knowledge-unit"}
    assert selected_id in unit_sources, f"selected unit {selected_id} missing from {unit_sources}"


# ---------------------------------------------------------------------------
# Logical-row comparison (D18)
# ---------------------------------------------------------------------------


def read_logical_rows(db_path: Path) -> dict:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        documents = sorted(conn.execute("SELECT * FROM documents ORDER BY key").fetchall())
        objects = sorted(conn.execute("SELECT * FROM knowledge_objects ORDER BY hydra_id").fetchall())
        relations = sorted(conn.execute(
            "SELECT * FROM knowledge_relations ORDER BY source_id, relation_type, target_id"
        ).fetchall())
        meta = {k: v for k, v in conn.execute("SELECT key, value FROM meta") if k != "generation"}
        return {"documents": documents, "objects": objects, "relations": relations, "meta": meta}
    finally:
        conn.close()


def assert_logical_equal(a: dict, b: dict, *, context: str) -> None:
    for key in ("documents", "objects", "relations", "meta"):
        if a[key] != b[key]:
            raise AssertionError(f"{context}: logical `{key}` rows differ between incremental and rebuild")


def db_generation(db_path: Path) -> str | None:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT value FROM meta WHERE key='generation'").fetchone()
        return row[0] if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Correctness gate
# ---------------------------------------------------------------------------


def gate_1_build(paths, resolver_paths, local, selected_id, log: list[str]) -> None:
    count, features = search_index.build_index(paths, resolver_paths, local, ())
    db_path = index_cache.default_db_path(local)
    assert db_path is not None, "build_index did not produce a live database"
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"documents", "meta", "knowledge_objects", "knowledge_relations"} <= tables, tables
        indices = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        assert {"idx_objects_uid", "idx_objects_path", "idx_objects_node", "idx_objects_kind",
                "idx_relations_source", "idx_relations_target"} <= indices, indices
        generation = conn.execute("SELECT value FROM meta WHERE key='generation'").fetchone()
        assert generation and generation[0], "empty generation after build"
    finally:
        conn.close()
    index_dir = local / "index"
    names = {p.name for p in index_dir.iterdir()}
    assert names <= {"knowledge.db", "knowledge.db-wal", "knowledge.db-shm"}, names
    assert not any(n.startswith("knowledge-") and n != "knowledge.db" for n in names), names
    output, source = run_provider_and_capture_source(paths, resolver_paths, selected_id)
    assert source == "sqlite", f"gate 1: expected sqlite source, got {source}"
    assert_selected(output, selected_id)
    log.append(f"gate 1 (build): {count} documents, generation present, WAL, no pointer/versioned files, source=sqlite")


def _apply_mutation(paths: ContextCompilerPaths, kind: str) -> None:
    victim = unit_path(paths, VICTIM_NAME)
    if kind == "unstaged_modify":
        write_unit(paths, NODE, VICTIM_NAME, body="Benchmark unit body. Marker: MUTATEDXXXX.\n")
    elif kind == "staged_modify":
        write_unit(paths, NODE, VICTIM_NAME, body="Benchmark unit body. Marker: MUTATEDYYYY.\n")
        _run(["git", "add", str(victim.relative_to(paths.root))], paths.root)
    elif kind == "add":
        write_unit(paths, NODE, "unit-added", body="Benchmark unit body. Marker: ADDEDZZZZZ.\n")
    elif kind == "delete":
        victim.unlink()
    elif kind == "rename_stable_id":
        raw = victim.read_bytes()
        victim.with_name("unit-renamed-stable.md").write_bytes(raw)
        victim.unlink()
    elif kind == "rename_changed_id":
        write_unit(paths, NODE, "unit-renamed-changed", body="Benchmark unit body. Marker: RENAMEDID.\n")
        victim.unlink()
    else:
        raise ValueError(kind)


def gate_2_mutations(root: Path, size: int, selected_id: str, log: list[str]) -> None:
    for kind in MUTATION_KINDS:
        with tempfile.TemporaryDirectory(prefix=f"p12-gate2-{kind}-inc-") as inc_raw, \
             tempfile.TemporaryDirectory(prefix=f"p12-gate2-{kind}-full-") as full_raw:
            inc_dir, full_dir = Path(inc_raw) / "r", Path(full_raw) / "r"
            shutil.copytree(root, inc_dir)
            shutil.copytree(root, full_dir)

            inc_paths = ContextCompilerPaths(root=inc_dir, hydra=inc_dir / ".hydra-framework")
            full_paths = ContextCompilerPaths(root=full_dir, hydra=full_dir / ".hydra-framework")
            inc_local, full_local = inc_dir / ".hydra-framework.local", full_dir / ".hydra-framework.local"
            inc_resolver = ObjectLocations(inc_dir, inc_paths.hydra, inc_local, "tasks/personal", inc_paths.hydra / "cognition/graph/registry.yaml")
            full_resolver = ObjectLocations(full_dir, full_paths.hydra, full_local, "tasks/personal", full_paths.hydra / "cognition/graph/registry.yaml")

            generation_before = db_generation(index_cache.default_db_path(inc_local))
            _apply_mutation(inc_paths, kind)
            _apply_mutation(full_paths, kind)

            output, source = run_provider_and_capture_source(inc_paths, inc_resolver, selected_id)
            assert source == "sqlite", f"gate 2 [{kind}]: expected sqlite source, got {source}"
            assert_selected(output, selected_id)
            search_index.build_index(full_paths, full_resolver, full_local, ())

            inc_db = index_cache.default_db_path(inc_local)
            full_db = index_cache.default_db_path(full_local)
            assert_logical_equal(read_logical_rows(inc_db), read_logical_rows(full_db), context=f"gate 2 [{kind}] size={size}")
            generation_after = db_generation(inc_db)
            assert generation_after != generation_before, f"gate 2 [{kind}]: generation did not move"
        log.append(f"gate 2 [{kind}] size={size}: incremental matches rebuild, generation moved, selection intact")


def gate_3_concurrent_reader(local: Path, paths, resolver_paths, log: list[str]) -> None:
    db_path = index_cache.default_db_path(local)
    reader = sqlite_db.open_published(db_path)
    try:
        generation_a = index_cache.read_generation(reader)
        assert generation_a
        write_unit(paths, NODE, VICTIM_NAME, body="Benchmark unit body. Marker: GATE3MOVEA.\n")
        state = search_index._cache_state(paths, local)
        assert isinstance(state, index_cache.Stale)
        search_index._update_index(paths, resolver_paths, local, (), state)
        assert index_cache.read_generation(reader) == generation_a, "pinned reader observed a moved generation"
        search_index.build_index(paths, resolver_paths, local, ())
        assert index_cache.read_generation(reader) == generation_a, "pinned reader observed the rebuild's generation"
    finally:
        reader.close()
    fresh = sqlite_db.open_published(db_path)
    try:
        generation_c = index_cache.read_generation(fresh)
    finally:
        fresh.close()
    assert generation_c and generation_c != generation_a
    log.append("gate 3: a pinned WAL reader observed generation A across both an incremental and a full-rebuild commit; a new reader saw the rebuild's generation")


def gate_4_hard_interruption(local: Path, paths, resolver_paths, log: list[str]) -> None:
    db_path = index_cache.default_db_path(local)
    generation_before = db_generation(db_path)
    rows_before = read_logical_rows(db_path)
    script = f"""
import os, sys
sys.path.insert(0, {str(ENGINE_SRC)!r})
from hydra_engine.knowledge import index_cache, index_collection
from hydra_engine.knowledge.packages import ContextCompilerPaths
from pathlib import Path
paths = ContextCompilerPaths(root=Path({str(paths.root)!r}), hydra=Path({str(paths.hydra)!r}))
local = Path({str(local)!r})
state_fingerprint = index_cache.fingerprint(paths.root)
def apply_update(conn, current):
    conn.execute("DELETE FROM documents WHERE key = ?", ({SELECTED_NAME!r},))
    os._exit(17)
index_cache.apply_index_delta(
    paths, local, expected_generation={generation_before!r}, expected_fingerprint=state_fingerprint,
    apply_update=apply_update,
)
"""
    completed = subprocess.run([sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert completed.returncode == 17, f"gate 4: subprocess did not hit the interruption point ({completed.returncode}): {completed.stderr.decode()}"
    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        conn.close()
    assert db_generation(db_path) == generation_before, "generation moved despite the interrupted transaction"
    assert read_logical_rows(db_path) == rows_before, "rows moved despite the interrupted transaction"
    log.append("gate 4: a subprocess killed mid-transaction (os._exit before commit) left the prior generation/rows intact and integrity_check=ok")


def gate_5_structural_fallback(paths, resolver_paths, local, selected_id, log: list[str]) -> None:
    node_yaml = paths.hydra / "repo/knowledge/spaces" / NODE / "node.yaml"
    text = node_yaml.read_text(encoding="utf-8")
    node_yaml.write_text(text.replace("routable: true", "routable: false"), encoding="utf-8")
    state = search_index._cache_state(paths, local)
    assert isinstance(state, index_cache.Stale), state
    from hydra_engine.knowledge import index_collection
    assert index_collection.delta_is_local(paths, resolver_paths, state.delta) is False, "structural node.yaml change was classified local"
    generation_before = state.generation
    with mock.patch("hydra_engine.knowledge.index_cache.apply_index_delta", side_effect=AssertionError("must not apply a delta for a structural change")):
        output, source = run_provider_and_capture_source(paths, resolver_paths, selected_id)
    assert source == "sqlite"
    generation_after = db_generation(index_cache.default_db_path(local))
    assert generation_after != generation_before, "structural change did not trigger a rebuild"
    node_yaml.write_text(text, encoding="utf-8")
    log.append("gate 5: a structural node.yaml change took the full-rebuild branch (apply_index_delta was never called)")


def run_gate(size: int) -> dict:
    log: list[str] = []
    with tempfile.TemporaryDirectory(prefix=f"p12-gate-{size}-") as tmp:
        root = Path(tmp) / "repo"
        paths, resolver_paths, local, selected_id = build_fixture(root, size)
        gate_1_build(paths, resolver_paths, local, selected_id, log)
        gate_2_mutations(root, size, selected_id, log)
        gate_3_concurrent_reader(local, paths, resolver_paths, log)
        gate_4_hard_interruption(local, paths, resolver_paths, log)
        gate_5_structural_fallback(paths, resolver_paths, local, selected_id, log)
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


def _load_checkpoint(out: Path, size: int, op: str) -> dict:
    if out.exists():
        try:
            data = json.loads(out.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"warmups_done": False, "samples_ms": []}
        if data.get("size") == size and data.get("op") == op and not data.get("complete"):
            return {"warmups_done": bool(data.get("warmups_done")), "samples_ms": list(data.get("samples_ms", []))}
    return {"warmups_done": False, "samples_ms": []}


def _save_checkpoint(out: Path, size: int, op: str, checkpoint: dict) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"size": size, "op": op, "complete": False, **checkpoint}, indent=2), encoding="utf-8")


def timed_full_rebuild_series(paths, resolver_paths, local, selected_id, *, out: Path, size: int, checkpoint: dict) -> list[float]:
    db_path = local / "index" / "knowledge.db"
    samples: list[float] = list(checkpoint["samples_ms"])
    warmups_remaining = 0 if checkpoint["warmups_done"] else WARMUPS
    for _ in range(warmups_remaining):
        for suffix in ("", "-wal", "-shm"):
            Path(f"{db_path}{suffix}").unlink(missing_ok=True)
        output, source = run_provider_and_capture_source(paths, resolver_paths, selected_id)
        assert source == "sqlite", f"full-rebuild warmup: expected sqlite source, got {source}"
        assert_selected(output, selected_id)
    _save_checkpoint(out, size, "rebuild", {"warmups_done": True, "samples_ms": samples})
    while len(samples) < SAMPLES:
        for suffix in ("", "-wal", "-shm"):
            Path(f"{db_path}{suffix}").unlink(missing_ok=True)
        start = time.perf_counter_ns()
        output, source = run_provider_and_capture_source(paths, resolver_paths, selected_id)
        elapsed_ms = (time.perf_counter_ns() - start) / 1e6
        assert source == "sqlite", f"full-rebuild sample {len(samples)}: expected sqlite source, got {source}"
        assert_selected(output, selected_id)
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            generation = conn.execute("SELECT value FROM meta WHERE key='generation'").fetchone()
        finally:
            conn.close()
        assert doc_count > 0 and generation and generation[0]
        samples.append(elapsed_ms)
        _save_checkpoint(out, size, "rebuild", {"warmups_done": True, "samples_ms": samples})
    return samples


def timed_incremental_series(paths, resolver_paths, local, selected_id, *, out: Path, size: int, checkpoint: dict) -> list[float]:
    victim = unit_path(paths, VICTIM_NAME)
    body_a = "Benchmark unit body. Marker: INCREMENTALA.\n"
    body_b = "Benchmark unit body. Marker: INCREMENTALB.\n"
    assert len(body_a) == len(body_b)
    samples: list[float] = list(checkpoint["samples_ms"])
    total_done = (WARMUPS if checkpoint["warmups_done"] else 0) + len(samples)

    def _one(i: int, *, timed: bool) -> float | None:
        search_index.build_index(paths, resolver_paths, local, ())
        generation_before = db_generation(index_cache.default_db_path(local))
        body = body_a if i % 2 == 0 else body_b
        write_unit(paths, NODE, VICTIM_NAME, body=body)
        state = search_index._cache_state(paths, local)
        assert isinstance(state, index_cache.Stale), f"incremental sample {i}: expected a stale delta, got {state}"

        start = time.perf_counter_ns()
        output, source = run_provider_and_capture_source(paths, resolver_paths, selected_id)
        elapsed_ms = (time.perf_counter_ns() - start) / 1e6

        assert source == "sqlite", f"incremental sample {i}: expected sqlite source, got {source}"
        db_path = index_cache.default_db_path(local)
        generation_after = db_generation(db_path)
        assert generation_after and generation_after != generation_before, f"incremental sample {i}: generation did not move once"
        assert_selected(output, selected_id)
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            row = conn.execute("SELECT body FROM documents WHERE key = ?", (victim.relative_to(paths.root).as_posix(),)).fetchone()
        finally:
            conn.close()
        assert row is not None and body.strip() in row[0], "incremental update did not persist the new body"
        return elapsed_ms if timed else None

    for i in range(total_done, WARMUPS):
        _one(i, timed=False)
    _save_checkpoint(out, size, "incremental", {"warmups_done": True, "samples_ms": samples})
    for i in range(max(total_done, WARMUPS), WARMUPS + SAMPLES):
        elapsed_ms = _one(i, timed=True)
        samples.append(elapsed_ms)
        _save_checkpoint(out, size, "incremental", {"warmups_done": True, "samples_ms": samples})
    return samples


def run_bench(size: int, op: str, out: Path) -> dict:
    checkpoint = _load_checkpoint(out, size, op)
    with tempfile.TemporaryDirectory(prefix=f"p12-bench-{op}-{size}-") as tmp:
        root = Path(tmp) / "repo"
        paths, resolver_paths, local, selected_id = build_fixture(root, size)
        search_index.build_index(paths, resolver_paths, local, ())
        if op == "rebuild":
            samples = timed_full_rebuild_series(paths, resolver_paths, local, selected_id, out=out, size=size, checkpoint=checkpoint)
        elif op == "incremental":
            samples = timed_incremental_series(paths, resolver_paths, local, selected_id, out=out, size=size, checkpoint=checkpoint)
        else:
            raise ValueError(op)
    summary = summarize(samples)
    gate_ms = GATE_FULL_REBUILD_P95_MS if op == "rebuild" else GATE_INCREMENTAL_P95_MS
    summary.update({"size": size, "op": op, "warmups": WARMUPS, "samples": SAMPLES, "gate_p95_ms": gate_ms, "verdict": "met" if summary["p95_ms"] <= gate_ms else "missed", "complete": True})
    return summary


# ---------------------------------------------------------------------------
# Machine info
# ---------------------------------------------------------------------------


def machine_info() -> dict:
    def _sh(args: list[str]) -> str:
        try:
            return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout.decode().strip()
        except (OSError, subprocess.CalledProcessError):
            return ""

    cpu_model = ""
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("model name"):
                cpu_model = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    fstype = _sh(["findmnt", "-no", "FSTYPE", "--target", str(REPO_ROOT)])
    free_bytes = shutil.disk_usage(REPO_ROOT).free
    tmp_fstype = _sh(["findmnt", "-no", "FSTYPE", "--target", tempfile.gettempdir()])
    tmp_free_bytes = shutil.disk_usage(tempfile.gettempdir()).free
    prod_paths = [
        str(REPO_ROOT / ".hydra-framework/engine/src"),
        str(REPO_ROOT / ".hydra-framework/engine/tests/unit"),
    ]
    dirty_production = _sh(["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--", *prod_paths])
    return {
        "kernel": platform.uname().release,
        "platform": platform.platform(),
        "cpu_model": cpu_model,
        "logical_cpus": os.cpu_count(),
        "python_version": platform.python_version(),
        "git_version": _sh(["git", "--version"]),
        "sqlite_version": sqlite3.sqlite_version,
        "repo_fstype": fstype,
        "repo_free_bytes": free_bytes,
        "tmp_fstype": tmp_fstype,
        "tmp_free_bytes": tmp_free_bytes,
        "commit": _sh(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"]),
        "production_dirty": dirty_production,
        "production_matches_checkpoint": dirty_production == "",
        "load_average": os.getloadavg(),
    }


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
    bench_p.add_argument("--op", choices=("rebuild", "incremental"), required=True)
    bench_p.add_argument("--out", type=Path, required=True)

    info_p = sub.add_parser("machine-info")
    info_p.add_argument("--out", type=Path, required=True)

    args = parser.parse_args()
    try:
        if args.command == "machine-info":
            result = machine_info()
        elif args.command == "gate":
            result = run_gate(args.size)
        elif args.command == "bench":
            result = run_bench(args.size, args.op, args.out)
        else:
            raise ValueError(args.command)
    except Exception as error:  # noqa: BLE001 - report, do not silently exit
        if args.command != "bench":
            # A `bench` checkpoint at `--out` may hold real in-progress samples;
            # never clobber it with a bare error object. Re-running the same
            # command resumes from that checkpoint instead.
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps({"passed": False, "error": str(error), "traceback": traceback.format_exc()}, indent=2), encoding="utf-8")
        print(f"FAILED: {error}", file=sys.stderr)
        traceback.print_exc()
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "log" and k != "samples_ms"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
