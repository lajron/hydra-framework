# Private Workspace

Status: operating guide

`.hydra-framework.local/` is the ignored, machine-local workspace for
unfinished thinking, scratch work, source staging, experiments, machine
observations, local indexes, and private configuration. It is not shared
Hydra memory and is not a backup. The [Placement Rules](/.hydra-framework/core/placement-rules.md)
define the boundary; the [State Tiers](/.hydra-framework/repo/knowledge/state-tiers.md)
guide lists the seeded shape.

## The Boundary

| Tier | Use | Location |
| --- | --- | --- |
| Shared | Repository rules, canonical knowledge, capabilities, validation, and other durable team state | `.hydra-framework/` |
| Personal | Tracked, resumable work another person may inherit | `.hydra-framework/tasks/personal/<owner>/` |
| Private | Personal thinking and machine-local material that is not shared evidence | `.hydra-framework.local/` |

If a thought becomes a repository fact, reusable procedure, or team policy,
promote it to its canonical shared owner. If another person must continue
unfinished work, use a personal task record rather than leaving the needed
context only in the private workspace.

Provider-local auto-memory is outside all three Hydra tiers. Hydra does not
create, back up, validate, or version it, and it is authoritative about
nothing shared. Promote any durable claim it suggests into a verified shared
owner or the relevant personal task record instead of relying on the provider
to remember it. The [Memory Governance](/.hydra-framework/repo/knowledge/memory-governance.md)
rules own this promotion boundary.

## Safe Use

Run `init-local` to prepare the local workspace and `init-local --check` to
check its ignore and directory readiness. Existing private files are not
overwritten by bootstrap. The state tiers guide
owns the seeded directory shape, while the implementation owns bootstrap
behavior.

When older state is in the wrong tier, preview the repository's migration
before changing anything:

```bash
python3 .hydra-framework/scripts/hydra.py migrate-state
```

The dry run reports moves, finished-record deletions, private retirements, and
README drops. Review the destinations and ownership attribution, then apply
the plan explicitly:

```bash
python3 .hydra-framework/scripts/hydra.py migrate-state --apply
```

Tracked finished records are removed because Git already owns their history;
untracked finished records are retired into private staging because the
working copy is their only copy. A destination conflict stops the apply
without changing anything. Resolve it first, or use `--force` only when an
overwrite is deliberate. Run `validate` afterward to check the tier boundary
and seeded private shape.

Do not commit private material as an archive or use it as shared evidence.
Shared files must never cite a concrete `.hydra-framework.local/` path because
other readers cannot verify it. When promoting private material, inline the
durable claim and cite the shared canonical owner. The complete boundary
contract is recorded for maintainers in the [Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence),
including the narrow operational exception for personal task-record resume
requirements.

If it is unclear who owns a path or which tier it belongs to, start with the
read-only diagnostic `python3 .hydra-framework/scripts/hydra.py explain-path
<path> --json`. It reports the path's tier and source, plus applicable object,
owner, provenance, and provider information. Then apply the placement rule;
the [Object Context Model](/project-wiki/hydra-framework/architecture/object-context-model.md)
and [Troubleshooting](/project-wiki/hydra-framework/operations/troubleshooting.md)
pages explain the next provenance or routing checks.
