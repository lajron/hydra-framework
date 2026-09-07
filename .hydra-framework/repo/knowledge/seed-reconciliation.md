---
title: Seed Reconciliation
status: active
created: 2026-07-30
owners:
  team: hydra
certainty: confirmed
provenance:
  sources:
    - .hydra-framework/README.md
    - .hydra-framework/evolution/adaptations.md
    - .hydra-framework/manifest.yaml
---

# Seed Reconciliation

## Purpose

Hydra spreads by copy, not by package manager. Someone places `.hydra-framework/`
into a repository and an agent wires it up. That makes divergence the normal
state, not an error, and it makes reconciliation a first-class responsibility
rather than a cleanup chore.

This document defines the lifecycle. The procedures live in the `adoption` and
`seed-reconciliation` skills.

## Lifecycle

`base seed -> copy -> adopt -> adapt -> record -> compare -> promote-or-keep-local`

- **copy**: `hydra.py init --target <repo>` places the framework, or a human copies it.
- **adopt**: `hydra.py adopt` reports what integration needs; `--record` stamps lineage.
- **adapt**: the repository changes Hydra to fit itself. Expected and encouraged.
- **record**: `hydra.py evolution record` appends intent, evidence, and disposition to `evolution/adaptations.md`.
- **compare**: `hydra.py diff-base --base <path>` compares local against base by content hash and marks differences as explained or unexplained from the adaptation ledger.
- **promote-or-keep-local**: each difference either becomes an evolution candidate for the base seed or is deliberately marked repository-local.

## Lineage

`manifest.yaml` carries a `lineage` block recording which base version a copy
descends from, which repository adopted it, and when. Without lineage a
comparison cannot distinguish "this repository adapted the file" from "the base
moved on," so classification degrades to guesswork. Record it at adoption time.

Lineage is descriptive, not authoritative: it says where a copy came from, not
which side is currently correct.

## Adaptation Ledger

`evolution/adaptations.md` is an append-only ledger for deliberate divergence
from the base seed. It is read on demand during reconciliation and is not part
of always-loaded context.

Each entry records:

- date
- base seed version at the time of change
- paths touched
- why the change was made
- evidence checked
- disposition: `repo-local` or `promote-candidate`

Record deletions as well as additions. A deliberate local deletion without a
ledger entry is indistinguishable from stale drift during a later comparison.

Write entries with `hydra.py evolution record`, which enforces the shape that
`hydra.py validate` checks. Paths are stored relative to `.hydra-framework/`.

Two files are explained by construction and never need an entry: `manifest.yaml`
carries the lineage block that `adopt --record` stamps, and the ledger itself
changes whenever anything is recorded. Every adopted copy differs from its base
in both, so treating them as drift would make `--fail-on-drift` unpassable.

## Difference Classification

`diff-base` reports explained and unexplained differences. The mechanical class
is still shown per path for diagnosis:

| Mechanical | Intent options |
| --- | --- |
| `local-modified` | `promote`, `repo-local`, `stale`, `conflicting` |
| `local-only` | `promote`, `repo-local` |
| `base-only` | `stale` (adopt the base version) or deliberately removed |
| `identical` | nothing to decide |

Read the ledger before assigning intent. If a path is explained, do not
re-litigate it unless new evidence contradicts the entry. If a path is
unexplained, assign intent:

- **promote**: solves a general problem any repository would hit. Needs evidence.
- **repo-local**: correct here, wrong or meaningless elsewhere.
- **stale**: the local copy is behind; the base version should win.
- **conflicting**: both sides changed the same meaning. Needs a human decision.

## Promotion Requires Evidence

A promotion candidate must name the observed problem, the change, and some sign
it worked. "Looks tidier" is not evidence. Record candidates in
`evolution/candidates/` using `evolution/templates/improvement-record.md`.

## What Never Promotes

- Repository-specific knowledge spaces, wiki pages, and task records.
- Host-specific paths, service names, and build commands.
- Anything from `.hydra-framework.local/`.
- Generated provider surfaces. Promote the canonical module instead.

## Boundaries

- Reconciliation reports and recommends. It does not overwrite either side automatically.
- A newer timestamp is not authority. Content and stated intent decide.
- `diff-base` deliberately ignores `tasks/` and `cognition/`: those are repository history and generated state, not framework definition.
