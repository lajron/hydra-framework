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
            routing = templates / "routing.yaml"
            routing.write_text("legacy routing\n", encoding="utf-8")
            (templates / "overview.md").write_text("[Routing](routing.yaml) for a package.\n", encoding="utf-8")
            writes: dict[str, str] = {}
            modes: dict[str, int] = {}
            originals: dict[str, str] = {}
            deletes: list[str] = []

            migration_templates.plan(legacy, knowledge, root, writes, modes, originals, deletes)

            space_path = ".hydra-framework/repo/knowledge/templates/space/space.yaml.template"
            self.assertIn(space_path, writes)
            self.assertEqual(modes[space_path], routing.stat().st_mode & 0o777)
            parsed_path = root / space_path
            parsed_path.parent.mkdir(parents=True)
            parsed_path.write_text(writes[space_path], encoding="utf-8")
            self.assertEqual(parse_yaml(parsed_path, root, required=True)["schema"], "hydra-framework.knowledge-node.v1")
            self.assertIn("[Routing](space.yaml.template)", writes[".hydra-framework/repo/knowledge/templates/space/overview.md"])
            self.assertIn(".hydra-framework/repo/knowledge/knowledge-packages/README.md", deletes)

    def test_rewrite_references_updates_sidecar_identity_and_template_path(self):
        old = (
            "package-template-routing: hydra://knowledge-template/package/routing "
            ".hydra-framework/repo/knowledge/knowledge-packages/templates/routing.yaml "
            "Knowledge Package Routing Template"
        )
        rewritten = migration_templates.rewrite_references(old)
        self.assertIn("space-template-routing", rewritten)
        self.assertIn("hydra://knowledge-template/space/routing", rewritten)
        self.assertIn("knowledge/templates/space/space.yaml.template", rewritten)
        self.assertIn("Knowledge Space Routing Template", rewritten)


if __name__ == "__main__":
    unittest.main()
