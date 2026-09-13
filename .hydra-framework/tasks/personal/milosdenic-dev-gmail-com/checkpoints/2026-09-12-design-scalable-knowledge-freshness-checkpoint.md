# Checkpoint: design-scalable-knowledge-freshness

Task: .hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-12-design-scalable-knowledge-freshness.md
Created: 2026-09-12
Status: ready-for-phase-1

## Goal

Resume implementation of the guarded Git-derived content fingerprint. The design
is selected and recorded in the task. Phase 1 is `knowledge/freshness.py` plus
its test set. Do not reopen the architecture decision without new evidence.

## Selected Design In One Paragraph

Git maintains a content-addressed map of the worktree. Read it with
`git ls-files -s` (4.9 ms at 10k files), hash only the paths
`git status --porcelain=v2 -uall` reports as differing from it, and compare the
resulting `path -> Git blob id` map against the identities stored in the
database. Empty delta serves from cache; non-empty delta re-parses only the
paths that moved. Both Git calls use `--no-optional-locks`. A precondition guard
evaluated once per process refuses the fast path when Git cannot be trusted to
report worktree divergence, degrading to canonical source mode.

## Why This And Not The Previous Two Positions

The cooperative epoch design was selected after an alternatives row dismissed
"Git metadata only" on a claim true of `git rev-parse HEAD` and false of
`git status`. It also forced every current caller into `source-only`, so it
would have shipped the full state machine with no measured benefit to anyone.
Rejected.

The subsequent blocked state rested on the aged-index counterexample. That
counterexample is real and was independently reproduced, but it depends on two
non-default Git settings and is closed by the guard. Lifted.

## Aged-Index Fixture, Validated

Required conditions, all simultaneous: `core.trustctime=false`; the index entry
stored outside Git's racy-clean window, which requires the file to be older than
the index write that recorded it; an unrelated staged file rewriting the index
afterwards; a same-size in-place content change preserving inode, device, mode,
uid and gid; and the exact original `mtime_ns` restored.

```text
restored-stat-equal=True
git-dirty=False
worktree-oid-changed=True
fingerprint-changed=False
```

Isolation run across both relevant settings:

| Setting | Value | Detected |
| --- | --- | --- |
| `core.trustctime` | `false` | missed |
| `core.trustctime` | unset (default) | caught |
| `core.checkStat` | `minimal` | missed |
| `core.checkStat` | unset (default) | caught |

Trap for whoever writes the regression test: a fixture that creates and commits
the file in the same second trips Git's racy-clean mitigation, which stores
size 0 in the index entry and forces content comparison forever after. Such a
fixture passes for the wrong reason. Age the file before committing it.

Reproducer preserved at
`.hydra-framework.local/scratchpad/incident-2026-09-13/recovered/aged-index-reproducer.sh`.

## Measured Evidence

10k synthetic fixture, 35 runs after 5 warmups, subprocess spawn included:
`git status` 14.57/15.52 ms, `--no-optional-locks` 15.82/17.82 ms,
`git ls-files -s` 4.91/5.61 ms, full fingerprint with 21 dirty 16.85/17.89 ms,
Python `rglob` + stat manifest 150.06/165.99 ms. An independent second harness
on the same fixture measured the fingerprint at 32.33/33.30 ms and the manifest
at 535.11/544.38 ms. Both runs sit inside the 50/100 ms gate. Record both
harnesses separately; do not average them.

This repository, 320 governed documents: fingerprint p50 12.43 ms, p95 13.81 ms.

Four-state detection verified on a throwaway clone: unstaged modified, staged
modified, untracked added, staged deleted, aggregate `+1 ~2 -1` in 14 ms. Two
successive edits of one file produce byte-identical porcelain including the OID
fields, which is why status text is never used as an identity.

Current repository carries no ignored governed path and no assume-unchanged or
skip-worktree bit. Object format is sha1 and must be read at runtime, never
assumed.

## Next Step

Phase 1 only: `knowledge/freshness.py`. Task section 9 gives the exact module
contract, the porcelain v2 `-z` parsing rules including the rename record trap,
the guard reason codes and their evaluation order, and the phase acceptance
check. Task section 10 gives the test list, including the aged-index regression
fixture written out step by step.

Read task sections 9 and 10 in full before writing code. They are written to be
followed literally; where they name an existing function, read that function
first.

Checkpoint before Phase 2.

Suggested model allocation, given how specified the phases now are: Phase 1
through 4 on a mid-tier model with a review pass at the Phase 2 and Phase 4
acceptance boundaries, Phases 5 and 6 unattended on a small model. The risk is
not code quality, it is a test that passes for the wrong reason. The aged-index
fixture is exactly that trap and its construction order in section 10 is
mandatory.

## Do Not Implement

`CacheReadPolicy` or any capability attestation type; mutation tokens; the
lineage/generation epoch; the five-state status machine; orphan-token recovery;
the managed provider or launcher gate; `freshness_effect` or the AST write-gate
as correctness requirements; a daemon, watcher, TTL, remote cache, per-document
freshness table, or per-search file manifest.

## Changed Files

- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-12-design-scalable-knowledge-freshness.md`
- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/checkpoints/2026-09-12-design-scalable-knowledge-freshness-checkpoint.md`

Preserve unrelated pre-existing edits in
`.hydra-framework/repo/knowledge/spaces/hydra-framework/problems.md` and
`.hydra-framework/cognition/graph/registry.yaml`.

## Validation Performed

- Aged-index counterexample independently reproduced and scoped to two
  non-default settings.
- Fingerprint cost, four-state detection and the porcelain trap reproduced on
  the live repository and a 10k synthetic fixture.
- No production code or provider adapter changed.
- Run `python3 .hydra-framework/scripts/hydra.py validate` after this checkpoint.

## Remaining Work

Phases 1 through 6 in task section 9. Sparse checkout and submodule behavior
need explicit handling before Phase 4; neither blocks Phase 1.

## Blockers

None.

## Useful References

- `AI_SYSTEM.md`
- `.hydra-framework/engine/src/hydra_engine/knowledge/search_index.py`
- `.hydra-framework/engine/src/hydra_engine/ports/sqlite_db.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/storage.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/snapshot.py`
- `.hydra-framework.local/scratchpad/incident-2026-09-13/`

## Provenance

This checkpoint is a reconstruction. On 2026-09-13 an agent overwrote the
untracked task record and its original checkpoint before completing
reproduction. The original checkpoint text is not recoverable. The pre-overwrite
task text and the overwriting versions of both files are preserved under
`.hydra-framework.local/scratchpad/incident-2026-09-13/`. The task record is the
current authority. Copy these files before editing them; they are untracked, so
Git offers no undo.

## Continuation Prompt

Read `AI_SYSTEM.md`, the task record, then this checkpoint. Preserve unrelated
changes to `problems.md` and `registry.yaml`. Implement Phase 1 from task
section 9 with the test set from section 10. The architecture is decided; if you
believe it is wrong, produce a reproduction that fails a named fixture before
proposing a change.
