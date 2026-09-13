"""Mirror tests for `hydra_engine.knowledge.index_cache`."""

from __future__ import annotations

import subprocess
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hydra_engine.knowledge import index_cache
from hydra_engine.knowledge.freshness import GuardResult
from hydra_engine.knowledge.packages import ContextCompilerPaths
from hydra_engine.knowledge.storage import StoredKnowledgeObject


class IndexCacheTests(unittest.TestCase):
    def test_guard_failure_is_source_only_without_opening_a_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")
            state = index_cache.cache_state(
                paths, root / ".hydra-framework.local",
                guard=GuardResult(False, "not-a-git-worktree"), schema="test", columns=(),
            )
        self.assertEqual(state, index_cache.SourceOnly("not-a-git-worktree"))

    def test_missing_live_database_has_no_default_database_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(index_cache.default_db_path(Path(tmp)))


class OperationStampTests(unittest.TestCase):
    """`capture_stamp` is the Phase 5 operation-scoped read stamp: the
    guarded governed-corpus fingerprint plus the currently published index
    identity, captured once and compared for equality at revalidation."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=self.root, check=True)
        (self.root / "AI_SYSTEM.md").write_text("# AI System\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=self.root, check=True)
        self.paths = ContextCompilerPaths(root=self.root, hydra=self.root / ".hydra-framework")
        self.local = self.root / ".hydra-framework.local"

    def test_repeated_capture_over_an_unchanged_repository_is_equal(self):
        first = index_cache.capture_stamp(self.paths, self.local)
        second = index_cache.capture_stamp(self.paths, self.local)
        self.assertEqual(first, second)

    def test_a_governed_edit_between_captures_changes_the_stamp(self):
        from hydra_engine.knowledge import search_index
        from hydra_engine.objects.discovery import ObjectLocations

        resolver_paths = ObjectLocations(
            self.root, self.root / ".hydra-framework", self.root / ".hydra-framework.local",
            "tasks/personal", self.root / ".hydra-framework/cognition/graph/registry.yaml",
        )
        search_index.build_index(self.paths, resolver_paths, self.local)
        first = index_cache.capture_stamp(self.paths, self.local)
        (self.root / "AI_SYSTEM.md").write_text("# AI System, edited\n", encoding="utf-8")
        second = index_cache.capture_stamp(self.paths, self.local)
        self.assertNotEqual(first, second)

    def test_a_new_publication_between_captures_changes_the_stamp(self):
        from hydra_engine.knowledge import search_index
        from hydra_engine.objects.discovery import ObjectLocations

        resolver_paths = ObjectLocations(
            self.root, self.root / ".hydra-framework", self.root / ".hydra-framework.local",
            "tasks/personal", self.root / ".hydra-framework/cognition/graph/registry.yaml",
        )
        search_index.build_index(self.paths, resolver_paths, self.local)
        first = index_cache.capture_stamp(self.paths, self.local)
        search_index.build_index(self.paths, resolver_paths, self.local)
        second = index_cache.capture_stamp(self.paths, self.local)
        self.assertEqual(first.publication, second.publication)
        self.assertNotEqual(first.generation, second.generation)
        self.assertNotEqual(first, second)

    def test_guard_failure_yields_a_stamp_with_no_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")
            stamp = index_cache.capture_stamp(paths, root / ".hydra-framework.local")
        self.assertEqual(stamp, index_cache.OperationStamp({}, None))

    def test_stamp_from_fresh_matches_a_fresh_capture_with_no_extra_git_read(self):
        from hydra_engine.knowledge import search_index
        from hydra_engine.objects.discovery import ObjectLocations

        resolver_paths = ObjectLocations(
            self.root, self.root / ".hydra-framework", self.root / ".hydra-framework.local",
            "tasks/personal", self.root / ".hydra-framework/cognition/graph/registry.yaml",
        )
        search_index.build_index(self.paths, resolver_paths, self.local)
        state = index_cache.cache_state(
            self.paths, self.local, guard=index_cache.guard_for(self.paths.root.resolve()),
            schema=search_index.SCHEMA_VERSION, columns=search_index._DOCUMENT_COLUMNS,
        )
        self.assertIsInstance(state, index_cache.Fresh)
        derived = index_cache.stamp_from_fresh(state)
        real = index_cache.capture_stamp(self.paths, self.local)
        self.assertEqual(derived, real)

    def test_stamp_from_fresh_is_unpinnable_for_every_non_fresh_state(self):
        for state in (
            index_cache.SourceOnly("force-source"),
            index_cache.Absent({}),
            index_cache.Stale(self.local / "index" / "knowledge.db", {}, index_cache.CorpusDelta((), (), ())),
        ):
            self.assertEqual(index_cache.stamp_from_fresh(state), index_cache.OperationStamp({}, None, None))


class FingerprintDigestFastPathTests(unittest.TestCase):
    """D9: a clean read proves freshness from one aggregate `meta` digest
    instead of scanning every `documents` row. Any digest mismatch --
    including a missing digest, the state of an index built before this fast
    path existed -- must fall back to the existing row-by-row delta, so both
    paths have to classify every corpus mutation identically."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=self.root, check=True)
        (self.root / "AI_SYSTEM.md").write_text("# AI System\n", encoding="utf-8")
        (self.root / ".hydra-framework/repo/knowledge").mkdir(parents=True)
        (self.root / ".hydra-framework/repo/knowledge/tracked.md").write_text("# Tracked\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=self.root, check=True)
        self.paths = ContextCompilerPaths(root=self.root, hydra=self.root / ".hydra-framework")
        self.local = self.root / ".hydra-framework.local"

    _SCHEMA = "test-schema"
    _COLUMNS = (
        "key", "hydra_id", "aliases", "path", "kind", "package", "title",
        "keywords", "routes", "use_when", "headings", "body", "relations", "content_id",
    )

    def _build_index_matching_worktree(self) -> None:
        current = index_cache.fingerprint(self.root)

        def populate(conn):
            for path, content_id in current.items():
                conn.execute(
                    "INSERT INTO documents VALUES (?, '', '', ?, '', '', '', '', '', '', '', '', '', ?)",
                    (path, path, content_id),
                )
            conn.execute("INSERT OR REPLACE INTO meta VALUES ('schema', ?)", (self._SCHEMA,))
        index_cache.rebuild_index(self.local, populate)

    def _classify(self):
        return index_cache.cache_state(
            self.paths, self.local, guard=index_cache.guard_for(self.root.resolve()),
            schema=self._SCHEMA, columns=self._COLUMNS,
        )

    def _drop_stored_digest(self) -> None:
        db_path = index_cache.default_db_path(self.local)
        assert db_path is not None
        conn = index_cache.connect(db_path)
        try:
            conn.execute("DELETE FROM meta WHERE key = 'fingerprint_digest'")
            conn.commit()
        finally:
            conn.close()

    def _assert_fast_and_full_scan_agree(self):
        fast = self._classify()
        self._drop_stored_digest()
        full = self._classify()
        self.assertEqual(fast, full)
        # Restore the digest for any later mutation in the same test.
        self._rewrite_stored_digest()
        return fast

    def _rewrite_stored_digest(self) -> None:
        db_path = index_cache.default_db_path(self.local)
        assert db_path is not None
        conn = index_cache.connect(db_path)
        try:
            index_cache._write_fingerprint_digest(conn)
            conn.commit()
        finally:
            conn.close()

    def test_clean_repository_is_fresh_without_scanning_any_document_row(self):
        self._build_index_matching_worktree()
        with mock.patch.object(index_cache, "_stored_content_ids", wraps=index_cache._stored_content_ids) as scan:
            state = self._classify()
        self.assertIsInstance(state, index_cache.Fresh)
        scan.assert_not_called()

    def test_a_mismatched_digest_falls_back_to_the_full_row_scan(self):
        self._build_index_matching_worktree()
        (self.root / ".hydra-framework/repo/knowledge/tracked.md").write_text("# Tracked, edited\n", encoding="utf-8")
        with mock.patch.object(index_cache, "_stored_content_ids", wraps=index_cache._stored_content_ids) as scan:
            state = self._classify()
        self.assertIsInstance(state, index_cache.Stale)
        scan.assert_called_once()

    def test_added_document_is_stale_identically_on_both_paths(self):
        self._build_index_matching_worktree()
        (self.root / ".hydra-framework/repo/knowledge/added.md").write_text("# Added\n", encoding="utf-8")
        state = self._assert_fast_and_full_scan_agree()
        self.assertIsInstance(state, index_cache.Stale)
        self.assertIn(".hydra-framework/repo/knowledge/added.md", state.delta.added)

    def test_modified_document_is_stale_identically_on_both_paths(self):
        self._build_index_matching_worktree()
        (self.root / ".hydra-framework/repo/knowledge/tracked.md").write_text("# Tracked, edited\n", encoding="utf-8")
        state = self._assert_fast_and_full_scan_agree()
        self.assertIsInstance(state, index_cache.Stale)
        self.assertIn(".hydra-framework/repo/knowledge/tracked.md", state.delta.modified)

    def test_deleted_document_is_stale_identically_on_both_paths(self):
        self._build_index_matching_worktree()
        (self.root / ".hydra-framework/repo/knowledge/tracked.md").unlink()
        state = self._assert_fast_and_full_scan_agree()
        self.assertIsInstance(state, index_cache.Stale)
        self.assertIn(".hydra-framework/repo/knowledge/tracked.md", state.delta.deleted)

    def test_reverted_document_is_fresh_again_identically_on_both_paths(self):
        self._build_index_matching_worktree()
        tracked = self.root / ".hydra-framework/repo/knowledge/tracked.md"
        original = tracked.read_text(encoding="utf-8")
        tracked.write_text("# Tracked, edited\n", encoding="utf-8")
        self.assertIsInstance(self._classify(), index_cache.Stale)
        tracked.write_text(original, encoding="utf-8")
        state = self._assert_fast_and_full_scan_agree()
        self.assertIsInstance(state, index_cache.Fresh)


class PersistentTransactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=self.root, check=True)
        (self.root / "AI_SYSTEM.md").write_text("# initial\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.root, check=True)
        self.paths = ContextCompilerPaths(root=self.root, hydra=self.root / ".hydra-framework")
        self.local = self.root / ".hydra-framework.local"

    @staticmethod
    def _populate(value: str):
        def run(conn):
            conn.execute("INSERT INTO documents VALUES (?, '', '', ?, '', '', '', '', '', '', '', ?, '', ?)", (value, value, value, value))
        return run

    def test_rebuild_keeps_one_wal_path_and_changes_generation(self):
        path = index_cache.rebuild_index(self.local, self._populate("a"))
        first = index_cache.open_published(path)
        assert first is not None
        generation = index_cache.read_generation(first)
        first.close()
        self.assertEqual(path, self.local / "index" / "knowledge.db")
        self.assertEqual(index_cache.rebuild_index(self.local, self._populate("b")), path)
        second = index_cache.open_published(path)
        assert second is not None
        try:
            self.assertNotEqual(index_cache.read_generation(second), generation)
            self.assertEqual(second.execute("SELECT key FROM documents").fetchone()[0], "b")
        finally:
            second.close()

    def test_delta_rejects_stale_generation_and_rolls_back_callback(self):
        path = index_cache.rebuild_index(self.local, self._populate("a"))
        reader = index_cache.open_published(path)
        assert reader is not None
        generation = index_cache.read_generation(reader)
        reader.close()
        expected = index_cache.fingerprint(self.root)
        with self.assertRaises(RuntimeError):
            index_cache.apply_index_delta(
                self.paths, self.local, expected_generation=generation, expected_fingerprint=expected,
                apply_update=lambda conn, _current: (conn.execute("DELETE FROM documents"), (_ for _ in ()).throw(RuntimeError("stop"))),
            )
        with index_cache.open_published(path) as check:
            self.assertEqual(check.execute("SELECT key FROM documents").fetchone()[0], "a")
            self.assertEqual(index_cache.read_generation(check), generation)
        with self.assertRaises(index_cache.PublicationMovedError):
            index_cache.apply_index_delta(
                self.paths, self.local, expected_generation="stale", expected_fingerprint=expected,
                apply_update=lambda _conn, _current: self.fail("must not apply"),
            )

    def test_corpus_moved_before_delta_rolls_back_and_does_not_advance_generation(self):
        """The pre-callback fingerprint, taken after `BEGIN IMMEDIATE`, must
        catch a governed edit that lands before the writer even starts
        computing its delta, roll the transaction back, and never call the
        update callback at all."""
        path = index_cache.rebuild_index(self.local, self._populate("a"))
        with index_cache.open_published(path) as reader:
            generation = index_cache.read_generation(reader)
        stale_expected_fingerprint = index_cache.fingerprint(self.root)
        (self.root / "AI_SYSTEM.md").write_text("# moved before delta\n", encoding="utf-8")

        callback_calls = []
        with self.assertRaises(index_cache.CorpusMovedError):
            index_cache.apply_index_delta(
                self.paths, self.local, expected_generation=generation,
                expected_fingerprint=stale_expected_fingerprint,
                apply_update=lambda conn, current: callback_calls.append(current),
            )
        self.assertEqual(callback_calls, [])
        with index_cache.open_published(path) as check:
            self.assertEqual(check.execute("SELECT key FROM documents").fetchone()[0], "a")
            self.assertEqual(index_cache.read_generation(check), generation)

    def test_corpus_moved_during_delta_rolls_back_and_does_not_advance_generation(self):
        """The post-callback fingerprint must catch a governed edit that
        lands while the callback is computing and writing the delta, even
        though the pre-callback check already passed, and roll the whole
        transaction back rather than commit a delta computed against a
        corpus that has since moved."""
        path = index_cache.rebuild_index(self.local, self._populate("a"))
        with index_cache.open_published(path) as reader:
            generation = index_cache.read_generation(reader)
        expected_fingerprint = index_cache.fingerprint(self.root)

        def apply_update(conn, current):
            conn.execute("DELETE FROM documents")
            conn.execute("INSERT INTO documents VALUES ('b', '', '', 'b', '', '', '', '', '', '', '', 'b', '', 'b')")
            (self.root / "AI_SYSTEM.md").write_text("# moved during delta\n", encoding="utf-8")

        with self.assertRaises(index_cache.CorpusMovedError):
            index_cache.apply_index_delta(
                self.paths, self.local, expected_generation=generation,
                expected_fingerprint=expected_fingerprint, apply_update=apply_update,
            )
        with index_cache.open_published(path) as check:
            self.assertEqual(check.execute("SELECT key FROM documents").fetchone()[0], "a")
            self.assertEqual(index_cache.read_generation(check), generation)

    def test_corrupt_file_is_recreated(self):
        path = self.local / "index" / "knowledge.db"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"corrupt")
        index_cache.rebuild_index(self.local, self._populate("fresh"))
        with index_cache.open_published(path) as conn:
            self.assertIsNotNone(index_cache.read_generation(conn))
            self.assertEqual(conn.execute("SELECT key FROM documents").fetchone()[0], "fresh")

    def test_replacement_preserves_stable_id_incoming_edges_and_removes_changed_ids(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        index_cache.create_index_tables(conn)
        conn.execute("CREATE TABLE knowledge_objects (hydra_id TEXT PRIMARY KEY, uid TEXT, kind TEXT, path TEXT, node_id TEXT)")
        conn.execute("CREATE TABLE knowledge_relations (source_id TEXT, relation_type TEXT, target_id TEXT, PRIMARY KEY(source_id, relation_type, target_id))")
        conn.executemany("INSERT INTO knowledge_objects VALUES (?, '', 'knowledge-unit', ?, '')", (("old", "old.md"), ("source", "source.md")))
        conn.executemany("INSERT INTO knowledge_relations VALUES (?, 'relates-to', ?)", (("old", "source"), ("source", "old")))
        stable = StoredKnowledgeObject("old", "", "knowledge-unit", "new.md", "")
        index_cache.replace_changed_knowledge_rows(conn, ("old.md",), (stable,))
        self.assertEqual(conn.execute("SELECT target_id FROM knowledge_relations WHERE source_id = 'source'").fetchone()[0], "old")
        changed = StoredKnowledgeObject("new", "", "knowledge-unit", "newer.md", "")
        index_cache.replace_changed_knowledge_rows(conn, ("new.md",), (changed,))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM knowledge_relations WHERE target_id = 'old'").fetchone()[0], 0)
        index_cache.replace_changed_knowledge_rows(conn, (), ())


if __name__ == "__main__":
    unittest.main()
