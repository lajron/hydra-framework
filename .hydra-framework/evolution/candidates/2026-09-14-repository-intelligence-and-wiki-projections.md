# Improvement: Repository Intelligence, Knowledge Spaces, and Wiki Projections

Status: superseded
Author: milosdenic-dev-gmail-com
Created: 2026-09-14

## Change

Treat Markdown as one projection of repository intelligence rather than as the
repository knowledge model, and give Hydra mechanical understanding of which
human-facing documentation depends on which parts of repository truth.

The proposal spans four layers (repository reality, repository intelligence,
knowledge spaces, projections) and nine delivery phases, from a one-time wiki
reconciliation through page-level documentation impact auditing, generated
mechanical reference, graph projections, a static documentation website, and
claim-level tracking.

Full text is in `2026-09-14-repository-intelligence-and-wiki-projections/`.
This router holds what is settled, the table of contents, and the review
boundary. Nothing in the subdirectory is a separate queue entry.

## Trigger

`project-wiki/hydra-framework/` does not reliably describe everything the
current framework does, and the documentation model makes that drift easy to
reproduce: an implementation change relies on a maintainer remembering which
pages it invalidates.

Measured on `main` at 7801b1d, 2026-09-14:

- 5 of 70 registered commands (`bindings list`, `bindings verify`,
  `capability scaffold-agent`, `capability scaffold-skill`,
  `knowledge migrate-v2`) appear nowhere in
  `project-wiki/hydra-framework/reference/command-surface.md`.
- `hydra.py knowledge stale` reports 2 of 7 knowledge units with sources
  committed after `checked_on`. The equivalent question cannot be asked of
  any wiki page at all, because no wiki page is a Hydra object.
- `project-wiki/hydra-framework/reference/source-map.md` is a hand-maintained
  page-to-source dependency table covering roughly 20 claim rows. Every path
  it cites currently resolves, but nothing mechanically checks that, and
  `hydra.py validate-wiki` explicitly does not validate backtick path
  citations.

## Rationale

The one-time rewrite fixes today's wiki and leaves the mechanism that
produced the drift in place. The durable problem is that documentation
dependency is knowledge Hydra holds nowhere.

Hydra already carries most of the machinery this needs, applied to a
different corpus: `provenance.sources` plus `source_digests` plus
`checked_on` on knowledge units, `knowledge stale` to compare them against
Git, the object registry, and a SQLite object store with `refs`, `relations`
and `provenance` tables answering `ref rdeps` and `ref impact`. What is
missing is not a knowledge graph. It is that `project-wiki/` sits outside the
object discovery root, so none of it can be asked about.

## Evidence

See the task record
`.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-14-repository-intelligence-and-wiki-projections.md`,
section "Current-State Reconstruction", for what was verified against `main`
before this candidate was filed, including which proposal components already
exist under a different name.

## Result

**Superseded 2026-09-14** by the MVP in
[`repository-intelligence-review/03-architecture-and-mvp.md`](repository-intelligence-review/03-architecture-and-mvp.md)
section 4, as amended by
[`repository-intelligence-review/04-decision.md`](repository-intelligence-review/04-decision.md)
section 1. The review that produced it is
[`repository-intelligence-review`](repository-intelligence-review.md), now
`captured`.

Superseded rather than accepted, and the distinction is deliberate. Acceptance is
partial in three ways, and recording a mixed verdict inside an `accepted` would
misrepresent all three.

**The problem is confirmed real.** No mechanism in this repository could answer,
for any wiki page, the question it already answers for every knowledge unit: did
a source this page depends on change since the page was last verified? That gap
is recorded as P16 in
`.hydra-framework/repo/knowledge/spaces/hydra-framework/problems.md`, open and
unresolved.

**Most of the proposal was already built under other names.** The review
classified 63 components across all six part files and answered all 25 of section
36's open questions. The repository graph, reverse-dependency queries, staleness
against Git, epistemic categories, the wiki-as-host model, and the projection
concept itself all already exist; `projection` is what this repository already
calls a `surface`.

**Four of the nine MVP items in section 33 are cut**, and **nine components are
deleted outright rather than deferred**, each against the contract it
contradicts. See section 5.4 of the architecture part file. Deferral was refused
on purpose: a deferred item invites a later agent to build it without rechecking
the contract it breaks.

**The framing premise is rejected on measurement.** This is not a wiki problem.
Four of the eight measured drift items are inside the engine, in files that are
themselves Hydra objects; `checks/validator_registry.py:21` describes ten
validator checks where `len(VALIDATORS)` is 19. The mechanism that was authorized
points at any repository path, because `provenance.sources` is a path list with no
wiki in it.

Implementation is authorized and is owned by
`.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-14-repository-documentation-dependency-mvp.md`.
It is the MVP, not this candidate.

## Scope Assessment

- Repository-specific: no. The design must work for repositories that adopt
  Hydra, not only for Hydra's own repository. Hydra's own wiki is the first
  dogfooding target, not the only target.
- Technology-specific: partially. The static-site half names candidate
  frontend stacks; the intelligence half is technology-neutral.
- Common seed candidate: yes for the mechanism that was authorized.
  Documentation dependency built on `provenance.sources` names any repository
  path and is framework behavior. Generated reference is cut from the MVP because
  `CommandMetadata` carries no descriptions and covers 70 of 74 dispatched
  commands. Projection boundaries are deleted; this repository's word is
  `surface`.

## Follow-Up

Closed 2026-09-14. The object boundaries were agreed with the maintainer at the
review's Phase 4 gate and this candidate's `Status:` was set in the same commit as
the review router's, so the two never disagree.

This candidate is now history. Read the review's part files instead: they carry
the corrections, and several of this candidate's factual claims were overturned by
measurement during the review. Nothing here is evidence of current behavior.

## Contents

| Part | Covers |
| --- | --- |
| [`01-problem-and-architecture.md`](2026-09-14-repository-intelligence-and-wiki-projections/01-problem-and-architecture.md) | Original problem, the four-layer model, terminology and boundaries |
| [`02-wikis-and-spaces.md`](2026-09-14-repository-intelligence-and-wiki-projections/02-wikis-and-spaces.md) | `project-wiki` as host, multiple wikis, spaces vs wikis, composition, portable knowledge, epistemic categories |
| [`03-object-and-relation-model.md`](2026-09-14-repository-intelligence-and-wiki-projections/03-object-and-relation-model.md) | Documentation as an object family, object families, relation vocabulary, claims, authored/generated/hybrid, source mapping |
| [`04-commands-and-ci.md`](2026-09-14-repository-intelligence-and-wiki-projections/04-commands-and-ci.md) | Generated graphs, `docs audit`, coverage, `docs reconcile`, PR experience, CI enforcement |
| [`05-website.md`](2026-09-14-repository-intelligence-and-wiki-projections/05-website.md) | Interactive website, graph explorer, health dashboard, CI/CD pipeline |
| [`06-delivery-and-risks.md`](2026-09-14-repository-intelligence-and-wiki-projections/06-delivery-and-risks.md) | Reconciliation pass, information architecture, phases, MVP, risks, principles, open questions |
