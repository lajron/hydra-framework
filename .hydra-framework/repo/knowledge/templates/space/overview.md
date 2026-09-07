# <Space Name>

Status: active
Certainty: verified | inferred | planned

## Purpose

What this space owns, in one short paragraph.

## Boundaries

In scope:

- <owned area>

Out of scope:

- <neighbor or external authority>

## Source Of Truth Policy

- Code is authoritative for shipped paths, APIs, names, and behavior.
- External specifications are authoritative for rules they own. Link them from
  `sources.md` instead of copying them wholesale.
- Design-only material must be marked `PLANNED` until implementation ships and
  the space is verified against code.
- If a claim in this space conflicts with an authoritative source, fix the space or
  file a concrete problem with evidence.

## If You Have Never Read This Before

1. [State](state.md)
2. [Glossary](glossary.md)
3. [Architecture Graph](architecture/00-graph.md)
4. <first useful architecture slice>

## Reading Map

| Need | Start here |
| --- | --- |
| Current work and handoff | [State](state.md) |
| Define a term | [Glossary](glossary.md) |
| Pick units to read for a task | [Routing](space.yaml.template) |
| Navigate related slices | [Architecture Graph](architecture/00-graph.md) |
| Track unresolved concerns | [Problems](problems.md) |
| Know when the space is done enough | [Definition Of Done](definition-of-done.md) |

## Validation

Run the node-document gate before marking node documentation or diagrams complete:

```bash
python3 .hydra-framework/scripts/hydra.py validate-package-docs --path .hydra-framework/repo/knowledge/spaces/<space-slug>
```

Use `--render` only when DOT diagrams changed and Graphviz is available.
