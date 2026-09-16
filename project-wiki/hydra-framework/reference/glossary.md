# Glossary

Audience: A reader who has encountered a Hydra term and needs its plain-language meaning

Reader goal: Translate the term and reach the page or command that owns the next decision

Page type: reference

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md).

Use this page to translate vocabulary, not to replace the linked canonical
rules. When a definition changes the action you should take, follow its route.

## Adapter

A provider-specific surface that makes Hydra visible to a runtime. Examples include `AGENTS.md`, `CLAUDE.md`, `.agents/`, `.claude/`, and `.codex/`. The provider adapter contract owns the boundary.

## Canonical Source

The version-controlled file that owns a rule or behavior. The wiki links to a
canonical source instead of becoming a competing source of truth. See the
[knowledge surface contract](/.hydra-framework/surfaces/README.md).

## Canonical Knowledge

Verified durable repository knowledge stored under `.hydra-framework/repo/knowledge/`,
as described by the [placement rules](/.hydra-framework/core/placement-rules.md).

## Baseline Tag

A tag listed in a capability profile policy's `baseline_tags` that stays
selected in every profile, regardless of which profile is active. See
[Capability Profiles And Tags](/project-wiki/hydra-framework/extending-hydra/capabilities.md#capability-profiles-and-tags).

## Capability Profile

A named set of tags that narrows which canonical skills
`hydra.py export-adapters` materializes as provider adapters for one
checkout. Agents are never filtered by profile. See
[Capability Profiles And Tags](/project-wiki/hydra-framework/extending-hydra/capabilities.md#capability-profiles-and-tags).

## Checkpoint

A concise recovery record created when work pauses, blocks, or needs handoff.

## Cognition

Generated or rebuildable model-facing structures such as indexes, graphs, summaries, or retrieval metadata. Their boundary is defined by the placement rules.

## Context Packet

A bounded reading result from `compile-context`. It records selected and
required context, omitted candidates, token estimates, provenance and
freshness information, and validation reminders. It is a view over canonical
files, not canonical knowledge. See [Context Retrieval](/project-wiki/hydra-framework/architecture/context-retrieval.md)
and the [Object And Context Model](/project-wiki/hydra-framework/architecture/object-context-model.md).

## Derived Store

Rebuildable local state used to accelerate a query, such as the knowledge
search index or object reference store. A stale store is a cache or evidence
condition to diagnose, not a reason to edit canonical source. See [Operations](/project-wiki/hydra-framework/operations/operations.md).

## Execution Harness

The layer that supplies instructions, tools, environment, state, and feedback around a model.

## Coordination Graph

The execution-stack responsibility for coordinating tasks, agents, dependencies,
handoffs, and recovery across loops. It is an architectural boundary, not by
itself proof of an unattended scheduler, worker service, or provider SDK. See
[Execution Stack](/project-wiki/hydra-framework/architecture/execution-stack.md).

## Orchestration Run

A provider-neutral local control-plane record anchored to one existing task
record, with an explicit owner and bounded worker requests. It is not a shared
task-record replacement or proof of provider execution.

## Worker Ownership

The explicit owner and optional parent worker recorded for one orchestration
worker. Parent-worker authorization is required for nested spawn; age or a
missing response never changes ownership.

## Request-Only Adapter

A provider boundary that accepts a bounded spawn, message, or collect request
for queueing or acknowledgement without claiming that a provider runtime
executed it. Claude and Codex currently use this boundary.

## Hydra

Repository-contained, provider-neutral AI-work infrastructure for shared
context, reusable capabilities, task state, adapters, and validation. The root
[README](/README.md) is the public orientation; the
Hydra README owns the internal framework map.

## Intake

The review path for source material before it becomes trusted canonical knowledge.

## Binding

A named mapping from a portable logical resource such as `@namespace/key` to a
repository file, directory, or glob plus assertions that verify the target.
Stale or ambiguous bindings cannot drive automatic path routing. See [Knowledge
Spaces](/project-wiki/hydra-framework/extending-hydra/knowledge-spaces.md).

## Route

A `space.yaml` or `node.yaml` entry for one task shape. It names when the route
applies, which units have priority, what is always required, what to avoid, and
how to verify the work. See [Context Retrieval](/project-wiki/hydra-framework/architecture/context-retrieval.md)
and [Knowledge Spaces](/project-wiki/hydra-framework/extending-hydra/knowledge-spaces.md).

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

## Provenance

The source trail that explains where a durable claim, object, or page gets its
meaning. Object provenance is part of canonical metadata; wiki source
declarations point to the files that support page claims. See the [Source
Map](/project-wiki/hydra-framework/reference/source-map.md).

## Source Declaration

The list of canonical files a managed wiki page names as support for its
durable claims. A declaration supports freshness checking, but it does not
prove that the list is complete or that the prose is correct. See the [wiki
surface contract](/.hydra-framework/surfaces/README.md).

## Source Freshness

Whether a declared source is present and its recorded digest and check date
still describe the current source. Source freshness is evidence of possible
drift, not a documentation completeness score. See [Operations](/project-wiki/hydra-framework/operations/operations.md).

## Wiki Audit

The report-only check that compares managed wiki pages with their declared
source files, dates, and digests. It can return successfully while reporting
findings, so the report still needs review. See [Documentation Authoring](/project-wiki/hydra-framework/reference/documentation-authoring.md)
and [Operations](/project-wiki/hydra-framework/operations/operations.md).

## Reference Graph

The identity and relation graph connecting Hydra objects and their source
paths. `ref check` validates it, `ref index` refreshes a rebuildable registry,
and `ref rdeps` or `ref impact` answer graph questions through a fresh query
store. See [Object And Context Model](/project-wiki/hydra-framework/architecture/object-context-model.md)
and [Operations](/project-wiki/hydra-framework/operations/operations.md).

## Knowledge Space

A local mini knowledge base for one accountability boundary with durable
complexity, listed in `spaces.yaml` and rooted at a `space.yaml`. See
[Knowledge Spaces](/project-wiki/hydra-framework/extending-hydra/knowledge-spaces.md).

## Knowledge Node

A descendant boundary inside a space, carrying its own `node.yaml`. The tree is
three levels deep by default and four at most, counting the space.

## Operational Readiness

The pre-execution check that records whether meaningful work can proceed safely.

## Ownership Index

The set of provider adapter paths derivable from currently existing canonical
skills and agents. Hydra deletes a generated provider path only when it is a
member of this index and passes every other ownership condition; membership
alone is not enough. See
[Ownership And Safe Deletion](/project-wiki/hydra-framework/extending-hydra/provider-adapters.md#ownership-and-safe-deletion).

## Reclaim

The provider-surface classification and promotion route for files Hydra cannot
currently prove it owns. It distinguishes generated, drifted, orphaned, and
stale files before any promotion or removal decision. See [Provider
Adapters](/project-wiki/hydra-framework/extending-hydra/provider-adapters.md).

## Seed Reconciliation

The review route for comparing a changed Hydra copy with its base seed and
deciding whether each difference stays local or flows back. It does not
overwrite either side automatically. See [Evolution](/project-wiki/hydra-framework/evolution/evolution.md).

## Provider Neutrality

Hydra depends on capabilities rather than one model vendor. Provider-specific behavior belongs in adapters or private local configuration.

## Task State

Personal-tier Markdown state for non-trivial work that should be resumable. Records
live in `.hydra-framework/tasks/personal/<owner>/` and are tracked. Read anyone's;
edit only your own. The task lifecycle workflow
owns the record contract.
