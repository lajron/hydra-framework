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


    def _run(self, paths, root, node):
        locations = ObjectLocations(root, paths.hydra, root / ".hydra-framework.local", "tasks/personal", paths.hydra / "cognition/graph/registry.yaml")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = validate_node_docs(argparse.Namespace(path=None, node=node, package=None, render=False), paths, locations)
        return result.exit_code, output.getvalue()

    def test_a_sibling_sharing_a_name_prefix_is_not_blamed_on_this_node(self):
        """`spaces/checkout` must not inherit findings from `spaces/checkout-api`."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = paths_for(root, ("checkout", "checkout-api"))
            write_node(paths, "checkout")
            write_node(paths, "checkout-api", scope="bogus-scope")
            code, out = self._run(paths, root, "checkout")
            self.assertEqual(code, 0, out)
            self.assertNotIn("checkout-api", out)
            code, out = self._run(paths, root, "checkout-api")
            self.assertEqual(code, 1)
            self.assertIn("bogus-scope", out)

    def test_a_spaces_config_failure_is_reported_rather_than_filtered_away(self):
        """Tree-level findings name `spaces.yaml`, which no node prefix matches."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = paths_for(root)
            write_node(paths, "demo")
            (paths.hydra / "repo/knowledge/spaces/stowaway").mkdir(parents=True)
            (paths.hydra / "repo/knowledge/spaces/stowaway/space.yaml").write_text("schema: x\n", encoding="utf-8")
            code, out = self._run(paths, root, "demo")
            self.assertEqual(code, 1, out)
            self.assertIn("unlisted knowledge space `stowaway`", out)


if __name__ == "__main__":
    unittest.main()
