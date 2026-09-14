# Phase 2 -- Gap Analysis

Part of [`repository-intelligence-review`](../repository-intelligence-review.md).
Deliverable B of the task record
`.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-14-repository-intelligence-and-wiki-projections.md`.

Measured 2026-09-14 on `main` at 7801b1d. Sections 1 through 7 of
[`01-current-state.md`](01-current-state.md) are treated as verified and are
cited by section number plus the `path:line` the reconstruction itself carries,
per the evidence rule. Where a classification depended on one of the six items
in that artifact's section 8, this phase established it directly rather than
classifying around it; section 1 below records what was established and how.

No README, wiki page, knowledge unit, or historical plan is used as evidence of
current behavior anywhere in this file.

Reproduce every measurement in this file with:

```bash
python3 .hydra-framework/scripts/hydra.py ref store rebuild
python3 .hydra-framework/scripts/hydra.py ref index
python3 .hydra-framework/scripts/hydra.py ref check
python3 .hydra-framework/scripts/hydra.py command-metadata --json
python3 .hydra-framework/scripts/hydra.py validate-wiki
python3 .hydra-framework/scripts/hydra.py validate
```

plus the isolated probe in section 1.2, which must be run on a scratch copy of
the repository and never on a working tree.

One spelling convention in this file: the probe object's id is written
`documentation/reference/source-map`, without its `hydra://` scheme prefix. This
file is itself scanned by `ref check` (`objects/references.py:121-136`), and the
probe object exists only on a scratch copy, so spelling the id in full would
make this artifact fail `validate`.

## 0. Corrections to Phase 1

Two findings contradict the Phase 1 artifact. Both are recorded in place in the
task record's Confirmed Decisions.

| Phase 1 claim | Where | Measured | Effect |
| --- | --- | --- | --- |
| "All 23 typed relations authored anywhere in `.hydra-framework/` are `relates-to`" | §3.3 | **22**, under the command §3.3 prints. The 23rd occurrence is a template string inside `knowledge/migration_templates.py:91`, which is generator source, not an authored relation | None on the conclusion. `governs`, `implements`, `tests`, `operates` and `supersedes` are still authored zero times, and the flattening point is unchanged |
| "The blast radius of registering `project-wiki/` pages as sidecar objects on `ref check`" is not established | §8 item 3 | Established here, §1.2. Registering a page adds it to the registry digest check at `objects/registry.py:191-193`, which is validator 11 and therefore `validate`, `doctor` and CI. Every content edit to a registered page fails `ref check` until `ref index` is rerun | Phase 3 question 1 now has a priced answer rather than an open one |

The rest of the Phase 1 artifact reproduces. Specifically re-run and confirmed
here: 5 of 70 registered commands absent from `command-surface.md`, the same
five; 41 distinct non-wiki canonical targets in `source-map.md`, all resolving;
`validate-wiki` passing; `validate` passing; 40 Markdown files under
`project-wiki/`, none carrying frontmatter.

## 1. What this phase established that Phase 1 could not

### 1.1 Why a probe was needed

Three classifications below turn on whether an `external`-tier object can exist
at all: a wiki page as a Hydra object (D2), a `Documentation` family (D1), and
where a wiki manifest lives (Q4). Phase 1 §8 item 3 recorded that no such object
exists today and no test constructs one, so the behavior of `explain-path`,
`move-object`, `reclaim` and `measure-context` on one was unknown. That is not a
question the source can settle by reading, because the relevant code paths have
never executed against that input.

### 1.2 The probe, and what it showed

Run on a copy of the repository at `main` with `.git` and
`.hydra-framework.local/` excluded. Two edits, both additive:

1. One entry appended to `.hydra-framework/repo/object-sidecars.yaml`
   registering `project-wiki/hydra-framework/reference/source-map.md` with
   `hydra_id: documentation/reference/source-map`, `kind: documentation`,
   `scope: repo-local`, and `provenance.sources` naming
   `.hydra-framework/engine/src/hydra_engine/cli/command_metadata.py`.
2. One `ObjectFamily(name="Documentation", id_prefixes=("documentation",),
   kinds=("documentation",))` entry appended to `OBJECT_FAMILIES`
   (`identity/object_families.py:132-142` is the shape it copies), plus
   `"Documentation"` appended to `SEARCH_FAMILIES`
   (`knowledge/context_providers.py:28`).

Results:

| Command | Result |
| --- | --- |
| `ref index` | `Indexed 58 objects` |
| `ref check` | `ok (58 objects)` |
| `validate` | `ok`, same five advisory notes as the unmodified tree |
| `ref store rebuild` | `rebuilt from 58 object(s)`; `objects: 58`, `provenance: 51`, no schema change |
| `explain-path project-wiki/.../source-map.md` | `Tier: external`, `Object: documentation/reference/source-map (Documentation/documentation)` |
| `explain-path .../cli/command_metadata.py` | `Source: sqlite`, `Cited as provenance by: documentation/reference/source-map` and `hydra://knowledge-unit/hydra-framework/build-status` |

Four further results, each of which decides a classification:

- **Before the family was registered**, `ref check` failed with
  `has unregistered hydra_id family prefix 'documentation'` and
  `has unregistered kind 'documentation'`, naming
  `hydra_engine.identity.object_families` as the point of edit. The family
  registry is enforceable exactly as `identity/object_families.py:40-41` claims.
- **With an existing prefix instead** (`kind: knowledge-slice`), the same page
  registered with no engine change at all: `ref index` -> 58, `ref check` -> ok,
  `validate` -> ok. So a wiki page can become an object today, without touching
  the engine, using `objects/discovery.py:48`'s existing `project-wiki/` sidecar
  root.
- **Appending one line of prose to the registered page** made `ref check` fail:
  `.hydra-framework/cognition/graph/registry.yaml has stale digest for ...;
  rerun 'hydra.py ref index'` (`objects/registry.py:191-193`). Nothing reindexes
  automatically: no path in `commands/hooks.py` and no step in
  `.github/workflows/hydra.yml` calls `ref index`.
- **Adding an unresolvable `hydra://` reference to the registered page** and then
  rerunning `ref index` left `ref check` at `ok`. Phase 1 §2.4 holds: a
  sidecar-registered file is not itself scanned for references
  (`objects/discovery.py:117-126` versus `objects/references.py:121-136`), so
  registering wiki pages does not put wiki prose under reference resolution.

The probe's `selftest` run did not complete and was killed; the copy has no
`.git`, and several suites depend on it. The claim here is therefore about the
six commands above, not about the full suite. Phase 3 must run `selftest` in a
real clone before relying on this.

**Net:** the cost of making a wiki page an object is one `ref index` per edit to
that page, enforced by CI. It is not reference resolution over prose, and it is
not a store change. That is a much smaller blast radius than Phase 3 question 1
assumed, and a larger recurring cost than "add a sidecar entry" suggests,
because it lands on the corpus humans and agents edit most often.

## 2. Part 1: classification of every proposal component

Vocabulary is the proposal's own, from section 37:
`existing`, `partially existing`, `missing but valuable`, `missing and
premature`, `conflicts with current architecture`.

Per the phase's rule, a `missing and premature` row states what would have to be
true for it to stop being premature, and a `conflicts with current architecture`
row names the contract it conflicts with by `path:line`. Both appear in the
Evidence column, prefixed `Premature until:` or `Conflicts with:`.

Rows are grouped by proposal part. Section numbers are the proposal's.

### 2.1 Architecture and vocabulary (part 1, plus section 27)

