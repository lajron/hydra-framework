---
hydra_id: "hydra://knowledge-unit/hydra-framework/fix-provider-surface"
uid: "dbde7a08-930b-4a00-a468-da79f87d2c9d"
schema_version: "3"
kind: "knowledge-unit"
unit_kind: "answer"
title: "Fixing An Orphaned Or Drifted Provider Surface"
status: "active"
scope: "base-seed"
owners:
  team: "hydra"
relations:
  - type: "relates-to"
    target: "hydra://knowledge-space/hydra-framework"
provenance:
  sources:
    - ".claude/rules/hydra-placement.md"
    - ".hydra-framework/engine/src/hydra_engine/providers/reclaim.py"
  source_digests:
    - source: .claude/rules/hydra-placement.md
      digest: sha256:e8f71f3d481932d35cc2c4c6717431c8e1a2be43e47e17fb75c39b5ddc1c5236
    - source: .hydra-framework/engine/src/hydra_engine/providers/reclaim.py
      digest: sha256:96cc1f63dda07e239bf711387bfe49baccba71467732e3c1b131f7350598fff1
question: "How is an orphaned, drifted, or stale provider surface file fixed?"
group: "fix-provider-surface"
certainty: "confirmed"
checked_on: "2026-09-12"
reads:
  - ".claude/rules/hydra-placement.md"
  - ".hydra-framework/engine/src/hydra_engine/providers/reclaim.py"
verify:
  - "python3 .hydra-framework/scripts/hydra.py reclaim"
  - "python3 .hydra-framework/scripts/hydra.py export-adapters --check"
---

# Fixing An Orphaned Or Drifted Provider Surface

## Answer

`reclaim.py`'s `classify_surfaces` labels every provider file `orphaned` (no
provenance sidecar -- promote it into the right canonical module directory),
`stale` (canonical source gone, or no longer in the export plan -- delete or
restore the source), or `drifted` (content no longer matches the plan --
move the edit to the canonical source, never the generated wrapper). Fix in
the canonical source, then confirm `hydra.py reclaim` and
`export-adapters --check` are both clean. `reclaim --promote` is a safe move for
an isolated provider-native module: after both canonical files are written it
removes the original, and a retry only removes the original when canonical
metadata names the same `promoted_from`. Use framework takeover and the material
migration workflow for a broader legacy setup.

## Do Not Read By Default

Every other provider surface. Fix the ones actually reported.
