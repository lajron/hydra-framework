# Task: repository-documentation-dependency-mvp

Status: active
Owner: milosdenic-dev-gmail-com
Created: 2026-09-14
Updated: 2026-09-14

## Goal

Give this repository a mechanical answer to the question it can already answer
for every knowledge unit and cannot answer for any documentation page: *did a
source this page depends on change since the page was last verified?*

The gap is P16 in
`.hydra-framework/repo/knowledge/spaces/hydra-framework/problems.md`. The
mechanism is authorized, not proposed. It was reviewed across four phases in
`.hydra-framework/evolution/candidates/repository-intelligence-review.md`, whose
`03-architecture-and-mvp.md` section 4 defines the MVP and whose `04-decision.md`
section 1 amends it with the maintainer's five decisions.

**This record owns the build. It does not own the design.** Every boundary below
is settled and each names the evidence that settles it. Reopen one only with
evidence that overturns it, and record the correction in place in Confirmed
Decisions the way the review's phases did.

### Out of scope, deliberately

- The nine components deleted outright in `03-architecture-and-mvp.md` section
  5.4. They are decided against, not deferred. Do not build them.
- The four section 33 items cut from the MVP: the generated CLI reference, the
  graph view, the website, and "separation of existing from planned".
- Typed relations reaching the store, and the transitive reverse relation walk.
  Both deferred with a stated condition in section 5.4.
- Rewriting wiki prose. This work makes drift detectable. Correcting it is
  separate work that the audit scopes.
- P5 and P12. Index scaling is owned elsewhere and must not be re-litigated here.

## Confirmed Decisions

Each is settled by the review. The citation is where to check it, not where to
reargue it.

### D1: A wiki page becomes an object, by object sidecar

Sidecar under `.hydra-framework/surfaces/wiki/`, `schema:
hydra-framework.object-sidecar.v1`. Not frontmatter: 0 of 40 wiki pages carry
frontmatter, and a second handler root in
`object_document_paths(hydra_root)` (`objects/object_handlers.py:145`) would also
widen what `ref check` scans for `hydra://` references
(`objects/references.py:121-136`).

`project-wiki/` is already a recognized sidecar root in two places,
`objects/discovery.py:48` and `objects/moves.py:104`, which is why `move-object`
works on a registered page with no engine change. Sidecar discovery is
schema-driven rather than location-driven (`objects/discovery.py:64-76`).

Evidence: `03-architecture-and-mvp.md` Decision 1 and section 1.

### D2: One `Documentation` family, deliberately not retrievable

`ObjectFamily(name="Documentation", id_prefixes=("documentation",),
kinds=("documentation-wiki", "documentation-page"))` in
`identity/object_families.py`. Without it, `ref check` fails on an unregistered
prefix and kind.

The family is **not** added to `SEARCH_FAMILIES`
(`knowledge/context_providers.py:28`). It gets an explicit non-retrieving context
provider instead. `unit/knowledge/test_context_providers.py:81` asserts name set
equality between `OBJECT_FAMILIES` and `CONTEXT_PROVIDERS`, so it requires a
provider *entry*, not a retrieving one. A provider returning
`ProviderOutput(candidates=[])` satisfies it.

This is the boundary the whole design defends, in the maintainer's words: the
wiki is the surface that explains the framework to humans, and the knowledge
spaces are what is written for agents. Wiki prose does not enter agent context
packets.

Measured in an isolated clone at 7801b1d: `selftest` 1633 tests OK;
`compile-context` returns 0 wiki candidates both by default and with
`--include-family Documentation` explicitly requested; `knowledge-search "state
tiers"` returns the registered page as a 3-token title-only stub beside the
knowledge unit's 71 tokens of content.

Two structural reasons no other family leaks one: `_family_search_collector`
skips any result where `family_for(doc.hydra_id, doc.kind) != family`
(`knowledge/context_providers.py:253`), and `_document_for_object`
(`knowledge/index_collection.py:168-170`) indexes a registered object as a
title-only document with empty body fields.

**This overturns `03-architecture-and-mvp.md` Decision 3**, which held the
`SEARCH_FAMILIES` line mandatory and the 511-token retrieval cost inseparable
from registration. The correction and its probe are in `04-decision.md` section
2.1. Phase 3's measured 511 tokens is a cost of the route it chose, not of
registration.

