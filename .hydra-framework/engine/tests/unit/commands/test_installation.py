"""Mirror test for `hydra_engine.commands.installation`."""

from __future__ import annotations

import argparse
import contextlib
import io as stdlib_io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.commands import installation  # noqa: E402
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
    root = Path(tempfile.mkdtemp(prefix="commands-installation-"))
    hydra = root / ".hydra-framework"
    return (
        InstallationPaths(root=root, hydra=hydra),
        ProvidersPaths(root=root, hydra=hydra),
        ContextCompilerPaths(root=root, hydra=hydra),
    )


def _seed_required_paths(root: Path) -> None:
    for rel in adopt.REQUIRED_PATHS:
        if rel.endswith((".md", ".yaml", ".json")):
            _write(root, rel, "placeholder\n")
        else:
            (root / rel).mkdir(parents=True, exist_ok=True)


class CommandAdoptTests(unittest.TestCase):
    def test_happy_path_reports_integrity_present(self):
        paths, providers_paths, context_compiler_paths = _all_paths()
        _seed_required_paths(paths.root)
        args = argparse.Namespace(record=False, repo="")
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = installation.command_adopt(args, paths, providers_paths, context_compiler_paths, manifest={})
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Framework integrity: required paths present", out.getvalue())
        self.assertIn("not recorded. Run `hydra.py adopt --record --repo <slug>`.", out.getvalue())
        self.assertIn("Preview a capability profile", out.getvalue())

    def test_missing_paths_reports_incomplete_copy(self):
        paths, providers_paths, context_compiler_paths = _all_paths()
        args = argparse.Namespace(record=False, repo="")
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = installation.command_adopt(args, paths, providers_paths, context_compiler_paths, manifest={})
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Framework integrity: INCOMPLETE COPY", out.getvalue())
        self.assertIn("- missing: AI_SYSTEM.md", out.getvalue())

    def test_record_missing_paths_refuses_on_stderr(self):
        paths, providers_paths, context_compiler_paths = _all_paths()
        args = argparse.Namespace(record=True, repo="example")
        err = stdlib_io.StringIO()
        with contextlib.redirect_stderr(err):
            result = installation.command_adopt(args, paths, providers_paths, context_compiler_paths, manifest={})
        self.assertEqual(result.exit_code, 1)
        self.assertIn("refusing to record lineage", err.getvalue())

    def test_record_already_recorded(self):
        paths, providers_paths, context_compiler_paths = _all_paths()
        _seed_required_paths(paths.root)
        args = argparse.Namespace(record=True, repo="example")
        manifest = {"lineage": {"adopted_into": "already-here"}}
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = installation.command_adopt(args, paths, providers_paths, context_compiler_paths, manifest)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("lineage already recorded for `already-here`", out.getvalue())

    def test_record_writes_lineage_and_reports_path(self):
        paths, providers_paths, context_compiler_paths = _all_paths()
        _seed_required_paths(paths.root)
        _write(paths.root, ".hydra-framework/manifest.yaml", "seed_version: 0.3.0\n")
        args = argparse.Namespace(record=True, repo="Example Repo")
        manifest = {"seed_version": "0.3.0"}
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = installation.command_adopt(args, paths, providers_paths, context_compiler_paths, manifest)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("recorded lineage for `example-repo`", out.getvalue())
        self.assertIn("lineage:", paths.manifest_path().read_text(encoding="utf-8"))


