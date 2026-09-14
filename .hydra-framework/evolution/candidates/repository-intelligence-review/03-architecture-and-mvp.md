# Phase 3 -- Revised Architecture And MVP

Part of [`repository-intelligence-review`](../repository-intelligence-review.md).
Deliverables C, D, E and F of the task record
`.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-14-repository-intelligence-and-wiki-projections.md`.

Decided 2026-09-14 on `main` at 7801b1d. Sections 1 through 7 of
[`01-current-state.md`](01-current-state.md) and sections 2 and 3 of
[`02-gap-analysis.md`](02-gap-analysis.md) are carried forward by citation, not
re-derived. Where this phase overturns one of them, the correction is in section
0 and is recorded in place in the task record's Confirmed Decisions.

No README, wiki page, knowledge unit, or historical plan is used as evidence of
current behavior anywhere in this file.

Every behavioral claim below that was not already established by Phase 1 or
Phase 2 was measured in an isolated `git clone` of this repository under the
session scratchpad. The working tree was never modified. Reproduce with:

```bash
python3 .hydra-framework/scripts/hydra.py ref store rebuild
python3 .hydra-framework/scripts/hydra.py ref index
python3 .hydra-framework/scripts/hydra.py ref check
python3 .hydra-framework/scripts/hydra.py validate
python3 .hydra-framework/scripts/hydra.py selftest
```

plus the Phase 3 probe recipe in section 1.

One spelling convention, inherited from Phase 2 and load-bearing: probe object
ids are written without their `hydra://` scheme prefix, as
`documentation/page/state-tiers`. This file is itself scanned by `ref check`
(`objects/references.py:121-136`) and the probe objects exist only in the clone,
so spelling an id in full would make this artifact fail `validate`.

## 0. Corrections to Phases 1 and 2

Five findings change an earlier claim. Each is recorded in place in the task
record.

| Claim | Where | Measured | Effect |
| --- | --- | --- | --- |
| A `Documentation` family "costs two lines, one `ObjectFamily` entry and one string in `SEARCH_FAMILIES`" | Phase 2 §1.2, D1 | Two lines is right, and both are mandatory for a reason neither phase found. `unit/knowledge/test_context_providers.py:81` asserts set equality between `OBJECT_FAMILIES` names and `CONTEXT_PROVIDERS` families, and `CONTEXT_PROVIDERS` is built from `KNOWLEDGE_FAMILY` plus `SEARCH_FAMILIES` (`knowledge/context_providers.py:273-277`). Measured: family without the `SEARCH_FAMILIES` string -> `ref index`, `ref check` and `validate` all pass, and `selftest` **fails**, 2 failures, `test_every_object_family_has_exactly_one_context_provider` plus the `contract.goldens.test_core` selftest golden cascading off it. Both lines together -> 1633 tests, OK | The price is confirmed at two lines and the second one is not a choice. Its measured consequence comes with it: a registered wiki page becomes a `compile-context` candidate, one page contributing 511 approximate tokens, capped at eight candidates |
| "Registering a page does not put its prose under reference resolution", therefore registration is cheap | Phase 2 §1.2 | Holds, and is incomplete. `index_collection.py:82-85` adds **every registered object that is not already in the file corpus** to the lexical search index as a title-only document. The search corpus itself is `.hydra-framework/`-rooted (`knowledge/freshness.py:24-30`, measured: 330 files, 0 under `project-wiki/`), so registration is the only way a wiki page enters retrieval, and registration does it automatically | Registering 40 pages adds 40 retrievable documents, title-only in the index and whole-file once selected. The context provider's share of that is bounded by `DEFAULT_FAMILY_CANDIDATE_CAP = 8` (`knowledge/context_providers.py:25`) |
| "One [graph view worth building]: the transitive reverse walk" | Phase 2 Q14, E3 | True of the object graph in general, **false for the documentation MVP**. Documentation impact runs through `provenance`, not `relations`. `citers_of_source_path` (`objects/store_queries.py:105-112`) already answers it in one hop and already ships. Measured: after registering three pages, `explain-path .hydra-framework/core/placement-rules.md` listed `documentation/page/state-tiers` beside the existing knowledge-unit citer, store-backed | Section 33 item 6 leaves the MVP. The reverse walk stays a real gap in the object graph and is not on this critical path |
| "`project-wiki/` is already a recognized sidecar root" at `objects/discovery.py:48` | Phase 1 §2.4 | Two places, not one. `objects/moves.py:104` carries the same three-prefix tuple for the sidecar `path:` rewrite, which is why `move-object` works on a wiki page unchanged | Decision 5 needed no engine change, and the reason is structural rather than accidental |
| "Phase 3 must run `selftest` in a real clone" | Phase 2 §1.2 | Run. **1633 tests, OK**, with the `Documentation` family registered and three wiki pages registered as objects. Also established: `selftest` fails in a fresh clone on `repository.test_provider_surfaces` until `export-adapters` runs, which is what `.github/workflows/hydra.yml:33` does before `:36` | Decision 3 is settled on measurement rather than inference |

One stale figure outside this phase's own artifacts: the router's Phase 1
paragraph still reads "all 23 typed relations". Phase 2 corrected that to 22.
Corrected in the router in the same commit as this file.

Everything else in both artifacts reproduces. Specifically re-run and confirmed:
`ref index` -> 57 objects and `ref check` -> ok on the unmodified tree, `ref
store rebuild` -> 57 objects, `validate` -> ok with five advisory notes,
`validate-wiki` -> ok, `knowledge stale` -> 7 units checked and 2 stale, 40
Markdown files under `project-wiki/`.

## 1. The Phase 3 probe

Phase 2's probe ran on a `.git`-less copy and could not finish `selftest`. This
one ran on `git clone "$PWD" <scratchpad>/clone`, at 7801b1d, with a real `.git`.
Four edits, all additive:

