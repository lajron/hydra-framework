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

import os
import sqlite3
from pathlib import Path
from typing import Callable

_BUSY_TIMEOUT_MS = 5000


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
