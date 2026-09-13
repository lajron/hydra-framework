# Task: bounded-knowledge-retrieval

Status: active
Owner: milosdenic-dev-gmail-com
Created: 2026-09-13
Updated: 2026-09-13

## Goal

Stop every knowledge query from loading and scanning the whole corpus in
Python, and cut the per-prompt Git fingerprint cost to what correctness
actually requires. Three recorded problems, all confirmed by measurement in
the shared Phase 1 design session:

- **P13**: every query materializes and scans the whole corpus in Python.
- **P14**: the CLI reports an FTS5 index that is never built.
- **P15**: every routed prompt runs three whole-repository Git fingerprints
  where two would do.

P14 is deliberately not fixed as a standalone label change. Building the real
index (P13) makes the existing message true; patching the message first is
churn that this work reverts. The condition on that decision is in D11.

Split out of `2026-09-13-scalable-incremental-knowledge-index` on 2026-09-13.
That record's single design session (its Phase 1) grew from four phases to
seven and absorbed this read-path scope alongside its own write-path scope
(P12). That was scope creep for one task record, not for the work itself:
each problem is independently confirmed and independently resolvable, so this
record now owns P13, P14 and P15 and the sibling record owns P12 only. See
that record's Step State for the split rationale and its Validation section
for the Phase 1 measurement method, which this split does not repeat.

A query should ask the database a question and get back the rows that match,
which is what the superseded design's section 5 required and what was never
built.

### Out of scope, deliberately

The public signatures and return shapes of `search()`; the ranking semantics,
which are preserved exactly rather than replaced (D10); the fingerprint,
guard and delta logic in `knowledge/freshness.py` itself (validated, fast,
correct) -- only its call sites change; the v3 schema and the existing
`documents` / `knowledge_objects` / `knowledge_relations` columns and indices,
which are added to but not altered.

## Confirmed Decisions

Moved verbatim from `2026-09-13-scalable-incremental-knowledge-index`:
D7a, D8, D9, D10, D11. Phase references below are renumbered for this
record; the decision labels themselves are unchanged and are the labels
`problems.md`'s P13/P14/P15 resolutions and the sibling record cite.

### D7a: The clean-read path is this task's core problem (P13)

The four clean-read section 8 gates are not caused by the publication layer
that the sibling task addresses. On a `Fresh` cache hit, `search()` reads the
whole `documents` table into Python and scans it by hand. The database holds
no index that any part of a query uses: its only query is `SELECT * FROM
documents ORDER BY rowid`. It is a file format, not a query engine.

Per-query cost, measured on synthetic corpora, 3 warmups + 15 samples,
median:

| documents | `_load_documents` | `exact_matches` | `substring_search` | per-query total |
| ---: | ---: | ---: | ---: | ---: |
| 320 | ~2.7 ms | 1.48 ms | 1.08 ms | ~6 ms |
| 1,000 | ~8 ms | 4.67 ms | 3.29 ms | ~18 ms |
| 10,000 | 83.24 ms | 46.41 ms | 35.24 ms | ~187 ms |

Plus `cache_state`'s own `SELECT path, content_id` row scan, 20.83 ms at 10k.
Linear in corpus size, independent of how many documents match.

This is the per-prompt path: `route-prompt` is wired to `UserPromptSubmit` in
`.claude/settings.json`, so it runs on every prompt. At this repository's 403
documents it is about 6 ms and invisible, which is why it shipped. It is a
cliff approached at constant speed, not a bug that bites.

