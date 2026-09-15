# Working With Hydra

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

Status: operating guide

Start with the change in front of you. For a small, self-contained change, keep
the work lightweight. For non-trivial work, run `board` first and continue an
existing task record when it covers the objective. If no record covers it,
create an owner-scoped record, a task file in your own owner directory. Then
read only the canonical sources, the version-controlled files that own the
relevant facts, keep unfinished thinking in the [private workspace](/project-wiki/hydra-framework/working-with-hydra/private-workspace.md), and validate before handoff.

## A Concrete Situation

You are asked to update several files and another person may need to continue.
Run:

```bash
python3 .hydra-framework/scripts/hydra.py board
```

Read the matching task record if one exists. Otherwise start a task record. If
the request is a small, self-contained change, keep it lightweight and validate
what changed. Next, use [Choose The Work Level](#choose-the-work-level) to
select the path that fits the change.

## Choose The Work Level

For a narrow question, one-file inspection, tiny obvious edit, or direct
command, keep the work lightweight and validate what changed. Do not create a
formal task for every request. This follows the task lifecycle's persistence
triggers in the canonical workflow.

For multi-file work, a framework change, a blocker, a handoff, or work that
would be costly to reconstruct, use the existing task record when one already
covers the objective. Check the board first, and edit only your own record.
Read [Task Lifecycle](/project-wiki/hydra-framework/working-with-hydra/task-lifecycle.md) for the persisted-work route, or use
the [First Task Walkthrough](/project-wiki/hydra-framework/working-with-hydra/first-task.md) for one realistic small change.

## Find The Context

Start with the repository entry points and current work:

```bash
python3 .hydra-framework/scripts/hydra.py board
python3 .hydra-framework/scripts/hydra.py knowledge-search "<task question>"
python3 .hydra-framework/scripts/hydra.py compile-context --task "<task>"
```

Read the relevant canonical owner, not an entire knowledge tree. Use matching
skills, workflows, agents, and tool capabilities when they apply. Git, code,
CI, package managers, and external systems remain the source of truth when
they already own the state. See the [New Contributor](/project-wiki/hydra-framework/start-here/new-contributor.md)
route for the repository and agent entry points.

## Work Safely

Keep unfinished thinking, source staging, machine details, and local
configuration in the [private workspace](/project-wiki/hydra-framework/working-with-hydra/private-workspace.md). If another
person must inherit the work, record the resumable coordination in the
personal task tier instead. Shared files must never cite a private path.
The [State Tiers](/project-wiki/hydra-framework/concepts/state-tiers.md) guide
explains the complete boundary contract.

When changing a wiki page, keep it concise and link durable claims to their
canonical owners. Do not copy live source-of-truth state into the wiki. Keep
unrelated worktree changes intact.

## Validate Before Handoff

Update the task's step state, changed paths, and validation evidence when
persisted work makes progress. Before handoff, run the validation required by
the changed surface. Wiki changes use:

```bash
python3 .hydra-framework/scripts/hydra.py validate-wiki
```

Changes under `.hydra-framework/` also use:

```bash
python3 .hydra-framework/scripts/hydra.py validate
```

Record the exact result in the task state when a task record exists. The
[Task Lifecycle](/project-wiki/hydra-framework/working-with-hydra/task-lifecycle.md)
defines continuation and completion; the [Documentation Authoring](/project-wiki/hydra-framework/reference/documentation-authoring.md)
page defines the wiki's citation and validation boundary.
