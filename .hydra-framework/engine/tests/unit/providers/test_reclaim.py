"""Mirror test for `hydra_engine.providers.reclaim`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.providers import reclaim  # noqa: E402
from hydra_engine.providers.paths import ProvidersPaths  # noqa: E402


def _write(root: Path, rel: str, content: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _paths() -> ProvidersPaths:
    root = Path(tempfile.mkdtemp(prefix="providers-reclaim-"))
    return ProvidersPaths(root=root, hydra=root / ".hydra-framework")


class SidecarForTests(unittest.TestCase):
    def test_agent_sidecar_is_named_per_wrapper(self):
        path = Path("/tmp/.claude/agents/hydra-demo.md")
        self.assertEqual(reclaim.sidecar_for(path, "agent"), Path("/tmp/.claude/agents/.hydra-adapter-hydra-demo.yaml"))

    def test_skill_sidecar_is_shared(self):
        path = Path("/tmp/.claude/skills/hydra-demo/SKILL.md")
        self.assertEqual(reclaim.sidecar_for(path, "skill"), Path("/tmp/.claude/skills/hydra-demo/.hydra-adapter.yaml"))


class ClassifySurfacesTests(unittest.TestCase):
    def test_hand_authored_file_is_orphaned(self):
        paths = _paths()
        _write(paths.root, ".claude/skills/deploy/SKILL.md", "---\nname: deploy\n---\nBody.\n")
        items = reclaim.classify_surfaces(paths)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["status"], "orphaned")
        self.assertIn("capabilities/skills/deploy/skill.md", items[0]["detail"])

    def test_generated_file_matching_the_plan_is_generated(self):
        paths = _paths()
        _write(
            paths.root,
            ".hydra-framework/capabilities/skills/demo-skill/metadata.yaml",
            "name: demo-skill\ndescription: Use when relevant.\nkind: procedure\n",
        )
        _write(paths.root, ".hydra-framework/capabilities/skills/demo-skill/skill.md", "# Demo Skill\n\nBody.\n")
        from hydra_engine.providers.adapter_plan import planned_adapter_files

        plan = planned_adapter_files(paths)
        for path, content in plan.items():
            _write(paths.root, path.relative_to(paths.root).as_posix(), content)

        items = reclaim.classify_surfaces(paths)
        claude_items = [item for item in items if item["path"].startswith(".claude/skills/")]
        self.assertTrue(claude_items)
        for item in claude_items:
            self.assertEqual(item["status"], "generated")

    def test_edited_wrapper_is_drifted(self):
        paths = _paths()
        _write(
            paths.root,
            ".hydra-framework/capabilities/skills/demo-skill/metadata.yaml",
            "name: demo-skill\ndescription: Use when relevant.\nkind: procedure\n",
        )
        _write(paths.root, ".hydra-framework/capabilities/skills/demo-skill/skill.md", "# Demo Skill\n\nBody.\n")
        from hydra_engine.providers.adapter_plan import planned_adapter_files

        plan = planned_adapter_files(paths)
        for path, content in plan.items():
            _write(paths.root, path.relative_to(paths.root).as_posix(), content)
        edited = paths.root / ".claude/skills/hydra-demo-skill/SKILL.md"
        edited.write_text(edited.read_text(encoding="utf-8") + "\nExtra.\n", encoding="utf-8")

        items = reclaim.classify_surfaces(paths)
        by_path = {item["path"]: item for item in items}
        self.assertEqual(by_path[".claude/skills/hydra-demo-skill/SKILL.md"]["status"], "drifted")

    def test_orphaned_sidecar_pointing_at_a_deleted_canonical_is_stale(self):
        paths = _paths()
        _write(paths.root, ".claude/skills/gone/SKILL.md", "content\n")
        _write(
            paths.root,
            ".claude/skills/gone/.hydra-adapter.yaml",
            "schema: hydra-framework.adapter.v2\nprovider: claude\nkind: skill\n"
            "canonical_source: .hydra-framework/capabilities/skills/gone/skill.md\ngenerated_file: SKILL.md\n",
        )
        items = reclaim.classify_surfaces(paths)
        self.assertEqual(items[0]["status"], "stale")
        self.assertIn("canonical source is gone", items[0]["detail"])
        self.assertIn("rm -rf .claude/skills/gone/", items[0]["detail"])


class PromoteSurfaceTests(unittest.TestCase):
    def test_promotes_yaml_frontmatter_skill(self):
        """Regression: the pre-move code called an undefined `_yaml_scalar`
        here (removed from `hydra.py` when its real
        implementation moved to `documents.tokens.yaml_scalar`, but this call site
        was never updated since `promote_surface` had not moved yet) -- a
        latent `NameError` on every promotion of a YAML-frontmatter surface,
        never caught because no test or golden exercised it. Fixed as part
        of this move; this test is the regression coverage that was missing."""
        paths = _paths()
        _write(paths.root, ".claude/skills/deploy/SKILL.md", '---\nname: deploy\ndescription: "Deploy the thing"\n---\nBody text.\n')
        item = {"path": ".claude/skills/deploy/SKILL.md", "kind": "skill", "detail": ""}
        target = reclaim.promote_surface(paths, item)
        self.assertEqual(target, paths.hydra / "capabilities/skills/deploy/skill.md")
        self.assertEqual(target.read_text(encoding="utf-8"), "Body text.\n")
        metadata = (paths.hydra / "capabilities/skills/deploy/metadata.yaml").read_text(encoding="utf-8")
        self.assertIn("description: Deploy the thing", metadata)
        self.assertIn("promoted_from: .claude/skills/deploy/SKILL.md", metadata)
        self.assertFalse((paths.root / item["path"]).exists())

    def test_promotes_codex_toml_agent(self):
        paths = _paths()
        _write(
            paths.root,
            ".codex/agents/hydra-demo.toml",
            'name = "hydra_demo"\ndescription = "Demo role"\ndeveloper_instructions = "Do the thing.\\n"\n',
        )
        item = {"path": ".codex/agents/hydra-demo.toml", "kind": "agent", "detail": ""}
        target = reclaim.promote_surface(paths, item)
        self.assertEqual(target, paths.hydra / "capabilities/agents/demo/agent.md")
        self.assertEqual(target.read_text(encoding="utf-8"), "Do the thing.\n")
        metadata = (paths.hydra / "capabilities/agents/demo/metadata.yaml").read_text(encoding="utf-8")
        self.assertIn("capability_class: fast-default", metadata)
        self.assertFalse((paths.root / item["path"]).exists())

    def test_retry_removes_source_only_when_metadata_matches(self):
        paths = _paths()
        _write(paths.root, ".claude/skills/deploy/SKILL.md", "content\n")
        _write(paths.root, ".hydra-framework/capabilities/skills/deploy/skill.md", "content\n")
        _write(
            paths.root,
            ".hydra-framework/capabilities/skills/deploy/metadata.yaml",
            "name: deploy\npromoted_from: .claude/skills/deploy/SKILL.md\n",
        )
        item = {"path": ".claude/skills/deploy/SKILL.md", "kind": "skill", "detail": ""}
        target = reclaim.promote_surface(paths, item)
        self.assertEqual(target, paths.hydra / "capabilities/skills/deploy/skill.md")
        self.assertFalse((paths.root / item["path"]).exists())

    def test_skips_when_canonical_target_already_exists(self):
        paths = _paths()
        _write(paths.root, ".claude/skills/deploy/SKILL.md", "content\n")
        _write(paths.root, ".hydra-framework/capabilities/skills/deploy/skill.md", "already here\n")
        item = {"path": ".claude/skills/deploy/SKILL.md", "kind": "skill", "detail": ""}
        self.assertIsNone(reclaim.promote_surface(paths, item))
        self.assertTrue((paths.root / item["path"]).exists())


class ProviderSurfaceNoticeTests(unittest.TestCase):
    def test_non_provider_paths_produce_no_notice(self):
        paths = _paths()
        self.assertEqual(reclaim.provider_surface_notice(paths, paths.root / "README.md"), [])
        self.assertEqual(reclaim.provider_surface_notice(paths, Path("/etc/hosts")), [])

    def test_ignored_names_produce_no_notice(self):
        paths = _paths()
        self.assertEqual(reclaim.provider_surface_notice(paths, paths.root / ".claude/skills/README.md"), [])

    def test_orphaned_file_produces_a_promotion_notice(self):
        paths = _paths()
        edited = paths.root / ".claude/skills/deploy/SKILL.md"
        _write(paths.root, ".claude/skills/deploy/SKILL.md", "content\n")
        notice = reclaim.provider_surface_notice(paths, edited)
        self.assertTrue(notice)
        self.assertIn("no canonical Hydra source", notice[0])
        self.assertIn("hydra.py reclaim --promote", notice[-1])


def _demo_skill(paths: ProvidersPaths) -> None:
    _write(
        paths.root,
        ".hydra-framework/capabilities/skills/demo-skill/metadata.yaml",
        "name: demo-skill\ndescription: Use when relevant.\nkind: procedure\n",
    )
    _write(paths.root, ".hydra-framework/capabilities/skills/demo-skill/skill.md", "# Demo Skill\n\nBody.\n")


class StaleWrapperNoticesTests(unittest.TestCase):
    def test_names_the_exact_directory_and_removal_command(self):
        paths = _paths()
        _write(paths.root, ".claude/skills/hydra-foo/SKILL.md", "content\n")
        lines = reclaim.stale_wrapper_notices(paths, "foo", "skill")
        self.assertTrue(any("stale: .claude/skills/hydra-foo/SKILL.md" in line for line in lines))
        self.assertTrue(any("rm -rf .claude/skills/hydra-foo/" in line for line in lines))

    def test_nothing_materialized_produces_no_notice(self):
        paths = _paths()
        self.assertEqual(reclaim.stale_wrapper_notices(paths, "foo", "skill"), [])


class ReconcileExportTests(unittest.TestCase):
    def test_no_selection_reconciles_the_full_catalog(self):
        paths = _paths()
        _demo_skill(paths)
        plan = reclaim.reconcile_export(paths)
        self.assertIsNone(plan.abort_reason)
        self.assertEqual(len(plan.created), len(plan.contents))
        self.assertEqual(plan.changed, ())
        self.assertEqual(plan.removable, ())

    def test_narrowing_after_a_prior_export_plans_removal(self):
        paths = _paths()
        _demo_skill(paths)
        full = reclaim.reconcile_export(paths)
        for path, content in full.contents.items():
            _write(paths.root, path.relative_to(paths.root).as_posix(), content)
        narrowed = reclaim.reconcile_export(paths, selection_skills=[])
        self.assertIsNone(narrowed.abort_reason)
        self.assertEqual(narrowed.created, ())
        self.assertEqual(narrowed.changed, ())
        members = {member for unit in narrowed.removable for member in unit.members}
        self.assertIn(paths.root / ".claude/skills/hydra-demo-skill/SKILL.md", members)

    def test_an_orphaned_surface_aborts_without_mutation(self):
        paths = _paths()
        _demo_skill(paths)
        _write(paths.root, ".claude/skills/deploy/SKILL.md", "content\n")
        plan = reclaim.reconcile_export(paths)
        self.assertIsNotNone(plan.abort_reason)
        self.assertIn("orphaned", plan.abort_reason)
        self.assertFalse((paths.root / ".claude/skills/hydra-demo-skill").exists())

    def test_a_drifted_surface_aborts_without_mutation(self):
        paths = _paths()
        _demo_skill(paths)
        full = reclaim.reconcile_export(paths)
        for path, content in full.contents.items():
            _write(paths.root, path.relative_to(paths.root).as_posix(), content)
        edited = paths.root / ".claude/skills/hydra-demo-skill/SKILL.md"
        edited.write_text(edited.read_text(encoding="utf-8") + "\nExtra.\n", encoding="utf-8")
        plan = reclaim.reconcile_export(paths)
        self.assertIsNotNone(plan.abort_reason)
        self.assertIn("drifted", plan.abort_reason)

    def test_a_symlinked_create_target_aborts_without_mutation(self):
        paths = _paths()
        _demo_skill(paths)
        (paths.root / ".claude/skills").mkdir(parents=True)
        outside = Path(tempfile.mkdtemp(prefix="providers-reclaim-outside-"))
        (paths.root / ".claude/skills/hydra-demo-skill").symlink_to(outside, target_is_directory=True)
        plan = reclaim.reconcile_export(paths)
        self.assertIsNotNone(plan.abort_reason)
        self.assertIn("containment", plan.abort_reason)
        self.assertFalse((outside / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
