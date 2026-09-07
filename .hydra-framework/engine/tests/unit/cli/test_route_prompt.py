"""Mirror test for `hydra_engine.cli.route_prompt`."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
_UNIT = Path(__file__).resolve().parents[1]
if str(_UNIT) not in sys.path:
    sys.path.insert(0, str(_UNIT))

from hydra_engine import thresholds  # noqa: E402
from hydra_engine.cli import route_prompt  # noqa: E402
from hydra_engine.cli.dispatch import RepoContext  # noqa: E402
from v3_fixtures import paths_for, write_node, write_unit  # noqa: E402


def _ctx() -> RepoContext:
    root = Path(tempfile.mkdtemp(prefix="route-prompt-test-"))
    (root / ".hydra-framework").mkdir(parents=True)
    return RepoContext.for_root(root)


def _seed_package(ctx: RepoContext) -> None:
    paths = paths_for(ctx.root, ("example",))
    write_node(paths, "example", keywords=("engine", "refactor"))


def _write_config(ctx: RepoContext, **overrides: int) -> None:
    config_dir = ctx.hydra / "config"
    config_dir.mkdir(parents=True)
    lines = ["schema: hydra-framework.engine-policy.v1", "thresholds:"]
    for entry in thresholds.THRESHOLDS:
        if entry.classification == thresholds.TEAM_TUNABLE_POLICY:
            lines.append(f"  {entry.key}: {overrides.get(entry.key, entry.value)}")
    (config_dir / "engine-policy.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (config_dir / "delegation-policy.yaml").write_text(
        "schema: hydra-framework.delegation-policy.v1\n"
        "enabled: true\nmax_active_workers: 2\nmax_depth: 1\n"
        "allowed_reasons:\n  - inspection\n"
        "role_defaults:\n  allowed_capability_classes:\n    - fast-default\n"
        "  fallback_capability_class: fast-default\n  effort_ceiling: max\n"
        "roles: {}\n",
        encoding="utf-8",
    )


def _seed_wrong_schema_package(ctx: RepoContext) -> None:
    path = ctx.hydra / "repo/knowledge/spaces/example/space.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("hydra-framework.knowledge-node.v1", "wrong.schema.v1"), encoding="utf-8")


def _seed_package_with_route(ctx: RepoContext) -> None:
    paths = paths_for(ctx.root, ("example",))
    write_node(
        paths,
        "example",
        keywords=("engine", "refactor"),
        routes=(
            "routes:\n  adopt_into_repo:\n    use_when:\n      - engine refactor adoption\n"
            "    priority_units:\n      - hydra://knowledge-unit/example/adopt\n"
            "    requires: []\n    avoid_by_default:\n      - generated/**\n"
            "    verify: []\n    expand_when: []\n"
        ),
    )
    write_unit(paths, "example", "adopt")


class CommandRoutePromptTests(unittest.TestCase):
    def test_matching_prompt_prints_pointers(self):
        ctx = _ctx()
        _seed_package(ctx)
        out = io.StringIO()
        args = type("Args", (), {"prompt": "Please do an engine refactor"})()
        with contextlib.redirect_stdout(out):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        self.assertIn("Hydra Knowledge v3 routing (pointers only):", out.getvalue())
        self.assertIn("Example", out.getvalue())

    def test_configured_package_cap_limits_implicit_matches(self):
        ctx = _ctx()
        _write_config(ctx, **{"hydra_engine.knowledge.routing.MAX_ROUTED_NODES": 1})
        paths = paths_for(ctx.root, ("example", "other"))
        write_node(paths, "example", keywords=("engine", "refactor"))
        write_node(paths, "other", keywords=("engine", "filler"))
        out, err = io.StringIO(), io.StringIO()
        args = type("Args", (), {"prompt": "Please do an engine refactor"})()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        self.assertIn("Example", out.getvalue())
        self.assertNotIn("Other", out.getvalue())

    def test_invalid_node_schema_fails_closed_with_warning(self):
        ctx = _ctx()
        _seed_package(ctx)
        _seed_wrong_schema_package(ctx)
        out, err = io.StringIO(), io.StringIO()
        args = type("Args", (), {"prompt": "Please do an engine refactor"})()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        self.assertNotIn("Example", out.getvalue())
        self.assertIn("Knowledge v3 routing unavailable", err.getvalue())

    def test_stdin_json_input_is_read_when_prompt_argument_is_empty(self):
        ctx = _ctx()
        _seed_package(ctx)
        args = type("Args", (), {"prompt": ""})()
        saved_stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps({"prompt": "engine refactor from hook"}))
        self.addCleanup(lambda: setattr(sys, "stdin", saved_stdin))
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        self.assertIn("Hydra Knowledge v3 routing (pointers only):", out.getvalue())
        self.assertIn("Example", out.getvalue())

    def test_route_prompt_output_does_not_render_route_directives(self):
        ctx = _ctx()
        _seed_package_with_route(ctx)
        out = io.StringIO()
        args = type("Args", (), {"prompt": "Please do an engine refactor adoption"})()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        output = out.getvalue()
        self.assertIn("Hydra Knowledge v3 routing (pointers only):", output)
        self.assertIn("Example", output)
        self.assertNotIn("Route:", output)
        self.assertNotIn("hydra://knowledge-unit/example/adopt", output)
        self.assertNotIn("Avoid by default:", output)
        self.assertNotIn("generated/**", output)

    def test_route_prompt_renders_exact_path_references_without_a_package_match(self):
        ctx = _ctx()
        note = ctx.hydra / "repo/knowledge/routing-note.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("# Routing Note\n", encoding="utf-8")
        out = io.StringIO()
        args = type("Args", (), {"prompt": "Read .hydra-framework/repo/knowledge/routing-note.md"})()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        output = out.getvalue()
        self.assertIn("Hydra exact references:", output)
        self.assertIn("`.hydra-framework/repo/knowledge/routing-note.md`", output)
        self.assertNotIn("Hydra Knowledge v3 routing (pointers only):", output)

    def test_second_turn_with_same_session_and_same_output_emits_nothing(self):
        ctx = _ctx()
        _seed_package(ctx)
        args = type("Args", (), {"prompt": ""})()
        payload = json.dumps({"prompt": "engine refactor from hook", "session_id": "session-123"})

        saved_stdin = sys.stdin
        sys.stdin = io.StringIO(payload)
        self.addCleanup(lambda: setattr(sys, "stdin", saved_stdin))
        first = io.StringIO()
        with contextlib.redirect_stdout(first), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)

        sys.stdin = io.StringIO(payload)
        second = io.StringIO()
        with contextlib.redirect_stdout(second), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)

        self.assertIn("Hydra Knowledge v3 routing (pointers only):", first.getvalue())
        self.assertEqual(second.getvalue(), "")

    def test_empty_prompt_prints_nothing(self):
        ctx = _ctx()
        args = type("Args", (), {"prompt": ""})()
        saved_stdin = sys.stdin
        sys.stdin = io.StringIO("")
        self.addCleanup(lambda: setattr(sys, "stdin", saved_stdin))
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "")

    def test_json_diagnostic_output_carries_score_reason_references_and_timing(self):
        ctx = _ctx()
        _seed_package(ctx)
        note = ctx.hydra / "repo/knowledge/routing-note.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("# Routing Note\n", encoding="utf-8")
        out = io.StringIO()
        args = type("Args", (), {
            "prompt": "Please do an engine refactor; read .hydra-framework/repo/knowledge/routing-note.md",
            "json": True,
        })()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        diagnostics = json.loads(out.getvalue())
        self.assertEqual(len(diagnostics["matches"]), 1)
        self.assertEqual(diagnostics["matches"][0]["node"], "example")
        self.assertEqual(diagnostics["matches"][0]["reason"], "global index")
        self.assertGreater(diagnostics["matches"][0]["score"], 0)
        self.assertEqual(len(diagnostics["exact_references"]), 1)
        self.assertIn(".hydra-framework/repo/knowledge/routing-note.md", diagnostics["exact_references"][0]["path"])
        self.assertFalse(diagnostics["suppressed"])
        self.assertGreaterEqual(diagnostics["timing_ms"], 0)

    def test_json_diagnostic_does_not_advance_session_suppression_state(self):
        ctx = _ctx()
        _seed_package(ctx)
        payload = json.dumps({"prompt": "engine refactor from hook", "session_id": "session-json"})

        saved_stdin = sys.stdin
        self.addCleanup(lambda: setattr(sys, "stdin", saved_stdin))

        sys.stdin = io.StringIO(payload)
        json_out = io.StringIO()
        with contextlib.redirect_stdout(json_out), contextlib.redirect_stderr(io.StringIO()):
            args = type("Args", (), {"prompt": "", "json": True})()
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        self.assertFalse(json.loads(json_out.getvalue())["suppressed"])

        sys.stdin = io.StringIO(payload)
        text_out = io.StringIO()
        with contextlib.redirect_stdout(text_out), contextlib.redirect_stderr(io.StringIO()):
            args = type("Args", (), {"prompt": ""})()
            self.assertEqual(route_prompt.command_route_prompt(args, ctx), 0)
        self.assertIn("Hydra Knowledge v3 routing (pointers only):", text_out.getvalue())


if __name__ == "__main__":
    unittest.main()
