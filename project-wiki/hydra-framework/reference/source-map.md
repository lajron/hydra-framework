# Source Map

This page routes material wiki claims to the canonical owner that can confirm
or correct them. The wiki explains and navigates; it does not replace these
owners.

## Maintainer Evidence

The rows below keep source traceability in one maintainer-facing place. Reader
journeys should start from the linked wiki route; use the evidence links when
checking a claim or updating its owner.

| Wiki route | Claim | Canonical evidence |
| --- | --- | --- |
| [Hydra Framework](/project-wiki/hydra-framework/hydra-framework.md) | Framework purpose, entry flow, and repository rules | [`AI_SYSTEM.md`](/AI_SYSTEM.md), [Hydra README](/.hydra-framework/README.md), and [placement rules](/.hydra-framework/core/placement-rules.md) |
| [State Tiers](/project-wiki/hydra-framework/concepts/state-tiers.md) | State tiers and private/shared boundaries | [placement rules](/.hydra-framework/core/placement-rules.md), [state tiers](/.hydra-framework/repo/knowledge/state-tiers.md), and [surface contract](/.hydra-framework/surfaces/README.md) |
| [Architecture](/project-wiki/hydra-framework/architecture/architecture.md) | Architecture, execution stack, and lifecycle | [architecture](/.hydra-framework/core/architecture.md), [lifecycle](/.hydra-framework/core/lifecycle.md), [execution harness](/.hydra-framework/repo/knowledge/execution-harness.md), and owning engine modules/tests |
| [Working With Hydra](/project-wiki/hydra-framework/working-with-hydra/working-with-hydra.md) | Daily work and task records | [task lifecycle workflow](/.hydra-framework/capabilities/workflows/task-lifecycle.md), [task step state](/.hydra-framework/repo/knowledge/task-step-state.md), and [placement rules](/.hydra-framework/core/placement-rules.md) |
| [Capabilities](/project-wiki/hydra-framework/extending-hydra/capabilities.md) and [Provider Adapters](/project-wiki/hydra-framework/extending-hydra/provider-adapters.md) | Capabilities and provider adapters | [capability sources](/.hydra-framework/capabilities), [provider adapter contract](/.hydra-framework/adapters/providers/README.md), provider maps, and the [provider engine](/.hydra-framework/engine/src/hydra_engine/providers) |
| [Extension Points](/project-wiki/hydra-framework/extending-hydra/extension-points.md) and [Safe Extension Recipes](/project-wiki/hydra-framework/extending-hydra/extension-recipes.md) | Supported extension boundaries and required gates | [engine architecture](/.hydra-framework/engine/src/hydra_engine/architecture.py), extension registries, and focused engine tests |
| [Knowledge Spaces](/project-wiki/hydra-framework/extending-hydra/knowledge-spaces.md) | Knowledge spaces, nodes, routing, bindings, and node validation | [Knowledge v3 contract](/.hydra-framework/core/knowledge-architecture.md), [node checks](/.hydra-framework/engine/src/hydra_engine/knowledge/nodes.py), [document checks](/.hydra-framework/engine/src/hydra_engine/knowledge/package_checks.py), and the space's own knowledge sources |
| [Intake And Migration](/project-wiki/hydra-framework/extending-hydra/intake-and-migration.md), [Migration](/project-wiki/hydra-framework/extending-hydra/migration.md), and [Seed And Adopt Hydra](/project-wiki/hydra-framework/start-here/adopt-a-repository.md) | Source integration, migration, adoption, and lineage | [material migration workflow](/.hydra-framework/capabilities/workflows/material-migration.md), [intake lifecycle](/.hydra-framework/repo/knowledge/intake-lifecycle.md), and [adoption skill](/.hydra-framework/capabilities/skills/adoption/skill.md) |
| [Evolution](/project-wiki/hydra-framework/evolution/evolution.md) | Reflections, candidates, adaptations, and seed reconciliation | [evolution README](/.hydra-framework/evolution/README.md), [adaptations ledger](/.hydra-framework/evolution/adaptations.md), and seed comparison/tests |
| [Documentation Authoring](/project-wiki/hydra-framework/reference/documentation-authoring.md) | Wiki purpose, audiences, citation, and sync rules | [surface contract](/.hydra-framework/surfaces/README.md) and [wiki-authoring skill](/.hydra-framework/capabilities/skills/wiki-authoring/skill.md) |
| [Validation](/project-wiki/hydra-framework/operations/validation.md) and [Troubleshooting](/project-wiki/hydra-framework/operations/troubleshooting.md) | Validation inventory, diagnostics, and mechanical-proxy boundaries | [validation README](/.hydra-framework/validation/README.md), [validator registry](/.hydra-framework/engine/src/hydra_engine/checks/validator_registry.py), and [validation rules](/.hydra-framework/validation/rules) |
| [Wiki link behavior](/project-wiki/hydra-framework/reference/documentation-authoring.md#validation) | Wiki link behavior and root-relative navigation contract | [wiki command](/.hydra-framework/engine/src/hydra_engine/commands/wiki.py), [link validator](/.hydra-framework/engine/src/hydra_engine/wiki/links.py), and [wiki tests](/.hydra-framework/engine/tests/unit/wiki/test_links.py) |
| [Command Surface](/project-wiki/hydra-framework/reference/command-surface.md) | CLI command behavior and test evidence | [scripts README](/.hydra-framework/scripts/README.md), [compatibility shim](/.hydra-framework/scripts/hydra.py), [engine command modules](/.hydra-framework/engine/src/hydra_engine/commands), and [engine tests](/.hydra-framework/engine/tests) |
| [Command-Output Reducers](/project-wiki/hydra-framework/architecture/command-output-reducers.md) | Command-output reduction, redaction, and the unknown-command fallback | [`command_output` engine package](/.hydra-framework/engine/src/hydra_engine/command_output), its mirrored unit tests, and the command-result contract golden |
| [Context Retrieval](/project-wiki/hydra-framework/architecture/context-retrieval.md) | Knowledge-search, route-prompt, and compile-context retrieval mechanics | [`knowledge` engine package](/.hydra-framework/engine/src/hydra_engine/knowledge), its mirrored unit tests, and the knowledge contract goldens |
| [Telemetry Pipeline](/project-wiki/hydra-framework/architecture/telemetry.md) | Event capture, field classification, the redaction gate, and evidence-package mechanics | [`telemetry` engine package](/.hydra-framework/engine/src/hydra_engine/telemetry), its mirrored unit tests, and the [telemetry redaction contract](/.hydra-framework/repo/knowledge/telemetry-redaction-contract.md) |
| [Evidence and Telemetry](/project-wiki/hydra-framework/operations/evidence-and-telemetry.md) | Evidence boundaries and telemetry handling | [telemetry package contract](/.hydra-framework/repo/telemetry/README.md), [telemetry redaction contract](/.hydra-framework/repo/knowledge/telemetry-redaction-contract.md), and the Hydra package state |
| [Public Positioning Brief](/project-wiki/hydra-framework/reference/public-positioning.md) | Public claims, terminology, and evidence limits | [Hydra package overview](/.hydra-framework/repo/knowledge/spaces/hydra-framework/overview.md), [build-status unit](/.hydra-framework/repo/knowledge/spaces/hydra-framework/units/build-status.md), and the relevant implementation/test owners |
| [Common Questions](/project-wiki/hydra-framework/start-here/common-questions.md) | Unresolved surface questions and repository ownership routes | [unresolved questions](/.hydra-framework/core/unresolved-questions.md) and repository ownership records |

## Review Rule

Start with the claim's row, then read the exact canonical file or owning code
and test. If the owner has changed, update this map and the affected wiki page
together. Backtick paths are useful for readers but are not link validation, so
verify every path against the repository when this map changes.

Keep this table concise. If a claim needs more implementation detail than the
listed owner provides, add it here rather than scattering a raw source link
through a reader-facing page.
