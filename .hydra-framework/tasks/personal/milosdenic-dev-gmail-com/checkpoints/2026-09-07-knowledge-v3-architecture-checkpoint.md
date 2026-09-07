# Checkpoint: knowledge-v3-architecture

Task: .hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-07-knowledge-v3-architecture.md
Created: 2026-09-07
Status: active

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
- Migration reference rewriting never touches engine sources, contract goldens,
  the derived registry, or the private local tier. Engine code is the v2 reader
  and the goldens encode v2 behavior, so rewriting them always corrupts them.
- The plan digest is the review contract, so it must be reproducible from
  content alone. Only the tracked executable bit is recorded, and a mode is
  applied only to files the migration creates.
- Identity, sidecar-key, and template-title rewriting is confined to
  `repo/object-sidecars.yaml`, the only place outside the engine where that
  vocabulary lives. Prose terminology is authored, never blanket-substituted.

## Approved Plan

Confirm with the owner, then complete the task. Nothing is in flight.

## Completed Work

- Baseline/enterprise gates, frozen contracts, v3 primitives and active runtime,
  and the review-gated migrator are committed.
- First digest `a7efbdd3...` rejected: broken links, incomplete legacy cleanup,
  stale route/candidate behavior, consumer debt, digest hardening.
- Second digest `da690c50...` rejected: templates discovered as live objects,
  sidecars left on v2 paths, stale flat provenance, lost executable mode.
- Third digest `db1a5b58...` rejected: blanket reference rewriting corrupted
  engine sources, the migrator's own tests, and contract goldens, adding seven
  test failures after an apply whose `ref check` and `validate` both passed;
  the digest was also irreproducible across checkouts because it embedded raw
  `st_mode`; the unanchored `/routing.yaml` rule corrupted the real space's
  registry path and produced a duplicate registry key.
- Fourth digest `17389e51...` cleared every isolated gate: reproduced byte-identically in a clean clone, `ref check` ok,
  `validate` ok, 1,270 unit tests green, zero new `selftest` failures with four
  pre-existing ones cleared, modes correct, legacy tree gone, dry-run and a
  second apply both no-ops, and live v3 routing, context compilation, search,
  and path explanation verified.
- The migration is applied to this repository as commit `bc257e4` from digest
  `19e4e37f...` at rollback boundary `793c435`, with reference, validation,
  unit, mode, legacy-removal, and live-runtime gates all confirmed here.

## Current Stage

Phase 5: migration applied, polish tail closed, independent review resolved.

## Changed Files

- `knowledge/migration_v2.py`, `migration_templates.py`, `migration_format.py`
- migration, template, and command tests
- `repo/README.md` and the framework glossary
- primary task and checkpoint

## Validation Performed

See the primary task record's Validation section for the full gate results of
the third-digest rejection and the fourth-digest approval.

## Remaining Work

Owner confirmation, then completion. The independent review is done and its
eight findings are fixed with regression tests. Every tail item is closed:

- Binding CLI: `bindings list` and `bindings verify [--accept]` ship, with
  acceptance refusing to launder a failed assertion.
- Distribution terminology: v2 vocabulary retired from docs, capabilities,
  generated surfaces, and the wiki; the orientation page is rewritten as
  `knowledge-spaces.md`.
- Golden snapshots: vacuous negatives repaired, node-document validation
  restored to the per-node gate, `selftest` green at 1,430 tests.
- Enterprise fixture rerun: `engine_gates.py` measures the shipped runtime and
  records where it falls short of the prototype's numbers.

## Blockers

- Never approve/apply `a7efbdd3...`, `da690c50...`, or `db1a5b58...`.
- Real second-repository distribution evidence remains pending, and the
  readiness assumptions allow it to stay pending.

## Useful References

- `AI_SYSTEM.md`
- `.hydra-framework/core/knowledge-architecture.md`
- Primary task record referenced above

## Continuation Prompt

Read `AI_SYSTEM.md`, this checkpoint, and the task. Run
`PYTHONPATH=.hydra-framework/engine/src:.hydra-framework/engine/tests/unit python3 -m unittest discover -s .hydra-framework/engine/tests/unit -p 'test_*.py'`
and expect 1,270 passing. Regenerate a manifest at the current checkpoint
commit; never reuse a recorded digest and never approve a rejected one.
