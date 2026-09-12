# Provider Adapters

Provider adapters describe how a model runtime maps onto framework capabilities.

Do not place provider-specific assumptions in `core/`.


Hydra treats provider-facing files as adapter surfaces over `.hydra-framework/`.

Examples include:

- `AGENTS.md`
- `CLAUDE.md`
- `.claude/`
- `.codex/`
- `.agents/`
- provider-specific hooks, skills, subagents, plugins, MCP configuration, and generated wrappers

These files may be generated, mirrored, or hand-written when a runtime requires a physical discovery path. They must not become canonical sources for framework meaning.

Canonical meaning lives in:

- `.hydra-framework/capabilities/skills/`
- `.hydra-framework/capabilities/agents/`
- `.hydra-framework/capabilities/workflows/`
- `.hydra-framework/capabilities/tools/`
- `.hydra-framework/tasks/`
- `.hydra-framework/repo/knowledge/`
- `.hydra-framework/core/`

Private provider configuration, credentials, local MCP auth, machine paths, and hook trust state belong in `.hydra-framework.local/` or user-local provider configuration.

## Trust Boundary

Adopting a checkout with provider hooks means allowing the provider to execute
repository-owned Python from `.hydra-framework/scripts/hydra.py` in the hook
events configured by that provider. Review `.claude/settings.json` and
`.codex/hooks.json` before enabling a provider session. The commands may read
repository files and, for commands that capture output or maintain indexes,
write the ignored `.hydra-framework.local/` state; they are not a security
sandbox.

The shared Claude settings intentionally allow
`Bash(python3 .hydra-framework/scripts/hydra.py:*)`, which covers every Hydra
subcommand, including future ones. Treat that wildcard as an explicit broad
trust choice and narrow it in local provider settings when the checkout needs a
smaller command surface.

## Model And Effort Mapping

Shared Hydra records should name provider-neutral capability classes and effort
budgets. Provider adapters or private local configuration map those to concrete
models, reasoning-effort settings, thinking modes, local inference profiles, and
cost limits. Keep those mappings close to the runtime that owns them so core
Hydra remains usable across providers.
