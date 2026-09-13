"""Mirror test for `hydra_engine.commands.knowledge`."""

from __future__ import annotations

import argparse
import contextlib
import io as stdlib_io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.commands import knowledge  # noqa: E402
from hydra_engine.documents.digests import normalized_digest  # noqa: E402
from hydra_engine.documents.frontmatter_blocks import markdown_frontmatter  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402
from hydra_engine.knowledge import search_index  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402
from hydra_engine.ports import lock as lock_port  # noqa: E402
from v3_fixtures import paths_for, write_node, write_unit  # noqa: E402


def _paths() -> ContextCompilerPaths:
    root = Path(tempfile.mkdtemp(prefix="commands-knowledge-"))
    return ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")


def _resolver_paths(paths: ContextCompilerPaths) -> ObjectLocations:
    return ObjectLocations(
        root=paths.root,
        hydra=paths.hydra,
        local=paths.root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal",
        object_registry=paths.hydra / "cognition/graph/registry.yaml",
    )


class CommandMeasureContextTests(unittest.TestCase):
    def test_reports_ok_under_budget(self):
        paths = _paths()
        (paths.root / "AI_SYSTEM.md").write_text("# Entry\n", encoding="utf-8")
        args = argparse.Namespace(include_generated_skills=False, path=[], json=False, fail_over=None)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = knowledge.command_measure_context(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Hydra context surface estimate", out.getvalue())

    def test_fail_over_budget_exceeded_returns_2(self):
        paths = _paths()
        (paths.root / "AI_SYSTEM.md").write_text("# Entry\n" * 100, encoding="utf-8")
        args = argparse.Namespace(include_generated_skills=False, path=[], json=False, fail_over=1)
        out = stdlib_io.StringIO()
        err = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = knowledge.command_measure_context(args, paths)
        self.assertEqual(result.exit_code, 2)
        self.assertIn("exceeds budget", err.getvalue())

    def test_json_mode_emits_machine_readable_output(self):
        paths = _paths()
        (paths.root / "AI_SYSTEM.md").write_text("# Entry\n", encoding="utf-8")
        args = argparse.Namespace(include_generated_skills=False, path=[], json=True, fail_over=None)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = knowledge.command_measure_context(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn('"files"', out.getvalue())


class CommandValidatePackageDocsTests(unittest.TestCase):
    def test_no_packages_found_reports_ok(self):
        paths = _paths()
        resolver_paths = _resolver_paths(paths)
        args = argparse.Namespace(package=None, path=None, render=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = knowledge.command_validate_package_docs(args, paths, resolver_paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("no knowledge nodes found", out.getvalue())

    def test_explicit_path_with_broken_link_fails(self):
        paths = _paths()
        resolver_paths = _resolver_paths(paths)
        package_root = paths.root / "package"
        package_root.mkdir()
        (package_root / "overview.md").write_text("[broken](missing.md)\n", encoding="utf-8")
        args = argparse.Namespace(package=None, path=str(package_root), render=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = knowledge.command_validate_package_docs(args, paths, resolver_paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Hydra Knowledge v3 docs: failed", out.getvalue())
        self.assertIn("missing.md", out.getvalue())

    def test_explicit_path_with_no_errors_reports_ok(self):
        paths = _paths()
        resolver_paths = _resolver_paths(paths)
        package_root = paths.root / "package"
        package_root.mkdir()
        args = argparse.Namespace(package=None, path=str(package_root), render=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = knowledge.command_validate_package_docs(args, paths, resolver_paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Hydra Knowledge v3 docs: ok", out.getvalue())


class KnowledgeStaleCommandTests(unittest.TestCase):
    def test_no_packages_reports_no_stale_units_and_exits_zero(self):
        paths = _paths()
        args = argparse.Namespace()
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = knowledge.command_knowledge_stale(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Checked units: 0", out.getvalue())
        self.assertIn("- none", out.getvalue())


class KnowledgeFingerprintCommandTests(unittest.TestCase):
    def _seed_unit(self, paths: ContextCompilerPaths) -> tuple[Path, Path]:
        source = paths.root / "source.py"
        source.write_text("x = 1\n", encoding="utf-8")
        paths_for(paths.root, ("example",))
        write_node(paths, "example")
        unit_path = write_unit(paths, "example", "demo", sources=("source.py",), checked_on="2026-08-29")
        return source, unit_path

    def test_writes_source_digests_for_one_unit(self):
        paths = _paths()
        source, unit_path = self._seed_unit(paths)
        args = argparse.Namespace(unit="hydra://knowledge-unit/example/demo")
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = knowledge.command_knowledge_fingerprint(args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("updated", out.getvalue())
        data = markdown_frontmatter(unit_path, paths.root)
        self.assertEqual(data["provenance"]["sources"], ["source.py"])
        self.assertEqual(
            data["provenance"]["source_digests"],
            [{"source": "source.py", "digest": normalized_digest(source)}],
        )

    def test_replaces_existing_source_digests_for_one_unit(self):
        paths = _paths()
        source, unit_path = self._seed_unit(paths)
        text = unit_path.read_text(encoding="utf-8")
        unit_path.write_text(
            text.replace(
                "  sources:\n    - source.py\n",
                "  sources:\n    - source.py\n  source_digests:\n    - source: source.py\n      digest: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
            ),
            encoding="utf-8",
        )
        args = argparse.Namespace(unit="hydra://knowledge-unit/example/demo")
        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            result = knowledge.command_knowledge_fingerprint(args, paths)
        self.assertEqual(result.exit_code, 0)
        data = markdown_frontmatter(unit_path, paths.root)
        self.assertEqual(
            data["provenance"]["source_digests"],
            [{"source": "source.py", "digest": normalized_digest(source)}],
        )

    def test_missing_unit_exits_nonzero(self):
        paths = _paths()
        args = argparse.Namespace(unit="hydra://knowledge-unit/example/missing")
        with contextlib.redirect_stderr(stdlib_io.StringIO()) as err:
            result = knowledge.command_knowledge_fingerprint(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("unit not found", err.getvalue())


def _seed_search_repo() -> tuple[ContextCompilerPaths, ObjectLocations, Path]:
    paths = _paths()
    paths_for(paths.root, ("example",))
    write_node(paths, "example", keywords=("adapter", "export"))
    (paths.hydra / "repo/knowledge/spaces/example/overview.md").write_text("# Example\nadapter export routing\n", encoding="utf-8")
    registry = paths.hydra / "cognition/graph/registry.yaml"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        "schema: hydra-framework.object-registry.v1\n"
        "generated_by: hydra.py ref index\n"
        "objects:\n"
        "  hydra://knowledge-space/example:\n"
        "    path: .hydra-framework/repo/knowledge/spaces/example/space.yaml\n"
        "    kind: knowledge-space\n"
        "    title: Example\n"
        "    aliases: []\n"
        "    relations: []\n",
        encoding="utf-8",
    )
    return paths, _resolver_paths(paths), paths.root / ".hydra-framework.local"


class KnowledgeSearchCommandTests(unittest.TestCase):
    def test_hook_reindex_knowledge_builds_private_sqlite_index(self):
        paths, resolver_paths, local = _seed_search_repo()
        args = argparse.Namespace(if_exists=False)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = knowledge.command_hook_reindex_knowledge(args, paths, resolver_paths, local, ("validate",))
        self.assertEqual(result.exit_code, 0)
        self.assertIsNotNone(search_index.default_db_path(local))
        self.assertIn("documents indexed", out.getvalue())

    def test_hook_reindex_knowledge_uses_incremental_update_when_stale(self):
        paths, resolver_paths, local = _seed_search_repo()
        for command in (
            ("git", "init"),
            ("git", "config", "user.email", "tests@example.invalid"),
            ("git", "config", "user.name", "Tests"),
            ("git", "add", "-A"),
            ("git", "commit", "-m", "seed"),
        ):
            subprocess.run(command, cwd=paths.root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        args = argparse.Namespace(if_exists=False)
        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            knowledge.command_hook_reindex_knowledge(args, paths, resolver_paths, local, ("validate",))

        overview = paths.hydra / "repo/knowledge/spaces/example/overview.md"
        overview.write_text(overview.read_text(encoding="utf-8") + "hook incremental phrase\n", encoding="utf-8")

        with mock.patch.object(search_index, "build_index", wraps=search_index.build_index) as rebuild:
            out = stdlib_io.StringIO()
            with contextlib.redirect_stdout(out):
                result = knowledge.command_hook_reindex_knowledge(args, paths, resolver_paths, local, ("validate",))
        rebuild.assert_not_called()
        self.assertEqual(result.exit_code, 0)
        results, _features, source = search_index.search(
            "hook incremental phrase", paths=paths, resolver_paths=resolver_paths, local=local, command_ids=("validate",),
        )
        self.assertEqual(source, "sqlite")
        self.assertIn("hook incremental phrase", results[0].document.body)

    def test_hook_reindex_knowledge_backs_off_while_quiescence_lock_is_held(self):
        """The bracket around a known multi-file governed write (see
        `migration_v2.apply_reviewed_plan`) is the same `knowledge-write.lock`
        this hook trigger tries non-blockingly; a contended lock is not an
        error, just nothing done this run."""
        paths, resolver_paths, local = _seed_search_repo()
        args = argparse.Namespace(if_exists=False)
        lock_path = paths.root / ".hydra-framework.local/locks/knowledge-write.lock"
        with lock_port.acquire(lock_path):
            out = stdlib_io.StringIO()
            with contextlib.redirect_stdout(out):
                result = knowledge.command_hook_reindex_knowledge(args, paths, resolver_paths, local, ("validate",))
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out.getvalue(), "")
        self.assertIsNone(search_index.default_db_path(local))

    def test_knowledge_search_prints_ranked_results(self):
        paths, resolver_paths, local = _seed_search_repo()
        args = argparse.Namespace(text="adapter export", budget=2000, limit=5, path=[])
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(stdlib_io.StringIO()):
            result = knowledge.command_knowledge_search(args, paths, resolver_paths, local, ("validate",))
        self.assertEqual(result.exit_code, 0)
        self.assertIn("adapter export routing", out.getvalue())

    def test_knowledge_search_uses_configured_limit_when_cli_limit_is_omitted(self):
        paths, resolver_paths, local = _seed_search_repo()
        args = argparse.Namespace(text="adapter export", budget=2000, limit=None, path=[])
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(stdlib_io.StringIO()):
            result = knowledge.command_knowledge_search(
                args, paths, resolver_paths, local, ("validate",), default_limit=1,
            )
        self.assertEqual(result.exit_code, 0)
        self.assertIn(" 1. [", out.getvalue())
        self.assertNotIn(" 2. [", out.getvalue())

    def test_delegation_brief_uses_same_search_path(self):
        paths, resolver_paths, local = _seed_search_repo()
        args = argparse.Namespace(text="adapter export", budget=1500, limit=5, path=[])
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out):
            result = knowledge.command_delegation_brief(args, paths, resolver_paths, local, ("validate",))
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Read first", out.getvalue())
        self.assertIn("Return: verified facts", out.getvalue())


if __name__ == "__main__":
    unittest.main()
