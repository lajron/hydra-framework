"""Mirror tests for `hydra_engine.knowledge.index_collection`."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.knowledge import index_collection
from hydra_engine.knowledge.freshness import CorpusDelta
from hydra_engine.knowledge.packages import ContextCompilerPaths
from hydra_engine.objects import discovery
from hydra_engine.objects.discovery import ObjectLocations


class IndexCollectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.paths = ContextCompilerPaths(self.root, self.root / ".hydra-framework")
        self.resolver = ObjectLocations(self.root, self.paths.hydra, self.root / ".hydra-framework.local", "tasks/personal", self.paths.hydra / "cognition/graph/registry.yaml")

    def test_local_document_delta_never_uses_full_collection_helpers(self):
        path = self.root / ".hydra-framework/core/example.md"
        path.parent.mkdir(parents=True)
        path.write_text("# Example\nlocal delta\n", encoding="utf-8")
        change = CorpusDelta((".hydra-framework/core/example.md",), (), ())
        self.assertTrue(index_collection.delta_is_local(self.paths, self.resolver, change))
        with mock.patch.object(discovery, "collect_hydra_objects", side_effect=AssertionError("all objects")), mock.patch.object(index_collection, "_canonical_search_files", side_effect=AssertionError("corpus walk")):
            docs = index_collection.collect_search_documents(self.paths, self.resolver, only_paths=frozenset(change.added))
        self.assertEqual([(doc.path, doc.body) for doc in docs], [(change.added[0], "# Example\nlocal delta")])

    def test_structural_and_ambiguous_deltas_rebuild(self):
        sidecar = self.root / ".hydra-framework/core/objects.yaml"
        sidecar.parent.mkdir(parents=True)
        sidecar.write_text("schema: hydra-framework.object-sidecar.v1\nobjects: {}\n", encoding="utf-8")
        cases = (
            CorpusDelta((".hydra-framework/repo/knowledge/spaces.yaml",), (), ()),
            CorpusDelta((".hydra-framework/repo/knowledge/views/demo.view.yaml",), (), ()),
            CorpusDelta((".hydra-framework/core/objects.yaml",), (), ()),
            CorpusDelta((), (), (".hydra-framework/core/deleted.yaml",)),
        )
        self.assertTrue(all(not index_collection.delta_is_local(self.paths, self.resolver, change) for change in cases))


if __name__ == "__main__":
    unittest.main()
