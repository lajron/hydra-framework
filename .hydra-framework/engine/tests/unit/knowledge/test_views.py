from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hydra_engine.knowledge.packages import ContextCompilerPaths
from hydra_engine.knowledge.views import KnowledgeView, ViewConflictError, ViewRoute, compose_views, validate_views


def _view(view_id: str, *, include: tuple[str, ...] = (), order: tuple[str, ...] = (), resolutions: dict[str, str] | None = None) -> KnowledgeView:
    return KnowledgeView(
        path=Path(f"{view_id}.view.yaml"), view_id=view_id,
        hydra_id=f"hydra://knowledge-view/{view_id}", uid=f"uid-{view_id}", title=view_id, owner="team",
        reviewers=("reviewer",), include=include, dynamic_bound_paths=False,
        routes=(ViewRoute("route", f"hydra://knowledge-view-route/{view_id}/route", ("task",), order, 1000),),
        resolutions=resolutions or {}, raw_keys=frozenset(), reference_only=True,
    )


class ViewTests(unittest.TestCase):
    def test_composes_references_and_partial_order(self):
        first = _view("first", include=("hydra://knowledge-node/product/checkout",), order=("product", "qa"))
        second = _view("second", include=("hydra://knowledge-node/security/pci",), order=("qa", "security"))
        composed = compose_views({first.hydra_id, second.hydra_id}, {first.hydra_id: first, second.hydra_id: second})
        self.assertEqual(composed.order, ("product", "qa", "security"))
        self.assertEqual(set(composed.includes), {"hydra://knowledge-node/product/checkout", "hydra://knowledge-node/security/pci"})

    def test_order_cycle_and_conflicting_resolutions_fail(self):
        first = _view("first", order=("product", "qa"), resolutions={"base": "titan"})
        second = _view("second", order=("qa", "product"), resolutions={"base": "nimbus"})
        with self.assertRaisesRegex(ViewConflictError, "conflicting view resolutions|ordering cycle"):
            compose_views({first.hydra_id, second.hydra_id}, {first.hydra_id: first, second.hydra_id: second})

    def test_reference_only_unresolved_and_cycle_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hydra = root / ".hydra-framework"
            views = hydra / "repo/knowledge/views"
            views.mkdir(parents=True)
            (views / "incident.view.yaml").write_text(
                "schema: hydra-framework.knowledge-view.v1\n"
                "view: incident\n"
                "hydra_id: hydra://knowledge-view/incident\n"
                "uid: 00000000-0000-4000-8000-000000000001\n"
                "schema_version: 3\nkind: knowledge-view\ntitle: Incident\nstatus: active\nscope: repo-local\n"
                "owners:\n  team: ops\nreviewers:\n  - security\nrelations: []\nprovenance:\n  sources: []\n"
                "constraints:\n  reference_only: false\n"
                "include:\n  - hydra://knowledge-node/product/missing\n"
                "content: forbidden narrative\n",
                encoding="utf-8",
            )
            paths = ContextCompilerPaths(root=root, hydra=hydra)
            details = "\n".join(str(item) for item in validate_views(paths, set()))
            self.assertIn("reference_only: true", details)
            self.assertIn("forbidden field `content`", details)
            self.assertIn("does not resolve", details)


if __name__ == "__main__":
    unittest.main()
