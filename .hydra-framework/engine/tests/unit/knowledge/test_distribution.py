from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hydra_engine.installation.seed_copy import planned_init_files
from hydra_engine.knowledge.distribution import included_scopes, knowledge_path_scope, scope_is_distributed


class DistributionTests(unittest.TestCase):
    def test_closed_profiles_and_invalid_scope(self):
        self.assertEqual(included_scopes("base"), {"base-seed"})
        self.assertEqual(included_scopes("common"), {"base-seed", "common-seed"})
        self.assertTrue(scope_is_distributed("common-seed", "common"))
        self.assertFalse(scope_is_distributed("repo-local", "common"))
        with self.assertRaisesRegex(ValueError, "invalid distribution scope"):
            scope_is_distributed("repo", "base")

    def test_nearest_node_scope_owns_descendant_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            space = root / ".hydra-framework/repo/knowledge/spaces/platform"
            child = space / "identity"
            child.mkdir(parents=True)
            (space / "space.yaml").write_text("scope: common-seed\n", encoding="utf-8")
            (child / "node.yaml").write_text("scope: repo-local\n", encoding="utf-8")
            unit = child / "units/token.md"
            unit.parent.mkdir()
            unit.write_text("# Token\n", encoding="utf-8")
            rel = unit.relative_to(root)
            self.assertEqual(knowledge_path_scope(rel, root), "repo-local")

    def test_seed_copy_uses_same_profile_without_repo_local_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hydra = root / ".hydra-framework"
            target = root / "target"
            for space, scope in (("framework", "base-seed"), ("security", "common-seed"), ("product", "repo-local")):
                directory = hydra / f"repo/knowledge/spaces/{space}"
                directory.mkdir(parents=True)
                (directory / "space.yaml").write_text(f"scope: {scope}\n", encoding="utf-8")
                (directory / "overview.md").write_text(f"# {space}\n", encoding="utf-8")
            (root / "AI_SYSTEM.md").write_text("# AI\n", encoding="utf-8")
            (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
            base = {source.relative_to(root).as_posix() for source, _target in planned_init_files(root, target, "base")}
            common = {source.relative_to(root).as_posix() for source, _target in planned_init_files(root, target, "common")}
            self.assertTrue(any("spaces/framework/" in path for path in base))
            self.assertFalse(any("spaces/security/" in path for path in base))
            self.assertTrue(any("spaces/security/" in path for path in common))
            self.assertFalse(any("spaces/product/" in path for path in common))


if __name__ == "__main__":
    unittest.main()
