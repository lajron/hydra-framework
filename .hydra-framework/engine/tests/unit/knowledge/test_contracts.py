import unittest

from hydra_engine.knowledge import contracts


class KnowledgeContractsTests(unittest.TestCase):
    def test_scope_depth_and_relation_vocabularies_are_closed(self):
        self.assertEqual(contracts.DEFAULT_DEPTH, 3)
        self.assertEqual(contracts.MAX_DEPTH, 4)
        self.assertEqual(contracts.LEGAL_SCOPES, ("base-seed", "common-seed", "repo-local"))
        self.assertIn("supersedes", contracts.RELATION_TYPES)


if __name__ == "__main__":
    unittest.main()
