"""Unit tests for hydra_engine.cli.rendering."""

from __future__ import annotations

import contextlib
import io
import unittest
from dataclasses import dataclass

from hydra_engine.cli import rendering
from hydra_engine.knowledge.search_index import SearchDocument, SearchResult


@dataclass(frozen=True)
class _Match:
    title: str
    state: str
    overview: str
    note: str
    route: str = ""
    priority_units: tuple = ()
    requires: tuple = ()
    avoid_by_default: tuple = ()


class RenderRoutePromptTests(unittest.TestCase):
    def test_prints_warnings_to_stderr(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            rendering.render_route_prompt([], ["broken.yaml unreadable"], [])
        self.assertIn("Hydra routing skipped: broken.yaml unreadable", stderr.getvalue())

    def test_prints_match_pointers(self) -> None:
        stdout = io.StringIO()
        matches = [
            _Match("hydra-framework", "state.md", "overview.md", "Read state first."),
            _Match("other-package", "other/state.md", "other/overview.md", "No packs yet."),
        ]
        with contextlib.redirect_stdout(stdout):
            rendering.render_route_prompt(matches, [], [])
        output = stdout.getvalue()
        self.assertIn("Hydra Knowledge v3 routing (pointers only):", output)
        self.assertIn("- hydra-framework: read `state.md` then `overview.md` first. Read state first.", output)
        self.assertIn("- other-package: read `other/state.md` then `other/overview.md` first. No packs yet.", output)

    def test_route_prompt_does_not_print_route_units_or_avoid_directives(self) -> None:
        stdout = io.StringIO()
        priority_units = tuple((f"hydra://knowledge-unit/demo/u{i}", f"Question {i}?") for i in range(7))
        matches = [
            _Match(
                "demo", "state.md", "overview.md", "Note.",
                route="main_route",
                priority_units=priority_units,
                requires=(("hydra://knowledge-unit/demo/required", "Required question?"),),
                avoid_by_default=("generated/**",),
            ),
        ]
        with contextlib.redirect_stdout(stdout):
            rendering.render_route_prompt(matches, [], [])
        output = stdout.getvalue()
        self.assertIn("- demo: read `state.md` then `overview.md` first. Note.", output)
        self.assertNotIn("Route: main_route", output)
        self.assertNotIn("hydra://knowledge-unit/demo/required", output)
        self.assertNotIn("+3 more, run compile-context", output)
        self.assertNotIn("Avoid by default:", output)
        self.assertNotIn("- generated/**", output)

    def test_prints_state_lines_last_and_skips_the_heading_with_no_matches(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rendering.render_route_prompt([], [], ["- board: 1 active task"])
        output = stdout.getvalue()
        self.assertIn("- board: 1 active task", output)
        self.assertNotIn("Hydra package routing", output)

    def test_prints_exact_references(self) -> None:
        stdout = io.StringIO()
        doc = SearchDocument(
            key="knowledge-unit",
            hydra_id="hydra://knowledge-unit/0013-routing",
            aliases=(),
            path=".hydra-framework/repo/knowledge-units/0013-routing.md",
            kind="knowledge-unit",
            package="",
            title="Routing Decision",
            keywords=(),
            routes=(),
            use_when=(),
            headings=(),
            body="",
            relations=(),
        )
        with contextlib.redirect_stdout(stdout):
            rendering.render_route_prompt([], [], [], (SearchResult(doc, "exact", 0),))
        output = stdout.getvalue()
        self.assertIn("Hydra exact references:", output)
        self.assertIn("hydra://knowledge-unit/0013-routing", output)
        self.assertIn("`.hydra-framework/repo/knowledge-units/0013-routing.md`", output)


if __name__ == "__main__":
    unittest.main()
