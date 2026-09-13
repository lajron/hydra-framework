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
Updated: 2026-09-12

Concrete unresolved concerns for Hydra's own machinery. Each needs evidence, not
opinion. Resolve or close with a reason; do not let entries rot.

## Open

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
