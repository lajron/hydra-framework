"""Core goldens: doctor, validate, selftest."""

from __future__ import annotations

import contextlib
import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from .fixtures import CAPABILITY_CALLERS_FIXTURE, CONFIG_POLICY_FIXTURE, PORTABLE_PROVIDER_SUPPORT_FIXTURE, PRIVATE_TIER_SHAPE_FIXTURE, PROVIDER_CAPABILITY_MAPS_FIXTURE, assert_golden, git_init, run_golden

_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

_REENTRANCY_GUARD_ENV = "_HYDRA_GOLDEN_SELFTEST_GUARD"


class CoreGoldenTests(unittest.TestCase):
    def test_doctor_happy_path(self):
        outcome = run_golden(["doctor"], extra_fixture={
            ".gitignore": ".hydra-framework.local/\n",
            ".hydra-framework/repo/knowledge/state-tiers.md": PRIVATE_TIER_SHAPE_FIXTURE,
            ".hydra-framework/validation/capability-callers.yaml": CAPABILITY_CALLERS_FIXTURE,
            **PORTABLE_PROVIDER_SUPPORT_FIXTURE,
            **CONFIG_POLICY_FIXTURE,
            **PROVIDER_CAPABILITY_MAPS_FIXTURE,
        }, pre_run=git_init)
        assert_golden(self, "core-doctor", outcome)

    def test_validate_happy_path(self):
        outcome = run_golden(["validate"], extra_fixture={
            ".hydra-framework/repo/knowledge/state-tiers.md": PRIVATE_TIER_SHAPE_FIXTURE,
            ".hydra-framework/validation/capability-callers.yaml": CAPABILITY_CALLERS_FIXTURE,
            **CONFIG_POLICY_FIXTURE,
            **PROVIDER_CAPABILITY_MAPS_FIXTURE,
        })
        assert_golden(self, "core-validate", outcome)

    def test_selftest_happy_path(self):
        """`command_selftest` discovers tests via `Path(__file__).parent /
        "tests"` — the *real* `scripts/tests/` on disk, unaffected by
        `RepoContext` (see the plan's "Hard constraints found in the tree") —
        and that real suite includes classes that themselves assert against
        the live repository (`RepositoryInvariantTests`, `TierBoundaryTests`,
        and others the plan names). Running `selftest` through `run_golden`'s
        synthetic fixture would swap `ROOT`/`HYDRA` out from under those
        classes for the call's duration and fail them for the wrong reason —
        so this one golden runs against the real ambient root (`ctx=None`),
        not a fixture, and only asserts the structural shape (exit 0, a
        trailing `OK`) rather than a byte-exact comparison, since the real
        suite's test count grows over time. Byte-exact coverage of
        `command_selftest`'s own logic (discovery, `--verbose`) remains
        deferred until test discovery is package-relative instead of
        repo-root-relative.

        Real ambient root also means `command_selftest`'s additive
        `engine/tests/` discovery finds *this very test* and would re-run
        it, and it would re-run `selftest` again, forever. The env-var guard
        breaks that cycle: it is set for the duration of the outer call, so
        the nested occurrence of this same test sees it already set and
        skips instead of recursing.
        """
        if os.environ.get(_REENTRANCY_GUARD_ENV):
            self.skipTest("nested recursive selftest invocation; guarded")

        import hydra

        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {_REENTRANCY_GUARD_ENV: "1"}):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = hydra.main(["selftest"])
        self.assertEqual(exit_code, 0, stderr.getvalue()[-2000:])
        # unittest.TextTestRunner's default stream is stderr, not stdout.
        self.assertIn("OK", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
