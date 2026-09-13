# Task: scalable-incremental-knowledge-index

Status: active
Owner: milosdenic-dev-gmail-com
Created: 2026-09-13
Updated: 2026-09-13

## Goal

Make a single-document knowledge-index update cost O(changed rows), not
O(corpus). Problem P12
(`.hydra-framework/repo/knowledge/spaces/hydra-framework/problems.md`) records
that at 10,000 governed documents, editing exactly one document costs p50
11544 ms / p95 12042 ms to reach the published index, against a section 8 gate
of p95 <= 100 ms.

Two structural causes, both addressed here:

1. The published index is a set of immutable versioned SQLite files behind an
   atomic pointer, so every write copies the whole database
   (`index_cache.update_index` -> `source_conn.backup(conn)` ->
   `ports/sqlite_db.publish_versioned`).
2. The incremental code path re-does whole-corpus canonical work regardless of
   how small the delta is.

### Split from this record's read-path scope (2026-09-13)

This record's Phase 1 design session also confirmed three read-path problems
-- P13 (every query scans the whole corpus in Python), P14 (the CLI reports
an FTS5 index that is never built), and P15 (three Git fingerprints per
prompt where two would do) -- and, in one session, grew this record's plan
from four phases to seven to cover them. That was scope creep for a single
task record: this record now keeps only the write path (P12), and the
read-path work moved to a new sibling record,
`.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-13-bounded-knowledge-retrieval.md`,
which owns P13, P14 and P15 and decisions D7a, D8, D9, D10 and D11 (the
pre-split record's Phases 5 and 6 map to that record's Phases 2 and 3). That
record's Phase 3 starts only after this record's Phase 4 lands, because it
adds FTS5 tables that every write transaction must maintain (see Readiness).

### Out of scope, deliberately

The fingerprint, guard and delta logic in `knowledge/freshness.py` (validated,
fast, correct); the v3 schema and the existing `documents` /
`knowledge_objects` / `knowledge_relations` columns and indices, which are
added to but not altered; the public signatures and return shape of
`build_index()`; the quiescence lock around multi-file governed writes in
`commands/knowledge_migration.py`; the read path in its entirety, now owned
by `bounded-knowledge-retrieval` (`search()`'s signature and return shape,
its ranking semantics, and the FTS5 work of D10).

## Confirmed Decisions

### D1: P12's stated root cause exists but its recorded percentage conflated three terms

P12 attributes the incremental cost to the full-database `backup()` copy. That
copy is real and worth removing, but the Phase 1 prose incorrectly called the
copy "roughly 7%" by adding the complete publication step and the digest
rewrite together. Against the recorded 10k p50 of 11544.09 ms, the three exact
ratios are: `backup()` alone 71.99 / 11544.09 = 0.62%; complete
`publish_versioned` 628.64 / 11544.09 = 5.45%; and complete publication plus
the 186.34 ms digest rewrite 814.98 / 11544.09 = 7.06%. None is the dominant
term.

Measured in-process on this machine (Linux 7.0.0-31-generic, AMD Ryzen 7 7730U,
16 CPUs, Python 3.12.3, SQLite 3.45.1) against a synthetic 10,000-row
`documents` table built with the shipped v3 schema, 2 KB bodies, 42.1 MB
published file, 2 warmups + 10 samples:

| Component of `update_index` at 10k | p50 | p95 |
| --- | ---: | ---: |
| `publish_versioned` with full `backup()` copy, fsync and replace | 628.64 ms | 692.71 ms |
| `documents_from_connection` + `_corpus_digest` (the meta rewrite) | 186.34 ms | 196.37 ms |
| Entire SQLite publication half | ~815 ms | ~889 ms |
| Measured single-document incremental (P12 evidence) | 11544 ms | 12042 ms |

`backup()` on its own measured p50 71.99 ms; the remaining 556.65 ms of
`publish_versioned` is the fsync, `os.replace` and pointer write of a 42 MB
file. The original section 8 fixture's database was recorded at about 20 MB,
but there is no retained probe artifact from which to infer how its copy or
fsync time scaled; the earlier claim that its term was "likely about half" is
removed as unsupported.

Consequence: subtracting only the measured backup predicts about 11.47 s;
subtracting the complete versioned-publication step predicts about 10.92 s;
subtracting publication plus digest predicts about 10.73 s. These are
attribution estimates, not new benchmarks. The gate is 100 ms. The WAL change
is necessary and correct, and it is not sufficient.

### D2: The dominant cost is delta-blind canonical re-collection

`search_index._update_index`'s `apply_update` does three whole-corpus
operations on every single-document update. Established by reading the code;
the 10.73 s attribution residual from D1 is consistent with it, and the full-rebuild
figure corroborates it (full rebuild measured 15910 ms p50 at 10k while its
entire SQLite write measured 235 ms, leaving 15675.49 ms of canonical
collection).

- `index_cache.write_changed_knowledge_rows(conn, paths, changed)` calls
  `storage.build_knowledge_store(paths)`
  (`.hydra-framework/engine/src/hydra_engine/knowledge/storage.py:215`), which
  walks every node and `read_unit`s every governed unit in the tree, then
  discards all but the changed ones. At 10k units this is 10k file reads and
  YAML parses per single-document update.
- `collect_search_documents(..., only_paths=changed)` still runs
  `discovery.collect_hydra_objects(resolver_paths)`,
  `_discover_nodes_or_empty(paths)` and `_canonical_search_files(paths.root)`
  over the whole corpus. `only_paths` filters after the walk, so it saves the
  per-file read and parse for unchanged files but none of the discovery.
- `_write_meta(conn, _documents_from_connection(conn), ...)` materializes every
  document row out of SQLite and digests all of them (186 ms at 10k, per D1).

### D3: The `digest` meta row is written on every update and never read

`index_cache.load_documents` compares `meta['digest']` only when
`expected_digest` is not `None`. The only caller,
`search_index._load_documents(state.db_path)` in `search()`, never passes it.
The single call site that does is
`.hydra-framework/engine/tests/unit/knowledge/test_search_index.py:164`.

So the 186.34 ms p50 `documents_from_connection` + `_corpus_digest` term on
every incremental update buys nothing in production. Phase 4 removes the
`digest` row and the `expected_digest` parameter on both rebuild and
incremental paths: retaining a digest written only on full rebuild would leave
false metadata after the first incremental update, and a test-only caller does
not justify it. The persisted-document ordering test remains, but stops passing
a digest.

### D4: Full rebuild mutates the live file in place; nothing is ever replaced

The original design's Phase 2 moved to immutable versioned publication because
replacing a fixed `knowledge.db` via `os.replace()` gave live WAL readers no
portable old-or-new boundary: the `-wal` and `-shm` sidecars are keyed by path,
not by inode, so a reader holding the old inode can pair the old main database
with the new WAL's shared-memory index.

Keeping temp-file-then-atomic-replace for full rebuild on a persistent WAL file
would reopen exactly that hazard. It is therefore not kept. Full rebuild
becomes one transaction on the live file: delete all rows, insert all rows,
bump the generation, commit. Crash safety comes from WAL rollback of an
uncommitted transaction rather than from the temp file, which is a stronger
guarantee than the replace path offered, and no published file is ever
replaced out from under a reader.

This is a deliberate deviation from the instruction to keep full rebuild on
temp-file-then-atomic-replace, decided 2026-09-13 with the task requester. The
reason is that the instruction and the reader-safety property it is meant to
preserve are in direct conflict once the file is persistent.

Free-page churn from delete-all-then-insert-all is handled with a
`wal_checkpoint(TRUNCATE)` after a full rebuild. A database that cannot be
opened at all (corrupt, or schema mismatch) is deleted with its sidecars and
recreated: at that point it is unusable, so there is no valid reader to
protect.

### D5: Identity becomes a generation value in the database, not a file path

With one persistent file, `OperationStamp.publication` stops carrying identity:
the path never changes. A `meta` row `generation`, set to a fresh
`uuid4().hex` inside the same transaction as every write (full rebuild and
incremental alike), carries it instead.

A fresh UUID rather than an incrementing counter, because a counter is
ambiguous across recreation: a stamp captured at version 1, followed by the
database being deleted and rebuilt to version 1, compares equal while the
index in fact moved. That is precisely the class of event the correctness
contract exists to catch. A UUID costs the same single row read and has no
such case.

`OperationStamp` keeps its `corpus` and `publication` fields (`publication` is
now the live database path, still used by callers to open the snapshot) and
gains `generation: str | None = None`. The default keeps the existing
positional two-argument construction in tests working.

### D6: Readers stop using `immutable=1`

`ports/sqlite_db.open_published` currently opens
`?mode=ro&immutable=1`, which tells SQLite the file will never change and
authorizes it to skip WAL and locking entirely. That is incompatible with a
file that is mutated in place. Readers move to `?mode=ro` on the live file and
rely on WAL snapshot isolation for a consistent view for the life of the read.
`storage.SqliteKnowledgeStore.open` already uses `?mode=ro`, but the earlier
claim that it needs no change is false: it does not explicitly begin a read
transaction and it has no deterministic close path. Phase 3 routes it through
the same read opener, begins the WAL read snapshot before any query, and closes
the snapshot in `finally`/context-manager exit so a long-lived connection does
not pin the WAL indefinitely.

