# Hydra Framework

Audience: A reader who understands the repository problem and needs the Hydra
system map

Reader goal: Choose one useful route and keep canonical ownership boundaries
clear

Page type: orientation

Hydra is repository-contained, provider-neutral AI-work infrastructure. It
gives people and agents a shared, inspectable working layer for canonical
knowledge, reusable capabilities, owner-scoped task state, provider adapters,
and mechanical validation.

Start with the root [README](/README.md) for the public explanation and
quick start. This page is the wiki route map: it sends each reader to operating
guides and source-traceable detail without repeating the landing page.

`.hydra-framework/` is the canonical shared system. `.hydra-framework.local/`
is private machine and developer state. `project-wiki/` explains and routes the
system for people. The [Source Map](/project-wiki/hydra-framework/reference/source-map.md)
points from a reader-facing claim to its canonical owner.

## Current status and boundaries

The wiki is a route map, not the live status store. Follow the owner that
answers the current question:

| Question | Canonical owner |
| --- | --- |
| What is implemented? | [Build Status](/.hydra-framework/repo/knowledge/spaces/hydra-framework/units/build-status.md) |
| What is the framework handoff? | [Framework State](/.hydra-framework/repo/knowledge/spaces/hydra-framework/state.md) |
| What concerns remain open? | [Framework Problems](/.hydra-framework/repo/knowledge/spaces/hydra-framework/problems.md) |
| Which high-impact questions remain open? | [Unresolved Questions](/.hydra-framework/core/unresolved-questions.md) |

## Choose a route

| Reader or need | Start here | Route |
| --- | --- | --- |
| First visit or uncertain role | [Start Here](/project-wiki/hydra-framework/start-here/start-here.md) | Audience routes and safe reading order |
| Fresh clone | [New Contributor](/project-wiki/hydra-framework/start-here/new-contributor.md) | Initialize, export, inspect ownership, and validate |
| Daily Hydra user | [Working With Hydra](/project-wiki/hydra-framework/working-with-hydra/working-with-hydra.md) | Retrieve context, manage task state, work, and verify |
| Find reusable behavior | [Capabilities](/project-wiki/hydra-framework/extending-hydra/capabilities.md) | Skills, agents, workflows, profiles, and provider surfaces |
| Understand orchestration | [Execution Stack](/project-wiki/hydra-framework/architecture/execution-stack.md) | Coordination responsibilities and implemented boundaries |
| Understand architecture | [Concepts](/project-wiki/hydra-framework/concepts/concepts.md) | State tiers, execution flow, and system structure |
| Retrieve context deliberately | [Context Retrieval](/project-wiki/hydra-framework/architecture/context-retrieval.md) | Search snippets, route pointers, bindings, and bounded packets |
| Trace identity or provenance | [Object And Context Model](/project-wiki/hydra-framework/architecture/object-context-model.md) | IDs, relations, source paths, and derived stores |
| Extend, adopt, or migrate | [Extending Hydra](/project-wiki/hydra-framework/extending-hydra/extending-hydra.md) | Capabilities, provider ownership, intake, and safe change routes |
| Reconcile a changed copy | [Evolution](/project-wiki/hydra-framework/evolution/evolution.md) | Compare a downstream copy with its base and record intent |
| Operate or diagnose | [Operations](/project-wiki/hydra-framework/operations/operations.md) | Choose validation, freshness, provenance, and troubleshooting checks |
| Look up exact terms or commands | [Reference](/project-wiki/hydra-framework/reference/reference.md) | Glossary, command surface, source map, and authoring rules |
| Prepare a public explanation | [Positioning Brief](/project-wiki/hydra-framework/reference/public-positioning.md) | Claims, audience, evidence, and terminology |

## The orchestration boundary

Hydra's execution stack names responsibilities from Coordination Graph through
Agent Loop, Execution Harness, Context Pack, Prompt, and Model. That vocabulary
does not by itself promise an unattended scheduler, a worker service, or a
provider SDK. Read [Execution Stack](/project-wiki/hydra-framework/architecture/execution-stack.md)
for the implemented-versus-conceptual boundary, then read [Provider
Adapters](/project-wiki/hydra-framework/extending-hydra/provider-adapters.md)
for what belongs to a provider runtime and what remains canonical Hydra meaning.

## First stops

- [Start Here](/project-wiki/hydra-framework/start-here/start-here.md) is the
  shortest role-based route.
- [Common Questions](/project-wiki/hydra-framework/start-here/common-questions.md)
  answers focused questions and sends each answer to its owning page.
- [Working With Hydra](/project-wiki/hydra-framework/working-with-hydra/working-with-hydra.md)
  is the practical daily route.
- [Operations](/project-wiki/hydra-framework/operations/operations.md) is the
  safe route for validation, source freshness, and diagnosis.
- [Reference](/project-wiki/hydra-framework/reference/reference.md) is the
  lookup hub for terms, commands, provenance, and documentation rules.

## Next action

Open [Start Here](/project-wiki/hydra-framework/start-here/start-here.md) and
follow the row that matches your role.

## Sources

- [Hydra Framework overview](/.hydra-framework/repo/knowledge/spaces/hydra-framework/overview.md)
- [Architecture](/.hydra-framework/core/architecture.md)
- [Ownership and composition](/.hydra-framework/core/ownership-and-composition.md)
- [Model neutrality](/.hydra-framework/core/model-neutrality.md)
- [Placement rules](/.hydra-framework/core/placement-rules.md)
- [Knowledge surface contract](/.hydra-framework/surfaces/README.md)
