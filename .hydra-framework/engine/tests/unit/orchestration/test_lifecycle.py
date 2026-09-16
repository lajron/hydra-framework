"""Mirror tests for ``hydra_engine.orchestration.lifecycle``."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine import config  # noqa: E402
from hydra_engine.orchestration import control, ledger, lifecycle  # noqa: E402


def _control(root: Path) -> control.OrchestrationControl:
    hydra = root / ".hydra-framework"
    local = root / ".hydra-framework.local"
    policy = config.load_effective_config(config.ConfigPaths(root, hydra, local)).delegation
    return control.OrchestrationControl(ledger.LocalLedger(ledger.OrchestrationPaths(root, hydra, local)), policy)


class LifecycleOperationTests(unittest.TestCase):
    def test_handoff_and_recovery_require_explicit_owners(self):
        self.assertTrue(issubclass(control.OrchestrationControl, lifecycle.OrchestrationLifecycle))
        with tempfile.TemporaryDirectory() as directory:
            runner = _control(Path(directory))
            runner.start_run("run1", "task.md", "alice")
            handed = runner.handoff("run", "run1", "alice", "bob")
            self.assertEqual((handed["status"], handed["owner"]), ("handed_off", "bob"))
            recovered = runner.recover("run", "run1", "carol", "bob")
            self.assertEqual((recovered["status"], recovered["owner"]), ("active", "carol"))
            with self.assertRaises(lifecycle.models.OwnershipError):
                runner.recover("run", "run1", "carol", "bob")

    def test_direct_handed_off_transition_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = _control(Path(directory))
            runner.start_run("run1", "task.md", "alice")
            with self.assertRaises(lifecycle.models.PolicyError):
                runner.transition("run", "run1", "alice", "handed_off")


if __name__ == "__main__":
    unittest.main()
