"""Mirror test for `hydra_engine.commands.subagents`."""

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

from hydra_engine.commands import subagents  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402
from v3_fixtures import write_node  # noqa: E402


def _context_paths() -> ContextCompilerPaths:
    root = Path(tempfile.mkdtemp(prefix="commands-subagent-context-"))
    return ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")


class CommandHookSubagentStartTests(unittest.TestCase):
    def run_hook(self, payload: object, paths: ContextCompilerPaths | None = None):
        args = argparse.Namespace()
        stdin = "" if payload is None else json.dumps(payload)
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch("sys.stdin", stdlib_io.StringIO(stdin)):
            result = subagents.command_hook_subagent_start(args, paths or _context_paths())
        return result, out.getvalue()

    def test_empty_stdin_is_silent_success(self):
        result, out = self.run_hook(None)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out, "")

    def test_unmatched_event_is_silent_success(self):
        result, out = self.run_hook({"hook_event_name": "PostToolUse", "agent_type": "Explore"})
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out, "")

    def test_hydra_agent_is_not_injected(self):
        result, out = self.run_hook({"hook_event_name": "SubagentStart", "agent_type": "hydra-orchestrator"})
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(out, "")

    def test_matched_agent_receives_additional_context_without_state_writes(self):
        paths = _context_paths()
        write_node(paths, "hydra-framework")

        result, out = self.run_hook({"hook_event_name": "SubagentStart", "agent_type": "Explore"}, paths)

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "SubagentStart")
        text = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("knowledge-search", text)
        self.assertIn("hydra-framework", text)
        self.assertFalse((paths.root / ".hydra-framework.local").exists())

    def test_configured_context_budget_limits_injected_context(self):
        paths = _context_paths()
        write_node(paths, "hydra-framework")
        args = argparse.Namespace()
        payload = {"hook_event_name": "SubagentStart", "agent_type": "Explore"}
        out = stdlib_io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch("sys.stdin", stdlib_io.StringIO(json.dumps(payload))):
            result = subagents.command_hook_subagent_start(args, paths, token_budget=5, chars_per_token=4)
        self.assertEqual(result.exit_code, 0)
        text = json.loads(out.getvalue())["hookSpecificOutput"]["additionalContext"]
        self.assertLessEqual(len(text), 20)


class ClaudeSubagentStartWiringTests(unittest.TestCase):
    def test_checked_in_claude_settings_wire_generic_subagents_to_the_hook(self):
        settings = Path(__file__).resolve().parents[5] / ".claude/settings.json"
        data = json.loads(settings.read_text(encoding="utf-8"))
        commands: list[str] = []
        for entry in data.get("hooks", {}).get("SubagentStart", []):
            matched = {part.strip() for part in str(entry.get("matcher", "")).split("|") if part.strip()}
            if matched.issuperset({"general-purpose", "Explore", "Plan"}):
                commands.extend(hook.get("command", "") for hook in entry.get("hooks", []))
        self.assertTrue(any("hook-subagent-start" in command for command in commands))


if __name__ == "__main__":
    unittest.main()
