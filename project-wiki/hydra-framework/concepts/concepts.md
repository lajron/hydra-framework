# Where to start with Hydra's concepts

Start with the question you need to answer. If you are deciding where a finding
belongs, read [State Tiers](/project-wiki/hydra-framework/concepts/state-tiers.md).
If you are tracing how a task gets prepared and verified, read
[Architecture](/project-wiki/hydra-framework/architecture/architecture.md).

## A concrete situation

You discover a repository rule while working on a change. If the rule should
guide the team, it belongs in shared state; [State Tiers](/project-wiki/hydra-framework/concepts/state-tiers.md)
explains that boundary. If you need to understand how a task receives that rule
and moves through execution and verification, follow
[Architecture](/project-wiki/hydra-framework/architecture/architecture.md),
then continue to [Execution Flow](/project-wiki/hydra-framework/architecture/execution-flow.md).

## The two foundations

The [placement rules](/.hydra-framework/core/placement-rules.md) define the
state boundary, and the [architecture rules](/.hydra-framework/core/architecture.md)
define runtime responsibilities. These version-controlled files own those rules.

- [State Tiers](/project-wiki/hydra-framework/concepts/state-tiers.md) explains
  where shared, personal, and private state belongs.
- [Architecture](/project-wiki/hydra-framework/architecture/architecture.md)
  routes from the runtime responsibility model to the execution stack and
  detailed flow pages.

## Next action

Choose [State Tiers](/project-wiki/hydra-framework/concepts/state-tiers.md) for
a placement decision. Choose [Architecture](/project-wiki/hydra-framework/architecture/architecture.md)
for a runtime question, then continue to [Execution Flow](/project-wiki/hydra-framework/architecture/execution-flow.md).

For maintainers checking a claim's owner, use the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).
