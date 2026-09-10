"""Mirror test for `hydra_engine.intake.takeover_scan`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.intake import takeover_scan  # noqa: E402


def _root() -> Path:
    return Path(tempfile.mkdtemp(prefix="takeover-scan-"))


def _write(root: Path, rel: str, content: str = "") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class TakeoverScanTests(unittest.TestCase):
    def test_missing_root_returns_read_only_report(self):
        result = takeover_scan.takeover_scan(_root() / "missing")
        self.assertFalse(result["exists"])
        self.assertEqual(result["totals"]["candidates"], 0)
        self.assertTrue(any("root does not exist" in note for note in result["notes"]))

    def test_classifies_hydra_entrypoint_without_staging(self):
        root = _root()
        _write(root, "AGENTS.md", "This repository uses Hydra.\nSee `.hydra-framework/`.\n")
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=["AGENTS.md"]):
            with mock.patch("hydra_engine.ports.git.ignore_match", return_value=""):
                result = takeover_scan.takeover_scan(root)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["classification"], "hydra-owned")
        self.assertEqual(candidate["staging"]["route"], "do-not-stage")

    def test_classifies_current_agents_entrypoint_through_hydra_system_target(self):
        root = _root()
        _write(root, "AGENTS.md", "# Shared Agent Instructions\n\nRead [`AI_SYSTEM.md`](AI_SYSTEM.md) first.\n")
        _write(root, "AI_SYSTEM.md", "# Hydra Operating Contract\n\nUse `.hydra-framework/`.\n")
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=["AGENTS.md"]):
            with mock.patch("hydra_engine.ports.git.ignore_match", return_value=""):
                result = takeover_scan.takeover_scan(root)
        agents = next(item for item in result["candidates"] if item["path"] == "AGENTS.md")
        self.assertEqual(agents["classification"], "hydra-owned")

    def test_classifies_current_claude_entrypoint_through_agents_import_and_hydra_reference(self):
        root = _root()
        _write(root, "CLAUDE.md", "@AGENTS.md\n\nGenerated skills come from `.hydra-framework/capabilities/`.\n")
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=["CLAUDE.md"]):
            with mock.patch("hydra_engine.ports.git.ignore_match", return_value=""):
                result = takeover_scan.takeover_scan(root)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["classification"], "hydra-owned")

    def test_reuses_provider_reclaim_for_orphaned_surface(self):
        root = _root()
        _write(root, ".claude/skills/deploy/SKILL.md", "---\nname: deploy\n---\nBody.\n")
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[".claude/skills/deploy/SKILL.md"]):
            with mock.patch("hydra_engine.ports.git.ignore_match", return_value=""):
                result = takeover_scan.takeover_scan(root)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["classification"], "provider-native")
        self.assertEqual(candidate["provider_surface_counts"], {"orphaned": 1})
        self.assertEqual(candidate["staging"]["route"], "shared-staging")
        self.assertEqual(candidate["staging"]["path"], ".migrations/claude/")

    def test_untracked_or_ignored_material_routes_to_private_staging(self):
        root = _root()
        _write(root, ".cursorrules", "Use old cursor rules.\n")
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            with mock.patch("hydra_engine.ports.git.ignore_match", return_value=".gitignore:1:.cursorrules\t.cursorrules"):
                result = takeover_scan.takeover_scan(root)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["classification"], "foreign-entrypoint")
        self.assertEqual(candidate["git"]["ignored_files"], 1)
        self.assertEqual(candidate["staging"]["route"], "private-staging")

    def test_provider_settings_need_owner_decision(self):
        root = _root()
        _write(root, ".codex/hooks.json", "{}\n")
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[".codex/hooks.json"]):
            with mock.patch("hydra_engine.ports.git.ignore_match", return_value=""):
                result = takeover_scan.takeover_scan(root)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["classification"], "needs-owner-decision")
        self.assertEqual(candidate["staging"]["route"], "confirm-owner")

    def test_top_level_prompts_need_owner_decision(self):
        root = _root()
        _write(root, "prompts/review.md", "Review this change.\n")
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=["prompts/review.md"]):
            with mock.patch("hydra_engine.ports.git.ignore_match", return_value=""):
                result = takeover_scan.takeover_scan(root)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["path"], "prompts")
        self.assertEqual(candidate["classification"], "needs-owner-decision")
        self.assertEqual(candidate["staging"]["route"], "confirm-owner")


if __name__ == "__main__":
    unittest.main()
