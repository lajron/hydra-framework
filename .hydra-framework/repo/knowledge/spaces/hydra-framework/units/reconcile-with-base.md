---
hydra_id: "hydra://knowledge-unit/hydra-framework/reconcile-with-base"
uid: "d6ac00af-f26f-4a46-b189-284c6e91a910"
schema_version: "3"
kind: "knowledge-unit"
unit_kind: "answer"
title: "Reconciling A Copy Against Its Base Seed"
status: "active"
scope: "base-seed"
owners:
  team: "hydra"
relations:
  - type: "relates-to"
    target: "hydra://knowledge-space/hydra-framework"
  - type: "relates-to"
    target: "hydra://capability/skill/seed-reconciliation"
provenance:
  sources:
    - ".hydra-framework/capabilities/skills/seed-reconciliation/skill.md"
    - ".hydra-framework/repo/knowledge/seed-reconciliation.md"
    - ".hydra-framework/engine/src/hydra_engine/commands/seed.py"
    - ".hydra-framework/engine/src/hydra_engine/seed/fingerprints.py"
  source_digests:
    - source: ".hydra-framework/capabilities/skills/seed-reconciliation/skill.md"
      digest: "sha256:ac1e1db96a1fe2b2dcd5ed2cbee8317a7d204966e7b2822f92e2591d8f641f92"
    - source: ".hydra-framework/repo/knowledge/seed-reconciliation.md"
      digest: "sha256:fd9145bb356e8733c62ecfcbf55c418add75794eb2f65768411bf849d05958b6"
    - source: ".hydra-framework/engine/src/hydra_engine/commands/seed.py"
      digest: "sha256:44273e680807679a3d1809917cd79252c0b73f3002918893dabde8b511870325"
    - source: ".hydra-framework/engine/src/hydra_engine/seed/fingerprints.py"
      digest: "sha256:c1f85e290f3f7a74eed545f816000476466538941ee0be673f6867c217faf2bf"
question: "How is a diverged Hydra copy compared against its base seed?"
group: "reconcile-with-base"
certainty: "confirmed"
checked_on: "2026-08-30"
reads:
  - ".hydra-framework/capabilities/skills/seed-reconciliation/skill.md"
  - ".hydra-framework/engine/src/hydra_engine/commands/seed.py"
  - ".hydra-framework/engine/src/hydra_engine/seed/fingerprints.py"
  - ".hydra-framework/evolution/templates/improvement-record.md"
see_also:
  - "hydra://knowledge-unit/hydra-framework/adopt-into-repo"
verify:
  - "python3 .hydra-framework/scripts/hydra.py diff-base --base <path>"
---

# Reconciling A Copy Against Its Base Seed

## Answer

`hydra.py diff-base --base <path>` compares this copy against a base
checkout by content hash (`seed/fingerprints.py`) and classifies differences
as explained or unexplained using the adaptation ledger. Each unexplained
difference must receive an intent, not just a mechanical class: `promote`
(evidence-backed, goes into an `evolution/templates/improvement-record.md`
candidate), `repo-local`, `stale`, or `conflicting`. Missing lineage in
`manifest.yaml` makes the classification less reliable, and that must be
said out loud, not silently trusted.

## Do Not Read By Default

`tasks/` and `cognition/` on either side -- `diff-base` excludes them
deliberately as repository history and derived state.
