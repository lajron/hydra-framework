"""Context-provider registry with Knowledge v3 as the Knowledge provider."""

from __future__ import annotations

import dataclasses
from typing import Callable

from hydra_engine.identity.object_families import family_for
from hydra_engine.knowledge.bindings import BindingResolutionError, bound_nodes_for_paths, bindings_root, load_bindings
from hydra_engine.knowledge import context_support
from hydra_engine.knowledge.nodes import discover_knowledge_nodes, resolve_inheritance
from hydra_engine.knowledge.routing import (
    NodeSelection,
    context_terms,
    node_document_path,
    route_expansion_ids,
    route_selector_owner,
    route_nodes,
    routes_for_node,
)
from hydra_engine.knowledge import unit_selection, view_routing

PROVIDER_CANDIDATE_PRIORITY = 30
DEFAULT_FAMILY_CANDIDATE_CAP = 8
PROVIDER_SEARCH_RESULT_LIMIT = 200
KNOWLEDGE_FAMILY = "Knowledge"
SEARCH_FAMILIES = ("Capability", "Work", "Source", "Runtime/Engine", "Telemetry")
NODE_STATE_PRIORITY = 10
NODE_OVERVIEW_PRIORITY = 20


@dataclasses.dataclass(frozen=True)
class ProviderRequest:
    task: str
    paths: "ContextCompilerPaths"
    resolver_paths: "ObjectLocations"
    object_seed_ids: frozenset
    chars_per_token: int
    family_cap: int
    node_values: tuple[str, ...] = ()
    space: str = ""
    search_results: tuple = ()
    route_values: tuple[str, ...] = ()
    path_values: tuple[str, ...] = ()
    view_values: tuple[str, ...] = ()
    command_ids: tuple[str, ...] = ()
    knowledge_snapshot: object | None = None


@dataclasses.dataclass(frozen=True)
class ProviderOutput:
    candidates: list[dict] = dataclasses.field(default_factory=list)
    nodes: list[dict] = dataclasses.field(default_factory=list)
    views: list[str] = dataclasses.field(default_factory=list)
    effective_policy: dict[str, dict] = dataclasses.field(default_factory=dict)
    route_expansions: list[dict] = dataclasses.field(default_factory=list)
    avoid_by_default: list[str] = dataclasses.field(default_factory=list)
    verify: list[str] = dataclasses.field(default_factory=list)
    warnings: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class ContextProvider:
    family: str
    collect: Callable[["ProviderRequest"], ProviderOutput]


