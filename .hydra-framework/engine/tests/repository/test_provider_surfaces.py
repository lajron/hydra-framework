"""Repository invariant: every provider-native file in this repository is
Hydra-generated, none unmanaged. Moved
from `scripts/tests/test_hydra.py`'s frozen `SurfaceClassificationTests`, one
of the named Hard-Constraint live-repository classes."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.providers.adapter_plan import ownership_paths  # noqa: E402
from hydra_engine.providers.paths import ProvidersPaths  # noqa: E402
from hydra_engine.providers.reclaim import classify_surfaces, provider_surface_notice  # noqa: E402
from hydra_engine.providers.selection import resolve_capability_selection  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
PATHS = ProvidersPaths(root=ROOT, hydra=ROOT / ".hydra-framework")


class SurfaceClassificationTests(unittest.TestCase):
    def test_repository_surfaces_are_all_generated(self) -> None:
        surfaces = classify_surfaces(PATHS)
        unmanaged = [item for item in surfaces if item["status"] != "generated"]
        self.assertEqual(
            unmanaged, [], "run `hydra.py export-adapters` or `hydra.py reclaim` to resolve unmanaged surfaces"
        )
        # Non-vacuity: generated adapters are untracked now, so an unbootstrapped
        # checkout would satisfy the assertion above on an empty list. Only a
        # body file (not its sidecar) is classified, so compare against the
        # body-only slice of the ownership index -- a sidecar's own name always
        # starts with `.hydra-adapter`.
        owned_bodies = {path for path in ownership_paths(PATHS) if not path.name.startswith(".")}
        self.assertEqual(
            len(surfaces), len(owned_bodies),
            "no provider surfaces are materialized; run `hydra.py export-adapters` first",
        )

    def test_non_provider_paths_produce_no_notice(self) -> None:
        self.assertEqual(provider_surface_notice(PATHS, ROOT / "README.md"), [])
        self.assertEqual(provider_surface_notice(PATHS, Path("/etc/hosts")), [])

    def test_ignored_names_produce_no_notice(self) -> None:
        self.assertEqual(provider_surface_notice(PATHS, ROOT / ".claude/skills/README.md"), [])

    def test_initial_profile_tagging_selects_only_the_reviewed_catalog_batch(self) -> None:
        core = resolve_capability_selection(PATHS, "core")
        maintainer = resolve_capability_selection(PATHS, "hydra-maintainer")
        self.assertEqual([skill.name for skill in core.skills], ["repository-inspection"])
        self.assertEqual(
            [skill.name for skill in maintainer.skills],
            ["complexity-review", "hydra-cleanup", "repository-inspection", "seed-reconciliation"],
        )


if __name__ == "__main__":
    unittest.main()
