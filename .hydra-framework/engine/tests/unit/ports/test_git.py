"""Mirror test for `hydra_engine.ports.git`."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.ports import git  # noqa: E402


class GitTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=str(self.root), check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=str(self.root), check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=str(self.root), check=True)
        (self.root / "tracked.txt").write_text("hello\n")
        subprocess.run(["git", "add", "tracked.txt"], cwd=str(self.root), check=True)
        subprocess.run(["git", "commit", "-q", "-m", "fixture commit"], cwd=str(self.root), check=True)

    def test_config_email_reads_the_given_root(self):
        self.assertEqual(git.config_email(self.root), "fixture@example.com")

    def test_config_email_returns_empty_string_on_failure(self):
        self.assertEqual(git.config_email(self.root / "does-not-exist"), "")

    def test_tracked_files_lists_staged_paths_under_the_given_root(self):
        self.assertEqual(git.tracked_files(self.root, "."), ["tracked.txt"])

    def test_tracked_files_returns_empty_list_on_failure(self):
        self.assertEqual(git.tracked_files(self.root / "does-not-exist", "."), [])

    def test_ignore_match_reports_verbose_rule_for_ignored_path(self):
        (self.root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        match = git.ignore_match(self.root, "ignored.txt")
        self.assertIn(".gitignore:1:ignored.txt", match)

    def test_ignore_match_is_empty_for_non_ignored_path_or_failure(self):
        self.assertEqual(git.ignore_match(self.root, "tracked.txt"), "")
        self.assertEqual(git.ignore_match(self.root / "does-not-exist", "tracked.txt"), "")

    def test_ignore_match_treats_a_tracked_path_as_not_ignored_by_default(self):
        (self.root / ".gitignore").write_text("tracked.txt\n", encoding="utf-8")
        self.assertEqual(git.ignore_match(self.root, "tracked.txt"), "")

    def test_ignore_match_no_index_reports_the_pattern_even_for_a_tracked_path(self):
        (self.root / ".gitignore").write_text("tracked.txt\n", encoding="utf-8")
        self.assertIn(".gitignore:1:tracked.txt", git.ignore_match(self.root, "tracked.txt", no_index=True))

    def test_ignored_files_lists_untracked_ignored_paths_under_a_prefix(self):
        (self.root / ".gitignore").write_text("dir/hydra-*/\n", encoding="utf-8")
        (self.root / "dir/hydra-demo").mkdir(parents=True)
        (self.root / "dir/hydra-demo/SKILL.md").write_text("x\n", encoding="utf-8")
        self.assertEqual(git.ignored_files(self.root, "dir"), ["dir/hydra-demo/SKILL.md"])

    def test_ignored_files_returns_empty_list_on_failure(self):
        self.assertEqual(git.ignored_files(self.root / "does-not-exist", "dir"), [])

    def test_stage_file_adds_a_path_to_the_index(self):
        (self.root / "new.txt").write_text("new\n")
        self.assertTrue(git.stage_file(self.root, "new.txt"))
        self.assertTrue(git.is_tracked(self.root, "new.txt"))
        self.assertTrue(git.worktree_matches_index(self.root, "new.txt"))

    def test_stage_file_returns_false_on_failure(self):
        self.assertFalse(git.stage_file(self.root / "does-not-exist", "new.txt"))

    def test_is_tracked_is_false_for_an_untracked_path(self):
        (self.root / "untracked.txt").write_text("new\n")
        self.assertFalse(git.is_tracked(self.root, "untracked.txt"))

    def test_worktree_matches_index_detects_unstaged_changes(self):
        (self.root / "tracked.txt").write_text("changed\n")
        self.assertFalse(git.worktree_matches_index(self.root, "tracked.txt"))

    def test_worktree_matches_index_returns_false_on_failure(self):
        self.assertFalse(git.worktree_matches_index(self.root / "does-not-exist", "tracked.txt"))

    def test_short_status_reports_dirty_paths(self):
        (self.root / "tracked.txt").write_text("changed\n")
        (self.root / "untracked.txt").write_text("new\n")
        self.assertEqual(git.short_status(self.root), [" M tracked.txt", "?? untracked.txt"])

    def test_short_status_returns_empty_list_on_failure(self):
        self.assertEqual(git.short_status(self.root / "does-not-exist"), [])

    def test_last_commit_iso_reads_the_committed_date(self):
        iso = git.last_commit_iso(self.root, "tracked.txt")
        self.assertRegex(iso, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_last_commit_iso_is_empty_for_an_untracked_path(self):
        self.assertEqual(git.last_commit_iso(self.root, "never-committed.txt"), "")

    def test_last_commit_iso_returns_empty_string_on_failure(self):
        self.assertEqual(git.last_commit_iso(self.root / "does-not-exist", "tracked.txt"), "")


if __name__ == "__main__":
    unittest.main()
