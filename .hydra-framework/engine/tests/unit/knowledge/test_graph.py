from __future__ import annotations

import unittest
from pathlib import Path

from hydra_engine.knowledge.graph import KnowledgeGraphError, global_required_closure, resolve_graph, resolve_supersession
from hydra_engine.knowledge.units import Unit


def _unit(hydra_id: str, *, requires: tuple[str, ...] = (), relations: tuple[tuple[str, str], ...] = ()) -> Unit:
    return Unit(
        path=Path(hydra_id.rsplit("/", 1)[-1] + ".md"), hydra_id=hydra_id,
        unit_kind="answer", title=hydra_id, question="Question?", group="",
        certainty="confirmed", checked_on="", reads=(), requires=requires,
        see_also=(), verify=(), expand_when=(), sources=(), relations=relations,
    )


class GlobalKnowledgeGraphTests(unittest.TestCase):
    def test_cross_space_closure_and_diamond_are_complete(self):
        product = "hydra://knowledge-unit/product/checkout/idempotency"
        platform = "hydra://knowledge-unit/platform/data/migrations"
        security = "hydra://knowledge-unit/security/compliance/pci"
        shared = "hydra://knowledge-unit/platform/data/money-safety"
        units = {
            product: _unit(product, requires=(platform, security)),
            platform: _unit(platform, requires=(shared,)),
            security: _unit(security, requires=(shared,)),
            shared: _unit(shared),
        }
        closure, required_by = global_required_closure(units, {product})
        self.assertEqual(closure, set(units))
        self.assertEqual(required_by[shared], (platform, security))

    def test_unresolved_dependency_fails_closed(self):
        source = "hydra://knowledge-unit/product/a"
        units = {source: _unit(source, requires=("hydra://knowledge-unit/platform/missing",))}
        with self.assertRaisesRegex(KnowledgeGraphError, "unresolved required unit"):
            global_required_closure(units, {source})

    def test_cycle_reports_full_path(self):
        first = "hydra://knowledge-unit/product/a"
        second = "hydra://knowledge-unit/platform/b"
        units = {first: _unit(first, requires=(second,)), second: _unit(second, requires=(first,))}
        with self.assertRaisesRegex(KnowledgeGraphError, f"{first} -> {second} -> {first}"):
            global_required_closure(units, {first})

    def test_conflicting_sibling_superseders_fail(self):
        base = "hydra://knowledge-unit/qa/shared/device-matrix"
        titan = "hydra://knowledge-unit/qa/titan/device-matrix"
        nimbus = "hydra://knowledge-unit/qa/nimbus/device-matrix"
        units = {
            base: _unit(base),
            titan: _unit(titan, relations=(("supersedes", base),)),
            nimbus: _unit(nimbus, relations=(("supersedes", base),)),
        }
        with self.assertRaisesRegex(KnowledgeGraphError, "supersession conflict"):
            resolve_supersession(units, set(units))

    def test_one_superseder_deterministically_removes_target(self):
        base = "hydra://knowledge-unit/qa/shared/device-matrix"
        titan = "hydra://knowledge-unit/qa/titan/device-matrix"
        units = {base: _unit(base), titan: _unit(titan, relations=(("supersedes", base),))}
        resolved = resolve_graph(units, {base, titan})
        self.assertEqual(resolved.selected_ids, (titan,))
        self.assertEqual(resolved.superseded, {base: titan})


if __name__ == "__main__":
    unittest.main()