1. One `ObjectFamily(name="Documentation", id_prefixes=("documentation",),
   kinds=("documentation-wiki", "documentation-page"))` appended to
   `OBJECT_FAMILIES` (`identity/object_families.py:132-142` is the shape it
   copies).
2. `"Documentation"` appended to `SEARCH_FAMILIES`
   (`knowledge/context_providers.py:28`), then removed again and `selftest`
   rerun, to establish whether the two lines are severable. They are not.
3. One new sidecar, `.hydra-framework/surfaces/wiki/hydra-framework.yaml`,
   `schema: hydra-framework.object-sidecar.v1`, declaring three objects: one
   wiki manifest and two pages, each with a real `uid`, real
   `provenance.sources` taken from `source-map.md` rows, real
   `provenance.source_digests`, and `checked_on`.
4. For the staleness measurement only, one appended line in
   `.hydra-framework/core/placement-rules.md`, reverted afterwards.

| Measurement | Result |
| --- | --- |
| `ref index` | `Indexed 60 objects` |
| `ref check` | `ok (60 objects)` |
| `validate` | `ok`, same five advisory notes |
| `validate-wiki` | `ok` |
| `validate-package-docs` | `ok` |
| `reclaim --fail-on-findings` | `orphaned: 0`, `drifted: 0`, `stale: 0` |
| `ref store rebuild` | `rebuilt from 60 object(s)`; `objects: 60`, `provenance: 57`, schema unchanged |
| `selftest` | **1633 tests, OK** |
| `explain-path <registered page>` | `Tier: external`, `Object: documentation/page/state-tiers (Documentation/documentation-page)`, with its three `provenance_sources` |
| `explain-path .hydra-framework/core/placement-rules.md` | `Source: sqlite`, `Cited as provenance by:` six objects including `documentation/page/state-tiers` |
| `knowledge stale` | `Checked units: 7`, unchanged. Registered pages are invisible to it |
| Sidecar in `surfaces/wiki/` versus `repo/object-sidecars.yaml` | Both work. Sidecar discovery is schema-driven, not location-driven (`objects/discovery.py:64-76`) |
| Family registered, `SEARCH_FAMILIES` left alone | `ref index`, `ref check` and `validate` pass, and `selftest` **fails** with 2 failures: `unit.knowledge.test_context_providers` `test_every_object_family_has_exactly_one_context_provider`, and the `contract.goldens.test_core` selftest golden cascading off it. The second line is mandatory |
| `SEARCH_FAMILIES` including `Documentation`, `compile-context --include-family Documentation --task "state tiers private shared boundaries"` | Selected `project-wiki/hydra-framework/concepts/state-tiers.md`, 511 approximate tokens, reason `Documentation context provider match` |
| Lexical search corpus | 330 files, **0** under `project-wiki/` (`_canonical_search_files`, `knowledge/index_collection.py:140-150`). Registered objects enter the index separately at `:82-85`, title-only |
| One appended line of prose in a registered page | `ref check` -> `failed`, `has stale digest for ...; rerun 'hydra.py ref index'`. `validate` -> `failed`, same finding |
| `hook-post-edit` on a registered wiki page | Exit 0, no output. It returns at `commands/hooks.py:78` because a wiki page is in no knowledge node |
| `ref index` runtime | 0.63 to 0.64 s, three runs |
| `hook-post-edit` runtime, no-op path | 0.14 s, three runs. Hook timeout budget is 30 s (`.claude/settings.json:46`) |
| `move-object <page> <new page>` | `Moved documentation/page/state-tiers`, then `Indexed 60 objects`. `hydra_id` and `uid` preserved, sidecar `path:` rewritten, registry reindexed by the command itself |
| `validate-wiki` after that move | `failed`, six missing links from four wiki pages that still name the old path. `move-object` itself reported none of them |
| `stale_provenance_sources` called with a sidecar `provenance` block | Works unchanged. Returned `[]` for all three pages, then `['.hydra-framework/core/placement-rules.md']` for the one page whose source was edited. Roughly 20 lines of reader code, no change to `knowledge/freshness.py` |

That last row is the whole MVP mechanism, proved. `stale_provenance_sources`
(`knowledge/freshness.py:287-314`) takes a plain `Mapping`, a `checked_on`
string and `ContextCompilerPaths`. It has no dependency on the unit model;
`knowledge/candidates.py:84-88` is simply the only caller today, and it builds
the same mapping out of a `Unit`.

## 2. The five boundary decisions

Each decision states what a reader checks against the repository to confirm it,
and what would overturn it.

### Decision 1: a wiki page becomes an object, by sidecar, and the reindex is automated

**Decided: yes, register pages as objects. Mechanism: an object sidecar under
`.hydra-framework/surfaces/`. Pay the recurring `ref index` cost, and automate
it in `hook-post-edit`.**

Register, because registration is the only thing that answers the question this
whole review exists for. Measured: `explain-path` on a source file named the
registered page as a citer, store-backed, one hop, with no new query. An
unregistered page is not in `provenance`, so `citers_of_source_path` cannot see
it, and the answer is empty rather than wrong.

By sidecar rather than frontmatter, per Q5. Frontmatter costs a second root in
`object_document_paths(hydra_root)` (`objects/object_handlers.py:145`), which
also widens what `ref check` scans for `hydra://` references
(`objects/references.py:121-136`). The sidecar route touches no page: 0 of 40
wiki pages carry frontmatter today and none needs to gain any.

The recurring cost is real and lands where it hurts most. A one-line prose edit
to a registered page fails `ref check` and therefore `validate`, `doctor` and
CI, until `ref index` is rerun, because `objects/registry.py:191-193` compares
the object's stored digest to its current one.

Three options were weighed and the third is rejected on evidence:

- *Pay it manually.* Correct and unpleasant. Every wiki pull request would fail
  CI once before someone remembers the command.