The remaining roughly 500 ms of the measured 692 ms engine clean read at 10k
(see the sibling record's D7 gate table) is in provider hydration and the
fingerprints, and is not attributed here because it cannot be attributed
without a real governed fixture. Phase 4 measures it.

Phase 3 fixes the corpus-scan half of this. Recorded as P13.

### D8: Three Git fingerprints per prompt, where two are required (P15)

Instrumenting `freshness.fingerprint` and running one real `route-prompt` on
this repository reports `fingerprint(git) calls=3 total=45.0ms`. The callers
are `index_cache.cache_state` (via `search_index._cache_state`),
`index_cache.capture_stamp` pinning the read, and `capture_stamp` again for
the closing revalidation.

The third is a genuine independent second observation and the correctness
contract in section 3 requires it: it is what proves nothing moved during the
operation. The first two ask the same question microseconds apart and share
nothing.

At 403 documents this is 45 ms of Git against about 6 ms of index work,
making it currently the largest single component of a clean routed prompt
here, ahead of everything P13 describes.

Ordering constraint that makes this less trivial than it looks: the stamp
must be captured *after* any self-heal rebuild the search triggers, which is
why both `route_prompt._route_once` and `context_providers` capture it below
the search rather than at the top. The shared value therefore cannot simply
be hoisted; `cache_state` must return the fingerprint it computed, and the
stamp must reuse it only on the path where no rebuild intervened.

Phase 2 fixes this.

### D9: A clean read should not scan every row to prove freshness

`cache_state` computes the delta by reading `path, content_id` for every row
(20.83 ms at 10k) and comparing against the fingerprint map entry by entry.
That comparison is inherently whole-corpus, but the common case does not need
it: almost every read finds nothing changed.

Store an aggregate digest of the fingerprint map in `meta` alongside the
generation, written in the same transaction. A clean read then reads one
row, compares one string, and returns `Fresh` without touching `documents` at
all. Only a mismatch pays for the full row scan to compute the actual delta,
which is exactly when the corpus really did change and a rebuild is about to
happen anyway.

Phase 2 does this together with D8, since both are the freshness layer.

**Ownership of the write-path change this requires (decided 2026-09-13):**
this decision needs the same-transaction meta write that `index_cache.py`'s
write transactions perform, and the sibling task
(`2026-09-13-scalable-incremental-knowledge-index`) owns that file through
its own Phase 2 to 4. Two ways to land it were considered: the sibling task lays
the digest row down now as part of its transaction work, or this task
modifies the write path later, in the same phase where it already has to
touch those same transaction functions to add FTS5 table maintenance
(Phase 3, D10/D11).

Decided: **this task modifies the write path later, in Phase 2**, not the
sibling task. Reason: this task already has to re-open
`index_cache.py`'s transaction functions in Phase 3 to make every write also
maintain the FTS5 table (see the Readiness ordering dependency below); adding
the digest write in Phase 2, in the same file, ahead of that, is one
coordinated set of touches to that file rather than two. The sibling task
does not compute or consume a fingerprint map at all -- `freshness.py` and its
callers are entirely this task's concern -- so having it write a row for a
value it cannot compute would mean carrying a speculative, unused parameter
through its transaction API for phases 3 and 4 before this task exists to
call it. That is more total change than touching the transaction functions
once, in the task that owns the value being written.

The sibling record's D9 pointer states the same decision so neither record
drifts from the other.

### D10: FTS5 narrows candidates; ranking semantics are preserved exactly (P13)

The superseded design's section 5 requires preserving "exact selector,
substring hit count, path-route channel, rank, graph count and the
deterministic tie-break `(channel tier, rank, -graph_count, hydra_id, path)`".
`search()`'s return shape is also a KEEP-UNCHANGED constraint of this task.

So FTS5 is used as a **candidate filter, not as a ranker**. Build an FTS5
table over the same text `substring_search` concatenates today, trigram
tokenizer where the host supports it. A query matches it to get the small set
of documents containing any query term, then computes the existing channel,
rank and graph count over that narrowed set in Python, unchanged, and applies
the existing `sorted_results` tie-break.

Explicitly not bm25. Replacing the ranking function would change which
results come back and in what order, which is a behavior change wearing a
performance change's clothes, and would invalidate every existing ranking
test.

The exact-selector path (`exact_matches`) is separately indexed: it resolves
`hydra_id`, aliases and path directly, and the slug lookups it currently
recomputes for every document on every query become a small persisted lookup
table maintained in the same write transaction.

Substring scan stays as the fallback for a host SQLite without FTS5, which is
the case `probe_sqlite_features` genuinely exists to detect.

### D11: P14's false FTS5 reporting is fixed by building the index, not by editing the message

`commands/knowledge.py:93-98` prints `(FTS5 trigram)` and `:140` prints
`lexical=fts5-trigram` from a flag that actually means "this host's SQLite
supports FTS5". No FTS5 table has ever existed on real data: the only
`CREATE VIRTUAL TABLE` statements in the engine are in
`probe_sqlite_features`'s throwaway `:memory:` probe. This misreporting is
why P13 survived: every operator check reported a trigram full-text index.

Decided 2026-09-13 with the task requester: do not patch the label first.
Phase 3 builds the index, which makes the message true, and then makes the
reported mode reflect what was actually built rather than what the host is
capable of.

The condition on that decision: if Phase 3 is dropped, deferred, or fails its
acceptance, the label fix becomes required standalone work before this task
completes. A tool reporting a capability it does not have is worse than one
reporting its fallback honestly, and this task is not allowed to end leaving
that in place.

## Approved Plan

Four phases, continuing the numbering of a design phase this task shares
with its sibling. Each ends at a clean stopping point with its own acceptance
check, followed by a checkpoint and a stopped session. Do not start a phase
before its predecessor's acceptance passes.

Phase 1 (design) is the shared session recorded in the sibling task; this
record's own executable phases are 2 and 3, with 4 as the benchmark. The
former phase numbers 5 and 6 from the pre-split record map to phases 2 and 3
here.

### Phase 1: design (shared with the sibling task)

Already complete, in the sibling record's Phase 1. Confirmed P13, P14 and
P15, and recorded D7a, D8, D9, D10 and D11. Not repeated here; see the
sibling record's Validation section for the measurement method.

### Phase 2: bounded freshness checking (P15, D8, D9)

Scope: `knowledge/index_cache.py`, `knowledge/freshness.py`'s call sites (not
its logic), `knowledge/context_providers.py` and `cli/route_prompt.py`.