Reversal, if this is ever wanted: move `"Documentation"` from
`NON_RETRIEVED_FAMILIES` to `SEARCH_FAMILIES`. One line, no data migration.

### D3: `relations` stays untyped, and the store is not touched

The relation type is discarded at `objects/envelopes.py:125-130`, before the
export exists, so widening `relations(src_id, dst_id)` would recover nothing. All
22 typed relations authored in this repository are `relates-to`; `governs`,
`implements`, `tests`, `operates` and `supersedes` are authored zero times.

Documentation dependency runs through `provenance.sources`, not `relations`, so
registering the wiki adds zero typed edges and supplies no new author for a type
column. Registered pages carry `relations: []`.

No schema change, no store change, no envelope change, and no change to
`knowledge/freshness.py`.

Evidence: `03-architecture-and-mvp.md` Decision 2.

### D4: Identity is `hydra_id` plus `uid`

`move-object` preserves both and rewrites the sidecar `path:` itself, confirmed
by an actual move on a registered wiki page in a clone. Widening
`stale_path_citations` is cut: `validate-wiki` already owns the wiki half of a
move and names every broken link. Note the measured gap, because it will bite
during M1b: `move-object` reports no broken wiki links itself, and
`validate-wiki` is what catches them afterwards.

Evidence: `03-architecture-and-mvp.md` Decision 5.

### D5: A source is exactly one existing file. Directories are refused

`commands/knowledge_fingerprint.py:112-114` refuses any source that is not
exactly one existing file, and the digest branch at `knowledge/freshness.py:306`
requires `path.is_file()`. Supporting directories would give the repository two
rules for what a source is.

Measured reason it would not work anyway: `command-surface.md` cites
`.hydra-framework/engine/tests` (605 files) and
`hydra_engine/commands` (54 files). Any change to any of those 659 files would
mark the page stale, so it would be stale from the first day and never clear.

**The eight directory rows in `source-map.md` are converted case by case, not
left as prose.** Where the directory was shorthand for a handful of modules, name
the files: `architecture/context-retrieval.md` has three sections, on routing, on
freshness, and a worked example, and depends on roughly four modules of the
`knowledge` package's 33, not on `migration_v2.py` or `bindings.py`. Where the
page genuinely means the whole directory, `engine/tests` being the clear case and
`.hydra-framework/capabilities` (47 files) likely another, leave prose and record
the citation as unverified rather than implying coverage that does not exist.

Evidence: `04-decision.md` Decision D, which amends
`03-architecture-and-mvp.md` M1's "the eight directory rows stay in
`source-map.md` prose".

### D6: The staleness signal is delivered at commit and reported in CI, never as a bare advisory note

`03-architecture-and-mvp.md` M4 made staleness a sixth advisory note after
`validate`'s verdict. That delivery is replaced. Its reasoning about `Finding` is
kept intact: no `Finding` is constructed, because
`knowledge/package_checks.py:148-156` gives every `Finding` a nonzero exit and
there is no warning tier, and a deliberately stale page must not block work.

What replaces it:

1. A `post-commit` hook report. One message per commit, naming the pages whose
   sources changed in that commit, and printing the exact `wiki fingerprint`
   command that clears each. Written to be executable by an agent and readable by
   a human, following the pattern `ref check` already uses when it prints `rerun
   'hydra.py ref index'`.
2. `wiki audit` as its own named CI step that reports stale pages and **exits
   0**.

Why a bare note was rejected, measured on `main` at 7801b1d: `knowledge stale` is
not a CI step at all (`.github/workflows/hydra.yml` runs `export-adapters`,
`selftest`, `doctor`, and a tracked-private-state check); `knowledge stale`
reports 2 of 7 units stale, with `units/build-status.md` at `checked_on:
"2026-09-10"` and its source `cli/command_metadata.py` committed 2026-09-12; and
`doctor` already prints five standing advisory notes, one reading "46 days old;
recheck provider compatibility" and another reporting 17,791 telemetry events
against a 5,000-line advisory. The channel already carries unread messages.

Why commit rather than edit: an edit-time report prints on every `Write` and
`Edit`, injecting a report into an agent's context on every tool call, to an
audience that cannot act on it. And `.hydra-framework/hooks/pre-push` already
records this repository's position, that push is the guarded boundary on purpose
because "pre-commit fires constantly, and blocking commits on bookkeeping is how
a team ends up passing `--no-verify`". The commit hook is a report, not a gate,
consistent with the four `post-*` hooks that are already best-effort and never
block.

