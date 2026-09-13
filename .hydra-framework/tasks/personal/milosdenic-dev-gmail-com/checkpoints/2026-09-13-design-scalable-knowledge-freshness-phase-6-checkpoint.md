# Checkpoint: design-scalable-knowledge-freshness

Task: .hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-12-design-scalable-knowledge-freshness.md
Created: 2026-09-13
Status: complete

## Goal

Implement the smallest correct knowledge-cache freshness mechanism. This
checkpoint records Phase 6: hooks. It is the sixth and final phase in
section 9 of the task record; with it done, the task's implementation
surface is complete.

## Confirmed Decisions

- The selected guarded Git-derived fingerprint design remains unchanged; do
  not reopen it without a reproduction that fails a named task fixture.
- Hooks stay a smaller, honest job that detects nothing: `post-commit`,
  `post-checkout`, `post-merge` and `post-rewrite` all trigger a reindex, and
  a quiescence lock brackets the one known multi-file governed write
  (`migration_v2.apply_reviewed_plan`, via `command_migrate_v2`). Nothing
  here is load-bearing for correctness; removing every hook only moves
  latency.
- The section 8 whole-operation benchmark matrix and Phase 4's component
  latency gate remain open, carried-forward, non-blocking follow-up. They
  are not part of Phase 6 and were not run or claimed as met in this pass.

## Approved Plan

Phase 6 was the only remaining phase per the prior checkpoint. It is now
complete on its own stated acceptance criterion. No further phases remain in
section 9; the two carried-forward benchmark/latency items are the only
open work, and they are explicitly separate from phase completion.

## Completed Work

- Added `.hydra-framework/hooks/post-commit` and
  `.hydra-framework/hooks/post-rewrite`, in the same style as the existing
  `post-checkout`/`post-merge` (best effort, `set -e` with `|| true` around
  each step): both call `hook-reindex-knowledge --if-exists` then
  `ref store rebuild --if-exists`. `post-rewrite` drains its stdin (the
  rewritten commit pairs Git supplies) since this hook does not need them.
  All four triggers now exist; `installation/git_hooks.py`'s
  `executable_hook_files` discovers whatever is in the hooks directory, so
  no installation-side change was needed.
- Changed `command_hook_reindex_knowledge` (`commands/knowledge.py`) to stop
  always doing a full `build_index` and instead delegate to a new
  `commands/knowledge_migration.py::refresh_knowledge_index`, which:
  - tries the quiescence lock non-blocking (`try_acquire(timeout=0.0)`) and
    quietly does nothing this run if it is held elsewhere;
  - does a first/bootstrap `build_index` when there is no published index
    yet (matching `build_index`'s own tolerance of a non-Git or
    guard-failed root -- there is no existing publication for a guard
    failure to protect there);
  - otherwise calls `search_index.search("", ...)` purely for its side
    effect, so the hook reuses exactly the same Stale/Absent/Fresh decision
    `search()` already makes (incremental update when merely stale, full
    rebuild only on a command-id or schema mismatch) rather than a second,
    parallel decision tree that could drift from it. This is warmed
    silently (returns `None`, nothing printed); only the first-build case
    still has a `(count, features)` to report.
- Identified the concrete multi-file governed write the design doc's
  "three new files and two old ones" describes:
  `migration_v2.apply_reviewed_plan`, called once, from
  `command_migrate_v2`. It writes an arbitrary number of governed files then
  deletes others across two unguarded loops, with no atomic worktree
  boundary between them -- exactly the case a content fingerprint alone
  cannot make atomic. Two smaller candidates were considered and rejected as
  not matching that pattern: `commands/capability.py`'s scaffolding (a
  bounded two-file write for one new skill/agent) and `commands/wiki.py`'s
  init (two files, but under `project-wiki/`, which is not a governed path
  at all).
- Implemented the quiescence bracket by reusing `ports/lock.py` exactly as
  instructed, with no new lock primitive: `command_migrate_v2` now holds
  `lock_port.acquire(ctx.root / KNOWLEDGE_WRITE_LOCK_REL)` for the whole
  `apply_reviewed_plan` call. This mirrors the existing
  `acquire_export_lock`-wraps-`apply_reconcile_plan` pattern already used in
  `commands/providers.py`, rather than reaching into `apply_reviewed_plan`
  itself -- `migration_v2.py` ends this phase completely untouched.
  `refresh_knowledge_index` tries the same lock non-blocking, so a
  hook-triggered reindex racing a live migration apply backs off instead of
  indexing a torn mid-write snapshot. Both ends share one constant,
  `commands/knowledge_migration.KNOWLEDGE_WRITE_LOCK_REL`.
