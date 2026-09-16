# Reference

Audience: A teammate who knows the question and needs an exact lookup route

Reader goal: Find the right command, term, source owner, or documentation contract

Page type: reference

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md).

Status: orientation

Reference is the lookup hub. It answers where exact detail lives without
becoming a second source of truth. Use the linked canonical owner when a rule,
current status, or command result matters.

## Lookup by need

| If you need to... | Open | What it owns or routes |
| --- | --- | --- |
| Translate an unfamiliar Hydra term | [Glossary](/project-wiki/hydra-framework/reference/glossary.md) | Plain-language definitions and the next relevant page |
| Find a command by task | [Command Surface](/project-wiki/hydra-framework/reference/command-surface.md) | Command inventory, lookup guidance, and command owners |
| Trace a claim to canonical evidence | [Source Map](/project-wiki/hydra-framework/reference/source-map.md) | Source paths, code, tests, and ownership boundaries |
| Understand object identity and provenance | [Object And Context Model](/project-wiki/hydra-framework/architecture/object-context-model.md) | IDs, aliases, relations, stores, and path-aware context |
| Find or compile bounded context | [Context Retrieval](/project-wiki/hydra-framework/architecture/context-retrieval.md) | Search, route pointers, bindings, freshness, and packets |
| Write or review a wiki page | [Documentation Authoring](/project-wiki/hydra-framework/reference/documentation-authoring.md) | Reader contract, citations, source declarations, and validation |
| Check source freshness or navigation | [Operations](/project-wiki/hydra-framework/operations/operations.md) | Wiki audit, fingerprint boundary, link validation, and diagnostics |
| Understand capabilities and profiles | [Capabilities](/project-wiki/hydra-framework/extending-hydra/capabilities.md) | Canonical skills, agents, workflows, tags, and adapters |
| Understand orchestration responsibilities | [Execution Stack](/project-wiki/hydra-framework/architecture/execution-stack.md) | Implemented controls and conceptual coordination boundaries |
| Adopt, migrate, or reconcile Hydra | [Evolution](/project-wiki/hydra-framework/evolution/evolution.md) | Safe change and seed-divergence routes |
| Prepare a public claim | [Public Positioning Brief](/project-wiki/hydra-framework/reference/public-positioning.md) | Audience, terminology, evidence limits, and public wording |

## Safe lookup habits

Start with the route above, then read the canonical owner named on that page.
For command syntax, confirm the current parser with `python3
.hydra-framework/scripts/hydra.py <command> --help`. For a path whose ownership
is unclear, use `explain-path <path> --json` before editing. For a graph query,
check the derived-store status first because reverse-dependency and impact
queries require a fresh store.

## Important boundary

Reference pages are maps and explanations. They do not override `.hydra-framework/`
rules, task state, knowledge units, or engine behavior. The [wiki surface
contract](/.hydra-framework/surfaces/README.md) defines the relationship between
this human-facing surface and its canonical owners.

## Next action

Open [Glossary](/project-wiki/hydra-framework/reference/glossary.md) for a term,
[Command Surface](/project-wiki/hydra-framework/reference/command-surface.md) for
a command, or [Source Map](/project-wiki/hydra-framework/reference/source-map.md)
for provenance.

## Sources

- [Knowledge surface contract](/.hydra-framework/surfaces/README.md)
- [Hydra Framework overview](/.hydra-framework/repo/knowledge/spaces/hydra-framework/overview.md)
- [Object and context model](/project-wiki/hydra-framework/architecture/object-context-model.md)
- [Scripts README](/.hydra-framework/scripts/README.md)