### D7: Five of the six section 8 gates were targeted; full rebuild is not

P12 states that all six section 8 gates miss "as a result" of the publication
layer. They do not share one cause. The scope below reflects the measured
causes, not P12's attribution.

| Gate | Measured at 10k | Gate | Targeted where |
| --- | ---: | ---: | --- |
| engine clean p50 | 692.82 ms | 50 ms | `bounded-knowledge-retrieval` (P13, P15) |
| engine clean p95 | 703.59 ms | 100 ms | `bounded-knowledge-retrieval` (P13, P15) |
| CLI clean p50 | 1373.75 ms | 300 ms | `bounded-knowledge-retrieval` (P13, P15) |
| CLI clean p95 | 1409.92 ms | 400 ms | `bounded-knowledge-retrieval` (P13, P15) |
| full rebuild p95 | 16437.83 ms | 5000 ms | **not targeted, outcome unknown** |
| single-document incremental p95 | 12042.02 ms | 100 ms | here, phases 2 to 4 (P12) |

Full rebuild is not targeted. Its measured 16437 ms contains only 235 ms of
SQLite write (Phase 1 probe), leaving about 15.6 s of canonical reading and
parsing. A full rebuild legitimately must read every file, so Phase 4's
delta-scoping does nothing for it. There is an unmeasured possibility that the
rebuild reads the corpus three times through
`collect_hydra_objects`, `_canonical_search_files` and `build_knowledge_store`
without sharing results, in which case collapsing those passes could move it
toward the gate. That is a hypothesis, not a plan, and no phase here commits to
it. Phase 5 reports the measured outcome either way.

The four clean-read gates and their P13/P15 causes are recorded in full as
D7a and D8 in `bounded-knowledge-retrieval`; not repeated here since this
record no longer owns that work.

### D7b: The stamp change is a measured-benchmark obligation, not a claimed win or regression

`capture_stamp` today resolves identity by reading the small
`knowledge-current.json` pointer. After D5 it opens the database and reads one
`meta` row. The earlier claim that this is a small regression was not measured
and is therefore not confirmed; its direction and size are unknown until the
benchmark. The design accepts the generation read as a correctness cost, not
as a read-path optimization. Phase 5 records its contribution without claiming
a direction, and `bounded-knowledge-retrieval`'s later benchmark observes it
again in its own before/after `route-prompt` measurement.

### D9's write-path ownership: decided against this task (read-path, P13)

`bounded-knowledge-retrieval`'s D9 needs an aggregate digest of the
fingerprint map written into `meta` alongside the generation, in the same
transaction this task's Phase 2 introduces. Decided 2026-09-13: **this task
does not lay that row down.** `bounded-knowledge-retrieval` modifies the
write path itself, in its own Phase 2, in the same touch where it already has
to re-open these same transaction functions to add FTS5 table maintenance
(its Phase 3). Adding an unused digest-write parameter here now, ahead of the
task that computes and consumes it, would carry speculative API surface
through this task's Phases 3 and 4 for no caller. See
`bounded-knowledge-retrieval`'s D9 for the full reasoning; this note exists so
neither record drifts from the other.

### D12: Phase 2 is additive; Phase 3 is the one cutover/removal boundary

The old plan asked Phase 2 to remove `publish_versioned` and the pointer while
also forbidding that phase from touching `search_index.py`, whose current
`build_index` and `_update_index` call those APIs. Those requirements cannot
both leave a coherent stopping point. Phase 2 therefore adds and tests the
persistent-file primitives in `ports/sqlite_db.py` and the final
knowledge-specific transaction APIs in `knowledge/index_cache.py`, while the
legacy pointer/versioned functions remain temporarily unchanged. Phase 3
rewires every caller in one cutover and then removes the legacy functions,
pointer JSON support, `json`/publication-id helpers, and their tests. No caller
may use both publication models after Phase 3.

The final knowledge-cache API shape produced by the two phases is:

```python
# ports/sqlite_db.py
def live_db_path(index_dir: Path) -> Path
def open_published(db_path: Path) -> sqlite3.Connection | None
def discard_database(db_path: Path) -> None
def truncate_wal(conn: sqlite3.Connection) -> bool

# knowledge/index_cache.py
def default_db_path(local: Path) -> Path | None
def rebuild_index(
    local: Path,
    populate: Callable[[sqlite3.Connection], None],
) -> Path
def apply_index_delta(
    paths,
    local: Path,
    *,
    expected_generation: str,
    expected_fingerprint: dict[str, str],
    apply_update: Callable[[sqlite3.Connection, dict[str, str]], None],
) -> Path
```

`live_db_path(index_dir)` always returns `index_dir / "knowledge.db"` without
claiming it exists. `default_db_path(local)` returns that path only when it is a
regular file; validity remains `cache_state`'s job. `open_published` opens
`file:...?...mode=ro`, sets the existing 5000 ms busy timeout, explicitly
executes `BEGIN` to pin a WAL read snapshot, probes `PRAGMA schema_version`, and
returns `None` after closing on any `OSError`/`sqlite3.DatabaseError`.

### D13: SQLite owns normal writer serialization; generation rejects a stale queued writer

There is no advisory lock around a valid database. `connect()` establishes WAL
mode and `BEGIN IMMEDIATE` obtains SQLite's single writer reservation. Every
incremental transaction then reads `meta.generation` after that reservation is
held and compares it with `expected_generation`; a mismatch raises
`PublicationMovedError(ValueError)` before any row mutation. It recomputes the
governed fingerprint and compares it with `expected_fingerprint`; a mismatch
raises `CorpusMovedError(ValueError)` before the callback. These subclasses fit
the existing `search()` catch at `search_index.py:216` and make the losing
operation rerun from canonical source rather than apply a delta derived from an
older publication. The next operation may repair the cache.

The exact successful incremental boundary is: open fixed file -> `BEGIN
IMMEDIATE` -> verify generation -> recompute/verify fingerprint -> invoke the
delta callback -> recompute the fingerprint again and require it still equals
the pre-callback value -> write a fresh `uuid4().hex` generation row -> `COMMIT`
-> close. `apply_update` receives the verified fingerprint so document
`content_id` values and the delta decision use the same map. A callback,
either fingerprint, SQL, commit, busy-timeout, or generation-check failure rolls back
and closes; the old generation and all old rows remain observable. The
`change` parameter currently accepted but unused at `index_cache.py:134` is
deleted rather than carried forward.

A full rebuild uses the same SQLite writer boundary: open -> `BEGIN IMMEDIATE`
-> drop the four index-owned tables if present -> recreate the unchanged v3
tables and indices -> invoke `populate` -> write a fresh generation -> `COMMIT`
-> best-effort `wal_checkpoint(TRUNCATE)` -> close. A busy checkpoint is not a
failed rebuild: committed readers and writers are already correct, the WAL is
retained, and a later checkpoint may truncate it. A transaction/commit failure
rolls back and leaves the prior generation visible.

The one place SQLite cannot supply a lock is a main file it cannot parse.
Automatic corrupt-file recreation therefore uses the existing `ports.lock`
only as a zero-timeout recovery mutex at
`<local>/locks/knowledge-index-recovery.lock`; it is not acquired on any normal
write. The holder rechecks the database after taking the mutex, discards the
main file plus `-wal`/`-shm` only if it is still invalid, recreates it, and then
enters the normal SQLite transaction. A contender or unavailable lock raises a
`ValueError` caught by the caller and degrades that operation to source mode.
This prevents two recovery attempts from replacing/unlinking each other's newly
valid database.

### D14: `generation` is a required meta row; tables and columns stay v3

No table or column changes are required. `documents`, `meta`,
`knowledge_objects`, `knowledge_relations`, and all six current locator/edge
indices retain their exact definitions. `SCHEMA_VERSION` remains
`hydra-framework.knowledge-store.v3`; the publication mechanism changes, not
the document/locator row schema. `meta` gains one required value row,
`("generation", uuid4().hex)`, written only by the transaction wrapper.
`cache_state`, `read_generation`, and `capture_stamp` treat a missing, empty, or
unreadable generation as an absent cache. That makes an old fixed-path v3 file
rebuild once, while old versioned files and `knowledge-current.json` are simply
ignored after cutover.

A valid SQLite file with missing/wrong tables, columns, schema meta, or
generation is rebuilt by transactional `DROP TABLE IF EXISTS`/`CREATE`, not
deleted. Only a file that SQLite itself cannot open/query uses the corrupt-file
recovery path in D13. The aggregate `digest` row is removed under D3; full
rebuild meta after this task contains `schema`, `fts5`, `trigram`,
`command_ids`, and `generation` only. The sibling task may later add its own
aggregate fingerprint row under its D9; this task neither reserves nor writes
that row.

### D15: A published reader is an explicit, deterministically closed WAL snapshot

`open_published` begins a read transaction before returning. Short-lived
callers (`cache_state` at `index_cache.py:99`, `command_ids_match` at `:122`,
`read_generation`/`capture_stamp`, and `load_documents` at `:207`) retain their
existing `finally: conn.close()` discipline. `SqliteKnowledgeStore.open` at
`storage.py:315-319` changes to use `open_published`; `SqliteKnowledgeStore`
gains `close()`, and `KnowledgeSnapshot` gains `close`, `__enter__`, and
`__exit__`.

