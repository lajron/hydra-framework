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
    - source: ".hydra-framework/capabilities/skills/knowledge-unit/metadata.yaml"
      digest: "sha256:38a2a5de779f73079ed7e782e1ce007188b27f04b7d377f63936993aa4302852"
    - source: ".hydra-framework/adapters/providers/claude/README.md"
      digest: "sha256:5d030b55f7a8859f7cfdd0f1447c367728f50a82102acbd10087f86a2e92c17e"
    - source: ".hydra-framework/engine/src/hydra_engine/providers/capabilities.py"
      digest: "sha256:56e3df1c20e6b5317dfadc964e614aa0818d1e639dee210b195e98e2789d33a6"
    - source: ".hydra-framework/engine/src/hydra_engine/providers/adapter_plan.py"
      digest: "sha256:da961602934435c1c19c1249d23a02e2f4bdb713359ba17ed1f9c19294ca2000"
question: "What must be true before a new Hydra skill or subagent ships?"
group: "add-module"
certainty: "confirmed"
checked_on: "2026-08-30"
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