- *Automate it in `hook-post-edit`.* Measured viable: `ref index` is 0.64 s
  against a 30 s hook budget, and the hook is already wired for
  `Write|Edit|MultiEdit` in both providers (`.claude/settings.json:41-49`,
  `.codex/hooks.json:22`). It changes one contract: the wired hook is read-only
  today, and this makes it write one derived, tracked file. `ref index` is
  deterministic and idempotent, so that write is the same class of action as a
  formatter on save. It does not cover human editor edits, merges, or rebases,
  so CI stays the backstop. That is the correct division: the hook removes the
  common case, CI catches the rest.
- *Keep documentation metadata outside the object graph.* Rejected. A manifest
  whose `schema:` is not `hydra-framework.object-sidecar.v1` is read by nothing
  (`objects/discovery.py:75-76`), so it produces no registry entry, no store
  row, no `explain-path` answer and no `move-object` support. It avoids the
  reindex cost by giving up the capability the reindex cost buys.

**What a reader checks.** Append a line to any registered page and run `ref
check`. It fails and names the command. Run `ref index` and it passes. Time
`ref index` and compare against the hook timeout in `.claude/settings.json:46`.

**What would overturn it.** A measurement showing `ref index` runtime growing
past the hook budget as the object count grows. At 60 objects it is 0.64 s.
`problems.md` P5 and P12 own index scaling and are out of scope here, so this
decision inherits whatever they conclude.

### Decision 2: `relations` stays untyped

**Decided: confirm Phase 2. Use the relation model unchanged and untyped. Do
not widen the store, and do not extend `RELATION_TYPES`.**

Phase 2's evidence stands and this phase adds one more reason. The type is
discarded at `objects/envelopes.py:125-130`, before the export exists, so
widening `relations(src_id, dst_id)` would recover nothing. All 22 typed
relations authored in this repository are `relates-to`; `governs`, `implements`,
`tests`, `operates` and `supersedes` are authored zero times. A type a human
types and no tool derives is an assertion no tool can contradict.

The new reason: the documentation case does not supply the missing author
either. Documentation dependency is `provenance.sources`, a path list that
`objects/envelopes.py:156` preserves intact, and staleness reads that list.
Measured: the three probe pages carry `relations: []` and the entire dependency
answer worked. Registering the wiki adds zero typed edges, so the type column
would still hold one constant.

**What a reader checks.** Run the loop in `01-current-state.md` §3.3 over
`.hydra-framework/`. Count 22 `relates-to` and zero of everything else. Then
read `objects/envelopes.py:129` and confirm the export never sees a type.

**What would overturn it.** A generator rather than a human authoring an edge.
That is the unchanged condition from D7 and Phase 2 Q2.

### Decision 3: one new family, `Documentation`, and both of its lines are mandatory

**Decided: add one `ObjectFamily` entry and the matching `SEARCH_FAMILIES`
string. Phase 2's two-line price is confirmed, and the second line is not
optional.**

The family is required, not optional. Before it is registered, `ref check` fails
with `has unregistered hydra_id family prefix 'documentation'` and `has
unregistered kind 'documentation-page'`, naming
`hydra_engine.identity.object_families` as the point of edit
(`objects/references.py:86-93`, `identity/object_families.py:166`).

Phase 2 established that a page can be registered under an existing prefix with
no engine change at all, using `knowledge-slice`. That is rejected on vocabulary
grounds, not cost: a slice is a Markdown file beside a knowledge node
(`01-current-state.md` §4.1), and calling a wiki page one would give the
repository two meanings for a shipped word. That is A2's objection turned on
ourselves. One registry line is the cheaper honesty.

Phase 2's family-count claim is now verified where it could not be: `selftest`
runs 1633 tests and passes with both lines added. Phase 2 was right that no test
asserts a family *count* and no contract golden names a family. It missed a
different assertion, which is what the next paragraph is about.

The `SEARCH_FAMILIES` line was drafted out of this MVP as a retrieval decision
wearing a registration decision's clothes, and the probe overturned that.
`unit/knowledge/test_context_providers.py:81` asserts set equality between
`OBJECT_FAMILIES` names and `CONTEXT_PROVIDERS` families, and
`CONTEXT_PROVIDERS` is `KNOWLEDGE_FAMILY` plus one provider per `SEARCH_FAMILIES`
entry (`knowledge/context_providers.py:273-277`). A family with no context
provider fails `selftest`, with the `contract.goldens.test_core` selftest golden
cascading off it. The invariant is deliberate: every object family answers
`compile-context`, or it is not a family.

So the retrieval consequence is not severable from the registration decision and
is accepted with it. Measured: a registered page becomes a `compile-context`
candidate, and one page contributed 511 approximate tokens to a compiled packet.
The bound already exists at `DEFAULT_FAMILY_CANDIDATE_CAP = 8`
(`knowledge/context_providers.py:25`). What it will not show up in is
`measure-context`, which measures always-loaded surfaces only
(`01-current-state.md` §5.5), so the cost is real and invisible to the one
command that reports context size. That is the thing to watch after M1 lands.

One asymmetry worth carrying forward: registering a page puts it in the lexical
index regardless of the family (`knowledge/index_collection.py:82-85`,
title-only), because the search corpus is `.hydra-framework/`-rooted and
registration is a wiki page's only route in. `SEARCH_FAMILIES` gates the context
provider, not the index.

**What a reader checks.** Add the `ObjectFamily` entry, add a sidecar entry, run
`ref check` before and after the family line. Then add the family line alone and
run `selftest`: it fails on the family-to-provider parity assertion. Add the
`SEARCH_FAMILIES` string and it passes.

**What would overturn it.** A decision to relax
`test_every_object_family_has_exactly_one_context_provider`, which is a change to
a shipped invariant and belongs to whoever owns the context-provider contract,
not to this review.

