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
- Descendant nodes inherit owners and declare an override only when accountability changes; spaces must declare owners. Scope, identity, provenance, certainty, keywords, and relations never inherit.
- Runtime v2 reading is not retained. The isolated migrator reads v2, while legacy CLI selectors are aliases that resolve only against v3 objects.

## Approved Plan

- Phase 1 revalidates current behavior, creates a checked-in 200+ node enterprise fixture, defines reproducible ground truth/metrics, runs cold-start, path, depth, authoring, and distribution gates, and records rejected alternatives.
- Phase 2 freezes tested contracts for nodes, identity, inheritance, global graph closure, relations/supersession, views, bindings, scopes, routing, compatibility, diagnostics, rollback, and failure behavior.
- Phase 3 implements vertical slices: recursive discovery/validation; global resolution/conflicts; bindings/freshness; two-phase routing and route-level `expand_when`; inheritance tracing; views; distribution; registry storage boundary.
- Phase 4 implements review-gated `knowledge migrate-v2` with dry-run, deterministic moves/rewrites, UID preservation, confidence/unresolved states, idempotence, registry rebuild, and an enforced clean/checkpointed Git boundary for rollback.
- Validate narrowly after each slice, then run reference, full validation, selftest, snapshots, negative tests, migration idempotence, and 200+ node benchmarks. Obtain an independent review before completion.

## Current Stage

Phase 4: third manifest rejected safely; reviewed fourth manifest cleared every isolated gate and is ready to apply.

## Readiness

Status: ready

- Branch or workspace assumptions: branch `main` tracks `origin/main`; the working tree was clean before this task record was created; preserve any subsequently discovered unrelated user edits.
- Relevant canonical docs: `AI_SYSTEM.md`; Hydra framework package state and overview; `capabilities/workflows/task-lifecycle.md`; `repo/knowledge/high-overhead-workflows.md`; `core/placement-rules.md`; current engine code and tests are authoritative for implemented behavior.
- Required dependencies, services, generated artifacts, or private local requirements: Python 3 and repository-bundled test tooling; raw benchmark output and experiments must remain under `.hydra-framework.local/`; the checked-in fixture and summarized reproducible evidence must be shared. No external service is assumed.
- Blockers and assumptions: a real second repository may be unavailable; if so, use a deterministic two-repository fixture and leave the real-repository distribution gate pending. Do not apply an ambiguous or destructive migration without a reviewed dry-run manifest and a focused checkpoint commit. The approved direction is architectural input, but every mechanism remains subject to executable evidence.
- Expected validation command or evidence: targeted engine tests after each slice, `python3 .hydra-framework/scripts/hydra.py ref check`, `python3 .hydra-framework/scripts/hydra.py validate`, `python3 .hydra-framework/scripts/hydra.py selftest`, deterministic packet snapshots, negative contract tests, migration dry-run/idempotence/rollback tests, 200+ node benchmark results, and independent review findings resolved or recorded.
- High-overhead workflow trigger and control: broad executable framework contracts and migration tooling create downstream and data-loss risk. Use an independent validation/review pass, deterministic migration dry-run plus explicit review evidence before apply, and focused Hydra checkpoint/Git commits as rollback boundaries. No separate worktree is required while one execution context owns this clean checkout; reassess before any parallel writer or destructive operation.

## Step State

