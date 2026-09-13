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
Updated: 2026-09-13

Concrete unresolved concerns for Hydra's own machinery. Each needs evidence, not
opinion. Resolve or close with a reason; do not let entries rot.

## Open

### P15: Every routed prompt runs three whole-repository Git fingerprints where one would do (2026-09-13)

- Evidence: instrumenting `freshness.fingerprint` and running `hydra.py route-prompt --prompt "how do I checkpoint a task record"` against this repository reports `fingerprint(git) calls=3 total=45.0ms` for a single prompt. The three come from `index_cache.cache_state` (via `search_index._cache_state`), `index_cache.capture_stamp` pinning the read, and `capture_stamp` again for the end-of-operation revalidation. The first two ask the same question microseconds apart and share nothing; only the third is a genuine second observation, and the correctness contract requires it.
- Impact: about 30ms on every prompt on this repository today, since `route-prompt` is wired to `UserPromptSubmit`. Unlike P13 this does not scale with corpus size in the same way, but it is currently the single largest component of a clean routed prompt here: 45ms of Git against roughly 6ms of index work at 403 documents. `guard_for` is already `lru_cache`d for exactly this reason; the fingerprint is not.
- Resolution: unresolved, being addressed by `2026-09-13-bounded-knowledge-retrieval` (split out of `2026-09-13-scalable-incremental-knowledge-index` on 2026-09-13, which owns only P12). The fix is to compute the pinning fingerprint once per operation and share it between the freshness classification and the stamp, leaving the closing revalidation as a genuinely independent second read. Note the ordering constraint: the stamp must be captured after any self-heal rebuild the search triggers, so the shared value cannot simply be hoisted to the top of the operation.
- Certainty: confirmed

### P14: `knowledge index` and `knowledge search` report an FTS5 index that is never built (2026-09-13)

- Evidence: the only `CREATE VIRTUAL TABLE ... USING fts5` statements in the engine are in `search_index.probe_sqlite_features` (`.hydra-framework/engine/src/hydra_engine/knowledge/search_index.py:66-77`), which builds them in a throwaway `:memory:` database purely to detect whether the host SQLite supports them, then discards it. `index_cache.create_index_tables` creates only `documents` and `meta`; `storage.write_sqlite_store` creates only `knowledge_objects`, `knowledge_relations` and their B-tree indices. No FTS5 table is ever created on real data. Verified by `grep -rn "VIRTUAL TABLE" --include=*.py .hydra-framework/engine/src`.
- Impact: `commands/knowledge.py:93-98` prints `Hydra knowledge index: <n> documents indexed at <path> (FTS5 trigram)` and `:140` prints `lexical=fts5-trigram`, from a flag whose actual meaning is "this host's SQLite is capable of FTS5". Actual retrieval is `search_index.substring_search`, a Python `in` test over a per-document concatenated string. The misreporting is why P13 went unnoticed: every operator check reported a trigram full-text index.
- Resolution: unresolved, being addressed by `2026-09-13-bounded-knowledge-retrieval`, and deliberately not being fixed as a standalone label change. Building the real FTS5 index (P13) makes the existing message true; patching the message first would be churn reverted by that work. If the P13 retrieval work is dropped or deferred, this becomes a required standalone fix, because a tool that reports a capability it does not have is worse than one that reports the fallback honestly.
- Certainty: confirmed

### P13: Every knowledge query materializes and scans the entire corpus in Python (2026-09-13)

- Evidence: on a `Fresh` cache hit, `search_index.search` calls `_load_documents`, whose only query is `SELECT * FROM documents ORDER BY rowid` (`knowledge/index_cache.py:219`), decoding every row including full body text; then `exact_matches` loops every document calling `slugify` on its title, package, routes and keywords; then `substring_search` loops every document again, concatenating id, aliases, path, kind, package, title, keywords, routes, use_when, headings and full body into one string, lowercasing it, and testing each query term with `in`. `cache_state` separately reads `path, content_id` for every row to compute the delta. The database holds no index used by any of this: it is read as a file format, never queried. Measured on Linux 7.0.0-31-generic / AMD Ryzen 7 7730U / Python 3.12.3 / SQLite 3.45.1, synthetic corpus, 3 warmups + 15 samples, median: at 320 documents `exact_matches` 1.48ms + `substring_search` 1.08ms; at 1,000 4.67ms + 3.29ms; at 10,000 46.41ms + 35.24ms, plus `_load_documents` 83.24ms and the `cache_state` row scan 20.83ms. Cost is linear in corpus size for every query, independent of how many documents match.
- Impact: this is the per-prompt path. `route-prompt` is wired to `UserPromptSubmit` (`.claude/settings.json`), so it runs on every prompt. At this repository's 403 documents the whole-corpus scan costs about 6ms and is invisible; at 10,000 it is roughly 187ms of SQLite and Python work per query, and it is the cause of section 8's four clean-read gate misses (engine clean p50 692.82ms against a 50ms gate; CLI clean p50 1373.75ms against 300ms), which P12 wrongly attributed to the publication layer. The superseded design's section 5 explicitly required the opposite: "bounded SQL retrieval with indexed lookups; never materialize the corpus in Python."
- Resolution: unresolved, being addressed by `2026-09-13-bounded-knowledge-retrieval` (split out of `2026-09-13-scalable-incremental-knowledge-index` on 2026-09-13). The intended fix is a real FTS5 (trigram where available) index maintained inside the same write transactions as `documents`, used to narrow candidates before ranking, with the existing rank, channel and tie-break semantics computed unchanged over the narrowed set rather than replaced by bm25, plus indexed lookups for the exact-selector path. Substring scan remains the fallback where the host SQLite lacks FTS5.
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
