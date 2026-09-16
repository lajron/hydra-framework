"""Mirror tests for ``hydra_engine.orchestration.control``."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine import config  # noqa: E402
from hydra_engine.orchestration import control, ledger, models  # noqa: E402


def _runner(root: Path, task_exists=None) -> control.OrchestrationControl:
    hydra = root / ".hydra-framework"
    local = root / ".hydra-framework.local"
    policy = config.load_effective_config(config.ConfigPaths(root, hydra, local)).delegation
    return control.OrchestrationControl(
        ledger.LocalLedger(ledger.OrchestrationPaths(root, hydra, local)), policy, task_exists
    )


def _spawn(runner, *, run_id="run1", request_id="req1", worker_id="worker1", owner="alice", parent="", actor="alice"):
    return runner.spawn(
        run_id, request_id, worker_id, owner, actor, parent,
        "review", "inspect one bounded area", "review", "tool-heavy", "standard",
        "claude", {"scope": "one file"},
    )


class RunAndWorkerTests(unittest.TestCase):
    def test_run_requires_an_existing_task_reference_when_checker_is_configured(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = _runner(Path(directory), lambda reference: reference == "task.md")
            runner.start_run("run1", "task.md", "alice")
            with self.assertRaises(models.PolicyError):
                runner.start_run("run2", "missing.md", "alice")

    def test_spawn_enforces_owner_parent_depth_and_active_worker_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = _runner(Path(directory))
            runner.start_run("run1", "task.md", "alice")
            first = _spawn(runner)
            self.assertEqual((first["depth"], first["owner"], first["capability_class"]), (0, "alice", "tool-heavy"))
            child = _spawn(runner, request_id="req2", worker_id="worker2", owner="carol", parent="worker1")
            self.assertEqual((child["depth"], child["parent_worker_id"]), (1, "worker1"))
            with self.assertRaises(models.PolicyError):
                _spawn(runner, request_id="req3", worker_id="worker3", owner="carol", parent="worker1")
            with self.assertRaises(models.PolicyError):
                runner.spawn("run1", "req4", "worker4", "alice", "carol", "worker2", "review", "too deep", "review", "fast-default", "standard", "claude", {})
            with self.assertRaises(models.OwnershipError):
                runner.spawn("run1", "req5", "worker5", "alice", "mallory", "", "review", "wrong owner", "review", "fast-default", "standard", "claude", {})

    def test_terminal_parent_cannot_spawn_a_child(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = _runner(Path(directory))
            runner.start_run("run1", "task.md", "alice")
            _spawn(runner)
            runner.collect("run1", "worker1", "collect-req", "result1", "alice", "unconfigured", {"ok": True}, True)
            runner.transition("worker", "worker1", "alice", "completed")
            with self.assertRaises(models.PolicyError):
                _spawn(runner, request_id="req2", worker_id="worker2", owner="bob", parent="worker1")

    def test_message_collect_review_validation_and_worker_completion_are_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = _runner(Path(directory))
            runner.start_run("run1", "task.md", "alice")
            worker = _spawn(runner, owner="bob")
            message = runner.message("run1", "worker1", "msg-req", "message1", "bob", "codex", {"instruction": "check"})
            self.assertEqual(message["status"], "queued")
            result = runner.collect("run1", "worker1", "collect-req", "result1", "bob", "codex", {"finding": "clear"}, True)
            self.assertTrue(result["complete"])
            runner.review("worker", "worker1", "bob", "requested", "ready")
            with self.assertRaises(models.OwnershipError):
                runner.review("worker", "worker1", "bob", "approved", "self approval")
            runner.review("worker", "worker1", "reviewer", "approved", "independent")
            runner.validate("worker", "worker1", "bob", "running", [])
            runner.validate("worker", "worker1", "reviewer", "passed", ["focused test passed"])
            completed = runner.transition("worker", "worker1", "bob", "completed")
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(runner.snapshot("run1")["workers"][0]["worker_id"], worker["worker_id"])

    def test_run_completion_requires_review_validation_and_terminal_workers(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = _runner(Path(directory))
            runner.start_run("run1", "task.md", "alice")
            _spawn(runner)
            with self.assertRaises(models.PolicyError):
                runner.transition("run", "run1", "alice", "completed")
            runner.collect("run1", "worker1", "collect-req", "result1", "alice", "unconfigured", {"ok": True}, True)
            runner.transition("worker", "worker1", "alice", "completed")
            runner.review("run", "run1", "alice", "requested", "ready")
            runner.review("run", "run1", "reviewer", "approved", "independent")
            runner.validate("run", "run1", "alice", "running", [])
            runner.validate("run", "run1", "reviewer", "passed", ["repository test passed"])
            self.assertEqual(runner.transition("run", "run1", "alice", "completed")["status"], "completed")

    def test_recovery_is_explicit_and_does_not_reap_stale_workers(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = _runner(Path(directory))
            runner.start_run("run1", "task.md", "alice")
            _spawn(runner)
            handed = runner.handoff("worker", "worker1", "alice", "bob")
            self.assertEqual(handed["status"], "handed_off")
            with self.assertRaises(models.OwnershipError):
                runner.recover("worker", "worker1", "bob", "bob")
            recovered = runner.recover("worker", "worker1", "carol", "bob")
            self.assertEqual((recovered["status"], recovered["owner"]), ("queued", "carol"))
            self.assertEqual(len(runner.snapshot("run1")["workers"]), 1)


if __name__ == "__main__":
    unittest.main()
