# Phase 4 -- Decision

Part of [`repository-intelligence-review`](../repository-intelligence-review.md).
The decision gate of the task record
`.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-14-repository-intelligence-and-wiki-projections.md`.

Decided 2026-09-14 with the maintainer, on `main` at 7801b1d. Sections 1 through
7 of [`01-current-state.md`](01-current-state.md),
[`02-gap-analysis.md`](02-gap-analysis.md) and
[`03-architecture-and-mvp.md`](03-architecture-and-mvp.md) are carried forward by
citation. Where this phase overturns one of them, the correction is in section 2
and is recorded in place in the task record's Confirmed Decisions.

Phase 3 recorded five items as unestablished because each is a judgment rather
than a measurement. This phase put all five to the maintainer and records what
was chosen. Two of the five were answered only after a new probe overturned the
evidence Phase 3 had offered; those probes are in section 2.

This file is scanned by `ref check` (`objects/references.py:121-136`), so object
ids that exist only in a probe are spelled without their `hydra://` scheme
prefix, as `documentation/page/state-tiers`. The convention is inherited from
Phase 2.

## 1. The five decisions

### Decision A: `hook-post-edit` may write `cognition/graph/registry.yaml`

**Accepted.** MVP item M6 is authorized as Phase 3 specified it.

The wired post-edit hook is read-only today and this makes it write one derived,
tracked file when the edited path is a registered object path. Measured viable by
Phase 3: `ref index` at 0.63 to 0.64 s and the hook's no-op path at 0.14 s,
against the 30 s budget at `.claude/settings.json:46`. The write is silent:
Phase 3 measured `hook-post-edit` on a registered wiki page at exit 0 with no
output, so it costs an agent no context.

Without it, `objects/registry.py:191-193` fails every registered page's digest
after any prose edit, validator 11 carries that into `doctor`, and
`.github/workflows/hydra.yml:39` runs `doctor`. Every wiki pull request would
fail CI once.

**New evidence, recorded because it makes the contract change smaller than Phase
3 presented it.** The Git hook layer already writes this file. `core.hooksPath`
resolves to `.hydra-framework/hooks`, which holds `post-checkout`, `post-commit`,
`post-merge`, `post-rewrite` and `pre-push`, and `.hydra-framework/hooks/post-merge`
already runs `ref index` unconditionally. So "a Hydra hook regenerates the object
registry" is existing behavior in this repository, not a new class of action. What
M6 adds is the same action in the agent-facing hook.

**Reversal.** Roughly 40 lines and one guard in `commands/hooks.py` plus its
tests. Nothing depends on it and the manual path still works.

### Decision B: registration is accepted, retrieval is refused

**Accepted with a correction to Phase 3's Decision 3.** Wiki pages become objects.
The `Documentation` family is added. It is **not** added to `SEARCH_FAMILIES`.
Instead it gets an explicit non-retrieving context provider, so a registered page
is addressable and is never a `compile-context` candidate.

Phase 3 held that the retrieval cost is inseparable from registration and must
therefore be accepted as part of this decision. That does not hold. See section
2.1 for the probe.

The maintainer's stated reason for refusing retrieval, recorded because it is the
boundary this decision defends: the wiki is the surface that explains the
framework to humans, and the knowledge spaces are what is written for agents.
Feeding wiki prose into agent context packets would put a human-facing
explanation layer into competition with the canonical material written for
agents, which is the distinction Hydra's knowledge model exists to hold.

Measured consequence of the chosen route: a registered page appears in
`knowledge-search` as a title-only stub costing 3 approximate tokens, against 71
for the knowledge unit on the same subject. Its prose never enters a compiled
packet.

**Reversal.** Move the string `"Documentation"` from `NON_RETRIEVED_FAMILIES` to
`SEARCH_FAMILIES`. One line, no data migration.

### Decision B2: the staleness signal is delivered at commit and reported in CI

**Accepted, replacing MVP item M4 as Phase 3 specified it.** Phase 3 made
staleness a sixth advisory note printed after `validate`'s verdict. The maintainer
rejected that delivery on evidence gathered in this phase, and chose:

1. A `post-commit` hook report. One message per commit, naming the pages whose
   sources changed in that commit, and printing the exact `wiki fingerprint`
   command that clears each. The message is written to be actionable by an agent
   and readable by a human, following the pattern `ref check` already uses when it
   prints `rerun 'hydra.py ref index'`.
2. `wiki audit` as its own named CI step that reports stale pages and exits 0. It
   does not fail the build.

