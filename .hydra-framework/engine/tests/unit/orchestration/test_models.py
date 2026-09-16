"""Mirror tests for ``hydra_engine.orchestration.models``."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.orchestration import models  # noqa: E402


class IdentityTests(unittest.TestCase):
    def test_task_reference_is_path_like_but_stays_relative(self):
        self.assertEqual(models.task_reference(".hydra-framework/tasks/personal/a/task.md"), ".hydra-framework/tasks/personal/a/task.md")
        with self.assertRaises(models.OrchestrationError):
            models.task_reference("../outside.md")
        with self.assertRaises(models.OrchestrationError):
            models.task_reference("/outside.md")

    def test_identifiers_and_owners_are_explicit(self):
        self.assertEqual(models.identifier("run:one", "run_id"), "run:one")
        self.assertEqual(models.owner_name("alice-example-com"), "alice-example-com")
        with self.assertRaises(models.OwnershipError):
            models.owner_name("owner with spaces")


class PayloadTests(unittest.TestCase):
    def test_payload_requires_structured_json(self):
        self.assertEqual(models.bounded_payload({"answer": "ok"}), {"answer": "ok"})
        with self.assertRaises(models.PayloadError):
            models.bounded_payload("raw transcript")

    def test_evidence_is_bounded(self):
        self.assertEqual(models.bounded_evidence(["unit test passed"]), ["unit test passed"])
        with self.assertRaises(models.PayloadError):
            models.bounded_evidence(["x"] * (models.max_evidence_items + 1))


class TransitionTests(unittest.TestCase):
    def test_run_worker_review_and_validation_transitions_are_fail_closed(self):
        models.transition_run("active", "failed")
        models.transition_worker("queued", "running")
        models.transition_worker("queued", "waiting")
        models.transition_review("not_requested", "requested")
        models.transition_validation("not_run", "running")
        with self.assertRaises(models.TransitionError):
            models.transition_run("completed", "active")


if __name__ == "__main__":
    unittest.main()