class CommandInitTests(unittest.TestCase):
    def test_target_not_a_directory_refuses(self):
        paths, _providers, _context = _all_paths()
        args = argparse.Namespace(target=str(paths.root / "nope"), force=False, dry_run=False)
        err = stdlib_io.StringIO()
        with contextlib.redirect_stderr(err):
            result = installation.command_init(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("target is not a directory", err.getvalue())

    def test_target_is_current_repository_refuses(self):
        paths, _providers, _context = _all_paths()
        args = argparse.Namespace(target=str(paths.root), force=False, dry_run=False)
        err = stdlib_io.StringIO()
        with contextlib.redirect_stderr(err):
            result = installation.command_init(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("target is the current repository", err.getvalue())

    def test_nothing_to_copy_when_no_sources_exist(self):
        paths, _providers, _context = _all_paths()
        target = Path(tempfile.mkdtemp(prefix="init-target-"))
        args = argparse.Namespace(target=str(target), force=False, dry_run=False)
        err = stdlib_io.StringIO()
        with contextlib.redirect_stderr(err):
            result = installation.command_init(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("nothing to copy", err.getvalue())

    def test_conflicts_without_force_are_reported(self):
        paths, _providers, _context = _all_paths()
        _write(paths.root, "AI_SYSTEM.md", "# AI System\n")
        target = Path(tempfile.mkdtemp(prefix="init-target-"))
        _write(target, "AI_SYSTEM.md", "# Existing\n")
        args = argparse.Namespace(target=str(target), force=False, dry_run=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = installation.command_init(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("already exist in the target", out.getvalue())
        self.assertEqual((target / "AI_SYSTEM.md").read_text(encoding="utf-8"), "# Existing\n")

    def test_dry_run_reports_without_copying(self):
        paths, _providers, _context = _all_paths()
        _write(paths.root, "AI_SYSTEM.md", "# AI System\n")
        target = Path(tempfile.mkdtemp(prefix="init-target-"))
        args = argparse.Namespace(target=str(target), force=False, dry_run=True)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = installation.command_init(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("would copy", out.getvalue())
        self.assertFalse((target / "AI_SYSTEM.md").exists())

    def test_copies_files_and_reports_next_steps(self):
        paths, _providers, _context = _all_paths()
        _write(paths.root, "AI_SYSTEM.md", "# AI System\n")
        _write(paths.root, "AGENTS.md", "# AGENTS\n")
        target = Path(tempfile.mkdtemp(prefix="init-target-"))
        args = argparse.Namespace(target=str(target), force=False, dry_run=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = installation.command_init(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual((target / "AI_SYSTEM.md").read_text(encoding="utf-8"), "# AI System\n")
        self.assertIn("hydra.py adopt", out.getvalue())

    def test_force_overwrites_conflicts(self):
        paths, _providers, _context = _all_paths()
        _write(paths.root, "AI_SYSTEM.md", "# New\n")
        target = Path(tempfile.mkdtemp(prefix="init-target-"))
        _write(target, "AI_SYSTEM.md", "# Old\n")
        args = argparse.Namespace(target=str(target), force=True, dry_run=False)
        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            result = installation.command_init(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual((target / "AI_SYSTEM.md").read_text(encoding="utf-8"), "# New\n")


class CommandInstallHooksTests(unittest.TestCase):
    def _git_paths(self) -> InstallationPaths:
        paths, _providers, _context = _all_paths()
        subprocess.run(["git", "init", "-q"], cwd=str(paths.root), check=True)
        return paths

    def test_missing_hooks_dir_refuses(self):
        paths = self._git_paths()
        args = argparse.Namespace(uninstall=False)
        err = stdlib_io.StringIO()
        with contextlib.redirect_stderr(err):
            result = installation.command_install_hooks(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("no hooks directory", err.getvalue())

    def test_install_sets_hooks_path_and_lists_hooks(self):
        paths = self._git_paths()
        _write(paths.root, ".hydra-framework/hooks/pre-push", "#!/bin/sh\necho hi\n")
        args = argparse.Namespace(uninstall=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = installation.command_install_hooks(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("core.hooksPath -> .hydra-framework/hooks", out.getvalue())
        self.assertIn("- pre-push", out.getvalue())
        configured = subprocess.run(
            ["git", "config", "core.hooksPath"], cwd=str(paths.root), capture_output=True, text=True, check=True
        )
        self.assertEqual(configured.stdout.strip(), ".hydra-framework/hooks")

    def test_uninstall_removes_hooks_path(self):
        paths = self._git_paths()
        _write(paths.root, ".hydra-framework/hooks/pre-push", "#!/bin/sh\necho hi\n")
        install_args = argparse.Namespace(uninstall=False)
        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            installation.command_install_hooks(install_args, paths)

        args = argparse.Namespace(uninstall=True)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = installation.command_install_hooks(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("removed core.hooksPath", out.getvalue())
        configured = subprocess.run(
            ["git", "config", "core.hooksPath"], cwd=str(paths.root), capture_output=True, text=True
        )
        self.assertNotEqual(configured.returncode, 0)


if __name__ == "__main__":
    unittest.main()