The two owners of cached snapshots close them on every return and exception:
`context_providers.run_context_providers` (current open at
`context_providers.py:304-333`, use through `:395-398`) uses a context manager,
including recursive canonical fallbacks; `cli.route_prompt._route_once`
(current open/use at `route_prompt.py:59-87`) uses a context manager around
routing and binding reads. A caller-supplied `ProviderRequest.knowledge_snapshot`
remains caller-owned and is wrapped with `contextlib.nullcontext`, so nested
provider calls do not close it. This makes D6's “consistent for the life of the
read” literal and prevents abandoned read transactions from indefinitely
pinning WAL pages.

### D16: Phase 4 optimizes local deltas; structural or ambiguous deltas rebuild

The 10k P12 fixture changes one Knowledge-unit Markdown file. Phase 4 makes
that class O(changed files/rows) without pretending every governed file has
only local effects. A delta is eligible for row-level apply only when every
added/modified/deleted path can be mapped independently. It falls back to
`build_index` before opening an incremental transaction when any path is:

- `repo/knowledge/spaces.yaml`, `space.yaml`, or `node.yaml`, because node
  membership, inheritance, packages, routes, keywords, and descendant search
  rows can change;
- a `*.view.yaml` declaration, because view composition is graph-structural and
  the first optimized path need not duplicate view validation in a delta
  collector;
- a deleted YAML file, whose old bytes are unavailable to distinguish a direct
  envelope from an object sidecar;
- an added/modified YAML sidecar with schema
  `hydra-framework.object-sidecar.v1`, because one envelope can add, remove, or
  retarget multiple object paths not represented by the sidecar's own path;
- outside the governed set or otherwise not safely attributable by the
  per-path collectors.

Added/modified direct Markdown/text/Python/shell documents, Knowledge units,
and direct non-sidecar/non-node/non-view YAML envelopes are locally eligible. A rename is the
existing `CorpusDelta` pair `(deleted old path, added new path)`; a Markdown
unit rename remains incremental, while a YAML rename conservatively rebuilds.
This fallback is correctness behavior, not a performance gate. The benchmark's
single-unit mutation remains on the incremental branch.

Node discovery remains one whole node-catalog pass per eligible delta because
owning-node and inherited routing fields require it; it is O(nodes), not
O(units). What Phase 4 removes is the unit-wide `discover_node_unit_paths` /
`read_unit` pass, the all-object `collect_hydra_objects` pass, and the
`_canonical_search_files` recursive corpus walk. The earlier Scope sentence
implying node discovery itself becomes changed-path-only is corrected.

### D17: Phase 4 introduces one `knowledge/index_collection.py` boundary

The live sizes are `search_index.py` 395/400, `storage.py` 400/400, and
`context_providers.py` 398/400. Adding delta collectors to either first two
files cannot pass architecture check 1, and adding another import to
`search_index.py` without moving its current collection dependencies risks the
fan-out cap. Phase 4 therefore creates
`knowledge/index_collection.py` with its mirror
`tests/unit/knowledge/test_index_collection.py`.

It owns `SearchDocument`, full and delta search-document collection, and full
and delta `StoredKnowledgeObject` collection. The current collection helpers at
`search_index.py:78-132` and `:298-365` move there; the current
`storage.build_knowledge_store` at `storage.py:215-242` moves there.
`search_index` re-exports `SearchDocument` so existing imports and the public
`build_index`/search result shape do not change. Moving the markdown and node
catalog dependencies with those helpers gives `search_index` import headroom
before it adds the one `index_collection` edge. `storage.py` continues to own
the store protocol/models, hydration, SQLite writer, and SQLite reader.

### D18: Delta replacement is defined as a logical-table differential

“Byte-equivalent in content” cannot mean identical SQLite file bytes: WAL page
layout, free pages, rowids, and the deliberately fresh generation UUID differ.
Acceptance compares sorted logical rows from `documents`,
`knowledge_objects`, `knowledge_relations`, and `meta` excluding only
`generation`. With D3's digest deletion, no stale/ignored meta row needs another
exception.

The final locator mutation API is:

```python
def replace_changed_knowledge_rows(
    conn: sqlite3.Connection,
    removed_paths: tuple[str, ...],
    replacements: tuple[StoredKnowledgeObject, ...],
) -> None
```

It reads old ids for all removed paths, computes replacement ids, deletes all
old outgoing edges, deletes incoming edges only for ids absent from the
replacement set, deletes old objects by path, then inserts replacement objects
and their outgoing edges. This preserves incoming edges for a rename whose
Hydra id is unchanged, removes dangling incoming edges for a true deletion or
id change, and handles modified paths in the same transaction. Empty path
tuples are no-ops and never produce `IN ()` SQL. Document replacement likewise
deletes `documents.path IN removed_paths` and inserts the changed documents;
commands are untouched because command-id changes already force full rebuild.

### D19: Phase 5 preserves the section 8 operation boundary, not just SQL timing

The historical section 8 numbers are evidence from 2026-09-13, not a retained
benchmark program: their fixture/method/result description survives in Git,
but the scratch harness and Phase 1 component probe do not. They are therefore
not independently reproducible byte-for-byte in this planning session. Static
inspection confirms the exact measured paths still exist unchanged; Phase 5
must record its generator/harness path or inline its complete script/commit so
future numbers are reproducible.

The timed engine operation remains the real `run_context_providers` call. For a
full-rebuild sample, remove the disposable fixture's live database and
sidecars before the timer, then time one provider operation that self-builds,
searches, hydrates the selected node/unit, and performs closing stamp
revalidation. For an incremental sample, start from a fresh index, alternate
one selected unit between two byte-distinct valid bodies, then time one provider
operation that detects and commits that delta and completes the same hydration
and revalidation. Fixture mutation and precondition checks occur before the
timer; all production work triggered by the provider call is timed. This is the
same whole-operation boundary as the historical matrix, while the Phase 1 SQL
probe remains diagnostic only.

## Approved Plan

Five phases. Each ends at a clean stopping point with its own acceptance
check, followed by a checkpoint and a stopped session. Do not start a phase
before its predecessor's acceptance passes.

All five phases are the write path (P12). The sibling task
`bounded-knowledge-retrieval` covers the read path (P13, P14, P15) in its own
phases 2 to 4; its Phase 3 adds FTS5 tables that every write transaction must
maintain, so it starts only after this task's Phase 4 lands (see that
record's Readiness).

### Phase 1: design (this record)

Read the current code, confirm or correct P12's diagnosis, record the design.

Acceptance: this record states a diagnosis backed by measurement, names every
file the plan touches, and `hydra.py validate` passes.

### Phase 2: persistent WAL store and generation counter

Scope: only `ports/sqlite_db.py`, `knowledge/index_cache.py`, and their mirror
tests. This phase is additive under D12; it does not change the active
`search_index` call graph and therefore leaves the complete unit suite green.

Current sites and what the final replacement must supply:

- `sqlite_db.py:33` names the pointer; `:119-127` validates version names;
  `:130-145` writes/fsyncs/replaces the pointer; `:147-166` resolves it;
  `:183-195` lists stale versions; and `:198-242` builds, fsyncs, renames,
  repoints, and cleans a complete file. Phase 2 leaves these temporarily for
  Phase 3 callers, adds D12's live-path/read/discard/checkpoint primitives, and
  updates the module documentation so the two publication models are clearly
  marked transitional.
- `sqlite_db.py:49-57` already supplies WAL writer connections. Harden it so a
  failure in either PRAGMA closes the partially opened connection before
  re-raising. `connect_existing` at `:60-73` must likewise close a connection
  on its failure path rather than return `None` while leaking it.
- `sqlite_db.py:169-180` is the current immutable read opener. Its final
  `mode=ro` + explicit `BEGIN` behavior is added now; rollback-journal
  versioned files remain readable during the transition, so this does not
  break Phase 3 callers.
- `index_cache.py:58-59` resolves the pointer; `:67-83` stamps the pointer path;
  and `:134-151` copies a whole publication before calling its closure. Leave
  those active functions until Phase 3, but add `rebuild_index`,
  `apply_index_delta`, generation helpers, and the transaction errors exactly
  as D12-D14 define. `apply_index_delta` is tested directly in this phase.
- `index_cache.py:154-159` and `storage.write_sqlite_store` currently create all
  four index-owned tables. Add an index-cache reset helper that drops
  `knowledge_relations`, `knowledge_objects`, `documents`, then `meta` in that
  dependency order and recreates only `documents`/`meta`; the caller's existing
  `write_sqlite_store` recreates the locator tables and indices inside the same
  transaction.

Transaction and error behavior:

- `rebuild_index` first tries the fixed path normally. On a valid database it
  runs the full D13 transaction without any external lock. On
  `sqlite3.DatabaseError` before `BEGIN`, it follows only the recovery branch
  in D13, retries once, and otherwise propagates `ValueError`/SQLite failure.
  It never falls back to versioned publication.
