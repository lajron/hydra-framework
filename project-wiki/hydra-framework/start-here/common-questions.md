# FAQ

Audience: A reader with one focused Hydra question

Reader goal: Get a short, trustworthy answer and reach the page that owns the detail

Page type: reference

Status: FAQ / question index

Start here if you have a specific question rather than time to read in
reading order. Each answer is short and links to the page that owns the full
explanation; treat that linked page, not this one, as the source of exact
rules.

## What Is This

**What is Hydra?**
Repository-contained, provider-neutral AI-work infrastructure for shared
context, reusable agent capabilities, and in-flight work. See the root
[README](/README.md) for the public overview and
[Hydra Framework Wiki](/project-wiki/hydra-framework/hydra-framework.md) for detailed routes.

**Why not just write good README files?**
Because the thing that goes missing across sessions isn't prose, it's state:
what's currently in flight, who owns it, what was decided and why, what
passed validation. READMEs describe a system; Hydra also tracks the system's
live, resumable work. See [Concepts](/project-wiki/hydra-framework/concepts/concepts.md).

**What's the one-sentence pitch?**
Hydra gives a repository a provider-neutral, governed working layer for
AI-assisted engineering, so shared context, reusable capabilities, and
in-flight work live with the code instead of inside one chat or provider
surface. See the [Public Positioning Brief](/project-wiki/hydra-framework/reference/public-positioning.md).

## Getting Started Today

**I just cloned this repository. What do I run?**
Run the fresh-clone sequence from the root [README.md](/README.md):
`init-local`, then `export-adapters`, then `doctor`. Generated provider
adapters are ignored by Git, so exporting them is required before a provider
session or `doctor` check. `install-hooks` is optional.

**I'm new to the team. Where do I start reading?**
[Working With Hydra](/project-wiki/hydra-framework/working-with-hydra/working-with-hydra.md) is the practical
checklist for starting work today; it comes before any policy deep-dive.

**I'm an AI agent picking up work in this repo. Where do I start?**
[Working With Hydra](/project-wiki/hydra-framework/working-with-hydra/working-with-hydra.md), then
`hydra.py board` to see what's in flight before starting non-trivial work.

**How do I see what's currently being worked on?**
`python3 .hydra-framework/scripts/hydra.py board`, computed live from task
records each time it runs. See [Task Lifecycle](/project-wiki/hydra-framework/working-with-hydra/task-lifecycle.md).

**I'm setting Hydra up in a different, new repository. Where does that start?**
That's a different path from a normal clone; see the
[Seed And Adopt Hydra](/project-wiki/hydra-framework/start-here/adopt-a-repository.md) route. If the goal is instead to
drain existing material, use [Migration](/project-wiki/hydra-framework/extending-hydra/migration.md).

## How It's Structured

**What's the difference between `.hydra-framework/`, `.hydra-framework.local/`, and `project-wiki/`?**
`.hydra-framework/` is canonical shared state for AI and automation, tracked
and review-gated. `.hydra-framework.local/` is your private, untracked,
machine-local thinking and scratch. `project-wiki/` (this space) is the
human-facing, Obsidian-friendly explanation layer. See
[State Tiers](/project-wiki/hydra-framework/concepts/state-tiers.md)
and the [Private Workspace](/project-wiki/hydra-framework/working-with-hydra/private-workspace.md).

**What are the shared, personal, and private state tiers?**
Shared describes the repository and is tracked and review-gated. Personal is
one owner's structured in-flight work, tracked so someone can inherit it.
Private is one person's raw thinking and scratch, never tracked. See
[State Tiers](/project-wiki/hydra-framework/concepts/state-tiers.md).

**What's the difference between a rule, a knowledge file, a runbook, and a postmortem?**
A rule is a current, forward-looking constraint in its canonical owner. A flat
knowledge file is descriptive, how something currently works, kept true by
editing in place. A runbook is prescriptive, the concrete steps for a recurring
operational situation. A postmortem is backward-looking, what happened in one
incident and what changed as a result. See [State Tiers](/project-wiki/hydra-framework/concepts/state-tiers.md)
and [Documentation Authoring](/project-wiki/hydra-framework/reference/documentation-authoring.md).

**What are `.claude/`, `.codex/`, and `.agents/` for?**
Provider adapters: generated or hand-maintained surfaces that expose
canonical Hydra capabilities to a specific runtime. They're not an
independent source of truth. See [Provider Adapters](/project-wiki/hydra-framework/extending-hydra/provider-adapters.md).

**What runs the commands, `hydra.py` or the engine?**
`scripts/hydra.py` is the stable entry point; behavior itself lives in the
`hydra_engine` package it calls into. See [Engine](/project-wiki/hydra-framework/architecture/engine.md).

**What are skills, agents, and workflows in this repo?**
Reusable capability definitions, canonical under
`.hydra-framework/capabilities/`, exported into provider adapters. See
[Capabilities](/project-wiki/hydra-framework/extending-hydra/capabilities.md).

## Finding context and capabilities

