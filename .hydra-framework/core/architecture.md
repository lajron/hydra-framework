# Architecture

## Agentic Execution Stack

Hydra uses this conceptual execution stack:

`Coordination Graph -> Agent Loop -> Execution Harness -> Context Pack -> Prompt -> Model`

- Coordination Graph: coordinates tasks, agents, dependencies, handoffs, and recovery across many loops.
- Agent Loop: drives one agent through understand, readiness, plan, act, verify, and learn.
- Execution Harness: supplies instructions, tools, environment, state, and feedback for reliable model work.
- Context Pack: selects the canonical state, task facts, constraints, and assumptions the model should see.
- Prompt: carries the immediate instruction assembled from the selected context.
- Model: provides the provider-neutral reasoning and execution runtime.

The stack explains runtime responsibilities. It does not require the filesystem to be organized by these layers.

## Execution Harness Subsystems

Hydra treats the Execution Harness as five cooperating subsystems:

- Instructions: short entry guidance, durable rules, workflows, skills, and links to deeper canonical docs.
- Tools: available capabilities, command access, validation helpers, adapters, and least-privilege execution boundaries.
- Environment: repository setup, dependency and service expectations, generated artifacts, local/private requirements, and reproducible runtime assumptions.
- State: task records, checkpoints, canonical knowledge, readiness, blockers, assumptions, and continuation notes.
- Feedback: validation commands, test evidence, review signals, observability, failure records, and self-evolution evidence.


## Recommended Structure

The seed uses responsibility as the primary physical organization axis. Each top-level directory owns one kind of concern: core rules, repository knowledge, task state, agents, skills, tools, surfaces, adapters, cognition, validation, scripts, or evolution.

Execution layer is represented through metadata, placement rules, and internal substructure rather than by duplicating every concern under `common/`, `repo/`, `provider/`, `private/`, and `runtime/`.

This keeps the folder tree navigable while still supporting:

- common seed behavior
- repository-specific adaptation
- technology-specific extensions
- provider-specific adapters
- shared Git-tracked state
- private developer and machine state
- generated runtime artifacts

## Intake as a Core Subsystem

Hydra treats intake as a first-class responsibility, separate from canonical repository knowledge.

The framework needs a place to receive messy source material, extracted artifacts, and staged interpretations before any of them become trusted memory. This avoids forcing unverified material into `repo/knowledge/`. The placement rules keep those early stages private, in `.hydra-framework.local/intake/`; only the promotion record is shared.

The intake lifecycle is:

`source -> raw -> extracted -> triage -> promoted -> canonical-or-archived`

The important boundary is promotion. A triage note may be useful, but it is not canonical until a model or developer deliberately promotes verified durable meaning into the correct owner.

## Canonical, Derived, Temporary, Private

- Canonical: human-readable, reviewed, durable facts and rules.
- Derived: generated indexes, summaries, graphs, or views that can be rebuilt.
- Temporary: current-session state that should not become memory.
- Private: personal, machine-specific, credential-bearing, or experimental state outside Git.

Important knowledge must not exist only in derived cognition structures.

## Alternative A: Execution-Layer First

An execution-layer-first tree would group files under `core/`, `repo/`, `provider/`, `private/`, and `runtime/`, then repeat responsibilities inside each area.

Tradeoff: it makes override boundaries very visible, but it scatters related concepts across multiple places and makes discovery harder for humans and models.

## Alternative B: Package-First Modules

A package-first tree would make every agent, skill, workflow, provider adapter, and knowledge pack a self-contained package with similar internal files.

Tradeoff: it is portable and generator-friendly, but it risks boilerplate and duplicated canonical knowledge unless ownership rules are strict.

## Chosen Bias

Use responsibility-first structure now. Allow package-like repeated module shapes where they are useful for agents, skills, workflows, integrations, and technology packs. Use deep structures only when semantic boundaries justify them.

Use repeated local shapes for knowledge spaces when the subject has durable internal structure. A repository service, app, bounded context, domain, product area, or automation area may own local state, questions, risks, procedures, sources, and validation notes without replacing the global canonical knowledge layer.
