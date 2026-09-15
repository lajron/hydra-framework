"""Mirror test for `hydra_engine.identity.object_families` (the
first extension registry).

Three jobs: prove resolution did not change when the flat map became a
registry, prove the registry is internally consistent (the invariant
`family_for`'s two passes rely on), and prove the enforcement the flat map
could not express.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.identity import object_families  # noqa: E402


class ResolutionParityTests(unittest.TestCase):
    """The three cases the flat map's own test asserted, unchanged."""

    def test_family_resolves_by_prefix_then_kind(self):
        self.assertEqual(object_families.family_for("hydra://source/0001-test", ""), "Source")
        self.assertEqual(object_families.family_for("hydra://unknown-prefix/x", "work"), "Work")
        self.assertEqual(object_families.family_for("hydra://unknown-prefix/x", "mystery"), "Unknown")

    def test_prefix_wins_over_kind_across_the_whole_registry(self):
        # Not merely "the prefix is checked first within a family": every
        # family's prefixes are consulted before any family's kinds.
        self.assertEqual(object_families.family_for("hydra://source/0001-test", "skill"), "Source")

    def test_a_non_hydra_id_falls_back_to_kind_alone(self):
        self.assertEqual(object_families.family_for("", "source"), "Source")
        self.assertEqual(object_families.family_for("not-a-hydra-id", "source"), "Source")


class RegistryConsistencyTests(unittest.TestCase):
    def test_no_token_is_claimed_by_two_families(self):
        # The invariant that makes `family_for`'s answer independent of tuple
        # order. Enforced as a test, not at runtime: the registry is code, so
        # the point of edit is where this is reviewable.
        for attribute in ("id_prefixes", "kinds"):
            claimed: dict[str, str] = {}
            for family in object_families.OBJECT_FAMILIES:
                for token in getattr(family, attribute):
                    self.assertNotIn(
                        token, claimed,
                        f"{attribute} token `{token}` claimed by both {claimed.get(token)} and {family.name}",
                    )
                    claimed[token] = family.name

    def test_every_family_claims_at_least_one_prefix_and_one_kind(self):
        for family in object_families.OBJECT_FAMILIES:
            self.assertTrue(family.id_prefixes, f"{family.name} claims no id prefix")
            self.assertTrue(family.kinds, f"{family.name} claims no kind")

    def test_the_four_kinds_this_repository_authors_are_registered(self):
        # These were absent from the flat map: they resolved to Capability only
        # via the `hydra://capability/` prefix, so a misspelling was invisible.
        for kind in ("agent", "skill", "workflow", "tool-capability-registry", "capability-profile-policy"):
            self.assertEqual(object_families.family_for("", kind), "Capability")

    def test_runtime_engine_is_registered(self):
        # Registered by the object-handler slice, which is what made it
        # matchable: `.py` is now a document form `objects.object_handlers`
        # claims, so the 2026-08-19 registration gap is closed.
        names = [family.name for family in object_families.OBJECT_FAMILIES]
        self.assertIn("Runtime/Engine", names)
        self.assertEqual(object_families.family_for("hydra://engine-module/x", ""), "Runtime/Engine")
        self.assertEqual(object_families.family_for("", "engine-module"), "Runtime/Engine")

    def test_knowledge_unit_is_registered(self):
        # Units are a new Knowledge-family member alongside
        # packages, slices, and templates, not a new family of their own.
        self.assertEqual(object_families.family_for("hydra://knowledge-unit/x/y", ""), "Knowledge")
        self.assertEqual(object_families.family_for("", "knowledge-unit"), "Knowledge")

    def test_telemetry_is_registered(self):
        # Telemetry is a first-class object family.
        names = [family.name for family in object_families.OBJECT_FAMILIES]
        self.assertIn("Telemetry", names)
        self.assertEqual(object_families.family_for("hydra://telemetry-evidence/x", ""), "Telemetry")
        self.assertEqual(object_families.family_for("", "telemetry-evidence"), "Telemetry")

    def test_source_integration_kind_is_registered(self):
        # source-integration is reserved for Hydra source-integration
        # workspaces instead of reusing the older integration-ledger concept.
        self.assertEqual(object_families.family_for("", "source-integration"), "Source")

    def test_documentation_is_registered_but_not_automatically_retrievable(self):
        self.assertEqual(object_families.family_for("hydra://documentation/wiki", ""), "Documentation")
        self.assertEqual(object_families.family_for("", "documentation-wiki"), "Documentation")
        self.assertEqual(object_families.family_for("", "documentation-page"), "Documentation")
        self.assertFalse(object_families.family_automatically_retrievable("Documentation"))
        self.assertTrue(object_families.family_automatically_retrievable("Knowledge"))

    def test_runtime_module_stays_unregistered(self):
        # Load-bearing: `runtime-module` is this suite's canonical unregistered
        # prefix (see UnregisteredTokenTests below and test_references.py).
        # Runtime/Engine claims `engine-module` precisely so those negative
        # cases keep testing what they were written to test.
        self.assertEqual(object_families.family_for("hydra://runtime-module/x", ""), "Unknown")


class UnregisteredTokenTests(unittest.TestCase):
    def test_a_registered_object_reports_nothing(self):
        self.assertEqual(object_families.unregistered_family_tokens("hydra://source/0001-a", "source"), [])
        self.assertEqual(object_families.unregistered_family_tokens("hydra://capability/skill/x", "skill"), [])

    def test_an_unregistered_prefix_is_reported(self):
        self.assertEqual(
            object_families.unregistered_family_tokens("hydra://runtime-module/x", "source"),
            ["hydra_id family prefix `runtime-module`"],
        )

    def test_an_unregistered_kind_is_reported(self):
        self.assertEqual(
            object_families.unregistered_family_tokens("hydra://source/0001-a", "decisoin"),
            ["kind `decisoin`"],
        )

    def test_both_can_be_reported_at_once(self):
        self.assertEqual(
            object_families.unregistered_family_tokens("hydra://mystery/x", "mystery"),
            ["hydra_id family prefix `mystery`", "kind `mystery`"],
        )

    def test_an_absent_kind_is_not_reported_here(self):
        # It is already a missing mandatory envelope field. Saying it twice
        # pushes a reader toward inventing a value to silence the second one.
        self.assertEqual(object_families.unregistered_family_tokens("hydra://source/0001-a", ""), [])


if __name__ == "__main__":
    unittest.main()
