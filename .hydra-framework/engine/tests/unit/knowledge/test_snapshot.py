from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hydra_engine.knowledge.snapshot import KnowledgeSnapshot
from v3_fixtures import paths_for, write_node


class KnowledgeSnapshotTests(unittest.TestCase):
    def test_canonical_snapshot_discovers_nodes_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp))
            write_node(paths, "demo")
            snapshot = KnowledgeSnapshot(paths)
            self.assertEqual(snapshot.canonical_nodes(), snapshot.canonical_nodes())


if __name__ == "__main__":
    unittest.main()
