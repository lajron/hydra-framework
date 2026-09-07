# Checkpoint: knowledge-v3-architecture

Task: .hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-07-knowledge-v3-architecture.md
Created: 2026-09-07
Status: paused

## Goal

Implement Knowledge v3 Option D end to end, including enterprise evidence,
recursive accountability nodes, global typed resolution, bindings, views,
scope-aware distribution, safe v2 migration, and migration of every active
consumer to one v3 write/read architecture.

## Confirmed Decisions

- Use global indexed node retrieval with a two-pointer implicit cold-start cap;
  use the tree for governance and explanation, not mandatory space-first pruning.
- Default to three levels including the space and enforce a hard ceiling of four.
- Use logical paths for corrective/explicit routing, followed by route-level
  `expand_when`; they are not the only cold-start signal.
- Fail closed on ambiguity, unresolved refs/bindings, cycles, supersession/view
  conflicts, invalid scopes, and depth violations.
- Use focused Hydra checkpoint/Git commits as rollback boundaries.

## Approved Plan

Run and preserve gates, freeze executable contracts, implement ten vertical
slices, ship a review-gated/idempotent v2 migrator, migrate the live framework,
remove active v2 mechanisms, run full validation, and obtain independent review.

## Completed Work

- Verified the current v2 implementation and consumers against source and tests.
- Captured a clean baseline: 173 Knowledge unit tests passed.
- Added a checked-in 216-leaf/258-total-node enterprise fixture, benchmark, and
  reproducible procedure.
- Recorded the initial failed naive-index result instead of tuning it away.
- Added indexed route/content hints matching the intended unified index and reran
  21 workloads. All deterministic gates pass except the explicitly pending real
  second-repository distribution gate.

## Current Stage

Phase 2: freeze Knowledge v3 contracts from gate evidence.

## Changed Files

- `.hydra-framework/validation/knowledge-v3/enterprise-fixture.json`
- `.hydra-framework/validation/knowledge-v3/benchmark.py`
- `.hydra-framework/validation/knowledge-v3/README.md`
- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-07-knowledge-v3-architecture.md`
- This checkpoint.

## Validation Performed

- `python3 .hydra-framework/scripts/hydra.py validate`: passed.
- Knowledge unit baseline: 173 passed.
- Final fixture run: indexed recall@3 0.6746 versus v2 0.4921; precision
  0.8333 versus 0.5397; pointer tokens 24.71 versus 28.33; ambiguity 0.1429
  versus 0.5238; false positives 0.1538 versus 0.4444; two cold misses
  corrected by paths; dependency closure 1.0; zero repo-local distribution
  leaks. Raw machine timing is in ignored local output.

## Remaining Work

Freeze and test all v3 contracts; implement discovery, graph/conflicts, bindings,
two-phase routing, inheritance, views, distribution, and storage boundary;
implement and review migration; migrate live knowledge and consumers; remove v2;
run full validation and independent review.

## Blockers

The real second-repository distribution gate is pending because no real adopted
second repository is available in scope. The deterministic two-profile fixture
passes and permits all non-production-dependent work to continue.

## Useful References

- `AI_SYSTEM.md`
- `.hydra-framework/core/placement-rules.md`
- `.hydra-framework/repo/knowledge/high-overhead-workflows.md`
- `.hydra-framework/validation/knowledge-v3/README.md`
- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-07-knowledge-v3-architecture.md`

## Continuation Prompt

Start by reading `AI_SYSTEM.md`, this checkpoint, and the referenced task state. Continue from the current stage without relying on prior conversation history.
