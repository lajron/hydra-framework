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
from hydra_engine.ports.sqlite_db import open_published, publish_versioned, query_store_disabled, resolve_published


@dataclasses.dataclass(frozen=True)
class SourceOnly:
    reason: str


@dataclasses.dataclass(frozen=True)
class Fresh:
    db_path: Path
    fingerprint: dict[str, str]


@dataclasses.dataclass(frozen=True)
class Stale:
    db_path: Path
    fingerprint: dict[str, str]
    delta: CorpusDelta


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


def default_db_path(local: Path) -> Path | None:
    return resolve_published(local / "index")


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
    return OperationStamp(corpus, default_db_path(local))


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
        if meta.get("schema") != schema or actual_columns != columns:
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
    return Fresh(db_path, current) if change.is_empty() else Stale(db_path, current, change)


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


def update_index(paths, local: Path, change: CorpusDelta, apply_update: Callable[[sqlite3.Connection, dict[str, str]], None]) -> Path:
    """Copy the current publication, apply one delta, and publish it atomically."""
    source = default_db_path(local)
    if source is None:
        raise ValueError("cannot incrementally update an absent publication")
    current = fingerprint(paths.root)

    def populate(conn: sqlite3.Connection) -> None:
        source_conn = open_published(source)
        if source_conn is None:
            raise ValueError("current publication became unavailable")
        try:
            source_conn.backup(conn)
        finally:
            source_conn.close()
        apply_update(conn, current)

    return publish_versioned(local / "index", populate, publication_id=uuid.uuid4().hex)


def create_index_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE documents (key TEXT PRIMARY KEY, hydra_id TEXT, aliases TEXT, path TEXT, kind TEXT, "
        "package TEXT, title TEXT, keywords TEXT, routes TEXT, use_when TEXT, headings TEXT, body TEXT, relations TEXT, content_id TEXT)"
    )
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")


def write_documents(conn: sqlite3.Connection, documents: list, encode: Callable[[object], tuple]) -> None:
    conn.executemany("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [encode(doc) for doc in documents])


def write_meta(
    conn: sqlite3.Connection, documents: list, command_ids: tuple[str, ...], features, schema: str, digest: Callable[[list], str],
) -> None:
    conn.executemany(
        "INSERT OR REPLACE INTO meta VALUES (?, ?)",
        [("schema", schema), ("fts5", "yes" if features.fts5 else "no"), ("trigram", "yes" if features.trigram else "no"),
         ("digest", digest(documents)), ("command_ids", json.dumps(sorted(command_ids)))],
    )


def documents_from_connection(conn: sqlite3.Connection, decode: Callable[[tuple], object]) -> list:
    return [decode(row) for row in conn.execute("SELECT * FROM documents ORDER BY rowid")]


def delete_knowledge_rows(conn: sqlite3.Connection, paths: tuple[str, ...]) -> None:
    placeholders = ", ".join("?" for _ in paths)
    ids = [row[0] for row in conn.execute(f"SELECT hydra_id FROM knowledge_objects WHERE path IN ({placeholders})", paths)]
    if ids:
        conn.execute(f"DELETE FROM knowledge_relations WHERE source_id IN ({', '.join('?' for _ in ids)})", ids)
    conn.execute(f"DELETE FROM knowledge_objects WHERE path IN ({placeholders})", paths)


def write_changed_knowledge_rows(conn: sqlite3.Connection, paths, changed: frozenset[str]) -> None:
    if not changed:
        return
    storage = __import__("hydra_engine.knowledge.storage", fromlist=("build_knowledge_store",))
    objects = [item for item in storage.build_knowledge_store(paths).iter_objects() if item.path in changed]
    conn.executemany("INSERT INTO knowledge_objects VALUES (?, ?, ?, ?, ?)", [(item.hydra_id, item.uid, item.kind, item.path, item.node_id) for item in objects])
    conn.executemany("INSERT INTO knowledge_relations VALUES (?, ?, ?)", [(item.hydra_id, relation_type, target) for item in objects for relation_type, target in item.relations])


def load_documents(
    db_path: Path | None,
    *,
    schema: str,
    columns: tuple[str, ...],
    decode: Callable[[tuple], object],
    expected_digest: str | None = None,
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
            meta.get("schema") != schema
            or actual_columns != columns
            or (expected_digest is not None and meta.get("digest") != expected_digest)
        ):
            return None
        return [decode(row) for row in conn.execute("SELECT * FROM documents ORDER BY rowid")]
    except (IndexError, sqlite3.Error):
        return None
    finally:
        conn.close()
