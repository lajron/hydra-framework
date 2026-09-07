# Checkpoint: knowledge-v3-architecture

Task: .hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-07-knowledge-v3-architecture.md
Created: 2026-09-07
Status: paused

## Goal

Migrate the framework from flat Knowledge v2 to the selected v3 Option D model
without a permanent dual runtime, using reviewed Git-checkpoint rollback.

## Confirmed Decisions

- `knowledge migrate-v2` is the only v2 reader.
- Apply requires the exact reviewed plan digest, reviewer/evidence fields, zero
  unresolved decisions, the recorded commit, and a clean worktree.
- The migrator makes no backup tree; Git commits/checkpoints are rollback.
- Legacy string relations become typed `relates-to` edges. Ambiguous unit-level
  expansion is unresolved rather than guessed.

## Approved Plan

Commit this tested migrator, generate the live dry-run from that clean commit,
review it, apply it, rebuild registry/index, verify idempotence, and checkpoint.

## Completed Work

- Runtime v3 slice checkpointed at `76b7ebd`.
- Implemented deterministic manifest planning, UID/move/reference/route and
  binding-candidate evidence, exact approval gates, clean Git preconditions,
  deterministic apply, and idempotence.
- Wired `knowledge migrate-v2` dry-run/apply CLI and post-apply registry/search
  index rebuild.
- Added v3 Knowledge identities and typed relation extraction to the generic
  object boundary.
- Refactored boundaries to satisfy module size, fan-out, and vocabulary limits.
- Full unit suite: 1,259 passing.

## Current Stage

Phase 4: ready to create the live dry-run review manifest.

## Changed Files

- `knowledge/migration_{v2,git,format}.py`
- `commands/knowledge_migration.py` and `commands/knowledge.py`
- `knowledge/{contracts,node_catalog,context_support,unit_selection,view_routing}.py`
- `commands/knowledge_docs.py`, object families/envelopes, and affected imports
- Mirror and migration tests for each new module
- Primary task and checkpoint

## Validation Performed

- Full unit discovery: 1,259 passed, zero failures/errors.
- `hydra.py validate`: architecture/caller checks pass; expected pre-migration
  findings are stale registry digests and missing `spaces.yaml`.
- `git diff --check` still required immediately before commit.

## Remaining Work

Commit; dry-run; review and approve exact digest; apply; verify idempotence,
UIDs, refs, index and live v3 validation; convert/delete legacy templates;
finish binding/distribution/terminology slices; full benchmarks and review.

## Blockers

No blocker. Real second-repository distribution evidence remains pending.

## Useful References

- `AI_SYSTEM.md`
- `.hydra-framework/core/knowledge-architecture.md`
- Primary task record referenced above

## Continuation Prompt

Read `AI_SYSTEM.md`, this checkpoint, and the task. Confirm commit/worktree state,
then run the exact dry-run command in the task continuation notes. Do not apply
until every manifest section is reviewed and the exact digest is approved.
