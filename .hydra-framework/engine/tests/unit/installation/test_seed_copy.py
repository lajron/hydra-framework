"""Mirror test for `hydra_engine.installation.seed_copy`.

Converted from `test_hydra.py`'s `InitPlanTests`, which ran
`hydra.planned_init_files` against the live repository tree (`hydra.ROOT`) --
not one of the named Hard-Constraint live-repo classes, so it is
rebuilt here as a hermetic fixture-based test against a synthetic source
root, matching the precedent for converting unnamed live-repo
classes rather than leaving them coupled to the real tree.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.installation.seed_copy import init_should_copy, planned_init_files  # noqa: E402


def _seed(root: Path, rel: str, content: str = "") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _source_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="seed-copy-source-"))
    _seed(root, "AI_SYSTEM.md", "# AI System\n")
    _seed(root, "AGENTS.md", "# AGENTS\n")
    _seed(root, ".claude/rules/hydra-placement.md", "# Placement rule\n")
    _seed(root, ".claude/settings.json", "{}\n")
    _seed(root, ".codex/hooks.json", "{}\n")
    _seed(root, ".github/CODEOWNERS", "* @local-reviewer\n")
    _seed(root, ".hydra-framework/core/placement-rules.md", "# Placement Rules\n")
    _seed(root, ".hydra-framework/tasks/templates/task.md", "# Task template\n")
    _seed(root, ".hydra-framework/tasks/templates/checkpoint.md", "# Checkpoint template\n")
    _seed(root, ".hydra-framework/tasks/personal/.gitkeep")
    _seed(root, ".hydra-framework/tasks/personal/dana/2026-01-01-x.md", "# In-flight task\n")
    _seed(root, ".hydra-framework/scripts/__pycache__/hydra.pyc", "bytecode")
    return root


class InitShouldCopyTests(unittest.TestCase):
    def test_framework_definition_travels(self):
        self.assertTrue(init_should_copy(Path(".hydra-framework/tasks/templates/task.md")))
        self.assertTrue(init_should_copy(Path(".hydra-framework/core/placement-rules.md")))

    def test_task_records_do_not_travel(self):
        self.assertFalse(init_should_copy(Path(".hydra-framework/tasks/personal/dana/2026-01-01-x.md")))

    def test_gitkeep_in_personal_tasks_travels(self):
        self.assertTrue(init_should_copy(Path(".hydra-framework/tasks/personal/.gitkeep")))

    def test_bytecode_and_git_metadata_are_excluded(self):
        self.assertFalse(init_should_copy(Path(".hydra-framework/scripts/__pycache__/hydra.pyc")))
        self.assertFalse(init_should_copy(Path(".git/config")))


class PlannedInitFilesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = _source_root()
        self.target = Path("/tmp/hydra-init-target")
        self.planned = planned_init_files(self.source, self.target)
        self.destinations = {
            destination.relative_to(self.target).as_posix() for _source, destination in self.planned
        }

    def test_top_level_files_travel(self):
        self.assertIn("AI_SYSTEM.md", self.destinations)
        self.assertIn("AGENTS.md", self.destinations)

    def test_portable_provider_support_files_travel(self):
        self.assertIn(".claude/rules/hydra-placement.md", self.destinations)
        self.assertIn(".claude/settings.json", self.destinations)
        self.assertIn(".codex/hooks.json", self.destinations)

    def test_repository_local_codeowners_does_not_travel(self):
        self.assertNotIn(".github/CODEOWNERS", self.destinations)

    def test_task_templates_travel(self):
        self.assertIn(".hydra-framework/tasks/templates/task.md", self.destinations)
        self.assertIn(".hydra-framework/tasks/templates/checkpoint.md", self.destinations)

    def test_task_records_do_not_travel(self):
        records = [
            path
            for path in self.destinations
            if path.startswith(".hydra-framework/tasks/personal/") and not path.endswith(".gitkeep")
        ]
        self.assertEqual(records, [], "a copy must not carry the source repository's task records")

    def test_bytecode_is_excluded(self):
        self.assertFalse([path for path in self.destinations if "__pycache__" in path])

    def test_private_tier_example_does_not_travel(self):
        """The private tier shape now travels as code-owned init-local seed."""
        example_root = ".hydra-framework" ".local" ".example"
        self.assertFalse([path for path in self.destinations if path.startswith(example_root)])

    def test_sources_paired_with_correct_target_destinations(self):
        for source, destination in self.planned:
            self.assertTrue(destination.is_relative_to(self.target))
            self.assertEqual(destination.relative_to(self.target), source.relative_to(self.source))


if __name__ == "__main__":
    unittest.main()
