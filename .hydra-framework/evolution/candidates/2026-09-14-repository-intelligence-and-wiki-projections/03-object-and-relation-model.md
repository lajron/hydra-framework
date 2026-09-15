# Part 3: Object And Relation Model

Part of the candidate
[`2026-09-14-repository-intelligence-and-wiki-projections`](../2026-09-14-repository-intelligence-and-wiki-projections.md).
Original proposal text, preserved. Section numbers are the author's.

---

# 13. Documentation as an object family

Documentation should become a Hydra-managed object family rather than a
separate unrelated Markdown subsystem.

Possible identities:

```text
hydra://documentation/concepts/context-compilation
hydra://documentation/reference/commands
hydra://documentation/guides/adoption
hydra://documentation/architecture/execution
```

A documentation object represents a documentation concept. It does not
necessarily have a one-to-one relationship with a physical file.

Example:

```yaml
hydra_id: hydra://documentation/concepts/context-compilation
kind: documentation

title: Context Compilation
doc_kind: concept

audiences:
  - user
  - contributor
  - maintainer

relations:
  - type: documents
    target: hydra://capability/context-compilation

  - type: documents
    target: hydra://engine-module/knowledge/context-providers

  - type: related-to
    target: hydra://documentation/concepts/knowledge

provenance:
  sources:
    - .hydra-framework/engine/src/hydra_engine/knowledge/context_providers.py
    - .hydra-framework/repo/knowledge/spaces/hydra-framework/

outputs:
  - project-wiki/hydra-framework/concepts/context-compilation.md
```

The reviewer should determine whether metadata belongs in Markdown
frontmatter, a central registry, existing Hydra object metadata, generated
indexes, or a hybrid of those mechanisms.

---

# 14. Important object families

The underlying model may eventually include: Repository, Source file, Source
symbol, Module, Command, Command argument, Schema, Provider, Profile, Reducer,
Validator, Capability, Workflow, State transition, Business rule, Decision,
Constraint, Guidance, Assumption, Evidence, Test, Validation, Telemetry
evidence, Task, Knowledge unit, Knowledge space, Wiki, Documentation concept,
Documentation page, Documentation section, Documentation claim, Generated
block, Diagram, Projection.

This list must not automatically become the first implementation. The review
should identify which identities already exist and which new types provide
enough value to justify their maintenance cost.

---

# 15. Relationship vocabulary

A controlled relation vocabulary may include:

| Relation | Example |
| --- | --- |
| `implements` | Source module implements capability |
| `owns` | Module owns command |
| `documents` | Page documents capability |
| `appears-in` | Claim appears in documentation section |
| `supported-by` | Claim is supported by evidence |
| `evidence-for` | Test provides evidence for capability |
| `tested-by` | Rule is tested by a test |
| `enforced-by` | Business rule is enforced by validator |
| `governed-by` | Workflow is governed by rule |
| `depends-on` | Capability depends on provider |
| `generated-from` | CLI page is generated from command metadata |
| `projects-to` | Object projects into wiki or adapter |
| `belongs-to` | Capability belongs to domain |
| `draws-from` | Wiki draws knowledge from space |
| `supersedes` | Decision replaces older decision |
| `overrides` | Repository decision overrides guidance |
| `related-to` | Non-authoritative semantic association |

The vocabulary should stay intentionally small at first. Ambiguous generic
relations will reduce the usefulness of impact analysis.

---

# 16. Claim-level documentation tracking

A page is not necessarily stale as one atomic unit. Often, only one durable
factual claim became questionable.

Example claim:

> Context compilation supports Knowledge, Capability, Work, Source,
> Runtime/Engine, and Telemetry object families.

The corresponding internal model might be:

```text
claim://docs/context-compilation/supported-families

value:
  - knowledge
  - capability
  - work
  - source
  - runtime-engine
  - telemetry

supported-by:
  source://context-providers-registry

appears-in:
  documentation://context-compilation#supported-families
```

If another family is added to the implementation, Hydra could report:

```text
DOCUMENTATION IMPACT

Claim affected:
  Context Compilation -> Supported families

Reason:
  Context-provider registry changed

Previous evidence:
  sha256:3c720338...

Current evidence:
  sha256:a87e...

Suggested action:
  Review the supported-family claim
```

