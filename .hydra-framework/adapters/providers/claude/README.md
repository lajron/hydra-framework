# Claude Adapter

Claude Code is a provider runtime over Hydra. It should not own canonical Hydra meaning.

## Entry Files

- `CLAUDE.md` imports `AGENTS.md` and adds only Claude-specific adapter notes.
- `.claude/skills/` holds generated skill wrappers sourced from `.hydra-framework/capabilities/skills/`.
- `.claude/agents/` holds generated subagents sourced from `.hydra-framework/capabilities/agents/`.
- `.claude/rules/` holds hand-written path-scoped rules for cases where always-loading them would waste context.
- `.claude/settings.json` wires hooks and permissions. Hand-maintained.

Generated files carry a `.hydra-adapter*.yaml` sidecar naming their canonical
source. Anything under a provider directory without one is unmanaged; see
Reclaiming below.

## Policy

- Keep `CLAUDE.md` small.
- Put reusable procedures in Hydra skills, then export wrappers.
- Put deterministic lifecycle behavior in hooks, not prompt prose.
- Put private local Claude behavior in `.hydra-framework.local/` or Claude's user-local settings, not shared Hydra state.

## Skills And Commands

Current Claude Code merges custom commands into skills: a skill at
`.claude/skills/<name>/SKILL.md` is also invocable as `/<name>`. Hydra therefore
has no separate commands module. Skill metadata carries `kind`:

- `kind: procedure` (default) — Claude may load it when relevant.
- `kind: command` — exported with `disable-model-invocation: true`, so only a human triggers it. Use for anything with side effects or timing requirements.

Skill metadata also supports `argument_hint`, `allowed_tools`, and
`user_invocable`, which map onto the matching Claude frontmatter fields.

`.claude/commands/` still works in Claude Code but is legacy. Hydra does not
generate into it; it only scans it during reclamation.

## Subagents

Canonical agent roles live in `.hydra-framework/capabilities/agents/`. Each has
`agent.md` (the system prompt) and `metadata.yaml`.

Canonical metadata names a provider-neutral `capability_class` and `effort`
budget. `capability-map.yaml` in this directory resolves those into the
`model:` and `effort:` frontmatter Claude Code expects. It uses provider aliases
instead of full model IDs, so routine framework work does not need provider
catalog checks. When a class has no mapping, the exporter omits the field and
the subagent inherits the session model.

## Model And Effort Mapping

`capability-map.yaml` is the only place in the Claude adapter that names runtime
model aliases. It records a `verified` date and a `certainty` label because
provider aliases and effort levels can change. `hydra.py validate` fails if a
capability class or effort budget used by any canonical agent has no entry here.

## Hook And Permission Wiring

The working configuration is checked in at `.claude/settings.json`. Read that
file rather than copying a snippet from this README. It wires:

- `UserPromptSubmit` -> `hydra.py route-prompt` (knowledge-package pointers only)
- `PostToolUse` on `Write|Edit|MultiEdit` -> `hydra.py hook-post-edit`
- `SubagentStart` on `general-purpose|Explore|Plan` -> `hydra.py hook-subagent-start`
- a permissions allowlist for `hydra.py`, so routine framework commands do not prompt

`hook-post-edit` does two things: it warns when a write lands on an unmanaged or
drifted provider surface, and it runs the package gate for knowledge-package
edits. Hook output stays small, and the surface warning never blocks the write.

`hook-subagent-start` supplies bounded Hydra discovery pointers to Claude's
provider-native generic subagents. Generated Hydra subagents are excluded because
their role prompts already carry Hydra context. The hook records no telemetry and
writes no state.

## Reclaiming Hand-Authored Files

People add skills and subagents where their runtime expects them, not where
Hydra wants them. That is the expected failure mode, not misuse.

Use reclaim for an isolated provider-native skill or agent. If it belongs to a
broader legacy agentic setup, use the framework-takeover skill and
`capabilities/workflows/material-migration.md` so related material is drained
together.

```bash
python3 .hydra-framework/scripts/hydra.py reclaim            # classify
python3 .hydra-framework/scripts/hydra.py reclaim --promote  # move into canonical Hydra
python3 .hydra-framework/scripts/hydra.py export-adapters    # regenerate
```

Classification is `generated`, `drifted` (wrapper edited instead of its source),
`orphaned` (hand-authored, no canonical source), or `stale` (canonical source
gone). Promoted modules are marked `scope: repo-local` and `certainty: inferred`
and need review. A successful promotion removes the provider-native source;
`export-adapters` then recreates the generated wrapper from canonical Hydra.
