# Command Surface

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

This is a lookup map for operators and maintainers. The exact parser,
arguments, help text, side-effect metadata, and output remain canonical in the
stable scripts README, the compatibility shim, and the owning command modules.
Run `command-metadata --json` to inspect the current registered IDs and
arguments without relying on this page.

`command-metadata` is generated from the live argparse tree. Its side-effect
annotations are maintained beside the generator, so read-only commands do not
inherit safety claims by implication. The compatibility entrypoint composes
engine command modules, the direct `validate` and `doctor` commands, the
metadata command itself, and the shim's `selftest` command into one parser.
Metadata walks that same parser, so a composed orchestration registration is
included as soon as its command module is part of the composition root. There
is no second parser or hand-copied command inventory to update.

## Lookup by need

| Need | Commands |
| --- | --- |
| Health and command discovery | `doctor`, `validate`, `selftest`, `command-metadata` |
| Knowledge and context | `compile-context`, `delegation-brief`, `knowledge-search`, `knowledge fingerprint`, `knowledge migrate-v2`, `knowledge stale`, `measure-context`, `route-prompt`, `validate-package-docs` |
| Objects and references | `explain-path`, `move-object`, `ref resolve`, `ref check`, `ref index`, `ref rdeps`, `ref impact`, `ref store status`, `ref store rebuild`, `schema upgrade` |
| Knowledge bindings | `bindings list`, `bindings verify` (add `--accept` only after reviewing the assertion) |
| Capability scaffolding, install, and provider surfaces | `capability scaffold-skill`, `capability scaffold-agent`, `init`, `adopt`, `init-local`, `install-hooks`, `export-adapters`, `profile list`, `profile show`, `profile select`, `reclaim` |
| Tasks and local work state | `board`, `note`, `migrate-state`, `task start`, `task checkpoint`, `task handoff`, `task complete` |
| Provider-neutral orchestration | `orchestration start`, `spawn`, `message`, `collect`, `transition`, `handoff`, `recover`, `review`, `validate`, `status` |
| Seed evolution | `diff-base`, `evolution record` |
| Intake and source integration | `migration inventory`, `migration ledger`, `migration request-stage`, `migration propose`, `migration validate-batch`, `migration request-close`, `migration decide`, `migration status`, `integrate scan`, `integrate identify`, `integrate map`, `integrate status`, `takeover scan` |
| Hooks and feedback helpers | `hook-token pre-context`, `hook-token command-result`, `summarize-log`, `retry-guard`, `hook-command-output`, `hook-codex-command-output`, `hook-retry-guard`, `hook-codex-retry-guard`, `hook-post-edit`, `hook-reindex-knowledge`, `hook-subagent-start` |
| Wiki and telemetry | `validate-wiki`, `wiki scaffold`, `wiki audit`, `wiki fingerprint`, `telemetry report`, `telemetry gate`, `telemetry evidence create` |

## Completeness and safety

The metadata report has three mechanical fields: command ID, aliases, and
arguments. It also carries hand-authored safety fields only for commands known
to write state. For example, `bindings verify` is report-only unless
`--accept` is supplied, while `knowledge fingerprint` and `wiki fingerprint`
write tracked provenance metadata. A safety annotation describes the boundary;
it does not turn a write command into a validation gate.

Commands added by a module must be registered through the composition root so
the parser, metadata report, command IDs passed to package validation, and
reader-facing inventory see the same leaf command. This includes the
orchestration registration when it is composed. If the report and a command's
`--help` output disagree, inspect the owning registration and the
[CLI composition sources](/.hydra-framework/engine/src/hydra_engine/cli/dispatch.py),
[parser](/.hydra-framework/engine/src/hydra_engine/cli/parser.py), and
[metadata generator](/.hydra-framework/engine/src/hydra_engine/cli/command_metadata.py)
before changing this page.

`wiki audit` reports source freshness and declaration gaps without blocking the
run. `validate-wiki`, `validate-package-docs`, `validate`, and the explicit CI
provider-surface gate are separate checks with their own boundaries. Use the
[Validation](/project-wiki/hydra-framework/operations/validation.md) route to
choose one; do not infer gate behavior from the command name alone.

Orchestration commands record an explicit, bounded control-plane request in
the private ledger. `orchestration start` requires an existing task record;
`spawn` requires a run owner or parent-worker owner plus configured active and
depth limits; `message` and `collect` require explicit worker and request IDs.
`collect --complete` records a provider-reported result but does not complete
the worker. Review, validation, handoff, recovery, and final completion remain
separate explicit transitions. The default adapter is request-only: these
commands do not prove that a Claude, Codex, or other provider runtime was
invoked.

## Safe lookup habits

- Use `python3 .hydra-framework/scripts/hydra.py <command> --help` for the
  current arguments and required values.
- Use `command-metadata --json` to review the assembled surface and side-effect
  annotations.
- Treat `--check` and `--dry-run` as the preview forms where the command owner
  provides them. Read the owner module before assuming a preview is available.
- `export-adapters --profile <name>` only previews; it requires `--dry-run`
  and refuses to combine with `--check`. Materializing a profile for the
  checkout is `profile select <name>`.
- Treat `--json` as an output-format request, not as a guarantee that a command
  has no side effect.
- For a failure, preserve the command, exit code, and finding path, then follow
  the owner links above or the [Troubleshooting](/project-wiki/hydra-framework/operations/troubleshooting.md)
  route.
