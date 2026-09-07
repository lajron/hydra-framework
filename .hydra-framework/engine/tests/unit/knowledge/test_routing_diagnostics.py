from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hydra_engine.knowledge.routing_diagnostics import route_prompt_match_diagnostics
from v3_fixtures import paths_for, write_node


class RoutePromptMatchDiagnosticsTests(unittest.TestCase):
    def test_scores_and_orders_matching_nodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp), ("product", "security"))
            write_node(paths, "product", keywords=("engine", "refactor"))
            write_node(paths, "security", keywords=("unrelated",))
            entries = route_prompt_match_diagnostics("Please do an engine refactor", paths)
            self.assertEqual([item["node"] for item in entries], ["product"])
            self.assertGreater(entries[0]["score"], 2.0)

    def test_non_matching_node_is_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp))
            write_node(paths, "demo", keywords=("unrelated",))
            self.assertEqual(route_prompt_match_diagnostics("engine refactor", paths), [])


if __name__ == "__main__":
    unittest.main()
