"""Mirror test for `hydra_engine.commands.context`."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.commands import context  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402
from v3_fixtures import write_node  # noqa: E402


def _paths() -> tuple[ContextCompilerPaths, ObjectLocations]:
    root = Path(tempfile.mkdtemp(prefix="commands-context-"))
    hydra = root / ".hydra-framework"
    hydra.mkdir(parents=True)
    paths = ContextCompilerPaths(root=root, hydra=hydra)
    resolver_paths = ObjectLocations(
        root=root,
        hydra=hydra,
        local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal",
        object_registry=hydra / "cognition/graph/registry.yaml",
    )
    return paths, resolver_paths


def _args(**overrides: object) -> argparse.Namespace:
    defaults = {
        "provider": "",
        "model": "",
        "budget": 12000,
        "package": [],
        "node": [],
        "domain": "",
        "space": "",
        "object": [],
        "path": [],
        "route": [],
        "view": [],
        "family_cap": None,
        "include_family": [],
        "exclude_family": [],
        "json": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _seed_package(paths: ContextCompilerPaths, name: str, *, keyword: str = "alpha", route: str = "") -> None:
    text = ""
    if route:
        text += (
            "routes:\n"
            f"  {route}:\n"
            "    use_when:\n"
            f"      - {keyword} task\n"
            "    priority_units: []\n"
            "    requires: []\n"
            "    avoid_by_default: []\n"
            "    verify: []\n"
            "    expand_when: []\n"
        )
    write_node(paths, name, keywords=(keyword,), routes=text)


class CommandCompileContextTests(unittest.TestCase):
    def test_missing_task_refuses(self):
        paths, resolver_paths = _paths()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            result = context.command_compile_context(_args(), "", paths, resolver_paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("task text is required", err.getvalue())

    def test_text_output_prints_header(self):
        paths, resolver_paths = _paths()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = context.command_compile_context(_args(), "Fixture task", paths, resolver_paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Hydra context packet", out.getvalue())
        self.assertIn("Task: Fixture task", out.getvalue())

    def test_json_output_is_well_formed(self):
        paths, resolver_paths = _paths()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = context.command_compile_context(_args(json=True), "Fixture task", paths, resolver_paths)
        self.assertEqual(result.exit_code, 0)
        packet = json.loads(out.getvalue())
        self.assertEqual(packet["schema"], "hydra-framework.context-packet.v2")
        self.assertEqual(packet["task"], "Fixture task")
        self.assertIsInstance(packet["provenance_freshness"]["registry_freshness_errors"], list)

    def test_configured_default_budget_is_used_when_cli_budget_is_omitted(self):
        paths, resolver_paths = _paths()
        note = paths.root / "note.md"
        note.write_text("content that exceeds one token\n", encoding="utf-8")
        out = io.StringIO()
        args = _args(budget=None, path=["note.md"], json=True)
        with contextlib.redirect_stdout(out):
            result = context.command_compile_context(args, "Fixture task", paths, resolver_paths, default_budget=1)
        self.assertEqual(result.exit_code, 0)
        packet = json.loads(out.getvalue())
        self.assertEqual(packet["budget_tokens"], 1)
        self.assertEqual(packet["selected_context"], [])

    def test_explicit_cli_budget_wins_over_configured_default(self):
        paths, resolver_paths = _paths()
        note = paths.root / "note.md"
        note.write_text("content that exceeds one token\n", encoding="utf-8")
        out = io.StringIO()
        args = _args(budget=100, path=["note.md"], json=True)
        with contextlib.redirect_stdout(out):
            result = context.command_compile_context(args, "Fixture task", paths, resolver_paths, default_budget=1)
        self.assertEqual(result.exit_code, 0)
        packet = json.loads(out.getvalue())
        self.assertEqual(packet["budget_tokens"], 100)
        self.assertEqual([item["path"] for item in packet["selected_context"]], ["note.md"])

    def test_explicit_route_values_are_passed_to_context_compiler(self):
        paths, resolver_paths = _paths()
        args = _args(route=["demo:main_route"], json=True)
        packet = {
            "schema": "hydra-framework.context-packet.v1",
            "date": "2026-01-01",
            "generated_at": "2026-01-01T00:00:00+00:00",
            "task": "Fixture task",
            "provider": "unspecified",
            "model": "unspecified",
            "budget_tokens": 12000,
            "packages": [],
            "selected_context": [],
            "omitted_candidates": [],
            "required_units": [],
            "avoid_by_default": [],
            "verify": [],
            "token_estimate": {
                "always_loaded_surfaces": 0,
                "selected_context": 0,
                "total_if_loaded": 0,
                "required_units": 0,
                "required_overage": 0,
                "approximation": "1 token ~= 4 characters",
            },
            "provenance_freshness": {
                "resolver_objects": 0,
                "object_errors": [],
                "registry_freshness_errors": [],
            },
            "validation_reminders": [],
            "known_risk_reminders": [],
            "warnings": [],
            "surface_file_count": 0,
        }
        with mock.patch("hydra_engine.commands.context.measure_context_surfaces", return_value=([], {"approx_tokens": 0})):
            with mock.patch("hydra_engine.commands.context._compile_context_packet", return_value=packet) as compiler:
                with contextlib.redirect_stdout(io.StringIO()):
                    result = context.command_compile_context(args, "Fixture task", paths, resolver_paths)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(compiler.call_args.kwargs["route_values"], ["demo:main_route"])

    def test_unknown_explicit_route_returns_error(self):
        paths, resolver_paths = _paths()
        _seed_package(paths, "demo", keyword="alpha")
        err = io.StringIO()
        args = _args(package=["demo"], route=["demo:missing"])
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            result = context.command_compile_context(args, "alpha task", paths, resolver_paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Route not found in node demo: missing", err.getvalue())

    def test_explicit_route_for_unselected_package_returns_error(self):
        paths, resolver_paths = _paths()
        _seed_package(paths, "selected", keyword="alpha")
        _seed_package(paths, "other", keyword="other", route="main")
        err = io.StringIO()
        args = _args(package=["selected"], route=["other:main"])
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            result = context.command_compile_context(args, "alpha task", paths, resolver_paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Route node not selected: other:main", err.getvalue())

    def test_json_output_echoes_provider_model_and_resolves_explicit_object(self):
        # Moved from `test_hydra.py`'s `ContextCompilerTests`
        #.
        paths, resolver_paths = _paths()
        obj_path = paths.hydra / "knowledge-units/0001-test.md"
        obj_path.parent.mkdir(parents=True)
        obj_path.write_text(
            "---\nhydra_id: hydra://knowledge-unit/0001-test\nuid: 11111111-1111-4111-8111-111111111111\n"
            "schema_version: 3\nkind: knowledge-unit\ntitle: Test Object\nstatus: accepted\nscope: repo\n"
            "owners:\n  team: fixture\nrelations: []\nprovenance:\n  sources: []\n---\n# Test Object\n",
            encoding="utf-8",
        )
        out = io.StringIO()
        args = _args(provider="codex", model="gpt-5", object=["hydra://knowledge-unit/0001-test"], json=True)
        with contextlib.redirect_stdout(out):
            result = context.command_compile_context(args, "Fixture task", paths, resolver_paths)
        self.assertEqual(result.exit_code, 0)
        packet = json.loads(out.getvalue())
        self.assertEqual(packet["provider"], "codex")
        self.assertTrue(any(item.get("hydra_id") == "hydra://knowledge-unit/0001-test" for item in packet["selected_context"]))

    def test_print_context_packet_reports_omitted_stale_units(self):
        packet = {
            "schema": "hydra-framework.context-packet.v1",
            "date": "2026-01-01",
            "task": "Fixture task",
            "provider": "unspecified",
            "model": "unspecified",
            "budget_tokens": 1,
            "packages": [],
            "selected_context": [],
            "omitted_candidates": [{
                "path": ".hydra-framework/repo/knowledge/knowledge-packages/demo/units/stale.md",
                "kind": "knowledge-unit",
                "reason": "token budget",
                "approx_tokens": 200,
                "source": "hydra://knowledge-unit/demo/stale",
                "stale_sources": ["source.py"],
            }],
            "required_units": [],
            "avoid_by_default": [],
            "verify": [],
            "token_estimate": {
                "always_loaded_surfaces": 0,
                "selected_context": 0,
                "total_if_loaded": 0,
                "approximation": "1 token ~= 4 characters",
            },
            "provenance_freshness": {
                "resolver_objects": 0,
                "object_errors": [],
                "registry_freshness_errors": [],
            },
            "validation_reminders": [],
            "known_risk_reminders": [],
            "warnings": [],
        }
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            context.print_context_packet(packet)
        text = out.getvalue()
        self.assertIn("Stale unit sources:", text)
        self.assertIn("hydra://knowledge-unit/demo/stale", text)
        self.assertIn("source.py committed after checked_on", text)


if __name__ == "__main__":
    unittest.main()
