"""Mirror test for `hydra_engine.knowledge.freshness`."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.documents.digests import normalized_digest  # noqa: E402
from hydra_engine.knowledge import freshness  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402


class FreshnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=str(self.root), check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=str(self.root), check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=str(self.root), check=True)
        (self.root / "source.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "source.py"], cwd=str(self.root), check=True)
        subprocess.run(["git", "commit", "-q", "-m", "fixture commit"], cwd=str(self.root), check=True)
        self.paths = ContextCompilerPaths(root=self.root, hydra=self.root / ".hydra-framework")

    def git(self, *args: str) -> bytes:
        return subprocess.run(["git", *args], cwd=self.root, check=True, stdout=subprocess.PIPE).stdout

    def write_governed(self, name: str, content: str) -> Path:
        path = self.root / ".hydra-framework/core" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def commit_all(self, message: str = "fixture") -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def aged_index_fixture(self, setting: tuple[str, str] | None = None) -> tuple[Path, str]:
        """Build the non-racy same-stat mutation fixture from the task record."""
        root = Path(tempfile.mkdtemp(prefix="freshness-aged-index-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
        if setting:
            subprocess.run(["git", "config", setting[0], setting[1]], cwd=root, check=True)
        target = root / ".hydra-framework/core/target.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"target content AAAA\n")
        other = root / "other.md"
        other.write_bytes(b"unrelated\n")
        time.sleep(2)  # The target must predate the index write; see section 10.
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)
        subprocess.run(["git", "status"], cwd=root, check=True, stdout=subprocess.PIPE)
        time.sleep(2)
        original_stat = target.stat()
        old = target.read_bytes()
        new = old[:-2] + b"B\n"
        self.assertEqual(len(new), len(old))
        with target.open("r+b") as handle:
            handle.write(new)
            handle.flush()
            os.fsync(handle.fileno())
        os.utime(target, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        restored = target.stat()
        self.assertEqual(
            (restored.st_mtime_ns, restored.st_size, restored.st_ino, restored.st_dev, restored.st_mode),
            (original_stat.st_mtime_ns, original_stat.st_size, original_stat.st_ino, original_stat.st_dev, original_stat.st_mode),
        )
        with other.open("ab") as handle:
            handle.write(b"unrelated edit\n")
        subprocess.run(["git", "add", "other.md"], cwd=root, check=True)
        return root, ".hydra-framework/core/target.md"

    def test_source_with_matching_digest_is_not_stale_by_date(self):
        digest = normalized_digest(self.root / "source.py")
        stale = freshness.stale_provenance_sources(
            {
                "sources": ["source.py"],
                "source_digests": [{"source": "source.py", "digest": digest}],
            },
            checked_on="2000-01-01",
            paths=self.paths,
        )
        self.assertEqual(stale, [])

    def test_source_without_digest_uses_date_fallback(self):
        stale = freshness.stale_provenance_sources(
            {"sources": ["source.py"]},
            checked_on="2000-01-01",
            paths=self.paths,
        )
        self.assertEqual(stale, ["source.py"])

    def test_changed_fingerprinted_source_is_stale(self):
        digest = normalized_digest(self.root / "source.py")
        (self.root / "source.py").write_text("x = 2\n", encoding="utf-8")
        stale = freshness.stale_provenance_sources(
            {
                "sources": ["source.py"],
                "source_digests": [{"source": "source.py", "digest": digest}],
            },
            checked_on="2099-01-01",
            paths=self.paths,
        )
        self.assertEqual(stale, ["source.py"])

    def test_is_governed_path(self):
        for root in freshness.SEARCH_ROOTS:
            self.assertTrue(freshness.is_governed_path(f"{root}/document.md"))
        self.assertTrue(freshness.is_governed_path("AI_SYSTEM.md"))
        self.assertFalse(freshness.is_governed_path("README.md"))
        self.assertFalse(freshness.is_governed_path(".hydra-framework/coreX/document.md"))
        self.assertFalse(freshness.is_governed_path("../.hydra-framework/core/document.md"))

    def test_blob_id_matches_git(self):
        for content in (b"", b"hello\n", b"\x00binary\xff"):
            path = self.root / "blob-input"
            path.write_bytes(content)
            expected = self.git("hash-object", "blob-input").decode().strip()
            self.assertEqual(freshness.blob_id(content, freshness.object_format(self.root)), expected)

    def test_object_format_read_not_assumed(self):
        root = Path(tempfile.mkdtemp(prefix="freshness-sha256-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        subprocess.run(["git", "init", "--object-format=sha256", "-q"], cwd=root, check=True)
        path = root / ".hydra-framework/core/document.md"
        path.parent.mkdir(parents=True)
        path.write_text("sha256 fixture\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        self.assertEqual(freshness.object_format(root), "sha256")
        self.assertEqual(len(freshness.fingerprint(root)[".hydra-framework/core/document.md"]), 64)

    def test_fingerprint_four_states(self):
        self.write_governed("unstaged.md", "before\n")
        self.write_governed("staged.md", "before\n")
        deleted = self.write_governed("deleted.md", "before\n")
        self.commit_all()
        before = freshness.fingerprint(self.root)
        self.write_governed("unstaged.md", "after\n")
        self.write_governed("staged.md", "after\n")
        self.git("add", ".hydra-framework/core/staged.md")
        deleted.unlink()
        self.git("add", "-u", "--", ".hydra-framework/core/deleted.md")
        self.write_governed("added.md", "new\n")
        after = freshness.fingerprint(self.root)
        changes = freshness.delta(before, after)
        self.assertEqual(changes.added, (".hydra-framework/core/added.md",))
        self.assertEqual(changes.modified, (
            ".hydra-framework/core/staged.md",
            ".hydra-framework/core/unstaged.md",
        ))
        self.assertEqual(changes.deleted, (".hydra-framework/core/deleted.md",))

    def test_fingerprint_rename_consumes_original_path_record(self):
        original = self.write_governed("a.md", "rename me\n")
        later = self.write_governed("z.md", "later path\n")
        self.commit_all()
        before = freshness.fingerprint(self.root)
        self.git("mv", str(original.relative_to(self.root)), ".hydra-framework/core/new-name.md")
        status = self.git("status", "--porcelain=v2", "--untracked-files=all", "-z")
        self.assertTrue(status.startswith(b"2 "))
        after = freshness.fingerprint(self.root)
        changes = freshness.delta(before, after)
        self.assertEqual(changes.added, (".hydra-framework/core/new-name.md",))
        self.assertEqual(changes.deleted, (".hydra-framework/core/a.md",))
        self.assertEqual(after[".hydra-framework/core/z.md"], before[".hydra-framework/core/z.md"])
        self.assertEqual(after[".hydra-framework/core/z.md"], freshness.blob_id(later.read_bytes(), freshness.object_format(self.root)))

    def test_fingerprint_unmerged_hashes_worktree(self):
        path = self.write_governed("conflict.md", "base\n")
        self.commit_all("base")
        branch = self.git("branch", "--show-current").decode().strip()
        self.git("checkout", "-q", "-b", "other")
        path.write_text("other\n", encoding="utf-8")
        self.commit_all("other")
        self.git("checkout", "-q", branch)
        path.write_text("current\n", encoding="utf-8")
        self.commit_all("current")
        merged = subprocess.run(["git", "merge", "other"], cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(merged.returncode, 0)
        ids = freshness.fingerprint(self.root)
        worktree_id = freshness.blob_id(path.read_bytes(), freshness.object_format(self.root))
        self.assertEqual(ids[".hydra-framework/core/conflict.md"], worktree_id)
        index_ids = self.git("ls-files", "-s", "--", ".hydra-framework/core/conflict.md").decode().splitlines()
        self.assertNotIn(worktree_id, {line.split()[1] for line in index_ids})

    def test_identical_porcelain_two_edits_have_distinct_fingerprints(self):
        path = self.write_governed("edits.md", "value base\n")
        self.commit_all()
        path.write_text("value one!\n", encoding="utf-8")
        first_status = self.git("status", "--porcelain=v2", "--untracked-files=all", "-z")
        first = freshness.fingerprint(self.root)
        path.write_text("value two!\n", encoding="utf-8")
        second_status = self.git("status", "--porcelain=v2", "--untracked-files=all", "-z")
        second = freshness.fingerprint(self.root)
        self.assertEqual(first_status, second_status)
        self.assertNotEqual(first, second)

    def test_revert_produces_delta(self):
        path = self.write_governed("revert.md", "original\n")
        self.commit_all()
        original = path.read_text(encoding="utf-8")
        first = freshness.fingerprint(self.root)
        path.write_text("changed\n", encoding="utf-8")
        second = freshness.fingerprint(self.root)
        path.write_text(original, encoding="utf-8")
        third = freshness.fingerprint(self.root)
        self.assertNotEqual(first, second)
        self.assertNotEqual(second, third)
        self.assertEqual(first, third)

    def test_fingerprint_ignores_non_governed(self):
        self.write_governed("kept.md", "same\n")
        self.commit_all()
        before = freshness.fingerprint(self.root)
        (self.root / ".gitignore").write_text("*.ignored\n", encoding="utf-8")
        (self.root / "README.md").write_text("unrelated\n", encoding="utf-8")
        local = self.root / ".hydra-framework.local/private.md"
        local.parent.mkdir()
        local.write_text("private\n", encoding="utf-8")
        self.assertEqual(freshness.fingerprint(self.root), before)

    def test_guard_refuses_when_trustctime_disabled(self):
        root, _target = self.aged_index_fixture(("core.trustctime", "false"))
        self.assertEqual(freshness.evaluate_guard(root), freshness.GuardResult(False, "trustctime-disabled"))

    def test_guard_refuses_when_checkstat_minimal(self):
        root, _target = self.aged_index_fixture(("core.checkStat", "minimal"))
        self.assertEqual(freshness.evaluate_guard(root), freshness.GuardResult(False, "checkstat-minimal"))

    def test_aged_index_forgery_detected_under_defaults(self):
        root, target = self.aged_index_fixture()
        index_id = subprocess.run(["git", "ls-files", "-s", "--", target], cwd=root, check=True, stdout=subprocess.PIPE).stdout.split()[1].decode()
        self.assertNotEqual(index_id, freshness.blob_id((root / target).read_bytes(), freshness.object_format(root)))
        self.assertEqual(freshness.evaluate_guard(root), freshness.GuardResult(True, freshness.GUARD_OK))
        committed = subprocess.run(["git", "show", f"HEAD:{target}"], cwd=root, check=True, stdout=subprocess.PIPE).stdout
        self.assertNotEqual(freshness.fingerprint(root)[target], freshness.blob_id(committed, freshness.object_format(root)))

    def test_guard_degrades_without_exceptions(self):
        non_git = Path(tempfile.mkdtemp(prefix="freshness-non-git-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(non_git, ignore_errors=True))
        self.assertEqual(freshness.evaluate_guard(non_git).reason, "not-a-git-worktree")
        with mock.patch.object(freshness.subprocess, "run", side_effect=FileNotFoundError):
            self.assertEqual(freshness.evaluate_guard(self.root).reason, "git-unavailable")

    def test_guard_refuses_assume_unchanged_skip_worktree_and_ignored_paths(self):
        assumed = self.write_governed("assumed.md", "assumed\n")
        self.commit_all()
        self.git("update-index", "--assume-unchanged", str(assumed.relative_to(self.root)))
        self.assertEqual(freshness.evaluate_guard(self.root).reason, "governed-path-assume-unchanged")
        self.git("update-index", "--no-assume-unchanged", str(assumed.relative_to(self.root)))
        self.git("update-index", "--skip-worktree", str(assumed.relative_to(self.root)))
        self.assertEqual(freshness.evaluate_guard(self.root).reason, "governed-path-skip-worktree")
        self.git("update-index", "--no-skip-worktree", str(assumed.relative_to(self.root)))
        (self.root / ".gitignore").write_text(".hydra-framework/core/ignored.md\n", encoding="utf-8")
        self.write_governed("ignored.md", "ignored\n")
        self.assertEqual(freshness.evaluate_guard(self.root).reason, "governed-path-ignored")

    def test_fingerprint_classifies_the_full_mutation_matrix_in_one_pass(self):
        """A combined-scenario companion to the individual fingerprint
        tests above: unstaged/staged modification, added, staged/unstaged
        deletion, a staged rename, an ignored path and a non-governed path
        change all in the same worktree, verified against directly computed
        Git blob ids (never a second copy of `fingerprint`'s own logic)."""
        algo = freshness.object_format(self.root)
        unstaged_src = self.write_governed("unstaged.md", "before\n")
        staged_src = self.write_governed("staged.md", "before\n")
        deleted_staged = self.write_governed("deleted-staged.md", "gone\n")
        deleted_unstaged = self.write_governed("deleted-unstaged.md", "gone-too\n")
        rename_src = self.write_governed("rename-me.md", "rename target\n")
        self.write_governed("non-governed-suffix.exe", "not governed\n")
        self.commit_all("baseline")

        unstaged_src.write_text("after\n", encoding="utf-8")
        staged_src.write_text("after\n", encoding="utf-8")
        self.git("add", ".hydra-framework/core/staged.md")
        self.write_governed("added.md", "new\n")
        deleted_staged.unlink()
        self.git("add", "-u", "--", ".hydra-framework/core/deleted-staged.md")
        deleted_unstaged.unlink()
        self.git("mv", str(rename_src.relative_to(self.root)), ".hydra-framework/core/renamed.md")
        (self.root / ".gitignore").write_text("*.ignored\n", encoding="utf-8")
        self.write_governed("skip.ignored", "ignored\n")
        (self.root / "unrelated-root.txt").write_text("stray\n", encoding="utf-8")

        actual = freshness.fingerprint(self.root)
        self.assertEqual(actual[".hydra-framework/core/unstaged.md"], freshness.blob_id(b"after\n", algo))
        self.assertEqual(actual[".hydra-framework/core/staged.md"], freshness.blob_id(b"after\n", algo))
        self.assertEqual(actual[".hydra-framework/core/added.md"], freshness.blob_id(b"new\n", algo))
        self.assertNotIn(".hydra-framework/core/deleted-staged.md", actual)
        self.assertNotIn(".hydra-framework/core/deleted-unstaged.md", actual)
        self.assertNotIn(".hydra-framework/core/rename-me.md", actual)
        self.assertEqual(actual[".hydra-framework/core/renamed.md"], freshness.blob_id(b"rename target\n", algo))
        self.assertNotIn(".hydra-framework/core/skip.ignored", actual)
        self.assertNotIn("unrelated-root.txt", actual)

    def test_no_governed_path_is_ignored_in_live_checkout(self):
        repository_root = Path(__file__).resolve().parents[5]
        result = freshness.evaluate_guard(repository_root)
        self.assertEqual(result, freshness.GuardResult(True, freshness.GUARD_OK))
        ids = freshness.fingerprint(repository_root)
        self.assertTrue(ids)
        self.assertTrue(all(freshness.is_governed_path(path) for path in ids))


if __name__ == "__main__":
    unittest.main()
