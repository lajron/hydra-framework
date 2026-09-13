"""Published SQLite cache state and copy-on-write update mechanics."""

from __future__ import annotations

import dataclasses
import functools
import json
import sqlite3
import uuid
from collections.abc import Callable
from pathlib import Path

from hydra_engine.knowledge.freshness import CorpusDelta, FreshnessError, GuardResult, delta, evaluate_guard, fingerprint
from hydra_engine.ports.lock import LockUnavailableError, try_acquire
from hydra_engine.ports.sqlite_db import (
    connect, discard_database, live_db_path, open_published, query_store_disabled,
    truncate_wal,
)


@dataclasses.dataclass(frozen=True)
class SourceOnly:
    reason: str


@dataclasses.dataclass(frozen=True)
class Fresh:
    db_path: Path
    fingerprint: dict[str, str]
    generation: str | None = None


@dataclasses.dataclass(frozen=True)
class Stale:
    db_path: Path
    fingerprint: dict[str, str]
    delta: CorpusDelta
    generation: str | None = None


@dataclasses.dataclass(frozen=True)
class Absent:
    fingerprint: dict[str, str]


CacheState = SourceOnly | Fresh | Stale | Absent


@dataclasses.dataclass(frozen=True)
class OperationStamp:
    """One operation's pinned read identity: the guarded governed-corpus
    fingerprint plus the publication it was resolved against.

    Two stamps compare equal only when both the canonical bytes and the
    published index agree. `publication` is `None` whenever the guard fails,
    the fingerprint is unavailable, or the query store is disabled -- the
    same conditions that degrade a normal read to canonical source mode, so
    there is nothing for a source-mode operation to revalidate against."""

    corpus: dict[str, str]
    publication: Path | None
    generation: str | None = None


class PublicationMovedError(ValueError):
    """The queued writer observed a newer committed cache generation."""


class CorpusMovedError(ValueError):
    """The governed tree moved while an incremental delta was in flight."""


def default_db_path(local: Path) -> Path | None:
    path = _persistent_db_path(local)
    return path if path.is_file() else None


def _persistent_db_path(local: Path) -> Path:
    return live_db_path(local / "index")


def _write_generation(conn: sqlite3.Connection) -> str:
    generation = uuid.uuid4().hex
    conn.execute("INSERT OR REPLACE INTO meta VALUES ('generation', ?)", (generation,))
    return generation


def read_generation(conn: sqlite3.Connection) -> str | None:
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = 'generation'").fetchone()
    except sqlite3.Error:
        return None
    return row[0] if row and isinstance(row[0], str) and row[0] else None


def _reset_index_tables(conn: sqlite3.Connection) -> None:
    for table in ("knowledge_relations", "knowledge_objects", "documents", "meta"):
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    create_index_tables(conn)


def _recover_database(local: Path, db_path: Path) -> None:
    lock_path = local / "locks" / "knowledge-index-recovery.lock"
    try:
        with try_acquire(lock_path, timeout=0):
            check = open_published(db_path)
            if check is not None:
                check.close()
                return
            discard_database(db_path)
    except LockUnavailableError as error:
        raise ValueError("knowledge-index recovery lock unavailable") from error


def rebuild_index(local: Path, populate: Callable[[sqlite3.Connection], None]) -> Path:
    """Replace all index-owned rows in one WAL transaction at the live path."""
    db_path = _persistent_db_path(local)
    recovered = False
    while True:
        conn = None
        try:
            conn = connect(db_path)
            conn.execute("BEGIN IMMEDIATE")
            _reset_index_tables(conn)
            populate(conn)
            _write_generation(conn)
            conn.commit()
            truncate_wal(conn)
            return db_path
        except sqlite3.DatabaseError:
            if conn is not None:
                conn.rollback()
            if recovered:
                raise
            recovered = True
            _recover_database(local, db_path)
        except BaseException:
            if conn is not None:
                conn.rollback()
            raise
        finally:
            if conn is not None:
                conn.close()


