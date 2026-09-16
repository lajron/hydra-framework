# Execution Flow

One loop moves a task from an understandable request to verified, reusable
outcomes. It is a model for operating Hydra, not a promise that Hydra starts
work or changes repository state on its own.

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

```mermaid
flowchart TB
  A[Task or prompt arrives] --> B[Understand]
  B --> C[Resolve consequential uncertainty]
  C --> D[Check readiness]
  D --> E[Plan]
  E --> F[Developer approval]
  F --> G[Execute]
  G --> H[Verify]
  H --> I[Promote durable outcome or record follow-up]
  I --> J[Learn]
  H -->|pause or ownership change| K[Checkpoint or handoff]
  K --> D
  L[Configured provider hook:<br/>route prompt or check an event] -. supplies pointers or feedback .-> B
  M[Human-invoked commands:<br/>board, context, task, validation] -. inspect or maintain .-> D
```

Readiness gates entry into execution, and verification brackets execution on
the way to learning. A task record is used only when the work is non-trivial,
interrupted, blocked, handed off, or valuable for team visibility. It keeps
readiness, step state, evidence, and continuation facts available without
becoming a transcript. When responsibility changes, hand off the record; when
the work is complete, preserve its durable outcome and complete the task so Git
history remains the archive.

The [Task Lifecycle](/project-wiki/hydra-framework/working-with-hydra/task-lifecycle.md)
page explains record state and handoff. Provider hook boundaries are covered by
[Provider Adapters](/project-wiki/hydra-framework/extending-hydra/provider-adapters.md).

## Explicit Coordinated Work

When one task needs bounded worker assistance, the caller opts into the local
control plane. The run remains anchored to the existing task record:

1. Start a run with an explicit run ID and owner.
2. Spawn a worker with an explicit worker ID, owner, role, reason, parent, and
   structured task payload. The shared policy limits active workers and depth.
3. Send bounded messages or collect a structured partial or complete result.
4. Review the complete result with an independent reviewer and validate it with
   an independent validator.
5. Transition the worker and then the run explicitly. Handoff and recovery use
   named owners; stale dates never trigger deletion or reaping.

The default adapter only records a request receipt in the private ledger. A
receipt does not mean that a model started, a provider delivered a message, or
the result is complete. See [Execution Stack](/project-wiki/hydra-framework/architecture/execution-stack.md#orchestration-boundary)
for the implemented-versus-conceptual boundary and [Task
Lifecycle](/project-wiki/hydra-framework/working-with-hydra/task-lifecycle.md)
for the durable task record that the run must reference.

## Activation Boundaries

| Boundary | What happens | What does not follow from it |
| --- | --- | --- |
| Human-invoked | A person or agent deliberately runs `board`, context, task-state, or validation commands and acts on their output. | Hydra does not infer that a task should be created, approved, or completed. |
| Provider hook | A configured provider event can route a prompt, attach pointers, check edits, or reduce command output. Codex hook wiring is local runtime integration, not canonical meaning. | Hooks are not available merely because the repository contains Hydra, and they do not do broad reasoning or silently rewrite canonical state. |
| Automatic deterministic behavior | Once a supported command or configured hook runs, its bounded implementation can produce its defined result, such as checking a package gate or removing a completed task record. | This is not an unattended scheduler or a replacement for review, approval, and validation judgment. |

The [Execution Harness](/project-wiki/hydra-framework/architecture/execution-stack.md) supplies the instructions, tools,
environment, state, and feedback for each loop. The governing sequence lives
in the [Task Lifecycle](/project-wiki/hydra-framework/working-with-hydra/task-lifecycle.md)
page; provider hook boundaries are covered by [Provider Adapters](/project-wiki/hydra-framework/extending-hydra/provider-adapters.md).

For a concrete small change from initial request through completion, follow
[First Task Walkthrough](/project-wiki/hydra-framework/working-with-hydra/first-task.md).
