# Operations

Audience: A daily Hydra operator or reviewer deciding what to check next

Reader goal: Run the smallest safe gate, interpret its result, and route a failure to its owner

Page type: orientation

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

Status: orientation

Choose the smallest gate that covers your change. A wiki link or page move uses
the focused wiki gate. A change to shared Hydra state uses full validation. A
source-freshness question uses the report-only wiki audit. If a gate fails,
keep the command, exit result, and finding path, then follow the owning route in
[Troubleshooting](/project-wiki/hydra-framework/operations/troubleshooting.md).

Operations is the route for proving that a Hydra repository is healthy and
narrowing a failure to the owning surface. Start with
[Validation](/project-wiki/hydra-framework/operations/validation.md) to choose the gate. Use
[Evidence and Telemetry](/project-wiki/hydra-framework/operations/evidence-and-telemetry.md) to understand what can
be retained for review and what remains local or deferred. Use [Reference](/project-wiki/hydra-framework/reference/reference.md)
when the check needs exact command or provenance lookup.

## A concrete situation

You update a Markdown link under `project-wiki/`. Run the focused wiki check:

```bash
python3 .hydra-framework/scripts/hydra.py validate-wiki --path project-wiki/hydra-framework
```

If the same change also modifies `.hydra-framework/`, run the full repository
check:

```bash
python3 .hydra-framework/scripts/hydra.py validate
```

The wiki check covers Markdown and double-bracket links. Full validation covers
the framework contracts listed in the [validation contract](/.hydra-framework/validation/README.md).

For exact command forms, use the [Command Surface](/project-wiki/hydra-framework/reference/command-surface.md).

## Choose the gate

| Situation | First command | What it tells you |
| --- | --- | --- |
| Wiki page or link changed | `python3 .hydra-framework/scripts/hydra.py validate-wiki` | Markdown and Obsidian-style links resolve under `project-wiki/` |
| Knowledge package changed | `python3 .hydra-framework/scripts/hydra.py validate-package-docs --node hydra-framework` | Package routes, units, and package links satisfy the node contract |
| Any tracked Hydra source changed | `python3 .hydra-framework/scripts/hydra.py validate` | The repository-wide Hydra contracts pass or name their finding |
| Need current health before work | `python3 .hydra-framework/scripts/hydra.py doctor` | Required paths, local health, and then the validation verdict |
| Need source freshness evidence | `python3 .hydra-framework/scripts/hydra.py wiki audit` | Declared wiki sources are present and their recorded freshness is current |
| Need knowledge-unit freshness evidence | `python3 .hydra-framework/scripts/hydra.py knowledge stale` | Knowledge-unit sources changed after their recorded check |
| Need object identity or reference evidence | `python3 .hydra-framework/scripts/hydra.py ref check` | IDs, aliases, relations, and the derived registry are coherent |
| Need to know who owns a path | `python3 .hydra-framework/scripts/hydra.py explain-path <path> --json` | The composed ownership explanation for a repository path |
| Need command or engine behavior evidence | `python3 .hydra-framework/scripts/hydra.py selftest` | Bundled unit, repository, and contract tests |

## Source freshness

`wiki audit` is a report about declared provenance, not a completeness or
quality score. It checks each managed page's declared source files, checked date,
and recorded digest. It can report findings and still exit successfully, so read
the findings instead of treating a zero exit status as proof that every claim is
covered.

When a page genuinely changes, re-read every source that supports its durable
claims. Only then use `wiki fingerprint --page <hydra-id>` to write the current
source digests and checked date into the page's managed metadata. Run
`validate-wiki` afterward for navigation links. The [wiki surface
contract](/.hydra-framework/surfaces/README.md) and [Documentation
Authoring](/project-wiki/hydra-framework/reference/documentation-authoring.md)
define the source declaration and freshness boundary.

## Provenance and reference graph

Use the smallest reference action that answers the question:

- `explain-path <path> --json` when a path may belong to a different tier,
  provider surface, or canonical owner.
- `ref resolve hydra://...` when you need one object's identity, relations, or
  provenance sources.
- `ref check` before intentionally refreshing the derived registry with
  `ref index`.
- `ref store status` before `ref rdeps` or `ref impact`; rebuild with `ref store
  rebuild` when the query store is missing or stale.

The query store is disposable derived state. `ref resolve` can fall back to a
canonical scan when the store is unavailable, while reverse-dependency and
impact queries require a fresh store. Do not change canonical files merely to
repair a cache. See [Object And Context Model](/project-wiki/hydra-framework/architecture/object-context-model.md)
and [Troubleshooting](/project-wiki/hydra-framework/operations/troubleshooting.md).

## Safe daily loop

1. Read [Working With Hydra](/project-wiki/hydra-framework/working-with-hydra/working-with-hydra.md)
   and run `hydra.py board` before non-trivial work.
2. Use [Context Retrieval](/project-wiki/hydra-framework/architecture/context-retrieval.md)
   to search, route, or compile only the context the task needs.
3. Keep durable work in the correct canonical or task tier, then run the
   smallest gate for the changed surface.
4. Preserve the command, exit result, and finding path for review. Use the
   [Task Lifecycle](/project-wiki/hydra-framework/working-with-hydra/task-lifecycle.md)
   route when work pauses, changes owner, or completes.

## Operator route

1. If the change is a wiki move or link edit, run the focused wiki gate.
2. If shared Hydra state changed, run the full validation gate.
3. If the failure names a package, provider surface, reference store, or engine
   behavior, run the corresponding focused check from [Troubleshooting](/project-wiki/hydra-framework/operations/troubleshooting.md).
4. Preserve the command, exit result, and finding path as review evidence.
5. Use [Evidence and Telemetry](/project-wiki/hydra-framework/operations/evidence-and-telemetry.md)
   when the evidence concerns measurements, redaction, or a future capture
   integration.

## Next action

Open [Validation](/project-wiki/hydra-framework/operations/validation.md) and match your change to a gate. If it
fails, use [Troubleshooting](/project-wiki/hydra-framework/operations/troubleshooting.md) to choose the next
diagnostic.

## Sources

- [Scripts README](/.hydra-framework/scripts/README.md)
- [Wiki command](/.hydra-framework/engine/src/hydra_engine/commands/wiki.py) and [link validator](/.hydra-framework/engine/src/hydra_engine/wiki/links.py)
- [Validation contract](/.hydra-framework/validation/README.md)
- [Knowledge surface contract](/.hydra-framework/surfaces/README.md)
