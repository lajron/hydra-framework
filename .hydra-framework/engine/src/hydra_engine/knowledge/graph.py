"""Knowledge v3 global dependency and supersession resolution."""

from __future__ import annotations

import dataclasses

from hydra_engine.knowledge.units import Unit


class KnowledgeGraphError(ValueError):
    pass


@dataclasses.dataclass(frozen=True)
class GraphResolution:
    selected_ids: tuple[str, ...]
    required_by: dict[str, tuple[str, ...]]
    superseded: dict[str, str]


def global_required_closure(units: dict[str, Unit], seed_ids: set[str]) -> tuple[set[str], dict[str, tuple[str, ...]]]:
    """Resolve strict global requires closure with deterministic diagnostics."""
    normalized = {key.lower(): value for key, value in units.items()}
    closure: set[str] = set()
    required_by: dict[str, list[str]] = {}

    def visit(node_id: str, stack: tuple[str, ...]) -> None:
        node_id = node_id.lower()
        if node_id in stack:
            raise KnowledgeGraphError(f"requires cycle detected: {' -> '.join((*stack, node_id))}")
        unit = normalized.get(node_id)
        if unit is None:
            source = stack[-1] if stack else "selection"
            raise KnowledgeGraphError(f"unresolved required unit `{node_id}` from `{source}`")
        if node_id in closure:
            return
        closure.add(node_id)
        for target in sorted(value.lower() for value in unit.requires):
            required_by.setdefault(target, []).append(node_id)
            visit(target, (*stack, node_id))

    for seed in sorted(value.lower() for value in seed_ids):
        visit(seed, ())
    return closure, {key: tuple(sorted(set(values))) for key, values in sorted(required_by.items())}


def resolve_supersession(units: dict[str, Unit], selected_ids: set[str]) -> tuple[set[str], dict[str, str]]:
    normalized = {key.lower(): value for key, value in units.items()}
    selected = {value.lower() for value in selected_ids}
    claims: dict[str, list[str]] = {}
    for unit_id in sorted(selected):
        unit = normalized.get(unit_id)
        if unit is None:
            raise KnowledgeGraphError(f"selected unit does not resolve: {unit_id}")
        for relation_type, target in unit.relations:
            if relation_type == "supersedes" and target.lower() in selected:
                claims.setdefault(target.lower(), []).append(unit_id)
    for target, superseders in sorted(claims.items()):
        if len(superseders) > 1:
            raise KnowledgeGraphError(
                f"supersession conflict for `{target}`: {', '.join(sorted(superseders))}; explicit view resolution required"
            )
    superseded = {target: values[0] for target, values in claims.items()}
    return selected - set(superseded), superseded


def resolve_graph(units: dict[str, Unit], seed_ids: set[str]) -> GraphResolution:
    closure, required_by = global_required_closure(units, seed_ids)
    active, superseded = resolve_supersession(units, closure)
    return GraphResolution(tuple(sorted(active)), required_by, superseded)
