# Repository Layer

This area contains repository-specific knowledge that the AI framework can rely on.

It should evolve independently inside this repository without corrupting the reusable seed architecture.

Use:

- `knowledge/` for verified facts, architecture, conventions, procedures, and domain understanding.
- `telemetry/` for the governed telemetry evidence package queue -- bounded, author-attributed evidence derived from the private telemetry corpus. See `telemetry/README.md`.

Use `.hydra-framework/intake/` before `repo/knowledge/` when material needs extraction, triage, source review, or promotion decisions.
Use `.hydra-framework.local/notes/` for lightweight unverified observations.
There is no shared `repo/pending/`; only governed shared review queues with
attribution and terminal outcomes are permitted.

Use a knowledge space under `knowledge/spaces/`, listed in `knowledge/spaces.yaml`, when a repository area needs local state, questions, risks, sources, and procedures while still following global placement rules. See `core/knowledge-architecture.md`.