The note after `validate` is not the delivery mechanism. See section 2.2 for why.

Commit rather than edit, for two reasons the maintainer gave. Edit-time delivery
would print on every `Write` and `Edit`, injecting a report into an agent's
context on every tool call, to an audience that cannot act on it. And commit is
where this repository already put the boundary: `.hydra-framework/hooks/pre-push`
states it directly, that push is the guarded boundary on purpose, because
"pre-commit fires constantly, and blocking commits on bookkeeping is how a team
ends up passing `--no-verify`". The commit hook is a report, not a gate,
consistent with the four `post-*` hooks that are already best-effort and never
block.

CI carries it as well as the hook, because `pre-push` also states the rule: "a
check that lives solely in an uninstalled hook is not a check."

**Reversal.** The CI step's exit code is one line. The hook report is one file.

### Decision C: all 40 wiki pages are registered, in two steps

**Accepted, widening Phase 3's MVP scope from 23 pages to 40.** Phase 3 scoped M1
to the 23 pages `source-map.md` covers and left the other 17 outside the MVP.

The widening is a consequence of Decision B. Phase 3's main argument for a small
page count was the per-page retrieval cost, and a non-retrieving family makes that
cost zero. What remains is authoring work, which is bounded and enumerable.

A measurement taken in this phase splits the 17 uncovered pages into two
populations that Phase 3 had treated as one:

- **Seven navigation pages** (`project-wiki/home.md`, and `concepts/concepts.md`,
  `extending-hydra/extending-hydra.md`, `operations/operations.md`,
  `reference/reference.md`, `reference/source-map.md`,
  `start-here/start-here.md` under `project-wiki/hydra-framework/`). They run 17
  to 33 lines, are almost entirely links, and carry 0 or 1 path citations each.
  They make no claim about behavior, so they have no sources to declare,
  permanently. They register with `provenance.sources: []`, which buys identity,
  `move-object` and `explain-path` at no staleness cost.
- **Ten content pages never mapped**: `architecture/engine.md` (114 lines),
  `reference/glossary.md` (110), `working-with-hydra/first-task.md` (101),
  `architecture/object-context-model.md` (67), `extending-hydra/intake.md` (61),
  `working-with-hydra/task-lifecycle.md` (58),
  `start-here/new-contributor.md` (56), `architecture/execution-flow.md` (52),
  `architecture/execution-stack.md` (41),
  `working-with-hydra/private-workspace.md` (38). These make claims and have no
  declared sources.

So the honest coverage figure is 23 of 33 content pages, not 23 of 40.

The ten are a separate sequenced step, **M1b**, because establishing their sources
means reading each page against the implementation and deciding which files own
each claim. That is analysis, not the transcription M1 is. A page carrying wrong
sources is worse than one carrying none, because it claims a verification it does
not have.

**One consequence the record should carry.** With all 40 registered, `wiki audit`'s
"no declared sources" category permanently holds the seven navigation pages, and
nothing distinguishes "deliberately has none" from "not yet established". No field
is added for this now. Revisit if the category becomes noise.

**Reversal.** Sidecar entries are data. Removing a page is deleting its entry and
rerunning `ref index`.

### Decision D: directory citations stay refused, and are converted case by case

**Accepted, with an addition to Phase 3's recommendation.** The engine rule is
unchanged: a `provenance.sources` entry is exactly one existing file.
`commands/knowledge_fingerprint.py:112-114` refuses anything else and the digest
branch at `knowledge/freshness.py:306` requires `path.is_file()`. Supporting
directories would give the repository two rules for what a source is.

Phase 3 then left the eight directory rows in `source-map.md` as prose, verified
by nothing. The maintainer accepted the refusal and rejected leaving all eight
unverified.

Measured in this phase, the eight directories and their file counts:

| Cited directory | Files |
| --- | --- |
| `.hydra-framework/engine/tests` | 605 |
| `.hydra-framework/engine/src/hydra_engine/knowledge` | 71 |
| `.hydra-framework/engine/src/hydra_engine/command_output` | 66 |
| `.hydra-framework/engine/src/hydra_engine/commands` | 54 |
| `.hydra-framework/capabilities` | 47 |
| `.hydra-framework/engine/src/hydra_engine/telemetry` | 16 |
| `.hydra-framework/engine/src/hydra_engine/providers` | 15 |
| `.hydra-framework/validation/rules` | 2 |

This is why expansion is refused rather than merely unsupported. The
`command-surface.md` page cites `engine/tests` and `hydra_engine/commands`, 659
files between them. Any change to any one of them would mark the page stale, so
it would be stale from the first day and never clear.

