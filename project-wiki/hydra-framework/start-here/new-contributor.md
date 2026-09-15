# New Contributor

If you have just cloned this repository, prepare the checkout before making a
change:

```bash
python3 .hydra-framework/scripts/hydra.py init-local
python3 .hydra-framework/scripts/hydra.py export-adapters
python3 .hydra-framework/scripts/hydra.py doctor
```

This route is for a clone that already contains `.hydra-framework/`. If Hydra
was copied into a different repository, use the [new-repository adoption
route](/project-wiki/hydra-framework/start-here/adopt-a-repository.md) instead.

## What the setup does

- `init-local` prepares ignored working areas for this clone's machine-specific
  and temporary material. It creates missing areas without overwriting existing
  files. Keep anything that should be shared in the tracked repository instead.
  See the [placement rules](/.hydra-framework/core/placement-rules.md).
- `export-adapters` prepares small, tool-specific files from tracked Hydra
  capabilities, the reusable definitions kept in the repository. Git does not
  track those files, so repeat this step after a fresh clone when your tool
  needs them. A lasting change belongs in its canonical source, the tracked
  file that owns the behavior, not in one of these tool-specific files. See
  the [provider command](/.hydra-framework/engine/src/hydra_engine/commands/providers.py).
- `doctor` checks required paths, reports the current owner, checks protection
  of private working areas, cache state, and tool-specific files, then runs
  validation when those prerequisite checks pass. If it reports that
  tool-specific files are missing when the checkout expects them, run
  `export-adapters` again. See the [validation
  command](/.hydra-framework/engine/src/hydra_engine/commands/validation.py).

## Next action

Read the [Hydra Framework orientation](/project-wiki/hydra-framework/hydra-framework.md), then check current ownership:

```bash
python3 .hydra-framework/scripts/hydra.py board
```

The board is the current list of active task records, tracked notes for ongoing
work, and their owners. If a record already covers your work, follow it.
Otherwise use [Working With
Hydra](/project-wiki/hydra-framework/working-with-hydra/working-with-hydra.md)
and the [First Task Walkthrough](/project-wiki/hydra-framework/working-with-hydra/first-task.md)
to choose the right amount of task tracking. The [board command](/.hydra-framework/engine/src/hydra_engine/commands/work.py)
owns that view.

Before review, validate the surface you changed. Wiki-only work uses
`validate-wiki`; changes under `.hydra-framework/` also use `validate`. The
[Validation](/project-wiki/hydra-framework/operations/validation.md) page
routes the detailed checks.

For a focused question, use [Common Questions](/project-wiki/hydra-framework/start-here/common-questions.md).

## Optional Git hooks

To point this clone at the tracked Git hooks, run:

```bash
python3 .hydra-framework/scripts/hydra.py install-hooks
```

This is a per-clone convenience setting. It is optional, and CI runs the same
checks without it. See the [installation command](/.hydra-framework/engine/src/hydra_engine/commands/installation.py).

## Maintainer route

The setup and ownership sources are collected in the
[Source Map](/project-wiki/hydra-framework/reference/source-map.md#maintainer-evidence).

## Sources

- [Hydra README](/.hydra-framework/README.md)
- [Adoption procedure](/.hydra-framework/capabilities/skills/adoption/skill.md)
- [Placement rules](/.hydra-framework/core/placement-rules.md)
- [Scripts README](/.hydra-framework/scripts/README.md)
- [Private-tier command](/.hydra-framework/engine/src/hydra_engine/commands/private_tier.py)
- [Private-tier implementation](/.hydra-framework/engine/src/hydra_engine/installation/private_tier.py)
- [Provider command](/.hydra-framework/engine/src/hydra_engine/commands/providers.py)
- [Provider ownership](/.hydra-framework/engine/src/hydra_engine/providers/git_ownership.py)
- [Validation command](/.hydra-framework/engine/src/hydra_engine/commands/validation.py)
- [Wiki command](/.hydra-framework/engine/src/hydra_engine/commands/wiki.py)
- [Installation command](/.hydra-framework/engine/src/hydra_engine/commands/installation.py)
- [Git hook implementation](/.hydra-framework/engine/src/hydra_engine/installation/git_hooks.py)
- [Work command](/.hydra-framework/engine/src/hydra_engine/commands/work.py)
- [Board implementation](/.hydra-framework/engine/src/hydra_engine/work/board.py)
- [Task lifecycle workflow](/.hydra-framework/capabilities/workflows/task-lifecycle.md)
