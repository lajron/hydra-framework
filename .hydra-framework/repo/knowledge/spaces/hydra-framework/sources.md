---
hydra_id: "hydra://knowledge-slice/hydra-framework/sources"
uid: "318d1be3-bf03-4901-99c9-a2896d8bd0bc"
schema_version: "3"
kind: "knowledge-slice"
title: "Hydra Framework Sources"
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

# Sources

Status: active
Updated: 2026-08-19

Source material behind this package's claims. Keep live state with its owner and
link it from here rather than copying it.

## In-Repository Authorities

| Source | Authoritative for |
| --- | --- |
| `.hydra-framework/engine/src/hydra_engine/` | What the tooling actually does |
| `.hydra-framework/scripts/hydra.py` | Stable compatibility CLI entrypoint |
| `.hydra-framework/engine/tests/` | Executable evidence for behavior claims |
| `.hydra-framework/core/` | Framework principles, placement rules, lifecycle |
| `.hydra-framework/manifest.yaml` | Seed version, enabled areas, lineage |
| `.hydra-framework/evolution/adaptations.md` | Append-only explanation ledger for intentional seed divergence |
| `.claude/settings.json` | Actual hook and permission wiring |
| `.hydra-framework/adapters/providers/*/capability-map.yaml` | Capability class and effort resolution per provider |

## External Sources

Provider behavior is authoritative from the provider's own documentation. Record
the checked date; these pages change.

| Source | Checked | Used for |
| --- | --- | --- |
| https://code.claude.com/docs/en/subagents | 2026-07-30 | `.claude/agents/` location; frontmatter fields `name`, `description`, `tools`, `model`, `effort`, `permissionMode`, `memory`, `isolation`, `color`; model aliases and `inherit` |
| https://code.claude.com/docs/en/memory | 2026-07-30 | `.claude/rules/` exists and supports `paths:` frontmatter globs; CLAUDE.md load order; `@import` behavior; AGENTS.md is not read directly |
| https://code.claude.com/docs/en/slash-commands | 2026-07-30 | Custom commands merged into skills; skill frontmatter `disable-model-invocation`, `user-invocable`, `argument-hint`, `allowed-tools`; `.claude/commands/` is legacy |
| https://learn.chatgpt.com/docs/agent-configuration/subagents.md | 2026-07-30 | Codex custom agents live under `.codex/agents/` as TOML files; required `name`, `description`, `developer_instructions`; optional `model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, `skills.config` |
| https://learn.chatgpt.com/docs/build-skills.md | 2026-07-30 | Codex local skills are discovered from `.agents/skills`; `SKILL.md` requires `name` and `description`; progressive-disclosure context budget |
| https://learn.chatgpt.com/docs/agent-configuration/agents-md.md | 2026-07-30 | Codex loads `AGENTS.md` / `AGENTS.override.md` instruction chains and applies closer files later |
| `codex --version` (`codex-cli 0.146.0`) and the local Codex model catalog at `~/.codex/models_cache.json` | 2026-07-30 | Codex runtime version recorded in the capability map; the reasoning-level vocabulary `low`, `medium`, `high`, `xhigh`, `max`, `ultra` |

## Verification Notes

- The four Claude Code surfaces used by the exporter were confirmed against the docs above before any generator code was written. Nothing in `.claude/` is generated on the assumption that a feature exists.
- `.claude/commands/` is deliberately scanned but never generated into: it still works in Claude Code, so a teammate may put a file there, and reclamation needs to see it.
- Claude full model IDs are deliberately not recorded. The capability map uses provider aliases so routine framework work does not need model-catalog lookups.
- Codex custom-agent generation was added only after the Codex documentation confirmed `.codex/agents/*.toml` and its required fields. The three required fields are always written; `model` and `model_reasoning_effort` are written only when the capability map resolves them.
- The snake_case `name` with a kebab-case filename (`hydra_task_steward` in `hydra-task-steward.toml`) is the documented Codex convention, not an inconsistency. Every example in the source above pairs them that way, and the `name` field is the identifier Codex resolves.
- The local Codex model catalog is evidence for the *reasoning-level vocabulary* only. The model slugs it lists are specific to one account and plan, so they are not recorded as shared framework truth. See P1 in `problems.md`.

## Deliberately Not Sources

- `project-wiki/hydra-framework/` — a derived human explanation surface, not evidence.
- Generated files under `.claude/`, `.agents/`, `.codex/` — outputs.
- Completed and archived task records — history, not current authority.
