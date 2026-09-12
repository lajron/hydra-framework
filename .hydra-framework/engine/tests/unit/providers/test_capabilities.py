"""Mirror test for `hydra_engine.providers.capabilities`."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.providers import capabilities  # noqa: E402
from hydra_engine.providers.paths import ProvidersPaths  # noqa: E402


def _write(root: Path, rel: str, content: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _paths() -> ProvidersPaths:
    root = Path(tempfile.mkdtemp(prefix="providers-capabilities-"))
    return ProvidersPaths(root=root, hydra=root / ".hydra-framework")


CLAUDE_MAP = (
    "schema: hydra-framework.capability-map.v1\n"
    "provider: claude\n"
    "verified: fixture\n"
    "certainty: fixture\n"
    "capability_classes:\n"
    "  deep-reasoning: opus\n"
    "effort_budgets:\n"
    "  standard: high\n"
    "  high: xhigh\n"
    "delegation_controls:\n"
    "  generated_agent_policy: supported\n"
    "  generic_subagent_start_context: advisory\n"
    "  effort_class_capping: supported\n"
    "  max_active_workers: advisory\n"
    "  max_depth: advisory\n"
)


class ResolveCapabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mapping = {
            "capability_classes": {"deep-reasoning": "opus", "local-private": "unresolved"},
            "effort_budgets": {"standard": "high"},
        }

    def test_resolves_known_values(self):
        self.assertEqual(capabilities.resolve_capability(self.mapping, "capability_classes", "deep-reasoning"), "opus")
        self.assertEqual(capabilities.resolve_capability(self.mapping, "effort_budgets", "standard"), "high")

    def test_unresolved_and_unknown_return_empty(self):
        self.assertEqual(capabilities.resolve_capability(self.mapping, "capability_classes", "local-private"), "")
        self.assertEqual(capabilities.resolve_capability(self.mapping, "capability_classes", "nonexistent"), "")
        self.assertEqual(capabilities.resolve_capability(self.mapping, "capability_classes", ""), "")
        self.assertEqual(capabilities.resolve_capability({}, "effort_budgets", "standard"), "")


class FrontmatterBlockTests(unittest.TestCase):
    def test_omits_empty_fields(self):
        block = capabilities.frontmatter_block([("name", "x"), ("model", ""), ("effort", "high")])
        self.assertEqual(block, "---\nname: x\neffort: high\n---")


class CapabilityMapTests(unittest.TestCase):
    def test_loads_valid_map(self):
        paths = _paths()
        _write(paths.root, ".hydra-framework/adapters/providers/claude/capability-map.yaml", CLAUDE_MAP)
        data = capabilities.capability_map(paths, "claude")
        self.assertEqual(data.get("provider"), "claude")

    def test_missing_map_returns_empty(self):
        paths = _paths()
        self.assertEqual(capabilities.capability_map(paths, "claude"), {})

    def test_wrong_schema_returns_empty(self):
        paths = _paths()
        _write(
            paths.root,
            ".hydra-framework/adapters/providers/claude/capability-map.yaml",
            "schema: something-else\n",
        )
        self.assertEqual(capabilities.capability_map(paths, "claude"), {})


class ValidateCapabilityMapsTests(unittest.TestCase):
    def test_ok_when_every_class_and_budget_resolves(self):
        paths = _paths()
        _write(
            paths.root,
            ".hydra-framework/capabilities/agents/demo/metadata.yaml",
            "name: demo\ncapability_class: deep-reasoning\neffort: standard\n",
        )
        _write(paths.root, ".hydra-framework/adapters/providers/claude/capability-map.yaml", CLAUDE_MAP)
        _write(
            paths.root,
            ".hydra-framework/adapters/providers/codex/capability-map.yaml",
            CLAUDE_MAP.replace("provider: claude", "provider: codex"),
        )
        self.assertEqual(capabilities.validate_capability_maps(paths), [])

    def test_missing_capability_map_is_an_error(self):
        paths = _paths()
        errors = capabilities.validate_capability_maps(paths)
        self.assertTrue(any("is missing" in error for error in errors))

    def test_unresolved_class_is_reported(self):
        paths = _paths()
        _write(
            paths.root,
            ".hydra-framework/capabilities/agents/demo/metadata.yaml",
            "name: demo\ncapability_class: local-private\neffort: standard\n",
        )
        _write(paths.root, ".hydra-framework/adapters/providers/claude/capability-map.yaml", CLAUDE_MAP)
        _write(
            paths.root,
            ".hydra-framework/adapters/providers/codex/capability-map.yaml",
            CLAUDE_MAP.replace("provider: claude", "provider: codex"),
        )
        errors = capabilities.validate_capability_maps(paths)
        self.assertTrue(any("local-private" in error for error in errors))

    def test_delegation_controls_are_required(self):
        paths = _paths()
        _write(
            paths.root,
            ".hydra-framework/adapters/providers/claude/capability-map.yaml",
            "schema: hydra-framework.capability-map.v1\nprovider: claude\nverified: fixture\ncertainty: fixture\n",
        )
        _write(
            paths.root,
            ".hydra-framework/adapters/providers/codex/capability-map.yaml",
            CLAUDE_MAP.replace("provider: claude", "provider: codex"),
        )
        errors = capabilities.validate_capability_maps(paths)
        self.assertTrue(any("delegation_controls" in error for error in errors))


class WrapperRenderingTests(unittest.TestCase):
    def _skill_dir(self, paths: ProvidersPaths) -> Path:
        _write(
            paths.root,
            ".hydra-framework/capabilities/skills/demo-skill/metadata.yaml",
            "name: demo-skill\ndescription: Use when relevant.\nkind: command\n",
        )
        _write(paths.root, ".hydra-framework/capabilities/skills/demo-skill/skill.md", "# Demo Skill\n\nBody.\n")
        return paths.root / ".hydra-framework/capabilities/skills/demo-skill"

    def _agent_dir(self, paths: ProvidersPaths) -> Path:
        _write(
            paths.root,
            ".hydra-framework/capabilities/agents/demo-agent/metadata.yaml",
            "name: demo-agent\ndescription: Use for the role.\ncapability_class: deep-reasoning\neffort: standard\n"
            "tools:\n  - Read\n  - Write\ndependencies:\n  knowledge:\n    - overview.md\n  skills:\n    - other-skill\n",
        )
        _write(paths.root, ".hydra-framework/capabilities/agents/demo-agent/agent.md", "# Demo Agent\n\nBody.\n")
        return paths.root / ".hydra-framework/capabilities/agents/demo-agent"

    def test_build_skill_wrapper_marks_commands_non_model_invocable(self):
        paths = _paths()
        skill_dir = self._skill_dir(paths)
        name, files = capabilities.build_skill_wrapper(skill_dir, "claude", paths.root)
        self.assertEqual(name, "hydra-demo-skill")
        self.assertIn("disable-model-invocation: true", files["SKILL.md"])
        self.assertIn("canonical_source: .hydra-framework/capabilities/skills/demo-skill/skill.md", files[".hydra-adapter.yaml"])

    def test_build_agent_wrapper_resolves_model_and_lists_dependencies(self):
        paths = _paths()
        agent_dir = self._agent_dir(paths)
        _write(paths.root, ".hydra-framework/adapters/providers/claude/capability-map.yaml", CLAUDE_MAP)
        mapping = capabilities.capability_map(paths, "claude")
        name, files = capabilities.build_agent_wrapper(agent_dir, "claude", mapping, paths.root)
        self.assertEqual(name, "hydra-demo-agent")
        body = files[f"{name}.md"]
        self.assertIn("model: opus", body)
        self.assertIn("effort: high", body)
        self.assertIn("`.hydra-framework/overview.md`", body)
        self.assertIn("`hydra-other-skill`", body)
        self.assertIn("`.hydra-framework/capabilities/skills/other-skill/skill.md`", body)
        self.assertIn("## Delegation Policy", body)

    def test_build_agent_wrapper_applies_role_capability_fallback_and_effort_ceiling(self):
        paths = _paths()
        agent_dir = self._agent_dir(paths)
        config = capabilities.hydra_config.EffectiveConfig(
            thresholds={},
            delegation=capabilities.hydra_config.DelegationPolicy(
                enabled=True,
                max_active_workers=2,
                max_depth=1,
                allowed_reasons=("inspection",),
                role_defaults=capabilities.hydra_config.RolePolicy(("fast-default",), "fast-default", "low"),
                roles={"demo-agent": capabilities.hydra_config.RolePolicy(("fast-default",), "fast-default", "low")},
            ),
        )
        mapping = {
            "capability_classes": {"fast-default": "inherit", "deep-reasoning": "opus"},
            "effort_budgets": {"low": "low", "standard": "high"},
            "delegation_controls": {"max_active_workers": "supported", "max_depth": "supported", "generic_subagent_start_context": "supported"},
        }
        _name, files = capabilities.build_agent_wrapper(agent_dir, "claude", mapping, paths.root, config)
        body = files["hydra-demo-agent.md"]
        self.assertIn("model: inherit", body)
        self.assertIn("effort: low", body)

    def test_build_codex_agent_wrapper_omits_model_when_unresolved(self):
        paths = _paths()
        agent_dir = self._agent_dir(paths)
        name, files = capabilities.build_codex_agent_wrapper(agent_dir, "codex", {}, paths.root)
        self.assertEqual(name, "hydra-demo-agent")
        content = files[f"{name}.toml"]
        self.assertNotIn("model =", content)
        self.assertIn("developer_instructions =", content)

    def test_build_codex_agent_wrapper_applies_effort_ceiling(self):
        paths = _paths()
        agent_dir = self._agent_dir(paths)
        config = capabilities.hydra_config.EffectiveConfig(
            thresholds={},
            delegation=capabilities.hydra_config.DelegationPolicy(
                enabled=True,
                max_active_workers=2,
                max_depth=1,
                allowed_reasons=("inspection",),
                role_defaults=capabilities.hydra_config.RolePolicy(("deep-reasoning",), "deep-reasoning", "low"),
                roles={"demo-agent": capabilities.hydra_config.RolePolicy(("deep-reasoning",), "deep-reasoning", "low")},
            ),
        )
        name, files = capabilities.build_codex_agent_wrapper(
            agent_dir,
            "codex",
            {
                "capability_classes": {"deep-reasoning": "unresolved"},
                "effort_budgets": {"low": "low", "standard": "medium"},
                "delegation_controls": {"max_active_workers": "supported", "max_depth": "supported", "generic_subagent_start_context": "supported"},
            },
            paths.root,
            config,
        )
        self.assertIn('model_reasoning_effort = "low"', files[f"{name}.toml"])


class RegistryConsistencyTests(unittest.TestCase):
    """The fourth extension registry: `PROVIDERS`."""

    def test_no_slug_is_claimed_by_two_providers(self):
        # The invariant that makes the registry reviewable as one flat list,
        # matching the object-family, object-handler, and validator
        # registries' equivalent invariant.
        seen: set[str] = set()
        for provider in capabilities.PROVIDERS:
            self.assertNotIn(provider.slug, seen, f"slug `{provider.slug}` claimed twice")
            seen.add(provider.slug)

    def test_every_provider_has_a_slug_skills_target_and_callable_builder(self):
        for provider in capabilities.PROVIDERS:
            self.assertTrue(provider.slug)
            self.assertTrue(provider.skills_target)
            self.assertTrue(provider.agent_extension)
            self.assertTrue(callable(provider.build_agent_wrapper))

    def test_each_providers_wrapper_builder_is_the_one_it_used_to_be_branched_to(self):
        # `adapter_plan.planned_adapter_files` used to pick the builder with
        # `if provider == "codex":`. The field replaces the branch, so it
        # must resolve to the same function per provider.
        by_slug = {provider.slug: provider for provider in capabilities.PROVIDERS}
        self.assertIs(by_slug["claude"].build_agent_wrapper, capabilities.build_agent_wrapper)
        self.assertIs(by_slug["codex"].build_agent_wrapper, capabilities.build_codex_agent_wrapper)


if __name__ == "__main__":
    unittest.main()