def apply_index_delta(
    paths, local: Path, *, expected_generation: str, expected_fingerprint: dict[str, str],
    apply_update: Callable[[sqlite3.Connection, dict[str, str]], None],
) -> Path:
    """Apply one verified local delta in SQLite's normal writer transaction."""
    db_path = _persistent_db_path(local)
    conn = None
    try:
        conn = connect(db_path)
        conn.execute("BEGIN IMMEDIATE")
        if read_generation(conn) != expected_generation:
            raise PublicationMovedError("knowledge-index generation moved")
        current = fingerprint(paths.root)
        if current != expected_fingerprint:
            raise CorpusMovedError("governed corpus moved before delta")
        apply_update(conn, current)
        if fingerprint(paths.root) != current:
            raise CorpusMovedError("governed corpus moved during delta")
        _write_generation(conn)
        conn.commit()
        return db_path
    except BaseException:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        if conn is not None:
            conn.close()


@functools.lru_cache(maxsize=None)
def guard_for(root: Path) -> GuardResult:
    return evaluate_guard(root)


def capture_stamp(paths, local: Path) -> OperationStamp:
    """Capture the operation-scoped read stamp once, at the start (or a
    revalidation point) of an observable operation.

    Callers thread the same stamp through every search, routing, snapshot,
    view and unit-hydration step of that operation, then capture a fresh
    stamp at the end and compare: unequal means the governed corpus or the
    publication moved during the operation, so the whole result must be
    discarded and rerun canonically rather than mixing generations."""
    guard = guard_for(paths.root.resolve())
    if not guard.ok or query_store_disabled():
        return OperationStamp({}, None)
    try:
        corpus = fingerprint(paths.root)
    except FreshnessError:
        return OperationStamp({}, None)
    db_path = default_db_path(local)
    if db_path is None:
        return OperationStamp({}, None, None)
    conn = open_published(db_path)
    if conn is None:
        return OperationStamp({}, None, None)
    try:
        generation = read_generation(conn)
    finally:
        conn.close()
    return OperationStamp(corpus, db_path, generation) if generation else OperationStamp({}, None, None)


def cache_state(paths, local: Path, *, guard: GuardResult, schema: str, columns: tuple[str, ...]) -> CacheState:
    """Classify a publication without parsing or walking canonical files."""
    if not guard.ok:
        return SourceOnly(guard.reason)
    if query_store_disabled():
        return SourceOnly("query-store-disabled")
    try:
        current = fingerprint(paths.root)
    except FreshnessError:
        return SourceOnly("fingerprint-unavailable")
    db_path = default_db_path(local)
    if db_path is None:
        return Absent(current)
    conn = open_published(db_path)
    if conn is None:
        return Absent(current)
    try:
        meta = dict(conn.execute("SELECT key, value FROM meta"))
        actual_columns = tuple(row[1] for row in conn.execute("PRAGMA table_info(documents)"))
        generation = read_generation(conn)
        if meta.get("schema") != schema or actual_columns != columns or generation is None:
            return Absent(current)
        previous = {
            path: content_id
            for path, content_id in conn.execute(
                "SELECT path, content_id FROM documents WHERE path != '' AND content_id != ''"
            )
        }
    except sqlite3.Error:
        return Absent(current)
    finally:
        conn.close()
    change = delta(previous, current)
    return Fresh(db_path, current, generation) if change.is_empty() else Stale(db_path, current, change, generation)


