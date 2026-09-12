"""Seed text for Hydra's private local tier."""

from __future__ import annotations

PRIVATE_ROOT = ".hydra-framework" ".local"

PRIVATE_TIER_INTRO = (
    f"This is the shape of `{PRIVATE_ROOT}/`, the private tier. It is created "
    "and seeded by `hydra.py init-local`; most machine-written files are "
    "created on demand by `hydra.py`."
)

TOP_LEVEL_README = f"""# Private Hydra Framework Layer

{PRIVATE_TIER_INTRO}

`{PRIVATE_ROOT}/` is never committed. That is not only about secrets: it is
where planning, open questions, and honest reactions live, and people record
what is actually wrong with something only when it is not permanently attributed
in a shared repository.

The placement rules define the tiers. `repo/knowledge/state-tiers.md` is the practical
guide.

## Areas

| Path | Kind | Holds |
| --- | --- | --- |
| `notes/` | machine | Free-form thinking. `hydra.py note "Some Title"` creates a dated titled note; stdin-only input appends to today's scratch note. |
| `intake/raw/` | machine | Source descriptors and safe source copies awaiting processing. |
| `intake/extracted/` | machine | Text, links, parsed metadata, and other source-derived artifacts. |
| `intake/triage/` | machine | Staging notes deciding what is useful, duplicated, unclear, or promotable. |
| `monitoring/` | machine | Private token, retry, loop-halt, and cost observations. |
| `index/` | machine | Rebuildable private search and retrieval indexes. |
| `logs/` | machine | Private execution logs kept out of shared history. |
| `baseline/` | machine | Private baseline snapshots and local comparison state. |
| `tasks/retired/` | machine | Finished records Git never tracked, kept because nothing else holds them. |
| `migrations/` | machine | Originals drained from a source area. |
| `evolution/experiments/` | machine | Framework trials that have not earned a candidate yet. |
| `scratch/` | thinking | Half-formed work, temporary calculations, and quick throwaways. |
| `plans/` | thinking | Private planning before the useful result becomes a task record or shared doc. |
| `research/` | thinking | Private research notes and checked-but-not-promoted findings. |
| `prompts/` | thinking | Prompt drafts, comparisons, and local prompt experiments. |
| `diagrams/` | thinking | Private sketches and diagrams before they become durable documentation. |
| `source-material/` | thinking | Local source material that should not be committed as an archive. |
| `tickets/` | thinking | Private ticket notes, triage, and issue-system drafts. |
| `bug-reports/` | thinking | Private bug reproduction notes and report drafts. |
| `developer/` | config | Personal workflow preferences. |
| `machine/` | config | Operating system, capabilities, and local tool mappings. |
| `repo-overrides/` | config | Repository-specific private overrides. |
| `secrets/` | config | Credentials or secret references. |
| `locks/` | machine | The per-checkout export lock guarding `export-adapters`/`profile select`. |
| `capabilities/` | config | The local capability-profile policy (`profiles.yaml`) and machine-owned selection (`active.yaml`). |

## What Does Not Belong Here

Task records. Those are personal, not private: they live tracked in
`.hydra-framework/tasks/personal/<owner>/` so they survive a lost machine and can
be inherited by whoever picks up the work.

## Two Cautions

**This directory is not backed up.** It is outside Git by design, so a lost
machine loses it. Anything you cannot afford to lose belongs in the personal or
shared tier. You may make `{PRIVATE_ROOT}/` a symlink into a synced directory if
you want it on more than one machine.

**Nothing shared may cite a file in here.** You can follow the path; no teammate
can, and they cannot tell a real citation from one they simply lack. When
promoting, copy what the shared file needs - origin, date checked, the claim -
into the shared file itself. `hydra.py validate` fails on violations.
"""

THINKING_SUFFIX = (
    "This is private thinking space: half-formed material is welcome here, "
    "nothing here is validated, and nothing here is authoritative for anyone else."
)

