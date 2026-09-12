"""Mirror test for `hydra_engine.commands.providers`."""

from __future__ import annotations

import argparse
import contextlib
import io as stdlib_io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.commands import providers  # noqa: E402
from hydra_engine.documents import tokens as tokens_module  # noqa: E402
from hydra_engine.providers.paths import ProvidersPaths  # noqa: E402


def _write(root: Path, rel: str, content: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _paths_with_one_skill() -> ProvidersPaths:
    root = Path(tempfile.mkdtemp(prefix="commands-providers-"))
    _write(
        root,
        ".hydra-framework/capabilities/skills/demo-skill/metadata.yaml",
        "name: demo-skill\ndescription: Use when relevant.\nkind: procedure\n",
    )
    _write(root, ".hydra-framework/capabilities/skills/demo-skill/skill.md", "# Demo Skill\n\nBody.\n")
    return ProvidersPaths(root=root, hydra=root / ".hydra-framework")


def _paths_with_profiles() -> ProvidersPaths:
    paths = _paths_with_one_skill()
    _write(
        paths.root,
        ".hydra-framework/capabilities/profiles.yaml",
        "schema: hydra-framework.capability-profiles.v1\nbaseline_tags: []\ndefault_profile: narrow\nprofiles:\n  narrow:\n    tags:\n      - narrow\n",
    )
    _write(
        paths.root,
        ".hydra-framework/capabilities/skills/demo-skill/metadata.yaml",
        "name: demo-skill\ndescription: Use when relevant.\nkind: procedure\ntags:\n  - narrow\n",
    )
    return paths


class CommandExportAdaptersTests(unittest.TestCase):
    def test_dry_run_reports_creates_without_writing(self):
        paths = _paths_with_one_skill()
        args = argparse.Namespace(check=False, dry_run=True)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_export_adapters(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("would write", out.getvalue())
        self.assertFalse((paths.root / ".claude/skills/hydra-demo-skill/SKILL.md").exists())

    def test_writes_generated_files(self):
        paths = _paths_with_one_skill()
        args = argparse.Namespace(check=False, dry_run=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_export_adapters(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue((paths.root / ".claude/skills/hydra-demo-skill/SKILL.md").exists())

    def test_export_never_deletes_an_unplanned_file(self):
        paths = _paths_with_one_skill()
        unrelated = paths.root / ".claude/skills/unrelated/SKILL.md"
        _write(paths.root, ".claude/skills/unrelated/SKILL.md", "keep me\n")
        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            providers.command_export_adapters(argparse.Namespace(check=False, dry_run=False), paths)
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "keep me\n")

    def test_check_reports_drift_and_fails(self):
        paths = _paths_with_one_skill()
        args = argparse.Namespace(check=True, dry_run=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_export_adapters(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("drift detected", out.getvalue())

    def test_check_passes_once_up_to_date(self):
        paths = _paths_with_one_skill()
        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            providers.command_export_adapters(argparse.Namespace(check=False, dry_run=False), paths)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_export_adapters(argparse.Namespace(check=True, dry_run=False), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("up to date", out.getvalue())

    def test_profile_preview_is_dry_run_only_and_does_not_write(self):
        paths = _paths_with_profiles()
        args = argparse.Namespace(check=False, dry_run=True, profile="narrow")
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_export_adapters(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("would write", out.getvalue())
        self.assertFalse((paths.root / ".claude/skills/hydra-demo-skill/SKILL.md").exists())

    def test_profile_preview_refuses_mutation(self):
        paths = _paths_with_profiles()
        args = argparse.Namespace(check=False, dry_run=False, profile="narrow")
        err = stdlib_io.StringIO()
        with contextlib.redirect_stderr(err):
            result = providers.command_export_adapters(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("preview-only", err.getvalue())


class CommandProfileTests(unittest.TestCase):
    def test_list_marks_local_shadow_and_show_reports_untagged(self):
        paths = _paths_with_profiles()
        _write(
            paths.root,
            ".hydra-framework.local/capabilities/profiles.yaml",
            "schema: hydra-framework.local-capability-profiles.v1\nprofiles:\n  narrow:\n    tags:\n      - local\n",
        )
        _write(
            paths.root,
            ".hydra-framework/capabilities/agents/demo/metadata.yaml",
            "name: demo\ndependencies:\n  skills:\n    - demo-skill\n",
        )
        _write(paths.root, ".hydra-framework/capabilities/agents/demo/agent.md", "# Demo\n")
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_profile_list(paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("narrow: local (local; shadows shared)", out.getvalue())
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_profile_show(argparse.Namespace(profile="narrow", untagged=False), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Unmaterialized declared skill dependencies", out.getvalue())
        self.assertIn("- demo-skill", out.getvalue())
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_profile_show(argparse.Namespace(profile="full", untagged=True), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Untagged skills: 0", out.getvalue())


class CommandReclaimTests(unittest.TestCase):
    def test_no_findings_reports_all_generated(self):
        root = Path(tempfile.mkdtemp(prefix="commands-reclaim-"))
        paths = ProvidersPaths(root=root, hydra=root / ".hydra-framework")
        args = argparse.Namespace(json=False, promote=False, fail_on_findings=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_reclaim(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("All provider files are generated", out.getvalue())

    def test_orphaned_reports_findings_and_respects_fail_on_findings(self):
        root = Path(tempfile.mkdtemp(prefix="commands-reclaim-orphaned-"))
        _write(root, ".claude/skills/deploy/SKILL.md", "content\n")
        paths = ProvidersPaths(root=root, hydra=root / ".hydra-framework")
        args = argparse.Namespace(json=False, promote=False, fail_on_findings=True)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_reclaim(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("orphaned: 1", out.getvalue())

    def test_promote_moves_orphaned_files_into_canonical_hydra(self):
        root = Path(tempfile.mkdtemp(prefix="commands-reclaim-promote-"))
        _write(root, ".claude/skills/deploy/SKILL.md", "---\nname: deploy\n---\nBody.\n")
        paths = ProvidersPaths(root=root, hydra=root / ".hydra-framework")
        args = argparse.Namespace(json=False, promote=True, fail_on_findings=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_reclaim(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue((paths.hydra / "capabilities/skills/deploy/skill.md").exists())
        self.assertIn("promoted:", out.getvalue())

    def test_json_flag_short_circuits_to_a_json_report(self):
        root = Path(tempfile.mkdtemp(prefix="commands-reclaim-json-"))
        paths = ProvidersPaths(root=root, hydra=root / ".hydra-framework")
        args = argparse.Namespace(json=True, promote=False, fail_on_findings=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_reclaim(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out.getvalue().strip(), "[]")


def _paths_two_skills_two_profiles() -> ProvidersPaths:
    """`keep-skill` carries tag `keep`; `drop-skill` is untagged, so `full`
    materializes both and profile `keep-only` materializes only the former."""
    root = Path(tempfile.mkdtemp(prefix="commands-providers-two-skills-"))
    _write(
        root,
        ".hydra-framework/capabilities/profiles.yaml",
        "schema: hydra-framework.capability-profiles.v1\nbaseline_tags: []\ndefault_profile: full\nprofiles:\n  keep-only:\n    tags:\n      - keep\n",
    )
    _write(root, ".hydra-framework/capabilities/skills/keep-skill/metadata.yaml", "name: keep-skill\ndescription: Kept.\ntags:\n  - keep\n")
    _write(root, ".hydra-framework/capabilities/skills/keep-skill/skill.md", "# Keep Skill\n")
    _write(root, ".hydra-framework/capabilities/skills/drop-skill/metadata.yaml", "name: drop-skill\ndescription: Dropped.\n")
    _write(root, ".hydra-framework/capabilities/skills/drop-skill/skill.md", "# Drop Skill\n")
    return ProvidersPaths(root=root, hydra=root / ".hydra-framework")


def _export(paths: ProvidersPaths) -> None:
    with contextlib.redirect_stdout(stdlib_io.StringIO()):
        providers.command_export_adapters(argparse.Namespace(check=False, dry_run=False), paths)


class CommandProfileSelectTests(unittest.TestCase):
    def test_selecting_a_narrower_profile_removes_the_deselected_wrapper(self):
        paths = _paths_two_skills_two_profiles()
        _export(paths)  # materializes both under the default (`full`) profile
        self.assertTrue((paths.root / ".claude/skills/hydra-drop-skill/SKILL.md").exists())

        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = providers.command_profile_select(argparse.Namespace(name="keep-only"), paths)
        self.assertEqual(result.exit_code, 0)
        active = (paths.root / ".hydra-framework.local/capabilities/active.yaml").read_text(encoding="utf-8")
        self.assertIn("active: keep-only", active)
        self.assertFalse((paths.root / ".claude/skills/hydra-drop-skill").exists())
        self.assertFalse((paths.root / ".agents/skills/hydra-drop-skill").exists())
        self.assertTrue((paths.root / ".claude/skills/hydra-keep-skill/SKILL.md").exists())
        self.assertIn("Restart your Claude/Codex session", out.getvalue())

    def test_never_rewrites_the_hand_authored_local_profiles_file(self):
        paths = _paths_two_skills_two_profiles()
        local_profiles = "schema: hydra-framework.local-capability-profiles.v1\n# a comment a person wrote\nprofiles: {}\n"
        _write(paths.root, ".hydra-framework.local/capabilities/profiles.yaml", local_profiles)
        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            providers.command_profile_select(argparse.Namespace(name="keep-only"), paths)
        self.assertEqual(
            (paths.root / ".hydra-framework.local/capabilities/profiles.yaml").read_text(encoding="utf-8"),
            local_profiles,
        )

    def test_an_unresolvable_profile_writes_nothing_and_fails(self):
        paths = _paths_two_skills_two_profiles()
        err = stdlib_io.StringIO()
        with contextlib.redirect_stderr(err):
            result = providers.command_profile_select(argparse.Namespace(name="nope"), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertFalse((paths.root / ".hydra-framework.local/capabilities/active.yaml").exists())


class ProfileSelectCrashRecoveryTests(unittest.TestCase):
    """The four-step ordering's recovery guarantee: an ordinary
    `export-adapters` finishes the job after any interruption, because it
    recomputes the whole desired plan from `active.yaml` on every run."""

    def test_crash_between_active_yaml_and_reconciliation_is_recovered_by_export(self):
        paths = _paths_two_skills_two_profiles()
        _export(paths)
        # Construct the post-crash state directly: `active.yaml` names the
        # narrower profile while the tree still holds the old profile's
        # adapters -- exactly what step 3 completing and step 4 never
        # starting looks like on disk.
        _write(
            paths.root,
            ".hydra-framework.local/capabilities/active.yaml",
            "schema: hydra-framework.local-capability-selection.v1\nactive: keep-only\n",
        )
        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            result = providers.command_export_adapters(argparse.Namespace(check=False, dry_run=False), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertFalse((paths.root / ".claude/skills/hydra-drop-skill").exists())
        self.assertTrue((paths.root / ".claude/skills/hydra-keep-skill/SKILL.md").exists())

    def test_crash_partway_through_creating_adapters_converges_on_rerun(self):
        # Switch narrow -> full, which must *create* drop-skill's wrapper
        # files (create precedes remove in the approved ordering, and this
        # switch has nothing to remove), and crash on the first one.
        paths = _paths_two_skills_two_profiles()
        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            providers.command_profile_select(argparse.Namespace(name="keep-only"), paths)
        self.assertFalse((paths.root / ".claude/skills/hydra-drop-skill").exists())

        def _crash(path):
            if "active.yaml" not in str(path):
                raise RuntimeError("simulated crash mid-reconcile")

        with mock.patch.object(tokens_module, "_before_replace", _crash):
            with self.assertRaises(RuntimeError):
                providers.command_profile_select(argparse.Namespace(name="full"), paths)

        # Step 3 (the commit point) landed even though step 4 crashed.
        active = (paths.root / ".hydra-framework.local/capabilities/active.yaml").read_text(encoding="utf-8")
        self.assertIn("active: full", active)

        # `--check` reports drift in this window, never "up to date".
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            check_result = providers.command_export_adapters(argparse.Namespace(check=True, dry_run=False), paths)
        self.assertEqual(check_result.exit_code, 1)
        self.assertIn("drift detected", out.getvalue())

        # A crash releases the lock; recovery needs nothing but this.
        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            result = providers.command_export_adapters(argparse.Namespace(check=False, dry_run=False), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue((paths.root / ".claude/skills/hydra-drop-skill/SKILL.md").exists())
        self.assertTrue((paths.root / ".claude/skills/hydra-keep-skill/SKILL.md").exists())

        # Rerun after successful recovery is a no-op.
        out2 = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out2):
            providers.command_export_adapters(argparse.Namespace(check=False, dry_run=False), paths)
        self.assertIn("already current", out2.getvalue())

    def test_crash_partway_through_removal_converges_on_rerun(self):
        # Switch full -> keep-only, which must *remove* drop-skill's wrapper
        # (removal is `Path.unlink`, not `write_text`, so this crash point
        # uses a targeted patch rather than the `_before_replace` seam).
        paths = _paths_two_skills_two_profiles()
        _export(paths)

        real_unlink = Path.unlink
        calls = []

        def _crashing_unlink(self, *args, **kwargs):
            calls.append(self)
            if len(calls) == 1:
                raise RuntimeError("simulated crash mid-removal")
            return real_unlink(self, *args, **kwargs)

        with mock.patch.object(Path, "unlink", _crashing_unlink):
            with self.assertRaises(RuntimeError):
                providers.command_profile_select(argparse.Namespace(name="keep-only"), paths)

        active = (paths.root / ".hydra-framework.local/capabilities/active.yaml").read_text(encoding="utf-8")
        self.assertIn("active: keep-only", active)

        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            result = providers.command_export_adapters(argparse.Namespace(check=False, dry_run=False), paths)
        self.assertEqual(result.exit_code, 0)
        self.assertFalse((paths.root / ".claude/skills/hydra-drop-skill").exists())
        self.assertFalse((paths.root / ".agents/skills/hydra-drop-skill").exists())
        self.assertTrue((paths.root / ".claude/skills/hydra-keep-skill/SKILL.md").exists())

    def test_validation_failure_writes_nothing_and_exits_non_zero(self):
        paths = _paths_two_skills_two_profiles()
        active_path = paths.root / ".hydra-framework.local/capabilities/active.yaml"
        with contextlib.redirect_stderr(stdlib_io.StringIO()):
            result = providers.command_profile_select(argparse.Namespace(name="does-not-exist"), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertFalse(active_path.exists())


class ExportAdaptersLockTests(unittest.TestCase):
    def test_mutation_is_refused_with_no_platform_lock_mechanism(self):
        paths = _paths_with_one_skill()
        from hydra_engine.ports import lock as lock_module

        err = stdlib_io.StringIO()
        with mock.patch.object(lock_module, "fcntl", None), mock.patch.object(lock_module, "msvcrt", None):
            with contextlib.redirect_stderr(err):
                result = providers.command_export_adapters(argparse.Namespace(check=False, dry_run=False), paths)
        self.assertEqual(result.exit_code, 1)
        self.assertFalse((paths.root / ".claude/skills/hydra-demo-skill").exists())

    def test_check_dry_run_and_profile_show_still_work_with_no_lock_mechanism(self):
        paths = _paths_with_profiles()
        from hydra_engine.ports import lock as lock_module

        with mock.patch.object(lock_module, "fcntl", None), mock.patch.object(lock_module, "msvcrt", None):
            with contextlib.redirect_stdout(stdlib_io.StringIO()):
                dry_run = providers.command_export_adapters(argparse.Namespace(check=False, dry_run=True), paths)
                check = providers.command_export_adapters(argparse.Namespace(check=True, dry_run=False), paths)
                show = providers.command_profile_show(argparse.Namespace(profile="full", untagged=False), paths)
        self.assertEqual(dry_run.exit_code, 0)
        self.assertEqual(check.exit_code, 1)  # drift: nothing generated yet
        self.assertEqual(show.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
