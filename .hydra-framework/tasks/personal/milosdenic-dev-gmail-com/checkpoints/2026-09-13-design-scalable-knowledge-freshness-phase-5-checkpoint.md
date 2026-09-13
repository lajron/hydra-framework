# Checkpoint: design-scalable-knowledge-freshness

Task: .hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-12-design-scalable-knowledge-freshness.md
Created: 2026-09-13
Status: paused

## Goal

Implement the smallest correct knowledge-cache freshness mechanism. This
checkpoint records Phase 5 only: operation-scoped read-stamp propagation and
final revalidation. A same-date checkpoint for Phase 3 already exists
(`2026-09-13-design-scalable-knowledge-freshness-checkpoint.md`); the task's
own checkpoint tooling (`command_task_checkpoint` in
`hydra_engine/commands/work.py`) has no multi-per-day disambiguation and
simply refuses to overwrite an existing same-day file, so this checkpoint is
named with an explicit phase suffix rather than colliding with or overwriting
that file.

## Confirmed Decisions

- The selected guarded Git-derived fingerprint design remains unchanged; do not
  reopen it without a reproduction that fails a named task fixture.
- Phase 5 alone authorized changes to `snapshot.py`, `context_providers.py`,
  and `route_prompt.py`; that authorization is now exhausted for this phase.
- Phase 6 (hooks) is the only remaining phase. Nothing in Phase 6 is
  load-bearing for correctness; only latency moves.

## Approved Plan

Phase 5 is complete on its own stated acceptance criterion. Resume at Phase 6
only after reading its exact task contract in section 9 of the task record.
Two carried-forward items are explicitly NOT resolved by Phase 5 and are not
Phase 6's job either: Phase 4's provisional 10k component latency gate is
still unmet, and the section 8 whole-operation (`engine`/`end-to-end`)
benchmark matrix has not yet been run.

## Completed Work

- Added `index_cache.OperationStamp` / `capture_stamp`: a guarded
  governed-corpus fingerprint plus the currently published index identity,
  captured once per operation.
- `knowledge/snapshot.py`'s `KnowledgeSnapshot` now carries the stamp it was
  opened against.
- `context_providers.py` captures the stamp once its shared search settles
  and opens the snapshot against that same pinned publication, instead of
  re-resolving the published index a second time.
- `cli/route_prompt.py` mirrors the same pin/revalidate shape via a
  `_route_once` helper.
- Both `run_context_providers` and `command_route_prompt` revalidate the
  stamp once at the end of the observable operation and, on a mismatch,
  discard every candidate/node gathered and rerun the whole operation with
  `force_source=True`, reusing the existing `HydrationMismatch`
  canonical-rerun recovery path rather than a new mechanism.
- `search()`'s signature, return shape, and Phase 4's whole-document /
  copy-on-write internals are unchanged. Phase 6 hooks were not touched.

## Current Stage

Phase 5's own correctness acceptance is met and claimed: a test publishing a
new version mid-operation observes a full rerun, not a mixed result. This is
the literal Phase 5 acceptance criterion from the design doc (section 9).

Explicitly NOT claimed by this checkpoint:
- Phase 4's own component latency gate (section 8 provisional 10k thresholds)
  remains unmet, as measured and recorded in the task's Phase 4 benchmark
  entry.
- The section 8 whole-operation (`engine`/`end-to-end`) benchmark matrix has
  not been run at all yet, for either phase.
- No cache-vs-source speedup claim is made anywhere in this pass. The
  `capture_stamp` cost (~16 ms p50/p95 on this repo's 320-doc corpus, paid
  twice per stamped operation beyond what `search()` already spends) is
  recorded as an added, unoptimized cost, not an improvement.

## Changed Files

- `.hydra-framework/engine/src/hydra_engine/knowledge/index_cache.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/snapshot.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/context_providers.py`
- `.hydra-framework/engine/src/hydra_engine/cli/route_prompt.py`
- `.hydra-framework/engine/tests/unit/knowledge/test_index_cache.py`
- `.hydra-framework/engine/tests/unit/knowledge/test_context_providers.py`
- `.hydra-framework/engine/tests/unit/cli/test_route_prompt.py`
- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-12-design-scalable-knowledge-freshness.md`
- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/checkpoints/2026-09-13-design-scalable-knowledge-freshness-phase-5-checkpoint.md`

## Validation Performed

- `PYTHONPATH=.hydra-framework/engine/src:.hydra-framework/engine/tests/unit
  python3 -m unittest knowledge.test_freshness knowledge.test_search_index
  knowledge.test_index_cache knowledge.test_storage
  knowledge.test_context_providers commands.test_knowledge
  cli.test_route_prompt ports.test_sqlite_db ports.test_lock`: 115 tests
  passed, including the three new stamp-revalidation tests
  (`test_publication_change_midoperation_reruns` x2 and
  `test_no_mixed_cache_and_source_graph`) and every prior Phase 1-4 regression
  test, unchanged.
- `python3 -m unittest discover -s .hydra-framework/engine/tests/unit -p
  "test_*.py"` (run from `.hydra-framework/engine`): full engine suite, 1438
  passed.
- `python3 .hydra-framework/scripts/hydra.py selftest`: 1596 passed.
- `git diff --check` and `python3 .hydra-framework/scripts/hydra.py validate`:
  both clean (provider and local-telemetry notices only).

## Remaining Work

Phase 6 only: hooks. `post-commit`, `post-checkout`, `post-merge` and
`post-rewrite` call the incremental update so the next read finds the
database current, plus the quiescence bracket around known multi-file Hydra
writes. Phase 6 acceptance: removing every hook leaves all correctness tests
green. Separately (not a Phase 6 task, but still open): resolve Phase 4's
component latency gap and run the section 8 whole-operation benchmark matrix.

## Blockers

None operational for Phase 5 itself; its stated correctness acceptance is met
and tested.

Carried forward, not resolved by Phase 5: Phase 4's provisional 10k component
measurements still miss the latency thresholds, and the section 8
whole-operation (`engine`/`end-to-end`) acceptance benchmark has not been run.
Do not claim the Phase 4 engine gate or a cache-vs-source speedup from
anything recorded here.

## Useful References

- `AI_SYSTEM.md`
- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-12-design-scalable-knowledge-freshness.md`
  (section 9, Phase 6 contract; section 8, benchmark/acceptance contract)
- `.hydra-framework/engine/src/hydra_engine/knowledge/index_cache.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/snapshot.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/context_providers.py`
- `.hydra-framework/engine/src/hydra_engine/cli/route_prompt.py`

## Continuation Prompt

Start by reading `AI_SYSTEM.md`, the Phase 6 contract in the active task
record (section 9), this checkpoint, and the current hook-related code paths.
Implement Phase 6 only: eager rebuild hooks and the quiescence bracket.
Nothing in Phase 6 is load-bearing for correctness; do not reintroduce hook
presence as evidence of freshness. Do not reopen the guarded Git-fingerprint
design, and do not claim Phase 4's component latency gate or the section 8
whole-operation benchmark as met unless they are actually run and pass.
