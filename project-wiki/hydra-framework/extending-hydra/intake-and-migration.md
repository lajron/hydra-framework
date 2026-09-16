# Intake, Migration, And Adoption

For canonical ownership and maintainer evidence, see the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

Page type: orientation

This route helps you choose the right way to bring material or Hydra itself
into a repository. The choice is based on the reader's job and the size of the
source area, not on which command happens to be familiar.

## Choose A Route

| Reader job | Route | Result |
| --- | --- | --- |
| Review one outside source | [Process One Source Through Intake](/project-wiki/hydra-framework/extending-hydra/intake.md) | A verified claim is promoted, kept private, rejected, or archived. |
| Clear a bounded source area | [Migrate A Bounded Source Area](/project-wiki/hydra-framework/extending-hydra/migration.md) | Every source item reaches a terminal ledger status. |
| Copy Hydra into a new repository | [Seed And Adopt Hydra](/project-wiki/hydra-framework/start-here/adopt-a-repository.md) | Hydra is wired without moving the repository's existing material. |
| Drain a legacy agentic setup | [Take over legacy material](/project-wiki/hydra-framework/extending-hydra/migration.md#take-over-legacy-agentic-material) | An explicitly scoped migration drains the selected roots. |
| Integrate another Hydra copy | [Hydra-to-Hydra integration](#hydra-to-hydra-integration) | A staged source copy gets an object map and decision ledger without changing the source tree. |
| Repair misplaced state or an unclear path owner | [Repair misplaced state](#repair-misplaced-state) | The existing placement plan is previewed, applied only when requested, and validated. |

## The Boundary

Ordinary intake handles one source that needs review before it becomes durable
knowledge. Migration handles a source area that must be inventoried as a whole
so the team can tell what remains. Adoption copies and wires Hydra
non-destructively; it does not migrate existing documentation, provider files,
or other agentic material.

The source type also matters. A non-Hydra or legacy setup follows the takeover
scan and approval-gated migration route. A source that already contains a full
Hydra copy follows Hydra-to-Hydra integration. A current adopted copy compared
with its base seed follows [Evolution](/project-wiki/hydra-framework/evolution/evolution.md#seed-copies-and-reconciliation).
Do not turn any of those routes into ordinary one-source intake.

The [glossary](/project-wiki/hydra-framework/reference/glossary.md) defines the terms used by these
routes. Exact staging, promotion, adoption, and takeover rules remain in the
canonical workflow and skills linked below.

## Hydra-to-Hydra integration

Use this route when the staged source is another Hydra repository copy, with its
own `.hydra-framework/`, lineage, capabilities, and knowledge. Ordinary
takeover is for foreign or legacy agentic material. Seed reconciliation is for
comparing the current copy with the base seed it descends from. Integration
keeps the staged source tree unchanged while it prepares explicit decisions.

The source must already be staged under `.migrations/<source-slug>/`. Run the
read-only scan, inspect the proposed mapping, and create the integration
workspace only after the source scope is confirmed:

```bash
python3 .hydra-framework/scripts/hydra.py integrate scan <slug> --json
python3 .hydra-framework/scripts/hydra.py integrate map <slug>
python3 .hydra-framework/scripts/hydra.py integrate map <slug> --create
```

`integrate scan` reports the source graph, collisions, and planned workspace
without changing files. `integrate map` without `--create` only reports the
source-scoped object map. `--create` writes
`.hydra-framework/intake/integrations/<date>-<slug>/` with `README.md`,
`ledger.md`, `object-map.yaml`, and `collisions.yaml`. The source tree remains
untouched.

After reviewing the workspace, `identify` rewrites only the object map, and
`status` reports pending decisions and collisions:

```bash
python3 .hydra-framework/scripts/hydra.py integrate identify <slug>
python3 .hydra-framework/scripts/hydra.py integrate status <slug> --json
```

These commands prepare integration evidence. They do not publish source objects
or merge the source tree. Continue through the recorded owner decisions and
validation route for any later promotion.

## Repair misplaced state

Use this route when a path is in the wrong state tier or its owner is unclear.
It is a placement repair, not content intake or migration. First ask the
read-only ownership explanation for the exact path:

```bash
python3 .hydra-framework/scripts/hydra.py explain-path <path> --json
```

If the placement plan is clear, preview the mechanical repair and inspect its
move and conflict report:

```bash
python3 .hydra-framework/scripts/hydra.py migrate-state
```

Apply only the reviewed plan, then validate the repository:

```bash
python3 .hydra-framework/scripts/hydra.py migrate-state --apply
python3 .hydra-framework/scripts/hydra.py validate
```

`migrate-state` is dry-run by default. `--apply` changes paths according to the
placement rules, and `--force` is available only when a reviewed destination
conflict should be overwritten. It does not promote claims, create a migration
ledger, or authorize a takeover. If `explain-path` cannot establish an owner,
stop and resolve ownership through [State Tiers](/project-wiki/hydra-framework/concepts/state-tiers.md)
before applying anything.

## Related Routes

[Knowledge Spaces](/project-wiki/hydra-framework/extending-hydra/knowledge-spaces.md) explains where promoted meaning
belongs. [Private Workspace](/project-wiki/hydra-framework/working-with-hydra/private-workspace.md)
explains where unreviewed or machine-local material stays. Use [Validation](/project-wiki/hydra-framework/operations/validation.md)
after the relevant shared or wiki surface changes.
