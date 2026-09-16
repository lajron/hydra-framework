---
hydra_id: "hydra://knowledge-unit/hydra-framework/add-module"
uid: "10219e6b-b5d9-43bc-9452-e77822d34184"
schema_version: "3"
kind: "knowledge-unit"
unit_kind: "answer"
title: "Adding A Skill Or Subagent"
status: "active"
scope: "base-seed"
owners:
  team: "hydra"
relations:
  - type: "relates-to"
    target: "hydra://knowledge-space/hydra-framework"
  - type: "relates-to"
    target: "hydra://capability/skill/knowledge-unit"
provenance:
  sources:
    - ".hydra-framework/capabilities/skills/knowledge-unit/metadata.yaml"
    - ".hydra-framework/adapters/providers/claude/README.md"
    - ".hydra-framework/engine/src/hydra_engine/providers/capabilities.py"
    - ".hydra-framework/engine/src/hydra_engine/providers/adapter_plan.py"
  source_digests:
    - source: .hydra-framework/capabilities/skills/knowledge-unit/metadata.yaml
      digest: sha256:7b8ef22df1d5d2fe6a0451bfc8196efaa1a7331e6ab8621d70f1894f1871b59c
    - source: .hydra-framework/adapters/providers/claude/README.md
      digest: sha256:4de81e2d852bb2970d6e3b667a3c497fce56417f45a17b064544f5ecfe6a7471
    - source: .hydra-framework/engine/src/hydra_engine/providers/capabilities.py
      digest: sha256:a2887b785d20626bd7302efb398e670c0955ce04b177fa5f34b63c8c0b8c5ce5
    - source: .hydra-framework/engine/src/hydra_engine/providers/adapter_plan.py
      digest: sha256:028b4d16bc9138222759938677e332b1a733419993f49fac71092aa748b74710
question: "What must be true before a new Hydra skill or subagent ships?"
group: "add-module"
certainty: "confirmed"
checked_on: "2026-09-10"
reads:
  - ".hydra-framework/capabilities/skills/knowledge-unit/metadata.yaml"
  - ".hydra-framework/adapters/providers/claude/README.md"
  - ".hydra-framework/engine/src/hydra_engine/providers/capabilities.py"
  - ".hydra-framework/engine/src/hydra_engine/providers/adapter_plan.py"
see_also:
  - "hydra://knowledge-unit/hydra-framework/agent-export-trace"
verify:
  - "python3 .hydra-framework/scripts/hydra.py export-adapters --check"
---

# Adding A Skill Or Subagent

## Answer

Add the canonical source under `capabilities/skills/<slug>/` (`metadata.yaml`
+ `skill.md`) or `capabilities/agents/<slug>/` (`metadata.yaml` + `agent.md`),
then run `export-adapters` to generate provider wrappers. A skill's
`metadata.yaml` needs `name` and `description`; an agent's also needs
`capability_class` and `effort`. Every used capability class and effort budget
must have an entry in each provider's `capability-map.yaml`
(`.hydra-framework/adapters/providers/claude/capability-map.yaml`,
`.hydra-framework/adapters/providers/codex/capability-map.yaml`). A usable entry
emits the provider field; an empty or `unresolved` entry is deliberately omitted
from the generated wrapper (`hydra://knowledge-unit/hydra-framework/agent-export-trace`
traces this resolution end to end).

If the new agent will participate in coordinated work, keep its role and
provider mapping separate from orchestration execution. The orchestration
control plane records explicit bounded requests and ownership; generated
provider files do not establish a scheduler or provider SDK runtime.

## Rules

- `kind` in a v2 metadata file is `procedure` or `command` (see any sibling
  `capabilities/skills/*/metadata.yaml`).
- `hydra_id`, `uid` (real UUID4), and the full `schema_version: 3` envelope
  are required on every canonical source file.
- `hydra.py export-adapters --check` must be clean after the change.

## Do Not Read By Default

Generated files under `.claude/`, `.agents/`, or `.codex/` -- they are outputs,
not sources. `project-wiki/` -- that is the human explanation surface, not
canonical definition.