| # | Component | Classification | Evidence that settled it |
| --- | --- | --- | --- |
| A1 | Four-layer model: repository reality, repository intelligence, knowledge spaces, projections (§3) | existing | All four layers are built under other names. Layer 2 is `cognition/graph/registry.yaml` plus the eight-table store in `objects/store_schema.py:16-41`; layer 3 is `repo/knowledge/spaces.yaml` with `knowledge/nodes.py:15-16`'s two schemas; layer 4 is `surfaces/README.md:3-6`. Phase 1 §2, §3, §4, §6 |
| A2 | `Projection` as a Hydra concept and noun (§4, §27) | conflicts with current architecture | Conflicts with: `.hydra-framework/surfaces/README.md:3-6`, which already defines a surface as an "audience-facing or interface-specific view of knowledge" with a recorded contract stating whether it is canonical, derived, synchronized, private, generated, or hand-maintained. That is §27 with a different noun. The repository argues against exactly this duplication in `identity/object_families.py:45-51`, which chose `engine-module` over `runtime-module` rather than promote a second word. D4 confirmed |
| A3 | Projection operations: compile, export, render, query, analyze, audit (§27) | partially existing | `compile-context`, `export-adapters`, `explain-path` and `ref impact` already are four of the six. `render` exists only for `.dot` diagrams (`hook-post-edit --render`) and has never run on real content: no `.dot` file exists in the repository. `audit` does not exist |
| A4 | Per-concept URI schemes `wiki://`, `space://`, `capability://`, `source://`, `test://`, `rule://`, `claim://`, `documentation://` (§5, §6, §9, §13, §16, §29) | conflicts with current architecture | Conflicts with: `identity/hydra_ids.py:10-11`, where `HYDRA_ID_RE` and `HYDRA_REF_RE` recognize `hydra://` and nothing else, and `hydra_id_prefix` (`:31-39`) returns `""` for any other scheme. A `wiki://` or `claim://` id would be invisible to `ref check`, `ref index`, `explain-path` and the store. The existing scheme already carries the same distinctions in its first segment (`hydra://knowledge-space/...`, `hydra://capability/skill/wiki-authoring`) |
| A5 | Repository reality outranks documentation; the section 30 evidence order (§3.1, §30, §35 principles 1 and 2) | existing | This is D6, and Phase 1 §7.4 strengthened it: four engine docstrings disagree with their own code today. The rule is already how this review operates |

### 2.2 Wikis (part 2, sections 5 to 8)

| # | Component | Classification | Evidence that settled it |
| --- | --- | --- | --- |
| B1 | `project-wiki/` is a host of several wikis, not one wiki (§5) | existing | `surfaces/README.md:15-19` already names `project-wiki/home.md`, `project-wiki/hydra-framework/` and `project-wiki/<project-name>/` as three distinct surfaces with distinct audiences and ownership, and `wiki scaffold <project>` (`commands/wiki.py`) creates another. D2 row 6 confirmed |
| B2 | A wiki stays ordinary Markdown, readable without Hydra (§6) | existing | Measured: 0 of 40 `project-wiki/*.md` files carry frontmatter. `wiki/links.py:108-112` validates links only. Nothing in the engine is required to read a page |
| B3 | A named-wiki manifest carrying id, title, owner, `managed`, and `root` (§7, §8) | missing but valuable | Nothing machine-readable exists at any surface boundary: `.hydra-framework/surfaces/` holds one `README.md`, with no frontmatter and no `hydra_id`, so it is scanned by the Markdown handler and discarded at `objects/envelopes.py:112-114` (Phase 1 §6.1). This **overturns D2 row 7**, which recorded the manifest question as "confirmed current behavior". The directory is the right home; the file does not exist |
| B4 | `managed: true` versus repository-owned wikis (§7, §8) | missing but valuable | Same evidence as B3. The distinction is real and already implicit: `wiki scaffold` produces a repository-owned wiki, and `project-wiki/hydra-framework/` is the Hydra-owned one. Nothing records which is which |
| B5 | `sources:` on a wiki, naming the spaces that feed it (§8) | missing and premature | Premature until: more than one knowledge space exists. `repo/knowledge/spaces.yaml` declares one (`hydra-framework`), with one node and no child nodes (Phase 1 §4.1), so a per-wiki source list would have exactly one legal value |
| B6 | `wiki list` (§8) | missing and premature | Premature until: B3 exists and at least two wikis are declared. There is one wiki directory under `project-wiki/` today plus `home.md`; a list command would print one row derived from a manifest that does not exist |
| B7 | Wiki boundary enforcement; project knowledge must not leak into Hydra's wiki (§7, §34.6) | partially existing | The mechanism exists and is scoped away from the wiki. Validator 8, `tier-boundaries` (`checks/repo_findings.py:58-59` -> `work/tiers.py:67`), fails `validate` when a shared Markdown file cites a concrete private path, but its scan iterates `iter_markdown_files(paths.hydra)` (`work/tiers.py:110`), which is `.hydra-framework/`-rooted. See Q15 for what widening it would find today |

### 2.3 Knowledge spaces (part 2, sections 9 to 12)

| # | Component | Classification | Evidence that settled it |
| --- | --- | --- | --- |
| C1 | Knowledge spaces are not wikis (§9) | existing | Two separate models already: `knowledge-space` and `knowledge-node` are object kinds in the Knowledge family (`identity/object_families.py:91-101`) with their own schemas (`knowledge/nodes.py:15-16`); the wiki has no object model at all. The proposal's distinction is the shipped one |
| C2 | One space feeding several consumers (§9) | existing | `knowledge/context_providers.py:274-277` runs six family providers over the same node tree for `compile-context`; `route-prompt` reads the same nodes (`knowledge/routing.py:25-28`); `knowledge-search` and `delegation-brief` read the same corpus. One space, four consumers, today |
| C3 | Spaces compose rather than inherit (§10) | conflicts with current architecture | Conflicts with: `knowledge/nodes.py:239-265`, `resolve_inheritance`, which walks a single `parent_id` chain and merges `owners`, `defaults`, `avoid_by_default` and `routes` down it, recording per key which ancestor supplied each value; depth is capped at `DEFAULT_DEPTH = 3` / `MAX_DEPTH = 4` (`knowledge/contracts.py:3-4`). The shipped model is exactly the classical inheritance §10 says not to build. Replacing it is a Knowledge v3 schema change, not an addition |
| C4 | A space as a semantic lens over objects, with `scope.paths` globs (§3.3, §10) | missing and premature | Premature until: a second space exists and something consumes a path-to-space assignment. Today selection is keyword-based (`knowledge/routing.py:25-28`, `MIN_ROUTE_MATCH_SCORE = 2`, `MAX_ROUTED_NODES = 2`), and there is nothing to disambiguate |
| C5 | One object participating in several spaces (§10) | missing and premature | Premature until: C4. With one space, every object is in it or in none |
| C6 | Portable external spaces with versions, `dotnet-enterprise@2` (§11) | missing and premature | Premature until: a second repository is actually consuming Hydra knowledge, which is the demonstrated need the task record's Goal says is absent. Deliberately out of scope there; recorded so Phase 3 checks its boundaries do not block it |
| C7 | Epistemic categories, the nine-value table (§12) | partially existing | `certainty:` is authored today with five distinct values, measured across `.hydra-framework/*.md`: `confirmed` (19 exact occurrences across two quoting styles, plus one carrying a trailing qualifier), `inferred` (5), `conflicting` (2), `reviewed` (1), `reviewed-docs` (2). Only four are referenced by code (`unresolved`, `conflicting`, `confirmed` at `knowledge/package_checks.py:99,214,229` and `flat_files.py:141`; `rejected`/`superseded` as `TERMINAL_CERTAINTIES` at `flat_files.py:19`). There is no closed vocabulary. `unit_kind` adds a second, closed axis: `answer | rule | map | divergence | status` (`knowledge/units.py:27`). The nine values are a superset of an open three-to-five value field already in use |
| C8 | Authority scopes: organization, repository, domain, module, feature, task (§12) | conflicts with current architecture | Conflicts with: `identity/schema_versions.py:35`, which makes `scope` a mandatory envelope field, and `knowledge/contracts.py:5`, `LEGAL_SCOPES = ("base-seed", "common-seed", "repo-local")`. `scope` already means seed distribution, not authority. Measured authored values: `base-seed` (23), `common-seed` (20). Reusing the word on the same field collides; reusing it on a different field gives the repository two meanings for one word, which is A2's objection again |
| C9 | Deterministic conflict resolution by category, authority, scope specificity, recency, evidence quality, and explicit override (§12) | missing and premature | Premature until: C3 or C8 is settled, and at least two knowledge sources actually disagree. `knowledge/package_checks.py:214-217` already handles the one disagreement shape that exists: `unit_kind: divergence` requires `certainty: conflicting` and the phrase "effect on agents", which records a conflict rather than resolving it. That is a deliberate design choice a resolution engine would reverse |

