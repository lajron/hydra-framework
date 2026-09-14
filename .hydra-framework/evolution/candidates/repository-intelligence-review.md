# Improvement: Review of Repository Intelligence And Wiki Projections

Status: captured
Author: milosdenic-dev-gmail-com
Created: 2026-09-14

## Change

This record reviews the dated candidate
[`2026-09-14-repository-intelligence-and-wiki-projections`](2026-09-14-repository-intelligence-and-wiki-projections.md)
rather than standing alone. It holds the four gate artifacts that review
produces, and carries the accept/reject recommendation that Phase 4 acts on.

Run by the task record
`.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-14-repository-intelligence-and-wiki-projections.md`,
whose Approved Plan defines the phases and gates. That record owns phase
state; this one owns findings.

## Trigger

The reviewed candidate asks for a nine-phase program touching the object
model, the query store, the knowledge model, CI, and a website. A first
reconstruction pass found most of its components already built under other
names, and one genuine structural gap. That spread — between what the
proposal assumes is missing and what is actually missing — is too wide to
decide from the proposal text.

## Rationale

Building from the proposal as written would add a second vocabulary for
concepts this repository already has (`projection` beside `surface`), a
second provenance mechanism beside the one knowledge units already carry, and
a second staleness mechanism beside `knowledge stale`. The review exists to
separate the components that are genuinely missing from the ones that are
renamed or undiscovered, before any of it is built.

## Evidence

Per phase, in `repository-intelligence-review/`. Nothing is written here
until its gate passes.

Phase 1 reconstructed the framework from implementation and tests only and
corrected six of the first-pass findings the task record carries as D1 to D7.
The object count is 57, not 44. There are six object families, not five.
The relation type is discarded in `objects/envelopes.py:129`, one layer above
the store, so widening the `relations` table alone would recover nothing, and
all typed relations authored in this repository are `relates-to` (22,
corrected by Phase 2 from the 23 this paragraph first recorded).
`project-wiki/` is already a recognized sidecar root in
`objects/discovery.py:48`, and in `objects/moves.py:104` (added by Phase 3).
`validate-wiki` already checks all 41 canonical
paths `source-map.md` cites. Every source of every knowledge unit is
fingerprinted, so `knowledge stale` never uses its date rule and its output
line states a reason that did not apply. Details and evidence are in the part
file.

Phase 2 classified 63 proposal components and answered all 25 open questions in
the reviewed candidate's section 36. It overturned three more rows of the task
record's D2: `ref impact` walks outbound edges, so the reverse-dependency and
impact queries D2 recorded as confirmed answer one hop inbound and the wrong
direction transitively; `surfaces/` holds nothing machine-readable, so the wiki
manifest is a new file rather than existing behavior; and `command-metadata`
carries no command descriptions and omits four commands, so the generated CLI
reference's input is incomplete. It also priced what Phase 1 left open: a wiki
page becomes a Hydra object today with no engine change, and a `Documentation`
family costs two lines, but every edit to a registered page fails `ref check`
until `ref index` is rerun, and nothing reindexes automatically. Five questions
are deferred whole, each with a reason. Details, the probe recipe, and the
`path:line` evidence for every classification are in the part file.

Phase 3 settled the five boundary decisions, cut the MVP from nine items to
five, and wrote the challenge section. A wiki page becomes an object through an
object sidecar in `.hydra-framework/surfaces/wiki/`, the `relations` model stays
untyped, one `Documentation` family is added, and identity stays `hydra_id` plus
`uid`. It corrected five further claims, three of them Phase 2's own. The family
price is confirmed at two lines and both are mandatory: a family with no context
provider fails `unit/knowledge/test_context_providers.py:81`, so the measured
retrieval cost (a registered page becomes a `compile-context` candidate, 511
approximate tokens for one page) comes with registration and cannot be deferred.
Registering a page puts it in the lexical search index automatically
(`knowledge/index_collection.py:82-85`), which Phase 2 did not price. And the
transitive reverse walk Phase 2 named as the one graph view worth building is
not what documentation impact needs, because that runs through `provenance` and
`citers_of_source_path` already answers it in one hop. `selftest` was run in a
real clone, which Phase 2 could not do: 1633 tests pass with the family
registered and three wiki pages registered as objects. Total estimated engine
cost is roughly 260 lines with no schema, store or envelope change. Details, the
probe results, and the delete-rather-than-defer list are in the part file.

