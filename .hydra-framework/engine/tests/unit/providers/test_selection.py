"""Mirror tests for capability-profile selection and validation."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.providers.adapter_plan import planned_adapter_files  # noqa: E402
from hydra_engine.providers.paths import ProvidersPaths  # noqa: E402
from hydra_engine.providers.selection import resolve_capability_selection, validate_capability_profiles  # noqa: E402


def _write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _paths() -> ProvidersPaths:
    root = Path(tempfile.mkdtemp(prefix="providers-selection-"))
    _write(root, ".hydra-framework/capabilities/profiles.yaml", "schema: hydra-framework.capability-profiles.v1\nbaseline_tags:\n  - base\ndefault_profile: focused\nprofiles:\n  focused:\n    tags:\n      - focused\n")
    for name, tags in [("base-skill", "  - base\n"), ("focused-skill", "  - focused\n"), ("untagged", "")]:
        _write(root, f".hydra-framework/capabilities/skills/{name}/metadata.yaml", f"name: {name}\ndependencies:\n  skills: []\n" + (f"tags:\n{tags}" if tags else ""))
        _write(root, f".hydra-framework/capabilities/skills/{name}/skill.md", f"# {name}\n")
    return ProvidersPaths(root=root, hydra=root / ".hydra-framework")


class CapabilitySelectionTests(unittest.TestCase):
    def test_full_selects_every_skill_with_a_full_reason(self):
        selection = resolve_capability_selection(_paths(), "full")
        self.assertEqual([path.name for path in selection.skills], ["base-skill", "focused-skill", "untagged"])
        self.assertEqual(set(selection.reasons.values()), {("full-profile",)})

    def test_profile_selects_union_of_baseline_and_profile_tags_with_sorted_reasons(self):
        paths = _paths()
        _write(paths.root, ".hydra-framework/capabilities/skills/base-skill/metadata.yaml", "name: base-skill\ntags:\n  - base\n  - focused\n")
        selection = resolve_capability_selection(paths)
        self.assertEqual([path.name for path in selection.skills], ["base-skill", "focused-skill"])
        self.assertEqual(selection.reasons[selection.skills[0]], ("baseline-tag:base", "profile-tag:focused"))

    def test_local_profile_shadows_shared_profile(self):
        paths = _paths()
        _write(paths.root, ".hydra-framework.local/capabilities/profiles.yaml", "schema: hydra-framework.local-capability-profiles.v1\nprofiles:\n  focused:\n    tags:\n      - base\n")
        selection = resolve_capability_selection(paths)
        self.assertEqual([path.name for path in selection.skills], ["base-skill"])

    def test_selection_does_not_change_shared_adapter_bytes(self):
        paths = _paths()
        full = planned_adapter_files(paths)
        selection = resolve_capability_selection(paths)
        narrow = planned_adapter_files(paths, selection.skills)
        self.assertEqual(narrow, {path: full[path] for path in narrow})

    def test_agent_rendering_is_identical_for_full_and_narrow_profiles(self):
        paths = _paths()
        _write(
            paths.root,
            ".hydra-framework/capabilities/agents/demo/metadata.yaml",
            "name: demo\ndependencies:\n  skills:\n    - untagged\n",
        )
        _write(paths.root, ".hydra-framework/capabilities/agents/demo/agent.md", "# Demo\n")
        full = planned_adapter_files(paths, resolve_capability_selection(paths, "full").skills)
        narrow = planned_adapter_files(paths, resolve_capability_selection(paths, "focused").skills)
        agent_paths = [path for path in full if "hydra-demo" in path.name]
        self.assertEqual({path: narrow[path] for path in agent_paths}, {path: full[path] for path in agent_paths})
        self.assertTrue(all("`hydra-untagged` -- `.hydra-framework/capabilities/skills/untagged/skill.md`" in full[path] for path in agent_paths if path.suffix in {".md", ".toml"}))


class CapabilityProfileValidationTests(unittest.TestCase):
    def test_validates_tags_dependencies_and_wrapper_names(self):
        paths = _paths()
        self.assertEqual(validate_capability_profiles(paths), [])
        _write(paths.root, ".hydra-framework/capabilities/skills/base-skill/metadata.yaml", "name: base-skill\ntags:\n  - Bad_Tag\ndependencies:\n  skills:\n    - missing\n")
        _write(paths.root, ".hydra-framework/capabilities/skills/base-skill/skill.md", "# base\n\nhydra-focused-skill\n")
        details = [finding.detail for finding in validate_capability_profiles(paths)]
        self.assertTrue(any("invalid tag" in detail for detail in details))
        self.assertTrue(any("does not exist" in detail for detail in details))
        self.assertTrue(any("canonical prose" in detail for detail in details))