- Active step: apply the reviewed fourth manifest to this checkout and verify live v3 runtime end to end.
- Next step: close the polish tail - binding CLI, distribution terminology, golden snapshots, enterprise fixture reruns - each scoped concretely before implementation.
- Completed steps: read required contracts and authoritative code; created and validated the primary task; captured a 173-test v2 baseline; added and ran the 216-leaf enterprise fixture; selected global indexed routing and measured depth/scope policy; froze `core/knowledge-architecture.md`; implemented tested contract primitives for recursive nodes/inheritance, strict global graph closure and supersession, namespaced asserted bindings/freshness, reference-only view composition/conflict detection, shared distribution policy, and the registry-independent KnowledgeStore boundary; integrated recursive discovery, global validation/closure, inherited routes, two-phase path rerouting hooks, route-level `expand_when`, v3 context-packet fields, prompt pointers, search/adoption/hook consumers, and fail-closed node parsing into the active engine; removed the flat routing-collision runtime and flat package discovery; converted affected unit tests to v3 fixtures; restored the full 1,246-test unit suite to green.
- Superseded or skipped steps: none.
- Also completed: scoped migration reference rewriting away from engine sources, contract goldens, and the derived registry; made the plan digest reproducible across checkouts; anchored template path rewriting; confined identity/title rewriting to the object sidecar; recorded real move sources in the manifest; redirected the superseded v2 concept doc to the frozen v3 contract; removed v2 authoring guidance from `repo/README.md` and the framework glossary.

## Changed Files

- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-07-knowledge-v3-architecture.md` - durable task state.
- `.hydra-framework/validation/knowledge-v3/enterprise-fixture.json` - checked-in 216-leaf enterprise ground truth with cross-space dependencies and path bindings.
- `.hydra-framework/validation/knowledge-v3/benchmark.py` - reproducible baseline and decision-gate harness.
- `.hydra-framework/validation/knowledge-v3/README.md` - fixture/gate procedure and real-repository limitation.
- `.hydra-framework/core/knowledge-architecture.md` - canonical frozen v3 contract.
- `.hydra-framework/engine/src/hydra_engine/knowledge/{nodes,graph,bindings,views,distribution,storage}.py` - v3 contract implementations.
- `.hydra-framework/engine/src/hydra_engine/knowledge/units.py` - stable UID and typed unit relations.
- `.hydra-framework/engine/src/hydra_engine/installation/seed_copy.py` - distribution-profile policy integration.
- `.hydra-framework/engine/src/hydra_engine/documents/frontmatter_blocks.py` - preserves the YAML parser import boundary for v3 modules.
- `.hydra-framework/engine/tests/unit/knowledge/test_{nodes,graph,bindings,views,distribution,storage}.py` - contract and negative tests.
- `.hydra-framework/engine/src/hydra_engine/knowledge/{checks,routing,routing_diagnostics,context_providers,context_packets,search_index,candidates}.py` - active v3 validation, routing, graph selection, context compilation, and indexing integration.
- `.hydra-framework/engine/src/hydra_engine/knowledge/{packages,package_checks}.py` and deleted `routing_collisions.py` - flat discovery/collision runtime removed; shared node document checks retained pending neutral module rename.
- `.hydra-framework/engine/src/hydra_engine/{checks,cli,commands,installation,thresholds.py}` - v3 consumers, diagnostics, and threshold registry integration.
- `.hydra-framework/engine/tests/unit/{v3_fixtures.py,knowledge,commands,cli,checks,installation}` - v3 fixture and affected consumer tests; obsolete flat routing-collision test removed.
- `.hydra-framework/engine/src/hydra_engine/knowledge/migration_templates.py` - deterministic conversion of inactive v2 authoring templates into the v3 template root.
- `.hydra-framework/engine/tests/repository/test_context_compiler.py` - real-repository packet contract migrated from v2 `packages`/`package_values` to v3 nodes and canonical route identities.

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
- Contract test run: 191 Knowledge tests passed in 0.446s, including depth, invalid scope, relation shape, route override/expand_when, cross-space closure, unresolved dependency, cycle, conflicting supersession, stale/unresolved binding, path binding, reference-only view, view ordering/resolution conflict, distribution leak, and storage-boundary cases.
- `python3 .hydra-framework/scripts/hydra.py validate`: passed after the contract modules; the initial YAML vocabulary in-degree finding was resolved by reusing the existing `frontmatter_blocks` re-export boundary.
- Runtime slice narrow validation: 143 Knowledge tests passed and 10 context-command tests passed after the final routing/packet changes.
- Full runtime-slice unit validation: `PYTHONPATH=.hydra-framework/engine/src:.hydra-framework/engine/tests/unit python3` discovery over `.hydra-framework/engine/tests/unit` ran 1,246 tests with zero failures and zero errors.
- Migrator slice: 1,259 unit tests passed with zero failures/errors. Tests cover deterministic dry-run output, UID evidence, reference/route rewrites, typed-relation conversion, unresolved ambiguous unit expansion, exact-digest approval, reviewer/evidence requirements, changed-plan rejection before writes, and post-apply idempotence.
- `hydra.py validate` now has no architecture/module/caller findings. Its only findings before live migration are two expected stale registry digests and the expected missing v3 `spaces.yaml`; registry/index rebuild is the final apply stage.
- The live repository still uses the v2 on-disk package, so `hydra.py validate` is intentionally not claimed green at this checkpoint; the v3 validator now rejects that active legacy tree until the reviewed migration applies.
- Live dry-run at checkpoint `67fada6a3c89a638768c8b5e2eba15eed8e7feb2` produced digest `sha256:a7efbdd3cbd4afa8275db1eb45b4cd56c80e9b249986f390df86e345e3ad29f2`: one package, 24 writes, 16 deletes, 16 preserved UIDs, six external reference rewrites, five route rewrites, 36 de-duplicated advisory binding candidates, and zero declared unresolved decisions.
- Independent isolated apply review rejected that digest. Apply and `ref check` succeeded, but `validate` found two moved overview links still targeting `routing.yaml` plus an active legacy root README, and `selftest` exposed v2 repository context-test consumers (`package_values`/`packages`). The manifest therefore overstated confidence despite known-invalid postconditions; it was not approved or applied to this checkout.
- The reviewer reran the same filtered selftest before apply and confirmed its 11 failures/6 errors already existed at checkpoint `67fada6`; they are required v3 consumer/golden debt, not an apply regression. The three added `validate` failures were caused by the rejected plan.
- Corrective tests now prove moved routing links target `space.yaml`, the legacy root/templates are fully removed after deterministic conversion into `repo/knowledge/templates/space`, route rewrites change consumer text, binding-candidate sources use migrated paths, and tampered manifest payloads are rejected even when the stored digest/approval fields are unchanged.
- Runtime routing accepts canonical `hydra://knowledge-route/...` selectors (including inherited routes) while retaining the bounded deprecated `owner:name` CLI compatibility form.
- Replacement corrective unit run: 1,262 tests passed with zero failures/errors. `hydra.py validate` again reports only the expected pre-migration stale registry entries and missing `spaces.yaml`; all module size, mirror, fan-out, and caller gates pass.
- Second dry-run at checkpoint `24c4775aa789b772cded6a32cd72ee5dbdc7cecb` produced digest `sha256:da690c5044497bc1d228105947c047a50e4c0dcebfad4bf67c8f1eac4e43f010`: 36 writes, 30 deletes, 16 preserved UIDs, 36 advisory candidates on v3 paths, and zero declared unresolved decisions.
- Independent isolated apply rejected the second digest because the new placeholder `templates/space/space.yaml` was discovered as an invalid live node and `repo/object-sidecars.yaml` retained all old template identities/paths, causing mandatory registry rebuild failure after file mutation. This checkout was not changed.
- The correction now emits the node template as non-discoverable `space.yaml.template`, rewrites sidecar keys, v3 knowledge-template identities, titles, paths and flat provenance, and records/applies a deterministic mode for every write so the template check script stays executable. Focused tests cover the mappings and mode; the full unit suite is now 1,263 passing.

