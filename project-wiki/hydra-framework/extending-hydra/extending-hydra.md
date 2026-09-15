# Extending Hydra

Page type: orientation

If you need to change Hydra, first identify the outcome you want, then use the
route that owns it. The linked pages explain the work and lead to the canonical
source, the version-controlled source that owns the rule.

## A concrete situation

You are about to add a reusable capability, register an engine extension,
update a provider surface, change repository knowledge, review outside
material, clear a defined source area, or copy Hydra into another repository.
Choose the first matching route below before editing a file. This keeps
framework meaning with its owner instead of turning a runtime-facing file or
wiki page into a second source of truth.

## Choose a route

| Need | Read |
| --- | --- |
| Add or maintain reusable agents, skills, workflows, or tools | [Capabilities](/project-wiki/hydra-framework/extending-hydra/capabilities.md) |
| Add a supported engine integration point | [Extension Points](/project-wiki/hydra-framework/extending-hydra/extension-points.md) |
| Make a safe registry change | [Safe Extension Recipes](/project-wiki/hydra-framework/extending-hydra/extension-recipes.md) |
| Understand runtime-facing files and generated adapters | [Provider Adapters](/project-wiki/hydra-framework/extending-hydra/provider-adapters.md) |
| Organize durable repository knowledge for routing and retrieval | [Knowledge Spaces](/project-wiki/hydra-framework/extending-hydra/knowledge-spaces.md) |
| Review one outside source | [Process One Source Through Intake](/project-wiki/hydra-framework/extending-hydra/intake.md) |
| Clear a bounded source area or legacy setup | [Migrate A Bounded Source Area](/project-wiki/hydra-framework/extending-hydra/migration.md) |
| Copy Hydra into a new repository | [Seed And Adopt Hydra](/project-wiki/hydra-framework/start-here/adopt-a-repository.md) |

## Keep ownership clear

Hydra's canonical meaning remains under `.hydra-framework/`. A provider surface
is a file or directory that a particular runtime discovers, such as `AGENTS.md`,
`CLAUDE.md`, `.claude/`, `.agents/`, or `.codex/`. The provider adapter contract
keeps those surfaces separate from canonical capabilities and rules, so check
[Provider Adapters](/project-wiki/hydra-framework/extending-hydra/provider-adapters.md)
before changing one.

The pages in this section explain where maintainers work and route to the
canonical contracts; they do not replace those contracts. For maintainer
evidence behind a claim, use the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

## Next action

Open the first route that matches your intended outcome, then follow its source
links and validation guidance before making the change. If no route
matches, trace ownership through the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence)
before creating a new extension path.

## Sources

- [Ownership And Composition](/.hydra-framework/core/ownership-and-composition.md)
- [Placement Rules](/.hydra-framework/core/placement-rules.md)
- [Modules](/.hydra-framework/capabilities/README.md)
- [Provider Adapter Contract](/.hydra-framework/adapters/providers/README.md)
- [Knowledge v3 Architecture](/.hydra-framework/core/knowledge-architecture.md)
- [Transferred Material Migration](/.hydra-framework/capabilities/workflows/material-migration.md)
- [Hydra Adoption Skill](/.hydra-framework/capabilities/skills/adoption/skill.md)