AREA_README = {
    "notes": f"""# Notes

Free-form thinking. `hydra.py note "Some Title"` creates a dated titled note
here, such as `YYYY-MM-DD-some-title.md`. Stdin-only input appends to today's
scratch note, `YYYY-MM-DD.md`.

{THINKING_SUFFIX}
""",
    "intake/raw": """# Raw Intake

Source descriptors and safe source copies awaiting processing live here before
anything is promoted into shared Hydra state.
""",
    "intake/extracted": """# Extracted Intake

Generated extraction artifacts such as text, links, parsed metadata, summaries,
or other source-derived files live here while intake work is private.
""",
    "intake/triage": """# Intake Triage

Use this area for staging notes that decide what is useful, duplicated, unclear,
unsafe, or promotable before shared promotion records are written.
""",
    "monitoring": """# Monitoring

Private token, retry, loop-halt, and cost observations live here. Keep provider
billing exports, customer data, credentials, and raw conversations out of this
area unless a workflow explicitly says how to sanitize them first.
""",
    "index": """# Index

Private search and retrieval indexes live here. Treat this area as rebuildable
machine-local state, not durable knowledge.
""",
    "logs": """# Logs

Private execution logs live here when a command or hook needs local evidence that
does not belong in shared history.
""",
    "baseline": """# Baseline

Private baseline snapshots and local comparison state live here. Promote only the
durable conclusion, not the machine-local working files.
""",
    "tasks/retired": """# Retired Tasks

Finished records Git never tracked may live here when nothing else holds them.
Tracked Hydra task records are completed by deletion because Git is their archive.
""",
    "migrations": """# Private Migration Staging

Shape reference. The real directory is `.hydra-framework.local/migrations/` and
is never committed.

## Layout

```
.hydra-framework.local/migrations/<YYYY-MM-DD>-<slug>/
    originals/          moved source roots, relative paths preserved
    notes.md            optional private working notes
```

## Purpose

Originals move here as the first step of a material migration, before anything is
promoted. This drains the host repository in one reversible operation and gives
the migration an undo that does not depend on Git having tracked the source.

The shared side of the same migration lives in
`.hydra-framework/intake/migrations/<slug>/` and holds the ledger and outcome.
Shared decisions, private material.

## Two Repository Shapes

- **Material was already committed and shared.** Git holds the history, so
  staging is a convenience and can be dropped once the ledger closes.
- **Each developer keeps a private pile.** Staging is the permanent home. Hydra
  extracts the shareable subset into canonical state and the rest stays here,
  which is the only correct place for it.

## Rules

- Verify this path is Git-ignored before moving anything into it. Probe a path
  beneath the directory, since a dir-only ignore pattern will not match a
  directory that does not exist yet.
- Do not promote raw copies from here into shared state. Promote durable meaning.
- Do not delete from `originals/` while any ledger row is still `pending`.
- This directory is not backed up by Git. Back it up separately if it holds the
  only copy of material that matters.
""",
    "evolution/experiments": """# Evolution Experiments

Framework trials live here before they have earned a shared evolution candidate.
Keep rough notes cheap; promote only reusable evidence and conclusions.
""",
    "scratch": f"""# Scratch

Temporary calculations, snippets, and throwaway work live here.

{THINKING_SUFFIX}
""",
    "plans": f"""# Plans

Private planning lives here before the useful result becomes a task record,
workflow, or other shared artifact.

{THINKING_SUFFIX}
""",
    "research": f"""# Research

Use this area for research notes and checked-but-not-promoted findings.

{THINKING_SUFFIX}
""",
    "prompts": f"""# Prompts

Prompt drafts, comparisons, and local prompt experiments live here.

{THINKING_SUFFIX}
""",
    "diagrams": f"""# Diagrams

Sketches and private diagrams live here before they become durable documentation.

{THINKING_SUFFIX}
""",
    "source-material": f"""# Source Material

Local source material that should not be committed as an archive lives here.

{THINKING_SUFFIX}
""",
    "tickets": f"""# Tickets

Private ticket notes, triage, and issue-system drafts live here.

{THINKING_SUFFIX}
""",
    "bug-reports": f"""# Bug Reports

Private bug reproduction notes and report drafts live here.

{THINKING_SUFFIX}
""",
    "developer": """# Developer

Personal workflow preferences live here. These settings describe one person, not
the repository, so they are private.
""",
    "machine": """# Machine

Operating system, capabilities, and local tool mappings live here. These settings
describe this machine, not the repository, so they are private.
""",
    "repo-overrides": """# Repo Overrides

Repository-specific private overrides live here. Shared behavior belongs in the
tracked framework; local exceptions stay private.
""",
    "secrets": """# Secrets

Store secret references here, not secret values. Prefer a password manager,
credential helper, vault, or environment-specific reference that can be rotated
outside the repository.
""",
    "locks": """# Locks

The per-checkout export lock lives here (`locks/export.lock`), guarding every
`hydra.py export-adapters` and `hydra.py profile select` mutation so two
processes can never interleave writes and removals. The file itself carries no
state -- it exists only to be locked -- and is safe to delete when nothing
holds it.
""",
    "capabilities": """# Capabilities

Two files, deliberately separate:

- `profiles.yaml` is hand-authored. It declares local capability profiles as
  named groups of tags, and is never rewritten by Hydra.
- `active.yaml` is machine-owned. `hydra.py profile select <name>` rewrites it
  wholesale; do not hand-edit it.

See `hydra.py profile list`/`show`/`select`.
""",
}

