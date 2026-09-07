# Checkpoint: knowledge-v3-architecture

Task: .hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-07-knowledge-v3-architecture.md
Created: 2026-09-07
Status: paused

## Goal

Implement and migrate to Knowledge v3 Option D with one active runtime model,
evidence-gated contracts, safe reviewed migration, and full validation.

## Confirmed Decisions

- Global indexed node retrieval with two implicit pointers; the tree governs
  accountability and inheritance rather than acting as mandatory pruning.
- Default depth is three including the space; hard maximum is four.
- Descendants inherit owners/defaults/routes with source tracing; identity,
  scope, provenance, certainty, keywords, and relations do not inherit.
- Unresolved dependencies/bindings, cycles, ambiguity, supersession conflicts,
  view conflicts, invalid scopes, and invalid depth fail closed.
- The active runtime is v3-only. The forthcoming migrator is the isolated v2
  reader. Git checkpoint commits are the rollback mechanism.

## Approved Plan

Build the review-gated migrator next, apply it to the live framework only after
a clean checkpoint and reviewed dry-run, finish distribution/binding CLI and
identity integration, remove remaining v2 terminology, run full validation and
benchmarks, then obtain an independent review.

## Completed Work

- Baseline and decision gates completed on the checked-in 216-leaf fixture.
- Contracts frozen in `core/knowledge-architecture.md`; contract checkpoint is
  commit `8ffcc4a`.
- Implemented node/inheritance, global graph, bindings/freshness, views,
  distribution policy, and stable KnowledgeStore primitives.
- Integrated v3 routing, recursive validation, global dependency selection,
  route-level `expand_when`, v3 packet fields, prompt pointers, path rerouting
  hooks, indexing, adoption, edit hooks, fingerprinting, and CLI consumers.
- Removed flat package discovery and the flat routing-collision runtime/tests.
- Converted affected tests to deterministic v3 fixtures. Full unit suite is
  green: 1,246 tests, zero failures/errors.

## Current Stage

Phase 3 slice 2: migration implementation and live repository migration.

## Changed Files

- Active engine: `knowledge/{nodes,checks,graph,bindings,views,distribution,
  storage,routing,routing_diagnostics,context_providers,context_packets,
  search_index,candidates,packages,package_checks,units}.py`.
- Consumers: `checks/`, `cli/`, `commands/`, `installation/`, threshold policy.
- Tests: affected `knowledge`, `commands`, `cli`, `checks`, and `installation`
  modules plus `tests/unit/v3_fixtures.py`.
- Deleted: active `knowledge/routing_collisions.py` and its obsolete test.
- Durable state: primary task and this checkpoint.

## Validation Performed

- 143 Knowledge tests passed after runtime integration.
- 10 context-command tests passed.
- Full unit discovery: 1,246 passed, zero failures/errors.
- Earlier deterministic enterprise gates pass; real second-repository
  distribution evidence remains explicitly pending.
- Full `hydra.py validate` is intentionally pending live migration because the
  new validator correctly rejects the still-present active v2 package tree.

## Remaining Work

Implement/test `knowledge migrate-v2`; create/review dry-run manifest; apply to
the live framework from a clean checkpoint; preserve every UID and rewrite
routes/references; add binding verify/accept CLI; finish identities and object
reference integration; make adoption/reconciliation/export fully scope-aware;
rename remaining package-era APIs/fields; rebuild registry/index; run snapshots,
negative tests, migration idempotence, benchmarks, ref check, validate,
selftest, and independent review.

## Blockers

No implementation blocker. The only pending external-quality gate is a real
second-repository distribution test; deterministic distribution fixtures pass.

## Useful References

- `AI_SYSTEM.md`
- `.hydra-framework/core/knowledge-architecture.md`
- `.hydra-framework/validation/knowledge-v3/README.md`
- Primary task record referenced above

## Continuation Prompt

Read `AI_SYSTEM.md`, this checkpoint, and the primary task. Run
`PYTHONPATH=.hydra-framework/engine/src:.hydra-framework/engine/tests/unit python3 -m unittest discover -s .hydra-framework/engine/tests/unit -p 'test_*.py'`
and expect 1,246 passing tests. Inspect `git status --short`; the next code step
is the isolated, review-gated `knowledge migrate-v2` implementation. Do not edit
the live v2 tree until its dry-run manifest is reviewed and a clean Git
checkpoint exists.
