"""Mirror tests for ``hydra_engine.orchestration.adapter``."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.orchestration import adapter  # noqa: E402


def _request() -> adapter.AdapterRequest:
    return adapter.AdapterRequest("req1", "spawn", "run1", "task.md", "worker1", "alice", {"work": "inspect"})


class RequestBoundaryTests(unittest.TestCase):
    def test_task_record_reference_can_be_repository_relative(self):
        request = adapter.AdapterRequest(
            "req1", "spawn", "run1", ".hydra-framework/tasks/personal/alice/task.md",
            "worker1", "alice", {"work": "inspect"},
        )
        self.assertIn(".hydra-framework/tasks/", request.task_id)

    def test_named_provider_is_queue_only_and_not_execution_evidence(self):
        receipt = adapter.request_only("claude").submit(_request())
        self.assertEqual(receipt.status, "queued")
        self.assertEqual(receipt.provider, "claude")
        self.assertIn("no provider runtime was invoked", receipt.detail)

    def test_failing_adapter_preserves_a_local_queued_receipt(self):
        class Broken:
            name = "codex"

            def submit(self, request):
                raise RuntimeError("provider unavailable")

        receipt = adapter.submit(Broken(), _request())
        self.assertEqual(receipt.status, "queued")
        self.assertEqual(receipt.provider, "codex")
        self.assertIn("remains local-only", receipt.detail)

    def test_invalid_request_payload_is_refused_before_adapter_use(self):
        with self.assertRaises(adapter.models.PayloadError):
            adapter.AdapterRequest("req1", "spawn", "run1", "task.md", "worker1", "alice", "raw text")


if __name__ == "__main__":
    unittest.main()