TOKEN_USAGE_TEMPLATE = f"""# Token Usage Monitoring

Use this private template in `{PRIVATE_ROOT}/monitoring/token-usage.md` when measuring AI cost or context pressure. Do not store API keys, provider billing exports, customer data, or raw conversations here.

## Baseline

Date:
Provider or surface:
Model or capability class:
Task or workflow:

| Metric | Value | Source |
| --- | --- | --- |
| Requests |  |  |
| Input tokens |  |  |
| Cached-input tokens |  |  |
| Output tokens |  |  |
| Reasoning tokens |  |  |
| Tool-output tokens or bytes |  |  |
| Estimated cost |  |  |
| Retry count |  |  |
| Loop halts |  |  |


## Context Surface Baseline

Use this with `hydra.py measure-context` when adapter or always-loaded prompt
surfaces change.

Date:
Command:
Budget or comparison target:

| Surface | Approx tokens | Notes |
| --- | ---: | --- |
|  |  |  |

Decision:

## Token Hook Policy

Use `{PRIVATE_ROOT}/monitoring/token-hooks.json` for private local hook
thresholds. The shared example leaves `context_budget_tokens` unset on purpose;
the budget should come from the workflow, model/context window, cached-token
telemetry, and the cost of the surfaces that are always loaded.

Budget owner:
Budget value:
Reason for value:
Revisit trigger:

## Retry Guard

`hydra.py retry-guard` stores fingerprints in
`{PRIVATE_ROOT}/monitoring/retry-state.jsonl`, one JSON event appended per
line (failures and reset tombstones), so a fingerprint's count is the
aggregate of its lines since the last reset rather than a single stored
number. Treat that file as private machine-local execution state. Do not
commit it. Safe to delete if it grows large: the counter simply restarts
from zero.

Loop halt reviewed:
Changed hypothesis or narrowed command:
Human escalation needed:

## Observation

What caused the largest token or cost pressure:

What was changed:

Validation or quality check:

Result:

## Tool Evaluation Gate

Use this before installing or routing through a token-saving tool, gateway, context compressor, or browser mapping layer.

- Baseline captured:
- Source or vendor trust reviewed:
- Privacy boundary reviewed:
- Rollback path exists:
- Correctness checked against uncompressed or direct behavior:
"""

MIGRATION_STAGING_README = AREA_README["migrations"]

DEVELOPER_PREFERENCES_STUB = """# Developer Preferences

Record personal workflow preferences here when they help local agents route or
operate. Do not treat this as repository policy.
"""

MACHINE_PROFILE_STUB = """# Machine Profile

os:
capabilities: []
tool_mappings: {}
"""

SECRETS_README = AREA_README["secrets"]
