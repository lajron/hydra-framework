"""SQLite connection primitives for Hydra's operational query stores.

The only module that talks `sqlite3` for pragmas and atomic rebuild. Layer 0
so every layer-1 store module (`objects/store_build.py`,
`work/task_store.py`) can depend on it without importing each other, the
same reason `documents/tokens.py`'s `write_text` sits below everything that
needs atomic writes.

`rebuild_atomically` is this store's write-safety chokepoint (mirroring
`documents/tokens.py.write_text`'s temp-file-then-`os.replace` discipline):
a concurrent reader always sees a complete old or new
store, never a half-populated one. `knowledge/search_index.py` now uses this
same boundary for its private `knowledge.db`; the store is disposable, but
its cache readers must still never observe a torn rebuild.
"""

from __future__ import annotations

import errno
import json
import os
import sqlite3
from pathlib import Path
from typing import Callable

_BUSY_TIMEOUT_MS = 5000

# The knowledge index is the only versioned publication currently using this
# port.  Keep this local rather than importing ``knowledge.search_index``:
# ports are below knowledge in the import graph.  Phase 4 moves the index to
# the v3 schema together with its caller.
SCHEMA_VERSION = "hydra-framework.knowledge-store.v3"
_POINTER_NAME = "knowledge-current.json"
_UNSUPPORTED_DIRECTORY_FSYNC = {errno.EINVAL, errno.ENOTSUP}
if hasattr(errno, "EOPNOTSUPP"):
    _UNSUPPORTED_DIRECTORY_FSYNC.add(errno.EOPNOTSUPP)


def query_store_disabled() -> bool:
    """`HYDRA_QUERY_STORE=off`: the escape hatch every read
    gate checks before even trying to connect, for a machine boundary (CI,
    `pre-push`) where the store's mtime-trust model does not apply and
    `--verify-digests` is not in use. Diagnostic commands (`ref store
    status`/`rebuild`) do not check this -- disabling reads must not blind
    the disagreement detector or the rebuild it recommends."""
    return os.environ.get("HYDRA_QUERY_STORE", "") == "off"


