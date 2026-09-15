# Part 6: Delivery, Risks, And Open Questions

Part of the candidate
[`2026-09-14-repository-intelligence-and-wiki-projections`](../2026-09-14-repository-intelligence-and-wiki-projections.md).
Original proposal text, preserved. Section numbers are the author's.

---

# 30. One-time Hydra documentation reconciliation

Before or alongside the new machinery, Hydra needs a reconciliation pass
against current `main`.

The inventory should be built in this order:

1. Current engine and implementation
2. Tests and validation behavior
3. Registered command metadata
4. Object and capability registries
5. Schemas
6. Existing canonical Hydra knowledge
7. Build-status or equivalent current-state material
8. README
9. Hydra framework wiki
10. Plans and historical design documents

Plans must not be treated as evidence of shipped behavior.

The pass should specifically investigate whether current public documentation
adequately covers areas previously identified during discussion, including:
operational query/object store; objects, refs, relations, and provenance;
reverse dependency and impact queries; extension registries; object handlers;
context compilation across object families; knowledge fingerprinting and
staleness; profiles and providers; reducers; hook and provider execution
surfaces; telemetry and shareable evidence; integration or takeover scanning;
`explain-path`; task and work lifecycle; trust boundaries; private/shared
behavior; schema and identity model.

These are conversation-derived observations and must be revalidated against
the current repository.

The reconciliation output should include a confirmed capability inventory,
existing documentation coverage, missing documentation, stale documentation,
duplicate documentation, wrong or misleading claims, pages that should be
generated, pages that should remain authored, a proposed information
architecture, and a migration plan.

---

# 31. Recommended Hydra wiki information architecture

The Hydra framework wiki should be organized around user intent rather than
mirroring internal folders.

```text
Hydra Framework
|-- Start Here
|   |-- What Hydra Is
|   |-- Installation
|   |-- Adoption
|   `-- First Workflow
|-- Concepts
|   |-- Repository Knowledge
|   |-- Objects and Identity
|   |-- Relations and Provenance
|   |-- Knowledge Spaces
|   |-- Context Compilation
|   |-- Work and Tasks
|   `-- Projections
|-- Using Hydra
|   |-- Commands
|   |-- Search and Retrieval
|   |-- Impact Analysis
|   |-- Context Workflows
|   `-- Provider Workflows
|-- Operations
|   |-- Validation
|   |-- Staleness
|   |-- Telemetry
|   |-- Recovery
|   `-- Troubleshooting
|-- Integration
|   |-- Existing Repository Adoption
|   |-- Provider Integration
|   |-- Hooks
|   `-- Migration
|-- Architecture
|   |-- System Overview
|   |-- Engine
|   |-- Query Store
|   |-- Extension Model
|   |-- Trust Model
|   `-- Projection System
|-- Maintainers
|   |-- Development
|   |-- Adding Commands
|   |-- Adding Object Families
|   |-- Documentation Maintenance
|   `-- Release Process
`-- Reference
    |-- CLI
    |-- Schemas
    |-- Object Families
    |-- Providers
    |-- Reducers
    `-- Validation Rules