### 2.4 Object and relation model (part 3)

| # | Component | Classification | Evidence that settled it |
| --- | --- | --- | --- |
| D1 | Documentation as an object family (§13) | missing but valuable | Measured cost, §1.2: one `ObjectFamily` tuple entry plus one string in `SEARCH_FAMILIES`. No test asserts a family count (`unit/identity/test_object_families.py` asserts resolution parity and the no-token-claimed-twice invariant only), and no contract golden names a family. `ref index`, `ref check`, `validate` and `ref store rebuild` all pass with it added. D2 row 12 confirmed and priced |
| D2 | A wiki page as an addressable Hydra object (§13, §18) | missing but valuable | Works today with zero engine change via `objects/discovery.py:48`'s `project-wiki/` sidecar root (§1.2). The recurring cost is one `ref index` per page edit, enforced through `objects/registry.py:191-193` and validator 11. Phase 1 §8 item 3 closed |
| D3 | A documentation object decoupled from a physical file, one concept to many pages (§13) | missing and premature | Premature until: a page-level identity exists and a real case appears where two pages document one concept. The object model is file-keyed: `objects` carries one `path` and one `digest` per object (`objects/store_schema.py:16-41`) and `objects/envelopes.py:156` digests the object's own file. A concept spanning files has no digest and no `path` |
| D4 | `doc_kind`, `audiences`, `outputs` envelope fields (§13) | missing but valuable | Free to author and inert until read: `objects/envelopes.py:103-166` builds a fixed record and nothing validates unknown keys, so extra fields are parsed and dropped. Valuable only once a consumer exists; `surfaces/README.md:44-51`'s four-row audiences table is the vocabulary they would carry, and nothing reads that table either (Phase 1 §6.2) |
| D5 | The 33-entry candidate family list: source symbol, command, schema, provider, reducer, validator, test, projection, and the rest (§14) | missing and premature | Premature until: each one has a query that needs it. The proposal says so itself ("must not automatically become the first implementation"). Measured counter-pressure: the Python handler roots at `engine/src` and turned 3 of roughly 200 engine modules into objects (`objects/object_handlers.py:115`, Phase 1 §2.2), and the Telemetry family has been registered with a context provider and zero members since it was added. Families are cheap; members are not |
| D6 | The 17-relation controlled vocabulary (§15) | conflicts with current architecture | Conflicts with: `knowledge/contracts.py:6`, `RELATION_TYPES` with exactly six values, enforced on Knowledge v3 nodes at `knowledge/nodes.py:341` and on units at `knowledge/checks.py:72-74`, with `knowledge/checks.py:69-71` additionally requiring v3 unit relations to be typed mappings. Adding `documents`, `appears-in`, `evidence-for`, `enforced-by`, `generated-from`, `projects-to`, `draws-from`, `overrides` and the rest means replacing a closed, validated set, and every one of them would be discarded at `objects/envelopes.py:129` before reaching any query |
| D7 | Typed relations surviving into the registry and the store (§15, D2 row 9) | missing and premature | Premature until: something other than a human authors a relation. Measured: 22 typed relations authored in `.hydra-framework/*.md` and `*.yaml`, all `relates-to`; `governs`, `implements`, `tests`, `operates`, `supersedes` are authored zero times. Both authoring surfaces are hand-edited frontmatter (Knowledge v3 nodes and units, `knowledge/checks.py:69-71`) or hand-edited capability `metadata.yaml` bare strings. A type a human types and no tool derives is a type no tool can disagree with. See Q2 |
| D8 | Claim-level documentation tracking, `claim://` (§16) | missing and premature | Premature until: page-level staleness is in use and measured to be too coarse, and a sub-file identity scheme exists. Same file-keyed limit as D3: `objects/envelopes.py:156` digests whole files. The proposal self-defers this to phase 6; that self-deferral is correct |
| D9 | Documentation declares how it is maintained: authored, generated, hybrid (§17) | partially existing | The model is shipped for a different corpus. `providers/reclaim.py:98-146` classifies every file under six provider roots (`:33-40`) as `generated`, `drifted`, `stale` or `orphaned` by reading a per-file `hydra-framework.adapter.v2` sidecar carrying `canonical_source` and `generated_file`, comparing against `planned_adapter_files`. CI enforces it (`.github/workflows/hydra.yml:56`, `reclaim --fail-on-findings`). Nothing equivalent exists for documentation |
| D10 | Generated documentation owns mechanical facts (§17.2, §35 principle 10) | partially existing | Already true for provider surfaces: every `.claude/skills/*/SKILL.md` and `.codex/agents/*.toml` is generated from a canonical capability by `export-adapters`, with a sidecar naming its `canonical_source`. Not true for any wiki page: all 40 are hand-authored |
| D11 | Bounded generated Markdown regions (§17.3) | missing but valuable | The pattern exists, applied to `.gitignore`: `IGNORE_BLOCK_HEADER` / `IGNORE_BLOCK_FOOTER` (`providers/git_ownership.py:22-23`) and `ensure_generated_adapter_ignore_block` (`:47-72`), which is idempotent, rewrites in place between markers, never appends a second block, and returns `already-present` / `updated`. Porting it to Markdown is a small, tested-shape change |
| D12 | Page-to-source dependency with digests and a last-verified record (§18) | partially existing | The exact contract exists on knowledge units: `provenance.sources`, `provenance.source_digests`, `checked_on` (`knowledge/units.py:30-48`), compared by `knowledge/freshness.py:287-314`, written by `commands/knowledge_fingerprint.py:96-127`. It has never been applied to a wiki page: no `project-wiki/` file is a unit and no unit cites one as a source (Phase 1 §4.6). D2 row 3 confirmed. One correction to §18's shape: its `last_verified.commit` field would be recorded and never read, because `knowledge/freshness.py:305-308` returns before the commit rule whenever a digest is present |
| D13 | Answer "which documentation depends on this changed source" (§18) | missing but valuable | This is the proposal's real ask and the one thing nothing answers today for a wiki page. Measured to be one sidecar entry away: after the §1.2 probe, `explain-path .../cli/command_metadata.py` returned `Cited as provenance by: documentation/reference/source-map`, store-backed, beside the knowledge unit. The staleness half still needs D12 |
| D14 | Answer "what implementation and evidence support this page" (§18) | existing | `explain-path <page>` already returns tier, object, provenance sources, reverse citations by relation, citers by provenance source, and directory owner, degrading to a scan and never requiring the store (`commands/explain_path.py:18-20`). It answers this for any path, object or not |
| D15 | Business rules as first-class objects, `rule://` (§29) | missing and premature | Premature until: this repository or an adopting one has business rules with stable identities worth maintaining. Deliberately out of scope by the task record's Goal; recorded so Phase 3 checks its boundaries do not block it. Also carries A4's scheme conflict |

### 2.5 Commands and CI (part 4)

