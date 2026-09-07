from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hydra_engine.knowledge.view_routing import normalized_token, select_and_compose_views
from v3_fixtures import paths_for


class ViewRoutingTests(unittest.TestCase):
    def test_empty_catalog_and_normalization_are_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp))
            selected, composed = select_and_compose_views("task", (), paths, set(), [])
            self.assertEqual(selected, set())
            self.assertIsNone(composed)
            self.assertEqual(normalized_token("Runtime/Engine"), "runtime-engine")


if __name__ == "__main__":
    unittest.main()