- Compute the pinning fingerprint once per operation and share it between
  `cache_state` and `capture_stamp`, respecting the ordering constraint in
  D8: the share is only valid on the path where no self-heal rebuild
  intervened between the two. The closing revalidation stays a genuinely
  independent second Git read and is not shared with anything.
- Write an aggregate digest of the fingerprint map into `meta` in the same
  transaction as the generation, and give `cache_state` a fast path that
  returns `Fresh` after one row read instead of scanning `documents` (D9).
  This is the write-path change D9's ownership note above assigns to this
  task, not the sibling task.

Acceptance: the instrumented `route-prompt` probe from Phase 1 reports
`fingerprint(git) calls=2` on this repository, down from 3, with the closing
revalidation still present and still a real Git call; a test proving the
shared fingerprint is *not* reused across a self-heal rebuild; a test proving
the aggregate-digest fast path and the full row-scan path classify
identically across added, modified, deleted and reverted documents; full
unit suite, `selftest` and `validate` all pass.

### Phase 3: real lexical index (P13, P14, D10, D11)

Scope: `knowledge/index_cache.py`, `knowledge/search_index.py`,
`commands/knowledge.py`.

- Create an FTS5 table over the same concatenated text `substring_search`
  builds today, trigram tokenizer where available, maintained inside the
  same transactions as `documents` on both the full-rebuild and incremental
  paths. Those transactions are stable by this point because the sibling
  task's Phase 4 has already landed (see Readiness).
- Add the persisted slug and identifier lookups the exact-selector path
  needs, so `exact_matches` stops recomputing `slugify` over every document
  per query.
- `search()` queries FTS5 to narrow candidates, then computes channel, rank,
  graph count and the tie-break over the narrowed set with the existing
  code, unchanged (D10). Substring scan remains the fallback when the host
  SQLite lacks FTS5.
- Make `commands/knowledge.py` report the mode actually built rather than
  the host capability (D11).

Acceptance: a differential test asserting that for a corpus of governed
documents and a set of queries covering exact-id, exact-path, exact-slug,
path-route and plain substring channels, the FTS5-narrowed path returns
**byte-identical** `SearchResult` lists to the current whole-corpus scan,
including order; a test that forces `fts5=False` and proves the substring
fallback still produces those same lists; a test asserting the reported mode
matches what the index contains; full unit suite, `selftest` and `validate`
all pass.

### Phase 4: benchmark (read half)

Re-run the section 8 methodology: correctness-gated, 5 warmups + 30 samples,
1k and 10k disposable Git fixtures built with `mktemp -d` outside this
checkout, nearest-rank p95, the same split between the in-process `engine`
harness and the CLI subprocess harness. Measure the four clean-read gates
(engine clean p50/p95, CLI clean p50/p95). The two write-path gates
(full rebuild, single-document incremental) are the sibling task's Phase 5
to measure, not this one.

