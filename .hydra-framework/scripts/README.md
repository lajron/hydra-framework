# Scripts

Scripts provide executable setup, maintenance, migration, validation, and adapter behavior.

Do not add scripts that silently install tools, write private state into Git, or hide provider-specific behavior inside the core.


Scripts are a required long-term Execution Harness surface. They should turn Hydra intent into repeatable console, GUI, provider-adapter, validation, export, migration, and task-state operations without forcing every model or developer to re-derive the procedure.

## Current Entry

`hydra.py` is the stable compatibility entrypoint. It bootstraps
`.hydra-framework/engine/src`, loads `hydra_engine.cli.dispatch`, and keeps
documented invocations working while engine behavior lives in the package.
Run it from the repository root.

### Health and validation

```bash
python3 .hydra-framework/scripts/hydra.py doctor     # paths, private tier, cache lifecycle, surfaces, lineage, owner, then validate
python3 .hydra-framework/scripts/hydra.py validate   # tasks, tiers, metadata, package docs, object refs, architecture
python3 .hydra-framework/scripts/hydra.py selftest   # bundled engine tests
python3 .hydra-framework/scripts/hydra.py install-hooks   # optional per-clone pre-push gate
```

`validate` is the single implementation of every check. CI runs it, `doctor` runs
it, and the optional pre-push hook runs it. Nothing is enforced only in a hook:
a hook is per-clone and opt-in, so a check that lives solely there is not a check.

### Provider surfaces

```bash
python3 .hydra-framework/scripts/hydra.py export-adapters
python3 .hydra-framework/scripts/hydra.py export-adapters --check     # CI drift gate
python3 .hydra-framework/scripts/hydra.py export-adapters --dry-run
python3 .hydra-framework/scripts/hydra.py reclaim                     # classify unmanaged files
python3 .hydra-framework/scripts/hydra.py reclaim --promote           # move them into canonical Hydra
```

### Copy, adopt, reconcile

```bash
python3 .hydra-framework/scripts/hydra.py init --target /path/to/repo --dry-run
python3 .hydra-framework/scripts/hydra.py init-local                  # seed ignored private tier
python3 .hydra-framework/scripts/hydra.py init-local --check
python3 .hydra-framework/scripts/hydra.py init-local --write-token-policy
python3 .hydra-framework/scripts/hydra.py adopt                       # integration report
python3 .hydra-framework/scripts/hydra.py adopt --record --repo <slug> # stamp lineage
python3 .hydra-framework/scripts/hydra.py evolution record \
  --title "repo-specific routing doc" --disposition repo-local \
  --path .hydra-framework/repo/knowledge/project.md \
  --why "Routing that only makes sense in this repository" \
  --evidence "Used during adoption; validate passes"
python3 .hydra-framework/scripts/hydra.py diff-base --base /path/to/base-repo
```

`evolution record` appends to `evolution/adaptations.md`, the on-demand ledger
used by `diff-base` to separate explained differences from unexplained drift.
`diff-base --fail-on-drift` exits `2` only when unexplained differences remain.
`init-local` appends the private-tier `.gitignore` rule when needed and writes
missing seed files without overwriting private edits. `--write-token-policy`
serializes `DEFAULT_TOKEN_HOOK_POLICY` from `agent_hooks/token_budget.py` into
the private monitoring area when that policy file is absent.

### Migration staging

```bash
python3 .hydra-framework/scripts/hydra.py migration inventory
python3 .hydra-framework/scripts/hydra.py migration inventory <slug>
python3 .hydra-framework/scripts/hydra.py migration inventory --json
python3 .hydra-framework/scripts/hydra.py migration ledger <slug>
python3 .hydra-framework/scripts/hydra.py migration ledger <slug> --create
python3 .hydra-framework/scripts/hydra.py migration request-stage <slug> <batch> --source <root> --route shared --worker-instance <id> --capability-class <class>
python3 .hydra-framework/scripts/hydra.py migration propose <slug> <batch> --manifest <proposal.json>
python3 .hydra-framework/scripts/hydra.py migration validate-batch <slug> <batch> --evidence <validation.json>
python3 .hydra-framework/scripts/hydra.py migration decide <slug> <batch> approve
python3 .hydra-framework/scripts/hydra.py migration request-close <slug> <batch> --reconciliation <reconciliation.json>
python3 .hydra-framework/scripts/hydra.py migration status <slug> <batch> --json
```

