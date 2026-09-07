---
hydra_id: hydra://knowledge-slice/hydra-framework/glossary
uid: 95311d29-a3ca-4ea4-b2c9-b9b3be46f55b
schema_version: 3
kind: knowledge-slice
title: Hydra Framework Glossary
status: active
scope: base-seed
owners:
  team: hydra
relations:
  - hydra://knowledge-package/hydra-framework
provenance:
  sources: []
---

# Hydra Framework Glossary

Status: active
Updated: 2026-07-30

Terms specific to Hydra's own machinery. Framework principles are defined in
`.hydra-framework/core/`.

| Term | Meaning |
| --- | --- |
| **Canonical module** | A skill, agent, or workflow under `.hydra-framework/capabilities/`. The source of truth for its meaning. |
| **Provider surface** | A file under `.claude/`, `.agents/`, or `.codex/`. An adapter for runtime discovery, never a source of truth. |
| **Wrapper** | A generated provider surface produced from a canonical module by `export-adapters`. |
| **Provenance sidecar** | A `.hydra-adapter*.yaml` file naming the canonical source of a generated wrapper. Its absence is what makes a file `orphaned`. |
| **Capability class** | A provider-neutral name for the kind of model a role needs: `fast-default`, `cheap-triage`, `deep-reasoning`, `large-context`, `tool-heavy`, `review-focused`, `local-private`. |
| **Effort budget** | A provider-neutral reasoning-depth name: `minimal`, `low`, `standard`, `high`, `max`. |
| **Capability map** | Per-provider file resolving capability classes and effort budgets into concrete runtime values. The only place in an adapter that names models. |
| **`unresolved`** | A capability map entry with no verified mapping. Exporters omit the field rather than guessing. |
| **Skill kind** | `procedure` (the model may load it when relevant) or `command` (only a human triggers it; exported with `disable-model-invocation`). |
| **Lineage** | The `manifest.yaml` block recording which base seed version a copy descends from, which repository adopted it, and when. |
| **Adoption** | Wiring a freshly copied Hydra into a host repository. |
| **Reclamation** | Promoting a hand-authored provider file into a canonical module. |
| **Seed reconciliation** | Comparing a diverged copy against its base and deciding what flows back. |
| **Knowledge space** | A directory under `repo/knowledge/spaces/` listed in `spaces.yaml`, owning local state, sources, and units for one accountability boundary. |
| **Knowledge node** | A descendant directory of a space carrying its own `node.yaml`, bounded to three levels by default and four at most. |
| **Knowledge unit** | One durable operational question, answered in `units/<slug>.md`, addressable by `hydra://knowledge-unit/<space>[/<node>]/<slug>` and compiled by `compile-context` via its `reads:`. |
| **Route** | A `space.yaml` or `node.yaml` entry naming which units (`priority_units`, budget-exempt `requires`) answer one task shape. |
| **Node-document gate** | The deterministic per-node check run by `validate-package-docs` and the post-edit hook. |

## Surface Classifications

Produced by `hydra.py reclaim`:

| Status | Meaning | Fix |
| --- | --- | --- |
| `generated` | Matches what export would produce | Nothing |
| `drifted` | Has provenance, but the wrapper was edited | Move the edit to the canonical file, re-export |
| `orphaned` | No provenance; hand-authored in a provider directory | `reclaim --promote`, then review |
| `stale` | Provenance names a canonical source that is gone or no longer exported | Delete the wrapper or restore the source |

## Difference Classifications

Produced by `hydra.py diff-base`, then assigned intent by an agent or human:

| Mechanical | Intent |
| --- | --- |
| `identical` | nothing to decide |
| `local-modified` | `promote`, `repo-local`, `stale`, or `conflicting` |
| `local-only` | `promote` or `repo-local` |
| `base-only` | `stale`, or deliberately removed locally |
