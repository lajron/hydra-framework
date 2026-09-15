"""Mirror test for `hydra_engine.commands.hooks`."""

from __future__ import annotations

import argparse
import contextlib
import io as stdlib_io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.commands import hooks  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402
from hydra_engine.providers.paths import ProvidersPaths  # noqa: E402
from hydra_engine.work.paths import WorkPaths  # noqa: E402
from v3_fixtures import write_node  # noqa: E402


def _write(root: Path, rel: str, content: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


class Bundle:
    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="commands-hooks-"))
        self.providers_paths = ProvidersPaths(root=self.root, hydra=self.root / ".hydra-framework")
        self.work_paths = WorkPaths(root=self.root, hydra=self.root / ".hydra-framework", local=self.root / ".hydra-framework.local")
        self.context_compiler_paths = ContextCompilerPaths(root=self.root, hydra=self.root / ".hydra-framework")
        write_node(self.context_compiler_paths, "demo")
        self.resolver_paths = ObjectLocations(
            root=self.root,
            hydra=self.root / ".hydra-framework",
            local=self.root / ".hydra-framework.local",
            personal_tasks_rel="tasks/personal",
            object_registry=self.root / ".hydra-framework/cognition/graph/registry.yaml",
        )

    def run(self, stdin_payload: dict, render: bool = False):
        args = argparse.Namespace(render=render)
        with mock.patch("sys.stdin", stdlib_io.StringIO(json.dumps(stdin_payload))):
            out = stdlib_io.StringIO()
            err = stdlib_io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                result = hooks.command_hook_post_edit(
                    args,
                    self.root,
                    self.providers_paths,
                    self.work_paths,
                    self.context_compiler_paths,
                    self.resolver_paths,
                    "tester",
                    "",
                )
        return result, out.getvalue(), err.getvalue()