- `apply_index_delta` refuses a missing/unopenable database, a missing/changed
  generation, or a moved fingerprint before invoking the callback. Any
  `BaseException` from the callback causes explicit rollback and is re-raised;
  `KeyboardInterrupt`/`SystemExit` are therefore covered, not accidentally
  committed by an `except Exception` boundary.
- The generation is written after all caller rows and before commit. A UUID is
  generated per attempted transaction, but becomes observable only if commit
  succeeds. A failed attempt may consume a UUID without changing database
  identity.
- Full-rebuild checkpoint is after commit. `truncate_wal` returns `True` only
  when SQLite reports `busy == 0`; `False` or a caught checkpoint error is
  recorded by the test seam but does not roll back or change the successful
  rebuild result.

Acceptance tests, all added to the two existing mirror files:

1. **Live path and read opener.** Create an index directory with no database;
   assert `live_db_path` returns exactly `knowledge.db`. Build a WAL database,
   open it through `open_published`, assert a write statement fails read-only,
   assert `PRAGMA query_only`/journal behavior is compatible with WAL, and
   close it. Point at a missing and a garbage file and assert `None`, with a
   patched connection verifying no leaked handle.
2. **Successful full rebuild.** Seed all four tables plus meta/generation A;
   call `rebuild_index` with replacement rows; assert the same fixed path still
   exists, journal mode is WAL, old rows are gone, all replacement rows and
   indices exist, generation B is non-empty and differs from A, and no pointer,
   versioned, or temp file was created.
3. **Concurrent reader across both writes.** Seed generation A and begin a read
   through `open_published`; read generation/data A. Commit an incremental
   delta B, then a full rebuild C on separate writer connections while the read
   remains open. Assert the held connection returns A after each commit; a new
   reader after B returns B, and a new reader after C returns C. Assert the
   full-rebuild checkpoint reports busy while A is pinned and succeeds after A
   closes.
4. **Queued stale writer.** Seed A. Open writer 1 with `BEGIN IMMEDIATE`; start
   writer 2 in a thread/process using expected generation A so it waits inside
   SQLite. Commit writer 1 as B. Assert writer 2 then acquires the writer lock,
   reads B, raises `PublicationMovedError` before its callback, and leaves B's
   rows/generation unchanged. This proves SQLite, not an advisory lock,
   serializes normal writers.
5. **Fingerprint movement.** Seed A and capture fingerprint F1. First change one
   governed file before calling `apply_index_delta`; assert `CorpusMovedError`,
   callback not called, and generation/rows A unchanged. Then start from A/F1,
   mutate a governed file from inside the callback; assert the post-callback
   comparison rolls back every callback row and again leaves A intact.
6. **Callback rollback.** Seed A; callback deletes/inserts rows and raises a
   sentinel `RuntimeError`. Assert the error propagates and a new read sees the
   complete A rows/generation, not any partial mutation.
7. **Hard interruption.** Seed A. Spawn a subprocess that begins the real
   incremental transaction, mutates rows, then calls `os._exit` from the
   callback before generation/commit. After exit, open the database in the
   parent and assert A's rows/generation are intact and `PRAGMA integrity_check`
   returns `ok`.
8. **Corrupt recreation.** Put non-SQLite bytes at the fixed path with dummy
   sidecars; run `rebuild_index`; assert the recovery mutex branch removes them,
   creates a valid WAL v3 database and generation, and leaves no recovery lock
   held. Hold the recovery mutex in another process and assert a simultaneous
   attempt fails to source-safe `ValueError` without modifying the bytes.
9. **Schema/meta reset.** Seed a valid SQLite file with wrong tables, wrong
   columns, and no generation; rebuild and assert the same path now has exactly
   the v3 table/column/index contract plus required meta rows. This path must
   not call `discard_database`.
10. **Legacy isolation.** Run every existing `VersionedPublicationTests` case
    unchanged during Phase 2 to prove the additive primitives did not alter the
    still-active pointer model.

Existing-test disposition for Phase 2:

- `ports/test_sqlite_db.py:24-111` (`connect`, `connect_existing`,
  `rebuild_atomically`) stays and must pass unchanged; add the connection-close
  assertions above. `:134-247` versioned tests stay unchanged until Phase 3.
- `knowledge/test_index_cache.py:15-80` stays unchanged because the active
  pointer and two-field stamp have not cut over; add a separate class for the
  new fixed-path transaction APIs.
- All `test_search_index.py`, `test_snapshot.py`,
  `test_context_providers.py`, `test_route_prompt.py`, `test_storage.py`,
  `commands/test_knowledge.py`, and `commands/test_knowledge_migration.py`
  tests are left alone and must pass. There is no accepted-failure list.

Validation: run the two focused mirror modules, then the full unit discovery
from `.hydra-framework/engine`. Checkpoint and stop; do not wire Phase 3.

### Phase 3: wiring

Scope: cut over `knowledge/search_index.py`, `knowledge/snapshot.py`,
`knowledge/context_providers.py`, `cli/route_prompt.py`, and the read opener in
`knowledge/storage.py`; remove the temporary legacy surface from
`ports/sqlite_db.py`/`knowledge/index_cache.py`; update only tests whose asserted
publication identity/lifetime changes. Whole-corpus delta collection is still
present until Phase 4.

Exact current call sites and rewiring:

- `search_index.py:63` continues re-exporting `default_db_path`, whose Phase 3
  implementation now returns the fixed file. Production callers at
  `commands/knowledge.py:85,92` need only absent/present detection and a display
  path; `commands/knowledge_migration.py:36-38` needs absent -> full build and
  present -> warm-through-search. Neither needs a publication id.
- `search_index.build_index` at `:135-151` keeps its public signature and
  `(len(docs), features)` return. Its `populate` stops creating
  `documents`/`meta` itself because `rebuild_index` owns reset/create, continues
  to call `storage.write_sqlite_store`, `_write_documents`, and `_write_meta`,
  and passes the closure to `index_cache.rebuild_index`. Remove the unused
  `uuid` import at `:9` and `index_cache.publish_versioned` call at `:150`.
- `_cache_state` at `:169-173` keeps its signature. `cache_state` now requires
  generation and returns `Fresh(db_path, fingerprint, generation)` or
  `Stale(db_path, fingerprint, delta, generation)`.
- `_update_index` at `:176-192` changes to
  `def _update_index(paths, resolver_paths, local, command_ids, state:
  index_cache.Stale) -> Path`. It derives `changed`/`removed` from
  `state.delta`, and calls `apply_index_delta(expected_generation=state.generation,
  expected_fingerprint=state.fingerprint, ...)`. The closure remains
  whole-corpus in Phase 3; only publication/transaction semantics change.
- `search()` at `:208-217` passes the whole `Stale` state. Any recovery,
  generation, fingerprint, busy-timeout, SQL, or callback error follows the
  existing catch to `SourceOnly("index-update-failed")`; no partial cache result
  is returned. After a successful write, the existing second `_cache_state`
  must see the newly committed generation and current rows before SQLite is
  used.
- `_load_documents` at `:291-295` still returns the same ordered document list
  or `None`. Digest removal is Phase 4, so its optional digest parameter remains
  for this one phase.
- `index_cache.capture_stamp` at current `:67-83` becomes
  `OperationStamp(corpus, db_path, generation)`. If guard/fingerprint/file/open/
  generation fails it returns `OperationStamp({}, None, None)` and the caller is
  source-only. `OperationStamp.generation: str | None = None` preserves current
  two-positional-argument test construction.
- `context_providers.py:304-333` opens the cached `KnowledgeSnapshot`; `:374-393`
  revalidates. Equality now detects generation movement while publication path
  stays fixed. Add `contextlib`; set `snapshot_scope` to
  `contextlib.nullcontext()` for caller-owned/no snapshot and to the locally
  opened `KnowledgeSnapshot` otherwise; wrap the existing provider/return body
  in `with snapshot_scope`. Use D15's ownership rule so every `return` at
  `:359`, `:393`, `:395` closes only the locally opened snapshot. Replace the
  two overlapping explanatory blocks at current `:305-308` and `:316-319`
  with one concise ownership/pinning comment; this funds the context-manager
  lines under the current 398/400 cap without moving behavior.
- `route_prompt.py:58-87` opens and consumes its snapshot; `:99-108`
  revalidates. Wrap each cached/source snapshot in a context manager. Preserve
  the existing rule that unrelated `ValueError` creates a warning while
  `HydrationMismatch` triggers one complete source rerun.
- `storage.py:315-319` changes `SqliteKnowledgeStore.open` to call the shared
  `open_published`; implement it as `conn = open_published(db_path); return
  cls(conn) if conn is not None else None`, and add one-line `close()`. Replacing
  the current try/except body plus one import is line-count neutral at the
  current 400/400 cap. `snapshot.py:169-173` continues to
  return source mode for `source != "sqlite"`, raises `HydrationMismatch` if a
  requested SQLite snapshot cannot open, and adds D15's lifecycle methods.
- After all callers use the fixed APIs, delete `sqlite_db.py:33,119-166,183-242`
  (pointer/version functions), their `json` import and fsync helpers that have
  no remaining caller; delete the legacy `index_cache.update_index` at
  `:134-151` and legacy imports at `:14`. Keep generic `connect`,
  `connect_existing`, `rebuild_atomically`, `query_store_disabled`, and
  `source_manifest` because other stores call them.