And this is why prose is not good enough either. `architecture/context-retrieval.md`
has three sections, on routing, on freshness, and a worked example. It cites the
whole `knowledge` package, 33 Python modules. It does not depend on
`migration_v2.py` or `bindings.py`. It depends on roughly four modules. Citing the
directory means a migration-code edit flags the page; citing the four means a
routing or freshness edit flags it. The second is signal, the first is noise, and
the difference is four files against 71.

**So, per row: ask whether the page means the whole directory or whether the
directory was shorthand.** Where it was shorthand, name the files. Where the page
genuinely means all of it, `engine/tests` being the clear case and
`.hydra-framework/capabilities` likely another, leave prose and record the
citation as unverified rather than implying coverage that does not exist.

**Reversal.** Source lists are data in the sidecar.

### Decision E: the nine-item delete list stands

**Accepted whole.** Section 5.4 of [`03-architecture-and-mvp.md`](03-architecture-and-mvp.md)
names nine components of the reviewed candidate that should be deleted rather than
deferred, each against the contract it contradicts: `projection` as a noun,
per-concept URI schemes, "spaces compose rather than inherit", authority scopes on
`scope`, the 17-relation vocabulary, four severity levels, `last_verified.commit`,
`docs` as a CLI namespace, and the premise that this is a wiki problem.

They are recorded as decided against, with reasons, not as a backlog. A deferred
item invites a later agent to build it without rechecking the contract it breaks.

Two rows are stronger after this phase than when Phase 3 wrote them:

- *Four severity levels.* Decision B2 solves the problem they were aimed at, a
  staleness signal that neither fails the build nor disappears, without touching
  `finding.py:38-42` or the 19 validators that depend on it.
- *The premise that this is a wiki problem.* Re-verified directly in this phase:
  `checks/validator_registry.py:21` describes `validate`/`doctor`'s "ten checks",
  and `len(VALIDATORS)` is **19**. That docstring is wrong in the engine today and
  nothing catches it. The dependency model this MVP builds points at any repository
  path, because `provenance.sources` is a path list with no wiki in it. That
  property is free and is the strongest thing about the design.

Any of the nine may be reopened by evidence, the way Phase 3's own recommendation
was overturned by its own probe before its gate closed.

## 2. Corrections to Phase 3

Two findings change a Phase 3 claim. Both are recorded in place in the task
record's Confirmed Decisions.

### 2.1 Registration and retrieval are severable

Phase 3's Decision 3 and its section 0 hold that the `"Documentation"` string in
`SEARCH_FAMILIES` is mandatory, and conclude that "the retrieval consequence
therefore comes with registration and cannot be deferred". The first half is true
as stated about that specific string. The conclusion does not follow.

The constraint Phase 3 cited, `unit/knowledge/test_context_providers.py:81`, is a
**name set equality** assertion between `{family.name for family in OBJECT_FAMILIES}`
and `{provider.family for provider in CONTEXT_PROVIDERS}`. It requires a provider
*entry* per family. It asserts nothing about what that provider returns. A provider
that yields zero candidates satisfies it exactly as well as a search collector does.

Phase 3 measured two configurations, family alone and family plus `SEARCH_FAMILIES`,
and did not measure the third.

Measured in this phase, in an isolated `git clone` of this repository at 7801b1d
under the session scratchpad, with the working tree never modified. Four additive
edits: one `ObjectFamily` entry for `Documentation`; a `_collect_nothing` provider
returning `ProviderOutput(candidates=[])`; a `NON_RETRIEVED_FAMILIES` tuple
appended into `CONTEXT_PROVIDERS` alongside the `SEARCH_FAMILIES` comprehension;
and one sidecar at `.hydra-framework/surfaces/wiki/hydra-framework.yaml`
registering one wiki manifest and one page with real `provenance.sources`,
`source_digests` and `checked_on`.

| Measurement | Result |
| --- | --- |
| `ref index` | `Indexed 59 objects` |
| `ref check` | `ok (59 objects)` |
| `validate` | `ok`, same advisory notes |
| `selftest` | **1633 tests, OK** |
| `compile-context --task "state tiers private shared boundaries"` | 0 wiki paths in the packet |
| `compile-context --include-family Documentation --task "..."` | 0 candidates, with the family explicitly requested |
| `knowledge-search "state tiers"` | knowledge unit at 71 approximate tokens of content; registered page at **3**, id, kind and title only |

