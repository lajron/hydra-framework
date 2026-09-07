from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hydra_engine.knowledge.node_catalog import discover_knowledge_nodes
from hydra_engine.knowledge.unit_selection import collect_all_units, resolve_selected_graph
from v3_fixtures import paths_for, write_node, write_unit


class UnitSelectionTests(unittest.TestCase):
    def test_global_selection_crosses_node_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = paths_for(root, ("a", "b"))
            write_node(paths, "a")
            write_node(paths, "b")
            target = "hydra://knowledge-unit/b/required"
            write_unit(paths, "a", "seed", requires=(target,))
            write_unit(paths, "b", "required")
            units, _owners = collect_all_units(discover_knowledge_nodes(paths), root)
            required, _by, selected, _superseded = resolve_selected_graph(units, set(), {"hydra://knowledge-unit/a/seed"})
            self.assertEqual(required, {target})
            self.assertEqual(selected, {"hydra://knowledge-unit/a/seed", target})


if __name__ == "__main__":
    unittest.main()
