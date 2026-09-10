# Modules

Modules provide reusable framework behavior. Each is the canonical source for its
meaning. `hydra.py export-adapters` generates provider wrappers for skills and
agents under `.claude/`, `.agents/`, and `.codex/`; workflows and tool capability
records remain canonical-only inputs.

Use package-like repeated structures where they improve portability and
discovery, but avoid boilerplate that does not add meaning.

| Directory | Owns | Shape |
| --- | --- | --- |
| `skills/` | Reusable procedures and expertise, including `/`-invocable commands | `<slug>/skill.md` + `<slug>/metadata.yaml` |
| `agents/` | Specialist roles and decision boundaries | `<slug>/agent.md` + `<slug>/metadata.yaml` |
| `workflows/` | Repeatable coordination patterns | `<slug>.md` |
| `tools/` | Capability definitions and tool requirements | `capabilities.yaml` |

## Required Metadata

`hydra.py validate` fails without these:

- Skills: `name`, `description`. Optional: `kind` (`procedure` default, or `command`), `argument_hint`, `allowed_tools`, `user_invocable`.
- Agents: `name`, `description`, `capability_class`, `effort`. Optional: `tools`, `dependencies`.

Agents name a provider-neutral capability class and effort budget; each provider's
`capability-map.yaml` resolves those into concrete runtime values. Never put a
model name in a canonical module.

## Adding A Module

1. Create the body and `metadata.yaml`.
2. For a skill or agent, run `hydra.py export-adapters`.
3. Run `hydra.py validate`.

If you instead find one isolated hand-authored skill or agent in a provider
directory, run `hydra.py reclaim --promote` to move it here, then review its
metadata. Route a broader legacy setup through the framework-takeover skill and
`capabilities/workflows/material-migration.md`.

## Integrations And Plugins

External-system integrations do not have a module directory yet. Add one only
when a real integration exists, and keep credentials and private configuration
out of Git. Tool capability requirements belong in `tools/capabilities.yaml`
today.
