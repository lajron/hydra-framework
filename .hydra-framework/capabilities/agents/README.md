# Agents

Agents are specialist roles that make decisions and coordinate work.

Agents may reference skills, workflows, tools, and knowledge. They should not duplicate canonical knowledge or skill instructions.

Recommended agent shape:

- `agent.md`: role, responsibilities, boundaries, inputs, outputs.
- `metadata.yaml`: scope, maturity, dependencies, evolution notes.
- `examples/`: optional usage examples.

Agent metadata must include `name`, `description`, `capability_class`, and
`effort`. Maintained roles should also retain the common envelope fields used by
the other capability objects: identity (`schema`, `hydra_id`, `uid`, and
`schema_version`), `scope`, `maturity`, `owners`, `dependencies`, `relations`,
and `provenance`. `tools` and `tags` are optional. Profiles narrow generated
skills only; tags on an agent do not remove that agent from a provider surface.

Use the provider-neutral class and effort vocabulary from the parent
capabilities README. A class describes the resource shape of the role and an
effort is its requested budget. Provider maps translate them at export time;
canonical agent metadata must not name a model.


Hydra treats mini-agents and provider subagents as first-class Execution Harness components. Use them for focused checking, research, review, validation, summarization, or other isolated work when they reduce main-context noise or improve confidence.

Provider-specific subagent files are adapters over canonical Hydra agent definitions.
