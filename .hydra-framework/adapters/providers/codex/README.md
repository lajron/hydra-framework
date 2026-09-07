# Codex Adapter

Codex is a provider runtime over Hydra. It should not own canonical Hydra meaning.

## Entry Files

- `AGENTS.md` is the shared agent instruction entry; Codex loads it directly.
- `.agents/skills/` contains generated or thin skill wrappers sourced from `.hydra-framework/capabilities/skills/`.
- `.codex/agents/` contains generated custom-agent TOML files sourced from `.hydra-framework/capabilities/agents/`.
- `.codex/config.toml` may define safe project-level Codex settings when the team deliberately needs them.
- `.codex/hooks.json` may wire deterministic lifecycle behavior when needed.

## Policy

- Keep `AGENTS.md` focused on durable repository and Hydra operating rules.
- Put reusable workflows in Hydra skills, then export Codex-compatible wrappers.
- Put provider, model, authentication, and personal runtime settings in user-local Codex config or `.hydra-framework.local/`, not shared project config.
- Use hooks for deterministic enforcement and lifecycle automation.

## Mini-Agents

Canonical agent roles live in `.hydra-framework/capabilities/agents/`.

Codex custom-agent TOML files are generated from those roles into
`.codex/agents/`, carrying the required `name`, `description`, and
`developer_instructions`.

The provider capability map resolves effort budgets to `model_reasoning_effort`.
It deliberately leaves capability classes unresolved, so generated agents omit
`model` and inherit the host's configured one — consistent with the rule above
that model selection is user-local, not shared project config.

## Hook Wiring Pattern

When a Codex runtime supports project hooks, route them through the canonical
Hydra helper instead of duplicating logic in `.codex/` files:

```bash
python3 .hydra-framework/scripts/hydra.py route-prompt
python3 .hydra-framework/scripts/hydra.py hook-post-edit
python3 .hydra-framework/scripts/hydra.py hook-subagent-start
python3 .hydra-framework/scripts/hydra.py hook-codex-command-output
python3 .hydra-framework/scripts/hydra.py hook-codex-retry-guard
```

`route-prompt` consumes prompt text or prompt JSON on stdin and emits pointers
only. `hook-post-edit` consumes tool-call JSON on stdin and runs the node-document
gate only when the edited file belongs to a Hydra knowledge space.

Codex `PostToolUse` on `^Bash$` is the Bash result surface for both successful
and non-zero shell commands. `hook-codex-command-output` consumes Codex's
`tool_response` value and records provider-neutral structural reducer telemetry
for Bash events with output. For large successful output from a reviewed reducer
family, it returns Codex-supported `continue: false` feedback rather than
Claude's unsupported `updatedToolOutput` field. `hook-codex-retry-guard`
consumes the same event and records non-zero Bash output by `session_id`; it
stays silent below the retry threshold and returns a Codex `decision: "block"`
feedback message only when the same failure repeats. The output reducer skips
model-visible replacement for known non-zero results so the two Bash hooks do not
race to replace one failed result.

When a Codex hook payload supplies a local transcript path, Hydra may derive a
`session.aggregate` event from Codex `token_count.info.last_token_usage` rows.
Provider token names are mapped to canonical fields: `cached_input_tokens` to
`cache_read_tokens`, and `cache_write_input_tokens` to
`cache_creation_tokens`. Transcript paths, rows, and raw hook payloads are not
stored in telemetry rows.

Verified against Codex CLI 0.149.1 documentation on 2026-08-26:
`PostToolUse` covers Bash and unified exec, runs for non-zero Bash exits, and
supports `continue: false`, `stopReason`, `decision: "block"`, and
`hookSpecificOutput.additionalContext` for feedback. Provider, model,
authentication, and personal runtime settings still belong in user-local config
or `.hydra-framework.local/`. Local Codex CLI 0.150.1 session rows on
2026-08-28 expose token counts through `token_count.info.last_token_usage`; Hydra
uses that shape only as an aggregate input and never as a raw telemetry row.
