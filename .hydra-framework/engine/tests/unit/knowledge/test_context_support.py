from __future__ import annotations

import unittest

from hydra_engine.knowledge import context_support


class ContextSupportTests(unittest.TestCase):
    def test_exports_candidate_and_search_operations(self):
        self.assertTrue(callable(context_support.add_candidate))
        self.assertTrue(callable(context_support.search))


if __name__ == "__main__":
    unittest.main()
