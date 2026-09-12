# Command Surface

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

This is a lookup map for operators and maintainers. The exact parser,
arguments, help text, side-effect metadata, and output remain canonical in the
stable scripts README, the
compatibility shim, and the
owning command modules. Run `command-metadata --json` to inspect the current
registered IDs and arguments without relying on this page.

`command-metadata` is generated from the live argparse tree. Its side-effect
annotations are maintained beside the generator, so read-only commands do not
inherit safety claims by implication.

## Lookup by need

| Need | Commands |
| --- | --- |
| Health and command discovery | `doctor`, `validate`, `selftest`, `command-metadata` |
| Knowledge and context | `compile-context`, `delegation-brief`, `knowledge-search`, `knowledge fingerprint`, `knowledge stale`, `measure-context`, `route-prompt`, `validate-package-docs` |
| Objects and references | `explain-path`, `move-object`, `ref resolve`, `ref check`, `ref index`, `ref rdeps`, `ref impact`, `ref store status`, `ref store rebuild`, `schema upgrade` |
| Install and provider surfaces | `init`, `adopt`, `init-local`, `install-hooks`, `export-adapters`, `profile list`, `profile show`, `profile select`, `reclaim` |
| Tasks and local work state | `board`, `note`, `migrate-state`, `task start`, `task checkpoint`, `task handoff`, `task complete` |
| Seed evolution | `diff-base`, `evolution record` |
| Intake and source integration | `migration inventory`, `migration ledger`, `migration request-stage`, `migration propose`, `migration validate-batch`, `migration request-close`, `migration decide`, `migration status`, `integrate scan`, `integrate identify`, `integrate map`, `integrate status`, `takeover scan` |
| Hooks and feedback helpers | `hook-token pre-context`, `hook-token command-result`, `summarize-log`, `retry-guard`, `hook-command-output`, `hook-codex-command-output`, `hook-retry-guard`, `hook-codex-retry-guard`, `hook-post-edit`, `hook-reindex-knowledge`, `hook-subagent-start` |
| Wiki and telemetry | `validate-wiki`, `wiki scaffold`, `telemetry report`, `telemetry gate`, `telemetry evidence create` |

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