`migration inventory` is read-only. It classifies already-shared source material
that a human staged under `.migrations/` and reports provider surfaces, Hydra
projects, AI prompts/rules, task/session state, docs/wiki material, generated
surfaces, raw source material, and privacy or machine-local risk signals. It
does not create ledgers, suggest promotions, move files, or make staged material
canonical.

`migration ledger <slug>` is read-only unless `--create` is passed. It reports
the planned or existing shared workspace under
`.hydra-framework/intake/migrations/<YYYY-MM-DD>-<slug>/`. With `--create`, it
writes only `README.md` and `ledger.md` from the current inventory. Ledger rows
start as `pending` triage scaffolding; the command does not move staged files,
merge Hydra projects, import task records, suggest promotions, or make staged
material canonical.

The approval-aware commands implement one bounded autonomous-first batch.
`request-stage` inventories source roots and writes the exact proposed move but
does not stage them. `decide approve` applies the current digest-bound action;
`reject` requires a terminal rationale, and `revise` requires guidance while
retaining the batch identity. `propose` records package/unit drafts;
`validate-batch` accepts only fresh evidence from an independent validator
instance using a provider-neutral capability class, then prepares publication
approval. `request-close` refuses incomplete reconciliation and records the
exact staged paths whose approved removal will finish the batch. The shared
workspace remains the audit trail after originals are removed.

### Object references

```bash
python3 .hydra-framework/scripts/hydra.py ref resolve hydra://engine-module/object-family-registry
python3 .hydra-framework/scripts/hydra.py ref check
python3 .hydra-framework/scripts/hydra.py ref index
```

`ref resolve` explains the current object behind a stable `hydra://` ID using
semantic metadata plus derived path and digest state. `ref check` validates
duplicate IDs, unresolved `hydra://` references, and stale generated registry
entries. `ref index` writes the rebuildable registry at
`.hydra-framework/cognition/graph/registry.yaml`.

Object envelopes own identity, kind, lifecycle state, scope, owners, relations,
and provenance. Current path and digest are resolver output, not fields agents
maintain inside ordinary canonical files.

Markdown objects use frontmatter. Canonical YAML objects use the same envelope
as top-level fields when the file already has a natural YAML shape. Derived
state under `cognition/` is not scanned as canonical object input.

Objects that cannot safely carry inline metadata use a YAML sidecar with
`schema: hydra-framework.object-sidecar.v1`. Sidecar entries live under
`objects:`, carry `hydra_id`, optional `aliases`, semantic envelope fields, and
`path`, and may point at Markdown, YAML, or non-frontmatter files. Relative
paths are resolved from the sidecar file unless they start with a repository
root such as `.hydra-framework/`. `ref resolve` accepts aliases, `ref check`
rejects alias collisions, and `ref index` records aliases and the sidecar
`envelope_path`.

When `.hydra-framework/cognition/graph/registry.yaml` exists, `ref check` also
compares it with current canonical object metadata. It reports missing registry
paths, stale digests, missing or extra objects, stale aliases, and path changes.
Use `ref index` to refresh the derived registry after intentional object edits.

### Moving an object

```bash
python3 .hydra-framework/scripts/hydra.py move-object <source> <destination> [--dry-run]
```

`move-object` is the canonical path for an intentional move. It
relocates the file, rewrites the `path` of a sidecar-described object, and
refreshes the registry. It never touches `hydra_id` or `uid`, and it refuses a
move that would change the object's state tier, change its file suffix, or break
`hydra://` references — the last case is reverted rather than left half-applied.
Files that still cite the old path are reported as notes, not rewritten.

Manual moves still happen in ordinary Git and editor work, so `ref check` and
`validate` classify every path change with one mechanical test over `uid`, the
registry-recorded path, and the content digest:

- **Same uid, same digest, a new path, and nothing left at the old path** is an
  unambiguous move. `ref index` repairs it.
- **Anything else** — no uid on either side, a differing uid, a changed digest,
  or a file still sitting at the recorded path — is ambiguous or not a move at
  all. It is reported for a human or agent to decide and is never guessed.

When the readable `hydra_id` itself changed, pairing falls back to the opaque
`uid`; that fallback is why objects carry both identities.

### Task state

```bash
python3 .hydra-framework/scripts/hydra.py board                       # who is on what
python3 .hydra-framework/scripts/hydra.py board --owner <slug> --json
python3 .hydra-framework/scripts/hydra.py task start <name> --goal "<goal>"
python3 .hydra-framework/scripts/hydra.py task checkpoint <name-or-path>
python3 .hydra-framework/scripts/hydra.py task handoff <name-or-path> --to <owner>
python3 .hydra-framework/scripts/hydra.py task complete <name-or-path> --outcome <path|none>
python3 .hydra-framework/scripts/hydra.py note "This needs to be better"
printf '%s\n' "loose scratch" | python3 .hydra-framework/scripts/hydra.py note
python3 .hydra-framework/scripts/hydra.py migrate-state [--apply]
```

`note "Title"` creates a dated slug file under the private notes directory.
Stdin-only input appends to that day's scratch file in the same directory.

Records live in `tasks/personal/<owner>/`. The owner slug resolves from
`--owner`, then `HYDRA_OWNER`, then `git config user.email`; unset is an error
rather than a default, because a default owner is how several people end up
writing into one directory.

`board` is computed from the records on each run and never stored, so it cannot
disagree with them. `complete` deletes the record — Git history is the archive,
and `--outcome` forces the question of where the durable meaning went.

`migrate-state` moves a pre-0007 tree into the tiers. Finished records Git
already tracks are deleted; ones it does not are retired to private staging,
because there the working copy is the only copy.

### Docs and token guardrails

```bash
python3 .hydra-framework/scripts/hydra.py validate-wiki
python3 .hydra-framework/scripts/hydra.py wiki scaffold <project-name>
python3 .hydra-framework/scripts/hydra.py measure-context
python3 .hydra-framework/scripts/hydra.py compile-context --task "<task>" --provider codex --model gpt-5 --budget 12000
python3 .hydra-framework/scripts/hydra.py hook-token pre-context --budget <tokens>
python3 .hydra-framework/scripts/hydra.py hook-token command-result --command "<command>" --exit-code <code> < full.log
python3 .hydra-framework/scripts/hydra.py summarize-log --command "<command>" --exit-code <code> < full.log
python3 .hydra-framework/scripts/hydra.py retry-guard --command "<command>" --exit-code <code> < failure.log
```

## Tests

Behavior claims are backed by stdlib `unittest` suites under
`.hydra-framework/engine/tests/`:

- `unit/` mirrors `engine/src/hydra_engine/` one-to-one.
- `repository/` checks invariants against this live repository.
- `contract/` holds command-output golden tests.

Run them through the compatibility entrypoint, or discover them directly:

```bash
python3 .hydra-framework/scripts/hydra.py selftest
python3 -m unittest discover -s .hydra-framework/engine/tests -p 'test_*.py' -t .hydra-framework/engine/tests
```

New engine behavior needs a mirrored unit test in `engine/tests/unit/` and, when
it changes CLI output, a contract golden in `engine/tests/contract/`. Live
repository assumptions belong in `engine/tests/repository/`.

`validate` enforces the module rules from `hydra_engine.architecture`: source
modules stay under 400 lines, imports stay acyclic and layer-correct, fan-out is
bounded, widely imported vocabulary remains small, source modules have matching
unit tests, banned boundary names are rejected, and repository-root derivation
stays in the declared composition root or the shim.

## Policy

- Shared scripts must be deterministic enough to inspect and review.
- Shared scripts must not require secrets to run basic validation or export.
- Private scripts, machine paths, local MCP auth, and credentials belong in `.hydra-framework.local/`.
- Provider-specific scripts belong under `adapters/providers/<provider>/` unless they are reusable common helpers.