### Decision 4: the manifest is an object sidecar in `surfaces/`, one file per wiki

**Decided: `.hydra-framework/surfaces/wiki/<wiki-name>.yaml`. The two candidates
collapse into one file.**

The Approved Plan offered "a contract in `surfaces/`" or "an object sidecar
under `.hydra-framework/`" as alternatives. They are not alternatives. Sidecar
discovery is schema-driven, not location-driven: `extract_sidecar_objects`
(`objects/discovery.py:64-76`) claims any `.yaml` under `.hydra-framework/`
whose top-level `schema:` matches, and `object_metadata_paths` rglobs the whole
tree. Measured: the same sidecar works at
`.hydra-framework/surfaces/wiki/hydra-framework.yaml` and at
`.hydra-framework/repo/object-sidecars.yaml`, with `ref index`, `ref check`,
`validate` and `validate-wiki` all passing from either location.

So put it in `surfaces/`, which is what that directory exists for.
`surfaces/README.md:101-105` asks for "a section here describing the contract,
not an empty directory"; this is that contract made machine-readable, in the
directory that owns it, rather than a second home for surface metadata.

One file per wiki rather than one for all, because `wiki scaffold <project>`
already creates additional wikis (`commands/wiki.py`) and a per-wiki file keeps
each wiki's diff local to itself. The wiki manifest is the first entry in its
own file and the pages follow it.

Is the manifest an object? Yes, and it costs nothing extra: it is one more
sidecar entry whose `path:` is the wiki's own root page. That is what makes
`managed:` and ownership queryable rather than prose, which is exactly what B3
and B4 asked for and `surfaces/README.md` does not have today
(`01-current-state.md` §6.1).

**What a reader checks.** Put a sidecar anywhere under `.hydra-framework/`, run
`ref index`, and confirm the object count rises. Then read
`objects/discovery.py:75-76` and confirm the schema string is the only gate.

**What would overturn it.** A validator that constrains `surfaces/` contents.
None exists: `validate` passed with a new YAML file in that directory.

### Decision 5: identity is `hydra_id` plus `uid`, and `validate-wiki` owns the wiki half of a move

**Decided: confirm Phase 2 on identity. Do not widen `stale_path_citations`.**

Phase 2 answered this from source. This phase moved an actual registered wiki
page. `move-object project-wiki/.../state-tiers.md project-wiki/.../tiers.md`
printed `Moved documentation/page/state-tiers` and then `Indexed 60 objects`:
`hydra_id` and `uid` untouched, the sidecar `path:` rewritten in place, the
registry reindexed by the command itself. No engine change was needed, and
`objects/moves.py:104` is why.

The named gap reproduced exactly. Four wiki pages carrying six links to the old
path were not reported by `move-object`, because `stale_path_citations`
(`commands/object_moves.py:30-45`) iterates `object_metadata_paths`, which is
`.hydra-framework/`-rooted. `validate-wiki` then failed on the next run and
named all six.

Widening `stale_path_citations` to the wiki is cut. It would duplicate a check
that already exists, already runs in CI (`.github/workflows/hydra.yml:62`) and
already produces a better message: `validate-wiki` names every broken link,
while `stale_path_citations` names files that mention a string. The MVP records
the split in the sidecar's own header comment instead: `move-object` owns object
identity, `validate-wiki` owns wiki links.

**What a reader checks.** Register a page, move it with `move-object`, and run
`validate-wiki`. The move succeeds silently and the link check fails loudly.

**What would overturn it.** A wiki page that cites another wiki page in a form
`validate_markdown_links` does not resolve. That is the 57 relative and
placeholder backtick fragments `01-current-state.md` §5.1 measured, which have
no defined resolution rule at all. That is a separate problem and is not made
worse by anything here.

## 3. Recommended object boundaries

What becomes an object:

| Thing | Object? | Why |
| --- | --- | --- |
| A wiki, as a named surface | Yes, one sidecar entry, `kind: documentation-wiki`, `path:` its root page | B3 and B4. Makes ownership and `managed:` queryable |
| A wiki page that declares sources | Yes, one sidecar entry, `kind: documentation-page` | D2 and D13. This is what `citers_of_source_path` needs |
| A wiki page that declares no sources | No | An object with `provenance.sources: []` costs a registry entry, a digest under CI, and a reindex per edit, and answers no question. Register a page when it earns one |
| A section or heading | No | The object model is file-keyed in three places: one `path` and one `digest` per row (`objects/store_schema.py:16-41`), a whole-file digest (`objects/envelopes.py:156`), and extension-driven discovery (`commands/object_moves.py:92-97`). Q7 |
| A claim | No | Same, and self-deferred by the proposal. D8 |
| A relation type | No | Decision 2 |
| A `surfaces/` contract section | Not separately | It is the sidecar. Decision 4 |

The sidecar entry shape, all fields already contractual:

```yaml
schema: hydra-framework.object-sidecar.v1
title: Hydra Framework Wiki Surface
objects:
  wiki:
    hydra_id: documentation/wiki/hydra-framework   # `hydra://` scheme spelled in the real file
    uid: <uuid4>
    schema_version: 3
    kind: documentation-wiki
    title: Hydra Framework Wiki
    status: active
    scope: repo-local
    path: project-wiki/hydra-framework/hydra-framework.md
    owners:
      team: hydra
    managed: true
    provenance:
      sources: []
    relations: []
  page-state-tiers:
    hydra_id: documentation/page/state-tiers
    uid: <uuid4>
    schema_version: 3
    kind: documentation-page
    title: State Tiers
    status: active
    scope: repo-local
    path: project-wiki/hydra-framework/concepts/state-tiers.md
    owners:
      team: hydra
    checked_on: '2026-09-14'
    provenance:
      sources:
        - .hydra-framework/core/placement-rules.md
        - .hydra-framework/repo/knowledge/state-tiers.md
        - .hydra-framework/surfaces/README.md
      source_digests:
        - source: .hydra-framework/core/placement-rules.md
          digest: sha256:...
    relations: []