Why CI carries it too: `pre-push` also records the rule, that "a check that lives
solely in an uninstalled hook is not a check".

Evidence: `04-decision.md` Decision B2 and section 2.2.

### D7: All 40 wiki pages register, and the 17 Phase 3 excluded are two different populations

`03-architecture-and-mvp.md` M1 scoped registration to the 23 pages
`source-map.md` covers. That widens to 40, because the per-page cost that bounded
it was retrieval and D2 removes it.

The 17 pages Phase 3 left out split cleanly, measured in this review's Phase 4:

- **Seven navigation pages**: `project-wiki/home.md`, and `concepts/concepts.md`,
  `extending-hydra/extending-hydra.md`, `operations/operations.md`,
  `reference/reference.md`, `reference/source-map.md`, `start-here/start-here.md`
  under `project-wiki/hydra-framework/`. They run 17 to 33 lines, are almost
  entirely links, and carry 0 or 1 path citations each. They make no claim about
  behavior, so they have no sources to declare, permanently. They register with
  `provenance.sources: []`, which buys identity, `move-object` and `explain-path`
  at no staleness cost.
- **Ten content pages never mapped**: `architecture/engine.md` (114 lines),
  `reference/glossary.md` (110), `working-with-hydra/first-task.md` (101),
  `architecture/object-context-model.md` (67), `extending-hydra/intake.md` (61),
  `working-with-hydra/task-lifecycle.md` (58), `start-here/new-contributor.md`
  (56), `architecture/execution-flow.md` (52),
  `architecture/execution-stack.md` (41),
  `working-with-hydra/private-workspace.md` (38).

So coverage today is 23 of 33 content pages, not 23 of 40.

The ten are their own step, M1b, because establishing their sources means reading
each page against the implementation and deciding which files own each claim.
That is analysis, not the transcription M1 is. **A page carrying wrong sources is
worse than one carrying none**, because it claims a verification it does not
have.

Known consequence, accepted: `wiki audit`'s "no declared sources" category
permanently holds the seven navigation pages, and nothing distinguishes
"deliberately has none" from "not yet established". No field is added for this
now. Revisit only if the category becomes noise.

Evidence: `04-decision.md` Decision C.

### D8: This is not a wiki problem, and the mechanism must not be scoped to one

Four of the eight drift items measured during the review are inside the engine,
in files that are themselves Hydra objects. Re-verified at Phase 4:
`checks/validator_registry.py:21` describes `validate`/`doctor`'s "ten checks"
where `len(VALIDATORS)` is 19. Also recorded by Phase 1: `cli/parser.py:12`
claims ten shim commands where there is one, `objects/object_handlers.py:45`
claims two engine-module objects where there are three, and
`commands/references.py:96` attributes `ref rdeps` to a table no query reads.

`provenance.sources` is a path list with no wiki in it, so the mechanism points at
`.hydra-framework/core/placement-rules.md` exactly as readily as at a wiki page.
**That property is free. Do not build anything that assumes a `project-wiki/`
prefix.** Registering canonical files is outside this MVP's scope, but nothing
here may make it harder.

Evidence: `03-architecture-and-mvp.md` section 5.4, last row.

## Approved Plan

Seven items, sequenced. `03-architecture-and-mvp.md` section 4.2 holds the full
outcomes, dependencies, acceptance criteria, tests, migration notes and
complexity per item; only the amendments are restated here. Each item is a gate:
it lands green before the next begins.

### M2: the `Documentation` object family

One `ObjectFamily` entry, plus the non-retrieving context provider per D2, **not**
a `SEARCH_FAMILIES` string.

First, because M1 fails `ref check` on an unregistered family prefix without it.

Acceptance: `ref check` accepts a `documentation/` id;
`unregistered_family_tokens` returns empty for both kinds; `selftest` passes. One
new case in `unit/identity/test_object_families.py` asserting both kinds resolve
to `Documentation` and no token is claimed by two families. Add a case asserting
the `Documentation` provider yields zero candidates, since that is now a
deliberate contract rather than an accident.

Roughly 10 lines plus tests.

### M1: the wiki surface sidecar, 30 pages