def _collect_knowledge(request: ProviderRequest) -> ProviderOutput:
    warnings: list[str] = []
    try:
        snapshot = request.knowledge_snapshot
        if snapshot is None:
            nodes = discover_knowledge_nodes(request.paths)
        else:
            route_owners = tuple(
                value.rpartition(":")[0]
                for value in request.route_values
                if ":" in value and not value.startswith("hydra://")
            )
            nodes = list(snapshot.routing_nodes(request.search_results, (*request.node_values, *route_owners), request.space))
            # Bound paths are explicit authoritative requests.  The compact
            # locator schema intentionally does not duplicate node bindings,
            # so use the one canonical snapshot rather than guessing.
            if snapshot.cached and request.path_values:
                mismatch = __import__("hydra_engine.knowledge.storage", fromlist=("HydrationMismatch",)).HydrationMismatch
                raise mismatch("path routing requires canonical binding snapshot")
    except (OSError, ValueError) as error:
        if error.__class__.__name__ == "HydrationMismatch":
            raise
        return ProviderOutput(warnings=[f"Knowledge v3 discovery failed: {error}"])
    by_node_id = {node.logical_id: node for node in nodes}
    try:
        bindings = snapshot.bindings() if snapshot is not None else (load_bindings(request.paths) if (bindings_root(request.paths) / "manifest.yaml").is_file() else {})
        path_matches = bound_nodes_for_paths(list(request.path_values), nodes, bindings, request.paths) if request.path_values else {}
    except (BindingResolutionError, OSError, ValueError) as error:
        return ProviderOutput(warnings=[f"Knowledge binding error: {error}"])

    selections, route_warnings = route_nodes(
        request.task,
        list(request.node_values),
        request.space,
        request.paths,
        search_results=request.search_results,
        nodes=nodes,
    )
    warnings.extend(route_warnings)
    explicit_routing = bool(request.node_values or request.space)
    if path_matches and not explicit_routing:
        selections = [NodeSelection(by_node_id[node_id], "bound path", float("inf")) for node_id in sorted(set(path_matches.values()))]
    selected_route_owners = {selection.node.logical_id for selection in selections}
    selected_route_ids = {
        route.route_id
        for selection in selections
        for route in resolve_inheritance(selection.node, by_node_id)["routes"].values()
    }
    for value in request.route_values:
        owner = route_selector_owner(value, nodes)
        if not owner:
            warnings.append(f"Route selector must be node-qualified: {value}")
        elif value.lower().startswith("hydra://knowledge-route/"):
            if value.lower() not in selected_route_ids:
                warnings.append(f"Route node not selected: {value}")
        elif owner not in selected_route_owners:
            warnings.append(f"Route node not selected: {value}")

    try:
        cached_views = snapshot.views_for_request(request.search_results, request.view_values) if snapshot is not None else None
        selected_view_ids, composed = view_routing.select_and_compose_views(
            request.task, request.view_values, request.paths, set(path_matches.values()), warnings, views=cached_views,
        )
    except view_routing.ViewConflictError as error:
        return ProviderOutput(warnings=[*warnings, f"Knowledge view error: {error}"])
    view_unit_seeds: set[str] = set()
    if composed is not None:
        selected_by_id = {selection.node.logical_id: selection for selection in selections}
        for ref in composed.includes:
            for prefix in ("hydra://knowledge-node/", "hydra://knowledge-space/"):
                if ref.startswith(prefix):
                    logical = ref.removeprefix(prefix)
                    matches = [node for node in nodes if node.logical_id == logical or node.logical_id.startswith(logical + "/")]
                    if snapshot is not None and not matches:
                        matches = [snapshot.node_for_reference(ref)]
                    for node in matches:
                        selected_by_id[node.logical_id] = NodeSelection(node, f"view {','.join(composed.sources)}", float("inf"))
            if ref.startswith("hydra://knowledge-unit/"):
                view_unit_seeds.add(ref)
        selections = [selected_by_id[key] for key in sorted(selected_by_id)]

    required_seeds = {value.lower() for value in request.object_seed_ids if value.lower().startswith("hydra://knowledge-unit/")}
    required_seeds.update(view_unit_seeds)
    priority_ids: set[str] = set()
    active_routes: dict[str, list] = {}
    route_expansions: list[dict] = []
    avoid_by_default: list[str] = []
    verify_commands: list[str] = []
    effective_policy: dict[str, dict] = {}
    for selection in selections:
        node = selection.node
        effective = resolve_inheritance(node, by_node_id)
        effective_policy[node.logical_id] = {
            "owners": effective["owners"], "defaults": effective["defaults"], "trace": effective["trace"],
        }
        routes = routes_for_node(selection, request.task, list(request.route_values), by_node_id, warnings)
        active_routes[node.logical_id] = routes
        for route in routes:
            priority_ids.update(route.priority_units)
            required_seeds.update(route.requires)
            try:
                expanded, diagnostics = route_expansion_ids(route, list(request.path_values), bindings, request.paths)
            except BindingResolutionError as error:
                return ProviderOutput(warnings=[*warnings, f"Knowledge binding error: {error}"])
            required_seeds.update(expanded)
            route_expansions.extend(diagnostics)
            for value in route.avoid_by_default:
                if value not in avoid_by_default:
                    avoid_by_default.append(value)
            for value in route.verify:
                if value not in verify_commands:
                    verify_commands.append(value)
    units, unit_owners = (
        snapshot.units_for_selection(nodes, request.search_results, required_seeds | priority_ids)
        if snapshot is not None else unit_selection.collect_all_units(nodes, request.paths.root)
    )
    try:
        required_ids, _required_by, selected_ids, superseded = unit_selection.resolve_selected_graph(units, required_seeds, priority_ids)
    except unit_selection.KnowledgeGraphError as error:
        return ProviderOutput(warnings=[*warnings, f"Knowledge graph error: {error}"])

    candidates: list[dict] = []
    seen_candidates: set[str] = set()
    selected_unit_ids: set[str] = set()
    node_rows: list[dict] = []
    for selection in selections:
        node = selection.node
        for raw, kind, priority in ((node.state or "./state.md", "node-state", NODE_STATE_PRIORITY), (node.overview or "./overview.md", "node-overview", NODE_OVERVIEW_PRIORITY)):
            try:
                path = node_document_path(node, raw, request.paths, bindings)
            except BindingResolutionError as error:
                warnings.append(f"Knowledge binding error: {error}")
                continue
            if path.is_file():
                context_support.add_candidate(candidates, seen_candidates, context_support.file_candidate(
                    path, kind=kind, reason=f"{node.logical_id} {selection.reason}", priority=priority,
                    paths=request.paths, source=node.hydra_id, chars_per_token=request.chars_per_token,
                ))
        node_unit_ids = {unit_id for unit_id, owner in unit_owners.items() if owner == node.logical_id}
        chosen: list = []
        if not active_routes[node.logical_id]:
            chosen.extend(unit_selection.search_ranked_units(request, units, unit_owners, node.logical_id, selected_unit_ids))
        for unit in chosen:
            selected_unit_ids.add(unit.hydra_id.lower())
        for candidate in context_support.unit_candidates(
            chosen, package=node.logical_id, paths=request.paths, required_ids=required_ids,
            warnings=warnings, chars_per_token=request.chars_per_token,
        ):
            context_support.add_candidate(candidates, seen_candidates, candidate)
        node_rows.append({
            "node": node.logical_id, "hydra_id": node.hydra_id, "title": node.title,
            "reason": selection.reason, "score": None if selection.score == float("inf") else round(selection.score, 4),
            "routes": [route.name for route in active_routes[node.logical_id]],
        })
    graph_units = [units[unit_id] for unit_id in sorted(selected_ids) if unit_id not in selected_unit_ids]
    for unit in graph_units:
        selected_unit_ids.add(unit.hydra_id.lower())
    for candidate in context_support.unit_candidates(
        graph_units, package="global-knowledge-graph", paths=request.paths, required_ids=required_ids,
        warnings=warnings, chars_per_token=request.chars_per_token,
    ):
            context_support.add_candidate(candidates, seen_candidates, candidate)
    for target, winner in superseded.items():
        warnings.append(f"Knowledge unit superseded: {target} by {winner}")
    return ProviderOutput(
        candidates=candidates, nodes=node_rows, views=sorted(selected_view_ids), effective_policy=effective_policy,
        route_expansions=route_expansions, avoid_by_default=avoid_by_default, verify=verify_commands, warnings=warnings,
    )


