"""Mirror test for `hydra_engine.checks.validator_registry` (the
third extension registry).

Three jobs: prove the registry is internally consistent, prove it reproduces
`cli.dispatch`'s prior manual interleave order exactly (the goldens depend on
this), and prove `checks_for` still behaves like the checks it replaced.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.checks import validator_registry  # noqa: E402
from hydra_engine.cli.dispatch import RepoContext  # noqa: E402
from hydra_engine import thresholds  # noqa: E402


def _ctx() -> RepoContext:
    root = Path(tempfile.mkdtemp(prefix="validator-registry-test-"))
    hydra = root / ".hydra-framework"
    for provider in ("claude", "codex"):
        capability_map = hydra / f"adapters/providers/{provider}/capability-map.yaml"
        capability_map.parent.mkdir(parents=True)
        capability_map.write_text(
            f"schema: hydra-framework.capability-map.v1\nprovider: {provider}\nverified: fixture\ncertainty: fixture\n"
            "delegation_controls:\n"
            "  generated_agent_policy: supported\n"
            "  generic_subagent_start_context: advisory\n"
            "  effort_class_capping: supported\n"
            "  max_active_workers: advisory\n"
            "  max_depth: advisory\n",
            encoding="utf-8",
        )
    config_root = hydra / "config"
    config_root.mkdir(parents=True)
    config_root.joinpath("engine-policy.yaml").write_text(_engine_policy(), encoding="utf-8")
    config_root.joinpath("delegation-policy.yaml").write_text(_delegation_policy(), encoding="utf-8")
    caller_evidence = hydra / "validation/capability-callers.yaml"
    caller_evidence.parent.mkdir(parents=True)
    caller_evidence.write_text(
        "\n".join([
            "schema: hydra-framework.capability-callers.v1",
            "mechanisms:",
            "  fixture:",
            "    classification: manual",
            "    implementation:",
            "      .hydra-framework/validation/capability-callers.yaml:",
            "        - fixture",
            "    callers:",
            "      .hydra-framework/validation/capability-callers.yaml:",
            "        - manual",
            "",
        ]),
        encoding="utf-8",
    )
    shape = hydra / "repo/knowledge/state-tiers.md"
    shape.parent.mkdir(parents=True)
    shape.write_text(_private_tier_shape(), encoding="utf-8")
    return RepoContext.for_root(root)


def _engine_policy() -> str:
    lines = ["schema: hydra-framework.engine-policy.v1", "thresholds:"]
    for entry in thresholds.THRESHOLDS:
        if entry.classification == thresholds.TEAM_TUNABLE_POLICY:
            lines.append(f"  {entry.key}: {entry.value}")
    return "\n".join(lines) + "\n"


def _delegation_policy() -> str:
    return (
        "schema: hydra-framework.delegation-policy.v1\n"
        "enabled: true\nmax_active_workers: 2\nmax_depth: 1\n"
        "allowed_reasons:\n  - inspection\n"
        "role_defaults:\n  allowed_capability_classes:\n    - fast-default\n  fallback_capability_class: fast-default\n  effort_ceiling: max\n"
        "roles: {}\n"
    )


def _private_tier_shape() -> str:
    paths = [
        "notes", "intake/raw", "intake/extracted", "intake/triage",
        "monitoring", "index", "logs", "baseline", "tasks/retired",
        "migrations", "evolution/experiments", "scratch", "plans",
        "research", "prompts", "diagrams", "source-material", "tickets",
        "bug-reports", "developer", "machine", "repo-overrides", "secrets",
    ]
    rows = "\n".join(f"| `{path}/` | fixture | fixture |" for path in paths)
    return f"""---
title: State Tiers
status: active
owners:
  team: hydra
certainty: confirmed
provenance:
  sources: []
---
# State Tiers

{rows}
"""


class RegistryConsistencyTests(unittest.TestCase):
    def test_no_name_is_claimed_by_two_validators(self):
        # The invariant that makes the registry reviewable as one flat list.
        # Enforced as a test, not at runtime, matching the object-family and
        # object-handler registries' equivalent invariants.
        seen: set[str] = set()
        for validator in validator_registry.VALIDATORS:
            self.assertNotIn(validator.name, seen, f"name `{validator.name}` claimed twice")
            seen.add(validator.name)

    def test_every_validator_has_a_name_and_a_callable_check(self):
        for validator in validator_registry.VALIDATORS:
            self.assertTrue(validator.name)
            self.assertTrue(callable(validator.check))


class LockedOrderTests(unittest.TestCase):
    def test_reproduces_the_prior_manual_interleave_exactly(self):
        # `cli.dispatch._validate_checks` used to write this order down by
        # hand: `package_and_task_findings`'s first two, `repo_findings`'s
        # seven, then `package_and_task_findings`'s last one. Byte-identical
        # contract goldens depend on this sequence, not any sorted version
        # of it.
        names = [validator.name for validator in validator_registry.VALIDATORS]
        self.assertEqual(
            names,
            [
                "task-records",
                "provider-surfaces",
                "module-metadata",
                "capability-maps",
                "task-contract-docs",
                "adaptations-ledger",
                "tier-boundaries",
                "private-tier-documented",
                "architecture",
                "object-model",
                "config-policy",
                "flat-knowledge",
                "knowledge-node-docs",
                "knowledge-v3",
                "capability-callers",
                "reflection-queue",
                "candidate-queue",
                "telemetry-evidence",
            ],
        )


class ChecksForTests(unittest.TestCase):
    def test_returns_zero_arg_checks_clean_on_a_fresh_tree(self):
        checks = validator_registry.checks_for(_ctx())
        self.assertEqual(len(checks), 18)
        for check in checks:
            self.assertEqual(check(), [])


if __name__ == "__main__":
    unittest.main()
