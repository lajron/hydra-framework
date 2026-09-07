"""Mirror test for `hydra_engine.installation.adopt`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.installation import adopt  # noqa: E402
from hydra_engine.installation.paths import InstallationPaths  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402
from hydra_engine.providers.paths import ProvidersPaths  # noqa: E402


def _write(root: Path, rel: str, content: str = "") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _all_paths() -> tuple[InstallationPaths, ProvidersPaths, ContextCompilerPaths]:
    root = Path(tempfile.mkdtemp(prefix="installation-adopt-"))
    hydra = root / ".hydra-framework"
    return (
        InstallationPaths(root=root, hydra=hydra),
        ProvidersPaths(root=root, hydra=hydra),
        ContextCompilerPaths(root=root, hydra=hydra),
    )


def _seed_required_paths(root: Path) -> None:
    for rel in adopt.REQUIRED_PATHS:
        if rel.endswith((".md", ".yaml")):
            _write(root, rel, "placeholder\n")
        else:
            (root / rel).mkdir(parents=True, exist_ok=True)


class AdoptionReportTests(unittest.TestCase):
    def test_reports_missing_required_paths(self):
        paths, providers_paths, context_compiler_paths = _all_paths()
        report = adopt.adoption_report(paths, providers_paths, context_compiler_paths, manifest={})
        self.assertEqual(report["missing"], adopt.REQUIRED_PATHS)

    def test_reports_present_required_paths_and_defaults(self):
        paths, providers_paths, context_compiler_paths = _all_paths()
        _seed_required_paths(paths.root)
        report = adopt.adoption_report(paths, providers_paths, context_compiler_paths, manifest={})
        self.assertEqual(report["missing"], [])
        self.assertEqual(report["seed_version"], "unknown")
        self.assertEqual(report["lineage"], {})
        self.assertIn("private_tier", report)
        self.assertEqual(report["host_stacks"], {})
        self.assertFalse(report["claude_md_present"])
        self.assertFalse(report["settings_json_present"])
        self.assertEqual(report["knowledge_nodes"], [])
        self.assertEqual(report["unmanaged_surfaces"], [])

    def test_reports_seed_version_and_lineage_from_manifest(self):
        paths, providers_paths, context_compiler_paths = _all_paths()
        manifest = {"seed_version": "0.4.0", "lineage": {"adopted_into": "example-repo"}}
        report = adopt.adoption_report(paths, providers_paths, context_compiler_paths, manifest)
        self.assertEqual(report["seed_version"], "0.4.0")
        self.assertEqual(report["lineage"], {"adopted_into": "example-repo"})

    def test_malformed_lineage_and_seed_version_fall_back(self):
        paths, providers_paths, context_compiler_paths = _all_paths()
        manifest = {"seed_version": 3, "lineage": "not-a-mapping"}
        report = adopt.adoption_report(paths, providers_paths, context_compiler_paths, manifest)
        self.assertEqual(report["seed_version"], "unknown")
        self.assertEqual(report["lineage"], {})

    def test_provider_surfaces_reflect_adapter_target_counts(self):
        paths, providers_paths, context_compiler_paths = _all_paths()
        _write(paths.root, ".claude/skills/demo/SKILL.md", "# Demo\n")
        report = adopt.adoption_report(paths, providers_paths, context_compiler_paths, manifest={})
        counts = {(provider, label): count for provider, label, _target, count in report["provider_surfaces"]}
        self.assertEqual(counts[("claude", "skills")], 1)
        self.assertEqual(counts[("claude", "agents")], 0)

    def test_claude_md_and_settings_presence(self):
        paths, providers_paths, context_compiler_paths = _all_paths()
        _write(paths.root, "CLAUDE.md", "@AGENTS.md\n")
        _write(paths.root, ".claude/settings.json", "{}\n")
        report = adopt.adoption_report(paths, providers_paths, context_compiler_paths, manifest={})
        self.assertTrue(report["claude_md_present"])
        self.assertTrue(report["settings_json_present"])

    def test_orphaned_provider_surface_is_unmanaged(self):
        paths, providers_paths, context_compiler_paths = _all_paths()
        _write(paths.root, ".claude/skills/demo/SKILL.md", "---\nname: demo\n---\nBody.\n")
        report = adopt.adoption_report(paths, providers_paths, context_compiler_paths, manifest={})
        self.assertEqual(len(report["unmanaged_surfaces"]), 1)
        self.assertEqual(report["unmanaged_surfaces"][0]["status"], "orphaned")


class RecordLineageTests(unittest.TestCase):
    def test_missing_required_paths_refuses(self):
        paths, _providers_paths, _context_compiler_paths = _all_paths()
        outcome = adopt.record_lineage(paths, manifest={}, repo_slug="example")
        self.assertEqual(outcome["status"], "missing-paths")
        self.assertEqual(outcome["missing"], adopt.REQUIRED_PATHS)

    def test_already_recorded_short_circuits(self):
        paths, _providers_paths, _context_compiler_paths = _all_paths()
        _seed_required_paths(paths.root)
        manifest = {"lineage": {"adopted_into": "already-here"}}
        outcome = adopt.record_lineage(paths, manifest, repo_slug="example")
        self.assertEqual(outcome, {"status": "already-recorded", "adopted_into": "already-here"})

    def test_records_lineage_block_and_writes_manifest(self):
        paths, _providers_paths, _context_compiler_paths = _all_paths()
        _seed_required_paths(paths.root)
        _write(paths.root, ".hydra-framework/manifest.yaml", "seed_version: 0.2.0\n")
        manifest = {"seed_version": "0.2.0"}
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-01"):
            outcome = adopt.record_lineage(paths, manifest, repo_slug="Example Repo!")
        self.assertEqual(outcome["status"], "recorded")
        self.assertEqual(outcome["slug"], "example-repo")
        written = paths.manifest_path().read_text(encoding="utf-8")
        self.assertIn("lineage:", written)
        self.assertIn("base_seed_version: 0.2.0", written)
        self.assertIn("adopted_into: example-repo", written)
        self.assertIn("adopted_date: 2026-01-01", written)
        self.assertIn("divergence_policy: reconcile-before-promoting", written)


if __name__ == "__main__":
    unittest.main()