def _family_search_collector(family: str):
    def _collect(request: ProviderRequest) -> ProviderOutput:
        candidates: list[dict] = []
        seen_paths: set[str] = set()
        for result in request.search_results:
            doc = result.document
            if not doc.path or doc.path in seen_paths or family_for(doc.hydra_id, doc.kind) != family:
                continue
            path = context_support.resolve_context_path(doc.path, request.paths)
            if not path.exists() or not path.is_file():
                continue
            seen_paths.add(doc.path)
            candidate = context_support.file_candidate(
                path, kind=f"context-provider-{view_routing.normalized_token(family)}",
                reason=f"{family} context provider match" + (f" for {request.task!r}" if request.task else ""),
                priority=PROVIDER_CANDIDATE_PRIORITY, paths=request.paths, source=doc.hydra_id,
                chars_per_token=request.chars_per_token,
            )
            candidate["rank"] = result.rank
            candidates.append(candidate)
            if request.family_cap >= 0 and len(candidates) >= request.family_cap:
                break
        return ProviderOutput(candidates=candidates)
    return _collect


CONTEXT_PROVIDERS: tuple[ContextProvider, ...] = (
    ContextProvider(KNOWLEDGE_FAMILY, _collect_knowledge),
    *(ContextProvider(family, _family_search_collector(family)) for family in SEARCH_FAMILIES),
)
PROVIDERS_BY_FAMILY = {provider.family: provider for provider in CONTEXT_PROVIDERS}


