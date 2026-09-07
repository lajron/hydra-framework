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
            script = templates / "scripts/check.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            script.chmod(0o775)
            writes: dict[str, str] = {}
            modes: dict[str, int] = {}
            move_sources: dict[str, str] = {}
            originals: dict[str, str] = {}
            deletes: list[str] = []

            migration_templates.plan(legacy, knowledge, root, writes, modes, move_sources, originals, deletes)

            space_path = ".hydra-framework/repo/knowledge/templates/space/space.yaml.template"
            self.assertIn(space_path, writes)
            self.assertEqual(modes[space_path], 0o644)
            self.assertEqual(move_sources[space_path], ".hydra-framework/repo/knowledge/knowledge-packages/templates/routing.yaml")
            parsed_path = root / space_path
            parsed_path.parent.mkdir(parents=True)
            parsed_path.write_text(writes[space_path], encoding="utf-8")
            self.assertEqual(parse_yaml(parsed_path, root, required=True)["schema"], "hydra-framework.knowledge-node.v1")
            self.assertIn("[Routing](space.yaml.template)", writes[".hydra-framework/repo/knowledge/templates/space/overview.md"])
            self.assertIn(".hydra-framework/repo/knowledge/knowledge-packages/README.md", deletes)
            # An executable source stays executable, but the recorded mode is the
            # tracked bit rather than the checkout's umask-dependent st_mode.
            self.assertEqual(modes[".hydra-framework/repo/knowledge/templates/space/scripts/check.sh"], 0o755)

    def test_rewrite_sidecar_updates_template_identity_key_title_and_path(self):
        old = (
            "package-template-routing: hydra://knowledge-template/package/routing "
            ".hydra-framework/repo/knowledge/knowledge-packages/templates/routing.yaml "
            "Knowledge Package Routing Template"
        )
        rewritten = migration_templates.rewrite_sidecar(old)
        self.assertIn("space-template-routing", rewritten)
        self.assertIn("hydra://knowledge-template/space/routing", rewritten)
        self.assertIn(".hydra-framework/repo/knowledge/templates/space/space.yaml.template", rewritten)
        self.assertIn("Knowledge Space Routing Template", rewritten)

    def test_rewrite_references_moves_template_paths_only(self):
        rewritten = migration_templates.rewrite_references(
            "see .hydra-framework/repo/knowledge/knowledge-packages/templates/overview.md\n"
            "and knowledge-packages/templates/routing.yaml\n"
        )
        self.assertIn(".hydra-framework/repo/knowledge/templates/space/overview.md", rewritten)
        self.assertIn("knowledge/templates/space/space.yaml.template", rewritten)

    def test_rewrite_references_redirects_superseded_contract_and_placeholder(self):
        rewritten = migration_templates.rewrite_references(
            "see .hydra-framework/repo/knowledge/knowledge-packages.md\n"
            "and repo/knowledge/knowledge-packages.md\n"
            "--path .hydra-framework/repo/knowledge/knowledge-packages/<package-slug>\n"
        )
        self.assertNotIn("knowledge-packages.md", rewritten)
        self.assertIn(".hydra-framework/core/knowledge-architecture.md", rewritten)
        self.assertIn("core/knowledge-architecture.md", rewritten)
        self.assertIn(".hydra-framework/repo/knowledge/spaces/<space-slug>", rewritten)

    def test_rewrite_references_leaves_unrelated_routing_and_prose_alone(self):
        """The blanket `/routing.yaml` and prose rules corrupted unrelated files."""
        original = (
            "path: .hydra-framework/repo/knowledge/knowledge-packages/hydra-framework/routing.yaml\n"
            "path: .hydra-framework/repo/routing.yaml\n"
            "# Knowledge Packages\n"
            "The Knowledge Package concept is explained in the wiki.\n"
        )
        self.assertEqual(migration_templates.rewrite_references(original), original)

    def test_rewrite_sidecar_retitles_only_template_objects(self):
        text = "title: Knowledge Package Overview Template\ntitle: Knowledge Packages\n"
        rewritten = migration_templates.rewrite_sidecar(text)
        self.assertIn("title: Knowledge Space Overview Template", rewritten)
        self.assertIn("title: Knowledge Packages", rewritten)


if __name__ == "__main__":
    unittest.main()
