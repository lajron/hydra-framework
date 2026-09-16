# Seed And Adopt Hydra In A New Repository

Page type: operating guide

Use this route when Hydra is not already part of the repository. It starts from
an already checked-out Hydra source repository and copies the supported framework
files into an existing target repository. It is not the setup path for a normal
clone that already contains Hydra; use the [post-clone path](/project-wiki/hydra-framework/start-here/new-contributor.md)
for that case.

## Before Copying

Choose the target repository and preserve its existing material. The supported
copy command refuses existing file conflicts unless `--force` is supplied, so
start with the preview and resolve any unexpected overlap before applying a
copy. Do not use this route to replace another AI framework or to clear
existing documentation, CI, provider files, or source material. Those changes
need separate, explicit scope through [Migration](/project-wiki/hydra-framework/extending-hydra/migration.md#take-over-legacy-agentic-material).

If the target is not empty of agentic material, choose the route before running
the copy:

| Target situation | Next route |
| --- | --- |
| No Hydra copy and no foreign agentic setup | Continue with this adoption guide. |
| Another AI framework or legacy agentic setup is present | Keep it in place. After the owner explicitly scopes a takeover, run the read-only `takeover scan`, then use [Migration](/project-wiki/hydra-framework/extending-hydra/migration.md#take-over-legacy-agentic-material). |
| The source material is another Hydra copy | Use [Hydra-to-Hydra integration](/project-wiki/hydra-framework/extending-hydra/intake-and-migration.md#hydra-to-hydra-integration), not foreign-material takeover. |
| Hydra is already present in the target | Use the [post-clone path](/project-wiki/hydra-framework/start-here/new-contributor.md) and inspect lineage with `adopt`. |

`takeover scan` is an inventory only. It does not authorize a move, and
`init --force` does not turn adoption into migration.

## 1. Copy From The Checked-Out Source

From the checked-out Hydra source repository, preview the files that would be
copied into the target:

```bash
python3 .hydra-framework/scripts/hydra.py init --target /path/to/target-repository --dry-run
```

When the preview is correct, apply the copy:

```bash
python3 .hydra-framework/scripts/hydra.py init --target /path/to/target-repository
```

For the current parser arguments and side-effect annotations, see the [Command
Surface](/project-wiki/hydra-framework/reference/command-surface.md) and run:

```bash
python3 .hydra-framework/scripts/hydra.py command-metadata --json
```

The copy includes the framework definition, entry files, Claude placement rule
and settings, and Codex hooks, but not the source repository's personal task
records. It also seeds the target's ignored private tier. It deliberately does
not copy `.github/CODEOWNERS`, because reviewer identities belong to the target
repository. `--force` overwrites conflicting copied files, so use it only after
the target and conflicts have been deliberately reviewed.

## 2. Inspect And Record The Adoption

Change to the target repository and run the adoption report before manually
inspecting or recreating framework files:

```bash
python3 .hydra-framework/scripts/hydra.py adopt
```

If the report identifies a missing required path, stop and re-copy it from the
source. Do not recreate a partial copy from memory. When the report is intact
and lineage has not yet been recorded, stamp the target's repository slug:

```bash
python3 .hydra-framework/scripts/hydra.py adopt --record --repo <repository-slug>
```

The lineage stamp lets later seed comparison distinguish intentional local
adaptation from unexplained drift. The command reports an existing lineage
without rewriting it.

When the target later changes its copied framework, use the [Evolution](/project-wiki/hydra-framework/evolution/evolution.md#seed-copies-and-reconciliation)
route to compare it with the base using `diff-base` and record deliberate
divergence with `evolution record`. Reconciliation reports and recommends; it
does not overwrite the target or the base automatically.

Create a target-local `.github/CODEOWNERS` mapping (or the code host's
equivalent) for `.hydra-framework/` and `project-wiki/` using reviewers who own
those areas in the target repository.

## 3. Wire Only The Provider Surfaces In Use

Generate the provider adapters from Hydra's canonical capabilities:

```bash
python3 .hydra-framework/scripts/hydra.py export-adapters
```

Generated adapters are Git-ignored and untracked, so this step must be run in
the target repository too, not only assumed from the source copy; every
future fresh clone of the target needs it as well before a provider session
starts. Optionally preview a narrower capability profile first with
`hydra.py profile list` and `hydra.py export-adapters --profile <name>
--dry-run` before materializing the full catalog. Then follow the
[provider adapter procedure](/project-wiki/hydra-framework/extending-hydra/provider-adapters.md)
for the runtimes the team actually uses. Keep provider entry files small and
leave existing provider configuration in place unless a separately scoped
migration or takeover calls for a change.

Before enabling the target's provider sessions, review the [Hydra trust
boundary](/README.md#trust-model). Provider hooks execute the copied
repository-owned `hydra.py`; this is an explicit trust decision, separate from
the optional Git hooks installed in the next step.

## 4. Validate The Result

Run both checks in the target repository:

```bash
python3 .hydra-framework/scripts/hydra.py doctor
python3 .hydra-framework/scripts/hydra.py selftest
```

`doctor` checks the repository and runs Hydra validation. `selftest` runs the
bundled engine tests. Address findings before treating the adoption as complete.

## Boundary: Copying Is The Route Documented Here

This page documents copying from a checked-out source repository. It does not
describe package distribution, release channels, or compatibility guarantees.
Use this route when the source checkout is available; use the canonical
installation command help for any other supported route.

## Maintainer Route

The copy, lineage, adapter, and validation owners are collected in the
[Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).
