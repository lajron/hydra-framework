---
hydra_id: "hydra://knowledge-unit/hydra-framework/adopt-into-repo"
uid: "24061c90-1f2c-496b-9bbf-6b7a8ddb1426"
schema_version: "3"
kind: "knowledge-unit"
unit_kind: "answer"
title: "Adopting Hydra Into A Repository"
status: "active"
scope: "base-seed"
owners:
  team: "hydra"
relations:
  - type: "relates-to"
    target: "hydra://knowledge-space/hydra-framework"
  - type: "relates-to"
    target: "hydra://capability/skill/adoption"
provenance:
  sources:
    - ".hydra-framework/capabilities/skills/adoption/skill.md"
    - ".hydra-framework/repo/knowledge/seed-reconciliation.md"
    - ".hydra-framework/engine/src/hydra_engine/installation/adopt.py"
    - ".hydra-framework/engine/src/hydra_engine/installation/host_detection.py"
  source_digests:
    - source: ".hydra-framework/capabilities/skills/adoption/skill.md"
      digest: "sha256:3d2070e6030f1f86ef902a3c8532b1fbaa39b27504acc2990966d382231f2187"
    - source: ".hydra-framework/repo/knowledge/seed-reconciliation.md"
      digest: "sha256:fd9145bb356e8733c62ecfcbf55c418add75794eb2f65768411bf849d05958b6"
    - source: ".hydra-framework/engine/src/hydra_engine/installation/adopt.py"
      digest: "sha256:068ddc3982002a669850da2706dd2e23f3dbb256d142a46cc56eba585600cd13"
    - source: ".hydra-framework/engine/src/hydra_engine/installation/host_detection.py"
      digest: "sha256:add0f62b9f1a741b2160c645dca4b4b280290ee209305ffae2826a5e5f32578f"
question: "What confirms Hydra was correctly wired into a freshly copied repository?"
group: "adopt-into-repo"
certainty: "confirmed"
checked_on: "2026-08-30"
reads:
  - ".hydra-framework/capabilities/skills/adoption/skill.md"
  - ".hydra-framework/engine/src/hydra_engine/installation/adopt.py"
  - ".hydra-framework/engine/src/hydra_engine/installation/host_detection.py"
see_also:
  - "hydra://knowledge-unit/hydra-framework/reconcile-with-base"
verify:
  - "python3 .hydra-framework/scripts/hydra.py adopt"
---

# Adopting Hydra Into A Repository

## Answer

Run `hydra.py adopt` (`--record` to stamp lineage) once `.hydra-framework/`
has been copied in. `installation/host_detection.py` detects the host stack;
`installation/adopt.py` reports what integration still needs. Success means
`adopt` reports no missing required paths, lineage is recorded in
`manifest.yaml`, provider surfaces in use are generated, and both `doctor` and
`selftest` pass. The host repository's existing docs and CI stay in place;
moving or replacing them is a separate migration task.

## Do Not Read By Default

The host repository's full source tree. Adoption does not require mapping
it.
