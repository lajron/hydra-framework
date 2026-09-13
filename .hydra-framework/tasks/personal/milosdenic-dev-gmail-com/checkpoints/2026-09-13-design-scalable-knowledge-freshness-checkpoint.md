# Checkpoint: design-scalable-knowledge-freshness

Task: .hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-12-design-scalable-knowledge-freshness.md
Created: 2026-09-13
Status: paused

## Goal

Implement the smallest correct knowledge-cache freshness mechanism. This
checkpoint records Phase 3 only: indexed, connection-backed SQLite knowledge
queries with full-corpus parity.

## Confirmed Decisions

- The selected guarded Git-derived fingerprint design remains unchanged; do not
  reopen it without a reproduction that fails a named task fixture.
- `SqliteKnowledgeStore` is connection-backed. Read-path lookups use bounded
  indexed SQL and do not materialize the corpus through `iter_objects`.
- Phase 4 owns the fingerprint-driven incremental search-index update. The
  cached snapshot iteration concern remains Phase 5, which alone authorizes
  changes to `snapshot.py`, `context_providers.py`, and `route_prompt.py`.

## Approved Plan

Phase 3 is complete. Resume at Phase 4 only after reading its exact task
contract. Preserve search ranking and parity semantics; do not alter the Phase
2 publication boundary or Phase 5 files.

## Completed Work

- Replaced eager SQLite hydration with `SqliteKnowledgeStore`, implementing
  `by_id`, `by_uid`, `by_path`, `node_for_path`, `outgoing`, and `incoming` as
  connection-backed SQL lookups.
- Added the six required object and relation indexes in `write_sqlite_store`
  after inserts.
- Added full-corpus differential coverage against `InMemoryKnowledgeStore` and
  a cached-search regression that monkeypatches `iter_objects` to raise.

## Current Stage

Phase 3 acceptance is complete. Phase 4 has not started.

## Changed Files

- `.hydra-framework/engine/src/hydra_engine/knowledge/storage.py`
- `.hydra-framework/engine/tests/unit/knowledge/test_storage.py`
- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-12-design-scalable-knowledge-freshness.md`
- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/checkpoints/2026-09-13-design-scalable-knowledge-freshness-checkpoint.md`

## Validation Performed

- `PYTHONPATH=.hydra-framework/engine/src python3
  .hydra-framework/engine/tests/unit/knowledge/test_storage.py`: 5 passed.
- `PYTHONPATH='<engine src>:<engine tests/unit>' python3
  .hydra-framework/engine/tests/unit/knowledge/test_context_providers.py`: 13
  passed.
- `PYTHONPATH='<engine src>:<engine tests/unit>' python3
  .hydra-framework/engine/tests/unit/knowledge/test_search_index.py`: 15
  passed.
- `python3 .hydra-framework/scripts/hydra.py validate`: passed after task-state
  update (provider and local-telemetry notices only).

## Remaining Work

Phases 4 through 6 remain. Phase 4 changes `knowledge/search_index.py` to use
the guarded Git fingerprint, immutable publication pointer, and incremental
document/object projection update.

## Blockers

None.

## Useful References

- `AI_SYSTEM.md`
- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-12-design-scalable-knowledge-freshness.md`
- `.hydra-framework/engine/src/hydra_engine/knowledge/search_index.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/freshness.py`
- `.hydra-framework/engine/src/hydra_engine/ports/sqlite_db.py`

## Continuation Prompt

Start by reading `AI_SYSTEM.md`, the Phase 4 contract in the active task record,
this checkpoint, and the current `knowledge/search_index.py`. Implement Phase 4
only. Do not modify `snapshot.py`, `context_providers.py`, or `route_prompt.py`;
their cached snapshot iteration concern belongs to Phase 5. Preserve unrelated
edits to `problems.md` and `registry.yaml`, and do not reopen the guarded
Git-fingerprint design.
