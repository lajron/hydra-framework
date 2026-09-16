"""Mirror tests for ``hydra_engine.orchestration.ledger``."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.orchestration import ledger, models  # noqa: E402


class LocalLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.store = ledger.LocalLedger(ledger.OrchestrationPaths(root, root / ".hydra-framework", root / ".hydra-framework.local"))

    def test_update_persists_a_valid_ledger_atomically(self):
        def add_run(data):
            data["runs"]["run1"] = models.run_record("run1", "task.md", "alice", "2026-01-01T00:00:00Z")
            return data["runs"]["run1"]["run_id"]

        self.assertEqual(self.store.update(add_run), "run1")
        self.assertEqual(self.store.read()["runs"]["run1"]["task_id"], "task.md")
        self.assertTrue(self.store.paths.ledger_path().is_file())

    def test_malformed_private_state_is_not_repaired_or_replaced(self):
        path = self.store.paths.ledger_path()
        path.parent.mkdir(parents=True)
        path.write_text("not-json\n", encoding="utf-8")
        with self.assertRaises(models.LedgerCorruptError):
            self.store.read()
        self.assertEqual(path.read_text(encoding="utf-8"), "not-json\n")

    def test_update_refuses_a_corrupt_result_from_a_mutator(self):
        with self.assertRaises(models.LedgerCorruptError):
            self.store.update(lambda data: data.update({"bad": True}))
        self.assertFalse(self.store.paths.ledger_path().exists())


if __name__ == "__main__":
    unittest.main()
