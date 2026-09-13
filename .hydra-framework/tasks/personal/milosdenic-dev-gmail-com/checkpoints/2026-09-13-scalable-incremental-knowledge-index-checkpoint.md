# Checkpoint: scalable-incremental-knowledge-index

Task: .hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-13-scalable-incremental-knowledge-index.md
Created: 2026-09-13
Status: paused

## Goal

Implement P12 write-path caching Phases 2-5 without touching the sibling
`bounded-knowledge-retrieval` task.

## Confirmed Decisions

D1-D7, D7b, D12-D19 in the task record remain authoritative. In particular,
normal writes use only SQLite WAL plus `BEGIN IMMEDIATE`; the lock port is
recovery-only; phase 2 remains additive; and no document/locator columns
change.

## Approved Plan

Phase 2 adds persistent WAL primitives and transaction APIs; Phase 3 is the
single caller cutover/removal boundary; Phase 4 scopes local deltas through
`knowledge/index_collection.py`; Phase 5 is correctness-gated benchmarking.

## Completed Work

All five phases are complete and accepted:

- Phase 2: live `knowledge.db` WAL read/write primitives, generation-aware
  rebuild/delta transactions, callback rollback, fingerprint and generation
  checks, and corrupt-file recovery mutex.
- Phase 3: callers cut over to the persistent WAL APIs; legacy pointer/
  version APIs and their obsolete tests removed; cached snapshots close
  deterministically.
- Phase 4: collection moved to `knowledge/index_collection.py`; safe
  direct-path deltas use one node catalog pass and never walk the full
  corpus; structural/ambiguous changes rebuild; document/locator replacement
  is logical-differential; unused digest meta removed. Its previously-open
  completed-selftest requirement was satisfied 2026-09-13 from a runner
  without a 30-second command limit ("Ran 1599 tests in 50.328s" / "OK").
- Phase 5: disposable 1k/10k Git fixtures built from the checkpointed engine
  source (`.hydra-framework/validation/knowledge-v3/write_path_benchmark.py`,
  tracked and committed); correctness gates passed at both sizes; timed
  full-rebuild and single-document-incremental series recorded (5 warmups +
  30 samples each, `time.perf_counter_ns`).

## Current Stage

Task implementation is finished. Both Phase 5 verdicts at 10k:

- Full rebuild: p50 15616.39 ms / p95 15809.12 ms against a 5000 ms gate --
  **missed**, exactly as D7 predicted (full rebuild was never targeted by any
  phase here).
- Single-document incremental: p50 685.05 ms / p95 743.38 ms against a
  100 ms gate -- **missed**, but a 16.85x/16.20x (p50/p95) improvement over
  the pre-task baseline (11544.09/12042.02 ms). A diagnostic probe attributes
  the residual cost to `index_cache.fingerprint`'s repeated git-subprocess
  calls (6 per operation, ~157 ms of ~214 ms measured at 1k) rather than to
  canonical collection, which this record's Phase 4 already bounded to the
  changed unit.

No production code was changed in response to either result, per Phase 5's
explicit instruction. Final full unit discovery (1441 tests), `hydra.py
selftest` (1599 tests), `hydra.py validate`, and `git diff --check` all
pass. This task's own Phase 2-5 production/test/harness changes and its own
task record/checkpoint are committed; the registry, the neighboring
`problems.md` edits, and the sibling `bounded-knowledge-retrieval` record/
checkpoint remain uncommitted/untouched, as required.

## Changed Files

- `.hydra-framework/engine/src/hydra_engine/ports/sqlite_db.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/index_cache.py`
- `.hydra-framework/engine/tests/unit/ports/test_sqlite_db.py`
- `.hydra-framework/engine/tests/unit/knowledge/test_index_cache.py`
- `.hydra-framework/engine/tests/unit/knowledge/test_search_index.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/search_index.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/storage.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/snapshot.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/context_providers.py`
- `.hydra-framework/engine/src/hydra_engine/cli/route_prompt.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/index_collection.py`
- `.hydra-framework/engine/tests/unit/knowledge/test_index_collection.py`
- `.hydra-framework/validation/knowledge-v3/write_path_benchmark.py` (new,
  Phase 5 harness)
- this task record and checkpoint

All pre-existing sibling-task and registry changes remain preserved.

## Validation Performed

- Focused Phase 2 tests: 30 passed. Complete Phase 2 unit discovery: 1450
  passed. Complete Phase 3 unit discovery: 1438 passed.
- Phase 4 focused collector/cache/search/storage tests: 38 passed. Phase 4
  complete unit discovery: 1441 passed. Phase 4 `hydra.py selftest`:
  completed, 1599 tests, OK (50.328s).
- Phase 5 correctness gate: passed at 1k (27.8s) and 10k (2m50.2s), covering
  build validity, all six D16-eligible mutation kinds against independent
  incremental/full-rebuild clones (logical-row-identical per D18), a pinned
  WAL reader across two commits, a hard-killed incremental transaction
  (integrity_check=ok, prior generation/rows intact), and a structural
  fallback (apply_index_delta never called).
- Phase 5 timed series: see Current Stage above for the four p50/p95 numbers
  and two verdicts; full raw sample vectors are in the task record's
  Validation section and in the harness's `--out` JSON files (not retained
  as repository artifacts; the harness itself is retained and reproducible).
- Final: complete unit discovery (1441), `hydra.py selftest` (1599, OK),
  `hydra.py validate` (only pre-existing advisories, no stale registry
  digest), `git diff --check` (clean).

## Remaining Work

None in this record. A follow-up task to address the `fingerprint()`
git-subprocess cost (identified but not fixed, per Phase 5's instruction not
to change production code in response to results) is a decision for the task
requester.

## Blockers

None.

## Useful References

- Task record named above (authoritative execution detail).
- P12 in `repo/knowledge/spaces/hydra-framework/problems.md`.
- Phase 5 harness: `.hydra-framework/validation/knowledge-v3/write_path_benchmark.py`.

## Continuation Prompt

This record's implementation work is finished. If resumed: read the task
record's Phase 5 Validation entries for the full evidence, and consult the
task requester about whether to open a new task for the `fingerprint()`
git-subprocess cost before taking any further action here.
