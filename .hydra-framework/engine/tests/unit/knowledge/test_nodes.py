from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hydra_engine.knowledge.nodes import (
    knowledge_node_for_path,
    node_roots_by_path,
    MAX_DEPTH,
    discover_knowledge_nodes,
    resolve_inheritance,
    validate_knowledge_nodes,
)
from hydra_engine.knowledge.packages import ContextCompilerPaths


def _paths(root: Path) -> ContextCompilerPaths:
    hydra = root / ".hydra-framework"
    (hydra / "repo/knowledge/spaces/product/commerce/checkout").mkdir(parents=True)
    (hydra / "repo/knowledge/spaces.yaml").write_text(
        "schema: hydra-framework.knowledge-spaces.v1\ndefault_depth: 3\nmax_depth: 4\nspaces:\n  - product\n",
        encoding="utf-8",
    )
    return ContextCompilerPaths(root=root, hydra=hydra)


def _node(path: Path, logical: str, *, kind: str, routable: bool = True, owner: str | None = "product", extra: str = "") -> None:
    owner_block = f"owners:\n  team: {owner}\n" if owner else ""
    path.write_text(
        "schema: hydra-framework.knowledge-node.v1\n"
        f"node: {logical}\n"
        f"hydra_id: hydra://{kind}/{logical}\n"
        f"uid: 00000000-0000-4000-8000-{len(logical):012d}\n"
        "schema_version: 3\n"
        f"kind: {kind}\n"
        f"title: {logical}\n"
        "status: active\n"
        "scope: repo-local\n"
        f"{owner_block}"
        "relations: []\n"
        "provenance:\n  sources: []\n"
        f"routable: {'true' if routable else 'false'}\n"
        f"{extra}",
        encoding="utf-8",
    )


class KnowledgeNodeTests(unittest.TestCase):
    def test_recursive_discovery_and_inheritance_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = _paths(root)
            space = paths.hydra / "repo/knowledge/spaces/product/space.yaml"
            area = paths.hydra / "repo/knowledge/spaces/product/commerce/node.yaml"
            leaf = paths.hydra / "repo/knowledge/spaces/product/commerce/checkout/node.yaml"
            _node(space, "product", kind="knowledge-space", routable=False, extra="defaults:\n  validation_profile: standard\n  avoid_by_default:\n    - generated/**\n")
            _node(area, "product/commerce", kind="knowledge-node", routable=False, owner="payments", extra="defaults:\n  validation_profile: strict\n")
            _node(leaf, "product/commerce/checkout", kind="knowledge-node", owner=None, extra="overview: ./overview.md\n")
            leaf.with_name("overview.md").write_text("# Checkout\n", encoding="utf-8")

            nodes = discover_knowledge_nodes(paths)
            self.assertEqual([node.logical_id for node in nodes], ["product", "product/commerce", "product/commerce/checkout"])
            by_id = {node.logical_id: node for node in nodes}
            effective = resolve_inheritance(by_id["product/commerce/checkout"], by_id)
            self.assertEqual(effective["owners"]["team"], "payments")
            self.assertEqual(effective["defaults"]["validation_profile"], "strict")
            self.assertEqual(effective["defaults"]["avoid_by_default"], ["generated/**"])
            self.assertEqual(effective["trace"]["owners.team"], "hydra://knowledge-node/product/commerce")
            self.assertEqual(validate_knowledge_nodes(paths), [])

    def test_depth_scope_relation_and_empty_node_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = _paths(root)
            _node(paths.hydra / "repo/knowledge/spaces/product/space.yaml", "product", kind="knowledge-space", routable=False)
            area = paths.hydra / "repo/knowledge/spaces/product/commerce/node.yaml"
            _node(area, "product/commerce", kind="knowledge-node", routable=False)
            leaf = paths.hydra / "repo/knowledge/spaces/product/commerce/checkout/node.yaml"
            _node(
                leaf,
                "product/commerce/checkout",
                kind="knowledge-node",
                extra=(
                    "scope: invalid\n"
                    "relations:\n"
                    "  - type: guesses\n"
                    "    target: not-a-hydra-id\n"
                ),
            )
            deep_root = leaf.parent / "component/subcomponent"
            deep_root.mkdir(parents=True)
            _node(deep_root / "node.yaml", "product/commerce/checkout/component/subcomponent", kind="knowledge-node", extra="overview: ./overview.md\n")
            findings = validate_knowledge_nodes(paths)
            details = "\n".join(str(item) for item in findings)
            self.assertIn("scope `invalid`", details)
            self.assertIn("relation type `guesses`", details)
            self.assertIn("relation target is not a valid hydra id", details)
            self.assertIn(f"exceeds {MAX_DEPTH}", details)
            self.assertIn("empty structural node", details)
            # Findings render as `detail` alone, so every node finding must
            # name its own file or the reader cannot locate the problem.
            for finding in findings:
                self.assertTrue(
                    str(finding).startswith(finding.path + ":"),
                    f"node finding does not name its path: {finding}",
                )

    def test_route_override_and_expand_when_contracts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = _paths(root)
            _node(
                paths.hydra / "repo/knowledge/spaces/product/space.yaml",
                "product",
                kind="knowledge-space",
                routable=True,
                extra="routes:\n  deploy:\n    use_when:\n      - deploy product\n",
            )
            area = paths.hydra / "repo/knowledge/spaces/product/commerce/node.yaml"
            _node(
                area,
                "product/commerce",
                kind="knowledge-node",
                extra=(
                    "routes:\n"
                    "  deploy:\n"
                    "    use_when: []\n"
                    "    expand_when:\n"
                    "      - when_paths: []\n"
                    "        read: []\n"
                ),
            )
            leaf = paths.hydra / "repo/knowledge/spaces/product/commerce/checkout/node.yaml"
            _node(leaf, "product/commerce/checkout", kind="knowledge-node", extra="overview: ./overview.md\n")
            leaf.with_name("overview.md").write_text("# Checkout\n", encoding="utf-8")
            details = "\n".join(str(item) for item in validate_knowledge_nodes(paths))
            self.assertIn("must declare it explicitly", details)
            self.assertIn("requires non-empty use_when", details)
            self.assertIn("expand_when requires when_paths, read, and why", details)


class NodeForPathTests(unittest.TestCase):
    def test_deepest_node_wins_and_precomputed_roots_agree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = _paths(root)
            spaces = paths.hydra / "repo/knowledge/spaces/product"
            _node(spaces / "space.yaml", "product", kind="knowledge-space", routable=False)
            _node(spaces / "commerce/node.yaml", "product/commerce", kind="knowledge-node", routable=False)
            leaf = spaces / "commerce/checkout"
            _node(leaf / "node.yaml", "product/commerce/checkout", kind="knowledge-node", extra="overview: ./overview.md\n")
            (leaf / "overview.md").write_text("# Checkout\n", encoding="utf-8")
            nodes = discover_knowledge_nodes(paths)
            roots = node_roots_by_path(nodes)
            # A precomputed root map must not change which node a path resolves to.
            for probe in (leaf / "units", leaf, spaces / "commerce", spaces):
                uncached = knowledge_node_for_path(probe, nodes, paths)
                cached = knowledge_node_for_path(probe, nodes, paths, roots)
                self.assertIsNotNone(uncached, probe)
                self.assertEqual(uncached.logical_id, cached.logical_id)
            self.assertEqual(
                knowledge_node_for_path(leaf / "units/x.md", nodes, paths).logical_id,
                "product/commerce/checkout",
            )
            self.assertIsNone(knowledge_node_for_path(root / "elsewhere", nodes, paths, roots))


if __name__ == "__main__":
    unittest.main()