## Token-Efficiency Helpers

`hydra.py hook-token` is the hook-facing wrapper. It is deterministic and
quiet by default: successful checks print nothing unless `--report` is passed.
Budgets are not globally hardcoded. The workflow owner sets them with `--budget`
or private local config in the monitoring area. Use
`hydra.py init-local --write-token-policy`; it writes
`DEFAULT_TOKEN_HOOK_POLICY` from `agent_hooks/token_budget.py` when no local
policy file exists.

```bash
python3 .hydra-framework/scripts/hydra.py hook-token pre-context --budget 12000
python3 .hydra-framework/scripts/hydra.py hook-token pre-context --require-budget
python3 .hydra-framework/scripts/hydra.py hook-token command-result --command "npm test" --exit-code 1 < test.log
python3 .hydra-framework/scripts/hydra.py hook-command-output < claude-post-tool-use.json
python3 .hydra-framework/scripts/hydra.py hook-retry-guard < claude-post-tool-use-failure.json
python3 .hydra-framework/scripts/hydra.py hook-codex-command-output < codex-post-tool-use.json
python3 .hydra-framework/scripts/hydra.py hook-codex-retry-guard < codex-post-tool-use.json
```

Use `hook-token pre-context` at session, task, adapter-export, or CI boundaries.
Use `hook-token command-result` around commands whose raw output may otherwise
enter model context. It summarizes failures and large successful logs, records
retry fingerprints privately, and returns `2` only when repeated-failure policy
says normal retries should stop.

Provider hooks use the same reducer registry but different payload contracts.
Claude replaces large successful Bash output with
`hookSpecificOutput.updatedToolOutput` and uses a separate
`PostToolUseFailure` retry hook. Codex has no `updatedToolOutput` contract:
`hook-codex-command-output` returns `continue: false` feedback for large
successful Bash output, while `hook-codex-retry-guard` reads non-zero Bash
results from Codex `PostToolUse.tool_response` and blocks only at the repeated
failure threshold. Both providers keep raw full logs private and optional.

`hydra.py measure-context` estimates the size of provider-visible entry and
adapter surfaces. It is an approximation for guardrails and trend checks, not a
replacement for provider telemetry:

```bash
python3 .hydra-framework/scripts/hydra.py measure-context
python3 .hydra-framework/scripts/hydra.py measure-context --include-generated-skills
python3 .hydra-framework/scripts/hydra.py measure-context --fail-over 12000
```