The structural reason no other family's provider can leak a Documentation
document: `_family_search_collector` skips any result where
`family_for(doc.hydra_id, doc.kind) != family`
(`knowledge/context_providers.py:253`). And a registered object enters the lexical
index through `_document_for_object` (`knowledge/index_collection.py:168-170`),
which builds a document whose searchable text is the title, with empty body
fields. Phase 3's "40 retrievable documents, title-only in the index and whole-file
once selected" is right about the index and wrong about selection once no provider
offers the family.

Effect: Phase 3's measured 511-token `compile-context` contribution is a cost of
the route Phase 3 chose, not a cost of registration. Decision B takes the other
route.

### 2.2 Advisory notes are not a delivery mechanism in this repository

Phase 3's M4 makes staleness an advisory note printed after `validate`'s verdict,
reasoning from `knowledge/package_checks.py:148-156` that a `Finding` would make
`validate` exit nonzero and that a deliberately stale page must not be a hard
failure. That reasoning holds. The conclusion that a note is therefore the right
delivery does not, and this phase measured why.

- `knowledge stale` is **not a CI step**. `.github/workflows/hydra.yml` runs
  `export-adapters`, `selftest`, `doctor`, and a tracked-private-state check.
  Staleness appears nowhere in the workflow.
- `knowledge stale` reports **2 of 7 units stale** on `main` at 7801b1d.
  `units/build-status.md` records `checked_on: "2026-09-10"`; its source
  `cli/command_metadata.py` was committed 2026-09-12.
- `doctor` prints **five standing advisory notes** on every run. One has read
  "compatibility verified 2026-07-30 (46 days old; recheck provider compatibility)"
  for 46 days. Another reports 17,791 telemetry events against a 5,000-line
  advisory.

So the channel Phase 3 chose already carries five unread messages, and the nearest
equivalent mechanism is both absent from CI and currently stale without effect.
Decision B2 changes the delivery and keeps Phase 3's reasoning about `Finding`
intact: the CI step reports and exits 0, and no `Finding` is constructed.

## 3. Outcome

- The reviewed candidate
  [`2026-09-14-repository-intelligence-and-wiki-projections`](../2026-09-14-repository-intelligence-and-wiki-projections.md)
  is **superseded** by the MVP in
  [`03-architecture-and-mvp.md`](03-architecture-and-mvp.md) section 4, as amended
  by the decisions above. Superseded rather than accepted because acceptance is
  partial: four of its section 33 items are cut, nine of its components are deleted
  outright, and its framing premise is rejected.
- This router reaches `captured`.
- The gap is recorded as **P16** in
  `.hydra-framework/repo/knowledge/spaces/hydra-framework/problems.md`, open and
  unresolved.
- An implementation task record is opened for the MVP, sequenced M2, M1, M1b, M3,
  M5, M6, M4, with M1b new in this phase and M4 redefined by Decision B2.

## 4. What this phase did not settle

Three of Phase 3's five unestablished items were decided here. Two remain
unestablished and are carried into implementation rather than closed:

1. **The false-positive rate of page-level digest staleness.** Still unmeasured,
   because no page-level staleness has ever run. M3 is what produces the
   measurement. Decision D reduces the expected rate by refusing directory sources
   and naming real files, but does not establish it.
2. **Whether `ref index` stays inside the hook budget as the object count grows.**
   0.64 s at 60 objects. `problems.md` P5 and P12 own index scaling and are out of
   scope here, so Decision A inherits whatever they conclude.

## 5. Gate evidence

Commands run for this phase on `main` at 7801b1d, in the working tree, all
read-only:

- `knowledge stale` -> `Checked units: 7`, 2 stale
- `doctor` -> `Hydra validate: ok` with five advisory notes
- `git config --get core.hooksPath` -> `.hydra-framework/hooks`, holding five hooks
- `len(VALIDATORS)` -> 19, against a docstring reading "ten checks"
- Page census over `project-wiki/` -> 40 pages, 23 covered by `source-map.md`
- Source-map target census -> 33 file targets, 8 directory targets

In an isolated `git clone` under the session scratchpad, never the working tree:

- `ref index` -> `Indexed 59 objects`; `ref check` -> `ok (59 objects)`;
  `validate` -> `ok`
- `selftest` -> **1633 tests, OK**, with the `Documentation` family registered, a
  non-retrieving provider, and two wiki pages registered as objects
- `compile-context` with and without `--include-family Documentation` -> 0 wiki
  candidates
- `knowledge-search "state tiers"` -> registered page returned as a 3-token
  title-only stub
