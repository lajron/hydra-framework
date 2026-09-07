---
hydra_id: "hydra://knowledge-slice/hydra-framework/architecture-graph"
uid: "bfb8c8c7-17f9-4183-93d4-325de2b9232b"
schema_version: "3"
kind: "knowledge-slice"
title: "Hydra Framework Architecture Graph"
status: "active"
scope: "base-seed"
owners:
  team: "hydra"
relations:
  - type: "relates-to"
    target: "hydra://knowledge-space/hydra-framework"
provenance:
  sources:
    - ".hydra-framework/scripts/hydra.py"
---

# Architecture Graph

Status: active
Updated: 2026-07-30

How Hydra's machinery fits together. Slices link outward from here.

## Canonical To Provider

```mermaid
flowchart LR
  subgraph canonical[".hydra-framework/ (source of truth)"]
    skills["capabilities/skills/*/skill.md<br/>+ metadata.yaml"]
    agents["capabilities/agents/*/agent.md<br/>+ metadata.yaml"]
    capmap["adapters/providers/*/<br/>capability-map.yaml"]
  end

  planner["planned_adapter_files()"]

  subgraph provider["provider surfaces (generated)"]
    cskills[".claude/skills/hydra-*/SKILL.md"]
    cagents[".claude/agents/hydra-*.md"]
    askills[".agents/skills/hydra-*/SKILL.md"]
    sidecars[".hydra-adapter*.yaml<br/>provenance"]
  end

  skills --> planner
  agents --> planner
  capmap -->|resolves capability_class<br/>and effort| planner
  planner --> cskills
  planner --> cagents
  planner --> askills
  planner --> sidecars

  planner -.->|--check| drift["CI drift gate"]
  planner -.->|compare| classify["classify_surfaces()"]
```

One planner drives generation, `--check`, `--dry-run`, and surface
classification, so those four cannot disagree about what is generated.

## Surface Classification

```mermaid
flowchart TD
  file["file under .claude/ .agents/ .codex/"]
  sidecar{"has provenance<br/>sidecar?"}
  exists{"canonical source<br/>still exists?"}
  inplan{"still in the<br/>export plan?"}
  matches{"content matches<br/>plan?"}

  file --> sidecar
  sidecar -->|no| orphaned["orphaned<br/>promote into canonical Hydra"]
  sidecar -->|yes| exists
  exists -->|no| stale1["stale<br/>delete or restore source"]
  exists -->|yes| inplan
  inplan -->|no| stale2["stale<br/>no longer exported"]
  inplan -->|yes| matches
  matches -->|no| drifted["drifted<br/>move edit to canonical source"]
  matches -->|yes| ok["generated<br/>nothing to do"]
```

`hook-post-edit` runs this on every write into a provider directory and prints
guidance for anything that is not `generated`. It never blocks the write.

## Copy And Reconcile

```mermaid
flowchart LR
  base["base seed repository"]
  copyA["repo A: .hydra-framework/"]
  copyB["repo B: .hydra-framework/"]
  candidates["evolution/candidates/"]

  base -->|"init --target"| copyA
  base -->|"init --target"| copyB
  copyA -->|"adopt --record<br/>stamps lineage"| copyA
  copyA -->|adapts locally| copyA
  copyA -->|"diff-base --base"| compare{"classify by<br/>content hash"}
  compare -->|promote| candidates
  compare -->|repo-local| copyA
  candidates -->|reviewed with evidence| base
  base -.->|next copy carries it| copyB
```

Divergence is the normal state. The return path is what keeps copies from
forking permanently.

## Validation Layers

| Layer | Trigger | Scope |
| --- | --- | --- |
| `hook-post-edit` | write into a provider dir or knowledge space | that file and its node |
| `route-prompt` | prompt submit | emits package pointers only |
| `validate` | manual, `doctor`, CI | task records, module metadata, capability maps, surfaces, contract drift, package links |
| `export-adapters --check` | manual, CI | generated-surface freshness |
| `selftest` | manual, CI | helper-script behavior |
| `doctor` | manual, CI | required paths, surface summary, lineage, then `validate` |

## Slices

- [Provider Export Example](01-example.md)
