# Lifecycle

Hydra's lifecycle is the default Agent Loop inside the agentic execution stack.

The Execution Harness supports this loop through instructions, tools, environment, state, and feedback. It selects context, checks readiness, preserves task state, handles blockers, and records validation evidence without storing raw conversation memory.

The normal flow is:

understand -> resolve uncertainty -> check readiness -> plan -> developer approval -> execute -> verify -> learn

## Before Non-Trivial Modification

1. Inspect cheap repository context.
2. Identify branch or worktree risk when Git exists.
3. Check active task state.
4. Record readiness for persisted non-trivial tasks.
5. Ask the first consequential blocking question if needed.
6. Produce a scoped plan for approval unless the developer has already asked for direct execution.

## Persisted Task State

When the persistence triggers apply, create an owner-scoped record with
`hydra.py task start <name> --goal "..."`, unless the board already contains a
record for the same objective. The owner is resolved in this order:
`--owner`, `HYDRA_OWNER`, then `git config user.email`, with the resolved value
slugified in full. If none is available, task commands fail instead of placing
work under a guessed shared owner.

Task records are tracked under
`.hydra-framework/tasks/personal/<owner>/`; checkpoints are beside them under
`<owner>/checkpoints/`. The task lifecycle workflow owns the exact required
fields. The board is a view computed from the records, and a stale date is an
advisory prompt to inspect or update work, not permission to transfer or reap
it.

Only the current owner may edit a task by default. Use
`task handoff <record> --to <owner>` for an explicit transfer. The handoff
writes the destination and its checkpoints before removing the source, so a
rerun can finish an interrupted move; a different destination record is a
collision and is refused. This is an ownership boundary, not a generic worker
scheduler.

## Checkpoints

Create or update a checkpoint when work pauses, context is low, a blocker appears, a model handoff is likely, or another developer needs to continue.

A checkpoint stores facts, not a conversation transcript:

- task goal
- confirmed decisions
- approved plan
- current stage
- completed work
- changed files
- validation performed
- remaining work
- blockers
- useful commands or references

The checkpoint command also updates the task's `Updated:` field. Before
completion, task state must be recoverable from Git: completion refuses an
untracked or unstaged task record or checkpoint. That refusal protects the last
known continuation state from being deleted before Git can recover it.

## Completion

When work finishes, decide what should persist:

- canonical knowledge
- reusable procedures
- follow-up tasks
- system improvement candidates
- archived checkpoint

Then promote the durable outcome and run
`hydra.py task complete <record> --outcome <path|none>`. The outcome must be an
existing repository-relative file outside task scaffolding and private staging,
or the explicit value `none`. Completion removes the task and checkpoints and
Git history remains the archive. A finished record can be recovered with
`git log --diff-filter=D -- <path>`.
