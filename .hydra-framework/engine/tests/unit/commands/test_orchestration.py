"""Mirror tests for ``hydra_engine.commands.orchestration``."""

from __future__ import annotations

import argparse
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

from hydra_engine.cli.dispatch import RepoContext  # noqa: E402
from hydra_engine.commands import orchestration  # noqa: E402


class CommandOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        task = self.root / ".hydra-framework/tasks/personal/alice/2026-01-01-task.md"
        task.parent.mkdir(parents=True)
        task.write_text("# Task: task\n\nOwner: alice\n", encoding="utf-8")
        self.ctx = RepoContext.for_root(self.root)

    def parse(self, *argv: str):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)
        orchestration.register(subparsers)
        return parser.parse_args(argv)

    def run_command(self, args):
        output = io.StringIO()
        errors = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            result = args.func(args, self.ctx)
        return result, output.getvalue(), errors.getvalue()

    def test_start_requires_and_records_a_task_reference(self):
        args = self.parse(
            "orchestration", "start", "--run-id", "run1", "--task",
            ".hydra-framework/tasks/personal/alice/2026-01-01-task.md", "--owner", "alice",
        )
        result, output, errors = self.run_command(args)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(errors, "")
        self.assertEqual(json.loads(output)["run_id"], "run1")

    def test_parser_registers_explicit_worker_and_status_commands(self):
        args = self.parse(
            "orchestration", "spawn", "--run-id", "run1", "--request-id", "req1",
            "--worker-id", "worker1", "--worker-owner", "alice", "--role", "review",
            "--task", "inspect", "--reason", "review", "--owner", "alice",
        )
        self.assertEqual(args.orchestration_command, "spawn")
        self.assertEqual(args.worker_id, "worker1")
        status = self.parse("orchestration", "status", "--run-id", "run1")
        self.assertEqual(status.orchestration_command, "status")


if __name__ == "__main__":
    unittest.main()