class CommandHookPostEditTests(unittest.TestCase):
    def _register_path(self, bundle: Bundle, path: str) -> None:
        _write(bundle.root, path, "# Registered object\n")
        _write(
            bundle.root,
            ".hydra-framework/cognition/graph/registry.yaml",
            "schema: hydra-framework.object-registry.v1\n"
            "objects:\n"
            "  hydra://fixture/object:\n"
            f"    path: {path}\n",
        )

    def test_empty_stdin_is_silent_success(self):
        bundle = Bundle()
        with mock.patch("sys.stdin", stdlib_io.StringIO("")):
            result = hooks.command_hook_post_edit(
                argparse.Namespace(render=False),
                bundle.root,
                bundle.providers_paths,
                bundle.work_paths,
                bundle.context_compiler_paths,
                bundle.resolver_paths,
                "tester",
                "",
            )
        self.assertEqual(result.exit_code, 0)

    def test_registered_path_reindexes_silently(self):
        bundle = Bundle()
        self._register_path(bundle, "project-wiki/registered.md")
        with mock.patch.object(hooks, "validate_object_references", return_value=[]) as validate, mock.patch.object(
            hooks, "write_object_registry", return_value=1
        ) as write:
            result, out, err = bundle.run({"tool_input": {"file_path": "project-wiki/registered.md"}})
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out, "")
        self.assertEqual(err, "")
        validate.assert_called_once_with(bundle.resolver_paths)
        write.assert_called_once_with(bundle.resolver_paths)

    def test_unregistered_path_does_not_reindex(self):
        bundle = Bundle()
        self._register_path(bundle, "project-wiki/registered.md")
        _write(bundle.root, "project-wiki/other.md", "# Other\n")
        with mock.patch.object(hooks, "validate_object_references") as validate, mock.patch.object(
            hooks, "write_object_registry"
        ) as write:
            result, out, err = bundle.run({"tool_input": {"file_path": "project-wiki/other.md"}})
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out, "")
        self.assertEqual(err, "")
        validate.assert_not_called()
        write.assert_not_called()

    def test_missing_registry_is_not_created(self):
        bundle = Bundle()
        _write(bundle.root, "project-wiki/registered.md", "# Registered object\n")
        with mock.patch.object(hooks, "validate_object_references") as validate, mock.patch.object(
            hooks, "write_object_registry"
        ) as write:
            result, out, err = bundle.run({"tool_input": {"file_path": "project-wiki/registered.md"}})
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out, "")
        self.assertEqual(err, "")
        self.assertFalse(bundle.resolver_paths.object_registry.exists())
        validate.assert_not_called()
        write.assert_not_called()

    def test_registered_path_with_broken_object_references_does_not_rewrite_registry(self):
        bundle = Bundle()
        self._register_path(bundle, "project-wiki/registered.md")
        before = bundle.resolver_paths.object_registry.read_text(encoding="utf-8")
        with mock.patch.object(hooks, "validate_object_references", return_value=[object()]) as validate, mock.patch.object(
            hooks, "write_object_registry"
        ) as write:
            result, out, err = bundle.run({"tool_input": {"file_path": "project-wiki/registered.md"}})
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out, "")
        self.assertIn("hydra.py ref check", err)
        self.assertIn("hydra.py ref index", err)
        self.assertEqual(bundle.resolver_paths.object_registry.read_text(encoding="utf-8"), before)
        validate.assert_called_once_with(bundle.resolver_paths)
        write.assert_not_called()

    def test_hook_post_edit_still_exits_zero_after_the_import_swap(self):
        bundle = Bundle()
        edited = bundle.root / "AI_SYSTEM.md"
        _write(bundle.root, "AI_SYSTEM.md", "content\n")
        result, out, err = bundle.run({"tool_input": {"file_path": str(edited)}})
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out, "")
        self.assertEqual(err, "")

    def test_provider_surface_write_prints_a_promotion_notice(self):
        bundle = Bundle()
        edited = bundle.root / ".claude/skills/deploy/SKILL.md"
        _write(bundle.root, ".claude/skills/deploy/SKILL.md", "content\n")
        result, out, _err = bundle.run({"tool_input": {"file_path": str(edited)}})
        self.assertEqual(result.exit_code, 0)
        self.assertIn("no canonical Hydra source", out)

    def test_tier_placement_violation_prints_a_relocation_notice(self):
        bundle = Bundle()
        edited = bundle.root / ".hydra-framework/tasks/active/2026-01-01-old.md"
        _write(bundle.root, ".hydra-framework/tasks/active/2026-01-01-old.md", "content\n")
        result, out, _err = bundle.run({"tool_input": {"file_path": str(edited)}})
        self.assertEqual(result.exit_code, 0)
        self.assertIn("uses a retired task directory", out)

    def test_private_tier_file_outside_any_package_is_silent_success(self):
        bundle = Bundle()
        edited = bundle.root / ".hydra-framework.local/notes/idea.md"
        _write(bundle.root, ".hydra-framework.local/notes/idea.md", "content\n")
        result, out, _err = bundle.run({"tool_input": {"file_path": str(edited)}})
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out, "")

    def test_non_markdown_non_dot_edit_is_silent_success(self):
        bundle = Bundle()
        edited = bundle.root / "README.txt"
        _write(bundle.root, "README.txt", "content\n")
        result, out, _err = bundle.run({"tool_input": {"file_path": str(edited)}})
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out, "")

    def test_edit_outside_any_knowledge_node_is_silent_success(self):
        bundle = Bundle()
        edited = bundle.root / "AI_SYSTEM.md"
        _write(bundle.root, "AI_SYSTEM.md", "content\n")
        result, out, _err = bundle.run({"tool_input": {"file_path": str(edited)}})
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out, "")

    def test_broken_node_edit_fails_the_gate(self):
        bundle = Bundle()
        edited = bundle.root / ".hydra-framework/repo/knowledge/spaces/demo/overview.md"
        _write(bundle.root, ".hydra-framework/repo/knowledge/spaces/demo/overview.md", "[bad](./missing.md)\n")
        result, _out, err = bundle.run({"tool_input": {"file_path": str(edited)}})
        self.assertEqual(result.exit_code, 2)
        self.assertIn("Hydra knowledge-node gate FAILED", err)
        self.assertIn("missing link", err)

    def test_unrelated_package_break_does_not_fail_a_clean_edit(self):
        bundle = Bundle()
        _write(
            bundle.root,
            ".hydra-framework/repo/knowledge/spaces/demo/broken.md",
            "[bad](./missing.md)\n",
        )
        edited = bundle.root / ".hydra-framework/repo/knowledge/spaces/demo/clean.md"
        _write(bundle.root, ".hydra-framework/repo/knowledge/spaces/demo/clean.md", "no links here\n")
        result, out, err = bundle.run({"tool_input": {"file_path": str(edited)}})
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(err, "")
        self.assertIn("1 pre-existing knowledge-node issue", out)

    def test_own_error_reports_with_unrelated_count_alongside(self):
        bundle = Bundle()
        _write(
            bundle.root,
            ".hydra-framework/repo/knowledge/spaces/demo/broken.md",
            "[bad](./missing.md)\n",
        )
        edited = bundle.root / ".hydra-framework/repo/knowledge/spaces/demo/overview.md"
        _write(bundle.root, ".hydra-framework/repo/knowledge/spaces/demo/overview.md", "[bad](./missing.md)\n")
        result, _out, err = bundle.run({"tool_input": {"file_path": str(edited)}})
        self.assertEqual(result.exit_code, 2)
        self.assertIn("Hydra knowledge-node gate FAILED", err)
        self.assertIn("1 pre-existing knowledge-node issue", err)


if __name__ == "__main__":
    unittest.main()