- Architecture-cap note: an earlier version of this change put the new
  decision/lock logic directly in `search_index.py` (as a `refresh_index`
  function) and the lock directly in `migration_v2.py`. Both modules were
  already sitting exactly at the architecture invariants' caps with zero
  headroom (`search_index.py` and `migration_v2.py` both already at the
  400-line module-size cap; `commands/knowledge.py` already at the 8-module
  fan-out cap), confirmed with
  `hydra_engine.architecture.discover_modules`. Rather than trim or
  restructure any Phase 1-5 code to make room, the new code was relocated to
  `commands/knowledge_migration.py`, which `commands/knowledge.py` already
  imports and which had real headroom on both axes (fan-out 4 of 8 before
  this change, 5 after; far under its own line cap). `search_index.py` and
  `migration_v2.py` are unchanged by Phase 6.

## Current Stage

Phase 6's own stated acceptance is met and tested:
`test_correctness_holds_with_all_hooks_removed`
(`knowledge/test_search_index.py`) points `core.hooksPath` at a directory of
hooks that all `exit 1` for every trigger Phase 6 adds, performs a real `git
commit`, and confirms `search()` still detects and repairs the resulting
staleness (incremental reparse of exactly the changed document) entirely on
its own -- proving hooks are never load-bearing, only a latency
optimization.

With Phase 6 done, all six phases in section 9 of the task record are
implemented and their own stated acceptance criteria are met. This closes
out the task's implementation surface.

Explicitly NOT claimed by this checkpoint, carried forward unresolved from
Phase 4/5 and not part of any phase's stated acceptance:
- Phase 4's provisional 10k component latency gate (section 8) is still
  unmet, as measured and recorded in the task's Phase 4 benchmark entry.
- The section 8 whole-operation (`engine`/`end-to-end`) benchmark matrix has
  still not been run.
- No cache-vs-source speedup claim is made anywhere in this pass.

## Changed Files

- `.hydra-framework/hooks/post-commit` (new)
- `.hydra-framework/hooks/post-rewrite` (new)
- `.hydra-framework/engine/src/hydra_engine/commands/knowledge.py`
- `.hydra-framework/engine/src/hydra_engine/commands/knowledge_migration.py`
- `.hydra-framework/engine/tests/unit/commands/test_knowledge.py`
- `.hydra-framework/engine/tests/unit/commands/test_knowledge_migration.py`
- `.hydra-framework/engine/tests/unit/knowledge/test_search_index.py`
- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-12-design-scalable-knowledge-freshness.md`
- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/checkpoints/2026-09-13-design-scalable-knowledge-freshness-phase-6-checkpoint.md`

## Validation Performed

- `PYTHONPATH=.hydra-framework/engine/src:.hydra-framework/engine/tests/unit
  python3 -m unittest knowledge.test_search_index knowledge.test_migration_v2
  commands.test_knowledge commands.test_knowledge_migration
  installation.test_git_hooks commands.test_installation`: 73 passed.
- `PYTHONPATH=src python3 -m unittest tests.contract.goldens.test_installation`
  (run from `.hydra-framework/engine`): 9 passed, `install-hooks` goldens
  unaffected (their fixture uses a synthetic hooks directory, not this
  repository's real one).
- `python3 -m unittest discover -s .hydra-framework/engine/tests/unit -p
  "test_*.py"` (run from `.hydra-framework/engine`): full engine suite, 1445
  passed.
- `python3 .hydra-framework/scripts/hydra.py selftest`: 1603 passed.
- `git diff --check` and `python3 .hydra-framework/scripts/hydra.py
  validate`: both passed (provider and local-telemetry notices only).

## Remaining Work

None for this task's six-phase implementation surface. Separately, not part
of this task's phases: run the section 8 whole-operation benchmark matrix
and resolve Phase 4's component latency gap, if and when that work is
picked up.

## Blockers

None for Phase 6 or for the task's implementation surface as a whole.

Carried forward, still open, non-blocking: Phase 4's provisional 10k
component latency measurements still miss the section 8 thresholds, and the
section 8 whole-operation benchmark matrix has not been run.

## Useful References

- `AI_SYSTEM.md`
- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-12-design-scalable-knowledge-freshness.md`
  (section 4, hooks contract; section 9 Phase 6; section 10 Phase 6 test)
- `.hydra-framework/hooks/post-commit`, `post-checkout`, `post-merge`, `post-rewrite`
- `.hydra-framework/engine/src/hydra_engine/commands/knowledge_migration.py`
- `.hydra-framework/engine/src/hydra_engine/commands/knowledge.py`
- `.hydra-framework/engine/src/hydra_engine/ports/lock.py`

## Continuation Prompt

This task's six-phase implementation surface (section 9) is complete. If
resuming this task specifically, the only remaining work is the separate,
non-blocking section 8 whole-operation benchmark matrix and Phase 4's
component latency gap -- neither reopens the guarded Git-fingerprint design
or any phase's completed correctness work. The task record itself has not
been archived via `hydra.py task complete`; that removal step (which
requires committing the currently-untracked task/checkpoint files first and
choosing an `--outcome`) was deliberately left for the owner.