Phase-boundary checks:

- Phase 2 already supplies the exact `rebuild_index`/`apply_index_delta`
  signatures, generation write, and WAL reader semantics used here; Phase 3
  must not invent a second transaction wrapper.
- Phase 3 deliberately retains `storage.build_knowledge_store`,
  `collect_search_documents(... only_paths=...)`, and the incremental digest
  rewrite. Its results are correct but still O(corpus); Phase 4 changes only
  what the already-atomic callback collects/writes.
- No FTS table or fingerprint aggregate is added. Those remain entirely in the
  sibling task.

Acceptance tests:

1. **Build cutover.** With no index, call public `build_index`; assert return
   shape unchanged, fixed `knowledge.db` exists in WAL mode, all four tables,
   indices and required meta/generation exist, and no pointer/version file is
   created. Run a second full build; assert the path is equal, generation
   differs, rows equal canonical state, and a reader pinned before the build
   still sees its old generation/rows.
2. **Incremental cutover.** Build, edit one governed document, call `search`;
   assert it returns SQLite results containing the edit, path is unchanged,
   generation changed, and a patched `source_conn.backup`, `publish_versioned`,
   and `os.replace` surface is absent/not called. Phase 4 parse-count
   performance is not asserted yet.
3. **Concurrent generation movement.** Arrange `_cache_state` to return stale A,
   commit B before `_update_index` obtains `BEGIN IMMEDIATE`, then run search.
   Assert the stale callback never mutates B, the observable result is a pure
   canonical-source rerun, and B remains valid for the next classification.
4. **Stamp identity.** Build generation A, capture two stamps and assert equal.
   Rebuild at the same path to B and assert `publication` paths equal,
   `generation` differs, and stamps differ. A governed edit changes `corpus`
   independently. Missing/corrupt/missing-generation databases yield the
   source stamp.
5. **Provider revalidation.** In both context-provider and route-prompt tests,
   patch the second stamp to `dataclasses.replace(real_stamp,
   generation="moved")` while keeping path/corpus. Assert exactly one forced
   source rerun and output identical to a pure source operation; this replaces
   the old fake-path movement seam.
6. **Snapshot pin/close.** Open cached snapshot A, perform multiple locator and
   relation reads while committing B, and assert all reads remain A. Exit the
   context; assert the underlying connection rejects further queries and a
   truncate checkpoint can complete. Pass a caller-owned snapshot into
   `run_context_providers` and assert it remains open afterward.
7. **All failure paths.** Force missing file between classification/open,
   corrupt SQL during state/read, busy writer timeout, rebuild callback error,
   hydration mismatch, and checkpoint busy. Assert each either preserves the
   prior committed generation or, for post-commit checkpoint busy, preserves
   the new one; observable operations return one canonical source result, never
   a cache/source mix.

Existing-test disposition for Phase 3:

- `ports/test_sqlite_db.py:134-247` is deleted as obsolete pointer/version
  mechanics and replaced by the persistent-publication tests from Phase 2.
  `:24-111` stays. Tests are removed because the APIs disappear, not weakened
  to accept both models.
- `knowledge/test_index_cache.py:26-28` changes “missing pointer” to “missing
  fixed file”; `:60-73` changes from publication-path inequality to equal path /
  unequal generation; `:49-58,75-80` otherwise stay.
- `knowledge/test_search_index.py:157-165` stays until Phase 4 digest deletion;
  `:167-175` changes from immutable DELETE journal to persistent WAL;
  `:177-186` replaces invalid-pointer setup with invalid fixed-database setup.
  `:188-346` stays semantically unchanged, with the new concurrency case added.
- `knowledge/test_snapshot.py:11-17` stays; add snapshot pin/close/ownership
  tests.
- `knowledge/test_context_providers.py:318-390` updates only the moved-stamp
  helper from path to generation and adds caller-owned close coverage. All
  selection/hydration assertions stay.
- `cli/test_route_prompt.py:237-279` updates only the moved-stamp helper from
  path to generation. All rendering/suppression tests stay.
- `knowledge/test_storage.py:64-123` stays, adds explicit closes where a store
  survives its `TemporaryDirectory`, and adds read-transaction close evidence.
- `commands/test_knowledge.py:204-259` and
  `commands/test_knowledge_migration.py:80-125` stay unchanged: their contract
  is absent/present, incremental-vs-rebuild selection, and source result, not
  the publication filename.

Validation: focused modules for all seven touched source files plus both
command caller tests; full unit discovery; `selftest`; `validate`; and
`git diff --check`. No expected failures. Checkpoint and stop.

### Phase 4: delta-scoped canonical collection

Scope: add D17's `knowledge/index_collection.py` and mirror test; move the
current full collectors out of `search_index.py`/`storage.py`; change
`index_cache.py`'s row replacement helpers and `search_index.py`'s delta
callback/branch selection. Do not touch snapshot/provider/CLI semantics or the
sibling task.

Exact current costs replaced:

- `index_cache.write_changed_knowledge_rows` at `index_cache.py:188-194`
  dynamically calls `storage.build_knowledge_store(paths)` and filters after
  `storage.py:222-240` has read every node, every unit, and every view. Replace
  it with D18's `replace_changed_knowledge_rows`; collection happens before the
  callback through `index_collection.collect_changed_knowledge_objects`.
- `index_cache.delete_knowledge_rows` at `:180-185` accepts one undifferentiated
  path tuple and deletes only outgoing edges. Remove it; D18's batched
  replacement handles modified/deleted/renamed ids and incoming-edge cleanup.
- `search_index.collect_search_documents` at `:78-128` calls
  `collect_hydra_objects`, discovers every node, and calls
  `_canonical_search_files`; `only_paths` filters only at `:107` and `:118`.
  Move it to `index_collection`; its delta branch iterates the sorted requested
  paths directly, calls `discovery.extract_hydra_object` only for each existing
  path, discovers nodes once, and never calls `collect_hydra_objects`,
  `object_document_paths`, `Path.rglob`, or `discover_node_unit_paths`.
- `_update_index` at `search_index.py:177-190` deletes old documents/locators,
  writes changed rows, then materializes every document at `:190`. Change it to
  classify D16 eligibility before `apply_index_delta`, collect replacement
  documents/locators for only added+modified paths, and perform both replacement
  sets inside the already-defined Phase 2 transaction.
- `_documents_from_connection` at `search_index.py:195-196`,
  `index_cache.documents_from_connection` at `:176-177`, the incremental
  `_write_meta` call at `search_index.py:190`, `_corpus_digest` at `:379-383`,
  `write_meta`'s document/digest arguments at `index_cache.py:166-173`, and
  `load_documents.expected_digest` at `:197-219` are removed under D3. Final
  signatures are `index_cache.write_meta(conn, command_ids, features, schema)`
  and `search_index._load_documents(db_path)`.

Collection and failure shape:

- `index_collection.delta_is_local(paths, resolver_paths, change) -> bool`
  implements D16. A parse/read error returns `False` so public search selects a
  full rebuild; it never partially applies the subset it understood.
- `collect_search_documents` keeps its existing public argument/return shape and
  full-build behavior. With `only_paths`, it accepts only paths already judged
  local; a missing file is skipped (deletion), an existing direct file produces
  at most one path document plus its direct envelope fields, and command rows
  are never regenerated.
- `collect_changed_knowledge_objects(paths, changed) -> tuple[...]` discovers
  nodes once, resolves each existing path to the deepest owning node, reads a
  unit only when the path is directly under that node's `units/*.md`, and emits
  no locator for ordinary state/overview/search-only files. YAML views and
  structural declarations are on D16's rebuild branch.
- Collection occurs after Phase 2's verified fingerprint is passed to the
  callback and before any delete. Any collection/parse error raises, causing
  rollback/source fallback; no subset commits.
- `removed_paths` is `deleted + modified`; `changed_paths` is `added + modified`.
  The two are sorted/deduplicated tuples. Empty added/modified or removed sets
  use no-op helpers, never dynamically constructed empty `IN` clauses.
- After an eligible delta commits, generation is the only meta row changed.
  `schema`, feature flags and command ids were validated before entering this
  branch. Structural/command/schema changes take full rebuild and rewrite all
  meta.

Cross-phase checks:

- The callback is still entirely inside Phase 2's `BEGIN IMMEDIATE`; documents,
  locator objects, relations, and generation commit or roll back together.
- The expected generation/fingerprint comparison occurs before collection, so
  a queued writer cannot delete rows using another writer's obsolete delta.
- Phase 3's readers keep one WAL snapshot; they may see all pre-delta rows and
  generation or all post-delta rows and generation, never the two mixed.
- Phase 5 mutates a unit Markdown file, which D16 explicitly classifies local;
  the timing therefore measures the intended delta path, not a fallback full
  rebuild.

Acceptance tests:

1. **Differential fixture.** Build a Git fixture containing two spaces, nested
   nodes, units with incoming/outgoing relations, a view, a sidecar-owned
   object, ordinary search files, and commands. For each case below, clone the
   same pre-change tree/database twice; apply the mutation to both; update one
   via public incremental search and the other via public full rebuild; compare
   D18's sorted logical rows and public search results.
