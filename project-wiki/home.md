# Hydra Project Wiki

Audience: A teammate who is new to this repository

Reader goal: Choose the right first page for the work in front of you

Page type: orientation

## Answer

This is the front door to the human-facing Hydra documentation. If you have a
fresh clone, open [Start Here](/project-wiki/hydra-framework/start-here/start-here.md).
If you are ready to make a change, use the [New Contributor
route](/project-wiki/hydra-framework/start-here/new-contributor.md). If you are
bringing Hydra to another repository, use [Seed And Adopt
Hydra](/project-wiki/hydra-framework/start-here/adopt-a-repository.md).

For every other question, choose the route that matches the decision you need
to make.

## A concrete situation

You have a task but do not know whether to search for context, inspect a task
record, change a capability, or run a validation gate. Start with [Start
Here](/project-wiki/hydra-framework/start-here/start-here.md), then follow one
specialized route. The wiki gives the explanation; the linked canonical source
owns the exact rule or current result.

## What Hydra is

Hydra keeps repository-owned rules, canonical knowledge, reusable capabilities,
owner-scoped task state, provider adapters, and validation in one inspectable
working layer. In plain language, it gives people and agents a shared place to
find context, continue work, expose repeatable behavior, and check the result.

`.hydra-framework/` is the canonical shared system. `.hydra-framework.local/`
is private, ignored machine and developer state. `project-wiki/` explains and
routes the system for people. The [Hydra Framework](/project-wiki/hydra-framework/hydra-framework.md)
page provides the detailed map, and the [wiki surface
contract](/.hydra-framework/surfaces/README.md) defines these boundaries.

## Choose a route

| If you need to... | Start here | The route answers |
| --- | --- | --- |
| Choose a first stop | [Start Here](/project-wiki/hydra-framework/start-here/start-here.md) | Which audience route fits your situation |
| Prepare a fresh clone | [New Contributor](/project-wiki/hydra-framework/start-here/new-contributor.md) | What to initialize, export, and check |
| Start or continue repository work | [Working With Hydra](/project-wiki/hydra-framework/working-with-hydra/working-with-hydra.md) | How to find context, track work, and verify a change |
| Understand the whole framework | [Hydra Framework](/project-wiki/hydra-framework/hydra-framework.md) | How the major areas and boundaries fit together |
| Find reusable behavior | [Capabilities](/project-wiki/hydra-framework/extending-hydra/capabilities.md) | Skills, agents, workflows, profiles, and provider surfaces |
| Check orchestration boundaries | [Execution Stack](/project-wiki/hydra-framework/architecture/execution-stack.md) | What the coordination model means and what it does not imply |
| Retrieve bounded context | [Context Retrieval](/project-wiki/hydra-framework/architecture/context-retrieval.md) | When to use search, route pointers, or a context packet |
| Trace identity, ownership, or provenance | [Object And Context Model](/project-wiki/hydra-framework/architecture/object-context-model.md) | How IDs, relations, sources, and derived stores fit together |
| Validate, diagnose, or check source freshness | [Operations](/project-wiki/hydra-framework/operations/operations.md) | Which safe gate or diagnostic to run |
| Look up a command or term | [Reference](/project-wiki/hydra-framework/reference/reference.md) | Where exact command, source, glossary, and authoring details live |
| Adopt, migrate, or extend Hydra | [Extending Hydra](/project-wiki/hydra-framework/extending-hydra/extending-hydra.md) | How to change or bring in material safely |
| Reconcile a changed Hydra copy | [Evolution](/project-wiki/hydra-framework/evolution/evolution.md) | How to compare a copy with its base and record divergence |

## Important boundary

Hydra uses a conceptual execution stack from Coordination Graph to Model. A
name in that stack is a responsibility map, not by itself evidence of an
unattended scheduler, a worker service, or a provider SDK. Read [Execution
Stack](/project-wiki/hydra-framework/architecture/execution-stack.md) for the
implemented-versus-conceptual boundary and [Provider
Adapters](/project-wiki/hydra-framework/extending-hydra/provider-adapters.md)
for the runtime trust boundary.

## Current status owners

The wiki is not the live status store. Follow the canonical owner for the
current answer:

| Question | Canonical owner |
| --- | --- |
| What is built? | [Build Status](/.hydra-framework/repo/knowledge/spaces/hydra-framework/units/build-status.md) |
| What is the current framework handoff? | [Framework State](/.hydra-framework/repo/knowledge/spaces/hydra-framework/state.md) |
| What concerns remain open? | [Framework Problems](/.hydra-framework/repo/knowledge/spaces/hydra-framework/problems.md) |
| Which high-impact questions are unresolved? | [Unresolved Questions](/.hydra-framework/core/unresolved-questions.md) |

## Next action

Open [Start Here](/project-wiki/hydra-framework/start-here/start-here.md) and
choose the row that matches your role.

## Sources

- [Root README](/README.md)
- [Hydra Framework README](/.hydra-framework/README.md)
- [Knowledge surface contract](/.hydra-framework/surfaces/README.md)
- [Architecture](/.hydra-framework/core/architecture.md)
- [Placement rules](/.hydra-framework/core/placement-rules.md)
