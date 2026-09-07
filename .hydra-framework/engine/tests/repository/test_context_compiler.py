"""Real-repository context-compiler coverage.

Split out of `scripts/tests/test_hydra.py`'s `ContextCompilerTests`. These
methods are not hermetically fixture-able the way `knowledge/test_context_packets.py`'s
mirror tests are: they assert against this repository's own real
`hydra-framework` Knowledge v3 space -- its `space.yaml` routes and
`units/` -- the same way the other named frozen classes assert
against real repository state.

Renamed from `test_context_packs.py`: context packs are gone,
replaced end to end by Knowledge v3 node routes and units, so a
file named for the deleted mechanism would be actively misleading.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.commands.context import compile_context_packet  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402

_ROOT = Path(__file__).resolve().parents[4]
_HYDRA = _ROOT / ".hydra-framework"


def _paths() -> ContextCompilerPaths:
    return ContextCompilerPaths(root=_ROOT, hydra=_HYDRA)


def _resolver_paths() -> ObjectLocations:
    return ObjectLocations(
        root=_ROOT,
        hydra=_HYDRA,
        local=_ROOT / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal",
        object_registry=_HYDRA / "cognition/graph/registry.yaml",
    )


class RealRepositoryContextPacketTests(unittest.TestCase):
    def test_routed_packet_contains_stage_zero_baseline_fields(self) -> None:
        packet = compile_context_packet(
            task="Change the Hydra task lifecycle contract fields and validate active task records",
            paths=_paths(),
            resolver_paths=_resolver_paths(),
            provider="codex",
            model="gpt-5",
            budget=20000,
        )
        for field in [
            "date", "generated_at", "task", "provider", "model", "nodes",
            "views", "effective_policy", "route_expansions",
            "selected_context", "omitted_candidates", "token_estimate",
            "provenance_freshness", "validation_reminders", "known_risk_reminders",
        ]:
            self.assertIn(field, packet)
        self.assertTrue(any(item["node"] == "hydra-framework" for item in packet["nodes"]))
        selected_paths = {item["path"] for item in packet["selected_context"]}
        self.assertIn(".hydra-framework/repo/knowledge/spaces/hydra-framework/state.md", selected_paths)
        self.assertIn(".hydra-framework/repo/knowledge/spaces/hydra-framework/overview.md", selected_paths)

    def test_explicit_object_reference_uses_resolver_metadata(self) -> None:
        packet = compile_context_packet(
            task="Use the reflection-absorb skill",
            paths=_paths(),
            resolver_paths=_resolver_paths(),
            node_values=["hydra-framework"],
            object_refs=["hydra://capability/skill/reflection-absorb"],
            budget=20000,
        )
        skill = [
            item for item in packet["selected_context"]
            if item.get("hydra_id") == "hydra://capability/skill/reflection-absorb"
        ]
        self.assertEqual(len(skill), 1)
        self.assertIn("digest", skill[0])
        self.assertEqual(skill[0]["status"], "experimental")

    def test_budget_omits_candidates_without_exceeding_selection(self) -> None:
        packet = compile_context_packet(
            task="Hydra Knowledge v3 context compiler",
            paths=_paths(),
            resolver_paths=_resolver_paths(),
            node_values=["hydra-framework"],
            budget=1,
        )
        self.assertEqual(packet["selected_context"], [])
        self.assertTrue(packet["omitted_candidates"])
        self.assertEqual(packet["token_estimate"]["selected_context"], 0)

    def test_add_module_route_selects_its_priority_unit(self) -> None:
        """A task matching the `add_module` route's `use_when` selects that
        route and surfaces its `priority_units` -- the route-time narrowing
        that replaced context packs."""
        packet = compile_context_packet(
            task="adding or changing a Hydra skill subagent or slash command",
            paths=_paths(),
            resolver_paths=_resolver_paths(),
            node_values=["hydra-framework"],
            route_values=["hydra://knowledge-route/hydra-framework/add-module"],
            budget=20000,
        )
        hydra_framework = [p for p in packet["nodes"] if p["node"] == "hydra-framework"][0]
        self.assertEqual(hydra_framework["routes"], ["add_module"])
        unit_ids = {item.get("hydra_id") for item in packet["selected_context"] if item["kind"] == "knowledge-unit"}
        self.assertIn("hydra://knowledge-unit/hydra-framework/add-module", unit_ids)

    def test_change_task_contract_route_echoes_avoid_by_default_and_verify(self) -> None:
        packet = compile_context_packet(
            task="adding renaming or removing a required task record field",
            paths=_paths(),
            resolver_paths=_resolver_paths(),
            node_values=["hydra-framework"],
            route_values=["hydra://knowledge-route/hydra-framework/change-task-contract"],
            budget=20000,
        )
        hydra_framework = [p for p in packet["nodes"] if p["node"] == "hydra-framework"][0]
        self.assertEqual(hydra_framework["routes"], ["change_task_contract"])
        self.assertIn("archived and completed task records", packet["avoid_by_default"])
        self.assertIn("python3 .hydra-framework/scripts/hydra.py validate", packet["verify"])

    def test_capability_context_provider_surfaces_a_real_capability_by_id(self) -> None:
        """End-to-end coverage: the Capability context provider reuses the
        shared search index against this repository's real, tracked object
        registry (unlike the mirror tests in `test_context_providers.py`,
        which hand-build search results). `--include-family` narrowed to
        just `Capability` so no other family's candidates can satisfy the
        assertion. This exercises the same provider machinery against a
        family with real local objects."""
        packet = compile_context_packet(
            task="hydra://capability/skill/reflection-absorb",
            paths=_paths(),
            resolver_paths=_resolver_paths(),
            include_families=["Capability"],
            budget=20000,
        )
        matches = [
            item for item in packet["selected_context"]
            if item.get("hydra_id") == "hydra://capability/skill/reflection-absorb"
        ]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["kind"], "context-provider-capability")
        self.assertIn("rank", matches[0])
        self.assertEqual(packet["nodes"], [])

    def test_family_cap_bounds_one_providers_contribution(self) -> None:
        packet = compile_context_packet(
            task="skill",
            paths=_paths(),
            resolver_paths=_resolver_paths(),
            include_families=["Capability"],
            family_cap=1,
            budget=20000,
        )
        capability_candidates = [c for c in packet["selected_context"] if c["kind"] == "context-provider-capability"]
        self.assertLessEqual(len(capability_candidates), 1)

    def test_excluding_a_family_removes_its_candidates(self) -> None:
        packet = compile_context_packet(
            task="hydra://capability/skill/reflection-absorb",
            paths=_paths(),
            resolver_paths=_resolver_paths(),
            exclude_families=["Capability", "Knowledge"],
            budget=20000,
        )
        self.assertFalse(any(item["kind"] == "context-provider-capability" for item in packet["selected_context"]))

    def test_no_matching_route_uses_ranked_unit_selection(self) -> None:
        """A task with no explicit route selects no route, but the package
        still contributes units ranked by the shared search index."""
        packet = compile_context_packet(
            task="Hydra build status",
            paths=_paths(),
            resolver_paths=_resolver_paths(),
            node_values=["hydra-framework"],
            budget=20000,
        )
        hydra_framework = [p for p in packet["nodes"] if p["node"] == "hydra-framework"][0]
        self.assertEqual(hydra_framework["routes"], [])
        unit_ids = {item.get("hydra_id") for item in packet["selected_context"] if item["kind"] == "knowledge-unit"}
        self.assertIn("hydra://knowledge-unit/hydra-framework/build-status", unit_ids)


if __name__ == "__main__":
    unittest.main()