| # | Component | Classification | Evidence that settled it |
| --- | --- | --- | --- |
| E1 | A `graph` command family with `--format mermaid|json|dot` (§19) | missing but valuable | No `graph`, `docs` or `projection` namespace exists in the CLI (measured from `hydra.py --help`). The data exists: `cognition/graph/registry.yaml` carries every object with `aliases`, `relations` and `provenance_sources`, is rewritten by `ref index`, and is freshness-checked by validator 11. Valuable narrowly, for E3; see Q14 for which views earn their place |
| E2 | The eight graph views in §19's table | missing and premature | Premature until: each has a caller. Seven of the eight restate `registry.yaml` in another shape. The exception is the change-impact graph, E3 |
| E3 | Change-impact graph: changed source to downstream consequences (§19) | partially existing | Half of it ships. `ref rdeps` is one hop inbound (`objects/store_queries.py:95-102`); `ref impact` is transitive **outbound**, depth 5, cycle-guarded (`:115-136`). There is no transitive reverse walk, so "what breaks if I change X" is unanswerable (Phase 1 §3.2). This **overturns D2 row 2**, which recorded "reverse-dependency and impact queries" as confirmed current behavior: the reverse query is one hop and the transitive query runs the wrong direction |
| E4 | Generated diagrams embedded in Markdown without rewriting authored prose (§19) | missing but valuable | Same mechanism as D11. Note the input is also missing: no `.dot` file exists in the repository, so `hook-post-edit --render` has never produced a diagram from real content, and every Mermaid diagram in the wiki (14 pages carry one) and in the architecture slice is hand-authored |
| E5 | `docs audit` (§20) | missing but valuable | The proposal's central command. Nothing answers its questions today for a wiki page; `validate-wiki` checks link resolution only (`wiki/links.py:108-112`) and `knowledge stale` cannot see a non-unit (`knowledge/units.py:74`). Its scope should be cut to what D12 and D13 make answerable; see Q14 and Q11 |
| E6 | Four severity levels: ERROR, WARNING, REVIEW REQUIRED, INFORMATIONAL (§20) | conflicts with current architecture | Conflicts with: `finding.py:38-42`, where `Finding` carries `path`, `code`, `detail` and no severity, and `knowledge/package_checks.py:148-152`, which states in the engine's own words that every `Finding` makes `validate` exit nonzero and "there is no separate warning tier". The repository's second tier is advisory notes printed **after** the verdict (`cli/dispatch.py:133-145`), which is deliberate so a note never reads as a failure. A four-level model inside one command either bypasses `Finding` or changes it for all 19 validators |
| E7 | The 13 audit categories in §20 | partially existing | Four already ship, applied to objects rather than pages: dead source path (`objects/references.py:95-102` existence-checks every `provenance.sources` entry), broken relation (`ref check`), unknown object identity (`unregistered_family_tokens`, `identity/object_families.py:166`), missing owner (`identity/schema_versions.py:35` makes `owners` mandatory). Nine do not: stale source dependency for a page, stale claim, missing coverage, orphan page, generated-reference drift, generated-diagram drift, wiki boundary violation, missing evidence, unverified high-contract page |
| E8 | Documentation coverage policy per capability, with a coverage report (§21) | missing and premature | Premature until: D1 and D2 exist and pages declare what they document. Coverage today would be computed against nothing: no page names a capability, and the only page-to-capability data in the repository is one `provenance.sources` entry pointing the other way (`capabilities/skills/wiki-authoring/metadata.yaml:23`, Phase 1 §6.4) |
| E9 | `docs reconcile`, a bounded agent reconciliation package (§22) | partially existing | The shape ships as `delegation-brief`, which turns `knowledge-search` results into a subagent read-first brief with stop rules (`commands/knowledge.py`). Its restrictions list is what §22's "Restrictions" block asks for. What is missing is the documentation-specific input: changed sources, affected objects, generated-reference differences |
| E10 | A pull-request documentation-impact report (§23) | missing and premature | Premature until: E3's reverse walk and D12's page-level staleness exist, because the report is a rendering of their output. Nothing in `.github/workflows/hydra.yml` writes to a PR today; all eight steps run commands and pass or fail |
| E11 | Marking an impact irrelevant with an explicit reason (§23, §34.3) | existing | Two mechanisms already do this. `knowledge fingerprint --unit <id>` re-verifies with no prose change (`commands/knowledge_fingerprint.py:96`). `bindings verify --accept` records a reviewed fingerprint only when every assertion still holds and the sole objection is that the fingerprint is unreviewed, which is tracked by `awaiting_review` set by the verifier rather than inferred from message text (`knowledge/bindings.py:193-202`, `commands/knowledge_bindings.py:64-68`) |
| E12 | Three-stage CI enforcement: warning, selective blocking, policy (§24) | partially existing | Stage 1 is how one CI step already runs: `measure-context` is advisory with no `--fail-over`, by an in-file comment saying the team has picked no budget (`.github/workflows/hydra.yml:67`, Phase 1 §5.5). Stage 2's category list is not expressible without E6 or a separate exit policy. Stage 3 is E13 |
| E13 | Per-wiki, per-document-kind policy YAML (§24 stage 3) | missing and premature | Premature until: B3 exists, more than one wiki exists, and a document-kind vocabulary exists (D4). With one wiki and no doc kinds, the policy file has one row |
| E14 | Generated CLI reference from command metadata (§17.2, §32 phase 2, §33 item 5) | partially existing | This **corrects D2 row 11**, which read "the generator does not exist; its input does". The input is incomplete in two ways. `CommandMetadata` carries `id`, `aliases`, `arguments` and an optional safety overlay and nothing else (`cli/command_metadata.py:314-322`): no command description, no per-argument help, no required/optional distinction. And the parser is built from `COMMAND_MODULES` alone (`cli/command_metadata.py:340`), so `validate`, `doctor`, `command-metadata` and `selftest` are absent: the CLI dispatches 74 commands and metadata reports 70 (Phase 1 §1.1). A generated page would also lose what the current one is for: `command-surface.md` is a lookup-by-need table, not a command dump |

### 2.6 Website (part 5)

Reviewed only for whether it constrains the data contract, per the task record's
Goal. Every row is deferred as a build; F7 is the one that constrains.

| # | Component | Classification | Evidence that settled it |
| --- | --- | --- | --- |
| F1 | Static documentation website (§25.1) | missing and premature | Premature until: F7 exists, and until D12 and D13 give the site something to show that reading the Markdown does not. Its listed features (verification status, authored/generated badges, related capabilities) are all renderings of data that does not exist yet |
| F2 | Interactive graph explorer (§25.2) | missing and premature | Premature until: F1, and until E3's reverse walk exists, since "Why is this page affected?" is that query |
| F3 | Documentation health dashboard (§25.3) | missing and premature | Premature until: E5 produces the numbers it would display |
| F4 | Commit and pull-request views (§25.4) | missing and premature | Premature until: E10 |
| F5 | Optional server-side backend (§25.5) | missing and premature | Premature until: cross-repository or organization-wide use exists, which is C6's condition. The proposal already says it should not be required initially |
| F6 | Website CI/CD pipeline (§26) | missing and premature | Premature until: F1 |
| F7 | A stable Hydra-generated JSON contract the site consumes (§25, §36 q21) | missing but valuable | The one website component that constrains the data contract now. Measured: of the 70 registered commands, 19 accept a `--json` argument and **none** is a `ref` subcommand. `cognition/graph/registry.yaml` is the graph snapshot the site would need and is YAML. See Q21 |

### 2.7 Delivery, risks and principles (part 6)

