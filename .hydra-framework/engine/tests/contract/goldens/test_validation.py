"""`validate`/`doctor` failure-path goldens.

A fixture that triggers every `validate_*`
family member's failure message in one run, proving the `Finding`-based
aggregation (`hydra_engine.checks` + `hydra_engine.commands.validation`)
still renders byte-identical text to the pre-conversion `list[str]` version.
`validate_architecture` is the one family member this fixture cannot
exercise: the sealed tmp fixture has no real `engine/src/hydra_engine/`
tree for `architecture.check()` to walk, so it always reports clean inside a
golden -- that check's own ~35 negative cases live in
`engine/tests/unit/test_architecture.py` instead.
"""

from __future__ import annotations

import unittest

from ..harness import run_command
from .fixtures import (CONFIG_POLICY_FIXTURE, PROVIDER_CAPABILITY_MAPS_FIXTURE, assert_golden, frozen_ports,
                       hydra_object_markdown, knowledge_space_fixture, run_golden)

EVERY_VALIDATOR_FAILS_FIXTURE = {
    # task_records_check: missing sections (no "## Readiness" etc.) and an
    # Owner header that does not match the directory it lives in.
    ".hydra-framework/tasks/personal/dana/2026-01-01-x.md": (
        "Owner: someone-else\nUpdated: 2026-01-01\n\n## Goal\n\nDo a thing.\n"
    ),
    # provider_surfaces_check: a provider-native file with no canonical source.
    ".claude/skills/deploy/SKILL.md": '---\nname: deploy\ndescription: "Deploy the thing"\n---\nBody text.\n',
    # validate_module_metadata: a body file with no metadata.yaml beside it.
    ".hydra-framework/capabilities/skills/broken/skill.md": "# Broken\n\nNo metadata.yaml next to this file.\n",
    # validate_capability_maps: overrides BASE_FIXTURE's claude map, dropping `certainty`.
    ".hydra-framework/adapters/providers/claude/capability-map.yaml": (
        "schema: hydra-framework.capability-map.v1\nprovider: claude\nverified: fixture\n"
    ),
    # validate_task_contract_docs: overrides BASE_FIXTURE's template, dropping "## Readiness".
    ".hydra-framework/tasks/templates/task.md": "# Task: <short-name>\n\nStatus: active\n\n## Goal\n\nDescribe it.\n",
    # validate_adaptations_ledger: an entry missing `Base seed version:`, with
    # an invalid disposition and no `Paths touched:`/`Why:`/`Evidence:` bullets.
    ".hydra-framework/evolution/adaptations.md": "## 2026-01-01 - example\n\nDisposition: maybe\n",
    # validate_tier_boundaries: private-tier content left in the shared tree.
    ".hydra-framework/intake/raw/leftover.md": "Should have moved to the private tier.\n",
    # object_model_check: two canonical objects sharing one hydra_id.
    ".hydra-framework/repo/knowledge-units/0001-a.md": hydra_object_markdown(
        hydra_id="hydra://knowledge-unit/duplicate", title="A"
    ),
    ".hydra-framework/repo/knowledge-units/0002-b.md": hydra_object_markdown(
        hydra_id="hydra://knowledge-unit/duplicate", title="B"
    ),
    # package_docs_check: a knowledge space with a broken relative link.
    **knowledge_space_fixture(overview="[broken](missing.md)\n"),
    # capability_callers_check: bad classification, with snippets that still resolve.
    ".hydra-framework/validation/capability-callers.yaml": (
        "schema: hydra-framework.capability-callers.v1\n"
        "mechanisms:\n"
        "  broken:\n"
        "    classification: maybe\n"
        "    implementation:\n"
        "      .hydra-framework/validation/capability-callers.yaml:\n"
        "        - broken\n"
        "    callers:\n"
        "      .hydra-framework/validation/capability-callers.yaml:\n"
        "        - maybe\n"
    ),
}


class ValidationGoldenTests(unittest.TestCase):
    def test_validate_reports_every_validator_failure(self):
        outcome = run_golden(["validate"], extra_fixture={**CONFIG_POLICY_FIXTURE, **PROVIDER_CAPABILITY_MAPS_FIXTURE, **EVERY_VALIDATOR_FAILS_FIXTURE}, owner="example-owner")
        assert_golden(self, "validation-validate-every-failure", outcome)

    def test_doctor_reports_missing_required_paths(self):
        # `run_golden` always starts from `BASE_FIXTURE`, which already
        # satisfies every `REQUIRED_PATHS` entry, and `extra_fixture` can
        # only add files, never remove one -- so this bypasses it and builds
        # a deliberately incomplete tree directly through the harness.
        with frozen_ports():
            outcome = run_command(["doctor"], fixture={"AI_SYSTEM.md": "# AI System Entry Point\n"})
        assert_golden(self, "validation-doctor-missing-required-paths", outcome)


if __name__ == "__main__":
    unittest.main()
