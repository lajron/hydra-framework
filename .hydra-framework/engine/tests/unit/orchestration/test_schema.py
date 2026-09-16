"""Mirror tests for ``hydra_engine.orchestration.schema``."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.orchestration import models, schema  # noqa: E402


class LedgerSchemaTests(unittest.TestCase):
    def test_empty_ledger_is_valid(self):
        schema.validate_ledger(models.empty_ledger())

    def test_unknown_top_level_data_is_rejected(self):
        data = models.empty_ledger()
        data["unexpected"] = True
        with self.assertRaises(models.LedgerCorruptError):
            schema.validate_ledger(data)

    def test_parent_depth_mismatch_is_rejected(self):
        data = models.empty_ledger()
        data["runs"]["run1"] = models.run_record("run1", "task.md", "alice", "2026-01-01T00:00:00Z")
        data["requests"]["req1"] = models.request_record(
            "req1", "spawn", "run1", "task.md", "worker1", "alice", "unconfigured", "2026-01-01T00:00:00Z"
        )
        data["requests"]["req2"] = models.request_record(
            "req2", "spawn", "run1", "task.md", "worker2", "alice", "unconfigured", "2026-01-01T00:00:00Z"
        )
        data["workers"]["worker1"] = models.worker_record(
            "worker1", "req1", "run1", "task.md", "alice", "", 0, "review", "one", "review",
            "fast-default", "fast-default", "standard", "standard", "unconfigured", "2026-01-01T00:00:00Z"
        )
        data["workers"]["worker2"] = models.worker_record(
            "worker2", "req2", "run1", "task.md", "alice", "worker1", 3, "review", "two", "review",
            "fast-default", "fast-default", "standard", "standard", "unconfigured", "2026-01-01T00:00:00Z"
        )
        data["runs"]["run1"]["worker_ids"] = ["worker1", "worker2"]
        with self.assertRaises(models.LedgerCorruptError):
            schema.validate_ledger(data)

    def test_record_key_and_cross_record_identity_are_rejected(self):
        data = models.empty_ledger()
        data["runs"]["run1"] = models.run_record("run1", "task.md", "alice", "2026-01-01T00:00:00Z")
        data["requests"]["req1"] = models.request_record(
            "req1", "spawn", "run1", "task.md", "worker1", "alice", "unconfigured", "2026-01-01T00:00:00Z"
        )
        data["workers"]["worker-key"] = models.worker_record(
            "worker1", "req1", "run1", "task.md", "alice", "", 0, "review", "one", "review",
            "fast-default", "fast-default", "standard", "standard", "unconfigured", "2026-01-01T00:00:00Z"
        )
        with self.assertRaises(models.LedgerCorruptError):
            schema.validate_ledger(data)


if __name__ == "__main__":
    unittest.main()
