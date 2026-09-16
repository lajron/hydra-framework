"""Mirror tests for ``hydra_engine.providers.orchestration``."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.providers import orchestration  # noqa: E402


class ProviderOrchestrationBoundaryTests(unittest.TestCase):
    def test_missing_map_fails_closed(self):
        self.assertEqual(
            orchestration.modes({}),
            {item: "unsupported" for item in orchestration.ORCHESTRATION_OPERATIONS},
        )

    def test_request_only_map_renders_a_non_execution_boundary(self):
        mapping = {"orchestration": {item: "request-only" for item in orchestration.ORCHESTRATION_OPERATIONS}}
        self.assertIn("Request-only operations: spawn, message, collect", orchestration.request_instruction(mapping))
        self.assertIn("does not invoke a provider SDK", orchestration.request_instruction(mapping))

    def test_invalid_map_state_is_a_finding(self):
        findings = orchestration.validate_mapping(
            {"orchestration": {"spawn": "provider-exec"}}, "provider-map.yaml"
        )
        self.assertEqual(len(findings), 3)
        self.assertTrue(all(item.code == "capability-maps" for item in findings))


if __name__ == "__main__":
    unittest.main()
