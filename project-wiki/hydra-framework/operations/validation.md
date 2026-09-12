# Validation

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

Status: reference

Validation turns deterministic Hydra contracts into repeatable evidence. The
wiki link gate is separate from canonical Hydra validation because
`project-wiki/` is a human-facing surface outside `.hydra-framework/`.

## Choose the Gate

| Need | Command | Evidence owner |
| --- | --- | --- |
| Check Markdown and double-bracket wiki links after a page move | `python3 .hydra-framework/scripts/hydra.py validate-wiki` | Wiki command and link validator |
| Check one knowledge space's node document, links, units, and size | `python3 .hydra-framework/scripts/hydra.py validate-package-docs --node hydra-framework` | Node and document checks |
| Check that logical bindings still resolve and their assertions hold | `python3 .hydra-framework/scripts/hydra.py bindings verify` | Binding resolution and assertions |
| Check repository-wide Hydra state | `python3 .hydra-framework/scripts/hydra.py validate` | Validator registry and aggregation |
| Check this checkout's generated provider surfaces for drift (local only) | `python3 .hydra-framework/scripts/hydra.py export-adapters --check` | Provider export planner |
| Check for provider files Hydra does not own (the CI gate for provider surfaces) | `python3 .hydra-framework/scripts/hydra.py reclaim --fail-on-findings` | Reclaim classifier |
| Check engine behavior and CLI contracts | `python3 .hydra-framework/scripts/hydra.py selftest` | Bundled unit, repository, and contract tests |
| Inspect required paths and local health before validation | `python3 .hydra-framework/scripts/hydra.py doctor` | Doctor command, then the same validation aggregation |

`validate-wiki` reports the owning file for each missing Markdown or Obsidian
link. `validate` prints every finding in validator order and returns a nonzero
status when a check fails. A passing full gate prints `Hydra validate: ok`.
The other commands are focused checks for the surfaces named in the table.

Generated provider adapters are Git-ignored and untracked, so a clean clone
has none materialized and `export-adapters --check` has nothing committed to
compare against; it stays a local developer command. CI instead bootstraps
adapters with a plain `export-adapters` run before any check that reads
materialized provider surfaces (`selftest`, `doctor`), and gates on
`reclaim --fail-on-findings` for orphaned, drifted, or stale files. See
[Provider Adapters](/project-wiki/hydra-framework/extending-hydra/provider-adapters.md#bootstrap-a-fresh-clone).

## What Full Validation Demonstrates

The full gate covers active task records, provider surfaces, capability and
module metadata, task-contract documentation, adaptation state, tier
boundaries, engine architecture, object references, package documentation,
capability-caller evidence, and evolution or telemetry queue contracts. It
does not replace human review of whether a page is useful or whether a claim is
well scoped.

`doctor` and `validate` also print provider verification notes. These show the
provider runtime and, when known, its recorded version, alongside the date its
compatibility evidence was last checked. Evidence older than 30 days is
reported as an advisory to recheck, independently of Hydra's own framework
build status.

## Review Boundary

Validation owns deterministic checks with concrete remediation. The
mechanical-proxy standard in the validation contract
keeps judgment-shaped working agreements out of brittle validators. Use the
canonical owner for policy, commands, and procedures, and use this page to
choose the evidence gate.

## Evidence For Review

For a scoped change, retain the command, its exit result, and the relevant
finding path or passing verdict. Match the gate to the changed surface rather
than presenting a broad pass as proof of an unrelated claim. A full validation
pass is useful evidence for shared Hydra state; it does not establish that the
wiki is clear, that a proposed design is appropriate, or that a deferred
integration exists.

The changed object's `owners:` field identifies the responsible team. This
repository's CODEOWNERS maps shared framework
and wiki paths to the repository's current review route. There is deliberately
no parallel reviewer register, and the normal Git review path records who
actually reviewed the change. For telemetry-specific boundaries and evidence,
use [Evidence and Telemetry](/project-wiki/hydra-framework/operations/evidence-and-telemetry.md).
