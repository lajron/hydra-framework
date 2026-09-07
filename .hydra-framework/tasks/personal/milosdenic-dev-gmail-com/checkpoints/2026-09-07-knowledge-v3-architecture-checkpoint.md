# Checkpoint: knowledge-v3-architecture

Task: .hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-07-knowledge-v3-architecture.md
Created: 2026-09-07
Status: paused

## Goal

Migrate flat Knowledge v2 to Option D Knowledge v3 without a permanent dual
runtime, with deterministic review-gated migration and Git commits as rollback.

## Confirmed Decisions

- `knowledge migrate-v2` is the sole v2 reader; v3 is the only runtime/write model.
- Canonical routes use `hydra://knowledge-route/...`; `owner:name` is a bounded
  deprecated CLI compatibility form.
- Migration review binds approval to a recomputed payload digest and clean
  checkpoint commit. The migrator creates no backup tree.
- Rejected digest `sha256:a7efbdd3cbd4afa8275db1eb45b4cd56c80e9b249986f390df86e345e3ad29f2`
  must never be approved or applied.

## Approved Plan

Checkpoint the corrected migrator, regenerate a live dry-run, repeat an
independent isolated apply with `ref check`, `validate`, and `selftest`, then
approve/apply only the exact digest that passes those gates.

## Completed Work

- Baseline gates, 216-leaf enterprise fixture, frozen contract, v3 primitives,
  active recursive runtime integration, and first migrator are committed.
- Independent review simulated the first live plan: apply/ref check succeeded,
  but it found broken moved links, retained v2 root material, stale route and
  binding evidence, unsupported canonical route selectors, and a digest guard gap.
- Corrected all six findings and migrated real-repository context tests to v3.
- Added deterministic v3 authoring-template conversion and full legacy-root removal.

## Current Stage

Phase 4: corrected migration slice is ready for a Git checkpoint and replacement manifest.

## Changed Files

- `knowledge/migration_v2.py`, `migration_format.py`, and new `migration_templates.py`
- `knowledge/routing.py`, `context_providers.py`, and `checks.py`
- migration/template/routing unit tests and repository context-compiler tests
- primary task and this checkpoint

## Validation Performed

- Migration/template/route focused tests pass.
- Full unit discovery: 1,262 tests, zero failures/errors.
- `hydra.py validate` has no architecture/mirror/caller findings; only the
  expected pre-migration stale registry digests and missing `spaces.yaml` remain.
- `git diff --check` passed before the prior checkpoint; rerun before this commit.

## Remaining Work

Commit; generate replacement manifest; independently simulate apply and full
gates; approve/apply; verify idempotence; finish binding CLI, distribution and
terminology/template cleanup; run full validation, benchmarks, and final review.

## Blockers

- The first digest is blocked permanently. Replacement digest is not yet reviewed.
- Real second-repository distribution evidence remains pending; deterministic
  two-repository fixture evidence passed but does not satisfy that production gate.

## Useful References

- `AI_SYSTEM.md`
- `.hydra-framework/core/knowledge-architecture.md`
- Primary task record referenced above

## Continuation Prompt

Start by reading `AI_SYSTEM.md`, this checkpoint, and the task. Run
`PYTHONPATH=.hydra-framework/engine/src:.hydra-framework/engine/tests/unit python3 -m unittest discover -s .hydra-framework/engine/tests/unit -p 'test_*.py'`
and expect 1,262 passing. Confirm only this corrective slice is dirty, then
create the Git checkpoint and regenerate the live manifest. Do not apply until
the replacement digest passes independent isolated post-apply gates.