2. **Add.** Add one valid unit under an existing node and commit neither tree.
   Assert the incremental database gains exactly one document and locator plus
   its outgoing relations, unchanged rows are identical, generation changes,
   and logical rows match rebuild.
3. **Modify.** Change body, title/relations and content id of one unit. Assert
   its old document/locator/outgoing edges are replaced, new incoming/outgoing
   queries match rebuild, unrelated rows unchanged, and only that unit parser is
   called.
4. **Delete.** Delete a unit targeted by an unchanged unit's relation. Assert
   its document/object/outgoing rows and all incoming edges to its vanished id
   are gone; unchanged objects remain; logical rows/results match rebuild.
5. **Rename with stable id.** Rename one unit Markdown path without changing its
   Hydra id. Assert old path rows disappear, new path rows exist, incoming edges
   to the stable id remain, no duplicate PK exists, and logical rows/results
   match rebuild.
6. **Rename with changed id.** Rename and change the id. Assert both old
   outgoing and incoming edges are removed, new rows/edges inserted, and no
   dangling old id remains.
7. **Zero/partial sets.** Exercise add-only, delete-only, and an explicitly empty
   helper call. Assert no SQL syntax error, no unintended row change, and one
   generation bump only for a real public update.
8. **Bounded work.** Build a 10k-unit/one-node fixture, modify one unit, patch
   `read_unit`, `collect_hydra_objects`, `object_document_paths`,
   `discover_node_unit_paths`, `_canonical_search_files`/`Path.rglob`, and
   `documents_from_connection`. Run the update; assert `read_unit` sees only the
   changed unit, node discovery occurs once, every forbidden whole-corpus helper
   is uncalled, and SQL changes only the expected document/object/edge/meta rows.
9. **Structural fallback.** Separately modify `spaces.yaml`, a `node.yaml`, an
   added/modified sidecar, and delete a YAML envelope. Patch `build_index` and
   `apply_index_delta`; assert exactly one full rebuild, zero delta apply, and
   results/logical rows match a clean rebuild in every case.
10. **Collection failure rollback.** Make a changed unit unreadable/invalid
    after classification but before callback collection. Assert the exception
    causes source-mode observable results and the prior database rows/generation
    remain wholly intact.
11. **Digest deletion.** Build and increment; assert no `digest` meta row exists
    after either operation, `_load_documents(db_path)` preserves rowid order,
    and no production or test call accepts/passes `expected_digest`.
12. **Command/schema behavior.** Change command ids and separately patch schema;
    assert both still choose full rebuild, not a delta that leaves meta stale.

Existing-test disposition for Phase 4:

- `knowledge/test_search_index.py:157-165` drops the digest argument but keeps
  its row-order assertion. `:236-248` and `:250-290` are strengthened to forbid
  whole-corpus helpers, not merely count `_document_for_path`; collection-unit
  assertions move to `test_index_collection.py` where the implementation now
  lives. Tests at `:331-336` for one node discovery move with the collector.
  All search/ranking/fallback/command/schema tests stay.
- `knowledge/test_storage.py:85-105` imports full collection from
  `index_collection` after the move but retains its in-memory/SQLite
  differential assertions. Hydration and SQL-reader tests stay. No test is
  deleted.
- `knowledge/test_index_cache.py` keeps every Phase 2/3 transaction and stamp
  test; add row-replacement cases for incoming/outgoing edge semantics and empty
  sets.
- Add `knowledge/test_index_collection.py` for full-vs-delta collection,
  structural classification, and bounded-work instrumentation. This is required
  by architecture's one-to-one test mirror.
- `ports/test_sqlite_db.py`, `knowledge/test_snapshot.py`,
  `knowledge/test_context_providers.py`, `cli/test_route_prompt.py`, and both
  command test modules are left alone; their Phase 3 semantics must remain
  green.

Validation: focused new/moved collector, cache, search and storage modules;
full unit discovery; `selftest`; `validate`; `git diff --check`. Checkpoint and
stop before benchmarking.

### Phase 5: benchmark (write half)

Scope: records and disposable fixtures/harness only. Do not change production
code in response to a result; a miss is reported and becomes a separately
planned follow-up. Do not measure or modify the sibling task's four read gates.

Fixture and harness contract:

- Run on the named reference machine and record kernel, CPU, logical CPUs,
  Python, Git, SQLite, filesystem type, free space, commit, and dirty diff.
  Refuse to compare against the historical matrix if production code differs
  from the Phase 4 checkpoint or unrelated load invalidates a run.
- Create a fresh `mktemp -d` outside this checkout with cleanup on exit. Build
  separate 1k and 10k Git repositories using the same fixed generator: copy the
  checkpointed engine source and shim; write minimal manifest/AI_SYSTEM,
  `spaces.yaml`, one `benchmark` space, one `benchmark/selected` node with
  state/overview, and exactly N valid block-style YAML Knowledge units under
  that node. Git-init/config/add/commit; install no hooks. Record exact governed
  overhead and database size rather than carrying forward the old 206+8/20 MB
  figures if they differ.
- Retain the harness as a tracked benchmark artifact if an existing canonical
  benchmark location is available by Phase 5; otherwise inline the complete
  generator/timing source and its sha256 in this record's Validation. Do not
  leave the only reproducible method in private scratch.
- Use `time.perf_counter_ns`. Five untimed warmups precede 30 measured samples
  for each fixture/operation. Sort milliseconds; p50 is the median of samples
  15 and 16, and nearest-rank p95 is rank `ceil(.95*30)=29` (zero-based index
  28). Report raw 30-sample vectors or a tracked artifact plus p50/p95.

Correctness gate before any timed result:

1. Build the fixed database; assert WAL, required tables/indices/meta, non-empty
   generation, no pointer/versioned files, and provider source `sqlite`.
2. On independent copies at both sizes, run unstaged modify, staged modify,
   add, delete, stable-id rename, and changed-id rename through the public
   provider operation. After each, assert D18 logical equality with a full
   rebuild, correct row counts/relations/search body, generation movement, and
   selected node/unit hydration.
3. Hold a read snapshot while incremental and full rebuild commits occur;
   assert it stays on its opening generation and a new reader sees each commit.
4. Kill an incremental subprocess before commit and assert prior rows/generation
   plus `integrity_check=ok`.
5. Trigger one structural YAML change and assert public behavior takes the full
   rebuild branch. If any correctness assertion fails, record the failure and
   do not calculate a latency verdict.

Timed full-rebuild series at each size:

- Before each sample, ensure canonical tree is unchanged and remove only the
  disposable fixture's `knowledge.db`, `-wal`, and `-shm`; absence/recovery work
  before the provider call is untimed.
- Start timer immediately before real in-process `run_context_providers` with a
  fixed request selecting `benchmark/selected`; stop after it returns, including
  fingerprinting, rebuild transaction/checkpoint, search, hydration, and final
  revalidation.
- Assert SQLite source, expected selected node/unit, correct row counts,
  generation, and logical snapshot after stopping the timer but before
  accepting the sample. A failed assertion invalidates the whole series.

Timed single-document incremental series at each size:

- Begin each sample with a fresh valid index. Before timing, alternate one
  selected unit between two same-size, byte-distinct, valid bodies and assert
  `_cache_state` would be stale without triggering a repair. Do not include the
  fixture write in the timer.
- Time the same real provider call. It must detect the one-file delta, commit
  documents/locators/relations/generation, search/hydrate, and revalidate before
  return.
- After timing, assert SQLite source, exactly one changed document/locator,
  expected content/body, generation changed once, no full rebuild fallback, and
  logical equality with the expected canonical state. Reset/prebuild outside
  the next timer as needed so every sample measures exactly one update.

Reporting/acceptance:

- Report 1k and 10k p50/p95 for both series. The two verdicts are 10k full
  rebuild p95 <= 5000 ms and 10k one-document incremental p95 <= 100 ms.
  State `met` or `missed` beside each exact number; no extrapolation or
  component probe substitutes for a whole-operation sample.
- Compare with historical values (full rebuild 15910.49/16437.83 ms,
  incremental 11544.09/12042.02 ms) only after noting any fixture/code/machine
  differences. Report speedup as secondary evidence, never as the gate.
- Measure generation capture separately only as a diagnostic for D7b; do not
  relabel it a clean-read gate. The sibling task owns clean engine/CLI p50/p95.
- Existing tests are not changed or deleted in this phase. Run full unit,
  `selftest`, `validate`, and `git diff --check` before recording final numbers.
  Complete the task only after both measured verdicts and all correctness/
  validation evidence are in this record; a legitimate full-rebuild miss does
  not erase successful P12 incremental work, but must be reported exactly.

## Current Stage

Phase 4 implementation is complete and its focused, full-unit, validation, and
whitespace checks pass. The required completed selftest result remains
unavailable: direct, detached, and PTY invocations are terminated at the
30-second boundary. This is a hard validation boundary: do not begin Phase 5
until a runner can complete `hydra.py selftest`. Its read-path findings (P13,
P14, P15) were split out to
`bounded-knowledge-retrieval` on 2026-09-13; this record now plans only the
write path in five phases. A records-only revalidation expanded Phases 2-5 and
added D12-D19 before implementation. Phase 2 added only the transitional WAL
primitives and transaction APIs; Phase 3 is next.

