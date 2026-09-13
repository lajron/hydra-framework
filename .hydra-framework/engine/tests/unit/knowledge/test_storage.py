from __future__ import annotations

import unittest
import sqlite3
import tempfile
from pathlib import Path
from unittest import mock

from hydra_engine.knowledge import search_index
from hydra_engine.knowledge.packages import ContextCompilerPaths
from hydra_engine.knowledge.storage import (
    HydrationMismatch,
    InMemoryKnowledgeStore,
    SqliteKnowledgeStore,
    StoredKnowledgeObject,
    build_knowledge_store,
    hydrate_node_and_ancestors,
    write_sqlite_store,
)
from hydra_engine.objects.discovery import ObjectLocations


class KnowledgeStoreTests(unittest.TestCase):
    def test_selected_node_hydration_requires_the_canonical_ancestor_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")
            knowledge = paths.hydra / "repo/knowledge"
            (knowledge / "spaces.yaml").parent.mkdir(parents=True)
            (knowledge / "spaces.yaml").write_text("schema: hydra-framework.knowledge-spaces.v1\nspaces: []\n", encoding="utf-8")
            parent_path = knowledge / "spaces/demo/space.yaml"
            child_path = knowledge / "spaces/demo/child/node.yaml"
            for path, logical_id, kind, uid in (
                (parent_path, "demo", "knowledge-space", "parent-uid"),
                (child_path, "demo/child", "knowledge-node", "child-uid"),
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    "schema: hydra-framework.knowledge-node.v1\n"
                    f"node: {logical_id}\nhydra_id: hydra://{kind}/{logical_id}\nuid: {uid}\n"
                    f"kind: {kind}\ntitle: {logical_id}\nstatus: active\nscope: repo-local\n"
                    "relations: []\nprovenance: {}\nroutable: true\nkeywords: []\n",
                    encoding="utf-8",
                )
            parent = StoredKnowledgeObject("hydra://knowledge-space/demo", "parent-uid", "knowledge-space", ".hydra-framework/repo/knowledge/spaces/demo/space.yaml", "demo")
            child = StoredKnowledgeObject("hydra://knowledge-node/demo/child", "child-uid", "knowledge-node", ".hydra-framework/repo/knowledge/spaces/demo/child/node.yaml", "demo/child")
            store = InMemoryKnowledgeStore((parent, child))
            self.assertEqual([node.logical_id for node in hydrate_node_and_ancestors(paths, store, child)], ["demo", "demo/child"])
            with self.assertRaises(HydrationMismatch):
                hydrate_node_and_ancestors(paths, InMemoryKnowledgeStore((child,)), child)

    def test_identity_and_typed_edge_queries_do_not_depend_on_registry_layout(self):
        target = StoredKnowledgeObject("hydra://knowledge-node/qa/shared", "uid-qa", "knowledge-node", "qa.yaml", "qa/shared")
        source = StoredKnowledgeObject(
            "hydra://knowledge-node/product/checkout", "uid-product", "knowledge-node", "product.yaml", "product/checkout",
            (("tests", target.hydra_id), ("relates-to", target.hydra_id)),
        )
        store = InMemoryKnowledgeStore([target, source])
        self.assertEqual(store.by_uid("uid-product"), source)
        self.assertEqual(store.outgoing(source.hydra_id, "tests"), (target,))
        self.assertEqual(store.incoming(target.hydra_id, "relates-to"), (source,))
        self.assertEqual([item.hydra_id for item in store.iter_objects()], [source.hydra_id, target.hydra_id])

    def test_sqlite_projection_preserves_identity_edges_and_node_path_lookup(self):
        node = StoredKnowledgeObject(
            "hydra://knowledge-node/product/checkout", "node-uid", "knowledge-node",
            ".hydra-framework/repo/knowledge/spaces/product/checkout/node.yaml", "product/checkout",
        )
        unit = StoredKnowledgeObject(
            "hydra://knowledge-unit/product/checkout/payments", "unit-uid", "knowledge-unit",
            ".hydra-framework/repo/knowledge/spaces/product/checkout/units/payments.md", "product/checkout",
            (("tests", node.hydra_id),),
        )
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "knowledge.db"
            with sqlite3.connect(db_path) as conn:
                write_sqlite_store(conn, InMemoryKnowledgeStore((node, unit)))
            store = SqliteKnowledgeStore.open(db_path)
        self.assertIsNotNone(store)
        assert store is not None
        self.assertEqual(store.by_uid("unit-uid"), unit)
        self.assertEqual(store.outgoing(unit.hydra_id, "tests"), (node,))
        self.assertEqual(store.node_for_path(".hydra-framework/repo/knowledge/spaces/product/checkout/units/payments.md"), node)

    def test_sqlite_store_matches_inmemory(self):
        root = Path(__file__).resolve().parents[5]
        paths = ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")
        memory = build_knowledge_store(paths)
        objects = tuple(memory.iter_objects())
        relation_types = {edge_type for item in objects for edge_type, _target in item.relations}
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "knowledge.db"
            with sqlite3.connect(db_path) as conn:
                write_sqlite_store(conn, memory)
            store = SqliteKnowledgeStore.open(db_path)
            self.assertIsNotNone(store)
            assert store is not None
            for item in objects:
                self.assertEqual(store.by_id(item.hydra_id), memory.by_id(item.hydra_id))
                self.assertEqual(store.by_uid(item.uid), memory.by_uid(item.uid))
                self.assertEqual(store.by_path(item.path), memory.by_path(item.path))
                self.assertEqual(store.node_for_path(item.path), memory.node_for_path(item.path))
                for relation_type in (*sorted(relation_types), ""):
                    self.assertEqual(store.outgoing(item.hydra_id, relation_type), memory.outgoing(item.hydra_id, relation_type))
                    self.assertEqual(store.incoming(item.hydra_id, relation_type), memory.incoming(item.hydra_id, relation_type))

    def test_read_path_does_not_call_iter_objects(self):
        root = Path(__file__).resolve().parents[5]
        paths = ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")
        resolver_paths = ObjectLocations(
            root, paths.hydra, root / ".hydra-framework.local", "tasks/personal",
            paths.hydra / "cognition/graph/registry.yaml",
        )
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / ".hydra-framework.local"
            search_index.build_index(paths, resolver_paths, local)
            with mock.patch.object(SqliteKnowledgeStore, "iter_objects", side_effect=AssertionError("eager read")):
                results, _features, source = search_index.search(
                    "hydra://knowledge-space/hydra-framework",
                    paths=paths, resolver_paths=resolver_paths, local=local,
                )
        self.assertEqual(source, "sqlite")
        self.assertTrue(results)


if __name__ == "__main__":
    unittest.main()
