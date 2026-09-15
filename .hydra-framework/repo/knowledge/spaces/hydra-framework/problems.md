---
hydra_id: "hydra://knowledge-slice/hydra-framework/problems"
uid: "3b5cdad3-e87f-4af2-b8c6-c5353c7a6d6e"
schema_version: "3"
kind: "knowledge-slice"
title: "Hydra Framework Problems"
status: "active"
scope: "base-seed"
owners:
  team: "hydra"
relations:
  - type: "relates-to"
    target: "hydra://knowledge-space/hydra-framework"
provenance:
  sources: []
---

# Problems

Status: active
Updated: 2026-09-15

Concrete unresolved concerns for Hydra's own machinery. Each needs evidence, not
opinion. Resolve or close with a reason; do not let entries rot.

## Open

### P16: No documentation surface can be asked whether a source it depends on has changed (2026-09-14)

- Evidence: `knowledge stale` asks exactly that of the 7 knowledge units and reports 2 stale on `main` at 7801b1d, reading `provenance.sources` + `source_digests` + `checked_on` through `knowledge/freshness.py:287-314`. No wiki page carries that contract: 0 of 40 pages under `project-wiki/` is a registered object, so none is in `provenance`, and `citers_of_source_path` (`objects/store_queries.py:105-112`) returns nothing for a source a wiki page describes. `project-wiki/hydra-framework/reference/source-map.md` records the dependency by hand in 19 prose rows covering 23 pages; `wiki/links.py:44` checks those links resolve and nothing checks whether the targets changed. Measured drift with no detector today: 5 of 70 registered commands are absent from `command-surface.md`, and `checks/validator_registry.py:21` describes `validate`/`doctor`'s "ten checks" where `len(VALIDATORS)` is 19.
- Impact: documentation dependency is maintainer memory rather than repository state, so drift is found by someone noticing. It is not a wiki-only gap: 4 of the 8 drift items measured during the review are inside the engine, in files that are themselves Hydra objects, and a mechanism scoped to `project-wiki/` would catch none of them. Current drift is small, which is the condition under which a detector can be built and validated against a corpus still worth trusting.
- Resolution: unresolved, and the mechanism is decided. Reviewed across four phases in `.hydra-framework/evolution/candidates/repository-intelligence-review.md`, now `captured`; the reviewed proposal `2026-09-14-repository-intelligence-and-wiki-projections` is `superseded` by the MVP in that review's `03-architecture-and-mvp.md` section 4 as amended by its `04-decision.md` section 1. Wiki pages become objects through an object sidecar under `.hydra-framework/surfaces/wiki/`, carrying the same `provenance` contract knowledge units already use, under one `Documentation` object family that is deliberately not in `SEARCH_FAMILIES`: it carries a non-retrieving context provider, so a page is addressable without its prose ever becoming a `compile-context` candidate. No schema change, no store change, no envelope change, and no change to `knowledge/freshness.py`; measured at 1633 tests passing in an isolated clone. Owned by `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-14-repository-documentation-dependency-mvp.md`. Two questions stay open inside it: the false-positive rate of page-level digest staleness, which has never run anywhere and which `wiki audit` is what measures, and whether `ref index` stays inside the 30 s hook budget as the object count grows, which P5 and P12 own.
- Certainty: confirmed

### P12: Incremental knowledge-index update cost scales with corpus size, not with the changed document (2026-09-13)