`.hydra-framework/surfaces/wiki/hydra-framework.yaml` declares the wiki plus the
23 pages `source-map.md` covers and the 7 navigation pages with
`provenance.sources: []`, per D7. The 23 carry `provenance.sources`,
`provenance.source_digests` and `checked_on`.

Convert the eight directory citations per D5 as part of this step, not after it.

Acceptance: `ref index` reports 57 plus the registered count; `ref check`,
`validate`, `validate-wiki`, `validate-package-docs` and `reclaim
--fail-on-findings` all pass; `explain-path` on any cited source names the page
citing it; `explain-path` on any registered page reports `Tier: external` and the
object.

No new tests. This is data, and validator 11 tests it on every `validate` run. A
contract golden would be wrong here: the object count changes with every page
added.

Authoring, not engineering. Roughly 24 lines of YAML per sourced page.

### M3: `wiki audit`

`hydra.py wiki audit [--wiki <name>] [--json]`. Reads every sidecar under
`.hydra-framework/surfaces/wiki/` and reports per page: sources whose digest no
longer matches, sources that no longer exist, and pages with no declared sources.
Exit 0 always.

Its output must name the `wiki fingerprint` command that clears each finding, per
D6. That string is reused by M6's commit report and M7's CI step, so build it
once here.

Measured, not estimated: the review's probe did the whole reader in about 20
lines by calling `stale_provenance_sources` (`knowledge/freshness.py:287-314`)
with the sidecar's `provenance` mapping and its `checked_on`. That function takes
a plain `Mapping` and has no dependency on the unit model;
`knowledge/candidates.py:84-88` is simply its only caller today. Budget roughly
120 lines with argument parsing, JSON output and the report shape.

It runs with no object store and with `HYDRA_QUERY_STORE=off`, because it reads
YAML and files, not the store.

**What it deliberately does not do**: check `hydra://` references in prose, which
`ref check` does not do for sidecar-registered files either; check links, which
`validate-wiki` owns; check coverage, which has no data.

### M5: `wiki fingerprint`

`hydra.py wiki fingerprint --page <id>` rewrites one page entry's
`provenance.source_digests` and `checked_on` from current file digests, the way
`knowledge fingerprint --unit <id>` does for a unit. It refuses any source that is
not exactly one existing file, with the same message shape as
`commands/knowledge_fingerprint.py:112-114`.

`replace_source_digests` (`commands/knowledge_fingerprint.py:68-93`) **cannot** be
reused: it requires Markdown frontmatter delimited by `---` with a `provenance:`
key at indent 0, and a sidecar entry's `provenance:` is nested at indent 4 inside
`objects.<name>`. The writer is new. Roughly 80 lines, rewriting one entry in a
YAML file it also reads while preserving the rest.

Before M6, because there is no point automating the reindex until pages can be
re-verified.

### M1b: sources for the ten unmapped content pages

The ten named in D7. For each: read the page against the implementation, decide
which files own each claim, add the sidecar entry, run `wiki fingerprint`.

This is analysis, and it is where the design gets stress-tested. Expect to find
wiki claims that are simply wrong; record those rather than fixing prose inline,
since correcting the wiki is out of scope here.

After M5 so the digests are generated rather than hand-computed, and after M3 so
the audit can confirm each page lands clean.

### M6: automatic reindex in `hook-post-edit`, plus the commit report

Two parts, both hook work.

*Reindex.* When the edited path is a registered object path, `hook-post-edit`
runs `ref index` before its existing checks. Silent: measured at exit 0 with no
output, so it costs an agent no context. Membership is guarded by reading
`registry.yaml` and testing path membership, or the hook would rewrite the
registry on every unrelated Markdown write. Measured budget: 0.14 s no-op path
plus 0.64 s `ref index`, against 30 s at `.claude/settings.json:46`.

Name the contract change in the module docstring: the wired hook writes one
derived tracked file, `cognition/graph/registry.yaml`, where it previously only
reported. Note in the same place that
`.hydra-framework/hooks/post-merge` already runs `ref index`, so the class of
action is not new to this repository.

*Commit report.* A `post-commit` hook reporting the pages whose sources changed in
that commit, with the `wiki fingerprint` line for each, per D6. Best-effort and
never blocking, matching the four `post-*` hooks already installed through
`core.hooksPath` at `.hydra-framework/hooks`.

