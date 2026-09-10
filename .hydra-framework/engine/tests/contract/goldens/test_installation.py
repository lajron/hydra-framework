"""installation goldens: init, adopt, install-hooks."""

from __future__ import annotations

import unittest

from .fixtures import PORTABLE_PROVIDER_SUPPORT_FIXTURE, assert_golden, external_dir, git_init, run_golden


class InstallationGoldenTests(unittest.TestCase):
    def test_init_happy_path(self):
        with external_dir() as target:
            outcome = run_golden(
                ["init", "--target", str(target)], extra_fixture=PORTABLE_PROVIDER_SUPPORT_FIXTURE
            )
            assert_golden(self, "installation-init", outcome, stdout_replacements={str(target): "<INIT_TARGET>"})

    def test_init_dry_run(self):
        with external_dir() as target:
            outcome = run_golden(
                ["init", "--target", str(target), "--dry-run"],
                extra_fixture=PORTABLE_PROVIDER_SUPPORT_FIXTURE,
            )
            assert_golden(self, "installation-init-dry-run", outcome, stdout_replacements={str(target): "<INIT_TARGET>"})

    def test_init_conflict_without_force_refuses(self):
        with external_dir({"AI_SYSTEM.md": "# Existing target copy\n"}) as target:
            outcome = run_golden(
                ["init", "--target", str(target)], extra_fixture=PORTABLE_PROVIDER_SUPPORT_FIXTURE
            )
            assert_golden(self, "installation-init-conflict-refusal", outcome, stdout_replacements={str(target): "<INIT_TARGET>"})

    def test_init_force_overwrites_conflict(self):
        with external_dir({"AI_SYSTEM.md": "# Existing target copy\n"}) as target:
            outcome = run_golden(
                ["init", "--target", str(target), "--force"],
                extra_fixture=PORTABLE_PROVIDER_SUPPORT_FIXTURE,
            )
            assert_golden(self, "installation-init-force-overwrite", outcome, stdout_replacements={str(target): "<INIT_TARGET>"})

    def test_init_local_check(self):
        outcome = run_golden(
            ["init-local", "--check"],
            extra_fixture={".gitignore": ".hydra-framework.local/\n"},
            pre_run=git_init,
        )
        assert_golden(self, "installation-init-local-check", outcome)

    # `adopt` without `--record` has no golden: `command_adopt` prints
    # `Repository root: {paths.root}`, which embeds the contract harness's own
    # per-run tmpdir -- the same non-determinism that dropped
    # a "task not found" golden elsewhere. `external_file()`/`external_dir()` scrub a
    # named *second* root, not the fixture root itself, so there is no
    # `stdout_replacements` value available to scrub this one. Covered instead
    # by `installation/test_adopt.py::AdoptionReportTests` and
    # `commands/test_installation.py::CommandAdoptTests.test_happy_path_reports_integrity_present`
    # / `test_missing_paths_reports_incomplete_copy`.

    def test_adopt_record_happy_path(self):
        outcome = run_golden(
            ["adopt", "--record", "--repo", "fixture-repo"],
            extra_fixture=PORTABLE_PROVIDER_SUPPORT_FIXTURE,
        )
        assert_golden(self, "installation-adopt-record", outcome)

    def test_adopt_record_already_recorded(self):
        outcome = run_golden(
            ["adopt", "--record", "--repo", "fixture-repo"],
            extra_fixture={
                **PORTABLE_PROVIDER_SUPPORT_FIXTURE,
                ".hydra-framework/manifest.yaml": (
                    "schema: hydra-framework.manifest.v1\n"
                    "framework_name: hydra-framework\n"
                    "seed_version: 0.1.0\n"
                    "status: foundation-seed\n"
                    "entry_point: ../AI_SYSTEM.md\n"
                    "\n"
                    "lineage:\n"
                    "  base_seed_version: 0.1.0\n"
                    "  adopted_into: already-adopted-repo\n"
                    "  adopted_date: 2026-01-01\n"
                    "  divergence_policy: reconcile-before-promoting\n"
                )
            },
        )
        assert_golden(self, "installation-adopt-record-already-recorded", outcome)

    # `adopt --record`'s missing-required-paths refusal is covered by
    # `installation/test_adopt.py::RecordLineageTests.test_missing_required_paths_refuses`
    # and `commands/test_installation.py::CommandAdoptTests.test_record_missing_paths_refuses_on_stderr`.

    def test_install_hooks_happy_path(self):
        outcome = run_golden(
            ["install-hooks"],
            extra_fixture={".hydra-framework/hooks/pre-push": "#!/bin/sh\necho hi\n"},
            pre_run=git_init,
        )
        assert_golden(self, "installation-install-hooks", outcome)

    def test_install_hooks_uninstall(self):
        outcome = run_golden(
            ["install-hooks", "--uninstall"],
            extra_fixture={".hydra-framework/hooks/pre-push": "#!/bin/sh\necho hi\n"},
            pre_run=git_init,
        )
        assert_golden(self, "installation-install-hooks-uninstall", outcome)


if __name__ == "__main__":
    unittest.main()