```

The root README should remain smaller. It should explain what Hydra is, why it
exists, what is currently implemented, five-minute setup, major capabilities,
and where to go next. It should not duplicate the full wiki.

---

# 32. Proposed incremental delivery

## Phase 0: Reconcile current documentation

- Reconstruct current behavior from implementation.
- Produce a capability inventory.
- Compare it with README and Hydra wiki.
- Correct misleading or obsolete material.
- Define the new wiki structure.

## Phase 1: Machine-readable documentation dependencies

- Register named wikis.
- Identify managed versus repository-owned wikis.
- Associate important pages with sources and capabilities.
- Store verification commit or source digests.
- Implement page-level impact detection.

Deliverable: `hydra.py docs audit --wiki hydra-framework`, initially
warning-only.

## Phase 2: Generated mechanical reference

- Generate CLI reference from actual command metadata.
- Generate other stable inventories where reliable registries exist.
- Support bounded generated Markdown regions.
- Add deterministic drift checking.

## Phase 3: Documentation coverage

- Define required documentation kinds per significant capability.
- Report missing concept, reference, example, and architecture coverage.
- Add ownership and audience metadata.

## Phase 4: Graph projections

- Produce deterministic JSON graph snapshots.
- Add Mermaid output.
- Support architecture, capability, wiki, and impact views.
- Embed generated graphs into hybrid documentation.

## Phase 5: Static interactive website

- Build named-wiki navigation.
- Render Markdown and Mermaid.
- Add search, source links, related pages, and verification status.
- Deploy through CI/CD.
- Preserve repository Markdown as canonical input.

## Phase 6: Claim-level tracking

- Add claims only for high-value factual assertions.
- Connect claims to evidence and source digests.
- Report claim-level staleness.
- Avoid paragraph-level bureaucracy.

## Phase 7: Agent-assisted reconciliation

- Generate bounded reconciliation packages.
- Allow agents to propose targeted updates.
- Validate generated sections and source impact mechanically.
- Preserve authored rationale.

## Phase 8: Advanced website intelligence

- Interactive graph explorer
- PR and commit impact views
- Documentation health dashboard
- Historical comparison
- Optional organization-wide or cross-repository features

---

# 33. Suggested MVP

The MVP should prove the model without building the entire vision. It should
include:

1. A named `hydra-framework` wiki.
2. Explicit wiki ownership and root path.
3. Page-to-source or page-to-capability dependency metadata.
4. A page-level `docs audit`.
5. One generated CLI reference from existing command metadata.
6. One generated architecture or capability graph.
7. CI warning when an owning source changes without documentation
   acknowledgment.
8. A static website build consuming the same Markdown.
9. Clear separation between existing functionality and planned functionality.

The MVP does not need claim-level annotations, organization-wide portable
spaces, a hosted graph database, live collaborative editing, automatic semantic
prose evaluation, a complex backend, historical graph analytics, or perfect
source-symbol extraction.

---

# 34. Major risks

## 34.1 Graph explosion

If every file, symbol, paragraph, claim, and concept becomes an object
immediately, the system will be too expensive to understand and maintain.

Mitigation: start with stable, meaningful identities; add granularity only when
it supports a real query or workflow; prefer page-level dependencies before
claim-level dependencies.

## 34.2 Annotation burden

Manual metadata can become worse than manually updating documentation.

Mitigation: derive mechanical relationships where possible; use conventions and
registries; require explicit metadata only for semantic relationships Hydra
cannot infer.

## 34.3 False-positive staleness

A source file may change without invalidating a page.

Mitigation: distinguish "stale" from "review required"; allow explicit
verification without prose changes; later introduce more precise object- or
claim-level dependencies.

## 34.4 Generated-documentation noise

Large generated pages can become unreadable.

Mitigation: generate reference, not explanation; use bounded blocks; keep human
narrative concise and intentional.

## 34.5 Agent authority

An agent might rewrite documentation confidently based on incomplete evidence.

Mitigation: Hydra creates bounded evidence packages; agents propose changes;
mechanical checks determine affected surfaces; plans and assumptions remain
labeled.

## 34.6 Space and wiki leakage

Business or repository-local knowledge could appear in Hydra-managed
documentation.

Mitigation: explicit projection scopes; wiki ownership; allowed source spaces;
boundary validation in `docs audit`.

## 34.7 Generic guidance presented as fact

Portable architecture guidance might cause incorrect claims about a repository.

Mitigation: epistemic categories; source-derived evidence; repository decisions
overriding generic guidance; clear visual labeling in agent context and
websites.

## 34.8 The graph itself becoming stale

A stale dependency graph would create false confidence.

Mitigation: rebuild deterministic parts in CI; track graph provenance; display
the represented commit; fail closed for high-contract generated reference.

## 34.9 Website becoming a second source of truth

Direct website editing could bypass repository review.

Mitigation: static site initially; repository-backed Markdown and JSON;
CI-generated deployment; website displays source commit and file links.

## 34.10 Private or sensitive knowledge exposure

A generated public site could accidentally include private spaces.

Mitigation: explicit projection allowlists; public/private classifications; CI
checks for forbidden spaces and objects; separate builds when necessary;
default-deny behavior for unclassified sensitive sources.

---

# 35. Design principles

1. Repository reality outranks documentation.
2. Plans must never masquerade as implemented behavior.
3. Wikis remain human-readable Markdown.
4. The Hydra wiki remains a distinct Hydra-managed wiki.
5. Repositories may create any number of their own wikis.
6. `project-wiki/` is a host, not one monolithic wiki.
7. Knowledge spaces and wikis are different concepts.
8. Spaces compose rather than inherit.
9. One object may participate in multiple spaces.
10. Generated documentation owns mechanical facts.
11. Humans own explanation, reasoning, and trade-offs.
12. The website is a projection, not a source of truth.
13. CI should detect impact and drift without pretending to understand
    arbitrary prose.
14. Agents may assist with reconciliation but should not silently redefine
    truth.
15. Every generated artifact should identify its provenance and represented
    commit.
16. The first implementation should be useful before it becomes sophisticated.

---

# 36. Open architectural questions

1. Can Hydra's existing operational query store represent documentation, wiki,
   claim, and projection objects cleanly?
2. Should documentation use the existing relation model unchanged?
3. Does Hydra already have a generic projection abstraction that should be
   extended?
4. Where should wiki manifests live?
5. Should documentation metadata use frontmatter, a central registry, Hydra
   objects, or a hybrid?
6. What is the minimum stable documentation identity?
7. Should pages, sections, and claims all have Hydra identities?
8. How should renamed and moved documents preserve identity?
9. How should verification state be recorded?
10. Should staleness use commits, file hashes, object hashes, semantic
    fingerprints, or multiple mechanisms?
11. Which documentation categories should block CI?
12. How should intentional non-impact be acknowledged?
13. How should generated blocks be updated without damaging authored prose?
14. Which graph views provide actual value in the MVP?
15. How should projection boundaries prevent knowledge leakage?
16. How should conflicting spaces resolve authority?
17. How should external portable spaces be versioned?
18. Should CLI naming use `docs`, `wiki`, `projection`, or a combination?
19. Should the website be one unified portal or support independently deployed
    wiki surfaces?
20. Which static-site framework best fits the existing repository without
    controlling the architecture?
21. Can the website consume a stable Hydra-generated JSON contract?
22. How should site previews work for pull requests?
23. What is the migration path for existing `project-wiki` content?
24. How much of the current Source Map can become the first dependency
    registry?
25. Which current-main capabilities are missing or poorly represented in the
    Hydra wiki?

---

# 37. Expected review deliverables

## A. Current-state reconstruction

Existing relevant components, existing object families, current graph/query
capabilities, current documentation validation, current projection behavior,
current wiki ownership model, current CI behavior.

## B. Gap analysis

For every proposed component:

```text
existing
partially existing
missing but valuable
missing and premature
conflicts with current architecture
```

## C. Revised architecture

Recommended boundaries, object model, relationship model, storage and
provenance, commands, CI behavior, website data contract, security and access
boundaries.

## D. MVP plan

A small implementation sequence with exact outcomes, dependencies, acceptance
criteria, tests, migration considerations, and estimated complexity.

## E. Future roadmap

Clearly separated from the MVP.

## F. Challenge section

Where this proposal over-engineers the problem; where it underspecifies
important behavior; which naming is misleading; which abstractions duplicate
existing Hydra concepts; which parts should be deleted or postponed; whether
the generic projection concept genuinely belongs in Hydra's core.

---

# 38. Concise product statement

> Hydra ships with its own readable framework wiki and gives repositories the
> infrastructure to create and maintain any number of their own wikis.

Underneath:

> Hydra maintains structured, provenance-backed repository intelligence that
> powers agent context, documentation, graphs, impact analysis, generated
> reference, CI validation, and interactive websites.

The ultimate concept is:

```text
portable knowledge
        +
repository knowledge
        +
domain knowledge
        +
source evidence
        +
current work
        |
repository intelligence graph
        |
agents + humans + tooling
```

Or more concisely:

> Hydra understands the repository and projects the right view of that
> understanding for each consumer.

---

# 39. Final recommendation

Do not begin by building a complex documentation knowledge graph or website.

Start with:

```text
machine-readable wiki/source ownership
        |
page-level docs impact audit
        |
generated CLI reference
        |
one useful generated graph
        |
CI visibility
        |
static interactive website
```

Use Hydra's own stale framework wiki as the first dogfooding target. Once that
works reliably, generalize the infrastructure for project, business,
operations, architecture, and other repository-defined wikis.

The website should arrive relatively early because it immediately makes the
material easier to navigate and demonstrates the value of the model. However,
it must consume repository-owned artifacts instead of becoming a separate
documentation platform.

The desired result is not merely better documentation tooling. It is:

> Multi-domain, provenance-backed repository intelligence with wikis, agent
> context, graphs, impact analysis, CI, and interactive websites as controlled
> projections of the same underlying truth.