def stamp_from_fresh(state: CacheState) -> OperationStamp:
    """Turn an already-settled `Fresh` cache classification into the same
    `OperationStamp` a fresh `capture_stamp` call would produce, with no
    further Git or SQLite read.

    Valid only immediately after the caller itself observed *state*: this
    performs no guard, generation or fingerprint check of its own, so it must
    never be called against a stale, cached, or reconstructed `Fresh` value.
    Every non-`Fresh` classification (source fallback, absent, stale) yields
    the same unpinnable stamp `capture_stamp` returns when it cannot pin."""
    if isinstance(state, Fresh):
        return OperationStamp(state.fingerprint, state.db_path, state.generation)
    return OperationStamp({}, None, None)


def command_ids_match(db_path: Path, command_ids: tuple[str, ...]) -> bool:
    conn = open_published(db_path)
    if conn is None:
        return False
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = 'command_ids'").fetchone()
        return row is not None and row[0] == json.dumps(sorted(command_ids))
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def create_index_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE documents (key TEXT PRIMARY KEY, hydra_id TEXT, aliases TEXT, path TEXT, kind TEXT, "
        "package TEXT, title TEXT, keywords TEXT, routes TEXT, use_when TEXT, headings TEXT, body TEXT, relations TEXT, content_id TEXT)"
    )
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")


def write_documents(conn: sqlite3.Connection, documents: list, encode: Callable[[object], tuple]) -> None:
    conn.executemany("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [encode(doc) for doc in documents])


def write_meta(conn: sqlite3.Connection, command_ids: tuple[str, ...], features, schema: str) -> None:
    conn.executemany(
        "INSERT OR REPLACE INTO meta VALUES (?, ?)",
        [("schema", schema), ("fts5", "yes" if features.fts5 else "no"), ("trigram", "yes" if features.trigram else "no"),
         ("command_ids", json.dumps(sorted(command_ids)))],
    )


def replace_changed_knowledge_rows(conn: sqlite3.Connection, removed_paths: tuple[str, ...], replacements: tuple) -> None:
    """Replace local locator rows while preserving valid incoming relations."""
    if not removed_paths and not replacements:
        return
    old_ids: list[str] = []
    if removed_paths:
        placeholders = ", ".join("?" for _ in removed_paths)
        old_ids = [row[0] for row in conn.execute(f"SELECT hydra_id FROM knowledge_objects WHERE path IN ({placeholders})", removed_paths)]
    replacement_ids = {item.hydra_id for item in replacements}
    if old_ids:
        placeholders = ", ".join("?" for _ in old_ids)
        conn.execute(f"DELETE FROM knowledge_relations WHERE source_id IN ({placeholders})", old_ids)
        removed_ids = tuple(value for value in old_ids if value not in replacement_ids)
        if removed_ids:
            conn.execute(f"DELETE FROM knowledge_relations WHERE target_id IN ({', '.join('?' for _ in removed_ids)})", removed_ids)
    if removed_paths:
        conn.execute(f"DELETE FROM knowledge_objects WHERE path IN ({', '.join('?' for _ in removed_paths)})", removed_paths)
    if replacements:
        conn.executemany("INSERT INTO knowledge_objects VALUES (?, ?, ?, ?, ?)", [(item.hydra_id, item.uid, item.kind, item.path, item.node_id) for item in replacements])
        conn.executemany("INSERT INTO knowledge_relations VALUES (?, ?, ?)", [(item.hydra_id, relation_type, target) for item in replacements for relation_type, target in item.relations])


def load_documents(
    db_path: Path | None,
    *,
    schema: str,
    columns: tuple[str, ...],
    decode: Callable[[tuple], object],
) -> list | None:
    if db_path is None:
        return None
    conn = open_published(db_path)
    if conn is None:
        return None
    try:
        meta = dict(conn.execute("SELECT key, value FROM meta"))
        actual_columns = tuple(row[1] for row in conn.execute("PRAGMA table_info(documents)"))
        if (
            meta.get("schema") != schema or actual_columns != columns
        ):
            return None
        return [decode(row) for row in conn.execute("SELECT * FROM documents ORDER BY rowid")]
    except (IndexError, sqlite3.Error):
        return None
    finally:
        conn.close()
