from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hydra_engine.knowledge.bindings import (
    BindingResolutionError,
    bound_nodes_for_paths,
    load_bindings,
    resolve_binding,
    validate_bindings,
    verify_binding,
)
from hydra_engine.knowledge.nodes import KnowledgeNode
from hydra_engine.knowledge.packages import ContextCompilerPaths


def _paths(root: Path) -> ContextCompilerPaths:
    hydra = root / ".hydra-framework"
    bindings = hydra / "repo/knowledge/bindings"
    bindings.mkdir(parents=True)
    (bindings / "manifest.yaml").write_text(
        "schema: hydra-framework.bindings-manifest.v1\nfragments:\n  - product.yaml\n",
        encoding="utf-8",
    )
    return ContextCompilerPaths(root=root, hydra=hydra)


def _fragment(paths: ContextCompilerPaths, fingerprint: str = "") -> None:
    (paths.hydra / "repo/knowledge/bindings/product.yaml").write_text(
        "schema: hydra-framework.bindings.v1\n"
        "namespace: product\n"
        "scope: repo-local\n"
        "bindings:\n"
        "  service/checkout-api:\n"
        "    target: src/Checkout.Api\n"
        "    kind: directory\n"
        "    assertions:\n"
        "      contains:\n"
        "        - Checkout.Api.csproj\n"
        "      identity:\n"
        "        - source: app.json\n"
        "          format: json\n"
        "          selector: /name\n"
        "          equals: Checkout.Api\n"
        f"    accepted_fingerprint: {fingerprint}\n",
        encoding="utf-8",
    )


def _node(binding: str, logical_id: str = "product/commerce/checkout") -> KnowledgeNode:
    return KnowledgeNode(
        path=Path("node.yaml"), logical_id=logical_id,
        hydra_id=f"hydra://knowledge-node/{logical_id}", uid="u", kind="knowledge-node",
        title="Checkout", status="active", scope="repo-local", owners={}, relations=(),
        provenance={}, role="service", routable=True, state="", overview="", binding=binding,
        keywords=(), defaults={}, routes=(), parent_id="product/commerce", depth=3,
    )


class BindingTests(unittest.TestCase):
    def test_assertions_require_explicit_fingerprint_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = _paths(root)
            target = root / "src/Checkout.Api"
            target.mkdir(parents=True)
            (target / "Checkout.Api.csproj").write_text("<Project />\n", encoding="utf-8")
            (target / "app.json").write_text('{"name":"Checkout.Api"}\n', encoding="utf-8")
            _fragment(paths)
            binding = load_bindings(paths)["@product/service/checkout-api"]
            status = verify_binding(binding, paths)
            self.assertEqual(status.state, "stale")
            _fragment(paths, status.fingerprint)
            binding = load_bindings(paths)["@product/service/checkout-api"]
            self.assertEqual(verify_binding(binding, paths).state, "verified")
            self.assertEqual(resolve_binding(binding.logical_name, {binding.logical_name: binding}, paths), target)

    def test_missing_marker_and_unresolved_name_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = _paths(root)
            (root / "src/Checkout.Api").mkdir(parents=True)
            _fragment(paths)
            details = "\n".join(str(item) for item in validate_bindings(paths))
            self.assertIn("contains assertion failed", details)
            with self.assertRaisesRegex(BindingResolutionError, "unresolved logical binding"):
                resolve_binding("@product/missing", load_bindings(paths), paths)

    def test_longest_verified_path_binding_selects_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = _paths(root)
            target = root / "src/Checkout.Api"
            target.mkdir(parents=True)
            (target / "Checkout.Api.csproj").write_text("<Project />\n", encoding="utf-8")
            (target / "app.json").write_text('{"name":"Checkout.Api"}\n', encoding="utf-8")
            _fragment(paths)
            first = load_bindings(paths)["@product/service/checkout-api"]
            _fragment(paths, verify_binding(first, paths).fingerprint)
            bindings = load_bindings(paths)
            result = bound_nodes_for_paths(
                ["src/Checkout.Api/Controllers/Payment.cs"], [_node("@product/service/checkout-api")], bindings, paths,
            )
            self.assertEqual(result, {"src/Checkout.Api/Controllers/Payment.cs": "product/commerce/checkout"})


if __name__ == "__main__":
    unittest.main()
