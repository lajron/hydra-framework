---
hydra_id: "hydra://knowledge-unit/hydra-framework/change-task-contract"
uid: "ef271cd9-2a76-4182-a180-5ee3d9f9d8aa"
schema_version: "3"
kind: "knowledge-unit"
unit_kind: "rule"
title: "Changing The Task-Record Contract"
status: "active"
scope: "base-seed"
owners:
  team: "hydra"
relations:
  - type: "relates-to"
    target: "hydra://knowledge-space/hydra-framework"
  - type: "relates-to"
    target: "hydra://capability/workflow/task-lifecycle"
provenance:
  sources:
    - ".hydra-framework/capabilities/workflows/task-lifecycle.md"
    - ".hydra-framework/engine/src/hydra_engine/checks/task_contract_docs.py"
    - ".hydra-framework/tasks/templates/task.md"
  source_digests:
    - source: .hydra-framework/capabilities/workflows/task-lifecycle.md
      digest: sha256:1c35730d9c438c2508d2d9a91cbefa268d02c862ac6188b40a307acf87cee672
    - source: .hydra-framework/engine/src/hydra_engine/checks/task_contract_docs.py
      digest: sha256:df0318e92911a167bb38d49ac9380c4ed51f937ce42b11190a783dc9971daed7
    - source: .hydra-framework/tasks/templates/task.md
      digest: sha256:32dd805b125370ccb27117f3984a894c773d0685fcd378aa6cbce3da715dba10
question: "What three places must agree when a required task-record field changes?"
group: "change-task-contract"
certainty: "confirmed"
checked_on: "2026-09-10"
reads:
  - ".hydra-framework/capabilities/workflows/task-lifecycle.md"
  - ".hydra-framework/engine/src/hydra_engine/checks/task_contract_docs.py"
  - ".hydra-framework/tasks/templates/task.md"
verify:
  - "python3 .hydra-framework/scripts/hydra.py validate"
---

# Changing The Task-Record Contract

## Answer

Three places must agree on a required task-record field: the prose contract
(`capabilities/workflows/task-lifecycle.md`), the executable contract
(`checks/task_contract_docs.py`'s `REQUIRED_TASK_SECTIONS`), and the fill-in
form (`tasks/templates/task.md`). `validate_task_contract_docs` fails if they
do not.

## Rules

- Update all three in the same change.
- Existing active task records must still validate, or be updated in the
  same change.
