"""Repository invariant: generated provider adapters are Git-ignored, not
tracked, and the ignore rules ignore exactly what Hydra owns -- no more, no
less. Runs against this repository's own real state and real Git, the same
way `test_tier_boundaries.py`'s `private_tier_ignored` check does."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.providers import git_ownership  # noqa: E402
from hydra_engine.providers.paths import ProvidersPaths  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
PATHS = ProvidersPaths(root=ROOT, hydra=ROOT / ".hydra-framework")


class GitOwnershipTests(unittest.TestCase):
    def test_every_ownership_path_is_ignored(self) -> None:
        self.assertEqual(git_ownership.unignored_ownership_findings(PATHS), [])

    def test_no_ownership_path_is_tracked(self) -> None:
        self.assertEqual(git_ownership.tracked_ownership_findings(PATHS), [])

    def test_every_observed_ignored_provider_path_is_a_verified_owner(self) -> None:
        self.assertEqual(git_ownership.unverified_ignored_provider_findings(PATHS), [])

    def test_no_tracked_provider_file_is_ignored(self) -> None:
        self.assertEqual(git_ownership.tracked_and_ignored_provider_findings(PATHS), [])

    def test_gitignore_carries_the_marked_generated_adapter_block(self) -> None:
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(git_ownership.IGNORE_BLOCK_HEADER, text)
        for pattern in git_ownership.generated_adapter_ignore_patterns():
            self.assertIn(pattern, text)


if __name__ == "__main__":
    unittest.main()
