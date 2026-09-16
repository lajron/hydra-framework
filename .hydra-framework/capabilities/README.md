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

Maintained modules normally use the shared object envelope as well: `schema`,
`hydra_id`, `uid`, `schema_version`, and `hydra_object_kind` identify the object;
`scope`, `maturity`, and `owners` describe its placement and stewardship;
`dependencies`, `relations`, and `provenance` describe its canonical context.
Skills may also carry `tags` for profile selection. These fields should contain
real information, not filler. The validator requires the fields above and
permits the rest to be omitted when they have no meaningful value; the scaffold
command writes a complete starter envelope.

The provider-neutral capability classes are `fast-default`, `cheap-triage`,
`deep-reasoning`, `large-context`, `tool-heavy`, `review-focused`, and
`local-private`. Effort budgets are `minimal`, `low`, `standard`, `high`, and
`max`. A class describes the resource shape a role needs, not a particular
model. Effective configuration may cap a role's requested effort, and a
provider map may leave a value unresolved so the runtime's local default is
used rather than inventing a model or effort setting.

## Scaffolding

Use the canonical scaffold commands when starting a module:

```bash
python3 .hydra-framework/scripts/hydra.py capability scaffold-skill <name> \
  --description "..." [--kind procedure|command] [--title "..."] [--force]
python3 .hydra-framework/scripts/hydra.py capability scaffold-agent <name> \
  --description "..." --capability-class <class> --effort <budget> \
  [--title "..."] [--force]
```

The command creates the canonical body and metadata files. `--force` replaces
those two files in an existing module; it does not export provider files. Review
the scaffold, then run `export-adapters --dry-run`, export, and validate. Manual
file creation remains useful when a module needs a shape beyond the starter.

## Adding A Module

1. Scaffold the body and `metadata.yaml`, or create both manually.
2. Review the metadata, dependencies, and provider-neutral boundaries.
3. For a skill or agent, run `hydra.py export-adapters --dry-run`, then export.
4. Run `hydra.py validate`.

If you instead find one isolated hand-authored skill or agent in a provider
directory, run `hydra.py reclaim --promote` to move it here, then review its
metadata. Route a broader legacy setup through the framework-takeover skill and
`capabilities/workflows/material-migration.md`.

## Integrations And Plugins

External-system integrations do not have a module directory yet. Add one only
when a real integration exists, and keep credentials and private configuration
out of Git. Tool capability requirements belong in `tools/capabilities.yaml`
today.
