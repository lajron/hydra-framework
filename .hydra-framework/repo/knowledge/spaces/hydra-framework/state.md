---
hydra_id: "hydra://knowledge-slice/hydra-framework/state"
uid: "d67d16a2-0504-44a5-a1f9-5c6d435c355a"
schema_version: "3"
kind: "knowledge-slice"
title: "Hydra Framework Itself State"
status: "active"
scope: "base-seed"
owners:
  team: "hydra"
relations:
  - type: "relates-to"
    target: "hydra://knowledge-space/hydra-framework"
provenance:
  sources:
    - ".hydra-framework/core/placement-rules.md"
    - ".hydra-framework/engine/src/hydra_engine/identity/path_owners.py"
    - ".hydra-framework/scripts/hydra.py"
---

# Hydra Framework Itself State

Status: active. Updated: 2026-08-30.

## Current Focus

Build status lives in `units/build-status.md`, not here. No separate framework
build focus is recorded in this pointer.

## Last Handoff

Revalidated the seven units reported by `hydra.py knowledge stale` after the
legacy cleanup, corrected build-status counts, and aligned the adoption unit
with its current validation procedure. Watch: routing v2 remains.
