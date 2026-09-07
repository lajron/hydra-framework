---
hydra_id: "hydra://knowledge-slice/hydra-framework/overview"
uid: "e86b49f5-8055-4aeb-a001-084148d578bc"
schema_version: "3"
kind: "knowledge-slice"
title: "Hydra Framework Itself"
status: "active"
scope: "base-seed"
owners:
  team: "hydra"
relations: []
provenance:
  sources:
    - ".hydra-framework/scripts/hydra.py"
    - ".hydra-framework/engine/src/hydra_engine/"
    - ".hydra-framework/engine/tests/"
---

# Hydra Framework Itself

Status: active
Certainty: verified

## Purpose

This package owns knowledge about Hydra's own machinery: how canonical modules
become provider surfaces, how a copy is adopted into a repository, and how a
diverged copy is reconciled against the base seed.

It exists because this repository's product *is* the framework, so framework
mechanics are the subject matter an agent most often needs to look up. It is also
the reference example for what a knowledge package looks like.

## Boundaries

In scope:

- The export pipeline: canonical modules -> provider wrappers -> provenance sidecars.
- Capability class and effort budget resolution per provider.
- Adoption, lineage, and seed reconciliation.
- Provider surface classification and reclamation.
- Task-record and validation contracts.

Out of scope:

- Framework *principles* and placement policy. Those live in `.hydra-framework/core/`; this package explains mechanics, not rules.
- Teammate-facing explanation of Hydra. That is `project-wiki/hydra-framework/`.
- Any host repository's product code.

## Source Of Truth Policy

- `.hydra-framework/engine/src/hydra_engine/` is authoritative for what the tooling actually does. `.hydra-framework/scripts/hydra.py` is the compatibility entrypoint.
- `.hydra-framework/core/` is authoritative for framework rules.
- Provider behavior is authoritative from the provider's own documentation. Record the checked date in `sources.md`.
- The bundled tests in `.hydra-framework/engine/tests/` are executable evidence for the claims here.

## If You Have Never Read This Before

1. [State](state.md)
2. [Glossary](glossary.md)
3. [Routing](space.yaml) -- its `routes:` are the scoped starts; `units/` holds what they point at.
4. [Architecture Graph](architecture/00-graph.md)

## Reading Map

| Need | Start here |
| --- | --- |
| Current work and handoff | [State](state.md) |
| Define a term | [Glossary](glossary.md) |
| Pick units to read for a task | [Routing](space.yaml) |
| Navigate related slices | [Architecture Graph](architecture/00-graph.md) |
| Track unresolved concerns | [Problems](problems.md) |
| Know when the package is done enough | [Definition Of Done](definition-of-done.md) |
| Where source material came from | [Sources](sources.md) |

## Command Surface

| Command | Purpose |
| --- | --- |
| `doctor` | Required paths, surface state, lineage, then full validation |
| `validate` | Task records, module metadata, capability maps, surfaces, object references, package docs, and engine architecture |
| `selftest` | Bundled engine unit, repository, and contract tests |
| `export-adapters [--check] [--dry-run]` | Generate provider skills and subagents |
| `reclaim [--promote]` | Classify and promote provider-native files |
| `adopt [--record]` | Integration report and lineage stamping |
| `init --target <repo>` | Copy the framework into another repository |
| `init-local [--check] [--write-token-policy]` | Seed and check the ignored private tier |
| `diff-base --base <path>` | Classify this copy against its base seed |
| `route-prompt`, `hook-post-edit`, `hook-token` | Hook entry points |
| `measure-context`, `compile-context`, `summarize-log`, `retry-guard` | Token and context tooling |
| `task start\|checkpoint\|complete` | Task-state maintenance |
| `wiki scaffold`, `validate-wiki`, `validate-package-docs` | Documentation surfaces |

## Validation

```bash
python3 .hydra-framework/scripts/hydra.py validate-package-docs --path .hydra-framework/repo/knowledge/spaces/hydra-framework
```