Also re-measure, on this repository rather than the fixture, the per-prompt
`route-prompt` cost before and after, since that is the number that
describes daily use and no section 8 gate covers it. This is a before/after
delta specific to this task's changes (D8's fingerprint count, D9's fast
path, D10's FTS5 narrowing), taken against the same real `route-prompt`
invocation Phase 1 already ran once.

Acceptance: each of the four clean-read gates reported with a measured
number and an explicit met or missed verdict. No gate is claimed met without
a measurement. Correctness fixtures pass before any latency figure is
allowed to select anything. The before/after `route-prompt` measurement is
reported even though no section 8 gate covers it. This task completes only
once the numbers support the claims made.

## Current Stage

Complete. Phases 2, 3 and 4 all landed on branch `bounded-knowledge-retrieval`
(this task's readiness blocker on the sibling task's Phase 4 was verified
lifted before starting: the sibling task and its own write-path
follow-up (`bounded-write-path-freshness-cost`) had both already been
completed and folded into `problems.md`, evidenced by `git log` showing
`4499edb` and `7ef193c`/`e3632f1` landed before this session began).
See "Completion Summary" below for what was actually done, measured, and
what remains.

## Readiness

Status: blocked

- Branch or workspace assumptions: branch `knowledge-freshness-scalable-cache`,
  shared with the sibling task. The repository's own `core.hooksPath` is
  `.hydra-framework/hooks`; benchmark fixtures are disposable repositories
  with no hooks installed.
- Relevant canonical docs: `AI_SYSTEM.md`;
  `.hydra-framework/core/placement-rules.md`;
  `.hydra-framework/repo/knowledge/spaces/hydra-framework/problems.md` (P13,
  P14, P15); `.hydra-framework/capabilities/workflows/task-lifecycle.md`;
  `.hydra-framework/core/agent-writing.md`. The superseded task's sections 3
  (correctness contract), 5 (retained decisions) and 8 (benchmark contract)
  are recoverable at
  `git show d5b9db0^:.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-12-design-scalable-knowledge-freshness.md`.
  The sibling record,
  `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-13-scalable-incremental-knowledge-index.md`,
  for the write-path decisions (D1-D6, D7, D7b) this task's Phase 2 and 3
  build on top of.
- Required dependencies, services, generated artifacts, or private local requirements:
  Python 3.12.3, Git 2.43.0, SQLite 3.45.1, all present. The
  published index lives under `.hydra-framework.local/index/`, which is
  private and disposable; deleting it is always safe because every read
  degrades to canonical source mode. Phase 4 needs roughly 1 GB of free space
  under the system temp directory for the 10k fixture.
- Blockers and assumptions: **blocked on the sibling task's Phase 4
  landing.** This task's Phase 2 and Phase 3 both modify
  `index_cache.py`'s write transaction functions (to add the aggregate
  fingerprint digest and the FTS5 maintenance respectively), which is the
  same code the sibling task's Phases 2 to 4 are actively changing. Starting
  before that lands means building on a transaction shape that is still
  moving. Not blocked on anything else. Assumes SQLite WAL snapshot
  isolation and FTS5 availability on the host SQLite, with the substring
  fallback covering the case where FTS5 is absent (D10).
- Expected validation command or evidence: `python3 -m unittest discover -s
  .hydra-framework/engine/tests/unit -p "test_*.py"` run from
  `.hydra-framework/engine`, plus `python3 .hydra-framework/scripts/hydra.py
  selftest` and `python3 .hydra-framework/scripts/hydra.py validate`, all
  passing; plus the Phase 4 benchmark matrix with a met or missed verdict on
  each of the four clean-read gates, plus the before/after `route-prompt`
  measurement.

## Step State

- Active step: none. All four phases are complete.
- Next step: none for this task record. `.hydra-framework.local/index/` may
  need one full rebuild after this lands (schema bump to v4 forces it
  automatically on the next read; see Phase 3 below).
- Completed steps: Phase 2 (bounded freshness checking, D8/D9), Phase 3
  (real FTS5 lexical index, D10/D11), Phase 4 (read-path benchmark).
