"""Mirror tests for `hydra_engine.knowledge.index_cache`."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from hydra_engine.knowledge import index_cache
from hydra_engine.knowledge.freshness import GuardResult
from hydra_engine.knowledge.packages import ContextCompilerPaths


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

    def test_missing_pointer_has_no_default_database_path(self):
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
        self.assertNotEqual(first.publication, second.publication)
        self.assertNotEqual(first, second)

    def test_guard_failure_yields_a_stamp_with_no_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")
            stamp = index_cache.capture_stamp(paths, root / ".hydra-framework.local")
        self.assertEqual(stamp, index_cache.OperationStamp({}, None))


if __name__ == "__main__":
    unittest.main()