- Evidence: section 8 benchmark in `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-12-design-scalable-knowledge-freshness.md` (correctness-gated, 5 warmups + 30 samples, disposable 1k/10k Git fixtures). At 10,000 governed documents, editing exactly one document costs p50 11544ms / p95 12042ms to reach the published index -- the same order of magnitude as a full rebuild (p50 15910ms / p95 16438ms), not a small constant. `index_cache.update_index` (`.hydra-framework/engine/src/hydra_engine/knowledge/index_cache.py`) opens the current publication and calls `source_conn.backup(conn)` -- a full-database copy -- before applying the one-document delta, then `publish_versioned` (`ports/sqlite_db.py`) fsyncs and atomically replaces the whole resulting file (about 20MB at 10k documents). Cost is O(database size), not O(changed rows).
- Impact: none of section 8's six latency gates are met at 10k (engine clean read, CLI clean read, full rebuild, and single-document incremental all miss; the incremental miss is roughly 120x). The freshness mechanism itself (fingerprint, guard, delta detection in `freshness.py`) is correct and fast; the SQLite publication layer built on top of it is what does not scale.
- Correction (2026-09-13): the attribution above is wrong in two ways, established by direct measurement during `2026-09-13-scalable-incremental-knowledge-index` Phase 1 and left here rather than rewritten, because the original reasoning is what a later reader needs to not repeat. First, the full-database copy is a minor term, not the cause: at 10,000 documents and a 42.1MB file, `publish_versioned` with the `backup()` copy measured p50 628.64ms and the `documents_from_connection` + `_corpus_digest` meta rewrite measured p50 186.34ms, together about 815ms of a measured 11544ms incremental. The dominant remainder is that `search_index._update_index`'s `apply_update` re-does whole-corpus canonical work regardless of delta size, chiefly `index_cache.write_changed_knowledge_rows` calling `storage.build_knowledge_store(paths)`, which `read_unit`s every governed unit in the tree and then keeps only the changed ones. Second, only two of the six gates (full rebuild, single-document incremental) relate to the publication layer at all; the four clean-read gates are caused by P13. A related deletion: the `digest` meta row costing that 186ms per update is never verified in production, since `index_cache.load_documents` checks it only when `expected_digest` is passed and the sole production caller never passes one.
- Resolution: unresolved. This is a deliberate consequence of the immutable-versioned-publication design (`sqlite_db.py`'s `publish_versioned`), chosen in this same task's Phase 2 to fix a real earlier hazard (replacing a file live WAL readers held open gave no portable old-or-new boundary). The believed fix is to switch the published index to one persistent SQLite file in WAL mode, mutated in place for incremental updates via real row-level `DELETE`/`INSERT` instead of a full-file copy, while keeping full rebuild on the existing temp-file-then-atomic-replace path. This preserves the same reader-safety property (no reader ever observes a torn or mixed generation) through WAL's native snapshot isolation instead of through "never touch a published file twice." Now owned by `2026-09-13-scalable-incremental-knowledge-index`, which also revises the "keep full rebuild on temp-file-then-atomic-replace" half of this plan: on a persistent file that would reopen the very live-WAL-reader hazard the versioned design was built to close, so full rebuild becomes an in-place transaction and no published file is ever replaced.
- Certainty: confirmed

### P5: The warm KnowledgeStore read path is still repo-linear per invocation (file-stat pass)

- Evidence: phase-instrumented on this repository's real tree (1 space, 7 units), not the synthetic fixture. `_source_manifest` -> `_search_files` rglobs and stats every governed file, 24.3ms of ~45ms warm retrieval at 316 files. `_load_fresh_documents` does `SELECT *` over all documents including body text (2.9ms), then `substring_search` scans them all in Python (5.6ms).
- Impact: negligible at today's scale. Warm retrieval cost grows with the size of the governed file set regardless of how many nodes a query actually selects. Would surface as real latency once the governed corpus grows.
- Resolution: unresolved and deliberately deferred. The index-build half of this problem (`_package_for`/`_routing_fields` re-parsing the node tree once per document) is fixed; see R9. The remaining file-stat pass would need a cheaper freshness signal than statting every governed file per invocation. Revisit when the governed corpus passes roughly 2k files, or when `route-prompt` p50 passes 0.3s, whichever comes first.
- Certainty: inferred

### P1: Codex capability classes resolve to no model

- Evidence: `.hydra-framework/adapters/providers/codex/capability-map.yaml` maps every capability class to `unresolved`; only `effort_budgets` resolve.
- Impact: generated `.codex/agents/*.toml` omit `model`, so every Hydra role runs on whatever model the host's Codex config selects. Capability-based routing does not reach Codex.
- Resolution: deliberate, not pending. Codex exposes concrete model slugs rather than stable aliases, and the only available source is the local account's model catalog — machine- and plan-specific state that does not belong in shared framework truth, and that would override the host's own `model` setting. Revisit if Codex publishes stable aliases.
- Certainty: confirmed

## Resolved

### R15: Documentation and implementation claims need reconciliation (2026-09-15, was P17)

- Evidence:
  - Page `project-wiki/hydra-framework/architecture/object-context-model.md` says the object handlers cover Markdown, YAML, and Python "under the engine source root." `.hydra-framework/engine/src/hydra_engine/objects/object_handlers.py:97-123` shows Markdown and YAML use the whole Hydra root, while only Python is rooted at `engine/src`.
  - The engine claim in scope through `project-wiki/hydra-framework/architecture/engine.md`, `.hydra-framework/engine/src/hydra_engine/objects/discovery.py:67-69`, says a sidecar can make a directory an object. `.hydra-framework/engine/src/hydra_engine/objects/envelopes.py:156` always fingerprints the object path, and `.hydra-framework/engine/src/hydra_engine/documents/digests.py:11-13` reads it as text, so a directory cannot pass object construction.
  - The engine claim in scope through `project-wiki/hydra-framework/architecture/engine.md`, `.hydra-framework/engine/src/hydra_engine/commands/hooks.py:1-14`, says its module fan-out is 7. Imports at `.hydra-framework/engine/src/hydra_engine/commands/hooks.py:23-30` total 8, and `.hydra-framework/engine/src/hydra_engine/architecture.py:21` sets the fan-out cap to 8.
  - The engine claim in scope through `project-wiki/hydra-framework/architecture/engine.md`, `.hydra-framework/engine/src/hydra_engine/cli/parser.py:12-13`, says `scripts/hydra.py` registers ten commands, but `.hydra-framework/scripts/hydra.py:48-51` registers only `selftest` through its extra hook.
  - The engine claim in scope through `project-wiki/hydra-framework/architecture/engine.md`, `.hydra-framework/engine/src/hydra_engine/checks/validator_registry.py:21,34-35,47`, describes ten validators, while `.hydra-framework/engine/src/hydra_engine/checks/validator_registry.py:94-106` defines 19 `VALIDATORS`.
  - The engine claim in scope through `project-wiki/hydra-framework/architecture/engine.md`, `.hydra-framework/engine/src/hydra_engine/objects/object_handlers.py:44-47`, says two engine modules declare envelopes. Frontmatter in `.hydra-framework/engine/src/hydra_engine/identity/object_families.py:1-15`, `.hydra-framework/engine/src/hydra_engine/objects/object_handlers.py:1-15`, and `.hydra-framework/engine/src/hydra_engine/checks/validator_registry.py:1-16` establishes three.
  - The engine claim in scope through `project-wiki/hydra-framework/architecture/engine.md`, `.hydra-framework/engine/src/hydra_engine/commands/references.py:96-98`, describes `ref rdeps` as serving the `refs` index, but `.hydra-framework/engine/src/hydra_engine/commands/references.py:99-110` calls `store_queries.citers_of`, whose implementation at `.hydra-framework/engine/src/hydra_engine/objects/store_queries.py:95-103` queries `relations`.
- Impact: The affected documentation and engine maintenance prose can direct readers to the wrong scope, count, or dependency table. The ten content-page provenance entries are now auditable, but they do not correct these claims.
- Resolution: Corrected the wiki and engine claims without changing behavior. The object-context page now states the broader Markdown and YAML root, YAML's `cognition/` exclusion, and Python's `engine/src` root. Sidecar discovery now states that target construction fingerprints and reads text, so directories are not valid objects. The hook documentation records the verified pre-M6 fan-out of 8 and the post-M6 runtime fan-out of 7, the parser documents dynamic module registration plus the separate `selftest` hook, the validator registry records 19 validators, the object-handler registry records three envelope-declaring modules, and `ref rdeps` documents `store_queries.citers_of` over relations rather than the refs table.
- Validation: Focused hook, Git, wiki-audit, and agent-hook contract suites pass 14, 23, 15, and 8 tests. Each of the eight affected pages was fingerprinted once after the corrections.
- Certainty: confirmed

### R12: Every knowledge query materialized and scanned the entire corpus in Python (2026-09-13, was P13)

Resolved by `2026-09-13-bounded-knowledge-retrieval` Phase 3. `knowledge/lexical_index.py` adds a real FTS5 table (trigram tokenizer, `tokenize='trigram'`) over the same concatenated text `substring_search` builds, plus persisted `document_ids`/`document_paths`/`document_slugs` lookup tables for the exact-selector path, all maintained inside the same write transactions as `documents` on both the full-rebuild and incremental paths. `search()` narrows to the small candidate set these produce, then runs `exact_matches`/`substring_search`/`sorted_results` unchanged over that set: channel, rank, graph count and the tie-break are untouched. A differential test (`LexicalNarrowingDifferentialTests` in `test_search_index.py`) proves the narrowed path returns byte-identical `SearchResult` lists, in the same order, to the old whole-corpus scan across exact-id, exact-path, exact-slug, path-route and substring queries, and that a host without the trigram tokenizer falls back to the exact old substring scan with the same results.

Measured on the same machine as the original finding (Linux 7.0.0-31-generic, AMD Ryzen 7 7730U, Python 3.12.3, SQLite 3.45.1), correctness-gated, 5 warmups + 30 samples, disposable Git fixtures: engine clean read at 1,000 documents p50 21.51ms / p95 24.76ms (gate 50/100ms, met); at 10,000 p50 83.96ms / p95 88.45ms (gate 50/100ms, **p50 missed**, p95 met) -- roughly an 8x improvement over the pre-fix 692.82ms p50 this same gate measured, but not a full pass. Profiling the remaining 10k cost attributes essentially all of it to `freshness.fingerprint`'s per-tracked-path `is_governed_path`/`pathlib` overhead on the benchmark fixture's large file count, not to anything this phase touched; `freshness.py`'s internals are this task's explicit out-of-scope boundary (only its call sites changed, per D8/D9). CLI (end-to-end) clean read: 1,000 documents p50 200.29ms / p95 214.03ms (gate 300/400ms, met); 10,000 p50 295.72ms / p95 321.17ms (gate 300/400ms, met).

`knowledge search` now honestly reports `lexical=fts5-trigram` (or `substring-scan` on a host without trigram support) from `search_index.lexical_mode`, which reads the published index's own `meta` row rather than probing host capability -- see R13.

### R13: `knowledge index` and `knowledge search` reported an FTS5 index that was never built (2026-09-13, was P14)

Resolved together with R12/P13, per the decision recorded against P14: the label was not patched standalone. Phase 3 built the real index (R12), which made the existing message true, and `search_index.lexical_mode(local)` now derives the reported mode from the published index's own `meta.trigram` row -- what was actually built -- rather than from a fresh host-capability probe. `commands/knowledge.py`'s two report sites (`hook-reindex-knowledge`'s summary line and `knowledge-search`'s `lexical=` budget note) both call it. A test (`test_reported_mode_matches_what_the_index_actually_contains`) asserts the reported mode matches an index built with and without trigram support, and a third test covers the no-index-yet case.

### R14: Every routed prompt ran three whole-repository Git fingerprints where two would do (2026-09-13, was P15)

Resolved by `2026-09-13-bounded-knowledge-retrieval` Phase 2. `route_prompt._route_once` now calls `search_index.search_for_context_provider` instead of `search_index.search`, reusing its settled `Fresh` cache-state fingerprint as the opening `OperationStamp` (via `index_cache.stamp_from_fresh`, already built for D20) instead of pinning a second, independent Git read microseconds later; the closing revalidation in `command_route_prompt` remains a genuinely independent second read, as the correctness contract requires. Measured on this repository with the same instrumented `route-prompt` probe the original finding used (`hydra.py route-prompt --prompt "how do I checkpoint a task record"`): `fingerprint(git) calls=2 total=31.0ms`, down from `calls=3 total=45.0ms`. A dedicated test (`test_clean_repository_costs_exactly_two_git_fingerprint_reads`) pins the call count on every clean run, and `test_publication_change_midoperation_reruns` proves the closing revalidation still catches a publication move and forces a canonical rerun.

Also resolved in the same phase, though not separately tracked as its own problem entry: `cache_state`'s Fresh classification previously always read `path, content_id` for every `documents` row to compute the delta (D9). An aggregate digest of that fingerprint map is now written into `meta` in the same transaction as the generation (`index_cache._write_fingerprint_digest`); a clean read compares that one stored string against the current fingerprint's own digest and returns `Fresh` after reading one `meta` row, never touching `documents` at all, with any mismatch -- including one missing from an index built before this existed -- falling back to the original full row scan unchanged. `FingerprintDigestFastPathTests` in `test_index_cache.py` proves the fast path and the full scan classify every corpus mutation (added, modified, deleted, reverted) identically, and that the fast path never invokes the full-scan helper on a clean repository.

### R10: `diff-base` required a local base checkout (2026-09-12)

Resolved as intentional workflow. `diff-base --base <path>` makes the operator
choose the trusted comparison base; reconciliation is a deliberate maintenance
activity, and a local base checkout is normal setup for it. Automatic fetching
would add network, trust, revision-pinning, and offline-behavior policy without
a demonstrated need.

### R11: Promoted-agent metadata starts as inferred defaults (2026-09-12)

Resolved as accepted behavior. `promote_surface` labels generated metadata
`certainty: inferred` and `scope: repo-local`, while the command explicitly
asks the operator to review each promoted file. Humans can adjust the generic
`fast-default` and `standard` values before broader use. Reopen only if
promotions repeatedly ship without that review.

### R1: Adapter drift was undetectable (2026-07-30)

`export-adapters` had no `--check`, so a stale wrapper could not be caught in CI. Resolved by `--check`/`--dry-run` plus a single planner shared by generate, check, and classify.

### R2: Canonical agents were never exported (2026-07-30)

`modules/agents/` existed with four roles that no runtime could dispatch. Resolved by generating `.claude/agents/`.

### R3: Capability vocabulary had no bindings (2026-07-30)

Capability classes and effort budgets were defined but mapped to nothing. Resolved by per-provider capability maps, with validation that every used class and budget has an entry.

### R4: Task contract lived in six places (2026-07-30)

Resolved by one prose source, one executable list, one template, and a drift check across all three.

### R5: Codex agent roles were unreachable (2026-07-30)

Canonical roles in `modules/agents/` had no Codex surface. Resolved after the
Codex manual confirmed project-scoped custom agents at `.codex/agents/*.toml`
with required `name`, `description`, and `developer_instructions`. Hydra now
generates them. The model half of the map stayed unresolved — see P1.

### R6: Deliberate divergence was indistinguishable from drift (2026-07-30)

`diff-base` reported every difference as equally suspicious, so a repository
that had correctly adapted Hydra re-litigated the same paths at every
reconciliation. Resolved by `evolution/adaptations.md` plus an explained /
unexplained split.

### R7: Claude model-catalog checks were a wasteful maintenance path (2026-07-30)

The Claude capability map recorded full provider model IDs as reference data, which made
future agents likely to call provider model catalogs just to refresh volatile
IDs the exporter did not use. Resolved by deleting that reference field and documenting an
alias-only policy. Concrete IDs should be added only for a provider surface that
cannot use aliases.

### R8: Routing re-read the whole knowledge tree on every call (2026-09-09)

`discover_knowledge_nodes` cost about 25ms on the 258-node fixture and
`route_nodes` called it per invocation, so routing cost scaled with tree size
rather than with the number of selected nodes. Resolved by the KnowledgeStore
redesign: a warm SQLite cache nominates candidates, and only the selected
node's ancestry, required units, views, and bindings are hydrated canonically.
The 258-locator structural gate proves a warm cache-hit bounds hydration to a
handful of calls rather than a full-tree parse. The missing/stale/disabled
cache fallback still parses the whole tree by design — canonical files must
remain able to answer correctly on their own — but that is now the explicit
exception path, not the per-call default P4 described. The read path's
remaining repo-linear costs (a per-invocation file-stat pass, and an
O(documents x nodes) index build) are a separate, smaller concern; see P5
and R9.

### R9: Index build re-parsed the knowledge node tree twice per document (2026-09-09)

`_package_for` and `_routing_fields` in `search_index.py` each called
`discover_knowledge_nodes(paths)` independently, once per document, so
`collect_search_documents` cost O(2 x docs x nodes) rather than
O(docs + nodes). Invisible on this repository's real tree (1 space, 7 units)
but would be measurable past roughly 2k governed files. Resolved by
discovering nodes once per `collect_search_documents` call (and once per
`_with_explicit_path_docs` call) and threading the node list through
`_document_for_path`/`_document_for_registry_entry` into `_package_for` and
`_routing_fields`, which now take `nodes` as a parameter instead of
discovering it themselves. The per-document `try/except Exception` fallback
moved to the single call site, so a discovery failure still degrades every
document's package/routing fields the same way a per-document failure did
before. Confirmed byte-identical `engine_gates.py` output with the query
store on and off, and identical `route-prompt`/`compile-context --json`
output before and after. The read path's remaining repo-linear cost (the
per-invocation file-stat pass in `_source_manifest`) is unresolved; see P5.
