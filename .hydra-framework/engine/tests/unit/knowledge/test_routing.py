from __future__ import annotations

import dataclasses
import tempfile
import unittest
from pathlib import Path

from hydra_engine.knowledge.bindings import Binding, verify_binding
from hydra_engine.knowledge.nodes import discover_knowledge_nodes
from hydra_engine.knowledge.routing import (
    NodeSelection,
    context_terms,
    route_expansion_ids,
    route_nodes,
    route_prompt_node_pointers,
    routes_for_node,
)
from v3_fixtures import paths_for, write_node, write_unit


class KnowledgeV3RoutingTests(unittest.TestCase):
    def test_terms_drop_stopwords_and_keep_plural_stem(self):
        self.assertNotIn("the", context_terms("the deployments"))
        self.assertIn("deployment", context_terms("the deployments"))

    def test_explicit_node_and_space_are_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp), ("product", "security"))
            write_node(paths, "product", routable=False)
            write_node(paths, "product/checkout", keywords=("checkout",))
            write_node(paths, "security", keywords=("security",))
            selected, warnings = route_nodes("", ["checkout"], "", paths)
            self.assertEqual([item.node.logical_id for item in selected], ["product/checkout"])
            self.assertEqual(warnings, [])
            selected, warnings = route_nodes("", [], "security", paths)
            self.assertEqual([item.node.logical_id for item in selected], ["security"])
            self.assertEqual(warnings, [])

    def test_implicit_routing_caps_and_reports_boundary_ambiguity(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp), ("a", "b", "c"))
            for name in ("a", "b", "c"):
                write_node(paths, name, keywords=("shared",))
            selected, warnings = route_nodes("shared", [], "", paths, max_routed_nodes=2)
            self.assertEqual(selected, [])
            self.assertIn("ambiguous", warnings[0])

    def test_named_route_is_inherited_and_qualified(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp), ("product",))
            write_node(
                paths,
                "product",
                routable=False,
                routes=(
                    "routes:\n"
                    "  deploy:\n"
                    "    use_when:\n"
                    "      - deploy product safely\n"
                    "    priority_units: []\n"
                    "    requires: []\n"
                    "    avoid_by_default: []\n"
                    "    verify: []\n"
                    "    expand_when: []\n"
                ),
            )
            write_node(paths, "product/checkout", keywords=("checkout",))
            nodes = discover_knowledge_nodes(paths)
            leaf = next(node for node in nodes if node.logical_id == "product/checkout")
            selection = NodeSelection(leaf, "explicit", float("inf"))
            warnings: list[str] = []
            routes = routes_for_node(selection, "", ["product/checkout:deploy"], {node.logical_id: node for node in nodes}, warnings)
            self.assertEqual([route.name for route in routes], ["deploy"])
            self.assertEqual(warnings, [])
            routes = routes_for_node(
                selection,
                "",
                ["hydra://knowledge-route/product/deploy"],
                {node.logical_id: node for node in nodes},
                warnings,
            )
            self.assertEqual([route.name for route in routes], ["deploy"])
            self.assertEqual(warnings, [])

    def test_route_expand_when_resolves_logical_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = paths_for(root)
            write_node(
                paths,
                "demo",
                routes=(
                    "routes:\n"
                    "  edit:\n"
                    "    use_when:\n"
                    "      - edit source file\n"
                    "    priority_units: []\n"
                    "    requires: []\n"
                    "    avoid_by_default: []\n"
                    "    verify: []\n"
                    "    expand_when:\n"
                    "      - when_paths:\n"
                    "          - '@app/src/**'\n"
                    "        read:\n"
                    "          - hydra://knowledge-unit/demo/editing\n"
                    "        why: source ownership\n"
                ),
            )
            write_unit(paths, "demo", "editing")
            source = root / "src/main.py"
            source.parent.mkdir()
            source.write_text("pass\n", encoding="utf-8")
            node = discover_knowledge_nodes(paths)[0]
            route = node.routes[0]
            binding = Binding(
                logical_name="@app/src", namespace="app", key="src", target="src", kind="directory",
                assertions={}, accepted_fingerprint="", source_path=paths.hydra / "repo/knowledge/bindings/app.yaml",
            )
            binding = dataclasses.replace(binding, accepted_fingerprint=verify_binding(binding, paths).fingerprint)
            selected, diagnostics = route_expansion_ids(route, ["src/main.py"], {"@app/src": binding}, paths)
            self.assertEqual(selected, {"hydra://knowledge-unit/demo/editing"})
            self.assertEqual(diagnostics[0]["why"], "source ownership")

    def test_prompt_pointer_contains_only_paths_and_route_unit_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = paths_for(Path(tmp))
            write_node(
                paths,
                "demo",
                keywords=("deploy",),
                routes=(
                    "routes:\n"
                    "  deploy:\n"
                    "    use_when:\n"
                    "      - deploy application\n"
                    "    priority_units:\n"
                    "      - hydra://knowledge-unit/demo/runbook\n"
                    "    requires: []\n"
                    "    avoid_by_default: []\n"
                    "    verify: []\n"
                    "    expand_when: []\n"
                ),
            )
            write_unit(paths, "demo", "runbook")
            pointers, warnings = route_prompt_node_pointers("deploy application", paths)
            self.assertEqual(warnings, [])
            self.assertEqual(pointers[0].node_id, "demo")
            self.assertEqual(pointers[0].route, "deploy")
            self.assertTrue(pointers[0].state.endswith("/state.md"))
            self.assertEqual(pointers[0].priority_units[0][0], "hydra://knowledge-unit/demo/runbook")


if __name__ == "__main__":
    unittest.main()
