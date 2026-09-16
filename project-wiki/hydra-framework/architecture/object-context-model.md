# Object And Context Model

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

Hydra uses objects to give repository artifacts durable, resolvable identity.
Context compilation then selects a bounded, task-relevant view of those
artifacts. Both mechanisms derive their answers from canonical files; neither
is a second source of truth.

## Identity Without Path Coupling

An authored object declares a `hydra_id` in its envelope. That is its primary
reference. A `uid` distinguishes the same logical object across an
unambiguous move, while its path and digest describe its current location and
contents. Aliases preserve explicitly declared alternate references. Relations
name other objects, rather than replacing their identifiers with a file path.

```mermaid
flowchart TB
  A["Authored envelope<br/>hydra_id + uid + aliases + relations"] --> B[ref check validates identity and references]
  B --> C[ref index writes the derived object registry]
  C --> D[ref resolve / query-store reads / context compiler]
```

The object-family registry classifies an object by identifier prefix first,
then by declared `kind`. The object-reference check rejects an unregistered
prefix or kind, duplicate identity, unresolved references, and missing
required envelope fields. A reference is therefore not made valid merely
because a similarly named file exists.

## Forms And Derived Stores

The object-handler registry decides which document forms can contribute an
envelope and where they are scanned. Today it covers Markdown and YAML across
the broader Hydra root, with YAML excluding `cognition/`, while Python is
rooted at `engine/src`. An unclaimed file form is not an error; it simply has
no registered envelope reader.

`ref index` exports the derived registry from validated canonical metadata.
The optional query store is local operational state. Its object, alias,
relation, and provenance tables are built from that export, while document and
reference rows are refreshed per changed file. A query uses the store only
when its schema and export digest are current. If it is missing, stale,
corrupt, or disabled, callers fall back to the scan path instead of treating
the cache as authority.

## Reference Graph Workflows

Use the graph when a change affects identity, ownership, or relationships:

| Question | First action | Meaning of the result |
| --- | --- | --- |
| What object is this ID or alias? | `ref resolve hydra://...` | Shows the canonical identity, UID, path, relations, and provenance sources. It can use the store or fall back to a canonical scan. |
| Which objects cite this object? | `ref store status`, then `ref rdeps hydra://...` | Lists one-hop reverse relation citations from a fresh derived store. |
| What can this object affect? | `ref store status`, then `ref impact hydra://... --depth N` | Walks outbound relations to a bounded depth. It is not a prediction of runtime behavior. |
| Who owns this path? | `explain-path <path> --json` | Combines tier, object, provider-surface, directory-owner, reverse-citation, and provenance-citer evidence. |
| Is the graph safe to refresh? | `ref check`, then `ref index` | Validates IDs, aliases, relations, and provenance before writing the rebuildable registry. |

For an intentional canonical move, run `move-object <source> <destination>
--dry-run` first. The move keeps the object's `hydra_id` and `uid`, refuses a
state-tier change or destination collision, and reports citations that still
name the old path. Apply only after reviewing that report, then run `ref check`.
An ambiguous identity, missing UID, unresolved relation, or stale binding is a
reason to stop and resolve the source decision, not to guess a replacement.

The derived registry and query store are operational projections. `ref index`
refreshes the registry from canonical envelopes, while `ref store rebuild`
refreshes the local query store. A missing, corrupt, or stale store does not
invalidate canonical objects: `ref resolve` and `explain-path` can scan the
sources, while `ref rdeps` and `ref impact` refuse until a fresh store exists.
Do not edit a source file to make a cache query pass.

## How Context Is Routed

`compile-context` begins with any explicit object or path references, then
runs registered context providers. The Knowledge provider uses knowledge
packages and their routes, including required units and route-specific
verification guidance. Other current family providers select ranked search
matches from the shared search corpus. Candidate priority, deduplication, a
per-family cap, and the packet token budget keep selection inspectable and
bounded.

Each registered object family has exactly one context provider. The current
registry is an engine extension boundary, not a claim that every repository
file participates in context selection. `--include-family` and
`--exclude-family` narrow the current provider set when a caller needs a
smaller blast radius.

## Maintainership Boundary

Object families, handlers, stores, and providers describe the current engine
design. They are reviewed source-level extension points, not a plugin API or
an ABI guarantee. For a change recipe and its checks, use [Safe Extension
Recipes](/project-wiki/hydra-framework/extending-hydra/extension-recipes.md).
