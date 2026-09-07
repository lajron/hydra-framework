---
hydra_id: "hydra://knowledge-slice/hydra-framework/provider-export-example"
uid: "9b4eb99d-439c-407e-84cc-22ef767dbefd"
schema_version: "3"
kind: "knowledge-slice"
title: "Provider Export Example"
status: "active"
scope: "base-seed"
owners:
  team: "hydra"
relations:
  - type: "relates-to"
    target: "hydra://knowledge-space/hydra-framework"
  - type: "relates-to"
    target: "hydra://capability/agent/orchestrator"
provenance:
  sources:
    - ".hydra-framework/scripts/hydra.py"
    - ".hydra-framework/adapters/providers/claude/capability-map.yaml"
---

# Slice: Provider Export Example

Status: active
Updated: 2026-07-30
Certainty: verified

A worked trace of one canonical agent becoming one Claude subagent. Verified
against `hydra.py` and the generated output in this repository.

## Input: canonical metadata

`.hydra-framework/capabilities/agents/orchestrator/metadata.yaml`

```yaml
schema: hydra-framework.agent.v2
name: orchestrator
description: Route a non-trivial goal to the right Hydra knowledge, skills, workflows, and task state. ...
capability_class: deep-reasoning
effort: standard
tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Skill
dependencies:
  knowledge:
    - repo/knowledge/capability-routing.md
    - repo/knowledge/certainty-model.md
    - core/placement-rules.md
  skills:
    - repository-inspection
    - task-lifecycle
```

Note what is absent: no model name, no effort level, no provider concept. Canonical
records stay provider-neutral.

## Resolution: capability map

`.hydra-framework/adapters/providers/claude/capability-map.yaml`

```yaml
capability_classes:
  deep-reasoning: opus
effort_budgets:
  standard: high
```

`resolve_capability()` turns `deep-reasoning` into `opus` and `standard` into
`high`. An entry of `unresolved`, or a missing entry, yields an empty string and
the exporter omits the field — the subagent then inherits the session model
rather than running on a guessed one.

## Output: generated subagent

`.claude/agents/hydra-orchestrator.md`

```markdown
---
name: hydra-orchestrator
description: Route a non-trivial goal to the right Hydra knowledge, ...
tools: Read, Grep, Glob, Bash, Skill
model: opus
effort: high
---

# Orchestrator Agent
... body of agent.md ...

## Hydra Context

Load only what the task needs. Paths are relative to `.hydra-framework/`.

Canonical knowledge:

- `.hydra-framework/repo/knowledge/capability-routing.md`
- `.hydra-framework/repo/knowledge/certainty-model.md`
- `.hydra-framework/core/placement-rules.md`

Relevant Hydra skills:

- `hydra-repository-inspection`
- `hydra-task-lifecycle`
```

The `Hydra Context` section is generated from `dependencies`, so declaring a
dependency in metadata is what puts it in front of the subagent.

## Provenance

`.claude/agents/.hydra-adapter-hydra-orchestrator.yaml`

```yaml
schema: hydra-framework.adapter.v2
provider: claude
kind: agent
canonical_source: .hydra-framework/capabilities/agents/orchestrator/agent.md
generated_file: hydra-orchestrator.md
```

This sidecar is the whole basis of surface classification. Without it the file
would classify as `orphaned`, which is exactly how a hand-authored subagent is
detected.

## Why the naming differs by kind

| Kind | Wrapper | Sidecar |
| --- | --- | --- |
| skill | `<name>/SKILL.md` | `<name>/.hydra-adapter.yaml` |
| agent | `<name>.md` | `.hydra-adapter-<name>.yaml` |

Skills get a directory, so one sidecar per directory works. Subagents are flat
files in a shared directory, so the sidecar name has to carry the agent name.
`sidecar_for()` owns this asymmetry.

## Verify this slice

```bash
python3 .hydra-framework/scripts/hydra.py export-adapters --dry-run
python3 .hydra-framework/scripts/hydra.py reclaim
cat .claude/agents/hydra-orchestrator.md
```
