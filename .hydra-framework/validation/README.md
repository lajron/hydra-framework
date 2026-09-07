# Validation

Validation keeps framework structure and knowledge coherent.

Validation currently checks:

- required manifests
- broken references
- private state accidentally placed in Git
- task-state consistency
- generated surface freshness
- command-to-argparse reachability and snippet-validated cross-surface caller evidence
- knowledge-package Markdown links and routing metadata
- module metadata and task-contract documentation
- adaptation-ledger consistency
- Hydra engine architecture bounds

Future checks may validate:

- duplicate canonical sources
- derived cognition rebuildability
- context surface budget checks when a repository opts into them

New checks for judgment-shaped working agreements must meet a mechanical-proxy
standard: deterministic artifact, recurring or imminent harm, low false
positives, and obvious remediation.


## Current Checks

`python3 .hydra-framework/scripts/hydra.py validate` checks:

- required fields in active task Markdown records
- generated provider surface metadata and drift
- every `command_*` implementation has an argparse caller, and
  `validation/capability-callers.yaml` snippets still point at live
  cross-surface caller evidence classified as `automatic`, `manual`, or
  `intentionally-disabled`
- module metadata, capability maps, task contract docs, adaptation ledger, tier boundaries, and object references
- knowledge-package Markdown links and routing metadata for discovered packages
- `hydra_engine` architecture: source/test size caps, acyclic imports, layer direction, high-in-degree vocabulary limits, fan-out limits, one unit test per source module, banned boundary names, and root-derivation locality

`python3 .hydra-framework/scripts/hydra.py validate-package-docs` runs the
package documentation gate directly and can optionally render DOT diagrams with
`--render`.

`python3 .hydra-framework/scripts/hydra.py selftest` also includes synthetic
negative tests for the architecture checker and a repository smoke test that the
live engine tree satisfies those bounds.

## Package Gate Defaults

The default package gate is intentionally cheap and deterministic:

- internal Markdown links must resolve
- package `routing.yaml` files must use `hydra-framework.package-routing.v2`,
  point at existing package files, and reference valid knowledge units from
  routes
- DOT diagrams render only when explicitly requested

Repositories can layer stricter package-local checks through
`spaces/<space-slug>/scripts/check.sh`.


## Optional Token Guardrails

These commands are manual guardrails, while provider Bash hooks wire the same
command-output and retry behavior where the runtime supports it. Use
Use `hydra.py hook-token pre-context --budget <tokens>` or `hydra.py
measure-context --fail-over <tokens>` in CI or local checks when a repository
wants adapter-size enforcement. Keep the threshold repository-specific and
review growth with a short token-efficiency rationale before expanding
always-loaded surfaces.

Use `hydra.py hook-token command-result` around noisy or repeated validation
failures before handing output back to an agent. It combines compact log
summarization with retry fingerprinting. The lower-level `summarize-log` and
`retry-guard` commands remain available for manual or custom wrappers. Claude
uses `hook-command-output` and `hook-retry-guard`; Codex uses
`hook-codex-command-output` and `hook-codex-retry-guard`.
