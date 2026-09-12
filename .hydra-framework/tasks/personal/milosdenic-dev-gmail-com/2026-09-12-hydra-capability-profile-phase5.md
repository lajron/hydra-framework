# Task: hydra-capability-profile-phase5

Status: active
Owner: milosdenic-dev-gmail-com
Created: 2026-09-12
Updated: 2026-09-12

## Goal

Prepare and, only after Gate B evidence is satisfied or explicitly overridden, implement Phase 5: untrack generated provider adapters and replace the tracked-output CI drift gate with canonical, ownership, ignore, bootstrap, and non-vacuity validation.

## Confirmed Decisions

- Phase 5 is a separate task from completed Phase 4. It changes Git tracking
  and CI behavior; it must not be folded into the reconciliation work.
- Generated adapter paths may be untracked only after Gate B is satisfied or
  the owner explicitly records an override. The evidence is: (1) a reviewed,
  real full profile-switch cycle for every active provider, (2) recorded
  profile-switch diff churn as an actual problem, (3) verified clean-clone
  bootstrap guidance when no adapters are materialized, and (4) one real
  canonical deletion taken through stale reporting and manual removal.
- Until then, Phase 4 remains the operating model: adapters are tracked,
  profile switches are visible/reviewable diffs, and `export-adapters --check`
  remains the current drift check.

**2026-09-12 override.** The owner (milosdenic-dev-gmail-com) explicitly
overrides Gate B on 2026-09-12, without collecting the four evidence items
above. Implementation of Phase 5 is authorized now, on the owner's direct
instruction, not on satisfied gate evidence. This is recorded here per the
task-lifecycle rule that an override must be explicit and durable before
untracking begins.

## Approved Plan

1. Collect and record Gate B evidence without changing Git tracking or CI.
2. If the gate is met or explicitly overridden, land generated-path ignore
   rules first, then allow one team pull cycle for bootstrap instructions.
3. In one reviewed commit, untrack exactly `ownership_paths()` output, replace
   CI's tracked-output drift gate with canonical, in-memory full-plan,
   black-box reconciliation, Git-ownership, and non-vacuity checks, and add
   ignored-path membership validation.
4. Export the full profile locally for framework development, then complete
   the clean-clone, existing-clone, distinct-worktree, profile-switch, and
   fresh-provider-session verification described in Phase 6 of the plan.

## Current Stage

Gate B evidence was not collected; the owner overrode the gate on 2026-09-12
(see Confirmed Decisions). Implementation is in progress: narrow ignore
patterns, Git ownership checks, the CI validation replacement, the untracking
commit, and bootstrap-explicitness updates.

## Readiness

Status: implementation and local validation complete; staged, not committed

- Branch or workspace assumptions: the pre-existing dirty working tree was
  preserved throughout. Phase 5 edits sit alongside Phase 1-4's uncommitted
  implementation and unrelated pre-existing modified files; nothing was
  reverted or discarded.
- Relevant canonical docs: `AI_SYSTEM.md`; `.hydra-framework/core/placement-rules.md`;
  `.hydra-framework/repo/knowledge/spaces/hydra-framework/overview.md`; and
  the Phase 5/Gate B sections of the private capability-profile plan.
- Required dependencies, services, generated artifacts, or private local requirements:
  `.hydra-framework.local/plans/hydra-capability-tag-filtering-plan.md` is
  the detailed Phase 5 specification.
- Blockers and assumptions: none remaining for implementation. The repository
  is in the intended migration index state (see Changed Files); an actual
  commit was intentionally not created, per standing instruction to commit
  only when the user explicitly asks.
- Expected validation command or evidence: see Validation below. All items
  from the Approved Plan and the plan's Phase 6 were exercised.

## Step State

- Active step: none; implementation and validation are complete for this
  session. Awaiting the owner's decision to commit.
- Next step: review the staged diff, commit the migration (the untracking
  `git rm --cached` is already staged), push, and watch the first real CI
  run on the new workflow. After that, complete this task record.
