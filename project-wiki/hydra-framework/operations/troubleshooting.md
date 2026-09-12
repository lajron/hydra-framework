# Troubleshooting

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

Status: operating guide

Use the first diagnostic that matches the failure. These commands are
read-only checks or test runs. Follow the reported path and canonical owner
before changing anything.

## Read Diagnostic Results Precisely

A nonzero exit result is a failed gate. `Hydra validate: ok` is a passing
full-validation result even when it is followed by `note:` lines: those are
advisories, not failures. `doctor` first reports repository prerequisites and
cache health, then delegates its final verdict to the same full-validation
aggregation. It stops before validation when required paths are missing or the
private tier is not effectively ignored.

Treat an unavailable or stale derived cache differently from a failed canonical
check. It limits an accelerated query path; it does not by itself say that the
tracked source is invalid. The [Validation](/project-wiki/hydra-framework/operations/validation.md) page explains which
commands prove which claims.

## Wiki Link Failure

Run:

```bash
python3 .hydra-framework/scripts/hydra.py validate-wiki --path project-wiki/hydra-framework
```

For a missing Markdown link, inspect the file named before the arrow and repair
the relative target. For a missing double-bracket wiki link, check the page name and
target location under the Hydra wiki. The validator does not check backtick
path citations, so review those paths against the filesystem as well.

## Full Hydra Validation Failure

Run:

```bash
python3 .hydra-framework/scripts/hydra.py validate
```

Read each finding in the printed order. Validation renders the finding detail
text, not the structured `code` and `path` fields as separate output columns.
Use the validator registry
and the finding text to identify the owning check and artifact. Do not treat an
advisory note after `Hydra validate: ok` as a failed gate.

## Knowledge-Package Failure

Run:

```bash
python3 .hydra-framework/scripts/hydra.py validate-package-docs --package hydra-framework
```

Use this when a package link, routing entry, unit reference, or package-size
finding is involved. The package gate is also included in full validation.

## No Provider Surfaces Are Materialized

Generated adapters (`.claude/skills/hydra-*`, `.codex/agents/hydra-*`, and
similar) are Git-ignored and untracked, so this is expected right after a
fresh clone. Run:

```bash
python3 .hydra-framework/scripts/hydra.py export-adapters
```

`doctor` fails, rather than warns, when nothing is materialized but the
active capability profile expects something to be. Restart the Claude or
Codex session afterward: it composed its skill list at session start and will
not see newly materialized adapters until then.

## Provider-Surface Drift Or Unmanaged Files

For this checkout's local drift against the current plan:

```bash
python3 .hydra-framework/scripts/hydra.py export-adapters --check
```

For provider files Hydra cannot prove it generated (the check CI runs):

```bash
python3 .hydra-framework/scripts/hydra.py reclaim
```

`reclaim` classifies each provider-native file as `generated`, `orphaned`,
`drifted`, or `stale`. Inspect the canonical capability or provider-map
source it names for `drifted`; promote an `orphaned` file with
`reclaim --promote`; remove a `stale` file by hand with the command the
finding prints. Generated provider files are outputs and are not the place to
author a correction.

## Cache Or Object-Store Health

Run:

```bash
python3 .hydra-framework/scripts/hydra.py doctor
python3 .hydra-framework/scripts/hydra.py ref store status
```

`doctor` reports the freshness of the private knowledge index and object store.
`ref store status` distinguishes a store that is not built, corrupt, built with
an incompatible schema, or stale because its object export changed. Rebuild a
missing or stale store from canonical objects:

```bash
python3 .hydra-framework/scripts/hydra.py ref store rebuild
```

The object store is a disposable local cache. `ref resolve` falls back to a
full canonical scan when no fresh store is available. `ref rdeps` and
`ref impact` instead require a fresh store because they have no equivalent
scan path. Do not repair source files merely because a cache needs rebuilding.

## Engine or CLI Behavior Failure

Run:

```bash
python3 .hydra-framework/scripts/hydra.py selftest
```

Use this when command behavior, validator behavior, architecture boundaries,
or CLI output is in question. A failing test names the unit, repository, or
contract test that owns the behavior.
