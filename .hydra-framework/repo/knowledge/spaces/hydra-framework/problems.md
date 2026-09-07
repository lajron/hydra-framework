---
hydra_id: "hydra://knowledge-slice/hydra-framework/problems"
uid: "3b5cdad3-e87f-4af2-b8c6-c5353c7a6d6e"
schema_version: "3"
kind: "knowledge-slice"
title: "Hydra Framework Problems"
status: "active"
scope: "base-seed"
owners:
  team: "hydra"
relations:
  - type: "relates-to"
    target: "hydra://knowledge-space/hydra-framework"
provenance:
  sources: []
---

# Problems

Status: active
Updated: 2026-09-07

Concrete unresolved concerns for Hydra's own machinery. Each needs evidence, not
opinion. Resolve or close with a reason; do not let entries rot.

## Open

### P4: Routing re-reads the whole knowledge tree on every call

- Evidence: `validation/knowledge-v3/engine_gates.py` over the checked-in 216-leaf fixture. `discover_knowledge_nodes` costs about 25 ms for the 258-node materialized tree, and `route_nodes` calls it per invocation, so routing cost scales with tree size rather than with the number of selected nodes.
- Impact: negligible in a repository with one space, and a per-prompt cost in a repository with hundreds of nodes, where every `route-prompt` and `compile-context` call pays a full parse of canonical files.
- Resolution: unresolved. The `KnowledgeStore` interface in `core/knowledge-architecture.md` exists for this: canonical files stay the source of truth while a derived, rebuildable index serves discovery. Implementing that cache is a separate workstream from Knowledge v3 itself, and a stale index must still be unable to authorize an invalid reference or a stale binding. Do not add a cache that selected content is not re-read against.
- Certainty: confirmed

### P1: Codex capability classes resolve to no model

- Evidence: `.hydra-framework/adapters/providers/codex/capability-map.yaml` maps every capability class to `unresolved`; only `effort_budgets` resolve.
- Impact: generated `.codex/agents/*.toml` omit `model`, so every Hydra role runs on whatever model the host's Codex config selects. Capability-based routing does not reach Codex.
- Resolution: deliberate, not pending. Codex exposes concrete model slugs rather than stable aliases, and the only available source is the local account's model catalog — machine- and plan-specific state that does not belong in shared framework truth, and that would override the host's own `model` setting. Revisit if Codex publishes stable aliases.
- Certainty: confirmed

### P2: `diff-base` needs a base checkout on disk

- Evidence: `command_diff_base` requires `--base <path>`.
- Impact: reconciliation cannot run in a repository that has no local copy of the base seed.
- Resolution: unresolved. Fetching a base by Git ref or URL would remove the requirement but adds network and trust surface. Wait for a real second repository before designing it.
- Certainty: inferred

### P3: Promotion metadata is a guess

- Evidence: `promote_surface` writes `capability_class: fast-default` and `effort: standard` for any promoted agent.
- Impact: a promoted subagent runs at default routing until a human reviews it.
- Resolution: acceptable by design — the metadata is marked `certainty: inferred` and `scope: repo-local` so review is expected. Revisit only if reviews are routinely skipped.
- Certainty: confirmed

## Resolved

### R1: Adapter drift was undetectable (2026-07-30)

`export-adapters` had no `--check`, so a stale wrapper could not be caught in CI. Resolved by `--check`/`--dry-run` plus a single planner shared by generate, check, and classify.

### R2: Canonical agents were never exported (2026-07-30)

`modules/agents/` existed with four roles that no runtime could dispatch. Resolved by generating `.claude/agents/`.

### R3: Capability vocabulary had no bindings (2026-07-30)

Capability classes and effort budgets were defined but mapped to nothing. Resolved by per-provider capability maps, with validation that every used class and budget has an entry.

### R4: Task contract lived in six places (2026-07-30)

Resolved by one prose source, one executable list, one template, and a drift check across all three.

### R5: Codex agent roles were unreachable (2026-07-30)

Canonical roles in `modules/agents/` had no Codex surface. Resolved after the
Codex manual confirmed project-scoped custom agents at `.codex/agents/*.toml`
with required `name`, `description`, and `developer_instructions`. Hydra now
generates them. The model half of the map stayed unresolved — see P1.

### R6: Deliberate divergence was indistinguishable from drift (2026-07-30)

`diff-base` reported every difference as equally suspicious, so a repository
that had correctly adapted Hydra re-litigated the same paths at every
reconciliation. Resolved by `evolution/adaptations.md` plus an explained /
unexplained split.

### R7: Claude model-catalog checks were a wasteful maintenance path (2026-07-30)

The Claude capability map recorded full provider model IDs as reference data, which made
future agents likely to call provider model catalogs just to refresh volatile
IDs the exporter did not use. Resolved by deleting that reference field and documenting an
alias-only policy. Concrete IDs should be added only for a provider surface that
cannot use aliases.
