---
title: State Tiers
status: active
created: 2026-07-30
owners:
  team: hydra
certainty: confirmed
provenance:
  sources:
    - .hydra-framework/core/placement-rules.md
    - .hydra-framework/engine/src/hydra_engine/installation/private_tier.py
---

# State Tiers

## Purpose

Where a piece of state goes, and how an agent knows what it is looking at.

This is the operational companion to `core/placement-rules.md`. The core rule
states the boundary; this file answers the questions that come up while applying it.

## The Tiers

| Tier | Question | Location | Git |
| --- | --- | --- | --- |
| Shared | Does this describe the repository? | `.hydra-framework/` | tracked, review-gated |
| Personal | Is this my structured work, that someone inherits if I vanish? | `.hydra-framework/tasks/personal/<owner>/` | tracked |
| Private | Is this my thinking, which should not be permanent? | `.hydra-framework.local/` | ignored |

## Private Tier Shape

`.hydra-framework.local/` is created and seeded by `hydra.py init-local`, and
new repositories receive that seed automatically from `hydra.py init --target`.
It is not copied from a tracked mirror tree.

This table is expected, not exhaustive. It lists every area Hydra seeds and
therefore the shape an agent should be able to rely on. A person may create
other private directories without making them repository policy first.

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

The directory is not backed up by Git. Anything you cannot afford to lose
belongs in the personal or shared tier, or in a private backup you manage. It
may be a symlink into a synced directory if you want it on more than one
machine.

Nothing shared may cite a file in the private tier. You can follow the path; no
teammate can, and they cannot tell a real citation from one they simply lack.
When promoting, copy what the shared file needs - origin, date checked, and the
claim - into the shared file itself.

## Provider-Local Memory

Some providers keep their own persistent memory outside this repository
entirely — for example Claude Code's per-project auto-memory, or an
equivalent Codex feature. It is written at model discretion across sessions
and lives in the provider's own account storage, keyed by project path, not
in this working tree.

This is a fourth kind of state, not a fourth tier. It sits outside the three
tiers above: Hydra does not create it, seed it, back it up, or version it, and
`hydra.py validate` cannot inspect it, because it is not part of the
repository at all.

Treat it the way private-tier material is treated, with one further
restriction: because it is not even in the repository, no shared file or
Hydra command may cite a provider-memory path, and no shared claim may rest on
"the assistant remembers this."

- It is authoritative about nothing shared. It may reflect stale, per-person,
  or per-machine understanding that other teammates and other providers never
  see.
- A durable claim worth keeping — a fact about the repository, an accepted
  standing preference that should outlive one person's provider account — is
  promoted the same way a private note is promoted: inline the verified claim
  into its canonical owner or a personal task record. Until promoted, it stays
  personal convenience state, not Hydra memory.
- Do not delegate durable Hydra state — task records, accepted rules,
  constraints, validation evidence, supersession — to provider auto-memory.
  Critical records require deterministic or explicit tool-mediated
  capture; provider auto-memory is model-discretion
  capture and does not meet that bar.

## What An Agent Should Assume

- Anything under `.hydra-framework/` outside `tasks/personal/` is authoritative
  about the repository.
- Anything under `tasks/personal/<owner>/` is authoritative about that person's
  in-flight work, and about nothing else. It is a plan, not a fact.
- Anything under `.hydra-framework.local/` is authoritative about nothing shared.
  It may be wrong, stale, or a thought someone abandoned. Use it during an
  investigation; never cite it as a reason.

Read any owner's records. Edit only your own — `hydra.py task handoff` is how a
record changes hands, and two people editing one record is how they end up
believing different things about the same work.

## Owner Identity

Resolution order: `--owner`, `HYDRA_OWNER`, then `git config user.email`.
Hydra slugifies the full resolved candidate. When the candidate is an email
address, the domain is kept (`dana.reed@example.com` becomes
`dana-reed-example-com`).

If none is set, commands fail with instructions rather than guessing.

`HYDRA_OWNER` exists for CI, containers, and shared machines where git identity
is a service account.

The task-lifecycle workflow owns the full-email and per-owner Personal-state
rules.

## Discovery

| Question | Answer |
| --- | --- |
| What am I working on? | `hydra.py board --owner <you>` |
| What is the team working on? | `hydra.py board` |
| Is this state authoritative? | Which tier is it in |
| What is finished? | It is gone. `git log --diff-filter=D -- <path>` |
| Where do I put a stray thought? | `hydra.py note "Some Title"` for a named note, or pipe stdin into `hydra.py note` for daily scratch |

`route-prompt` also emits counts and pointers on each prompt when something is in
flight. It never emits contents; the board is a command, not a file.

There is deliberately no stored index of active work. The records are the index,
and a second one could disagree with them.

## Frequent Questions

**Why is a finished record deleted rather than archived?**
Git holds every version. Placement rules require querying state Git owns rather
than duplicating it, and an archive directory is exactly that duplicate. Deleting
is also what keeps the tracked set small enough that "active" stays meaningful
with eight engineers.

**How do I find a finished record?**
`git log --diff-filter=D -- .hydra-framework/tasks/personal/<owner>/<file>.md`,
then `git show <commit>^:<path>`.

**Why is personal work tracked at all, if it is scaffolding?**
Because the cost of losing it is real — a dead laptop, or a teammate who goes on
leave mid-migration — and the cost of keeping it is bounded once completion
removes it. The unbounded-archive problem and the backup problem have different
solutions; deleting on completion solves the first without giving up the second.

**Can I keep private state on more than one machine?**
`.hydra-framework.local/` may be a symlink into a synced directory. It is
untracked and therefore unbacked; anything you cannot afford to lose belongs in
the personal or shared tier.

**Where do intake sources go?**
`.hydra-framework.local/intake/`. Only the promotion record is shared, and it
must contain what it needs rather than linking to the private source. See
`intake-lifecycle.md`.

**A migration ledger churns like scaffolding. Why is it shared?**
Its definition of done is a property of the repository, not of a person.

## Validation

`hydra.py validate` fails on:

- a private-tier file tracked in Git
- private-tier content left in the shared tree
- a shared file citing a concrete private file path

and notes, without failing:

- a record whose status is not `active`, `blocked`, or `parked`
- a record not updated in fourteen days

Notes are advisory because a check that blocks work for bookkeeping is a check
people route around.