- Superseded or skipped steps: none.

## Changed Files

- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-13-bounded-knowledge-retrieval.md`
  (new, this record).
- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/checkpoints/2026-09-13-bounded-knowledge-retrieval-checkpoint.md`
  (new).
- `.hydra-framework/repo/knowledge/spaces/hydra-framework/problems.md`:
  repointed the `Resolution:` lines of P13, P14 and P15 at this record.

Planned, not yet touched:

- `.hydra-framework/engine/src/hydra_engine/knowledge/index_cache.py` (phases 2, 3)
- `.hydra-framework/engine/src/hydra_engine/knowledge/search_index.py` (phase 3)
- `.hydra-framework/engine/src/hydra_engine/knowledge/context_providers.py` (phase 2)
- `.hydra-framework/engine/src/hydra_engine/cli/route_prompt.py` (phase 2)
- `.hydra-framework/engine/src/hydra_engine/commands/knowledge.py` (phase 3)
- the corresponding `tests/unit/` modules for each of the above

Size risk to watch, per the caps in `architecture.py:19-23`: `search_index.py`
is at 395 of 400 lines before this work starts, and phase 3 adds to it. New
code goes into `index_cache.py` where it can, and any genuinely new module is
a deliberate decision recorded in that phase's checkpoint, not an accident
discovered by `validate`.

## Validation

- Phase 1 measurement, 2026-09-13, run in the shared design session recorded
  in the sibling task. Machine: Linux 7.0.0-31-generic, AMD Ryzen 7 7730U
  with Radeon Graphics, 16 CPUs, Python 3.12.3, SQLite 3.45.1. This is a
  diagnostic probe, not the section 8 harness: it has no governed Git
  fixture and no correctness gate. The section 8 matrix for this task's
  scope is Phase 4.
- `cache_state`'s delta row scan: p50 20.83 ms, p95 21.16 ms.
  `_load_documents`: p50 83.24 ms, p95 94.67 ms. `substring_search` over the
  materialized corpus: p50 35.85 ms, p95 46.43 ms.
- `probe_sqlite_features`: p50 0.35 ms. Called up to three times per
  `search()` and not a cost worth addressing on its own.
- Per-query Python scan cost across corpus sizes, 3 warmups + 15 samples,
  median, synthetic `SearchDocument` lists, query "how do I checkpoint a
  task record": at 320 documents `exact_matches` 1.48 ms, `substring_search`
  1.08 ms, `_with_explicit_path_docs` 0.04 ms; at 1,000 4.67 / 3.29 / 0.12 ms;
  at 10,000 46.41 / 35.24 / 1.17 ms. Linear in corpus size.
- One real `route-prompt` on this repository (403 documents), with
  `freshness.fingerprint`, `index_cache.cache_state` and
  `search_index._load_documents` instrumented:
  `fingerprint(git) calls=3 total=45.0ms | cache_state calls=1 |
  _load_documents calls=1 rows=403`. Command:
  `hydra.py route-prompt --prompt "how do I checkpoint a task record"`. This
  is the baseline Phase 4's before/after measurement compares against.
- Static confirmation that no FTS5 index exists on real data:
  `grep -rn "VIRTUAL TABLE" --include=*.py
  .hydra-framework/engine/src/hydra_engine/` returns only
  `knowledge/search_index.py:69` and `:72`, both inside
  `probe_sqlite_features`'s throwaway `:memory:` connection.
  `index_cache.create_index_tables` creates `documents` and `meta` only;
  `storage.write_sqlite_store` creates `knowledge_objects`,
  `knowledge_relations` and six B-tree indices, none of them full-text.
- Static confirmation of the misreporting: `commands/knowledge.py:93-98` sets
  `mode` to `"FTS5 trigram"` from `features.trigram` and prints it as the
  index's mode; `:140` prints `lexical=fts5-trigram` from the same flag. The
  flag is set by `probe_sqlite_features`, which reports host capability.
- `python3 .hydra-framework/scripts/hydra.py validate`: run at the end of the
  shared Phase 1, result recorded in the sibling task's Phase 1 checkpoint.

## Blockers

None. The sibling task's blocker was verified lifted (see Current Stage).

Remaining, not blocking completion:

