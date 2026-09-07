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
| Check generated provider surfaces for drift | `python3 .hydra-framework/scripts/hydra.py export-adapters --check` | Provider export planner |
| Check engine behavior and CLI contracts | `python3 .hydra-framework/scripts/hydra.py selftest` | Bundled unit, repository, and contract tests |
| Inspect required paths and local health before validation | `python3 .hydra-framework/scripts/hydra.py doctor` | Doctor command, then the same validation aggregation |

`validate-wiki` reports the owning file for each missing Markdown or Obsidian
link. `validate` prints every finding in validator order and returns a nonzero
status when a check fails. A passing full gate prints `Hydra validate: ok`.
The other commands are focused checks for the surfaces named in the table.

## What Full Validation Demonstrates

The full gate covers active task records, provider surfaces, capability and
module metadata, task-contract documentation, adaptation state, tier
boundaries, engine architecture, object references, package documentation,
capability-caller evidence, and evolution or telemetry queue contracts. It
does not replace human review of whether a page is useful or whether a claim is
well scoped.

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
