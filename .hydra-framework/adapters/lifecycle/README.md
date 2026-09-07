# Lifecycle Adapters

Lifecycle adapters may later connect framework events to hooks, scripts, wrappers, commands, or provider-specific integrations.

Common lifecycle moments include:

- before context loss
- before session termination
- before and after tool execution
- before and after model handoff
- when work becomes blocked
- when work is paused


## Default Hook Patterns

Hydra now exposes provider-neutral hook commands through
`.hydra-framework/scripts/hydra.py`:

- `route-prompt`: prompt-time package routing from `routing.yaml`, emitting
  pointers only.
- `hook-post-edit`: post-edit node-document validation for changed Markdown or
  DOT files under knowledge spaces.
- `hook-token pre-context`: context surface budget guard. It should run silently
  on success and only print when the configured workflow budget is exceeded.
- `hook-token command-result`: command-output feedback guard. It summarizes
  failing or oversized output and tracks repeated failures in private local
  state.
- `hook-command-output`: Claude Bash `PostToolUse` command-output reducer for
  large successful results.
- `hook-retry-guard`: Claude Bash `PostToolUseFailure` repeated-failure guard.
- `hook-codex-command-output`: Codex Bash `PostToolUse` command-output reducer
  for large successful results, using Codex `continue: false` feedback.
- `hook-codex-retry-guard`: Codex Bash `PostToolUse` repeated-failure guard for
  non-zero results.
- `hook-subagent-start`: provider subagent-start discovery injector. It emits
  bounded Hydra command pointers for provider-native generic subagents and writes
  no telemetry or state.

Adapters should call these commands rather than copying routing, validation, or
token-efficiency logic into provider-owned files. Hook output must stay small and
deterministic. Context budgets are set by the workflow or local policy, not by a
shared magic number.