```

Five envelope fields are mandatory and carry no defaults: `kind`, `title`,
`status`, `scope`, `owners` (`identity/schema_versions.py:35`,
`objects/envelopes.py:132-138`). `relations` and `provenance.sources` are
mandatory and may be empty, and `objects/references.py:69-78` says so in the
finding text specifically so an agent does not invent filler.

Three fields are read by the new reader only and are dropped by the envelope
builder: `managed`, `checked_on`, `provenance.source_digests`.
`objects/envelopes.py:103-166` builds a fixed record and nothing validates
unknown keys, so they are parsed and discarded on the object path while the
audit reads them straight out of the sidecar YAML. This is deliberate and is the
reason the MVP needs no envelope change. It is also the one thing about this
shape a future reader will find surprising, so the sidecar header says it.

`scope: repo-local` is correct and is not authority. `LEGAL_SCOPES` is
`("base-seed", "common-seed", "repo-local")` (`knowledge/contracts.py:5`) and
means seed distribution. A wiki page about this repository's Hydra is not seed
material. `tier` is derived, never declared: every path under `project-wiki/` is
`external` (`objects/envelopes.py:27-34`), confirmed by `explain-path`.

Two things this boundary deliberately does not decide, because nothing consumes
them yet: `doc_kind`, `audiences` and `outputs` (D4, inert until a consumer
exists), and per-wiki `sources:` naming knowledge spaces (B5, premature with one
space).

## 4. The MVP

### 4.1 Scope, cut from section 33

Section 33's nine items, with Phase 2 §2.7 row G4's mapping:

| # | Section 33 item | Phase 2 row | In MVP | Why |
| --- | --- | --- | --- | --- |
| 1 | A named `hydra-framework` wiki | B3, missing but valuable | **in** | M1. One sidecar entry |
| 2 | Explicit wiki ownership and root path | B4, missing but valuable | **in** | M1. Same entry |
| 3 | Page-to-source dependency metadata | D12, partially existing | **in** | M1. The contract exists; it has never been applied to a page |
| 4 | A page-level `docs audit` | E5, missing but valuable | **in**, cut and renamed | M3, as `wiki audit`. Q18 settles the namespace. Scope cut to what M1 makes answerable |
| 5 | Generated CLI reference | E14, partially existing | out | Input incomplete: `CommandMetadata` carries no description and no per-argument help (`cli/command_metadata.py:314-322`), and reports 70 of 74 commands (`:340`). Widening the metadata is separate work with its own value |
| 6 | Generated architecture or capability graph | E1/E3, missing but valuable | out | Section 0 correction. Documentation impact runs through `provenance` and `citers_of_source_path` already answers it. The transitive reverse walk remains a real gap in the object graph and is not on this path |
| 7 | CI warning when an owning source changes | E12, partially existing | **in** | M4. As an advisory note, never a `Finding`. Q11 |
| 8 | Static website build | F1, missing and premature | out | Deferred whole by the task record's Goal, and premature until items 1, 3 and 4 produce something to show |
| 9 | Separation of existing from planned | A5, existing | out as a build item | It is D6, and it is the rule this review operated under. Nothing to build |

Five items in, four out. Phase 2 recommended cutting two; this phase cuts four.

### 4.2 The five MVP items

#### M1: the wiki surface sidecar

**Outcome.** `.hydra-framework/surfaces/wiki/hydra-framework.yaml` exists, declares
the wiki and the 23 pages `source-map.md` already covers, and every page entry
carries `provenance.sources`, `provenance.source_digests` and `checked_on`.

**Dependencies.** M2 must land first or `ref check` fails on an unregistered
family prefix.

**Acceptance.** `ref index` reports 57 plus the registered count. `ref check`,
`validate`, `validate-wiki`, `validate-package-docs` and `reclaim
--fail-on-findings` all pass. `explain-path` on any cited source names the page
that cites it. `explain-path` on any registered page reports `Tier: external`
and the object.

**Tests.** None new. This is data, and validator 11 already tests it on every
`validate` run. A contract golden is wrong here: the object count would change
with every page added.

**Migration.** Q23's three steps, with the sequencing Phase 2 recommends. The 23
Source-Map-covered pages first, because their sources are already written down
and already link-checked. The other 17 pages are a separate bounded authoring
pass, and are not MVP scope. Of `source-map.md`'s 41 distinct non-wiki targets,
33 are files and convert mechanically; the 8 directories do not.

**Directory sources are refused, not expanded.** `knowledge fingerprint` already
refuses any source that is not exactly one existing file
(`commands/knowledge_fingerprint.py:112-114`) and the digest branch requires
`path.is_file()` (`knowledge/freshness.py:306`). Adding a per-directory manifest
digest or a fingerprint-time expansion would give the repository two rules for
what a source is. The citation names files, or it is not a `provenance.sources`
entry. The eight directory rows stay in `source-map.md` prose, which is what that
page is for.

**Complexity.** Authoring, not engineering. Roughly 24 lines of YAML per page
with digests, so about 550 lines for 23 pages, mostly generated by M5. The real
cost is deciding sources for pages `source-map.md` does not cover, which is why
they are out of MVP scope.

#### M2: the `Documentation` object family

**Outcome.** One `ObjectFamily` entry in `identity/object_families.py`, with
`id_prefixes=("documentation",)` and `kinds=("documentation-wiki",
"documentation-page")`, plus `"Documentation"` in `SEARCH_FAMILIES`
(`knowledge/context_providers.py:28`).

**Dependencies.** None.

**Acceptance.** `ref check` accepts a `documentation/` id.
`unregistered_family_tokens` returns empty for both kinds. `selftest` passes,
which requires both lines: `unit/knowledge/test_context_providers.py:81` asserts
every object family has exactly one context provider, and the family line alone
fails it.

**Tests.** One case in `unit/identity/test_object_families.py` asserting that
both kinds resolve to `Documentation` and that no token is claimed by two
families, which is the invariant `family_for`'s two-pass resolution depends on
(`unit/identity/test_object_families.py:42`). The family-to-provider parity test
already exists and needs no change.

**Complexity.** Six lines plus one test. Verified: 1633 tests pass with both
lines; 2 fail with only the family line.

#### M3: `wiki audit`

**Outcome.** `hydra.py wiki audit [--wiki <name>] [--json]` reads every wiki
sidecar under `.hydra-framework/surfaces/wiki/` and reports, per page: sources
whose digest no longer matches, sources that no longer exist, and pages with no
declared sources. Exit 0 always in the MVP.

**Dependencies.** M1 for data. Nothing else. It is a reader.

**Acceptance.** With every source unchanged, it reports zero stale pages. Edit
one source and it names that page and that source. Delete a source and it names
the page. It runs with no object store and with `HYDRA_QUERY_STORE=off`, because
it reads YAML and files, not the store.

**Tests.** `unit/commands/test_wiki.py` gains cases for clean, stale, missing
source, and no sidecar present. One contract golden, `wiki-audit.json`, on a
fixture rather than on the repository's own wiki, so adding a page does not
churn a golden.

**Migration.** None. New command.

**Complexity.** Small, and this is the measured claim rather than an estimate.
The probe did the whole thing in about 20 lines by calling
`stale_provenance_sources` (`knowledge/freshness.py:287-314`) with the sidecar's
`provenance` mapping and its `checked_on`. `knowledge/freshness.py` needs no
change: it already takes a plain `Mapping`, and `knowledge/candidates.py:84-88`
is simply its only caller today. Budget roughly 120 lines with argument parsing,
JSON output and the report shape, plus a `wiki` subparser entry.

**What it deliberately does not do.** It does not check `hydra://` references in
prose, which `ref check` does not do for sidecar-registered files either
(`01-current-state.md` §2.4). It does not check links, which `validate-wiki`
owns. It does not check coverage, which needs E8's data and has none. Nine of the
13 audit categories in the proposal's §20 are out; the four that ship already
ship through `ref check` (`02-gap-analysis.md` E7).

