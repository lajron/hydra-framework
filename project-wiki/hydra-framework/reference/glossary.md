# Glossary

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

## Adapter

A provider-specific surface that makes Hydra visible to a runtime. Examples include `AGENTS.md`, `CLAUDE.md`, `.agents/`, `.claude/`, and `.codex/`. The provider adapter contract owns the boundary.

## Canonical Knowledge

Verified durable repository knowledge stored under `.hydra-framework/repo/knowledge/`, as described by the placement rules.

## Checkpoint

A concise recovery record created when work pauses, blocks, or needs handoff.

## Cognition

Generated or rebuildable model-facing structures such as indexes, graphs, summaries, or retrieval metadata. Their boundary is defined by the placement rules.

## Execution Harness

The layer that supplies instructions, tools, environment, state, and feedback around a model.

## Hydra

Repository-contained, provider-neutral AI-work infrastructure for shared
context, reusable capabilities, task state, adapters, and validation. The root
[README](/README.md) is the public orientation; the
Hydra README owns the internal framework map.

## Intake

The review path for source material before it becomes trusted canonical knowledge.

## Adoption

The non-destructive process of copying Hydra into a repository, recording
lineage, wiring the provider surfaces in use, and validating the result. It
does not migrate the repository's existing material. See [Seed And Adopt Hydra](/project-wiki/hydra-framework/start-here/adopt-a-repository.md).

## Ledger

The migration workspace's item-by-item account of source material, its verdict,
destination, and terminal status. See [Migrate A Bounded Source Area](/project-wiki/hydra-framework/extending-hydra/migration.md).

## Migration

The bounded source-area process for staging, inventorying, triaging, promoting,
redirecting, and closing every source item. It is different from per-source
intake. See [Migrate A Bounded Source Area](/project-wiki/hydra-framework/extending-hydra/migration.md).

## Promotion Record

A shared, self-contained record of durable meaning promoted from an outside
source, including its origin, privacy note, claim, destination, and evidence.
See the promotion record rule.

## Takeover

The explicitly scoped migration of a legacy non-Hydra or agentic setup. It is
separate from adoption and does not make provider surfaces canonical. See
[Take over legacy material](/project-wiki/hydra-framework/extending-hydra/migration.md#take-over-legacy-agentic-material).

## Knowledge Space

A local mini knowledge base for one accountability boundary with durable
complexity, listed in `spaces.yaml` and rooted at a `space.yaml`. See
[Knowledge Spaces](/project-wiki/hydra-framework/extending-hydra/knowledge-spaces.md).

## Knowledge Node

A descendant boundary inside a space, carrying its own `node.yaml`. The tree is
three levels deep by default and four at most, counting the space.

## Operational Readiness

The pre-execution check that records whether meaningful work can proceed safely.

## Provider Neutrality

Hydra depends on capabilities rather than one model vendor. Provider-specific behavior belongs in adapters or private local configuration.

## Task State

Personal-tier Markdown state for non-trivial work that should be resumable. Records
live in `.hydra-framework/tasks/personal/<owner>/` and are tracked. Read anyone's;
edit only your own. The task lifecycle workflow
owns the record contract.