- Third dry-run at checkpoint `dd617b5ab835b91078d54768b6b6530ecb0fc3b5` produced digest `sha256:db1a5b58f255d884581e42edbf5ea55ab1e3ab92d37b3d205592c0694a0ab598`: 50 writes, 30 deletes, 19 reference rewrites.
- Independent isolated apply rejected that third digest. `ref check` and `validate` both passed after apply, which is exactly why postconditions were checked harder: the unit suite gained seven failures and `selftest` gained the same seven. Blanket reference rewriting had mutated engine sources, the migrator's own tests, and contract goldens, including neutering `migration_templates.rewrite_references` into identity replacements.
- The same review found the third digest irreproducible: the plan embedded raw `st_mode`, so a clean clone computed `sha256:f64c5ec2...` for identical content and no reviewer could ever approve the digest the target checkout would compute.
- It also found the unanchored `/routing.yaml` rewrite corrupting the real space's registry path and producing a duplicate `hydra://knowledge-space/hydra-framework` registry key, the repository-wide `Knowledge Package` title rewrite half-renaming wiki and doc prose, and manifest write rows attributing basename-matched sources to unrelated files.
- Corrections: reference rewriting now skips `engine/`, the derived registry, `.git`, and the private local tier; only the tracked executable bit is recorded, and modes apply only to files the migration creates; template path rewriting is anchored to the template directory; identity, key, and title rewriting is confined to `repo/object-sidecars.yaml`; write rows carry the real move source or none. The superseded `repo/knowledge/knowledge-packages.md` is deleted with references redirected to `core/knowledge-architecture.md`.
- `hydra.py ref index` cleared the two long-standing stale registry digests, so `validate` before migration reports only the expected missing v3 `spaces.yaml`.
- Full unit suite after the corrections: 1,270 tests, zero failures/errors, including new regression tests for rewrite scope, digest reproducibility under changed file modes, and write-row source/mode attribution.
- Fourth dry-run at checkpoint `9ac790950fe41f99528171030b0ef373deb43a4d` produced digest `sha256:17389e512810e1baee777cbe7d0fc78110f7b154356bcc76bf9aa973e5ac7ce9`: 40 writes, 31 deletes, nine reference rewrites, zero unresolved decisions. A clean clone reproduced the manifest byte-identically.
- Independent isolated apply of the fourth digest passed every gate: `ref check` ok on 56 objects; `validate` ok; 1,270 unit tests green; `selftest` gained zero failures and cleared the four real-repository context-compiler failures; `check.sh` landed executable while in-place rewrites kept their existing modes; the legacy tree was fully removed; the node-document gate passed; a repeat dry-run reported `already-v3` with zero writes and a committed second apply was a clean no-op.
- Live v3 runtime verified in the migrated clone: `route-prompt` emits v3 node pointers on v3 paths, `compile-context` produces a `hydra-framework.context-packet.v2` packet selecting v3 nodes and routes, `knowledge-search` returns v3-path snippets with preserved UIDs, and `explain-path` resolves ownership.
- Ten `selftest` golden-snapshot failures remain. They are present at the pre-apply baseline as well, are not apply regressions, and are the golden-snapshot item in the polish tail.

## Blockers

- Real second-repository distribution evidence is not yet known to be available; deterministic fixture evidence can advance the implementation, but cannot silently satisfy that production gate.
- Migration digest `sha256:a7efbdd3cbd4afa8275db1eb45b4cd56c80e9b249986f390df86e345e3ad29f2` is explicitly rejected and must never be approved or applied. Its known defects are corrected, but the replacement digest still requires isolated post-apply proof.
- Replacement digest `sha256:da690c5044497bc1d228105947c047a50e4c0dcebfad4bf67c8f1eac4e43f010` is also rejected and must never be approved or applied; its sidecar/template discovery defects are corrected in a later slice.
- Third digest `sha256:db1a5b58f255d884581e42edbf5ea55ab1e3ab92d37b3d205592c0694a0ab598` is rejected and must never be approved or applied; blanket reference rewriting corrupted engine sources, tests, and goldens, and the digest was not reproducible across checkouts.

## Continuation Notes

What another model or developer needs to continue safely.

- Running state: none
- Resume check: `PYTHONPATH=.hydra-framework/engine/src:.hydra-framework/engine/tests/unit python3 -m unittest discover -s .hydra-framework/engine/tests/unit -p 'test_*.py'`; expect 1,270 passing tests. Never approve or apply any rejected digest recorded in Blockers. Regenerate a manifest at the current checkpoint commit rather than reusing a recorded digest.
