"""Mirror test for `hydra_engine.checks.repo_findings`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.checks import repo_findings  # noqa: E402
from hydra_engine.cli.dispatch import RepoContext  # noqa: E402


def _ctx() -> RepoContext:
    root = Path(tempfile.mkdtemp(prefix="repo-findings-test-"))
    hydra = root / ".hydra-framework"
    hydra.mkdir(parents=True)
    for provider in ("claude", "codex"):
        capability_map = hydra / f"adapters/providers/{provider}/capability-map.yaml"
        capability_map.parent.mkdir(parents=True)
        capability_map.write_text(
            f"schema: hydra-framework.capability-map.v1\nprovider: {provider}\nverified: fixture\ncertainty: fixture\n"
            "delegation_controls:\n"
            "  generated_agent_policy: supported\n"
            "  generic_subagent_start_context: advisory\n"
            "  effort_class_capping: supported\n"
            "  max_active_workers: advisory\n"
            "  max_depth: advisory\n",
            encoding="utf-8",
        )
    shape = hydra / "repo/knowledge/state-tiers.md"
    shape.parent.mkdir(parents=True)
    shape.write_text(_private_tier_shape(), encoding="utf-8")
    return RepoContext.for_root(root)


def _private_tier_shape() -> str:
    paths = [
        "notes", "intake/raw", "intake/extracted", "intake/triage",
        "monitoring", "index", "logs", "baseline", "tasks/retired",
        "migrations", "evolution/experiments", "scratch", "plans",
        "research", "prompts", "diagrams", "source-material", "tickets",
        "bug-reports", "developer", "machine", "repo-overrides", "secrets",
        "locks", "capabilities",
    ]
    return "\n".join(f"`{path}/`" for path in paths)


class NamedChecksTests(unittest.TestCase):
    def test_exposes_named_checks(self):
        self.assertEqual(len(repo_findings.NAMED_CHECKS), 9)
        ctx = _ctx()
        (ctx.hydra / "capabilities").mkdir(parents=True, exist_ok=True)
        (ctx.hydra / "capabilities/profiles.yaml").write_text(
            "schema: hydra-framework.capability-profiles.v1\nbaseline_tags: []\ndefault_profile: full\nprofiles: {}\n",
            encoding="utf-8",
        )
        for name, check in repo_findings.NAMED_CHECKS:
            self.assertIsInstance(name, str)
            self.assertEqual(check(ctx), [])

    def test_no_name_is_repeated(self):
        names = [name for name, _check in repo_findings.NAMED_CHECKS]
        self.assertEqual(len(names), len(set(names)))

    def test_object_model_check_skips_freshness_once_references_are_broken(self):
        ctx = _ctx()
        obj = ctx.hydra / "knowledge-units/0001-a.md"
        obj.parent.mkdir(parents=True)
        obj.write_text(
            "---\nhydra_id: hydra://knowledge-unit/0001-a\nstatus: active\nscope: repo\nowners:\n  a: '2026-08-17'\n"
            "relations:\n  - hydra://knowledge-unit/missing\nprovenance:\n  sources: []\n---\n# Title\n",
            encoding="utf-8",
        )
        findings = repo_findings.object_model_check(ctx)
        self.assertTrue(any("references unresolved" in str(f) for f in findings))


if __name__ == "__main__":
    unittest.main()
