from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from hydra_engine.knowledge.checks import validate_knowledge_v3
from hydra_engine.knowledge.packages import ContextCompilerPaths
from hydra_engine.objects.discovery import ObjectLocations


class KnowledgeV3ChecksTests(unittest.TestCase):
    def test_unit_level_expansion_bad_scope_and_unresolved_global_requires_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hydra = root / ".hydra-framework"
            node_root = hydra / "repo/knowledge/spaces/product"
            units = node_root / "units"
            units.mkdir(parents=True)
            (hydra / "repo/knowledge/spaces.yaml").write_text(
                "schema: hydra-framework.knowledge-spaces.v1\ndefault_depth: 3\nmax_depth: 4\nspaces:\n  - product\n",
                encoding="utf-8",
            )
            (node_root / "space.yaml").write_text(
                "schema: hydra-framework.knowledge-node.v1\nnode: product\n"
                "hydra_id: hydra://knowledge-space/product\nuid: 00000000-0000-4000-8000-000000000001\n"
                "schema_version: 3\nkind: knowledge-space\ntitle: Product\nstatus: active\nscope: repo-local\n"
                "owners:\n  team: product\nrelations: []\nprovenance:\n  sources: []\nroutable: true\n",
                encoding="utf-8",
            )
            (units / "bad.md").write_text(
                "---\nhydra_id: hydra://knowledge-unit/product/bad\nuid: 00000000-0000-4000-8000-000000000002\n"
                "schema_version: 3\nkind: knowledge-unit\nunit_kind: answer\ntitle: Bad\nstatus: active\nscope: invalid\n"
                "owners:\n  team: product\nrelations:\n  - hydra://knowledge-unit/product/legacy\n"
                "provenance:\n  sources: []\nquestion: Bad?\n"
                "requires:\n  - hydra://knowledge-unit/security/missing\nexpand_when:\n  - when: legacy\n---\n# Bad\n",
                encoding="utf-8",
            )
            context_paths = ContextCompilerPaths(root=root, hydra=hydra)
            resolver = ObjectLocations(root, hydra, root / ".hydra-framework.local", "tasks/personal", hydra / "cognition/graph/registry.yaml")
            ctx = SimpleNamespace(
                context_compiler_paths=lambda: context_paths,
                resolver_paths=lambda: resolver,
                command_ids=(),
                threshold_value_or_default=lambda _key: 8000 if "FAIL" in _key else 4,
            )
            details = "\n".join(str(item) for item in validate_knowledge_v3(ctx))
            self.assertIn("unit-level expand_when is invalid", details)
            self.assertIn("scope `invalid`", details)
            self.assertIn("unresolved required unit", details)
            self.assertIn("typed mappings", details)


if __name__ == "__main__":
    unittest.main()