def _matched_families(values: tuple[str, ...]) -> tuple[set[str], list[str]]:
    matched: set[str] = set()
    unknown: list[str] = []
    for value in values:
        hit = next((family for family in PROVIDERS_BY_FAMILY if view_routing.normalized_token(value) == view_routing.normalized_token(family)), None)
        if hit:
            matched.add(hit)
        else:
            unknown.append(value)
    return matched, unknown


def run_context_providers(
    request: ProviderRequest, *, include_families: tuple[str, ...] = (), exclude_families: tuple[str, ...] = (),
) -> ProviderOutput:
    warnings: list[str] = []
    included, unknown_included = _matched_families(include_families)
    excluded, unknown_excluded = _matched_families(exclude_families)
    warnings.extend(f"Unknown context-provider family: {value}" for value in [*unknown_included, *unknown_excluded])
    active = [
        family for family in PROVIDERS_BY_FAMILY
        if (family in included if include_families else True) and family not in excluded
    ]
    if active and request.knowledge_snapshot is None:
        results, _features, _source = context_support.search(
            request.task, paths=request.paths, resolver_paths=request.resolver_paths,
            local=request.resolver_paths.local, command_ids=request.command_ids,
            path_refs=request.path_values, limit=PROVIDER_SEARCH_RESULT_LIMIT,
        )
        from hydra_engine.knowledge.search_index import default_db_path
        open_knowledge_snapshot = __import__("hydra_engine.knowledge.snapshot", fromlist=("open_knowledge_snapshot",)).open_knowledge_snapshot
        try:
            snapshot = open_knowledge_snapshot(request.paths, default_db_path(request.resolver_paths.local), _source)
        except ValueError as error:
            if error.__class__.__name__ != "HydrationMismatch":
                raise
            results, _features, _source = context_support.search(
                request.task, paths=request.paths, resolver_paths=request.resolver_paths,
                local=request.resolver_paths.local, command_ids=request.command_ids,
                path_refs=request.path_values, limit=PROVIDER_SEARCH_RESULT_LIMIT, force_source=True,
            )
            snapshot = open_knowledge_snapshot(request.paths, default_db_path(request.resolver_paths.local), _source)
        request = dataclasses.replace(request, search_results=tuple(results), knowledge_snapshot=snapshot)

    candidates: list[dict] = []
    seen: set[str] = set()
    nodes: list[dict] = []
    views: list[str] = []
    policies: dict[str, dict] = {}
    expansions: list[dict] = []
    avoid: list[str] = []
    verify: list[str] = []
    for family in active:
        try:
            output = PROVIDERS_BY_FAMILY[family].collect(request)
        except HydrationMismatch:
            # Never combine a partially hydrated cache graph with source
            # values.  Re-run the complete provider operation from one
            # canonical snapshot, including shared search candidates.
            from hydra_engine.knowledge.search_index import search
            results, _features, _source = search(
                request.task, paths=request.paths, resolver_paths=request.resolver_paths,
                local=request.resolver_paths.local, command_ids=request.command_ids,
                path_refs=request.path_values, limit=PROVIDER_SEARCH_RESULT_LIMIT, force_source=True,
            )
            from hydra_engine.knowledge.search_index import default_db_path
            open_knowledge_snapshot = __import__("hydra_engine.knowledge.snapshot", fromlist=("open_knowledge_snapshot",)).open_knowledge_snapshot
            source_request = dataclasses.replace(
                request, search_results=tuple(results),
                knowledge_snapshot=open_knowledge_snapshot(request.paths, default_db_path(request.resolver_paths.local), "source"),
            )
            return run_context_providers(source_request, include_families=include_families, exclude_families=exclude_families)
        for candidate in output.candidates:
            context_support.add_candidate(candidates, seen, candidate)
        nodes.extend(output.nodes)
        views.extend(value for value in output.views if value not in views)
        policies.update(output.effective_policy)
        expansions.extend(output.route_expansions)
        for value in output.avoid_by_default:
            if value not in avoid:
                avoid.append(value)
        for value in output.verify:
            if value not in verify:
                verify.append(value)
        warnings.extend(output.warnings)
    return ProviderOutput(
        candidates=candidates, nodes=nodes, views=views, effective_policy=policies,
        route_expansions=expansions, avoid_by_default=avoid, verify=verify, warnings=warnings,
    )
