# Architecture

Hydra's architecture has two useful views of the same runtime:

- [Execution stack](/project-wiki/hydra-framework/architecture/execution-stack.md) explains the responsibilities from
  coordination through the model.
- [Execution flow](/project-wiki/hydra-framework/architecture/execution-flow.md) follows one work cycle from
  understanding and readiness through verification and learning.
- [Explicit orchestration](/project-wiki/hydra-framework/architecture/execution-stack.md#orchestration-boundary)
  describes the bounded run and worker control plane when a task needs coordinated work.
- [Object and context model](/project-wiki/hydra-framework/architecture/object-context-model.md) explains durable object
  identity, derived lookups, and task-context selection.
- [Context retrieval](/project-wiki/hydra-framework/architecture/context-retrieval.md) explains the knowledge-search,
  route-prompt, and compile-context retrieval mechanics.
- [Command-output reducers](/project-wiki/hydra-framework/architecture/command-output-reducers.md) explains how a
  provider hook reduces Bash tool output before the model sees it.
- [Telemetry pipeline](/project-wiki/hydra-framework/architecture/telemetry.md) explains how events are captured,
  classified, redacted, and drained into governed evidence.

The stack is a conceptual architecture frame, not a required filesystem
layout. Hydra keeps a responsibility-first repository structure while the
Execution Harness brings instructions, tools, environment, state, and feedback
together for reliable model work. The [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence)
records the exact owners for this architecture.

For the governing work sequence, read [Execution Flow](/project-wiki/hydra-framework/architecture/execution-flow.md).
For coordinated work, read the [Orchestration Boundary](/project-wiki/hydra-framework/architecture/execution-stack.md#orchestration-boundary)
and its [command reference](/project-wiki/hydra-framework/reference/command-surface.md#orchestration).
