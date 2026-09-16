# Validation

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

Status: reference

Validation turns deterministic Hydra contracts into repeatable evidence. Start
with the smallest gate that answers the question, then use the full gate when
the change crosses several framework surfaces. The wiki link gate is separate
from canonical Hydra validation because `project-wiki/` is a human-facing
surface outside `.hydra-framework/`.

## Choose the Gate

| Need | Command | Mode and boundary | Evidence owner |
| --- | --- | --- | --- |
| Check Markdown and double-bracket wiki links after a page move | `python3 .hydra-framework/scripts/hydra.py validate-wiki` | Blocking link and traversal check | Wiki command and link validator |
| Check one knowledge space's node document, links, units, and size | `python3 .hydra-framework/scripts/hydra.py validate-package-docs --node hydra-framework` | Blocking package check; `--render` also writes diagram images | Node and document checks |
| Check that logical bindings still resolve and their assertions hold | `python3 .hydra-framework/scripts/hydra.py bindings verify` | Focused check; `--accept` writes a reviewed fingerprint | Binding resolution and assertions |
| Report stale Knowledge v3 sources | `python3 .hydra-framework/scripts/hydra.py knowledge stale` | Report-only; an intentionally stale unit is not a hard failure | Knowledge freshness report |
| Report wiki source freshness and declaration gaps | `python3 .hydra-framework/scripts/hydra.py wiki audit` | Report-only; exits successfully when it reports findings | Wiki sidecar audit |
| Check repository-wide Hydra state | `python3 .hydra-framework/scripts/hydra.py validate` | Blocking aggregation of the registered validators | Validator registry and aggregation |
| Record current Knowledge or wiki source digests | `python3 .hydra-framework/scripts/hydra.py knowledge fingerprint --unit <hydra-id>` or `wiki fingerprint --page <hydra-id>` | Writes tracked provenance metadata; re-read sources first | Fingerprint commands |
| Check this checkout's generated provider surfaces for drift | `python3 .hydra-framework/scripts/hydra.py export-adapters --check` | Local drift check only; generated files are ignored | Provider export planner |
| Check for provider files Hydra does not own | `python3 .hydra-framework/scripts/hydra.py reclaim --fail-on-findings` | Blocking CI provider-surface ownership gate | Reclaim classifier |
| Check engine behavior and CLI contracts | `python3 .hydra-framework/scripts/hydra.py selftest` | Blocking test run | Bundled unit, repository, and contract tests |
| Check an orchestration request or result | `orchestration status`, then the focused orchestration tests | Ledger read plus explicit review/validation state; no provider execution claim | Orchestration control-plane modules and mirrored tests |
| Inspect required paths and local health before validation | `python3 .hydra-framework/scripts/hydra.py doctor` | Blocking when required paths, private-tier setup, or validation fail | Doctor command, then the same validation aggregation |
| Check telemetry redaction before making shared evidence | `python3 .hydra-framework/scripts/hydra.py telemetry gate` | Blocking redaction gate; `--output` additionally writes an attestation | Telemetry gate |

`validate-wiki` reports the owning file for each missing Markdown or Obsidian
link. `validate` prints every finding in validator order and returns a nonzero
status when a check fails. A passing full gate prints `Hydra validate: ok`.
The other commands are focused checks for the surfaces named in the table, and
their mode matters when you interpret an exit code.

Generated provider adapters are Git-ignored and untracked, so a clean clone
has none materialized and `export-adapters --check` has nothing committed to
compare against; it stays a local developer command. CI instead bootstraps
adapters with a plain `export-adapters` run before any check that reads
materialized provider surfaces (`selftest`, `doctor`), and gates on
`reclaim --fail-on-findings` for orphaned, drifted, or stale files. The plain
export is bootstrap, not proof that a provider surface is owned. See
[Provider Adapters](/project-wiki/hydra-framework/extending-hydra/provider-adapters.md#bootstrap-a-fresh-clone).

## Reports, hooks, and CI

The validator registry currently holds 19 ordered checks. Their findings are
blocking when returned by `validate`; queue age, provider compatibility age,
retry-state growth, and other drain signals are printed as notes after a
successful verdict. Advisory output is evidence to review, not a substitute
for a failing contract check.

`wiki audit`, `knowledge stale`, and `measure-context` are report surfaces.
They help a maintainer decide what to inspect, but their successful exit does
not prove completeness, freshness of every undeclared source, or an acceptable
context budget unless `measure-context --fail-over <tokens>` is explicitly
used. `hook-token` is an optional guardrail: it is quiet on success and returns
2 for a configured budget overage or a repeated failure threshold.

`hook-post-edit` is scoped to the edited Knowledge package. It reports package
issues caused by that edit and counts unrelated pre-existing issues instead of
blaming the new file for them. It is useful immediate feedback, not a
repository-wide replacement for `validate`. The optional pre-push hook calls
`validate` and can block a push when installed. Post-commit, post-merge,
post-checkout, and post-rewrite hooks refresh derived local state on a
best-effort basis.

The CI-authoritative sequence is plain `export-adapters`, `selftest`, `doctor`,
the private-state check, `reclaim --fail-on-findings`, package validation, wiki
link validation, the report-only wiki audit, and context-size reporting. A
report-only step remains report-only in CI; it must not be described as a
blocking gate.

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

Orchestration validation is a separate local control-plane concern. A complete
result, independent review, and independent validation are required before a
run can be marked complete. A queued or acknowledged provider receipt is not
execution evidence, and a stale date never authorizes owner deletion or worker
reaping. Keep provider execution and human approval claims outside the ledger
unless an explicit adapter and reviewer provide that evidence.
