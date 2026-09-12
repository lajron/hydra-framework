"""Mirror test for `hydra_engine.providers.adapter_plan`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.providers.adapter_plan import (  # noqa: E402
    LockUnavailableError,
    acquire_export_lock,
    apply_reconcile_plan,
    candidate_removals,
    ownership_paths,
    path_is_contained,
    planned_adapter_files,
)
from hydra_engine.providers.capabilities import PROVIDERS  # noqa: E402
from hydra_engine.providers.paths import ProvidersPaths  # noqa: E402


def _write(root: Path, rel: str, content: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _paths_with_one_skill() -> ProvidersPaths:
    root = Path(tempfile.mkdtemp(prefix="providers-adapter-plan-"))
    _write(
        root,
        ".hydra-framework/capabilities/skills/demo-skill/metadata.yaml",
        "name: demo-skill\ndescription: Use when relevant.\nkind: procedure\n",
    )
    _write(root, ".hydra-framework/capabilities/skills/demo-skill/skill.md", "# Demo Skill\n\nBody.\n")
    return ProvidersPaths(root=root, hydra=root / ".hydra-framework")


class PlannedAdapterFilesTests(unittest.TestCase):
    def test_provider_registry_has_expected_adapter_targets(self):
        self.assertEqual(
            [(provider.slug, provider.skills_target, provider.agents_target, provider.agent_extension) for provider in PROVIDERS],
            [("claude", ".claude/skills", ".claude/agents", ".md"), ("codex", ".agents/skills", ".codex/agents", ".toml")],
        )
    def test_plans_a_skill_wrapper_for_every_adapter_target(self):
        paths = _paths_with_one_skill()
        plan = planned_adapter_files(paths)
        claude_skill = paths.root / ".claude/skills/hydra-demo-skill/SKILL.md"
        codex_skill = paths.root / ".agents/skills/hydra-demo-skill/SKILL.md"
        self.assertIn(claude_skill, plan)
        self.assertIn(codex_skill, plan)
        self.assertIn("# Demo Skill", plan[claude_skill])

    def test_every_generated_body_has_a_provenance_sidecar(self):
        paths = _paths_with_one_skill()
        plan = planned_adapter_files(paths)
        bodies = [path for path in plan if path.name == "SKILL.md"]
        self.assertTrue(bodies)
        for body in bodies:
            sidecar = body.parent / ".hydra-adapter.yaml"
            self.assertIn(sidecar, plan)
            self.assertIn("canonical_source: .hydra-framework/capabilities/skills/demo-skill/skill.md", plan[sidecar])

    def test_empty_modules_produce_an_empty_plan(self):
        root = Path(tempfile.mkdtemp(prefix="providers-adapter-plan-empty-"))
        paths = ProvidersPaths(root=root, hydra=root / ".hydra-framework")
        self.assertEqual(planned_adapter_files(paths), {})

    def test_selection_filters_skills_but_never_agents(self):
        paths = _paths_with_one_skill()
        _write(paths.root, ".hydra-framework/capabilities/agents/demo-agent/metadata.yaml", "name: demo-agent\ndescription: Use for the role.\n")
        _write(paths.root, ".hydra-framework/capabilities/agents/demo-agent/agent.md", "# Demo Agent\n\nBody.\n")
        plan = planned_adapter_files(paths, selection=[])
        self.assertFalse(any("hydra-demo-skill" in str(path) for path in plan))
        self.assertTrue(any("hydra-demo-agent" in str(path) for path in plan))

    def test_ownership_paths_are_the_full_plan_identity(self):
        paths = _paths_with_one_skill()
        self.assertEqual(ownership_paths(paths), frozenset(planned_adapter_files(paths)))

    def test_each_provider_gets_its_own_registered_agent_wrapper_form(self):
        # `PROVIDERS`' `build_agent_wrapper` field replaced an
        # `if provider == "codex":` branch here; this proves the field-based
        # dispatch still produces Codex TOML and Claude Markdown, not that
        # both providers silently got the same renderer.
        paths = _paths_with_one_skill()
        _write(
            paths.root,
            ".hydra-framework/capabilities/agents/demo-agent/metadata.yaml",
            "name: demo-agent\ndescription: Use for the role.\n",
        )
        _write(paths.root, ".hydra-framework/capabilities/agents/demo-agent/agent.md", "# Demo Agent\n\nBody.\n")
        plan = planned_adapter_files(paths)
        claude_agent = paths.root / ".claude/agents/hydra-demo-agent.md"
        codex_agent = paths.root / ".codex/agents/hydra-demo-agent.toml"
        self.assertIn(claude_agent, plan)
        self.assertIn(codex_agent, plan)
        self.assertIn("developer_instructions =", plan[codex_agent])


def _export_full(paths: ProvidersPaths) -> None:
    """Simulate a prior successful `export-adapters` run: write the whole
    full plan to disk, so a later narrowing has something to remove."""
    for path, content in planned_adapter_files(paths).items():
        _write(paths.root, path.relative_to(paths.root).as_posix(), content)


class PathIsContainedTests(unittest.TestCase):
    def test_ordinary_path_under_root_is_contained(self):
        root = Path(tempfile.mkdtemp(prefix="containment-"))
        self.assertTrue(path_is_contained(root / "a" / "b.txt", root))

    def test_a_path_outside_root_is_refused(self):
        root = Path(tempfile.mkdtemp(prefix="containment-"))
        self.assertFalse(path_is_contained(Path("/definitely/outside"), root))

    def test_refuses_when_an_intermediate_component_is_a_symlink(self):
        root = Path(tempfile.mkdtemp(prefix="containment-"))
        outside = Path(tempfile.mkdtemp(prefix="containment-outside-"))
        (root / "wrapper-real").mkdir()
        (root / "wrapper").symlink_to(outside, target_is_directory=True)
        self.assertFalse(path_is_contained(root / "wrapper" / "SKILL.md", root))

    def test_refuses_when_the_target_itself_is_an_existing_symlink(self):
        root = Path(tempfile.mkdtemp(prefix="containment-"))
        target = root / "real.txt"
        target.write_text("x", encoding="utf-8")
        link = root / "link.txt"
        link.symlink_to(target)
        self.assertFalse(path_is_contained(link, root))

    def test_a_target_that_does_not_yet_exist_may_still_be_contained(self):
        root = Path(tempfile.mkdtemp(prefix="containment-"))
        self.assertTrue(path_is_contained(root / "new" / "file.txt", root))


class CandidateRemovalsTests(unittest.TestCase):
    def test_deselected_skill_wrapper_is_removable(self):
        paths = _paths_with_one_skill()
        _export_full(paths)
        desired = planned_adapter_files(paths, selection=[])
        removable, kept = candidate_removals(paths, ownership_paths(paths), desired)
        self.assertEqual(kept, [])
        members = {member for unit in removable for member in unit.members}
        self.assertIn(paths.root / ".claude/skills/hydra-demo-skill/SKILL.md", members)
        self.assertIn(paths.root / ".claude/skills/hydra-demo-skill/.hydra-adapter.yaml", members)
        self.assertIn(paths.root / ".agents/skills/hydra-demo-skill/SKILL.md", members)
        directories = {unit.directory for unit in removable}
        self.assertIn(paths.root / ".claude/skills/hydra-demo-skill", directories)

    def test_unchanged_skill_has_nothing_removable(self):
        paths = _paths_with_one_skill()
        _export_full(paths)
        desired = planned_adapter_files(paths)
        removable, kept = candidate_removals(paths, ownership_paths(paths), desired)
        self.assertEqual(removable, [])
        self.assertEqual(kept, [])

    def test_a_renamed_wrapper_directory_is_never_removed(self):
        # The wrapper directory no longer matches `hydra-<canonical-name>`,
        # so `ownership_paths()` never contains it in the first place: it is
        # not merely refused, it is invisible to removal from the start.
        paths = _paths_with_one_skill()
        _export_full(paths)
        renamed = paths.root / ".claude/skills/hydra-demo-skill"
        renamed.rename(paths.root / ".claude/skills/hydra-renamed-skill")
        desired = planned_adapter_files(paths, selection=[])
        removable, kept = candidate_removals(paths, ownership_paths(paths), desired)
        members = {member for unit in removable for member in unit.members}
        self.assertFalse(any("hydra-renamed-skill" in str(member) for member in members))
        self.assertFalse(any("hydra-renamed-skill" in label for label, _ in kept))

    def test_a_hand_added_file_in_the_wrapper_directory_blocks_removal(self):
        paths = _paths_with_one_skill()
        _export_full(paths)
        (paths.root / ".claude/skills/hydra-demo-skill/reference.txt").write_text("mine\n", encoding="utf-8")
        desired = planned_adapter_files(paths, selection=[])
        removable, kept = candidate_removals(paths, ownership_paths(paths), desired)
        claude_units = [unit for unit in removable if unit.directory == paths.root / ".claude/skills/hydra-demo-skill"]
        self.assertEqual(claude_units, [])
        self.assertTrue(any("hydra-demo-skill" in label and "did not generate" in reason for label, reason in kept))
        # Never partially emptied: both generated files are still present.
        self.assertTrue((paths.root / ".claude/skills/hydra-demo-skill/SKILL.md").exists())
        self.assertTrue((paths.root / ".claude/skills/hydra-demo-skill/.hydra-adapter.yaml").exists())

    def test_a_malformed_sidecar_refuses_removal(self):
        paths = _paths_with_one_skill()
        _export_full(paths)
        sidecar = paths.root / ".claude/skills/hydra-demo-skill/.hydra-adapter.yaml"
        sidecar.write_text("not: a valid adapter sidecar\n", encoding="utf-8")
        desired = planned_adapter_files(paths, selection=[])
        removable, kept = candidate_removals(paths, ownership_paths(paths), desired)
        claude_units = [unit for unit in removable if unit.directory == paths.root / ".claude/skills/hydra-demo-skill"]
        self.assertEqual(claude_units, [])
        self.assertTrue(any("hydra-demo-skill" in label for label, _ in kept))

    def test_a_sidecar_disagreeing_on_provider_refuses_removal(self):
        paths = _paths_with_one_skill()
        _export_full(paths)
        sidecar = paths.root / ".claude/skills/hydra-demo-skill/.hydra-adapter.yaml"
        sidecar.write_text(
            "schema: hydra-framework.adapter.v2\nprovider: codex\nkind: skill\n"
            "canonical_source: .hydra-framework/capabilities/skills/demo-skill/skill.md\ngenerated_file: SKILL.md\n",
            encoding="utf-8",
        )
        desired = planned_adapter_files(paths, selection=[])
        removable, kept = candidate_removals(paths, ownership_paths(paths), desired)
        claude_units = [unit for unit in removable if unit.directory == paths.root / ".claude/skills/hydra-demo-skill"]
        self.assertEqual(claude_units, [])

    def test_canonical_source_outside_capabilities_refuses_removal(self):
        paths = _paths_with_one_skill()
        _export_full(paths)
        sidecar = paths.root / ".claude/skills/hydra-demo-skill/.hydra-adapter.yaml"
        sidecar.write_text(
            "schema: hydra-framework.adapter.v2\nprovider: claude\nkind: skill\n"
            "canonical_source: AI_SYSTEM.md\ngenerated_file: SKILL.md\n",
            encoding="utf-8",
        )
        desired = planned_adapter_files(paths, selection=[])
        removable, kept = candidate_removals(paths, ownership_paths(paths), desired)
        claude_units = [unit for unit in removable if unit.directory == paths.root / ".claude/skills/hydra-demo-skill"]
        self.assertEqual(claude_units, [])

    def test_canonical_source_containing_dotdot_refuses_removal(self):
        paths = _paths_with_one_skill()
        _export_full(paths)
        sidecar = paths.root / ".claude/skills/hydra-demo-skill/.hydra-adapter.yaml"
        sidecar.write_text(
            "schema: hydra-framework.adapter.v2\nprovider: claude\nkind: skill\n"
            "canonical_source: .hydra-framework/capabilities/skills/../skills/demo-skill/skill.md\ngenerated_file: SKILL.md\n",
            encoding="utf-8",
        )
        desired = planned_adapter_files(paths, selection=[])
        removable, kept = candidate_removals(paths, ownership_paths(paths), desired)
        claude_units = [unit for unit in removable if unit.directory == paths.root / ".claude/skills/hydra-demo-skill"]
        self.assertEqual(claude_units, [])

    def test_a_symlinked_wrapper_directory_refuses_removal(self):
        paths = _paths_with_one_skill()
        _export_full(paths)
        real_dir = paths.root / ".claude/skills/hydra-demo-skill"
        moved = paths.root / ".claude/skills/.moved-demo-skill"
        real_dir.rename(moved)
        real_dir.symlink_to(moved, target_is_directory=True)
        desired = planned_adapter_files(paths, selection=[])
        removable, kept = candidate_removals(paths, ownership_paths(paths), desired)
        claude_units = [unit for unit in removable if unit.directory == real_dir]
        self.assertEqual(claude_units, [])
        self.assertTrue(any("containment" in reason for label, reason in kept if "hydra-demo-skill" in label))

    def test_a_stale_wrapper_whose_canonical_skill_is_deleted_is_never_removable(self):
        paths = _paths_with_one_skill()
        _export_full(paths)
        skill_dir = paths.hydra / "capabilities/skills/demo-skill"
        (skill_dir / "skill.md").unlink()
        (skill_dir / "metadata.yaml").unlink()
        skill_dir.rmdir()
        desired = planned_adapter_files(paths)
        removable, kept = candidate_removals(paths, ownership_paths(paths), desired)
        # No export flag removes it: it left the ownership index along with
        # its canonical source, so it is not even a removal candidate.
        self.assertEqual(removable, [])
        self.assertEqual(kept, [])
        self.assertTrue((paths.root / ".claude/skills/hydra-demo-skill/SKILL.md").exists())


class ApplyReconcilePlanTests(unittest.TestCase):
    def test_applies_creates_updates_and_whole_unit_removal(self):
        paths = _paths_with_one_skill()
        _export_full(paths)
        desired = planned_adapter_files(paths, selection=[])
        removable, _kept = candidate_removals(paths, ownership_paths(paths), desired)
        from hydra_engine.providers.adapter_plan import ReconcilePlan

        plan = ReconcilePlan(desired, (), (), tuple(removable), (), None)
        apply_reconcile_plan(plan)
        self.assertFalse((paths.root / ".claude/skills/hydra-demo-skill").exists())
        self.assertFalse((paths.root / ".agents/skills/hydra-demo-skill").exists())


class AcquireExportLockTests(unittest.TestCase):
    def test_lock_lives_under_the_private_local_tier(self):
        paths = _paths_with_one_skill()
        with acquire_export_lock(paths):
            self.assertTrue((paths.root / ".hydra-framework.local/locks/export.lock").exists())

    def test_lock_unavailable_error_is_a_hydra_yaml_error(self):
        from hydra_engine.documents.tokens import HydraYamlError

        self.assertTrue(issubclass(LockUnavailableError, HydraYamlError))


if __name__ == "__main__":
    unittest.main()