Tests in `unit/commands/test_hooks.py`: registered path reindexes, unregistered
path does not, missing registry is not created. One
`agent-hooks-hook-post-edit` golden for the registered-path case.

Roughly 40 lines plus tests for the reindex, plus the report.

### M4: `wiki audit` as a CI step

Add `wiki audit` to `.github/workflows/hydra.yml` as its own named step that
reports and exits 0, per D6. Not an advisory note appended to `validate`.

Last, because it is the only item that changes what every CI run prints.

Acceptance: a stale page appears in the CI log under its own step name; the build
stays green; no `Finding` is constructed.

## Current Stage

Not started. Authorized by the review's Phase 4 gate, 2026-09-14.

The immediate next action is M2, and it is small: one `ObjectFamily` entry, one
non-retrieving context provider, and two test cases. Read D2 before writing it,
because the obvious implementation, adding `"Documentation"` to
`SEARCH_FAMILIES`, is the one thing this design specifically refuses.

## Readiness

Status: ready

- Branch or workspace assumptions: branch `repository-documentation-dependency-mvp`,
  cut from `main` at 7801b1d and carrying only the Phase 4 decision commit.
  `main` is unchanged, so this merges back by pull request the way
  `bounded-knowledge-retrieval` did.
- Relevant canonical docs:
  `.hydra-framework/evolution/candidates/repository-intelligence-review/03-architecture-and-mvp.md`
  (the MVP),
  `.hydra-framework/evolution/candidates/repository-intelligence-review/04-decision.md`
  (the amendments),
  `.hydra-framework/surfaces/README.md`,
  `.hydra-framework/core/placement-rules.md`,
  `.hydra-framework/repo/knowledge/spaces/hydra-framework/problems.md` (P16).
- Required dependencies, services, generated artifacts, or private local requirements: a Python 3 stdlib checkout.
  `ref store rebuild` is required before any `explain-path` measurement, since the
  store is Git-ignored and reports "not built" on a fresh clone.
  `export-adapters` is required before `selftest` in a fresh clone, which is what
  `.github/workflows/hydra.yml:33` does before `:36`.
- Blockers and assumptions: none. Total estimated engine cost is roughly 260 lines
  plus tests across three modules, plus the commit report, with no schema change,
  no store change, no envelope change and no change to `knowledge/freshness.py`.
- Expected validation command or evidence: run per item and at the end.
  `python3 .hydra-framework/scripts/hydra.py ref index`,
  `... ref check`, `... validate`, `... validate-wiki`,
  `... validate-package-docs`, `... reclaim --fail-on-findings`,
  `... selftest`. Baseline to beat: 57 objects and 1633 tests on `main` at
  7801b1d.

## Step State

- Active step: none
- Next step: M2, the `Documentation` object family with a non-retrieving context
  provider. See D2.
- Completed steps: none. The design phase is complete and is owned by
  `repository-intelligence-review`, not by this record.
- Superseded or skipped steps: none.

## Changed Files

- None yet.

## Validation

Baseline on `main` at 7801b1d: `ref index` 57 objects, `ref check` ok, `validate`
ok with five advisory notes, `selftest` 1633 tests OK, `knowledge stale` 7 units
checked and 2 stale.

Measured in an isolated clone during the review, as the target state for M2 and
M1: `ref index` 59 to 60 objects, `ref check` ok, `validate` ok, `selftest` 1633
tests OK, `compile-context` 0 wiki candidates.

## Blockers

- None.

## Continuation Notes

What another model or developer needs to continue safely.

- Running state: none. Nothing is implemented.
- Resume check: `python3 .hydra-framework/scripts/hydra.py board`, then read this
  record's Step State.
- The two things most likely to be got wrong, both because the obvious move is
  the refused one: adding `"Documentation"` to `SEARCH_FAMILIES` (see D2), and
  expanding a directory citation into a digest instead of naming the files it
  stands for (see D5).
- Two questions are open inside this work and are not design gaps to close before
  starting. The false-positive rate of page-level digest staleness has never been
  measured anywhere, and M3 is what measures it; if it is bad, say so and correct
  the design in place here rather than shipping a noisy audit. And whether `ref
  index` stays inside the 30 s hook budget as the object count grows is owned by
  P5 and P12, which M6 inherits.
