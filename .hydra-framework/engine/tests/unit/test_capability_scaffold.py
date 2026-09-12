"""Tests for capability scaffold text renderers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine import capability_scaffold  # noqa: E402


class CapabilityScaffoldTests(unittest.TestCase):
    def test_skill_text_has_canonical_identity_and_required_sections(self):
        metadata = capability_scaffold.skill_metadata_text("demo-skill", "Demo skill.", "uid", "procedure")
        body = capability_scaffold.skill_body_text("Demo Skill")
        self.assertIn("hydra_id: hydra://capability/skill/demo-skill", metadata)
        self.assertIn("tags: []", metadata)
        for section in ("## Capability", "## Procedure", "## Output", "## Boundaries"):
            self.assertIn(section, body)

    def test_agent_text_has_canonical_identity_and_required_sections(self):
        metadata = capability_scaffold.agent_metadata_text("demo-agent", "Demo agent.", "uid", "fast-default", "standard")
        body = capability_scaffold.agent_body_text("Demo Agent")
        self.assertIn("hydra_id: hydra://capability/agent/demo-agent", metadata)
        for section in ("## Purpose", "## Responsibilities", "## Boundaries"):
            self.assertIn(section, body)


if __name__ == "__main__":
    unittest.main()