## Readiness

Status: ready

- Branch or workspace assumptions: branch `knowledge-freshness-scalable-cache`,
  HEAD `d5b9db0`. The working tree is intentionally not clean: before this
  planning pass it already contained the two task records/checkpoints, P12/P13-
  P15 edits, and a modified registry. `git diff` confirms all seven production
  files in this task remain byte-unchanged from HEAD. Preserve every unrelated
  dirty file. The repository's own `core.hooksPath` is
  `.hydra-framework/hooks`; benchmark fixtures are disposable repositories
  with no hooks installed.
- Relevant canonical docs: `AI_SYSTEM.md`;
  `.hydra-framework/core/placement-rules.md`;
  `.hydra-framework/repo/knowledge/spaces/hydra-framework/problems.md` (P12, and
  P5 for the related warm-read cost);
  `.hydra-framework/capabilities/workflows/task-lifecycle.md`;
  `.hydra-framework/core/agent-writing.md`. The superseded task's sections 3
  (correctness contract), 5 (retained decisions) and 8 (benchmark contract) are
  recoverable at
  `git show d5b9db0^:.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-12-design-scalable-knowledge-freshness.md`.
  The sibling record,
  `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-13-bounded-knowledge-retrieval.md`,
  for the read-path decisions (D7a, D8, D9, D10, D11) this task no longer
  carries.
- Required dependencies, services, generated artifacts, or private local requirements:
  Rechecked 2026-09-13: Linux 7.0.0-31-generic, AMD Ryzen 7 7730U, 16 logical
  CPUs, Python 3.12.3, Git 2.43.0, SQLite 3.45.1, all present. Checkout and
  `/tmp` are ext4 on the same local block filesystem, with about 312 GiB free.
  The
  published index lives under `.hydra-framework.local/index/`, which is private
  and disposable; deleting it is always safe because every read degrades to
  canonical source mode. It currently contains both historical
  `knowledge-<uuid>.db`/pointer files and a legacy `knowledge.db`; Phase 3's
  cutover ignores versioned artifacts and validates/rebuilds the fixed file.
  Phase 5 requires disposable space under the system temp directory; record
  actual consumption rather than relying on the earlier rough 1 GiB estimate.
- Blockers and assumptions: none blocking. SQLite WAL snapshot isolation and
  single-writer serialization are acceptance conditions in Phases 2-3, not
  assumptions. Network filesystems are unsupported for this cache: if
  `PRAGMA journal_mode=WAL` does not return `wal`, the write fails and the
  observable operation degrades to canonical source mode; the plan does not
  silently fall back to a weaker journal mode. The recovery-only mutex in D13
  must be available on the execution platform or corrupt-file recovery also
  degrades to source mode.
  This task's own execution has no ordering dependency on the sibling task;
  the dependency runs the other way, recorded in that record's Readiness.
- Expected validation command or evidence: `python3 -m unittest discover -s
  .hydra-framework/engine/tests/unit -p "test_*.py"` run from
  `.hydra-framework/engine`, plus `python3 .hydra-framework/scripts/hydra.py
  selftest` and `python3 .hydra-framework/scripts/hydra.py validate`, all
  passing; plus the Phase 5 benchmark matrix with a met or missed verdict on
  each of the two write-path section 8 gates (full rebuild, single-document
  incremental).

## Step State

- Active step: obtain a completed Phase 4 `hydra.py selftest` result.
- Next step: record that result, checkpoint the accepted Phase 4 boundary, and
  stop. Do not begin Phase 5 in this task continuation.
- Completed steps: Phase 4 implementation: collection moved to
  `knowledge/index_collection.py`; safe direct-path deltas use one node
  catalog pass and never walk the full corpus; structural/ambiguous changes
  rebuild; document and locator replacement is logical-differential; and the
  unused digest meta behavior is removed. Focused tests (38) and complete unit
  discovery (1441) pass, as do `validate` and `git diff --check`; no completed
  selftest result is claimed.
- Completed steps: Phase 3 accepted: `build_index` and incremental updates use
  the fixed-path WAL transaction APIs; pointer/version APIs and their obsolete
  tests are removed; generation participates in cache state and stamps;
  locally-owned provider/CLI snapshots close deterministically. Complete unit
  discovery passed (1438 tests), as did `validate` and `git diff --check`.
  Completed selftest evidence is unavailable because all recorded attempts hit
  the terminal's 30-second boundary.
- Completed steps: Phase 1. Read the current implementation; measured the
  publication layer and the read path (see Validation); corrected P12's root
  cause attribution (D1, D2); confirmed the never-read digest (D3); settled the
  full-rebuild write path against the WAL-reader hazard (D4); chose the
  generation identity (D5); found and recorded three further confirmed problems
  in the read path, P13, P14 and P15, and wrote all three into
  `.hydra-framework/repo/knowledge/spaces/hydra-framework/problems.md` so they
  survive record splitting and deletion; appended a dated correction to P12
  there rather than rewriting it. On 2026-09-13, after the same design
  session had widened this record's plan from four phases to seven, split the
  read-path decisions and phases (the former D7a, D8, D9, D10, D11 and
  phases 5 and 6) out into the new sibling record
  `bounded-knowledge-retrieval`, narrowing this record back to the write path
  and renumbering its remaining benchmark phase from 7 to 5. On 2026-09-13,
  re-read every Phase 2-5 source/mirror test and all direct production/test
  callers; corrected D1/D3/D6/D7b; added D12-D19; specified final APIs,
  transactions, failure paths, snapshot closure, structural fallbacks, logical
  differential semantics, every acceptance setup/operation/assertion, and
  per-phase existing-test disposition. No phase advanced.
- Superseded or skipped steps: the instruction to keep full rebuild on
  temp-file-then-atomic-replace is superseded by D4, agreed with the task
  requester on 2026-09-13. The originating four-phase instruction is superseded
  by this record's five-phase write-path plan; its phases 1, 2 and 3 map to
  phases 1, 2 and 3 here and its phase 4 maps to phase 5 here. Phase 4 here is
  write-path work that D1 and D2 showed to be necessary. The read-path work
  the design session added on 2026-09-13 (P13, P14, P15) is superseded here by
  the split into `bounded-knowledge-retrieval`; it is not superseded as work,
  only as a reason to keep it in this record. The separate "fix the FTS5
  label now" option was considered and rejected in favour of D11, now in the
  sibling record.
  The former Phase 2 instruction to remove the versioned API before its
  `search_index` callers could be changed is superseded by D12's additive Phase
  2 and single Phase 3 cutover. The former Phase 4 instruction to keep a stale
  full-rebuild-only `digest` row is superseded by D3/D14. The former claim that
  Phase 4 can add collection code directly to capped `search_index.py` and
  `storage.py` is superseded by D17's `index_collection.py` boundary.

## Changed Files

- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-13-scalable-incremental-knowledge-index.md`
  (edited, this record: narrowed to the write path, phases renumbered 1-5,
  read-path decisions and phases split out).
- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/checkpoints/2026-09-13-scalable-incremental-knowledge-index-checkpoint.md`
  (edited to match).
- `.hydra-framework/tasks/personal/milosdenic-dev-gmail-com/2026-09-13-bounded-knowledge-retrieval.md`
  (new sibling record) and its checkpoint (new).
- `.hydra-framework/repo/knowledge/spaces/hydra-framework/problems.md`: P13,
  P14 and P15's `Resolution:` lines repointed at `bounded-knowledge-retrieval`;
  P12's stays pointed at this record.

Planned, not yet touched:

- `.hydra-framework/engine/src/hydra_engine/ports/sqlite_db.py` (phase 2)
- `.hydra-framework/engine/src/hydra_engine/knowledge/index_cache.py` (phases 2, 4)
- `.hydra-framework/engine/src/hydra_engine/knowledge/search_index.py` (phases 3, 4)
- `.hydra-framework/engine/src/hydra_engine/knowledge/snapshot.py` (phase 3)
- `.hydra-framework/engine/src/hydra_engine/knowledge/context_providers.py` (phase 3)
- `.hydra-framework/engine/src/hydra_engine/cli/route_prompt.py` (phase 3)
- `.hydra-framework/engine/src/hydra_engine/knowledge/storage.py` (phases 3, 4)
- `.hydra-framework/engine/src/hydra_engine/knowledge/index_collection.py`
  (new, phase 4)
- the corresponding mirror tests, including new
  `tests/unit/knowledge/test_index_collection.py`, plus the two existing command
  caller tests named in Phase 3

Size risk is resolved in plan, not deferred: per `architecture.py:19-23`,
`search_index.py` is 395/400, `storage.py` 400/400, and
`context_providers.py` 398/400 before work starts. Phase 3 must make its close/
context-manager changes without net growth over the cap; Phase 4 moves
collection into D17's named module and mirror test. `index_cache.py` is 223
lines and has headroom for Phase 2 transaction ownership. No phase may raise a
  cap or create an unplanned module to make validation pass.