Phase 4 put the five judgments Phase 3 recorded as unestablished to the
maintainer and recorded what was chosen. Three were settled, two carried into
implementation. It corrected two Phase 3 claims, both by measurement.
Registration and retrieval are severable: the parity test at
`unit/knowledge/test_context_providers.py:81` asserts name set equality and
requires a provider entry, not a retrieving one, so a `Documentation` family with
an explicit non-retrieving provider passes `selftest` at 1633 tests and offers
zero `compile-context` candidates even when the family is requested by name. The
511-token retrieval cost is therefore a property of the route Phase 3 chose, not
of registration. And an advisory note is not a delivery mechanism here: `knowledge
stale` is absent from CI, reports 2 of 7 units stale on `main`, and `doctor`
already prints five standing notes, one unread for 46 days. The staleness signal
moves to a `post-commit` report naming the fix command, plus `wiki audit` as a
named CI step that reports and exits 0. Scope widened from 23 pages to all 40,
because Decision B removed the per-page retrieval cost that bounded it; the 17
pages Phase 3 left out are seven navigation pages with nothing to declare and ten
content pages that need their sources established by reading the implementation,
which becomes its own step M1b. Directory sources stay refused and are converted
to named files case by case rather than left as unverified prose. The nine-item
delete list stands whole. Details, the probe, and the census are in the part file.

| Phase | Artifact | State |
| --- | --- | --- |
| 1 — Current-state reconstruction | [`01-current-state.md`](repository-intelligence-review/01-current-state.md) | complete 2026-09-14 |
| 2 — Gap analysis | [`02-gap-analysis.md`](repository-intelligence-review/02-gap-analysis.md) | complete 2026-09-14 |
| 3 — Revised architecture and MVP | [`03-architecture-and-mvp.md`](repository-intelligence-review/03-architecture-and-mvp.md) | complete 2026-09-14 |
| 4 — Decision | [`04-decision.md`](repository-intelligence-review/04-decision.md), plus this router's `Status:` and a `problems.md` entry | complete 2026-09-14 |

## Result

Captured 2026-09-14. The reviewed candidate is **superseded** by the MVP in
[`03-architecture-and-mvp.md`](repository-intelligence-review/03-architecture-and-mvp.md)
section 4, as amended by
[`04-decision.md`](repository-intelligence-review/04-decision.md) section 1.
Superseded rather than accepted because acceptance is partial: four of its
section 33 items are cut, nine of its components are deleted outright rather than
deferred, and its framing premise is rejected on measurement.

What was authorized:

- Wiki pages become Hydra objects through an object sidecar under
  `.hydra-framework/surfaces/wiki/`, with `provenance.sources`,
  `source_digests` and `checked_on` per page.
- One `Documentation` object family, **not** in `SEARCH_FAMILIES`. It carries an
  explicit non-retrieving context provider, so a registered page is addressable
  and never becomes a `compile-context` candidate. The wiki stays the
  human-facing surface; the knowledge spaces stay what is written for agents.
- All 40 wiki pages register: 23 whose sources `source-map.md` already records,
  7 navigation pages with `provenance.sources: []`, and 10 content pages whose
  sources are established by reading the implementation in a separate step.
- `wiki audit` and `wiki fingerprint` as new commands. The `relations` model,
  the store schema, the envelope contract and `knowledge/freshness.py` are all
  unchanged.
- The staleness signal reaches a human through a `post-commit` hook report that
  names the pages and prints the `wiki fingerprint` command that clears each,
  plus `wiki audit` as its own CI step that reports and exits 0. It never fails
  the build and never constructs a `Finding`.
- `hook-post-edit` reruns `ref index` when the edited path is a registered object
  path, writing `cognition/graph/registry.yaml`. `.hydra-framework/hooks/post-merge`
  already does this, so the class of action is not new.
- Directory citations stay refused. A `provenance.sources` entry is exactly one
  existing file.

Recorded as P16 in
`.hydra-framework/repo/knowledge/spaces/hydra-framework/problems.md`, open and
unresolved. Implementation is owned by the task record
`.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-14-repository-documentation-dependency-mvp.md`.

## Scope Assessment

- Repository-specific: no. The reviewed design must work for repositories
  adopting Hydra, not only for Hydra's own.
- Technology-specific: no, for the intelligence half.
- Common seed candidate: yes for the mechanism. A documentation
  dependency model built on `provenance.sources` names any repository path, so
  it is not specific to this repository's wiki. The registered page set is
  repository-local data.

## Follow-Up

Done 2026-09-14. This router is `captured` and the reviewed candidate is
`superseded`, set in the same commit so the two never disagree.

Two questions are carried into implementation rather than closed, both from
[`04-decision.md`](repository-intelligence-review/04-decision.md) section 4: the
false-positive rate of page-level digest staleness, which M3 is what measures,
and whether `ref index` stays inside the hook budget as the object count grows,
which P5 and P12 own.