#### M4: staleness as an advisory note

**Outcome.** `validate` and `doctor` print stale registered pages as an advisory
note after the verdict, beside the seven notes already there
(`cli/dispatch.py:133-145`).

**Dependencies.** M3's reader.

**Acceptance.** A stale page appears in `validate`'s output after the `ok` line
and `validate` still exits 0. CI does not fail on it.

**Tests.** One case in `unit/commands/test_validation.py`. The existing
`core-validate.json` golden covers note placement.

**Why not a `Finding`.** `knowledge/package_checks.py:148-156` states the reason
in the engine's own words and it transfers to pages unchanged: every `Finding`
makes `validate` exit nonzero, there is no warning tier, and a deliberately
stale page must not be a hard failure. Q11. The proposal's four severity levels
are the wrong answer to this and are deleted outright, see section 5.

**Complexity.** Roughly 20 lines, one note builder following the shape of the
existing seven.

#### M5: `wiki fingerprint`

**Outcome.** `hydra.py wiki fingerprint --page <id>` rewrites one page entry's
`provenance.source_digests` and `checked_on` from current file digests, the way
`knowledge fingerprint --unit <id>` does for a unit.

**Dependencies.** M1.

**Acceptance.** After an intentional source change, `wiki fingerprint` followed
by `wiki audit` reports the page clean, with no prose change to the page. It
refuses any source that is not exactly one existing file, with the same message
shape as `commands/knowledge_fingerprint.py:112-114`.

**Tests.** `unit/commands/test_wiki.py`: rewrite, idempotent rewrite, refusal on
a directory source, refusal on a missing source.

**Why this is not free.** `replace_source_digests`
(`commands/knowledge_fingerprint.py:68-93`) cannot be reused. It requires
Markdown frontmatter delimited by `---` and a `provenance:` key at indent 0; a
sidecar entry's `provenance:` is nested at indent 4 inside `objects.<name>`. The
writer is new. This is the one place the MVP pays for choosing the sidecar over
frontmatter, and it is the right trade: the alternative pays an engine root
change and a wider `ref check` scan on every wiki page forever.

**Complexity.** Roughly 80 lines. Rewriting one entry in a YAML file it also
reads, preserving the rest of the file.

#### M6: automatic reindex in `hook-post-edit`

**Outcome.** When the edited path is a registered object path, `hook-post-edit`
runs `ref index` before its existing checks.

**Dependencies.** M1, or it never fires.

**Acceptance.** Edit a registered wiki page through an agent tool and `ref check`
stays clean with no manual step. Edit an unregistered file and the registry is
not rewritten. The hook stays inside its 30 s budget: measured 0.14 s for the
no-op path plus 0.64 s for `ref index`.

**Tests.** `unit/commands/test_hooks.py`: registered path reindexes, unregistered
path does not, missing registry is not created. One `agent-hooks-hook-post-edit`
golden for the registered-path case.

**Migration.** None, but name the contract change in the module docstring: the
wired hook writes one derived tracked file, `cognition/graph/registry.yaml`,
where it previously only reported.

**Why the membership guard.** Reading `registry.yaml` and testing path
membership is cheap and avoids rewriting the registry on every unrelated edit.
Without the guard the hook would run `ref index` on every Markdown write in the
repository.

**Complexity.** Roughly 40 lines plus tests.

### 4.3 Sequence, and what CI looks like after

