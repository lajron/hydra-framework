---
title: Repository Procedures
status: active
owners:
  team: hydra
certainty: inferred
provenance:
  sources:
    - AI_SYSTEM.md
    - .hydra-framework/README.md
    - .hydra-framework/capabilities/workflows/material-migration.md
---

# Repository Procedures

Use this file for repeatable commands and workflows that have been validated in this repository.

## Integrating Hydra Into An Existing Repository

Use this procedure when applying the Hydra seed to a real project repository.

1. Copy or install the Hydra seed into the target repository, preserving `.hydra-framework/`, root provider entry files such as `AI_SYSTEM.md` and `AGENTS.md`, and any required provider adapter directories.
2. Run `python3 .hydra-framework/scripts/hydra.py doctor` from the target repository root.
3. Run `python3 .hydra-framework/scripts/hydra.py validate`.
4. Run `python3 .hydra-framework/scripts/hydra.py export-adapters` when provider skill wrappers need to be generated or refreshed.
5. Create the human wiki surface for the project with `python3 .hydra-framework/scripts/hydra.py wiki scaffold <project-name>` when it does not already exist.
6. Treat existing project docs, README files, diagrams, issue records, and code as source material initially. Do not rewrite or delete them as part of installing Hydra.
7. Migrate documentation one area at a time. For each module, feature, or system, create or update a human page under `project-wiki/<project-name>/` and link it to verified code and existing docs.
8. Create Hydra knowledge spaces only for complex or repeatedly-used areas where scoped AI operational knowledge improves retrieval, handoff, validation, or repeated execution. Do not create one space per folder by default.
9. Keep source-of-truth state with its owner: code in code, live workflow state in issue trackers or CI, package state in package managers, durable rules in their canonical Hydra `core/` or `repo/knowledge/` owner, and human explanations in the wiki.
10. Record migration progress in task state when the migration spans sessions or affects team-visible docs.

To clear a source area rather than migrate opportunistically, follow `.hydra-framework/capabilities/workflows/material-migration.md`. It bounds the effort, moves originals to private staging first, and tracks completion in a ledger.

For a newly adopted project, first name the project wiki area and establish
source links. Migrate useful scattered documentation one area at a time into
human wiki pages or Hydra knowledge spaces according to reuse and complexity.

## Propose A Hydra Framework Change

Use this procedure for any change to `.hydra-framework/` shared state:
`repo/knowledge/`, `capabilities/`, `core/`, or engine code. It picks the
right weight for the change rather than defaulting every edit to the
heaviest path.

1. Capture the idea privately first. `hydra.py note "<title>"` for a raw
   thought; a reflection packet (the `session-reflection` skill) once it
   survives that stage as a sanitized, reduced observation. Do not open a
   pull request from a raw impression.
2. Decide the weight:
   - A small, mechanical fix (a broken link, a stale path citation, a typo, a
     missing envelope field) is a direct edit.
   - A change to architecture, framework behavior, a repository convention,
     or anything with real alternatives worth weighing is still a direct
     edit to its canonical owner (`core/`, `repo/knowledge/`,
     `capabilities/`, or code) -- there is no separate step for recording
     the choice. Weigh the alternatives in the PR description; Git history is the
     rationale archive, not a standing policy log.
3. Find the reviewer. `repo/knowledge/review-routing.md` — the changed
   object's own `owners:` field is the signal; this repository's mapping to
   real reviewers lives in `.github/CODEOWNERS`.
4. Land the change through the normal Git review path for this repository.
5. Run `python3 .hydra-framework/scripts/hydra.py validate` before
   considering the change done. It is required, not optional, the same way
   it is required for every other slice of shared-state work.