- Completed steps:
  1. `WRAPPER_PREFIX` constant added to `providers/capabilities.py` and wired
     through `adapter_plan.py`, `reclaim.py`, `selection.py` (single source
     of truth for the wrapper-name prefix, per review point 7).
  2. New `providers/git_ownership.py`: ignore-pattern generation from
     `PROVIDERS`/`WRAPPER_PREFIX`, `ensure_generated_adapter_ignore_block`,
     and the four required Git ownership checks (unignored ownership,
     tracked ownership, unverified ignored provider paths, tracked-and-ignored
     provider paths). `ports/git.py` gained `ignored_files()` and an
     `ignore_match(..., no_index=True)` mode (needed because plain
     `check-ignore` treats an already-tracked path as never-ignored, verified
     against real Git 2.43 behavior).
  3. `.gitignore` carries the marked, generated ignore block.
  4. Untracked exactly the 76 tracked `ownership_paths()` members via
     `git rm --cached` (staged; files remain on disk). Verified
     programmatically: no canonical `.hydra-framework/` path and no stable
     integration file (`settings.json`, `rules/`, etc.) was in that set.
  5. `commands/validation.py`'s `command_doctor` now fails closed (not just a
     note) when nothing is materialized but the active profile's plan is
     non-empty; `cli/dispatch.py` supplies `desired_plan_nonempty` via the
     new `commands/providers.resolve_active_plan`.
  6. `.github/workflows/hydra.yml`: replaced the `export-adapters --check`
     drift-gate step with a `Bootstrap capability adapters` step
     (`export-adapters`, no flags) run before `Selftest`/`Doctor`, since a
     clean CI clone now starts with nothing materialized. `--check` stays a
     local developer command only.
  7. `AI_SYSTEM.md` checklist gained a bootstrap-detection item; the `adopt`
     report's suggested steps now state that `export-adapters` is required
     every fresh clone, not merely available.
  8. `tests/repository/test_provider_surfaces.py`'s
     `test_repository_surfaces_are_all_generated` gained a non-vacuity
     assertion (surface count vs. the ownership index's body-only paths), so
     an unbootstrapped checkout fails loudly instead of passing vacuously.
  9. New `tests/repository/test_git_ownership.py` (live-repo, real Git) and
     `tests/unit/providers/test_git_ownership.py` +
     `tests/unit/ports/test_git.py` additions (pure/fixture-git tests).
     `tests/unit/commands/test_validation.py` gained the doctor bootstrap-fail
     tests.
  10. Refreshed `source_digests`/`checked_on` on the two knowledge units whose
      sources changed (`fix-provider-surface.md`, `agent-export-trace.md`)
      via `hydra.py knowledge fingerprint`, then `hydra.py ref index`.
      `adopt-into-repo.md` was reviewed; its sources were untouched and its
      content stayed accurate, so it needed no edit.
  11. `cli/command_metadata.py`: `export-adapters`/`profile select` privacy
      fields updated from "shared (tracked repository files)" to reflect
      that generated output is now local-working-tree-only.

## Changed Files

New: `.hydra-framework/engine/src/hydra_engine/providers/git_ownership.py`;
`.hydra-framework/engine/tests/repository/test_git_ownership.py`;
`.hydra-framework/engine/tests/unit/providers/test_git_ownership.py`.

Modified (Phase 5-specific; Phase 1-4's own uncommitted changes are untouched):
`providers/capabilities.py`, `providers/adapter_plan.py`, `providers/reclaim.py`,
`providers/selection.py`, `ports/git.py`, `commands/providers.py`,
`commands/validation.py`, `cli/dispatch.py`, `cli/command_metadata.py`,
`commands/installation.py`, `.gitignore`, `.github/workflows/hydra.yml`,
`AI_SYSTEM.md`, `tests/repository/test_provider_surfaces.py`,
`tests/unit/ports/test_git.py`, `tests/unit/commands/test_validation.py`,
knowledge units `fix-provider-surface.md`, `agent-export-trace.md`, and
`cognition/graph/registry.yaml` (reindexed).

Staged (index-only): `git rm --cached` on the exact 76 tracked
`ownership_paths()` members under `.claude/skills`, `.claude/agents`,
`.agents/skills`, `.codex/agents` -- files remain on disk, untracked and
Git-ignored. No canonical source and no stable integration file was touched.

## Validation

- `hydra.py selftest`: 1545 tests, OK (both on the live repo and inside a
  from-scratch clean-clone simulation built from the current working tree,
  described below).
- `hydra.py validate`: ok.
- `hydra.py doctor`: exit 0 on the live repo; exit 1 with the new
  "no provider surfaces are materialized" message on a genuinely fresh clone
  before bootstrap, exit 0 after `export-adapters`.
- Git ownership invariants (`git_ownership.py`, both as unit tests against
  fixture repos and as `tests/repository/test_git_ownership.py` against this
  live repo): every `ownership_paths()` member is ignored; none remain
  tracked; every path Git actually ignores under a provider target is a
  verified ownership member; no tracked provider file is ignored. All four
  hold on the live repo after the `git rm --cached`.
- Clean-clone simulation: materialized the current working tree (index +
  working-tree edits, respecting `.gitignore`) into a scratch repo, then ran
  a real `git clone` of it -- a true fresh clone with zero local state.
  Confirmed: `doctor` fails closed before bootstrap; `export-adapters`,
  `selftest` (1545 OK), `doctor` (exit 0), and `reclaim --fail-on-findings`
  (38 generated, 0 unmanaged) all pass after bootstrap, in that order,
  matching the new CI step order.
- Profile-switch round trip in that same clone: `full` -> `core` (removed
  52 files, 1 skill selected) -> `full` (recreated 52, back to 14 skills),
  `doctor` exit 0 after.
- Two independent clones with distinct active profiles (`full` and
  `hydra-maintainer`) coexisted with no interference.
- Generated wrapper structure sanity: Claude `SKILL.md` frontmatter, the
  dual wrapper-name/canonical-path agent dependency line, and the Codex
  agent TOML all parsed correctly in the bootstrapped fresh clone.
- Not verified in this session: an actual fresh Claude or Codex CLI session
  discovering the materialized skills/agents at session start -- this
  sandbox cannot launch either provider's real session. The generated file
  structure was checked mechanically instead (see above).

## Blockers

None. Gate B evidence was never collected; the owner's 2026-09-12 override
(see Confirmed Decisions) is the authorization on record for proceeding
without it.

## Continuation Notes

What another model or developer needs to continue safely.

- Running state: everything is staged in the working tree/index; no commit
  exists yet. `git status` shows 76 staged deletions (`D`, the untracked
  ownership paths, files still present on disk) plus the modified/new files
  listed in Changed Files, plus Phase 1-4's own pre-existing uncommitted
  work.
- Resume check: run `python3 .hydra-framework/scripts/hydra.py board --owner
  milosdenic-dev-gmail-com`; confirm this task is still active, then run
  `git status` and `git diff --cached --stat` to see exactly what is staged
  before deciding whether to commit.
- If you commit: after pushing, watch the first CI run on
  `.github/workflows/hydra.yml` closely -- it is the first real (non-simulated)
  clean-clone exercise of the new `Bootstrap capability adapters` step and
  the git-ownership repository tests.
- Recommended next step if the user wants this task closed: after a
  reviewed commit and a green CI run, run `hydra.py task complete
  hydra-capability-profile-phase5` with the durable outcome (this record's
  Changed Files section, or the commit it becomes).
