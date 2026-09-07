from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hydra_engine.knowledge.node_catalog import discover_knowledge_nodes, knowledge_node_for_path
from v3_fixtures import paths_for, write_node


class NodeCatalogTests(unittest.TestCase):
    def test_discovers_and_maps_to_the_deepest_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp), ("product",))
            write_node(paths, "product", routable=False)
            leaf = write_node(paths, "product/checkout")
            target = leaf.parent / "units/example.md"
            nodes = discover_knowledge_nodes(paths)
            self.assertEqual(knowledge_node_for_path(target, nodes, paths).logical_id, "product/checkout")


if __name__ == "__main__":
    unittest.main()
