---
hydra_id: "hydra://knowledge-unit/hydra-framework/agent-export-trace"
uid: "6261c72a-da1b-46f9-8474-dddc40b53430"
schema_version: "3"
kind: "knowledge-unit"
unit_kind: "answer"
title: "Agent Export Trace"
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
    - ".hydra-framework/capabilities/agents/orchestrator/metadata.yaml"
    - ".hydra-framework/adapters/providers/claude/capability-map.yaml"
    - ".hydra-framework/engine/src/hydra_engine/providers/capabilities.py"
    - ".hydra-framework/engine/src/hydra_engine/providers/reclaim.py"
  source_digests:
    - source: .hydra-framework/capabilities/agents/orchestrator/metadata.yaml
      digest: sha256:6578086c05679a94319cdd396d0e044cca011e87e8f0dd40999ed7534ef56357
    - source: .hydra-framework/adapters/providers/claude/capability-map.yaml
      digest: sha256:21f9816a665e6025bc84f1cd7a2c2b1ae3be1523389e6f98c6491ded2790001f
    - source: .hydra-framework/engine/src/hydra_engine/providers/capabilities.py
      digest: sha256:a2887b785d20626bd7302efb398e670c0955ce04b177fa5f34b63c8c0b8c5ce5
    - source: .hydra-framework/engine/src/hydra_engine/providers/reclaim.py
      digest: sha256:eeab0f4fc577d4f964ef096944f750c4a980d616d9ef07bb63cef46d8d06a70d
question: "How does one canonical agent's metadata become one generated Claude subagent, end to end?"
group: "provider-export"
certainty: "confirmed"
checked_on: "2026-09-12"
reads:
  - ".hydra-framework/capabilities/agents/orchestrator/metadata.yaml"
  - ".hydra-framework/adapters/providers/claude/capability-map.yaml"
verify:
  - "python3 .hydra-framework/scripts/hydra.py export-adapters --dry-run"
  - "python3 .hydra-framework/scripts/hydra.py reclaim"
---

# Agent Export Trace

## Answer

`export-adapters` reads a canonical agent's `metadata.yaml`, resolves its
provider-neutral `capability_class`/`effort` through the provider's own
`capability-map.yaml` via `resolve_capability()`, and writes a generated
subagent file plus a provenance sidecar naming the canonical source. An
unresolved or missing mapping entry yields an empty field rather than a
guessed value, so the subagent falls back to the session default instead of
running on an invented model.

## Worked Trace

Input — `.hydra-framework/capabilities/agents/orchestrator/metadata.yaml`:

```yaml
capability_class: deep-reasoning
effort: standard
```

Resolution — `.hydra-framework/adapters/providers/claude/capability-map.yaml`:

```yaml
capability_classes:
  deep-reasoning: opus
effort_budgets:
  standard: high
```

`resolve_capability()` (`providers/capabilities.py`) turns `deep-reasoning`
into `opus` and `standard` into `high`.

Output — `.claude/agents/hydra-orchestrator.md` frontmatter:

```
model: opus
effort: high
```

Provenance — `.claude/agents/.hydra-adapter-hydra-orchestrator.yaml`:

```yaml
provider: claude
kind: agent
canonical_source: .hydra-framework/capabilities/agents/orchestrator/agent.md
generated_file: hydra-orchestrator.md
```

This sidecar is the whole basis of surface classification (`reclaim.py`'s
`classify_surfaces`): without it, the generated file would classify as
`orphaned`, which is exactly how a hand-authored subagent is detected.

The exported agent may also carry the provider map's orchestration request
boundary. That text is an explicit limitation: it can describe or queue a
bounded request, but it is not evidence that a Claude or Codex worker started,
received a message, or produced a result.

## Rules

Naming differs by kind (`sidecar_for()` in `providers/reclaim.py`): a skill
gets a directory, so `<name>/.hydra-adapter.yaml` is unambiguous; an agent is
a flat file in a shared directory, so its sidecar carries the agent's name,
`.hydra-adapter-<name>.yaml`.

`resolve_capability()` returns `""` (never a guess) when the key is empty,
the mapping has no entry, or the entry is the literal string `"unresolved"` —
this is what lets a provider capability map defer a class deliberately.
