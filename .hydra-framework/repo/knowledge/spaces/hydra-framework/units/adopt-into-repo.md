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
    - ".hydra-framework/engine/src/hydra_engine/installation/seed_copy.py"
    - ".hydra-framework/engine/src/hydra_engine/installation/adopt.py"
    - ".hydra-framework/engine/src/hydra_engine/installation/host_detection.py"
  source_digests:
    - source: .hydra-framework/capabilities/skills/adoption/skill.md
      digest: sha256:f6cea6f6b71f5c822b753b5cf62f9e2ed930610057e6029921772fddfc09b682
    - source: .hydra-framework/repo/knowledge/seed-reconciliation.md
      digest: sha256:1f1f42930cb7d7e8df659ef42ac4a2a84ae6f1b21ea33621c285a834026c937d
    - source: .hydra-framework/engine/src/hydra_engine/installation/seed_copy.py
      digest: sha256:116cb424f9b39a04bd27cbf84d01a2b7bc3cdc1b9698f7b6c0abf4cdd3ae396d
    - source: .hydra-framework/engine/src/hydra_engine/installation/adopt.py
      digest: sha256:558fce63bfdbc610fedbf989f3d4b74819ecab89a8039c084638fe2198010f10
    - source: .hydra-framework/engine/src/hydra_engine/installation/host_detection.py
      digest: sha256:add0f62b9f1a741b2160c645dca4b4b280290ee209305ffae2826a5e5f32578f
question: "What confirms Hydra was correctly wired into a freshly copied repository?"
group: "adopt-into-repo"
certainty: "confirmed"
checked_on: "2026-09-10"
reads:
  - ".hydra-framework/capabilities/skills/adoption/skill.md"
  - ".hydra-framework/engine/src/hydra_engine/installation/seed_copy.py"
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
`adopt` reports no missing required paths, including the portable Claude rule
and settings plus Codex hooks; lineage is recorded in `manifest.yaml`; provider
surfaces in use are generated; and both `doctor` and `selftest` pass. The host
repository creates its own reviewer mapping because `.github/CODEOWNERS` is not
portable. Existing docs and CI stay in place; moving or replacing them is a
separate migration task.

## Do Not Read By Default

The host repository's full source tree. Adoption does not require mapping
it.
