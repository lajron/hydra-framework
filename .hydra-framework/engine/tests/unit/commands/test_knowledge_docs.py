from __future__ import annotations

import argparse
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from hydra_engine.commands.knowledge_docs import validate_node_docs
from hydra_engine.objects.discovery import ObjectLocations
from v3_fixtures import paths_for, write_node


class KnowledgeDocsTests(unittest.TestCase):
    def test_valid_node_reports_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = paths_for(root)
            write_node(paths, "demo")
            locations = ObjectLocations(root, paths.hydra, root / ".hydra-framework.local", "tasks/personal", paths.hydra / "cognition/graph/registry.yaml")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = validate_node_docs(argparse.Namespace(path=None, node="demo", package=None, render=False), paths, locations)
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Knowledge v3 docs: ok", output.getvalue())


if __name__ == "__main__":
    unittest.main()