M2, then M1, then M3, then M5, then M6, then M4. M2 first because M1 fails
`ref check` without it. M5 before M6 because there is no point automating the
reindex until pages can be re-verified. M4 last because it is the only item that
changes what every `validate` run prints.

CI gains nothing new. `.github/workflows/hydra.yml` runs `doctor` at `:39`,
which carries validator 11, which is what enforces a registered page's digest
freshness. `wiki audit` is not a CI step in the MVP, by Q11. Adding it as a step
later is one line, and only after someone decides what it should do about a page
that is stale on purpose.

Total estimated new engine code: roughly 260 lines plus tests, across three
modules, with no schema change, no store change, no envelope change, and no
change to `knowledge/freshness.py`.

## 5. Challenge (deliverable F)

### 5.1 What the proposal over-engineers

- **The 33-entry candidate object family list (§14, D5).** Families are one
  registry line; members are the expensive part. The measured counter-evidence is
  in the repository already: the Python handler roots at `engine/src` and turned
  3 of roughly 200 engine modules into objects, and the Telemetry family has
  shipped with a context provider and zero members since it was added.
- **The 17-relation controlled vocabulary (§15, D6).** Six types exist and are
  validated; five of the six are authored zero times. Adding eleven more to a set
  where five are unused is vocabulary, not capability.
- **The nine-value epistemic category table (§12, C7).** `certainty:` is an open
  field with five authored values and four referenced by code. A nine-value
  closed table is a schema change to fix a problem nobody has reported.
- **Claim-level tracking (§16, D8).** Correctly self-deferred by the proposal to
  its own phase 6, and it should stay there. Page-level staleness has never run
  in this repository; there is no measurement saying it is too coarse.
- **The eight graph views (§19, E2).** Seven are filters over one YAML export
  that already carries every field they would show.
- **Per-wiki, per-document-kind policy YAML (§24 stage 3, E13).** One wiki, no
  document kinds. The policy file has one row.
- **The website, sections 25 and 26 entire (F1 to F6).** Deferred whole by the
  Goal, and every listed feature renders data that does not exist.
- **Its own review, which is to say this one.** Three artifacts totalling about
  2,700 lines have produced a decision whose implementation is measured at about
  260 lines of engine code. That ratio was worth paying once, because the
  proposal asked for a nine-phase program and the measurement is what shrank it.
  It is not a template for the next candidate.

### 5.2 Which naming misleads

- **`projection` (§4, §27).** The repository's word is `surface`, defined at
  `surfaces/README.md:3-6` with the exact contract §27 describes. A second noun
  for one concept, in a codebase whose family registry argues at length against
  precisely that (`identity/object_families.py:45-51`, which chose
  `engine-module` over `runtime-module`).
- **`docs` as a CLI namespace (§20, Q18).** The CLI already spells this corpus
  `wiki`, with `wiki scaffold` and `validate-wiki`. `docs audit` would be a
  second namespace over the same 40 files.
- **`wiki://`, `claim://`, `rule://`, `documentation://`, `space://`, `test://`
  (§5, §6, §9, §13, §16, §29, A4).** `HYDRA_ID_RE` recognizes `hydra://` and
  nothing else, and `hydra_id_prefix` returns `""` for any other scheme
  (`identity/hydra_ids.py:10-11`, `:31-39`). An id in one of these schemes would
  be invisible to `ref check`, `ref index`, `explain-path` and the store. The
  existing scheme already carries the distinction in its first segment.
- **`scope` for authority levels (§12, C8).** `scope` is a mandatory envelope
  field meaning seed distribution, with three legal values
  (`knowledge/contracts.py:5`). Reusing the word on the same field collides;
  reusing it on a different field gives one word two meanings.
- **`last_verified.commit` (§18).** It would be written and never read.
  `knowledge/freshness.py:305-308` returns before the commit rule whenever a
  digest exists, and all 27 sources across all 7 units are digested. A field
  named "last verified" that no verification consults is worse than no field.
- **"Repository intelligence" for the whole proposal.** What is actually missing
  is one sidecar and one reader. The name sets the expectation that a new
  subsystem is required, and that expectation is what produced a nine-phase plan.
- **"Spaces compose rather than inherit" (§10).** The shipped model is single
  parent-chain inheritance with a per-key ancestor trace
  (`knowledge/nodes.py:239-265`). Stating the opposite as a principle describes a
  system this repository does not have.

### 5.3 Which abstractions duplicate existing Hydra concepts

| Proposed | Already is |
| --- | --- |
| Projection (§27) | Surface, `surfaces/README.md:3-6`, and the working mechanism is `providers/reclaim.py:98-146` |
| Page-to-source dependency with digests (§18) | `provenance.sources` + `source_digests` + `checked_on`, `knowledge/units.py:30-48` |
| A documentation staleness engine (§18, §20) | `stale_provenance_sources`, `knowledge/freshness.py:287-314`. Measured this phase to work unchanged on a sidecar block |
| Authored / generated / hybrid maintenance (§17) | `classify_surfaces`, `providers/reclaim.py:98-146`, four states, CI-enforced |
| Bounded generated Markdown regions (§17.3) | `ensure_generated_adapter_ignore_block`, `providers/git_ownership.py:47-72`, idempotent, marker-bounded, already tested |
| `docs reconcile` bounded agent package (§22) | `delegation-brief`, which already emits a read-first brief with stop rules |
| Four severity levels (§20) | `Finding` plus advisory notes after the verdict, `finding.py:38-42` and `cli/dispatch.py:133-145`. A deliberate two-tier model |
| Explicit non-impact acknowledgment (§23, §34.3) | `knowledge fingerprint --unit` and `bindings verify --accept`, `knowledge/bindings.py:193-202` |
| Deterministic conflict resolution (§12) | `unit_kind: divergence`, which records a conflict rather than resolving it, `knowledge/package_checks.py:214-229` |
| A stable JSON graph contract (§25) | `cognition/graph/registry.yaml`, already derived, already validated by validator 11. It needs a JSON rendering, not a second export |