Phase 2 changed:

- `.hydra-framework/engine/src/hydra_engine/ports/sqlite_db.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/index_cache.py`
- their mirror tests `tests/unit/ports/test_sqlite_db.py` and
  `tests/unit/knowledge/test_index_cache.py`

Phase 3 changed:

- `.hydra-framework/engine/src/hydra_engine/ports/sqlite_db.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/index_cache.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/search_index.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/storage.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/snapshot.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/context_providers.py`
- `.hydra-framework/engine/src/hydra_engine/cli/route_prompt.py`
- `.hydra-framework/engine/tests/unit/ports/test_sqlite_db.py`
- `.hydra-framework/engine/tests/unit/knowledge/test_index_cache.py`
- `.hydra-framework/engine/tests/unit/knowledge/test_search_index.py`

Phase 4 changed:

- `.hydra-framework/engine/src/hydra_engine/knowledge/index_collection.py`
  (new full and delta collection boundary)
- `.hydra-framework/engine/src/hydra_engine/knowledge/index_cache.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/search_index.py`
- `.hydra-framework/engine/src/hydra_engine/knowledge/storage.py`
- `.hydra-framework/engine/tests/unit/knowledge/test_index_collection.py`
  (new mirror)
- `.hydra-framework/engine/tests/unit/knowledge/test_index_cache.py`
- `.hydra-framework/engine/tests/unit/knowledge/test_search_index.py`

## Validation

- Phase 1 measurement, 2026-09-13. Machine: Linux 7.0.0-31-generic, AMD Ryzen 7
  7730U with Radeon Graphics, 16 CPUs, Python 3.12.3, SQLite 3.45.1. Method:
  in-process probe against a synthetic `documents` table built through the
  shipped `index_cache.create_index_tables` / `search_index._write_documents` /
  `search_index._write_meta` path, 10,000 rows, about 2 KB bodies, 42.1 MB
  published file; 2 to 3 warmups, 10 to 25 samples, median for p50. This is a
  diagnostic probe, not the section 8 harness: it has no governed Git fixture
  and no correctness gate, so it attributes cost within the SQLite layer and
  deliberately claims nothing about end-to-end latency. The section 8 matrix is
  Phase 5.
- `publish_versioned` with a full `backup()` copy: p50 628.64 ms, p95 692.71 ms.
  `backup()` alone: p50 71.99 ms, p95 78.06 ms. A full publish of all 10,000
  rows from Python: 235 ms.
- `documents_from_connection` + `_corpus_digest`: p50 186.34 ms, p95 196.37 ms.
- Arithmetic recheck: backup p50 is 0.62% of 11544.09 ms; complete
  `publish_versioned` is 5.45%; publication plus digest is 7.06%. The earlier
  D1 wording attributed the last percentage to the copy and is corrected.
- The read-path measurements from this same Phase 1 session (`cache_state`'s
  delta row scan, `_load_documents`, `substring_search`, `probe_sqlite_features`,
  per-query scan cost across corpus sizes, the instrumented `route-prompt` run,
  and the FTS5 static confirmations) now live in `bounded-knowledge-retrieval`'s
  Validation section, since they back that record's D7a, D8, D9, D10 and D11
  rather than any decision kept here.
- Static confirmation that `meta['digest']` is never verified in production:
  `expected_digest` is defaulted to `None` at
  `knowledge/index_cache.py:203`, checked only at `:216`, and the sole caller
  passing a value is
  `.hydra-framework/engine/tests/unit/knowledge/test_search_index.py:164`.
- Static confirmation that `storage.build_knowledge_store` is whole-tree:
  `.hydra-framework/engine/src/hydra_engine/knowledge/storage.py:222-236` loops
  every node and `read_unit`s every unit path under it.
- Static confirmation of additional Phase 4 correctness boundaries:
  `collect_search_documents` performs all-object and recursive-file discovery
  before its `only_paths` filters (`search_index.py:87-128`); node declaration
  fields feed descendant package/routing rows (`:334-365`), so node deltas are
  not local; object sidecars record a distinct `envelope_path`
  (`objects/envelopes.py:154-155`), which the current document schema does not
  persist; and `delete_knowledge_rows` removes outgoing but not incoming edges
  (`index_cache.py:180-185`). D16/D18 address each rather than silently assuming
  the old callback is differential-correct.
- Static confirmation of Phase 2/3 concurrency/lifetime gaps:
  `index_cache.update_index` accepts but never uses `change`
  (`index_cache.py:134-151`), does not compare publication identity after a
  queued writer obtains SQLite's lock, and `SqliteKnowledgeStore.open`
  (`storage.py:315-319`) neither begins nor deterministically closes a read
  transaction. D13/D15 define the replacements.
- Architecture caps that constrain phases 3 and 4, read from
  `.hydra-framework/engine/src/hydra_engine/architecture.py:19-23`:
  `MAX_SOURCE_LINES` 400, `MAX_TEST_LINES` 600, `MAX_FAN_OUT` 8. Current sizes:
  `search_index.py` 395, `sqlite_db.py` 283, `index_cache.py` 223,
  `snapshot.py` 173, `context_providers.py` 398, `route_prompt.py` 199,
  `storage.py` 400. `commands/knowledge.py` has exactly eight internal import
  targets, so no new edge belongs there.
- Historical measurement provenance recheck, 2026-09-13: the section 8 matrix,
  its two disposable fixture sizes, 5+30 sampling, nearest-rank p95, machine
  versions, 206+8 fixed overhead, and four write numbers are present in the
  superseded record recoverable with `git show d5b9db0^:...`; its current
  production call paths are byte-unchanged from HEAD. The smaller Phase 1
  component-probe script/raw samples were not retained; their reported numbers
  can be checked for arithmetic and against unchanged call sites, but cannot be
  independently reproduced from the repository. They remain explicitly
  diagnostic/historical and Phase 5 must retain its own reproducible harness or
  inline it under D19.
- The checkpoint and old record disagree about whether the Phase 1 terminal
  `validate` actually ran: the record says it did, while the checkpoint says it
  was still to be run. No command output artifact resolves that conflict. Do
  not rely on the old claim; this records-only pass runs `validate` after its
  own checkpoint and records that result below.
- Records-only planning validation, 2026-09-13: `python3
  .hydra-framework/scripts/hydra.py validate` passed. It reported advisory
  provider-compatibility age, local telemetry volume, and provider delegation-
  enforcement notes only; it did not report a stale registry digest, so
  `ref index` was not run.
- Phase 2 validation, 2026-09-13: focused
  `python3 -m unittest tests.unit.ports.test_sqlite_db
  tests.unit.knowledge.test_index_cache` passed (30 tests); complete unit
  discovery passed (1450 tests); `hydra.py validate` passed with only the
  existing provider-age, telemetry-volume, and delegation-enforcement
  advisories; `git diff --check` passed. Direct selftest invocations exceeded
  the terminal's 30-second command window and were not recorded as passing;
  the required complete selftest remains in final-phase validation.
- Phase 3 implementation validation, 2026-09-13: complete unit discovery
  passed (1438 tests). The 12 removed tests were obsolete
  `VersionedPublicationTests`, deleted with the removed pointer/version API.
  `storage.py` is 400 lines, `search_index.py` 396, and
  `context_providers.py` 379, within the 400-line cap. Direct, detached, and
  PTY `hydra.py selftest` attempts were all forcibly stopped after 30 seconds;
  `hydra.py validate` and `git diff --check` passed (only the existing advisory
  notices); no completed selftest pass is claimed, and Phase 3 remains
  uncheckpointed.
- Phase 3 acceptance state, 2026-09-13: the requester accepted Phase 3 despite
  unavailable completed selftest evidence. Phase 4 is authorized; its final
  validation retains the requirement for a completed selftest result.
- Phase 4 validation, 2026-09-13: focused collector/cache/search/storage tests
  passed (38 tests); complete unit discovery passed (1441 tests); `hydra.py
  validate` passed with only the existing provider-age, telemetry-volume, and
  delegation-enforcement advisories; `git diff --check` passed. `validate` did
  not report a stale registry digest, so `ref index` was not run. A direct
  `hydra.py selftest` invocation again produced partial progress and was
  terminated at the terminal's 30-second boundary; no completed selftest pass
  is claimed. Phase 5 must not start until that evidence exists.

## Blockers

None.

Not blockers, recorded so they are not rediscovered:

- The full-rebuild gate is not targeted and its outcome is unknown (D7). Phase 5
  measures it and reports it missed if it is missed.
- This record's read-path scope (P13, P14, P15, the false FTS5 reporting among
  them) moved to `bounded-knowledge-retrieval`; that record's own Blockers
  section carries the FTS5-label obligation now, not this one.

## Continuation Notes

- Running state: none. No background processes, no dev servers, no extra
  worktrees. The Phase 1 probe scripts were scratch under the session
  scratchpad and are not needed again; the measurements they produced are
  inlined in Validation above.
- Resume check: inspect `git status --short`, then obtain a completed
  `python3 .hydra-framework/scripts/hydra.py selftest` from a runner that does
  not terminate at 30 seconds. The legacy `update_index`, `publish_versioned`,
  pointer functions, and all digest call paths must remain absent.