| # | Component | Classification | Evidence that settled it |
| --- | --- | --- | --- |
| G1 | One-time reconciliation pass (§30) | partially existing | Its inventory half is done and is [`01-current-state.md`](01-current-state.md), which follows §30's own evidence order. Its correction half is deliberately not run, per D5. The §30 topic list is answered there except for reducers, which Phase 1 covers as `commands/agent_hooks.py`'s output reduction |
| G2 | Recommended wiki information architecture (§31) | partially existing | Six of the eight proposed top sections already have a counterpart: Start Here / `start-here`, Concepts / `concepts`, Using Hydra / `working-with-hydra`, Operations / `operations`, Architecture / `architecture`, Reference / `reference`. `extending-hydra` covers the proposed Integration plus part of Maintainers; `evolution` has no proposed counterpart. The genuinely new asks are a Maintainers section and a Projection System page, which A2 would rename |
| G3 | The nine-phase delivery sequence (§32) | partially existing | Phase 0's inventory half is complete (G1). Phases 1 through 8 map to rows above and inherit their classifications; phase 5 (website) and phase 6 (claims) are `missing and premature` in every constituent row |
| G4 | The nine-item MVP (§33) | partially existing | Item by item: 1 and 2 are B3/B4 (missing but valuable); 3 is D12 (partially existing); 4 is E5 (missing but valuable); 5 is E14 (partially existing, input incomplete); 6 is E1/E3 (missing but valuable, one view); 7 is E12 (partially existing); 8 is F1 (missing and premature); 9 is A5 (existing). Two of the nine should leave the MVP: item 8 by F1's condition, and item 5 until `command-metadata` carries descriptions |
| G5 | The ten risks (§34) | not components | Recorded as checked rather than classified. Two are measurably overstated: §34.6 (space and wiki leakage) would produce zero findings today, see Q15; §34.3 (false-positive staleness) asserts a rate nothing has measured, because no page-level staleness has ever run. Two are understated: §34.8 (the graph itself becoming stale) is the `ref index` cost §1.2 measured, and §34.2 (annotation burden) is D7's finding that every relation type is hand-typed |
| G6 | The sixteen design principles (§35) | partially existing | Nine are already enforced mechanically: 1 and 2 (A5), 3 (B2), 6 (B1), 10 and 11 (D9/D10, for provider surfaces), 13 (E6's two-tier model), 14 (E11), 15 (the `hydra-framework.adapter.v2` sidecar records `canonical_source` per generated file). Four are policy this review adopts (4, 5, 12, 16). Three restate components classified above: 7 (C1, existing), 8 (C3, conflicts), 9 (C5, premature) |

### 2.8 D2's fourteen rows, re-verified

| D2 row | Now | Change |
| --- | --- | --- |
| Repository graph, objects, relations, provenance | A1, existing | Holds. Count corrected to 57 objects and six families by Phase 1 |
| Reverse-dependency and impact queries | E3, partially existing | **Overturned.** `ref impact` walks outbound, not reverse; the reverse query is one hop only |
| Page-to-source dependency with digests | D12, partially existing | Holds. `last_verified.commit` in §18 flagged as write-only |
| Staleness detection against Git | D12 / Q10, partially existing | Refined. Corrected by Phase 1 §4.5: the Git date rule is never exercised |
| Epistemic categories | C7, partially existing | Holds. Value set measured: five authored, no closed vocabulary |
| Wiki as host with named sub-wikis | B1, existing | Holds |
| Where wiki manifests live | B3, missing but valuable | **Overturned.** `surfaces/` is the right home and holds nothing machine-readable |
| Projection duplicates Surface | A2, conflicts | Holds. Mechanism correction in Q3: `reclaim` is the closest working projection model |
| Typed relation vocabulary | D6 conflicts, D7 premature | Refined twice. Corrected by Phase 1 (flattened at `envelopes.py:129`, not in the store) and again here (22 authored, all `relates-to`) |
| Page-to-source dependency registry (q24) | Q24 | Refined. Corrected by Phase 1 §5.1; quantified here as 33 files of 41 targets |
| Generated CLI reference | E14, partially existing | **Overturned.** "Its input does [exist]" is only partly true: no descriptions, 4 commands missing |
| Documentation as an object family | D1, missing but valuable | Holds, and priced: two lines |
| Claim-level tracking | D8, missing and premature | Holds |
| Website | F1 to F6, missing and premature | Holds |

Three rows overturned, three refined, eight hold. Sixteen components the
proposal contains that D2 never listed are classified above: A3, A4, A5, B2, B4,
B5, B7, C2, C4, C9, D3, D4, D14, E4, E9, E11.

## 3. Part 2: the 25 open questions in section 36

### Q1. Can Hydra's existing operational query store represent documentation, wiki, claim, and projection objects cleanly?

Documentation and wiki objects: **yes, with no store change**, measured. The
`objects` table is keyed on `hydra_id` and carries `family`, `kind`, `path`,
`digest`, `tier` and `scope` as opaque strings (`objects/store_schema.py:16-41`),
and the whole table is rebuilt wholesale from the validated export, keyed to the
export digest (Phase 1 §3.1). The §1.2 probe rebuilt the store with a
`project-wiki/` page registered under a new `Documentation` family: `objects:
58`, `provenance: 51`, schema unchanged, `export digest: agrees with the export`.

Claim objects: **no**. The store's unit of identity is a file. One `path` and one
`digest` per object row, and `objects/envelopes.py:156` computes that digest over
the object's own whole file. A claim inside a page has no path, no digest, and
nothing to key on. See D3 and D8.

Projection objects: the question does not arise. See Q3.

Two limits worth carrying into Phase 3, both from Phase 1 §3.1 and §3.2:

- The `refs` table is populated on every rebuild and indexed
  (`store_schema.py:23`, `store_build.py:108,186`) and **no query function reads
  it**. 104 rows of citation-site data with no consumer. `explain-path` answers a
  narrower question through `provenance` instead.
- `relations(src_id, dst_id)` carries no type, and cannot, because the type is
  gone by `objects/envelopes.py:129`. See Q2.

### Q2. Should documentation use the existing relation model unchanged?

**Yes, unchanged**, and the typed-edge question must not be answered first.

The proposal frames this as a schema question. It is not. The relation type is
discarded at `objects/envelopes.py:125-130`, which reduces a `{type, target}`
mapping to its `target` string before the registry export is written, before the
store exists. "The existing relation model", as it reaches any query, is an
untyped edge list. Using it unchanged costs nothing.

Per the phase's rule, before any recommendation for typed edges:

**What would author a non-`relates-to` edge?** Nothing does. Measured: 22 typed
relations authored across `.hydra-framework/*.md` and `*.yaml`, every one
`relates-to`. `governs`, `implements`, `tests`, `operates` and `supersedes` are
authored zero times, in source and in tests alike. The only other occurrence in
the tree is a template string in `knowledge/migration_templates.py:91`, which
emits `relates-to` as well.

**Who maintains it?** A human, in every case. The two authoring surfaces are
Knowledge v3 node and unit frontmatter, where `knowledge/checks.py:69-71`
requires typed mappings, and capability `metadata.yaml`, which uses bare
`hydra://` strings (`identity/object_families.py:11-12` is one of the three
engine-module docstring envelopes doing the same). No generator produces a
relation. So a type is whatever the page author typed, and no tool can ever
contradict them: the column would be an unverifiable assertion, not evidence.

Recommendation: documentation uses untyped relations plus `provenance.sources`,
which is where the verifiable dependency already lives. Revisit typed edges only
when a generator rather than a human is the author of an edge, because then the
type is derived and free. That is the condition D7 records.

### Q3. Does Hydra already have a generic projection abstraction that should be extended?

D4's answer is **confirmed on vocabulary and corrected on mechanism**.

Confirmed: `surface` is the word. `.hydra-framework/surfaces/README.md:3-6`
defines a surface as an "audience-facing or interface-specific view of
knowledge", records "whether a surface is canonical, derived, synchronized,
private, generated, or hand-maintained", and states that "the pages themselves
live outside `.hydra-framework/`". That is §27's projection with a different
noun, and `identity/object_families.py:45-51` is the repository's own argument
against carrying a second word for one concept.

Corrected: D4 implied the concept is implemented at the surface boundary. It is
not. `.hydra-framework/surfaces/` contains one `README.md` with no frontmatter
and no `hydra_id`, so it is scanned by the Markdown handler and discarded
(`objects/envelopes.py:112-114`, Phase 1 §6.1). The contract is prose.

But a working projection mechanism does exist, one level down and for a
different corpus:

- `providers/reclaim.py:33-40` lists six provider-native roots.
- `planned_adapter_files` computes what Hydra would generate for each.
- `classify_surfaces` (`providers/reclaim.py:98-146`) classifies every file
  under those roots as `generated`, `drifted`, `stale` or `orphaned`, reading a
  per-file sidecar with `schema: hydra-framework.adapter.v2`, `canonical_source`
  and `generated_file`.
- `reclaim --fail-on-findings` runs in CI (`.github/workflows/hydra.yml:56`),
  and the same classification feeds validator 2 and `doctor`'s surface report.

That is §17's authored/generated/hybrid model and four of §20's drift categories,
shipped and enforced. Phase 3's answer to "which abstraction do we extend" is
this one, generalized past its hardcoded six roots, not a new `projection`
concept beside `surface`.

### Q4. Where should wiki manifests live?

D4's `surfaces/` is **confirmed**, with one correction and one measured
alternative Phase 3 must weigh against it.

Confirmed: `surfaces/README.md:101-105` says to add "a section here describing
the contract, not an empty directory", so a recorded contract there is what the
directory exists for.

Corrected: D2 row 7 recorded this as "confirmed current behavior". Nothing in
`surfaces/` is machine-readable (Phase 1 §6.1), so the manifest is a new file.
See B3.

The measured alternative: the manifest can be the object sidecar itself.
`objects/discovery.py:48` already resolves a sidecar `path:` beginning
`project-wiki/` from the repository root, and `objects/discovery.py:117-126`
requires only that the sidecar live under `.hydra-framework/`. The §1.2 probe
registered a wiki page by appending one entry to
`.hydra-framework/repo/object-sidecars.yaml`, with no engine change:
`ref index` -> 58, `ref check` -> ok, `validate` -> ok, `explain-path` reporting
`Tier: external` and the object.

The blast radius, now established where Phase 1 §8 item 3 left it open:

- Registering a page puts it under the registry digest check at
  `objects/registry.py:191-193`, reached by validator 11
  (`objects/registry.py:225-235`) and therefore by `validate`, `doctor` and CI.
  **Measured: appending one line of prose to a registered page makes `ref check`
  fail** with `has stale digest ... rerun 'hydra.py ref index'`. Nothing
  reindexes automatically; no path in `commands/hooks.py` and no step in
  `.github/workflows/hydra.yml` calls `ref index`.
- Registering a page does **not** put its prose under reference resolution.
  Measured: a deliberately unresolvable `hydra://` reference added to the
  registered page left `ref check` at `ok` after reindexing. Phase 1 §2.4 holds.

So the recurring price is one `ref index` per wiki edit. That price already
applies to all 57 objects; what is new is extending it to the 40 files edited
most often by humans and agents. Phase 3 decides whether to pay it, to automate
it in the post-edit hook, or to hold the manifest outside the object graph. This
review does not settle that; it settles what it costs.

### Q5. Should documentation metadata use frontmatter, a central registry, Hydra objects, or a hybrid?

**A central registry of Hydra objects: the sidecar.** Frontmatter is the
expensive option and a hybrid buys nothing.

- Frontmatter on wiki pages costs an engine change. The Markdown handler roots
  at `.hydra-framework/` (`objects/object_handlers.py:98`) and
  `object_document_paths(hydra_root)` (`:145`) `rglob`s under that one
  directory. Phase 1 §2.2 records that this single parameter is the whole of the
  gap. Adding a second root also widens what `ref check` scans for `hydra://`
  references (`objects/references.py:121-136`), which is exactly the blast radius
  the sidecar route avoids.
- A sidecar costs nothing today (Q4), and 0 of 40 wiki pages carry frontmatter,
  so the sidecar route changes no page at all.
- Extra fields are inert either way. `objects/envelopes.py:103-166` reads a fixed
  field list and nothing validates unknown keys, so `doc_kind`, `audiences` and
  `outputs` would be parsed and dropped until a consumer exists. See D4.

Deferred to Phase 3: whether the sidecar is one file per wiki or one file for
all wikis, and whether the wiki manifest (Q4) and the page entries are the same
file. Both are shapes, not contracts.

### Q6. What is the minimum stable documentation identity?

`hydra_id` plus `uid`. The mechanism exists and needs nothing new.

`identity/schema_versions.py:20` requires `uid` from schema version 2 onward, and
`:29` requires the envelope from version 3; all 57 objects are at 3, so
`ref check` prints no pending-upgrade clause (Phase 1 §2.5).
`commands/object_moves.py:48-55` states the contract directly: a move "relocates
the file and rewrites derived state only; `hydra_id` and `uid` are never
touched, which is exactly what lets `ref check` recognize the result as the same
object rather than a delete plus an add". `move-object` refuses outright when an
object has no `uid` (`commands/object_moves.py:78-84`).

`path` is derived, movable state. It is stored in the sidecar and the registry
and rewritten by the move. That is the whole answer: identity is the pair, and
location is not part of it.

### Q7. Should pages, sections, and claims all have Hydra identities?

Pages yes, sections and claims no, and not for the MVP.

Pages: cheap and already possible (Q4).

Sections and claims: the object model's unit of identity is a file, in three
places that would all have to change. `objects` carries one `path` and one
`digest` per object (`objects/store_schema.py:16-41`);
`objects/envelopes.py:156` digests the object's own whole file;
`commands/object_moves.py:92-97` refuses a suffix change because "object
discovery is extension-driven". A section identity needs anchor addressing and a
sub-file digest; neither exists, and inventing them for documentation alone would
give the repository two identity models.

Deferred to Phase 3 as a boundary question, with the recommendation recorded:
pages only, and the cheapest sub-page mechanism available if one is ever needed
is the one already shipping, `bindings`, whose assertions fingerprint a slice of
a target rather than the whole file (`knowledge/bindings.py:131-202`).

### Q8. How should renamed and moved documents preserve identity?

Through `move-object`, which already does it, with one gap that CI covers.

What it does (`commands/object_moves.py:48-144`): validates references first,
refuses when the object has no `uid`, refuses when the destination exists,
refuses a suffix change, refuses a tier change, moves the file, rewrites the
sidecar `path:` in place, re-runs `validate_object_references`, **reverts the
whole move and restores the sidecar if references break**, then rewrites the
registry and prints the new index count.

What applies to a wiki page: the tier check passes, because every path under
`project-wiki/` is `external` (`objects/envelopes.py:27-34`), so any move inside
the wiki keeps the tier. The suffix and destination checks apply unchanged.

The gap: `stale_path_citations` (`commands/object_moves.py:30-45`) reports files
that still name the pre-move path, deliberately reporting rather than rewriting,
but it iterates `object_metadata_paths`, which is `.hydra-framework/`-rooted. A
wiki page linking to the moved page is not in that set and will not be reported.
Nothing breaks silently: `validate_markdown_links` (`wiki/links.py:31-50`) fails
the next CI run on the broken link. But the two halves of the answer come from
two commands, and Phase 3 should either widen `stale_path_citations` or say
plainly that `validate-wiki` owns the wiki half.

### Q9. How should verification state be recorded?

With the four fields that already exist, unchanged: `provenance.sources`,
`provenance.source_digests`, `checked_on`, and `verify`.

`knowledge/units.py:30-48` is the only dataclass carrying `source_digests` and
`checked_on`. `commands/knowledge_fingerprint.py:96-127` is what writes them: it
re-hashes every listed source and rewrites the block in place. `verify` is a list
of commands that nothing in `hydra_engine/` executes; it is instruction to a
human or agent (Phase 1 §4.5). None of that changes for a page.

One correction to the proposal's §18 shape: do not add `last_verified.commit`.
`knowledge/freshness.py:305-308` returns before the commit-date branch whenever a
digest is recorded for a source, and Phase 1 §4.5 measured that all 27 sources
across all 7 units are digested. A commit field would be written and never read.

One limit that decides how much converts (Q24): `knowledge fingerprint` refuses
any source that is not exactly one existing file
(`commands/knowledge_fingerprint.py:112-114`), and the digest branch requires
`path.is_file()` (`knowledge/freshness.py:306`).

### Q10. Should staleness use commits, file hashes, object hashes, semantic fingerprints, or multiple mechanisms?

**File hashes alone.** Not multiple mechanisms, which is what the repository has
and what produces its one wrong message.

Both rules exist at `knowledge/freshness.py:287-314`, and the hash rule wins
every time it applies: a digested source `continue`s at `:308` and never reaches
the Git date rule at `:311`. Phase 1 §4.5 measured that every source of every
unit is digested, so the date rule has never fired in this repository. The cost
of keeping both is visible at `commands/knowledge.py:194`, which hardcodes
"committed after checked_on" for every row, so every line `knowledge stale`
currently prints states a reason that did not apply (Phase 1 §7.3).

Object hashes are not a third mechanism: `objects.digest` is the same
`normalized_digest` over the same file (`objects/envelopes.py:156`).

Semantic fingerprints: deferred, and premature until page-level digest staleness
has run and been measured to produce too many false positives. Risk §34.3 asserts
that rate; nothing has measured it, because no page-level staleness exists.

Per the phase's rule on typed edges: none of this needs a relation type. The
dependency that staleness reads is `provenance.sources`, a path list, which
`objects/envelopes.py` preserves intact. Only the `relations` list is flattened.

### Q11. Which documentation categories should block CI?

**Nothing new, in the first increment.** Cited by Phase 1 §5.5.

What already blocks, and should continue to: link resolution
(`.github/workflows/hydra.yml:62`, `validate-wiki`) and the whole object model
through `doctor` (`:39`, validator 11), which is what would enforce a registered
page's digest freshness.

What must not block: staleness. `knowledge/package_checks.py:148-156` gives the
reason in the engine's own words, and it applies unchanged to pages: every
`Finding` makes `validate` exit nonzero, there is no warning tier, and turning a
deliberately stale page into a hard failure contradicts the design's own "never a
hard failure" requirement. Staleness belongs in the existing second tier,
advisory notes printed after the verdict (`cli/dispatch.py:133-145`).

What is worth blocking later, and only later: generated-reference drift, because
it is deterministic. The generator either reproduces the committed bytes or it
does not, which is the same test `reclaim` already applies to provider wrappers
(`providers/reclaim.py:98-146`). Note the counter-precedent before adopting it:
`export-adapters --check` was removed from CI deliberately, with the comment at
`.github/workflows/hydra.yml:28-31` explaining that a drift gate is meaningless
once nothing is tracked. A generated wiki page would be tracked, so the reasoning
does not transfer, but Phase 3 should say why.

### Q12. How should intentional non-impact be acknowledged?

With `bindings verify --accept`'s model, which already exists. See E11.

`knowledge/bindings.py:193-202` computes a fingerprint over a binding's
assertions and sets `awaiting_review` only when every assertion still holds and
the sole objection is that the fingerprint is unreviewed. `BindingStatus`
documents that callers "must not infer this by searching `errors`, whose text
interpolates author-controlled values" (`:41-45`).
`commands/knowledge_bindings.py:64-68` accepts only in that state, so
`--accept` cannot paper over a real failure.

That is exactly the distinction §34.3 asks for: "the source changed" is separate
from "I looked and the claim still holds", and the acknowledgment is recorded in
the file under review rather than in a side channel.

The simpler mechanism, `knowledge fingerprint --unit <id>`
(`commands/knowledge_fingerprint.py:96`), re-verifies with no prose change but
records no reasoning. Use it for a mechanical re-verify and the bindings shape
where a reason matters.

No new mechanism is needed for this question.

### Q13. How should generated blocks be updated without damaging authored prose?

With marker-bounded idempotent replacement, which the repository already
implements for `.gitignore`.

`providers/git_ownership.py:22-23` defines `IGNORE_BLOCK_HEADER` and
`IGNORE_BLOCK_FOOTER`. `ensure_generated_adapter_ignore_block` (`:47-72`) finds
the header, finds the footer from there, compares the existing block to the
rendered one, returns `already-present` when identical, replaces the slice in
place when not, and appends only when no header exists. It never writes a second
block and never touches a line outside the markers.

Port that for Markdown. It is roughly 25 lines with an existing tested shape.

Deferred to Phase 3: whether the marker is the HTML-comment syntax §17.3 shows,
which keeps markers invisible in a rendered page, and whether the drift check
compares rendered output to the committed block or only reports that the
generator's inputs changed. Note one interaction with D2: a regenerated block
changes the page's digest, so a generated block inside a registered page means
the generator must also run `ref index`.

### Q14. Which graph views provide actual value in the MVP?

**One: the transitive reverse walk.** It is the only view in §19 that the
repository cannot already answer.

Phase 1 §3.2 established the shape: `ref rdeps` is one hop inbound
(`objects/store_queries.py:95-102`, measured to return 14 citers for
`hydra://knowledge-space/hydra-framework`), and `ref impact` is transitive
**outbound**, depth 5, cycle-guarded by a path-membership test in the recursive
CTE (`:115-136`). So "what breaks if I change X" has no query. That is the
question §19's change-impact graph is drawn to answer and the question a
documentation impact report needs.

The other seven views restate `cognition/graph/registry.yaml` in another shape.
The registry already carries, per object, `uid`, `path`, `digest`, `family`,
`kind`, `status`, `tier`, `scope`, `schema_version`, `title`, `aliases`,
`relations` and `provenance_sources`. A repository graph, architecture graph,
documentation graph and space graph are filters over one export.

Two adjacent gaps that are not graph views and are cheaper than any of them: no
`ref` subcommand emits JSON (Q21), and no `.dot` file exists in the repository,
so `hook-post-edit --render`'s diagram path has never run on real content.

### Q15. How should projection boundaries prevent knowledge leakage?

By widening one existing check, not by building an allowlist system.

Validator 8, `tier-boundaries` (`checks/repo_findings.py:58-59` ->
`work/tiers.py:67`), already fails `validate` on the two failures that matter:
a private-tier file tracked in Git, and a shared Markdown file citing a concrete
private file path. Its docstring (`work/tiers.py:68-80`) states why the second is
worse than a broken link.

It does not see the wiki. The citation scan iterates
`iter_markdown_files(paths.hydra)` (`work/tiers.py:110`), which is
`.hydra-framework/`-rooted.

**Measured: widening it to `project-wiki/` would produce zero findings today.**
All 19 `.hydra-framework.local/` mentions across the 40 wiki pages either name a
directory or name an area outside `PRIVATE_CONTENT_AREAS`
(`work/tiers.py:47`, `intake|notes|tasks|migrations|evolution|scratch|logs`), and
`PRIVATE_FILE_REF_RE` (`:51-54`) matches none of them. The comment at `:44-46`
explains why `capabilities/` is deliberately excluded: conventional locations
with fixed names tell a reader where to put theirs rather than citing yours.

So risk §34.6 and §34.10 are prospective, not current, and the first increment is
a one-argument widening of a shipped check. A public website build needs a real
allowlist and a default-deny for unclassified sources; deferred with the website
(F1), because nothing decides it until there is a build to protect.

### Q16. How should conflicting spaces resolve authority?

**Deferred to Phase 3 at the earliest, and probably past it.** Premature for the
same reason C9 is: there is one space, one node, and no child nodes
(`repo/knowledge/spaces.yaml` is 5 lines; Phase 1 §4.1), so there is nothing to
conflict and no way to test a rule against real data.

What Phase 3 must not contradict, if it does touch this: `knowledge/nodes.py:239-265`
resolves values down a single parent chain and records, per key, which ancestor
supplied each value, with depth capped by `knowledge/contracts.py:3-4`. Any
resolution rule either fits that trace or replaces the node model. And the
repository's existing answer to a genuine disagreement is to record it rather than
resolve it: `unit_kind: divergence` requires `certainty: conflicting` and the
phrase "effect on agents" (`knowledge/package_checks.py:214-229`).

### Q17. How should external portable spaces be versioned?

**Deferred whole.** Out of this review's scope by the task record's Goal, which
excludes section 11 as an enterprise-repository concern with no demonstrated need
here. Reviewed only for whether the chosen boundaries would block it later; they
would not, because a version marker is a field on a space manifest and no
boundary in this review touches space manifests.

Two notes for whoever picks it up. `scope:` is taken and means seed distribution
(C8). And the repository already versions one kind of portable material: `diff-base`
classifies this Hydra copy against the base seed it descends from, and
`evolution record --base-seed-version` (`commands/seed.py:163`) records the seed
version at the time of a change.

### Q18. Should CLI naming use `docs`, `wiki`, `projection`, or a combination?

**`wiki`.** D4 is confirmed on ruling out `projection` and does not reach CLI
naming, so this answers the rest.

Measured from `hydra.py --help`: the CLI already has a top-level `wiki`
namespace with one subcommand, `wiki scaffold <project>`, plus a top-level
`validate-wiki`. There is no `docs`, no `graph`, no `projection` and no `surface`
command.

So `wiki list`, `wiki audit`, `wiki coverage` extend a namespace that exists and
already owns this corpus. `docs` would be a second namespace for the same files.
`projection` is out by A2. `surface` is the right word for the concept and the
wrong word for the command, because the CLI already spells this corpus `wiki`
and `surfaces/` is where the contract lives, not what the corpus is called.

One caveat Phase 3 should weigh: if the audit is ever to cover more than
`project-wiki/` (README, `AI_SYSTEM.md`, generated provider wrappers), `wiki` is
the wrong name for it. The scope decision comes first; the name follows.

### Q19. Should the website be one unified portal or support independently deployed wiki surfaces?

**Deferred.** Out of scope by the task record's Goal, which defers the website
whole and reviews it only for whether it constrains the data contract. This
question does not: one portal and several deployments consume the same per-page
metadata, so nothing upstream changes either way.

One measured fact that bears on it when it is taken up: there is one wiki
(`project-wiki/hydra-framework/`, 8 sections, 39 pages) plus `home.md`. A
multi-deployment design has one thing to deploy.

### Q20. Which static-site framework best fits the existing repository without controlling the architecture?

**Deferred.** Out of scope by the Goal. Nothing in the intelligence half depends
on the answer provided Q21 is settled first, which is the Goal's own test for
whether a website question constrains the data contract.

### Q21. Can the website consume a stable Hydra-generated JSON contract?

**Not today, and this is the one website question that constrains the data
contract now.**

Measured: of the 70 registered commands, 19 accept a `--json` argument (`board`,
`compile-context`, `diff-base`, `explain-path`, `integrate scan`,
`integrate status`, `measure-context`, seven `migration` subcommands, `reclaim`,
`route-prompt`, `takeover scan`, `telemetry report`). **None is a `ref`
subcommand.** `ref resolve`, `ref rdeps`, `ref impact`, `ref check` and
`ref store status` are text-only, so the graph is not machine-readable through
any command.

What does exist is `cognition/graph/registry.yaml`, `schema:
hydra-framework.object-registry.v1`: a derived export of every object with its
`uid`, `path`, `digest`, `family`, `kind`, `status`, `tier`, `scope`,
`schema_version`, `title`, `aliases`, `relations` and `provenance_sources`,
rewritten by `ref index` and freshness-checked by validator 11. That is the graph
snapshot §25 asks for, in YAML, minus relation types (Q2).

So the answer is yes, with a small addition: a JSON rendering of the export that
already exists and is already validated. Deferred to Phase 3 only for whether it
is `ref index --json`, a new command, or a generated file beside the YAML. The
contract itself is settled: it is the registry, and it should not be a second
export with its own freshness question.

### Q22. How should site previews work for pull requests?

**Deferred.** Out of scope by the Goal, and dependent on Q20. Nothing upstream is
constrained.

### Q23. What is the migration path for existing `project-wiki` content?

There is no content migration. Measured: 40 Markdown files, none with
frontmatter, links either root-relative or file-relative, `validate-wiki` passing
today. Registering the pages changes no page.

The path is three steps:

1. Add one sidecar entry per page under `.hydra-framework/`, with `hydra_id`,
   `uid`, `kind`, `title`, `status`, `scope`, `owners`, `path`,
   `provenance.sources` and `relations`. The five envelope fields are mandatory
   and carry no defaults (`identity/schema_versions.py:35`,
   `objects/envelopes.py:132-138`); `relations` and `provenance.sources` are
   mandatory but may be empty, and `objects/references.py:69-78` says so in the
   finding text specifically so an agent does not invent filler.
2. Run `ref index`.
3. Accept the recurring cost established in Q4: `ref index` after every edit to a
   registered page, or `validate` fails.

What is not free is deciding `provenance.sources` per page. Source Map supplies
that decision for 23 of the 40 pages already (Q24); the other 17 have no recorded
sources and someone has to establish them from the implementation. That is the
real migration cost, and it is authoring work, not tooling work.

Sequencing recommendation for Phase 3: register the 23 Source-Map-covered pages
first, because their sources are already written down and already link-checked,
and treat the remaining 17 as a separate, bounded authoring pass.

### Q24. How much of the current Source Map can become the first dependency registry?

D2's answer is **corrected by Phase 1 §5.1 and quantified here.** The gap is
freshness, not existence.

Reproduced: `source-map.md` has 19 rows citing **41 distinct non-wiki canonical
targets**, all resolving, all root-relative Markdown links, and
`validate_markdown_links` (`wiki/links.py:44`) resolves every root-relative link
from the repository root on every CI run. The page contains zero backtick path
citations. The unchecked citations in this repository are the 94 root-anchored
backticks on **other** wiki pages (Phase 1 §5.1), not on this one.

The new measurement, which is what answers "how much":

| Of the 41 distinct non-wiki targets | Count |
| --- | --- |
| Files, convertible to digested `provenance.sources` today | **33** |
| Directories, not convertible | **8** |
| Not resolving | 0 |

The eight directories are `/.hydra-framework/capabilities`,
`/.hydra-framework/engine/src/hydra_engine/command_output`, `/commands`,
`/knowledge`, `/providers`, `/telemetry`, `/.hydra-framework/engine/tests` and
`/.hydra-framework/validation/rules`. They cannot be digested:
`knowledge/freshness.py:306` requires `path.is_file()` for the digest branch, and
`commands/knowledge_fingerprint.py:112-114` refuses outright any source that is
not exactly one existing file.

So **33 of 41 citations convert mechanically today**, with no new mechanism. The
8 directory citations are the same hole Phase 1 §4.6 found in the `overview`
slice, which cites two engine directories and is unchecked twice over. Phase 3
must decide directory sources explicitly: a per-directory manifest digest, an
expansion to the files it contains at fingerprint time, or a refusal that forces
the citation to name files. That is a real design decision this phase does not
settle.

Page coverage, which the proposal does not ask about and Phase 3 needs: the 19
rows name **23 distinct wiki pages out of 40**. A Source-Map-derived registry
starts at roughly 58% page coverage, with 17 pages unassigned. See Q23.

### Q25. Which current-main capabilities are missing or poorly represented in the Hydra wiki?

Cited by Phase 1 §7, with the measurements reproduced.

**Absent from the wiki's command reference.** 5 of the 70 registered commands
appear nowhere in `command-surface.md`: `bindings list`, `bindings verify`,
`capability scaffold-agent`, `capability scaffold-skill`, `knowledge migrate-v2`.
Reproduced exactly against `command-metadata --json` today.

**Built but represented nowhere, because there is nothing to represent yet.**
Four capabilities are shipped, tested and unused, so a wiki page about them would
document a mechanism with no instance: `bindings` (`manifest.yaml` is
`fragments: []`, `bindings list` prints "none declared", Phase 1 §4.2); knowledge
views (`repo/knowledge/views/` does not exist; `discover_views` returns `[]`,
§4.3); the `refs` table (populated every rebuild, read by nothing, §3.1); the
Telemetry object family (registered with a context provider, zero members, §2.1).

**Represented wrongly rather than absently.** Four engine docstrings disagree
with their own code (`cli/parser.py:12` says ten shim commands where there is
one; `checks/validator_registry.py:21` says ten checks where there are 19;
`objects/object_handlers.py:45` says two engine-module objects where there are
three; `commands/references.py:96` attributes `ref rdeps` to the `refs` table,
which no query reads). `knowledge stale` prints a reason that applied to no row
it has ever printed (`commands/knowledge.py:194`, §7.3). `scripts/README.md:129-135`
hides that `project-wiki/` is a first-class sidecar root (§7.1). `source-map.md`'s
own Review Rule warns about backtick citations on a page that has none (§7.2).

**The part of the answer that matters for Phase 3.** The drift is not
concentrated in the wiki. Four of the eight items above are inside the engine, in
files that are themselves Hydra objects. A mechanism scoped to `project-wiki/`
would have found none of them. Whatever Phase 3 designs, its dependency model
should be able to point at a docstring in `cli/parser.py` as readily as at a page
in `project-wiki/`, because that is where half the measured drift is.

## 4. Gate evidence

Every proposal component is classified in section 2: 63 rows across seven
groups, covering all six proposal part files. Every one of the 25 questions in
§36 is answered in section 3, Five are deferred whole, each with a reason: Q16, Q17, Q19, Q20 and Q22. The
other twenty carry an evidence-backed answer; several of those defer one named
sub-decision to Phase 3 rather than the question.

Commands run for this phase, on `main` at 7801b1d:

- `ref store rebuild` -> `rebuilt from 57 object(s)`; `status: fresh`, `export
  digest: agrees with the export`, `objects: 57`, `refs: 104`, `relations: 30`,
  `provenance: 50`, `documents: 365`
- `ref index` -> `Indexed 57 objects`
- `command-metadata --json` -> 70 entries; 5 absent from `command-surface.md`;
  19 accept `--json`, none of them a `ref` subcommand
- `validate-wiki` -> `ok`
- `validate` -> `ok`
- Isolated probe (§1.2), on a scratch copy only -> `Indexed 58 objects`,
  `ref check ok (58 objects)`, `validate ok`, `ref store rebuild` from 58 objects
  with no schema change, `explain-path` resolving in both directions

Not run: `selftest` in the probe copy, which was killed after it failed to
complete without a `.git` directory. Phase 3 must run it in a real clone before
relying on §1.2's family registration.
