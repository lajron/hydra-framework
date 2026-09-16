# Safe Extension Recipes

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

Hydra's extension points are explicit registries in the engine. They support
reviewed source changes in a repository copy. They do not promise a plugin API,
runtime discovery, or ABI stability.

Start with [Extension Points](/project-wiki/hydra-framework/extending-hydra/extension-points.md) to choose the owning
registry. Keep the implementation in its domain module, make the one registry
edit that exposes it, and update the matching mirror test before considering
the change complete.

## Choose The Smallest Boundary

| Need | Make the reviewed change | Focused proof |
| --- | --- | --- |
| Recognize a new identity family | Add one `ObjectFamily` to `OBJECT_FAMILIES` with non-overlapping identifier prefixes and kinds. Add its one context provider to `CONTEXT_PROVIDERS` and define whether it uses knowledge routing or bounded search. | `test_object_families.py`, `test_context_providers.py`, then `hydra.py ref check` and `hydra.py ref index`. |
| Read a new object document form | Add one `ObjectHandler` to `OBJECT_HANDLERS` with its suffixes, reader, field spellings, roots, and exclusions. Do not broaden scan roots without a concrete need. | `test_object_handlers.py`, then `hydra.py ref check`. |
| Add a validation check | Implement the check in the appropriate checks module and add one named `Validator` at its deliberate order in `VALIDATORS`. Do not move the existing order. | `test_validator_registry.py` and the validation command contract tests. |
| Add a CLI command family | Implement `register(subparsers)` in its command module and add that module once to `COMMAND_MODULES`. Update side-effect metadata when the command changes state. | `test_command_metadata.py` and the command's contract tests. |
| Reduce a recognized command output | Implement a `CommandOutputReducer`, expose it from its reducer group, and add it once to `REDUCERS`. Leave unmatched commands on the unknown reduction path. | `test_registry.py` and the relevant command-output contract tests. |
| Add a provider surface | Change the canonical capability or `PROVIDERS` registry, then generate the provider wrappers. Do not hand-edit generated adapters. | `test_capabilities.py` and `hydra.py export-adapters --check`. |

The test paths above are under `.hydra-framework/engine/tests/unit/` unless a
row says otherwise. Run them through the repository's supported test command
or invoke the exact test module while developing.

## Required Gates

For every engine change, run the focused test named above, then
`python3 .hydra-framework/scripts/hydra.py validate` and `git diff --check`.
An object-model change also requires `python3 .hydra-framework/scripts/hydra.py
ref check`; regenerate the derived registry with `ref index` only after that
check passes. A canonical capability change additionally requires
`python3 .hydra-framework/scripts/hydra.py export-adapters --check`.

When the change edits these wiki routes, finish with
`python3 .hydra-framework/scripts/hydra.py validate-wiki --path project-wiki`.

## Stop Conditions

Do not add a registry entry to make a hypothetical integration look supported.
If the change needs an import-time scan, a second central switchboard, an
unbounded context collector, or a generated wrapper hand edit, stop and
revisit the boundary. The intended design is a small, explicit registration
with an owning test and an observable validation path.
