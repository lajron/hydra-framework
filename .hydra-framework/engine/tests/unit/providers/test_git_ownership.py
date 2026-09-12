"""Mirror test for `hydra_engine.providers.git_ownership`."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.providers import git_ownership  # noqa: E402
from hydra_engine.providers.paths import ProvidersPaths  # noqa: E402


def _write(root: Path, rel: str, content: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _init_git(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=str(root), check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=str(root), check=True)


def _demo_skill(paths: ProvidersPaths) -> None:
    _write(
        paths.root,
        ".hydra-framework/capabilities/skills/demo-skill/metadata.yaml",
        "name: demo-skill\ndescription: Use when relevant.\nkind: procedure\n",
    )
    _write(paths.root, ".hydra-framework/capabilities/skills/demo-skill/skill.md", "# Demo Skill\n\nBody.\n")


def _paths() -> ProvidersPaths:
    root = Path(tempfile.mkdtemp(prefix="providers-git-ownership-"))
    return ProvidersPaths(root=root, hydra=root / ".hydra-framework")


class IgnorePatternsTests(unittest.TestCase):
    def test_patterns_are_derived_from_providers_and_wrapper_prefix(self):
        patterns = git_ownership.generated_adapter_ignore_patterns()
        self.assertIn(".claude/skills/hydra-*/", patterns)
        self.assertIn(".agents/skills/hydra-*/", patterns)
        self.assertIn(".claude/agents/hydra-*.md", patterns)
        self.assertIn(".claude/agents/.hydra-adapter-hydra-*.yaml", patterns)
        self.assertIn(".codex/agents/hydra-*.toml", patterns)
        self.assertIn(".codex/agents/.hydra-adapter-hydra-*.yaml", patterns)

    def test_never_ignores_a_whole_provider_directory(self):
        for pattern in git_ownership.generated_adapter_ignore_patterns():
            self.assertNotIn(pattern, {".claude/skills/", ".claude/agents/", ".agents/skills/", ".codex/agents/"})

    def test_render_block_is_marked(self):
        block = git_ownership.render_generated_adapter_ignore_block()
        self.assertTrue(block.startswith(git_ownership.IGNORE_BLOCK_HEADER))
        self.assertIn(git_ownership.IGNORE_BLOCK_FOOTER, block)


class EnsureIgnoreBlockTests(unittest.TestCase):
    def test_adds_block_to_empty_gitignore(self):
        root = Path(tempfile.mkdtemp(prefix="providers-git-ownership-"))
        self.assertEqual(git_ownership.ensure_generated_adapter_ignore_block(root), "added")
        text = (root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(git_ownership.IGNORE_BLOCK_HEADER, text)

    def test_second_call_is_a_no_op(self):
        root = Path(tempfile.mkdtemp(prefix="providers-git-ownership-"))
        git_ownership.ensure_generated_adapter_ignore_block(root)
        self.assertEqual(git_ownership.ensure_generated_adapter_ignore_block(root), "already-present")

    def test_preserves_unrelated_gitignore_content(self):
        root = Path(tempfile.mkdtemp(prefix="providers-git-ownership-"))
        _write(root, ".gitignore", "*.pyc\n")
        git_ownership.ensure_generated_adapter_ignore_block(root)
        text = (root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("*.pyc", text)
        self.assertIn(git_ownership.IGNORE_BLOCK_HEADER, text)

    def test_a_real_hand_authored_hydra_named_skill_is_still_ignored_and_detectable(self):
        """The known silent-loss vector: `.claude/skills/hydra-*/` also
        swallows a hand-authored skill literally named `hydra-deploy`. The
        ignore block cannot special-case it; `unverified_ignored_provider_findings`
        is what is supposed to catch it instead (covered in
        `RepositoryChecksTests` below with real ownership data)."""
        root = Path(tempfile.mkdtemp(prefix="providers-git-ownership-"))
        _init_git(root)
        git_ownership.ensure_generated_adapter_ignore_block(root)
        _write(root, ".claude/skills/hydra-deploy/SKILL.md", "hand-authored\n")
        from hydra_engine.ports import git as git_port

        self.assertTrue(git_port.ignore_match(root, ".claude/skills/hydra-deploy/SKILL.md"))


class RepositoryChecksTests(unittest.TestCase):
    def _bootstrap(self) -> ProvidersPaths:
        paths = _paths()
        _init_git(paths.root)
        git_ownership.ensure_generated_adapter_ignore_block(paths.root)
        _demo_skill(paths)
        from hydra_engine.providers.adapter_plan import planned_adapter_files

        for path, content in planned_adapter_files(paths).items():
            _write(paths.root, path.relative_to(paths.root).as_posix(), content)
        return paths

    def test_every_ownership_path_is_ignored(self):
        paths = self._bootstrap()
        self.assertEqual(git_ownership.unignored_ownership_findings(paths), [])

    def test_ownership_path_not_covered_by_the_ignore_block_is_reported(self):
        paths = _paths()
        _init_git(paths.root)
        # No ignore block written: nothing is ignored yet.
        _demo_skill(paths)
        from hydra_engine.providers.adapter_plan import planned_adapter_files

        for path, content in planned_adapter_files(paths).items():
            _write(paths.root, path.relative_to(paths.root).as_posix(), content)
        findings = git_ownership.unignored_ownership_findings(paths)
        self.assertTrue(findings)

    def test_no_ownership_path_is_tracked_after_migration(self):
        paths = self._bootstrap()
        self.assertEqual(git_ownership.tracked_ownership_findings(paths), [])

    def test_a_tracked_ownership_path_is_reported(self):
        paths = self._bootstrap()
        subprocess.run(
            ["git", "add", "-f", ".claude/skills/hydra-demo-skill/SKILL.md"],
            cwd=str(paths.root), check=True,
        )
        findings = git_ownership.tracked_ownership_findings(paths)
        self.assertTrue(any("hydra-demo-skill/SKILL.md" in finding.path for finding in findings))

    def test_a_hand_authored_hydra_named_skill_is_unverified(self):
        paths = self._bootstrap()
        _write(paths.root, ".claude/skills/hydra-deploy/SKILL.md", "hand-authored\n")
        findings = git_ownership.unverified_ignored_provider_findings(paths)
        self.assertTrue(any("hydra-deploy/SKILL.md" in finding.path for finding in findings))

    def test_generated_files_are_all_verified(self):
        paths = self._bootstrap()
        self.assertEqual(git_ownership.unverified_ignored_provider_findings(paths), [])

    def test_a_tracked_stable_file_is_not_ignored(self):
        paths = self._bootstrap()
        _write(paths.root, ".claude/skills/README.md", "stable\n")
        subprocess.run(["git", "add", ".claude/skills/README.md"], cwd=str(paths.root), check=True)
        self.assertEqual(git_ownership.tracked_and_ignored_provider_findings(paths), [])

    def test_a_tracked_file_matching_the_ignore_pattern_is_reported(self):
        paths = self._bootstrap()
        _write(paths.root, ".claude/skills/hydra-tracked/SKILL.md", "should not happen\n")
        subprocess.run(
            ["git", "add", "-f", ".claude/skills/hydra-tracked/SKILL.md"],
            cwd=str(paths.root), check=True,
        )
        findings = git_ownership.tracked_and_ignored_provider_findings(paths)
        self.assertTrue(any("hydra-tracked/SKILL.md" in finding.path for finding in findings))


if __name__ == "__main__":
    unittest.main()
