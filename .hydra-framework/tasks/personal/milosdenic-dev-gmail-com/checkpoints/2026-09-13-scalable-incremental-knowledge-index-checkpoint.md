# Checkpoint: scalable-incremental-knowledge-index

Task: .hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-13-scalable-incremental-knowledge-index.md
Created: 2026-09-13
Status: paused

## Goal

Implement P12 write-path caching Phases 2-5 without touching the sibling
`bounded-knowledge-retrieval` task.

## Confirmed Decisions

D1-D7, D7b and D12-D19 in the task record remain authoritative. In
particular, normal writes use only SQLite WAL plus `BEGIN IMMEDIATE`; the lock
port is recovery-only; phase 2 remains additive; and no document/locator
columns change.

## Approved Plan

Phase 2 adds persistent WAL primitives and transaction APIs; Phase 3 is the
single caller cutover/removal boundary; Phase 4 scopes local deltas through
`knowledge/index_collection.py`; Phase 5 is correctness-gated benchmarking.

## Completed Work

Phase 2 complete: added live `knowledge.db` WAL read/write primitives,
generation-aware rebuild/delta transactions, callback rollback, fingerprint
and generation checks, and corrupt-file recovery mutex. Phase 3 complete and
accepted: callers use the persistent WAL APIs, legacy pointer/version APIs and
their obsolete tests are removed, and cached snapshots close deterministically.

## Current Stage

Phase 4 implementation is complete. Its hard validation boundary remains open
only because this terminal terminates `hydra.py selftest` at 30 seconds. Do not
begin Phase 5.

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
- this task record and checkpoint

All pre-existing sibling-task and registry changes remain preserved.

## Validation Performed

- Focused Phase 2 tests: 30 passed.
- Complete Phase 2 unit discovery: 1450 passed.
- Complete Phase 3 unit discovery: 1438 passed.
- `hydra.py validate`: passed, with only existing advisory notices.
- `git diff --check`: passed.
- Phase 3 selftest was not recorded as complete: direct, detached, and PTY
  attempts were terminated at the terminal's 30-second boundary. The requester
  accepted Phase 3 with this evidence gap; Phase 4 final validation must obtain
  a completed selftest result.
- Phase 4 focused collector/cache/search/storage tests: 38 passed.
- Phase 4 complete unit discovery: 1441 passed.
- Phase 4 `hydra.py validate`: passed, with only the existing advisory notices;
  no stale registry digest was reported, so `ref index` was not run.
- Phase 4 `git diff --check`: passed.
- Phase 4 selftest was invoked but did not complete: the terminal stopped it at
  30 seconds after partial progress. No passing result is claimed.

## Remaining Work

Obtain a completed Phase 4 selftest from a runner without the 30-second limit,
record its factual result, then stop. Do not begin Phase 5.

## Blockers

None.

## Useful References

- Task record named above (authoritative execution detail).
- P12 in `repo/knowledge/spaces/hydra-framework/problems.md`.

## Continuation Prompt

Start by reading `AI_SYSTEM.md`, this checkpoint, and the referenced task state. Continue from the current stage without relying on prior conversation history.

Run `python3 .hydra-framework/scripts/hydra.py selftest` to completion from a
suitable runner. Preserve all unrelated dirty changes and do not touch
`bounded-knowledge-retrieval`; do not begin Phase 5.
