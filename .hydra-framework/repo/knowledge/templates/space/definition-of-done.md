# Definition Of Done

This file defines when the space is useful enough to stop polishing. It is a
stop condition, not a deadline.

## Audience Goals

- Humans can answer common repository questions by reading the space instead
  of rediscovering patterns from scratch.
- AI agents can load `state.md`, one route's units, and one or two slices with
  enough context to work safely.

## Done When

- `overview.md` defines space boundaries and source-of-truth policy.
- Architecture slices listed in the reading map exist or are explicitly parked.
- Design-only slices carry `certainty: unresolved`; shipped behavior is
  verified against code or its owning external source.
- `space.yaml.template`'s `routes:` name the scoped units to read for common tasks.
- `architecture/00-graph.md` lists active slices and important relationships.
- Each architecture slice ends with a `## See Also` section when related slices
  exist.
- `glossary.md` covers terms used by active slices.
- `problems.md` is empty or every remaining problem has evidence and a next
  action.
- The node-document gate passes.

## Not Required

- Perfect coverage of every source file. Units are scoped answers, not
  exhaustive indexes.
- Permanent archives of resolved problems. Keep only durable lessons elsewhere
  when useful.
- Duplicating external source material that is already authoritative.

## Maintenance Mode

- Touch the relevant space slice next to repository changes that alter its
  claims.
- Move a slice off `certainty: unresolved` only after implementation exists
  and it has been verified.
- Add or update units and routes when the correct read path changes.
- Run the node-document gate before merging node documentation changes.