### 5.4 What should be deleted outright, not deferred

Deferral is the right answer for something premature. These are not premature.
Each contradicts a contract this repository has already decided, and leaving them
in the proposal as "later" invites a future agent to build them.

| Delete | Contradicts |
| --- | --- |
| `projection` as a concept and a noun (§4, §27, A2) | `surfaces/README.md:3-6`. Use `surface` |
| Per-concept URI schemes (§5, §6, §9, §13, §16, §29, A4) | `identity/hydra_ids.py:10-11`. Use `hydra://<first-segment>/` |
| "Spaces compose rather than inherit" (§10, C3) | `knowledge/nodes.py:239-265`. Replacing it is a Knowledge v3 schema change with no demonstrated need |
| Authority scopes on `scope` (§12, C8) | `knowledge/contracts.py:5`, `identity/schema_versions.py:35` |
| The 17-relation vocabulary (§15, D6) | `knowledge/contracts.py:6`, and every one of them would be discarded at `objects/envelopes.py:129` |
| Four severity levels (§20, E6) | `finding.py:38-42`, `knowledge/package_checks.py:148-152`. It either bypasses `Finding` or changes it for all 19 validators |
| `last_verified.commit` (§18) | `knowledge/freshness.py:305-308` |
| `docs` as a CLI namespace (§20, Q18) | The shipped `wiki` namespace |
| The premise that this is a wiki problem | Measured: four of the eight drift items Phase 2 §Q25 found are inside the engine, in files that are themselves Hydra objects. A mechanism scoped to `project-wiki/` would have caught none of them |

That last row is the one that should change the proposal's framing rather than
its component list. `cli/parser.py:12` claims ten shim commands where there is
one, `checks/validator_registry.py:21` claims ten checks where there are 19,
`objects/object_handlers.py:45` claims two engine-module objects where there are
three, and `commands/references.py:96` attributes `ref rdeps` to a table no query
reads. The dependency model this MVP builds points at
`.hydra-framework/core/placement-rules.md` exactly as readily as at a wiki page,
because `provenance.sources` is a path list with no wiki in it. That property is
free and should be kept.

Deferred with a condition, rather than deleted:

- Typed relations reaching the store (D7): revisit when a generator authors an
  edge.
- The transitive reverse relation walk (E3): a real gap in the object graph, off
  the documentation critical path.
- Generated CLI reference (E14): revisit when `CommandMetadata` carries
  descriptions and covers all 74 dispatched commands.
- Portable external spaces (C6) and business rules as objects (D15): out of scope
  by the Goal, and nothing in these boundaries blocks them. A space version is a
  field on a space manifest, and a rule object is a family entry; neither touches
  the wiki sidecar.

## 6. Unestablished

1. **Whether `hook-post-edit` writing a tracked file is acceptable to the
   maintainer.** M6 is measured viable and is a contract change. It is a
   judgment, not a measurement, and Phase 4 owns it.
2. **Whether 23 pages is enough to validate the model.** Source Map covers 23 of
   40 pages. Nothing establishes how many registered pages it takes before the
   audit's output is worth reading.
3. **The false-positive rate of page-level digest staleness.** Risk §34.3 asserts
   one. Nothing has measured it, because no page-level staleness has ever run.
   M3 is what would produce the measurement.
4. **Whether `ref index` stays inside the hook budget as the object count
   grows.** 0.64 s at 60 objects. `problems.md` P5 and P12 own index scaling and
   are out of scope here.
5. **Whether the 17 pages Source Map does not cover have sources worth
   declaring.** Establishing them is authoring work against the implementation,
   and it is deliberately outside the MVP.

## 7. Gate evidence

Commands run for this phase, on `main` at 7801b1d, in the working tree:

- `ref store rebuild` -> `rebuilt from 57 object(s)`; `status: fresh`, `export
  digest: agrees with the export`, `objects: 57`, `refs: 108`, `relations: 30`,
  `provenance: 50`, `documents: 366`
- `validate` -> `ok`, five advisory notes

In an isolated `git clone` under the session scratchpad, never the working tree:

- Baseline `selftest` -> **1633 tests, OK**, after `export-adapters`
- `selftest` with the `Documentation` family registered -> **1633 tests, OK**
- `selftest` with the family plus three registered wiki pages -> **1633 tests,
  OK**
- `selftest` with the family line but no `SEARCH_FAMILIES` entry -> **2
  failures**: `unit.knowledge.test_context_providers`
  `test_every_object_family_has_exactly_one_context_provider`, and
  `contract.goldens.test_core` `test_selftest_happy_path` cascading off it
- `ref index` -> `Indexed 60 objects`; `ref check` -> `ok (60 objects)`
- `validate`, `validate-wiki`, `validate-package-docs`, `reclaim
  --fail-on-findings` -> all pass
- `ref store rebuild` -> `rebuilt from 60 object(s)`, `provenance: 57`, no schema
  change
- `explain-path` resolving in both directions, store-backed
- `move-object` on a registered wiki page -> id and uid preserved, sidecar
  rewritten, registry reindexed; `validate-wiki` then failing on six wiki links
  the move did not report
- One appended prose line in a registered page -> `ref check` and `validate` both
  fail with `has stale digest`
- `stale_provenance_sources` over the sidecar's `provenance` block -> clean, then
  correctly stale after one source edit, with no change to
  `knowledge/freshness.py`

The decisions in section 2 each name what a reader checks and what would
overturn them. The MVP in section 4 names outcomes, dependencies, acceptance
criteria, tests, migration and complexity per item, with complexity measured
rather than estimated for M3. The challenge in section 5 names what the proposal
over-engineers, which naming misleads, which abstractions duplicate existing
Hydra concepts, and what to delete rather than defer.