- The engine-clean 10k read gate's p50 (83.96ms) misses its 50ms target
  (p95, 88.45ms, meets the 100ms target). Profiling attributes the residual
  cost entirely to `freshness.fingerprint`'s per-tracked-path
  `is_governed_path`/`pathlib` overhead on the benchmark fixture's file
  count, not to anything this task's phases touched -- `freshness.py`'s
  internals are this task's explicit out-of-scope boundary (D8/D9 changed
  only its call sites). If this gate needs to be met, it is a new,
  separately-scoped problem against `freshness.fingerprint` itself, not a
  reopening of P13/this task's scope.

Not blockers, recorded so they are not rediscovered:

- This record was split out of a single design session that grew from four
  phases to seven. That is not scope creep by drift: each problem this
  record owns is confirmed, measured, and has its own entry in
  `problems.md`, so the findings survive independently of either task
  record's lifecycle.

## Continuation Notes

- Running state: none. No background processes, no dev servers, no extra
  worktrees.
- Resume check: not applicable; this record is complete.

## Completion Summary (2026-09-13)

### Phase 2: bounded freshness checking (P15/R14, D8/D9)

Files: `knowledge/freshness.py` (`fingerprint_digest`), `knowledge/index_cache.py`
(`_write_fingerprint_digest`, `cache_state` fast path), `cli/route_prompt.py`
(`_route_once` now calls `search_index.search_for_context_provider`), plus
`tests/unit/cli/test_route_prompt.py` and
`tests/unit/knowledge/test_index_cache.py`.

- D8: `route_prompt._route_once` reuses the settled `Fresh` cache-state
  fingerprint as its opening `OperationStamp` (`stamp_from_fresh`, already
  built for D20) instead of an independent `capture_stamp` read, falling back
  to `capture_stamp` only when the search did not answer from `Fresh` sqlite.
  The closing revalidation in `command_route_prompt` is untouched -- still a
  genuinely independent second read.
- D9: `_write_fingerprint_digest` writes an aggregate digest of the
  `documents` table's `(path, content_id)` pairs into `meta` in the same
  transaction as the generation (both `rebuild_index` and
  `apply_index_delta`). `cache_state` compares that stored digest against
  `fingerprint_digest(current)`; a match returns `Fresh` after one `meta`
  row, never touching `documents`. Any mismatch, including a missing digest
  from a pre-existing index, falls back to the original full row scan
  unchanged.
- Tests added: `FingerprintDigestFastPathTests` (clean/added/modified/
  deleted/reverted all classify identically on both paths; the fast path
  never calls the full-scan helper on a clean repository) in
  `test_index_cache.py`; `test_clean_repository_costs_exactly_two_git_fingerprint_reads`
  and an updated `test_publication_change_midoperation_reruns` in
  `test_route_prompt.py`. The "not reused across a self-heal rebuild" proof
  is the existing D20 test `test_incremental_update_settling_fresh_shares_final_state_as_stamp`
  in `test_search_index.py`, which `route_prompt` now shares by construction
  (it calls the same `search_for_context_provider`).
- Measured on this repository: `fingerprint(git) calls=2 total=31.0ms`, down
  from `calls=3 total=45.0ms` (Phase 1 baseline).

### Phase 3: real lexical index (P13/R12, P14/R13, D10/D11)

Files: new `knowledge/lexical_index.py` (FTS5 table + exact-selector lookup
tables) and `tests/unit/knowledge/test_lexical_index.py`; `knowledge/index_cache.py`
(`_reset_index_tables` drops the new tables too); `knowledge/search_index.py`
(`SCHEMA_VERSION` bumped v3->v4, `_narrowed_documents`, `lexical_mode`, write
paths call `lexical_index.write_rows`/`delete_rows_for_keys`); `commands/knowledge.py`
(both report sites use `search_index.lexical_mode`); plus
`tests/unit/knowledge/test_search_index.py`.

A genuinely new module was needed rather than fitting inside `index_cache.py`
or `search_index.py`: both were within 30-80 lines of the 400-line cap before
this phase, and the new FTS5/lookup-table logic is a distinct, cohesive unit.
`lexical_index.py` is 119 lines; `index_cache.py` and `search_index.py` stayed
under the cap throughout (see `wc -l` in Validation below).