`hydra.py compile-context` builds a bounded context packet over the current
knowledge-package system. It reuses package routing metadata (including a
matched route's units), knowledge-unit `reads:`, whole-file token estimates,
and resolver object metadata. The MVP prints selected read pointers and
provenance, not file bodies:

```bash
python3 .hydra-framework/scripts/hydra.py compile-context --task "Change Hydra task lifecycle fields" --provider codex --model gpt-5 --budget 12000
python3 .hydra-framework/scripts/hydra.py compile-context --task "Use the object identity resolver" --package hydra-framework --object hydra://engine-module/object-family-registry
python3 .hydra-framework/scripts/hydra.py compile-context --task "Hydra context compiler" --json
```

The packet includes selected context, omitted candidates, required units and
their overage (a `requires` unit larger than the budget is still included --
that is reported, never gated), token estimates, provenance/freshness notes,
and validation or known-risk reminders. A route's `avoid_by_default` and
`verify` are merged into the packet; a unit's own `reads:` become
package-scoped candidates when that unit is selected. A unit whose
`provenance.sources` entry was committed after its own `checked_on` is
marked `[STALE: ... committed after checked_on]` on its selected-context
line -- advisory only, never a `validate` failure, since an intentionally
stale unit must stay legal.

`hydra.py knowledge-search` retrieves ranked, cited snippets from indexed
Hydra knowledge (`repo/knowledge/`, `capabilities/`,
`core/`, `validation/`, the engine source, and `AI_SYSTEM.md`) without
loading whole files. Prefer it over reading a directory or grepping when a
package route does not match the task, or as the first step before broader
search:

```bash
python3 .hydra-framework/scripts/hydra.py knowledge-search "task record ownership"
python3 .hydra-framework/scripts/hydra.py knowledge-search "hydra://engine-module/object-family-registry" --limit 5
python3 .hydra-framework/scripts/hydra.py knowledge-search "routing false positive" --budget 1000
```

Results are ranked (exact id/path match, then package-route hits, then
lexical relevance) and trimmed to `--budget` approx tokens; omitted
lower-ranked hits are reported, not silently dropped. `hydra.py
hook-reindex-knowledge` refreshes the private local SQLite index this reads
from; `knowledge-search` falls back to an in-memory scan when no index
exists. `hydra.py delegation-brief` shapes the same search into a
read-first brief with stop rules, for handing a bounded reading list to a
subagent.

`hydra.py summarize-log` reduces noisy command output before an agent reads it.
It preserves exact error lines, paths, commands, and stack-frame literals. Use
`--store-full` only when the full log should be retained privately under
`.hydra-framework.local/logs/`:

```bash
python3 .hydra-framework/scripts/hydra.py summarize-log --command "npm test" --exit-code 1 < test.log
python3 .hydra-framework/scripts/hydra.py summarize-log --store-full --name test-run < test.log
```

`hydra.py retry-guard` records repeated failure fingerprints in private local
state. When the same command/error shape reaches the threshold, normal retries
should stop and the next step should change hypothesis, narrow validation, or
ask a human:

```bash
python3 .hydra-framework/scripts/hydra.py retry-guard --command "npm test" --exit-code 1 < failure.log
```

## Package Documentation Gates

`hydra.py validate-package-docs` validates knowledge-package Markdown links and,
when requested, renders package DOT diagrams. Run it for all packages, one slug,
or an explicit package path:

```bash
python3 .hydra-framework/scripts/hydra.py validate-package-docs
python3 .hydra-framework/scripts/hydra.py validate-package-docs --package <package-slug>
python3 .hydra-framework/scripts/hydra.py validate-package-docs --path .hydra-framework/repo/knowledge/spaces/<space-slug>
python3 .hydra-framework/scripts/hydra.py validate-package-docs --package <package-slug> --render
```

`--render` requires Graphviz `dot`; the default gate does not render diagrams.

## Prompt Routing

`hydra.py route-prompt` reads package `routing.yaml` files and emits tiny routing
pointers for matching prompts. It intentionally prints paths to read, not package
contents:

```bash
python3 .hydra-framework/scripts/hydra.py route-prompt --prompt "question text"
```

Provider UserPromptSubmit-style hooks can pipe their prompt JSON to the same
command.

## Wiki Surface Helpers

`hydra.py validate-wiki` validates Markdown links and Obsidian-style `[[links]]` under `project-wiki/` by default:

```bash
python3 .hydra-framework/scripts/hydra.py validate-wiki
python3 .hydra-framework/scripts/hydra.py validate-wiki --path project-wiki/hydra-framework
```

`hydra.py wiki scaffold <project-name>` creates starter human wiki pages under `project-wiki/<project-name>/` without reading or migrating project code:

```bash
python3 .hydra-framework/scripts/hydra.py wiki scaffold <project-name> --title "<Project Name>"
```

Use the scaffold as a starting point, then migrate existing project docs one area at a time and link pages to verified source material.

## Post-Edit Hook Gate

`hydra.py hook-post-edit` reads provider tool-call JSON from stdin and does two
things, in order:

1. If the edited path is inside a provider directory (`.claude/`, `.agents/`, `.codex/`) and is not a current generated file, it prints guidance for reclaiming it. This is advisory: it never blocks the write.
2. Otherwise, if the edited path belongs to a knowledge space, it runs that node-document gate and fails on deterministic errors.

```bash
python3 .hydra-framework/scripts/hydra.py hook-post-edit
```

The first behavior exists because the common way Hydra gets bypassed is someone
adding a skill or subagent where their runtime expects it, never touching
`.hydra-framework/`. Catching it at write time is cheaper than discovering it at
the next export.

Use package-local `scripts/check.sh` wrappers for project-specific stricter
checks.