**How do I find the right context without reading the whole repository?**
Use `knowledge-search "<query>"` for ranked, cited snippets, `route-prompt
--prompt "<prompt>"` for small route pointers, and `compile-context --task
"<task>" --budget <tokens>` for a bounded reading packet. Add `--json` to
`route-prompt` when you need scores, ambiguity, or resolution diagnostics. See
[Context Retrieval](/project-wiki/hydra-framework/architecture/context-retrieval.md).

**What is in a context packet?**
It records the selected context, required material, omitted candidates, token
budget, provenance and freshness information, and validation reminders. The
packet is a bounded view of canonical files, not a new source of truth. See
[Object And Context Model](/project-wiki/hydra-framework/architecture/object-context-model.md).

**How do capability profiles affect what I use?**
Profiles narrow which canonical skills are materialized as provider adapters;
canonical agents are not filtered by a profile. Inspect with `profile list` or
`profile show`, preview with `export-adapters --profile <name> --dry-run`, and
read [Capabilities](/project-wiki/hydra-framework/extending-hydra/capabilities.md)
before selecting a profile.

## Boundaries and evidence

**Does the Coordination Graph mean Hydra runs a generic multi-agent scheduler?**
No. The execution stack is a responsibility map. Read [Execution
Stack](/project-wiki/hydra-framework/architecture/execution-stack.md) for the
currently implemented controls and the remaining conceptual pieces. Provider
adapters expose canonical capabilities to a runtime; they are not, by
themselves, a worker scheduler or a provider SDK. See [Provider
Adapters](/project-wiki/hydra-framework/extending-hydra/provider-adapters.md).

**How do I trace a claim, object, or path to its owner?**
Use `ref check` to validate object IDs and references, `ref resolve
hydra://...` to inspect one object's identity and provenance, and `explain-path
<path> --json` when the ownership of a file is unclear. `ref rdeps` and `ref
impact` answer graph questions only when the derived query store is fresh. See
[Object And Context Model](/project-wiki/hydra-framework/architecture/object-context-model.md),
[Reference](/project-wiki/hydra-framework/reference/reference.md), and
[Operations](/project-wiki/hydra-framework/operations/operations.md).

**Does `wiki audit` prove that the documentation is complete?**
No. It checks the declared page sources, dates, and recorded digests. It does
not prove that every source was declared or that the prose is semantically
correct. `wiki fingerprint` records source digests only after the page has been
re-read against its sources; `validate-wiki` separately checks navigation
links. See [Operations](/project-wiki/hydra-framework/operations/operations.md).

**How do I evolve a Hydra copy without silently changing the seed?**
Use [Evolution](/project-wiki/hydra-framework/evolution/evolution.md) to
compare the copy with its base, record why a difference exists, and decide
whether it stays local or flows back. Adoption, migration, and seed
reconciliation are separate routes, so start from the source type you actually
have.

## Day To Day

**When does work need a task record?**
For non-trivial work: anything spanning sessions, with real blockers, needing
handoff, or that the team should see in flight. Not for small, one-shot
edits. See [Task Lifecycle](/project-wiki/hydra-framework/working-with-hydra/task-lifecycle.md).

**How do I start, checkpoint, hand off, or complete a task?**
`hydra.py task start`, `task checkpoint`, `task handoff --to <owner>`, and
`task complete --outcome <path|none>`. Completion deletes the record; Git
history is the archive. See
[Task Lifecycle](/project-wiki/hydra-framework/working-with-hydra/task-lifecycle.md#useful-commands).

**Someone on the team went quiet or left. What happens to their task record?**
Nothing automatic. A record whose `Updated:` date is older than 14 days is
flagged as possibly stale, which is a prompt to check, not a verdict.
Confirm the owner is actually gone outside Hydra, then use `task handoff
--force` to take the work over or `task complete` to close it out. See
[Task Lifecycle](/project-wiki/hydra-framework/working-with-hydra/task-lifecycle.md#the-lifecycle).

**Who reviews a change to shared Hydra state?**
Every Hydra object already declares an `owners:` field; that's the
review-routing signal. The [Validation](/project-wiki/hydra-framework/operations/validation.md)
page and [Source Map](/project-wiki/hydra-framework/reference/source-map.md)
describe the review route.

**How do I propose a change to the framework itself, versus just editing it?**
A small, mechanical fix (a broken link, a typo, a stale citation) is a direct
edit. A change to architecture, behavior, or convention needs explicit review
and a current canonical owner; Git preserves the rationale. See the
[Extending Hydra](/project-wiki/hydra-framework/extending-hydra/extending-hydra.md)
route and [Source Map](/project-wiki/hydra-framework/reference/source-map.md).

**How do I validate my changes before review?**
`hydra.py validate-wiki` for wiki-only edits; `hydra.py validate` for
anything under `.hydra-framework/`. See [Validation](/project-wiki/hydra-framework/operations/validation.md).

## Still Stuck

Check the [Glossary](/project-wiki/hydra-framework/reference/glossary.md) for terminology, the
[Source Map](/project-wiki/hydra-framework/reference/source-map.md) for where a specific claim's canonical owner
lives, including unresolved-question evidence. If none of those cover it, the question is
a real gap: record it with the appropriate owner rather than guessing an answer
into a wiki page.