- FTS5 table `documents_fts` (trigram tokenizer), plus `document_ids`,
  `document_paths`, `document_slugs` lookup tables, all maintained inside the
  same write transactions as `documents` on both `rebuild_index` and
  `apply_index_delta`.
- `search()`'s `_narrowed_documents` narrows to a small candidate set via
  these tables (only when the published index's stored `trigram` meta flag
  is `yes`; otherwise returns `None` and the caller falls back to the
  original `_load_documents` whole-corpus read, unchanged), then runs the
  existing, unmodified `exact_matches`/`substring_search`/`sorted_results`
  over that narrowed set. Channel, rank, graph count, and the tie-break are
  untouched.
- `commands/knowledge.py` reports `search_index.lexical_mode(local)`, which
  reads the published index's own `meta.trigram` row, not a fresh
  host-capability probe.
- Differential tests added (`LexicalNarrowingDifferentialTests` in
  `test_search_index.py`): narrowed vs. whole-corpus-scan agreement across
  exact-id, exact-path, exact-slug, path-route and substring queries
  (byte-identical `SearchResult` lists, same order); a forced-no-FTS5 build
  matches both; reported mode matches what was actually built, with and
  without trigram, and with no index yet. Unit tests for
  `lexical_index.py` itself (9 tests) cover every table's write/narrow/
  delete path directly.

### Phase 4: read-path benchmark

New harness `validation/knowledge-v3/read_path_benchmark.py`, mirroring
`write_path_benchmark.py`'s conventions (disposable `mktemp -d` Git fixtures
outside this checkout, a correctness gate before any latency figure counts,
5 warmups + 30 samples, nearest-rank p50/p95). Correctness gates passed at
both 1,000 and 10,000 documents before any benchmark ran.

Measured on Linux 7.0.0-31-generic, AMD Ryzen 7 7730U, Python 3.12.3, SQLite
3.45.1 (same machine as the Phase 1 finding):

| Gate | p50 | p95 | Target | Verdict |
| --- | ---: | ---: | --- | --- |
| engine clean, 1,000 docs | 21.51 ms | 24.76 ms | p50<=50, p95<=100 | met |
| engine clean, 10,000 docs | 83.96 ms | 88.45 ms | p50<=50, p95<=100 | **missed** (p50 only) |
| CLI clean, 1,000 docs | 200.29 ms | 214.03 ms | p50<=300, p95<=400 | met |
| CLI clean, 10,000 docs | 295.72 ms | 321.17 ms | p50<=300, p95<=400 | met |

Three of four gates fully met. The engine-10k gate's p95 is met; only p50
misses, by 34ms, against a pre-fix baseline of p50 692.82ms at the same
scale -- roughly an 8x improvement, not a full pass. See Blockers for why
this is not attributed to this task's changes.

Before/after `route-prompt` measurement on this repository (403 documents),
same command as the Phase 1 probe
(`hydra.py route-prompt --prompt "how do I checkpoint a task record"`):
`fingerprint(git) calls=3 total=45.0ms` before, `calls=2 total=31.0ms` after.

### Validation run at completion

- `PYTHONPATH=.hydra-framework/engine/src python3 -m unittest discover -s
  .hydra-framework/engine/tests/unit -p "test_*.py"` (run from
  `.hydra-framework/engine`): 1475 tests, all passed.
- `python3 .hydra-framework/scripts/hydra.py selftest`: 1633 tests, all
  passed.
- `python3 .hydra-framework/scripts/hydra.py validate`: `Hydra validate: ok`
  (only pre-existing provider-compatibility and telemetry-volume advisory
  notes, unrelated to this work).
- `wc -l` at completion: `index_cache.py` 369, `search_index.py` 382,
  `lexical_index.py` 119, `commands/knowledge.py` 308 -- all under the
  400-line cap.
- `python3 .hydra-framework/validation/knowledge-v3/read_path_benchmark.py
  gate --size 1000|10000`: both passed (correctness gate, run before any
  benchmark).

### Outcome

P13, P14 and P15 moved from `problems.md`'s Open section to Resolved as R12,
R13 and R14 respectively, each recording its own measured evidence. This task
record and its checkpoint are removed on completion per
`hydra.py task complete`; this section is their durable archive.