def connect(db_path: Path) -> sqlite3.Connection:
    """WAL mode lets a concurrent reader keep working through a rebuild;
    `busy_timeout` waits out a writer instead of raising `database is
    locked` (matches `knowledge/search_index.py`'s `_connect`)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
    return conn


def connect_existing(db_path: Path) -> sqlite3.Connection | None:
    """Open an already-built store for reading, or `None` if it does not
    exist or is not a valid SQLite database.

    A store is always disposable: every caller degrades to a full scan
    on `None` rather than raising."""
    if not db_path.exists():
        return None
    try:
        conn = connect(db_path)
        conn.execute("SELECT 1")
        return conn
    except sqlite3.DatabaseError:
        return None


def _remove_with_wal_sidecars(path: Path) -> None:
    path.unlink(missing_ok=True)
    Path(f"{path}-wal").unlink(missing_ok=True)
    Path(f"{path}-shm").unlink(missing_ok=True)


def _remove_temp_database(path: Path) -> None:
    """Remove the complete temporary SQLite artifact, if a build failed."""
    path.unlink(missing_ok=True)
    Path(f"{path}-journal").unlink(missing_ok=True)
    Path(f"{path}-wal").unlink(missing_ok=True)
    Path(f"{path}-shm").unlink(missing_ok=True)


def _fsync_file(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    """Persist a directory entry when this platform exposes that operation."""
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        if error.errno in _UNSUPPORTED_DIRECTORY_FSYNC:
            return
        raise
    try:
        try:
            os.fsync(descriptor)
        except OSError as error:
            if error.errno not in _UNSUPPORTED_DIRECTORY_FSYNC:
                raise
    finally:
        os.close(descriptor)


def _publication_file_name(publication_id: str) -> str:
    if (
        not publication_id
        or publication_id in {".", ".."}
        or "\x00" in publication_id
        or Path(publication_id).name != publication_id
    ):
        raise ValueError("publication_id must be a non-empty filename component")
    return f"knowledge-{publication_id}.db"


def _write_pointer(index_dir: Path, publication_id: str, db_path: Path) -> None:
    pointer = index_dir / _POINTER_NAME
    temp_pointer = index_dir / f".{_POINTER_NAME}.tmp"
    payload = {
        "schema": SCHEMA_VERSION,
        "file": db_path.name,
        "publication_id": publication_id,
    }
    try:
        temp_pointer.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        _fsync_file(temp_pointer)
        os.replace(temp_pointer, pointer)
        _fsync_directory(index_dir)
    finally:
        temp_pointer.unlink(missing_ok=True)


def resolve_published(index_dir: Path) -> Path | None:
    """Return the current immutable knowledge publication, if it is usable."""
    pointer = index_dir / _POINTER_NAME
    try:
        payload = json.loads(pointer.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA_VERSION:
        return None
    publication_id = payload.get("publication_id")
    file_name = payload.get("file")
    if not isinstance(publication_id, str) or not isinstance(file_name, str):
        return None
    try:
        if file_name != _publication_file_name(publication_id):
            return None
    except ValueError:
        return None
    candidate = index_dir / file_name
    return candidate if candidate.is_file() else None


def open_published(db_path: Path) -> sqlite3.Connection | None:
    """Open an immutable publication read-only, or treat it as absent."""
    try:
        conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro&immutable=1", uri=True)
        conn.execute("PRAGMA schema_version").fetchone()
        return conn
    except (OSError, sqlite3.DatabaseError):
        try:
            conn.close()
        except UnboundLocalError:
            pass
        return None


def collect_unreferenced(index_dir: Path) -> tuple[Path, ...]:
    """List obsolete version files after a valid pointer has gone live.

    A missing or invalid pointer is deliberately not a cleanup signal: keeping
    disposable bytes is safer than deleting the only recoverable publication.
    """
    current = resolve_published(index_dir)
    if current is None:
        return ()
    return tuple(sorted(
        (path for path in index_dir.glob("knowledge-*.db") if path != current),
        key=lambda path: path.name,
    ))


def publish_versioned(
    index_dir: Path,
    populate: Callable[[sqlite3.Connection], None],
    *,
    publication_id: str,
) -> Path:
    """Publish one complete SQLite file through a durable atomic pointer.

    The pointer is the sole reader-visible boundary.  A failed build may leave
    an unreferenced completed version, but readers can only resolve the prior
    pointer or the new one, never a partially written database.
    """
    db_name = _publication_file_name(publication_id)
    index_dir.mkdir(parents=True, exist_ok=True)
    temp_db = index_dir / f".{db_name}.tmp"
    published_db = index_dir / db_name
    _remove_temp_database(temp_db)
    try:
        conn = sqlite3.connect(temp_db)
        try:
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
            populate(conn)
            conn.commit()
        finally:
            conn.close()
        _fsync_file(temp_db)
        os.replace(temp_db, published_db)
        _fsync_directory(index_dir)
        _write_pointer(index_dir, publication_id, published_db)
    finally:
        _remove_temp_database(temp_db)

    try:
        stale_paths = collect_unreferenced(index_dir)
    except OSError:
        stale_paths = ()
    for stale in stale_paths:
        try:
            stale.unlink()
        except OSError:
            # Cleanup is intentionally best-effort.  The live pointer remains
            # authoritative even where an old reader prevents unlinking.
            pass
    return published_db


def rebuild_atomically(db_path: Path, populate: Callable[[sqlite3.Connection], None]) -> None:
    """Build a fresh store at a temp path and swap it into place with
    `os.replace`, so a concurrent reader always sees a complete old or new
    store, never a half-populated one.

    `populate` receives an open connection to the temp database and does all
    DDL and inserts; this function commits, closes (which checkpoints WAL
    back into the single file so the swap moves one self-contained file),
    and replaces. The previous store is left untouched if `populate` raises.
    """
    tmp_path = db_path.with_name(f".{db_path.name}.hydra-tmp-{os.getpid()}")
    _remove_with_wal_sidecars(tmp_path)
    try:
        conn = connect(tmp_path)
        try:
            populate(conn)
            conn.commit()
        finally:
            conn.close()
        os.replace(tmp_path, db_path)
    except BaseException:
        _remove_with_wal_sidecars(tmp_path)
        raise
    finally:
        _remove_with_wal_sidecars(tmp_path)


def source_manifest(root: Path, files: list[Path]) -> list[tuple[str, int, int]]:
    """Stable stat-only inventory for a derived store's governed inputs."""
    manifest: list[tuple[str, int, int]] = []
    for path in sorted(set(files)):
        try:
            stat = path.stat()
            relative = path.relative_to(root).as_posix()
        except (OSError, ValueError):
            continue
        if path.is_file():
            manifest.append((relative, stat.st_mtime_ns, stat.st_size))
    return manifest
