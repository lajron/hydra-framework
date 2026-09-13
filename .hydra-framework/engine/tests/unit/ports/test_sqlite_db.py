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


def _published_value(index_dir: Path) -> str:
    path = sqlite_db.resolve_published(index_dir)
    if path is None:
        raise AssertionError("expected a published database")
    conn = sqlite_db.open_published(path)
    if conn is None:
        raise AssertionError("expected a readable published database")
    try:
        return conn.execute("SELECT x FROM t").fetchone()[0]
    finally:
        conn.close()


def _populate(value: str):
    def _run(conn: sqlite3.Connection) -> None:
        conn.execute("CREATE TABLE t (x TEXT)")
        conn.execute("INSERT INTO t VALUES (?)", (value,))
    return _run


class VersionedPublicationTests(unittest.TestCase):
    def setUp(self):
        self.index_dir = _db_path().parent
        sqlite_db.publish_versioned(self.index_dir, _populate("old"), publication_id="old")

    def _assert_old_is_live(self):
        self.assertEqual(_published_value(self.index_dir), "old")

    def test_publishes_a_rollback_journal_database_and_resolves_it(self):
        path = sqlite_db.resolve_published(self.index_dir)
        self.assertEqual(path, self.index_dir / "knowledge-old.db")
        with sqlite3.connect(path) as conn:
            self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0].lower(), "delete")
        self.assertEqual(_published_value(self.index_dir), "old")

    def test_failure_before_temp_build_keeps_the_old_pointer(self):
        with mock.patch.object(sqlite_db.sqlite3, "connect", side_effect=sqlite3.OperationalError("nope")):
            with self.assertRaises(sqlite3.OperationalError):
                sqlite_db.publish_versioned(self.index_dir, _populate("new"), publication_id="new")
        self._assert_old_is_live()

    def test_failure_during_populate_keeps_the_old_pointer(self):
        def _fails(_conn: sqlite3.Connection) -> None:
            raise RuntimeError("populate failed")

        with self.assertRaisesRegex(RuntimeError, "populate failed"):
            sqlite_db.publish_versioned(self.index_dir, _fails, publication_id="new")
        self._assert_old_is_live()

    def test_failure_before_database_fsync_keeps_the_old_pointer(self):
        with mock.patch.object(sqlite_db, "_fsync_file", side_effect=OSError("fsync failed")):
            with self.assertRaises(OSError):
                sqlite_db.publish_versioned(self.index_dir, _populate("new"), publication_id="new")
        self._assert_old_is_live()

    def test_failure_before_database_rename_keeps_the_old_pointer(self):
        original_replace = sqlite_db.os.replace

        def _fail_database_replace(source, target):
            if Path(target).name == "knowledge-new.db":
                raise OSError("replace failed")
            return original_replace(source, target)

        with mock.patch.object(sqlite_db.os, "replace", side_effect=_fail_database_replace):
            with self.assertRaises(OSError):
                sqlite_db.publish_versioned(self.index_dir, _populate("new"), publication_id="new")
        self._assert_old_is_live()

    def test_failure_after_database_rename_before_pointer_write_keeps_old_pointer(self):
        with mock.patch.object(sqlite_db, "_write_pointer", side_effect=OSError("pointer failed")):
            with self.assertRaises(OSError):
                sqlite_db.publish_versioned(self.index_dir, _populate("new"), publication_id="new")
        self._assert_old_is_live()

    def test_failure_during_pointer_write_keeps_old_pointer(self):
        original_replace = sqlite_db.os.replace

        def _fail_pointer_replace(source, target):
            if Path(target).name == "knowledge-current.json":
                raise OSError("pointer replace failed")
            return original_replace(source, target)

        with mock.patch.object(sqlite_db.os, "replace", side_effect=_fail_pointer_replace):
            with self.assertRaises(OSError):
                sqlite_db.publish_versioned(self.index_dir, _populate("new"), publication_id="new")
        self._assert_old_is_live()

    def test_cleanup_failure_after_pointer_write_keeps_new_pointer(self):
        original_unlink = Path.unlink

        def _fail_old_unlink(path: Path, *args, **kwargs):
            if path.name == "knowledge-old.db":
                raise OSError("old reader holds the database")
            return original_unlink(path, *args, **kwargs)

        with mock.patch.object(Path, "unlink", _fail_old_unlink):
            sqlite_db.publish_versioned(self.index_dir, _populate("new"), publication_id="new")
        self.assertEqual(_published_value(self.index_dir), "new")
        self.assertTrue((self.index_dir / "knowledge-old.db").exists())

    def test_reader_survives_republish(self):
        old_path = sqlite_db.resolve_published(self.index_dir)
        old_conn = sqlite_db.open_published(old_path)
        self.assertIsNotNone(old_conn)
        try:
            sqlite_db.publish_versioned(self.index_dir, _populate("new"), publication_id="new")
            self.assertEqual(old_conn.execute("SELECT x FROM t").fetchone()[0], "old")
            self.assertEqual(_published_value(self.index_dir), "new")
        finally:
            old_conn.close()

    def test_no_orphan_tmp_after_failure(self):
        with self.assertRaises(RuntimeError):
            sqlite_db.publish_versioned(
                self.index_dir,
                lambda _conn: (_ for _ in ()).throw(RuntimeError("build failed")),
                publication_id="new",
            )
        self.assertEqual(list(self.index_dir.glob(".knowledge-*.db.tmp")), [])
        self.assertEqual(list(self.index_dir.glob(".knowledge-current.json.tmp")), [])

    def test_pointer_rejects_foreign_schema(self):
        path = self.index_dir / "knowledge-foreign.db"
        path.write_bytes(b"placeholder")
        (self.index_dir / "knowledge-current.json").write_text(
            '{"schema":"foreign","file":"knowledge-foreign.db","publication_id":"foreign"}',
            encoding="utf-8",
        )
        self.assertIsNone(sqlite_db.resolve_published(self.index_dir))

    def test_collect_unreferenced_lists_only_old_versions_after_a_valid_pointer(self):
        orphan = self.index_dir / "knowledge-orphan.db"
        orphan.write_bytes(b"old")
        self.assertEqual(sqlite_db.collect_unreferenced(self.index_dir), (orphan,))

if __name__ == "__main__":
    unittest.main()
