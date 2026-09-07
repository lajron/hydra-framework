"""Global Knowledge-unit collection and graph selection."""

from __future__ import annotations

from hydra_engine.documents.tokens import display_path
from hydra_engine.knowledge.graph import KnowledgeGraphError, global_required_closure, resolve_supersession
from hydra_engine.knowledge.nodes import discover_node_unit_paths
from hydra_engine.knowledge.units import read_unit


def collect_all_units(nodes, root) -> tuple[dict, dict[str, str]]:
    units: dict = {}
    owners: dict[str, str] = {}
    for node in nodes:
        for path in discover_node_unit_paths(node):
            unit = read_unit(path, root)
            if unit is None or not unit.hydra_id:
                continue
            unit_id = unit.hydra_id.lower()
            units[unit_id] = unit
            owners[unit_id] = node.logical_id
    return units, owners


def search_ranked_units(request, units: dict, unit_owners: dict[str, str], node_id: str, seen: set[str]) -> list:
    by_path = {display_path(unit.path, request.paths.root): unit for unit in units.values()}
    selected: list = []
    for result in request.search_results:
        document = result.document
        unit = units.get(document.hydra_id.lower()) if document.hydra_id else by_path.get(document.path)
        if unit is None or unit_owners.get(unit.hydra_id.lower()) != node_id or unit.hydra_id.lower() in seen:
            continue
        selected.append(unit)
        seen.add(unit.hydra_id.lower())
        if request.family_cap >= 0 and len(selected) >= request.family_cap:
            break
    return selected


def resolve_selected_graph(units: dict, required_seeds: set[str], priority_ids: set[str]):
    required_ids, required_by = global_required_closure(units, required_seeds) if required_seeds else (set(), {})
    priority_closure, _priority_by = global_required_closure(units, priority_ids) if priority_ids else (set(), {})
    required_ids.update(priority_closure - priority_ids)
    selected_ids, superseded = resolve_supersession(units, required_ids | priority_ids)
    return required_ids, required_by, selected_ids, superseded


__all__ = ("KnowledgeGraphError", "collect_all_units", "resolve_selected_graph", "search_ranked_units")
