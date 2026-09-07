from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hydra_engine.knowledge.context_packets import compile_context_packet, today
from hydra_engine.objects.discovery import ObjectLocations
from v3_fixtures import paths_for, write_node, write_unit


def _resolver(root: Path) -> ObjectLocations:
    hydra = root / ".hydra-framework"
    return ObjectLocations(root, hydra, root / ".hydra-framework.local", "tasks/personal", hydra / "cognition/graph/registry.yaml")


def _compile(root: Path, paths, **changes):
    values = {
        "task": "demo knowledge",
        "paths": paths,
        "resolver_paths": _resolver(root),
        "surface_totals": {"approx_tokens": 5},
        "surface_file_count": 1,
        "include_families": ["Knowledge"],
        "node_values": ["demo"],
        "budget": 20000,
    }
    values.update(changes)
    return compile_context_packet(**values)


class TodayTests(unittest.TestCase):
    def test_today_is_iso_date(self):
        self.assertRegex(today(), r"^\d{4}-\d{2}-\d{2}$")


class CompileContextPacketTests(unittest.TestCase):
    def test_v2_packet_schema_exposes_v3_node_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = paths_for(root)
            write_node(paths, "demo")
            packet = _compile(root, paths)
            self.assertEqual(packet["schema"], "hydra-framework.context-packet.v2")
            self.assertEqual(packet["nodes"][0]["node"], "demo")
            for field in ("views", "effective_policy", "route_expansions", "selected_context", "required_units", "warnings"):
                self.assertIn(field, packet)
            self.assertNotIn("packages", packet)

    def test_explicit_path_is_selected_and_missing_path_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = paths_for(root)
            write_node(paths, "demo")
            note = root / "note.md"
            note.write_text("hello\n", encoding="utf-8")
            packet = _compile(root, paths, path_refs=["note.md", "missing.md"])
            self.assertTrue(any(item["path"] == "note.md" for item in packet["selected_context"]))
            self.assertIn("Path not found or not a file: missing.md", packet["warnings"])

    def test_required_cross_space_unit_overrides_budget_and_reports_overage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = paths_for(root, ("demo", "security"))
            required = "hydra://knowledge-unit/security/baseline"
            write_node(
                paths,
                "demo",
                routes=(
                    "routes:\n  use:\n    use_when:\n      - demo knowledge\n"
                    "    priority_units: []\n    requires:\n"
                    f"      - {required}\n"
                    "    avoid_by_default: []\n    verify: []\n    expand_when: []\n"
                ),
            )
            write_node(paths, "security")
            write_unit(paths, "security", "baseline", body="x" * 400)
            packet = _compile(root, paths, budget=1)
            self.assertEqual([item["hydra_id"] for item in packet["required_units"]], [required])
            self.assertGreater(packet["token_estimate"]["required_overage"], 0)
            self.assertTrue(any(item.get("source") == required for item in packet["selected_context"]))

    def test_optional_search_candidate_is_omitted_at_zero_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = paths_for(root)
            write_node(paths, "demo")
            note = root / "note.md"
            note.write_text("optional\n", encoding="utf-8")
            packet = _compile(root, paths, budget=0, path_refs=["note.md"])
            self.assertEqual(packet["selected_context"], [])
            self.assertEqual(packet["omitted_candidates"][0]["reason"], "zero token budget")


if __name__ == "__main__":
    unittest.main()
