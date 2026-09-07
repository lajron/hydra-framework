from __future__ import annotations

import unittest

from hydra_engine.knowledge.storage import InMemoryKnowledgeStore, StoredKnowledgeObject


class KnowledgeStoreTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
