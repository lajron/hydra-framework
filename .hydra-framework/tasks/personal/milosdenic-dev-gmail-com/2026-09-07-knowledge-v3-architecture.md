# Task: knowledge-v3-architecture

Status: active
Owner: milosdenic-dev-gmail-com
Created: 2026-09-07
Updated: 2026-09-07

## Goal

Implement Knowledge v3 Option D end to end: bounded recursive policy/accountability nodes, typed cross-space relations, reference-only composed views, namespaced logical bindings, scope-aware distribution, a stable registry storage boundary, safe v2 migration, enterprise benchmarks, and migration of all consumers without permanent dual architecture.

## Confirmed Decisions

- Target topology is Knowledge v3 Option D: a bounded accountability/policy tree, typed cross-space graph, reference-only composed views, namespaced logical bindings, executable distribution scopes, and a registry storage interface independent of physical sharding.
- Stable system boundaries define identity paths; ownership remains mutable metadata.
- Registry sharding is out of scope except for the minimal storage interface needed to keep Knowledge v3 independent of registry layout.
- V3 is the only write architecture after migration. Any dual-read support is bounded to the migration window and must be removed after the repository and enterprise fixture migrate.
- Ambiguity, unresolved references/bindings, dependency cycles, supersession conflicts, view-order conflicts, invalid scopes, and depth violations fail closed.
- Rollback is provided by focused Hydra checkpoints and Git commits at approved milestone boundaries; do not create a duplicate backup/restore architecture in the migrator.
- The cold-start gate selects global indexed node retrieval with a two-pointer implicit cap. The accountability tree explains and governs selection; it is not a mandatory first-stage pruning boundary.
- The measured default topology depth is three levels including the space; the hard ceiling is four. Units remain legal at every routable level, so the fourth level is an exception rather than a required shape.
- Logical paths are a corrective and explicit routing signal. They do not replace prompt routing.

## Approved Plan

- Phase 1 revalidates current behavior, creates a checked-in 200+ node enterprise fixture, defines reproducible ground truth/metrics, runs cold-start, path, depth, authoring, and distribution gates, and records rejected alternatives.
- Phase 2 freezes tested contracts for nodes, identity, inheritance, global graph closure, relations/supersession, views, bindings, scopes, routing, compatibility, diagnostics, rollback, and failure behavior.
- Phase 3 implements vertical slices: recursive discovery/validation; global resolution/conflicts; bindings/freshness; two-phase routing and route-level `expand_when`; inheritance tracing; views; distribution; registry storage boundary.
- Phase 4 implements review-gated `knowledge migrate-v2` with dry-run, deterministic moves/rewrites, UID preservation, confidence/unresolved states, idempotence, registry rebuild, and an enforced clean/checkpointed Git boundary for rollback.
- Validate narrowly after each slice, then run reference, full validation, selftest, snapshots, negative tests, migration idempotence, and 200+ node benchmarks. Obtain an independent review before completion.

## Current Stage

Phase 2: freeze Knowledge v3 contracts from gate evidence.

## Readiness

Status: ready

- Branch or workspace assumptions: branch `main` tracks `origin/main`; the working tree was clean before this task record was created; preserve any subsequently discovered unrelated user edits.
- Relevant canonical docs: `AI_SYSTEM.md`; Hydra framework package state and overview; `capabilities/workflows/task-lifecycle.md`; `repo/knowledge/high-overhead-workflows.md`; `core/placement-rules.md`; current engine code and tests are authoritative for implemented behavior.
- Required dependencies, services, generated artifacts, or private local requirements: Python 3 and repository-bundled test tooling; raw benchmark output and experiments must remain under `.hydra-framework.local/`; the checked-in fixture and summarized reproducible evidence must be shared. No external service is assumed.
- Blockers and assumptions: a real second repository may be unavailable; if so, use a deterministic two-repository fixture and leave the real-repository distribution gate pending. Do not apply an ambiguous or destructive migration without a reviewed dry-run manifest and a focused checkpoint commit. The approved direction is architectural input, but every mechanism remains subject to executable evidence.
- Expected validation command or evidence: targeted engine tests after each slice, `python3 .hydra-framework/scripts/hydra.py ref check`, `python3 .hydra-framework/scripts/hydra.py validate`, `python3 .hydra-framework/scripts/hydra.py selftest`, deterministic packet snapshots, negative contract tests, migration dry-run/idempotence/rollback tests, 200+ node benchmark results, and independent review findings resolved or recorded.
- High-overhead workflow trigger and control: broad executable framework contracts and migration tooling create downstream and data-loss risk. Use an independent validation/review pass, deterministic migration dry-run plus explicit review evidence before apply, and focused Hydra checkpoint/Git commits as rollback boundaries. No separate worktree is required while one execution context owns this clean checkout; reassess before any parallel writer or destructive operation.

