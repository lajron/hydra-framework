# Task: bounded-write-path-freshness-cost

Status: active
Owner: milosdenic-dev-gmail-com
Created: 2026-09-13
Updated: 2026-09-13

## Goal

Cut the per-operation `knowledge/freshness.py` Git fingerprint/guard cost on
the write (single-document incremental update) path. `2026-09-13-scalable-
incremental-knowledge-index`'s Phase 5 benchmark measured this task's real
target directly: a single-document incremental update at 10,000 governed
units costs p50 685.05 ms / p95 743.38 ms against that task's own 100 ms
section-8 gate -- missed, despite a 16.85x/16.20x improvement over the
pre-task baseline (11544.09/12042.02 ms), because Phase 4's delta-scoped
canonical collection fixed the dominant cost (whole-corpus file reads/
parses) but never touched the freshness/guard layer.

A targeted diagnostic (untimed, one-off, on a 1k fixture) instrumented
`index_cache.fingerprint` around one such operation: it is called 6 times
(twice inside `apply_index_delta`'s pre/post corpus-movement check, twice via
`_cache_state` before and after the update, twice via `capture_stamp`'s
opening pin and closing revalidation), each costing about 26 ms, for about
157 ms of a 214 ms total. Each call runs `git ls-files -s -z` plus
`git status --porcelain=v2 --untracked-files=all -z` as separate `git`
subprocesses over the *entire* tracked-file set (not just what changed) --
cost scales with total governed corpus size, not with the size of the edit.
This is a real, structural cost, not the sibling `bounded-knowledge-
retrieval` task's problem: that task's D8 optimization (sharing the
fingerprint between `cache_state` and the opening stamp) explicitly does
not apply once an update actually commits, and 2 of the 6 calls are inside
this task's own `apply_index_delta` transaction, which no other task
proposes to touch.

Fix the per-call cost (subprocess-spawn overhead, two separate `git`
invocations per fingerprint) and/or the call count (redundant re-asks of
"did anything change" within one operation), without weakening the
correctness guarantees that some of these checks exist to provide (in
particular, `apply_index_delta`'s pre/post check catches a real race: the
governed corpus moving *during* the transaction).

## Confirmed Decisions

- None yet. This record captures the measured problem and its evidence;
  no design session has happened.

## Approved Plan

- None yet.

## Current Stage

Not started. Opened directly from `2026-09-13-scalable-incremental-
knowledge-index`'s Phase 5 finding; that task is complete and its record
removed (`git log` on branch `knowledge-freshness-scalable-cache` is the
archive for its full Phase 1-5 history and the exact measurements this
record's Goal summarizes).

## Readiness

Status: not-checked

- Branch or workspace assumptions: no assumption yet; work has not started.
  Whichever branch is current when a design session begins should be
  recorded here then.
- Relevant canonical docs: `AI_SYSTEM.md`;
  `.hydra-framework/engine/src/hydra_engine/knowledge/freshness.py` (the
  fingerprint/guard/delta logic itself -- explicitly out of scope for
  correctness in the originating task, still in scope for its call cost
  here); `.hydra-framework/engine/src/hydra_engine/knowledge/index_cache.py`
  (`apply_index_delta`, `_write_generation`, `capture_stamp`, `cache_state`);
  `.hydra-framework/engine/src/hydra_engine/knowledge/search_index.py`
  (`_cache_state`, `_update_index`, `search`);
  `.hydra-framework/validation/knowledge-v3/write_path_benchmark.py` (the
  retained, reproducible harness that measured this problem -- reuse its
  `bench --size N --op incremental` path rather than rebuilding a fixture
  generator from scratch).
- Required dependencies, services, generated artifacts, or private local requirements: none beyond what the harness above already needs (Python
  3.12.3, Git 2.43.0, SQLite 3.45.1, disposable `mktemp -d` space).
- Blockers and assumptions: none blocking. Not dependent on
  `bounded-knowledge-retrieval`'s own Phase 2/3 landing -- that task's
  fingerprint sharing is scoped to the clean-read path and does not touch
  `apply_index_delta` or the write-path double `_cache_state` call this
  record is about, so the two do not conflict, but check that task's status
  before touching shared files (`index_cache.py`) to avoid a concurrent-edit
  collision.
- Expected validation command or evidence: re-run
  `.hydra-framework/validation/knowledge-v3/write_path_benchmark.py bench
  --size 10000 --op incremental` (and its `gate --size 10000` correctness
  check first) after any change; report a new p50/p95 against the same
  100 ms gate, plus full unit discovery, `hydra.py selftest`, `hydra.py
  validate`, and `git diff --check`, all passing. Do not claim the gate met
  without a fresh measurement against unchanged fixture methodology.

## Step State

- Active step: none
- Next step: a design session -- decide which of the 6 fingerprint calls can
  safely share one answer within a single operation (the two correctness-
  critical checks inside `apply_index_delta` most likely cannot), and
  whether to also cut per-call cost (avoid spawning a fresh `git` process
  twice per check).
- Completed steps: problem identified and measured (see Goal); no design or
  implementation yet.
- Superseded or skipped steps: none.

## Changed Files

- None yet.

## Validation

- Inherited measurement, 2026-09-13, from `2026-09-13-scalable-incremental-
  knowledge-index`'s Phase 5 (see that task's final commit,
  `8ce51bc`, on branch `knowledge-freshness-scalable-cache`, for the full
  benchmark record before that task record was removed on completion):
  10k single-document incremental p50 685.05 ms / p95 743.38 ms against a
  100 ms gate, missed; 1k p50 200.94 ms / p95 247.41 ms. Machine: Linux
  7.0.0-31-generic, AMD Ryzen 7 7730U, 16 logical CPUs, Python 3.12.3,
  Git 2.43.0, SQLite 3.45.1.
- Diagnostic probe, 2026-09-13 (untimed, one-off, not part of the tracked
  harness): instrumented `index_cache.fingerprint` around one single-unit
  incremental `run_context_providers` call on a freshly-built 1k fixture --
  6 calls, ~26 ms each, ~157 ms of a 214 ms total operation. Call sites:
  `search_index._cache_state` (called twice per operation: once inside
  `search()` before the update, once again after to reload `Fresh` state),
  `index_cache.apply_index_delta` (twice: pre-callback and post-callback
  corpus-movement check), `context_providers._capture_stamp` (twice: opening
  pin and closing revalidation).

## Blockers

- None.

Not blockers, recorded so they are not rediscovered:

- `bounded-knowledge-retrieval`'s D8 (sharing the fingerprint between
  `cache_state` and the opening stamp) is scoped to the clean-read path and,
  by its own stated ordering constraint, does not apply once an update
  actually commits. It will not reduce this record's 6-call count on its
  own; do not assume it does without re-measuring after that task lands.

## Continuation Notes

What another model or developer needs to continue safely.

- Running state: none. No background processes, no dev servers, no extra
  worktrees.
- Resume check: read this record's Validation section, then re-run
  `.hydra-framework/validation/knowledge-v3/write_path_benchmark.py bench
  --size 1000 --op incremental` to confirm the ~200 ms/6-call baseline still
  holds on current `main`/current branch before designing a fix; a changed
  number means re-diagnose rather than trusting this record's figures.
