"""knowledge goldens: measure-context,
validate-package-docs, compile-context, route-prompt."""

from __future__ import annotations

import unittest

from .fixtures import DEMO_UNIT, SPACE_DOC_WITH_ROUTE, assert_golden, knowledge_space_fixture, run_golden


ROUTED_SPACE_FIXTURE = knowledge_space_fixture(
    space_doc=SPACE_DOC_WITH_ROUTE,
    extra={
        ".hydra-framework/repo/knowledge/spaces/demo/units/guide.md": DEMO_UNIT,
    },
)


class KnowledgeGoldenTests(unittest.TestCase):
    def test_measure_context_happy_path(self):
        outcome = run_golden(["measure-context"])
        assert_golden(self, "knowledge-measure-context", outcome)

    def test_measure_context_json(self):
        outcome = run_golden(["measure-context", "--json"])
        assert_golden(self, "knowledge-measure-context-json", outcome)

    def test_measure_context_fail_over_exceeded(self):
        outcome = run_golden(["measure-context", "--fail-over", "1"])
        assert_golden(self, "knowledge-measure-context-fail-over", outcome)

    def test_validate_package_docs_happy_path(self):
        """No knowledge nodes present: still a real happy path
        (`no knowledge nodes found`)."""
        outcome = run_golden(["validate-package-docs"])
        assert_golden(self, "knowledge-validate-package-docs", outcome)

    def test_validate_package_docs_valid_space(self):
        """A well-formed v3 space passes the node-document and link gates."""
        outcome = run_golden(["validate-package-docs"], extra_fixture=knowledge_space_fixture())
        assert_golden(self, "knowledge-validate-package-docs-valid-space", outcome)

    def test_validate_package_docs_broken_link(self):
        outcome = run_golden(
            ["validate-package-docs"],
            extra_fixture=knowledge_space_fixture(overview="[broken](missing.md)\n"),
        )
        assert_golden(self, "knowledge-validate-package-docs-broken-link", outcome)

    def test_validate_package_docs_broken_node_document(self):
        """A node document missing its required envelope fails the local gate,
        the way the v2 gate failed a `routing.yaml` missing `keywords`."""
        outcome = run_golden(
            ["validate-package-docs"],
            extra_fixture=knowledge_space_fixture(
                space_doc=(
                    "schema: hydra-framework.knowledge-node.v1\n"
                    "node: demo\n"
                    "hydra_id: hydra://knowledge-package/demo\n"
                    "kind: knowledge-package\n"
                    "title: Demo\n"
                ),
            ),
        )
        assert_golden(self, "knowledge-validate-package-docs-broken-routing", outcome)

    def test_validate_package_docs_render_flag_with_no_diagrams(self):
        """`--render` on a node with no `diagrams/*.dot` files: the render
        path returns immediately without touching the `dot` binary, so this
        stays deterministic on a machine without Graphviz installed."""
        outcome = run_golden(["validate-package-docs", "--render"], extra_fixture=knowledge_space_fixture())
        assert_golden(self, "knowledge-validate-package-docs-render-no-diagrams", outcome)

    def test_compile_context_no_knowledge_configured(self):
        """No `spaces.yaml`: the packet still renders and says discovery failed
        rather than silently reporting an empty selection."""
        outcome = run_golden(["compile-context", "--task", "fixture task"])
        assert_golden(self, "knowledge-compile-context", outcome)

    def test_compile_context_selects_a_routed_space(self):
        """The real v3 path: a routed space is selected and its route named."""
        outcome = run_golden(
            ["compile-context", "--task", "demo routing task"],
            extra_fixture=ROUTED_SPACE_FIXTURE,
        )
        assert_golden(self, "knowledge-compile-context-routed-space", outcome)

    def test_compile_context_refusal_missing_task(self):
        """Closed once `command_compile_context` moved into the engine."""
        outcome = run_golden(["compile-context"], stdin="")
        assert_golden(self, "knowledge-compile-context-refusal-missing-task", outcome)

    def test_route_prompt_no_knowledge_configured(self):
        outcome = run_golden(["route-prompt", "--prompt", "fixture prompt"])
        assert_golden(self, "knowledge-route-prompt", outcome)

    def test_route_prompt_emits_v3_node_pointer(self):
        """The real v3 path: a matching space becomes one compact pointer."""
        outcome = run_golden(
            ["route-prompt", "--prompt", "demo routing task"],
            extra_fixture=ROUTED_SPACE_FIXTURE,
        )
        assert_golden(self, "knowledge-route-prompt-routed-space", outcome)


if __name__ == "__main__":
    unittest.main()
