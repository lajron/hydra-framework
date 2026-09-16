# Extension Points

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

Hydra's supported engine extension points are explicit, reviewable registries.
They are registered in code rather than discovered by scanning the repository at
import time. A maintainer extending one of these boundaries edits its owning
registry and keeps the matching tests current.

| Extension point | Explicit registry | What it owns | Focused proof |
| --- | --- | --- | --- |
| Object families | [`OBJECT_FAMILIES`](/.hydra-framework/engine/src/hydra_engine/identity/object_families.py) | The families, ID prefixes, and `kind` values the resolver recognizes. | [`test_object_families.py`](/.hydra-framework/engine/tests/unit/identity/test_object_families.py) |
| Object document forms | [`OBJECT_HANDLERS`](/.hydra-framework/engine/src/hydra_engine/objects/object_handlers.py) | Markdown, YAML, and Python envelope discovery. | [`test_object_handlers.py`](/.hydra-framework/engine/tests/unit/objects/test_object_handlers.py) |
| Validators | [`VALIDATORS`](/.hydra-framework/engine/src/hydra_engine/checks/validator_registry.py) | The locked `validate` and `doctor` check order. | [`test_validator_registry.py`](/.hydra-framework/engine/tests/unit/checks/test_validator_registry.py) |
| Providers | [`PROVIDERS`](/.hydra-framework/engine/src/hydra_engine/providers/capabilities.py) | Provider slugs, generated targets, and agent-wrapper renderers. | [`test_capabilities.py`](/.hydra-framework/engine/tests/unit/providers/test_capabilities.py), [`test_adapter_plan.py`](/.hydra-framework/engine/tests/unit/providers/test_adapter_plan.py) |
| Command handlers | [`COMMAND_MODULES`](/.hydra-framework/engine/src/hydra_engine/cli/dispatch.py) | The registered command modules consumed by the parser. | [`test_dispatch.py`](/.hydra-framework/engine/tests/unit/cli/test_dispatch.py), [`test_command_metadata.py`](/.hydra-framework/engine/tests/unit/cli/test_command_metadata.py) |
| Orchestration provider boundary | [`ProviderAdapter`](/.hydra-framework/engine/src/hydra_engine/orchestration/adapter.py) and the control-plane adapter factory | The bounded request interface for spawn, message, and collect without assuming a provider SDK or worker runtime. | [`test_adapter.py`](/.hydra-framework/engine/tests/unit/orchestration/test_adapter.py), [`test_control.py`](/.hydra-framework/engine/tests/unit/orchestration/test_control.py) |
| Command-output reducers | [`REDUCERS`](/.hydra-framework/engine/src/hydra_engine/command_output/registry.py) | Reviewed reducers selected for recognized shell-command output. | [`test_registry.py`](/.hydra-framework/engine/tests/unit/command_output/test_registry.py) |
| Context and route providers | [`CONTEXT_PROVIDERS`](/.hydra-framework/engine/src/hydra_engine/knowledge/context_providers.py) | One context provider per registered object family for `compile-context` candidates. | [`test_context_providers.py`](/.hydra-framework/engine/tests/unit/knowledge/test_context_providers.py) |

The registry is the documented extension location for each boundary. The
architecture keeps these registrations explicit and reviewable; it does not
promise a plugin mechanism that avoids touching the engine source.

Command-output reducers are an explicit extension point. The reducer registry
selects a reviewed reducer for recognized shell commands and falls back to an
unknown reduction when no reducer matches. Command functions still return a
`CommandResult` directly; that separate command-result type is not the reducer
registry.

`COMMAND_MODULES` owns the command modules added through the parser. A small set
of direct commands, including health checks and command metadata, is wired in
the dispatch composition root. Inspect that owner and its metadata tests when
extending those commands instead of creating a second command switchboard.

The registry invariants are covered by the corresponding unit tests:
object families,
object handlers,
validators,
providers,
command registration,
command-output reducers,
and context providers.

For the exact edit sequence and validation gate for each boundary, use [Safe
Extension Recipes](/project-wiki/hydra-framework/extending-hydra/extension-recipes.md). These are source-level extension
points, not a plugin or ABI compatibility contract.
