# Checkpoint: knowledge-v3-architecture

Task: .hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-07-knowledge-v3-architecture.md
Created: 2026-09-07
Status: paused

## Goal

Complete Option D Knowledge v3 and migrate flat v2 without a permanent dual
runtime. Use reviewed Git commits as rollback boundaries.

## Confirmed Decisions

- `knowledge migrate-v2` is the sole v2 reader; runtime/write behavior is v3-only.
- Apply binds reviewer evidence to a recomputed exact manifest payload and a
  clean recorded commit.
- Canonical route IDs are executable; the legacy `owner:name` form is only a
  deprecated CLI alias.
- Template objects retain stable UIDs, move through sidecar rewrites, and use a
  non-discoverable `.template` filename until copied into an active space.

## Approved Plan

Checkpoint the second correction, generate a third live manifest, simulate it
in an independent clean clone, and apply only if its registry/index rebuild,
reference, validation, selftest, mode-preservation, and idempotence gates pass.

## Completed Work

- Baseline/enterprise gates, frozen contracts, v3 primitives and active runtime,
  and the review-gated migrator are committed.
- First digest `a7efbdd3...` was rejected for broken links, incomplete legacy
  cleanup, stale route/candidate behavior, consumer debt, and digest hardening.
- Second digest `da690c50...` was rejected because templates were discovered as
  live objects, sidecars remained v2, flat provenance became stale, and the
  executable check script lost its mode.
- Fixed sidecar identity/path/title rewrites, non-discoverable template naming,
  flat template-reference rewriting, and deterministic target mode preservation.

## Current Stage

Phase 4: second corrective implementation passes locally and needs checkpoint/review.

## Changed Files

- `knowledge/migration_v2.py`, `migration_templates.py`, `migration_format.py`
- migration, template, and command tests
- primary task and checkpoint

## Validation Performed

- Focused migration/template/format/command tests pass.
- Full unit discovery: 1,263 tests, zero failures/errors.
- `hydra.py validate` has only expected pre-migration registry-digest and
  missing-`spaces.yaml` findings; no module, mirror, caller, or reference debt.
- The two rejected digests were never applied to this checkout.

## Remaining Work

Commit; third dry-run; independent isolated apply review; approve/apply if green;
verify idempotence and live v3; finish binding CLI, distribution, terminology,
golden snapshots, enterprise reruns, and final independent review.

## Blockers

- Never approve/apply `a7efbdd3...` or `da690c50...`.
- A third digest is not yet generated or reviewed.
- Real second-repository distribution evidence remains pending.

## Useful References

- `AI_SYSTEM.md`
- `.hydra-framework/core/knowledge-architecture.md`
- Primary task record referenced above

## Continuation Prompt

Read `AI_SYSTEM.md`, this checkpoint, and the task. Run
`PYTHONPATH=.hydra-framework/engine/src:.hydra-framework/engine/tests/unit python3 -m unittest discover -s .hydra-framework/engine/tests/unit -p 'test_*.py'`
and expect 1,263 passing. Inspect `git status`, create the Git checkpoint, and
generate the third manifest. Do not apply until independent isolated gates pass.