Claim-level metadata should not be mandatory for ordinary prose. Use it
selectively for durable factual assertions such as supported object families,
default behavior, command parameters, state transitions, trust boundaries,
generated paths, schema contracts, compatibility guarantees, required
validation gates, registered providers, and capability inventories.

Human rationale and explanatory prose should remain normal authored content.
Claim-level tracking is a later-stage capability, not necessarily the MVP.

---

# 17. Authored, generated, and hybrid documentation

Documentation should explicitly declare how it is maintained.

## 17.1 Authored documentation

Humans explain why a feature exists, concepts, architecture reasoning,
trade-offs, tutorials, guides, examples, migration reasoning, and operational
advice.

## 17.2 Generated documentation

Hydra describes exact mechanical facts: CLI commands and options, registered
object families, provider capabilities, profile inventories, schema reference,
validation checks, reducers, extension points, supported adapters, and
generated provider surfaces.

## 17.3 Hybrid documentation

Human explanation with generated factual sections:

```markdown
# Context Compilation

Context compilation exists because...

[Human-written explanation and trade-offs.]

## Supported families

<!-- hydra:generated query="context-providers" -->

| Family |
| --- |
| Knowledge |
| Capability |
| Work |
| Source |
| Runtime / Engine |
| Telemetry |

<!-- /hydra:generated -->

## Context flow

<!-- hydra:graph capability="context-compilation" -->

[Generated Mermaid diagram.]

<!-- /hydra:graph -->
```

This keeps documentation readable while eliminating duplicated mechanical
facts.

---

# 18. Source and dependency mapping

Every important documentation object or page should be connected to its owning
sources. A minimal model might look like:

```yaml
document: project-wiki/hydra-framework/concepts/context-retrieval.md
maintenance: hybrid
audiences:
  - user
  - contributor

sources:
  - .hydra-framework/engine/src/hydra_engine/knowledge/context_providers.py
  - .hydra-framework/repo/knowledge/spaces/hydra-framework/

documents:
  - capability://context-retrieval
  - capability://context-compilation

last_verified:
  commit: abc123
  source_digest: sha256:...
```

Hydra should be able to answer "Which documentation depends on this changed
source?" and "What implementation and evidence support this page?".

The initial implementation can operate at page-to-source granularity before
introducing claims.

---

# 29. Business rules as first-class objects

For enterprise repositories, business rules may deserve stable identities:

```text
rule://reservation/departure-after-arrival
rule://fiscalization/refund-requires-original-reference
rule://reception/checkin-requires-room-assignment
```

Example:

```text
rule://reservation/departure-after-arrival
    |-- defined-in -> space://hms/reception/reservations
    |-- enforced-by -> ReservationValidator.cs
    |-- tested-by -> ReservationValidatorTests.cs
    |-- documented-by -> Reservation Rules
    `-- used-by -> Create Reservation
                   Modify Reservation
                   Reservation Import
```

If enforcement changes, Hydra could report:

```text
BUSINESS RULE IMPACT

Rule:
  departure-after-arrival

Enforcement source changed.

Affected workflows:
  Create Reservation
  Modify Reservation
  Reservation Import

Tests:
  coverage found

Documentation:
  verification required
```

This should be introduced only where rules are valuable enough to justify
stable identity. Not every conditional statement in code is a business-rule
object.

---

# 28. Example in a real HMS repository

Suppose a repository contains:

```text
Reception/
  Reservations/
    CreateReservationCommand.cs

Infrastructure/
  Persistence/
    ReservationRepository.cs
```

Knowledge may come from:

```text
space://dotnet-architecture
space://hms-domain
space://hms/reception
space://hms/reception/reservations
```

The handler might be represented as:

```text
CreateReservationCommandHandler
    |-- belongs-to -> Reception
    |-- implements -> Command Handler Pattern
    |-- participates-in -> Reservation Lifecycle
    |-- uses -> ReservationRepository
    `-- governed-by -> Reservation Creation Rules
```

An agent changing it receives relevant composed context. A human reading the
project wiki sees a clear reservation workflow. A maintainer reviewing a PR
sees its impact on architecture, business rules, tests, and documentation.

All three views come from the same underlying repository intelligence.
