# Task: harden-mixed-hydra-entrypoint-detection

Status: active
Owner: milosdenic-dev-gmail-com
Created: 2026-09-10
Updated: 2026-09-10

## Goal

Prevent takeover scan from classifying mixed AGENTS.md or CLAUDE.md files as fully Hydra-owned when they contain additional repository-local or legacy instructions.

## Confirmed Decisions

- A false Hydra-owned classification is more dangerous than an owner-review result because takeover then recommends `do-not-stage`.
- Preserve recognition of the currently shipped thin `AGENTS.md` and `CLAUDE.md` shapes and the older supported Hydra entrypoint shape.
- Mixed entrypoints containing additional local or legacy instructions must resolve to `needs-owner-decision` with `confirm-owner` staging.

## Approved Plan

- Add negative takeover fixtures for Hydra markers combined with additional local instructions in both root entrypoints.
- Tighten thin-entrypoint recognition without broadening the finite takeover marker list or making the scan mutating.
- Preserve positive coverage for current and legacy Hydra-owned shapes, then update affected guidance and knowledge fingerprints if behavior changes.

## Current Stage

Ready for implementation.

## Readiness

Status: ready

- Branch or workspace assumptions: begin from the commit containing the Hydra reproducibility repairs; preserve unrelated working-tree changes.
- Relevant canonical docs: `.hydra-framework/capabilities/skills/framework-takeover/skill.md`, `.hydra-framework/capabilities/workflows/material-migration.md`, and `.hydra-framework/repo/knowledge/silent-failure-modes.md`.
- Required dependencies, services, generated artifacts, or private local requirements: repository Python environment only; regenerate adapters and the object registry only if their canonical sources change.
- Blockers and assumptions: none; owner review is the conservative fallback when an entrypoint is not provably thin.
- Expected validation command or evidence: focused takeover unit tests, source takeover JSON classification, `hydra.py validate`, and `hydra.py selftest`.

## Step State

- Active step: await implementation of stricter thin-entrypoint recognition.
- Next step: add mixed-entrypoint negative tests before changing the classifier.
- Completed steps: review identified the false-positive boundary and recorded the required classifications and compatibility constraints.
- Superseded or skipped steps: none

## Changed Files

- None yet.

## Validation

- Review evidence: current recognition is based on marker presence, while classification immediately maps a match to `hydra-owned` and `do-not-stage`.

## Blockers

- None.

## Continuation Notes

What another model or developer needs to continue safely.

- Running state: none
- Resume check: run `python3 .hydra-framework/scripts/hydra.py board`; this task should appear active for `milosdenic-dev-gmail-com`.
