---
hydra_id: "hydra://knowledge-slice/hydra-framework/definition-of-done"
uid: "5dce06f1-1d9f-4911-ba35-cfbad747da1f"
schema_version: "3"
kind: "knowledge-slice"
title: "Hydra Framework Definition Of Done"
status: "active"
scope: "base-seed"
owners:
  team: "hydra"
relations:
  - type: "relates-to"
    target: "hydra://knowledge-space/hydra-framework"
provenance:
  sources: []
---

# Definition Of Done

Status: active
Updated: 2026-08-19

When a change to Hydra's own machinery is complete.

## Every Change

- [ ] Canonical source edited, not a generated wrapper.
- [ ] `python3 .hydra-framework/scripts/hydra.py selftest` passes.
- [ ] `python3 .hydra-framework/scripts/hydra.py export-adapters --check` is clean.
- [ ] `python3 .hydra-framework/scripts/hydra.py doctor` passes.
- [ ] No secrets, machine paths, or personal preferences in shared state.

## Adding Or Changing A Module

- [ ] `metadata.yaml` has every key `validate_module_metadata` requires.
- [ ] Any new capability class or effort budget has an entry in every provider capability map.
- [ ] Wrappers regenerated and committed alongside the canonical change.
- [ ] `kind: command` set if only a human should trigger it.

## Changing Engine Code Or The CLI Shim

- [ ] New behavior has a mirrored unit test under `.hydra-framework/engine/tests/unit/`, plus a contract golden when CLI output changes.
- [ ] New commands register through the appropriate `hydra_engine.commands` module, or document why they must stay in the shim.
- [ ] Failure modes are loud. Silent skips are only acceptable for advisory surfaces, and then they print to stderr.
- [ ] The overview's command table is updated.

## Changing A Contract

- [ ] Prose source, executable definition, and template all updated together.
- [ ] A validation check enforces the agreement, or the gap is recorded in `problems.md`.

## Changing Provider Behavior

- [ ] Claimed runtime behavior verified against the provider's own documentation.
- [ ] `sources.md` records what was checked and when.
- [ ] Capability maps carry a fresh `verified` date and honest `certainty`.

## Documentation

- [ ] `state.md` handoff updated.
- [ ] New unresolved concerns recorded in `problems.md` with evidence.
- [ ] `python3 .hydra-framework/scripts/hydra.py validate-package-docs --path .hydra-framework/repo/knowledge/spaces/hydra-framework` passes.

## Explicitly Not Required

- Wiki pages for every change. `project-wiki/` covers teammate-facing explanation, updated when the explanation actually changes.
- Task records for trivial one-shot edits.
- Diagram regeneration when no diagram changed.
