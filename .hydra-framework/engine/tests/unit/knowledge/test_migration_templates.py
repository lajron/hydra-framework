from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hydra_engine.documents.yaml_documents import parse_yaml
from hydra_engine.knowledge import migration_templates


class MigrationTemplateTests(unittest.TestCase):
    def test_plan_moves_templates_to_v3_authoring_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            knowledge = root / ".hydra-framework/repo/knowledge"
            legacy = knowledge / "knowledge-packages"
            templates = legacy / "templates"
            templates.mkdir(parents=True)
            (legacy / "README.md").write_text("legacy root\n", encoding="utf-8")
            (templates / "routing.yaml").write_text("legacy routing\n", encoding="utf-8")
            (templates / "overview.md").write_text("[Routing](routing.yaml) for a package.\n", encoding="utf-8")
            writes: dict[str, str] = {}
            originals: dict[str, str] = {}
            deletes: list[str] = []

            migration_templates.plan(legacy, knowledge, root, writes, originals, deletes)

            space_path = ".hydra-framework/repo/knowledge/templates/space/space.yaml"
            self.assertIn(space_path, writes)
            parsed_path = root / space_path
            parsed_path.parent.mkdir(parents=True)
            parsed_path.write_text(writes[space_path], encoding="utf-8")
            self.assertEqual(parse_yaml(parsed_path, root, required=True)["schema"], "hydra-framework.knowledge-node.v1")
            self.assertIn("[Routing](space.yaml)", writes[".hydra-framework/repo/knowledge/templates/space/overview.md"])
            self.assertIn(".hydra-framework/repo/knowledge/knowledge-packages/README.md", deletes)


if __name__ == "__main__":
    unittest.main()
