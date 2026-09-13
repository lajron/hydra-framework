"""Mirror test for `hydra_engine.ports.sqlite_db`."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.ports import sqlite_db  # noqa: E402


def _db_path() -> Path:
    root = Path(tempfile.mkdtemp(prefix="ports-sqlite-db-"))
    return root / "sub" / "store.db"


class ConnectTests(unittest.TestCase):
    def test_connect_creates_missing_parent_and_enables_wal_and_busy_timeout(self):
        path = _db_path()
        conn = sqlite_db.connect(path)
        try:
            self.assertTrue(path.parent.is_dir())
            self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal")
            self.assertGreater(conn.execute("PRAGMA busy_timeout").fetchone()[0], 0)
        finally:
            conn.close()


class ConnectExistingTests(unittest.TestCase):
    def test_missing_file_returns_none(self):
        self.assertIsNone(sqlite_db.connect_existing(_db_path()))

    def test_valid_database_returns_a_working_connection(self):
        path = _db_path()
        conn = sqlite_db.connect(path)
        conn.execute("CREATE TABLE t (x TEXT)")
        conn.commit()
        conn.close()

        reopened = sqlite_db.connect_existing(path)
        self.assertIsNotNone(reopened)
        self.assertEqual(reopened.execute("SELECT COUNT(*) FROM t").fetchone()[0], 0)
        reopened.close()

    def test_corrupt_file_returns_none_rather_than_raising(self):
        path = _db_path()
        path.parent.mkdir(parents=True)
        path.write_bytes(b"not a sqlite database")
        self.assertIsNone(sqlite_db.connect_existing(path))


class LivePublicationTests(unittest.TestCase):
    def test_live_path_and_pinned_read_opener(self):
        path = sqlite_db.live_db_path(_db_path().parent)
        self.assertEqual(path.name, "knowledge.db")
        conn = sqlite_db.connect(path)
        conn.execute("CREATE TABLE t (x TEXT)")
        conn.execute("INSERT INTO t VALUES ('a')")
        conn.commit()
        reader = sqlite_db.open_published(path)
        self.assertIsNotNone(reader)
        assert reader is not None
        try:
            self.assertEqual(reader.execute("SELECT x FROM t").fetchone()[0], "a")
            with self.assertRaises(sqlite3.OperationalError):
                reader.execute("INSERT INTO t VALUES ('b')")
        finally:
            reader.close()
            conn.close()

    def test_garbage_file_is_not_opened(self):
        path = sqlite_db.live_db_path(_db_path().parent)
        path.parent.mkdir(parents=True)
        path.write_bytes(b"not sqlite")
        self.assertIsNone(sqlite_db.open_published(path))


class RebuildAtomicallyTests(unittest.TestCase):
    def test_populate_builds_the_store_and_no_temp_file_is_left_behind(self):
        path = _db_path()

        def _populate(conn: sqlite3.Connection) -> None:
            conn.execute("CREATE TABLE t (x TEXT)")
            conn.execute("INSERT INTO t VALUES ('a')")

        sqlite_db.rebuild_atomically(path, _populate)

        conn = sqlite3.connect(path)
        self.assertEqual(conn.execute("SELECT x FROM t").fetchone()[0], "a")
        conn.close()
        leftovers = list(path.parent.glob(".*.hydra-tmp-*"))
        self.assertEqual(leftovers, [])

    def test_rebuild_replaces_previous_content_wholesale(self):
        path = _db_path()

        def _populate(value: str):
            def _run(conn: sqlite3.Connection) -> None:
                conn.execute("CREATE TABLE t (x TEXT)")
                conn.execute("INSERT INTO t VALUES (?)", (value,))
            return _run

        sqlite_db.rebuild_atomically(path, _populate("old"))
        sqlite_db.rebuild_atomically(path, _populate("new"))

        conn = sqlite3.connect(path)
        rows = [row[0] for row in conn.execute("SELECT x FROM t")]
        conn.close()
        self.assertEqual(rows, ["new"])

    def test_failed_populate_leaves_the_previous_store_untouched(self):
        path = _db_path()

        def _populate_original(conn: sqlite3.Connection) -> None:
            conn.execute("CREATE TABLE t (x TEXT)")
            conn.execute("INSERT INTO t VALUES ('original')")

        sqlite_db.rebuild_atomically(path, _populate_original)

        def _fails(_conn: sqlite3.Connection) -> None:
            raise RuntimeError("simulated build failure")

        with self.assertRaises(RuntimeError):
            sqlite_db.rebuild_atomically(path, _fails)

        conn = sqlite3.connect(path)
        self.assertEqual(conn.execute("SELECT x FROM t").fetchone()[0], "original")
        conn.close()
        leftovers = list(path.parent.glob(".*.hydra-tmp-*"))
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
