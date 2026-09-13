# Checkpoint: bounded-knowledge-retrieval

Task: .hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-13-bounded-knowledge-retrieval.md
Created: 2026-09-13
Status: paused

## Goal

Stop every knowledge query from loading and scanning the whole corpus in
Python, and cut the per-prompt Git fingerprint cost to what correctness
actually requires. Three confirmed problems: P13 (every query scans the
whole corpus in Python), P14 (the CLI reports an FTS5 index that was never
built), P15 (three whole-repository Git fingerprints per prompt where two
are needed). All three are recorded in
`.hydra-framework/repo/knowledge/spaces/hydra-framework/problems.md`.

Split out of `2026-09-13-scalable-incremental-knowledge-index` on
2026-09-13: that record's single Phase 1 design session grew from four
phases to seven, absorbing this read-path scope alongside its own
write-path scope (P12). This record now owns P13, P14, P15 and decisions
D7a, D8, D9, D10, D11; the sibling record kept D1-D6, D7, D7b and P12 only.

## Confirmed Decisions

D7a, D8, D9, D10, D11, recorded in full in the task record (moved verbatim
from the sibling record, phase references renumbered). In short:

- D7a: the four clean-read section 8 gates are caused by whole-corpus
  materialization per query (P13), not by the publication layer the sibling
  task addresses.
- D8: share the pinning fingerprint between `cache_state` and
  `capture_stamp`, keeping the closing revalidation an independent second
  Git read (P15).
- D9: a clean read proves freshness from one aggregate-digest row instead of
  scanning every row. Its write-path change (writing that row into `meta`)
  is decided as this task's own responsibility, in this task's Phase 2, not
  the sibling task's -- see the ownership note under D9 in the task record.
- D10: FTS5 narrows candidates; channel, rank, graph count and the tie-break
  stay the existing code over the narrowed set. Explicitly not bm25.
- D11: P14 is fixed by building the index, not by editing the message, with
  an explicit fallback obligation if Phase 3 does not land.

## Approved Plan

Four phases, continuing the numbering of the design phase shared with the
sibling task: 1 design (shared, done in the sibling record), 2 bounded
freshness checking (shared fingerprint, aggregate-digest fast path, and the
D9 write-path change), 3 the real FTS5 lexical index plus honest mode
reporting, 4 the read-half section 8 benchmark (four clean-read gates) plus
a before/after per-prompt `route-prompt` measurement on this repository.

Blocked on the sibling task's Phase 4 landing: Phase 2 and Phase 3 both
modify `index_cache.py`'s write transaction functions, which the sibling
task's Phases 2 to 4 are still actively changing.

## Completed Work

None under this record's own numbering. The shared Phase 1 design work
(confirming P13, P14, P15 and recording D7a, D8, D9, D10, D11) is recorded
in the sibling task's Phase 1, not repeated here. This session's only work
was the split itself: creating this record, moving the read-path decisions
and phases into it, and repointing P13/P14/P15's `Resolution:` lines in
`problems.md`.

## Current Stage

Split out of the sibling record at its Phase 1 boundary. Blocked on that
record's Phase 4. No phase of this record's own numbering has started.

## Changed Files

- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-13-bounded-knowledge-retrieval.md`
  (new, this record).
- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/checkpoints/2026-09-13-bounded-knowledge-retrieval-checkpoint.md`
  (this file).
- `.hydra-framework/repo/knowledge/spaces/hydra-framework/problems.md`: P13,
  P14 and P15's `Resolution:` lines repointed at this record.

## Validation Performed

- `python3 .hydra-framework/scripts/hydra.py validate`: to be run at the end
  of this split session.
- The Phase 1 read-path measurements (per-query scan costs, the instrumented
  `route-prompt` run, the FTS5 static confirmations) are inlined in this
  record's own Validation section, moved from the sibling record where they
  were originally recorded.
- No test suite run this session: no production code changed, only task
  records, and this record has not started its own Phase 2.

## Remaining Work

Phases 2 through 4, as listed in the task record's Approved Plan. Blocked
until the sibling task's Phase 4 lands.

## Blockers

Blocked on `2026-09-13-scalable-incremental-knowledge-index`'s Phase 4
landing (see the task record's Readiness). Two standing obligations, not
additional blockers: the false FTS5 reporting stays live until Phase 3, and
Phase 3's fallback obligation (D11) applies if it does not land.

## Useful References

- P13, P14, P15 in `.hydra-framework/repo/knowledge/spaces/hydra-framework/problems.md`.
- Sibling record: `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-13-scalable-incremental-knowledge-index.md`.
- The superseded task's sections 3, 5 and 8:
  `git show d5b9db0^:.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-12-design-scalable-knowledge-freshness.md`.
- Architecture caps: `.hydra-framework/engine/src/hydra_engine/architecture.py:19-23`.

## Continuation Prompt

Start by reading `AI_SYSTEM.md`, this checkpoint, and the referenced task state. Continue from the current stage without relying on prior conversation history.

Confirm the sibling task's Phase 4 has landed before starting anything here. If it has not, this record stays blocked; do not begin Phase 2.