## Step State

- Active step: define executable v3 node, relation, inheritance, view, binding, scope, route, compatibility, and failure contracts with negative tests.
- Next step: freeze the contracts in canonical rules and tests, checkpoint them, then implement recursive discovery and global resolution as the first vertical slice.
- Completed steps: read the operating contract, routed framework package state/overview, task lifecycle, high-overhead workflow matrix, placement rules, silent-failure modes, current architecture, build status, problems, and the full approved architecture proposal; checked the board; confirmed no competing active task; created and completed this record; verified the v2 engine flow and consumer surface; captured a passing 173-test Knowledge baseline; defined a checked-in deterministic 216-leaf/258-total-node fixture and reproducible cold-start, path, dependency, depth, authoring, latency, ambiguity, false-positive, pointer-budget, and distribution metrics; ran and reviewed the first benchmark; recorded the failed naive-index attempt and selected the evidence-backed indexed retrieval contract.
- Superseded or skipped steps: none.

## Changed Files

- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-07-knowledge-v3-architecture.md` - durable task state.
- `.hydra-framework/validation/knowledge-v3/enterprise-fixture.json` - checked-in 216-leaf enterprise ground truth with cross-space dependencies and path bindings.
- `.hydra-framework/validation/knowledge-v3/benchmark.py` - reproducible baseline and decision-gate harness.
- `.hydra-framework/validation/knowledge-v3/README.md` - fixture/gate procedure and real-repository limitation.

## Validation

- `python3 .hydra-framework/scripts/hydra.py board` before task creation: no active task records.
- Initial `git status --short --branch`: `main...origin/main`, with no pre-existing changes reported.
- `PYTHONPATH=.hydra-framework/engine/src python3 -m unittest discover -s .hydra-framework/engine/tests/unit/knowledge -p 'test_*.py' -v`: 173 tests passed in 0.426s.
- Direct code inspection confirmed v2 flat package/unit discovery, package-local `requires` closure, global keyword/route collisions, route-level `expand_when` not consumed, deterministic packet budget/omission behavior, and whole-tree seed copy.
- `python3 .hydra-framework/scripts/hydra.py validate`: passed after task creation.
- Initial naive global node scorer failed the cold-start gate: recall 0.4630 and mean pointer budget 25.56 versus v2 recall 0.4444 and 22.17. This disproved identity-only global scoring.
- Reviewed indexed-hint run on 216 leaves and 21 workloads passed all deterministic gates: global-index recall@3 0.6746 versus v2 0.4921; precision@3 0.8333 versus 0.5397; mean pointer tokens 24.71 versus 28.33; ambiguity 0.1429 versus 0.5238; false positives 0.1538 versus 0.4444; median routing latency 0.1732 ms versus 0.0638 ms. The latency increase is accepted because it remains sub-millisecond in this fixture.
- Path signal: useful bindings for 21/21 workloads, two cold misses corrected, mean/max one bound node. Global dependency fixture closure was complete (1.0).
- Depth replay selected depth 3 with mean browse cost 5.807 versus 7.209 at depth 2, 8.307 at depth 4, and 10.807 at depth 5. Depth 4 remains the hard exception ceiling.
- Authoring fixture repeats 1,080 v2 policy fields versus 42 v3 space/area declarations; v3 requires three placement decisions per leaf versus one in v2, an accepted explicit cost.
- Deterministic distribution fixture copied 36 base-seed leaves in the base profile and 144 base/common leaves in the common profile with zero repo-local leaks. The real second-repository gate remains pending.
- Rejected by evidence: identity-only global scoring, flat v2 keyword proportion, and mandatory space-first hierarchical pruning.

## Blockers

- Real second-repository distribution evidence is not yet known to be available; deterministic fixture evidence can advance the implementation, but cannot silently satisfy that production gate.

## Continuation Notes

What another model or developer needs to continue safely.

- Running state: none
- Resume check: `python3 .hydra-framework/validation/knowledge-v3/benchmark.py --output .hydra-framework.local/knowledge-v3/gates.json && python3 .hydra-framework/scripts/hydra.py validate`; expect all deterministic fixture gates except the explicitly pending real-repository distribution gate to pass.
