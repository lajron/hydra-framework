"""Knowledge v3 global node routing and route-level conditional expansion."""

from __future__ import annotations

import dataclasses
import fnmatch
import re
from pathlib import Path

from hydra_engine.documents.tokens import HydraYamlError, display_path
from hydra_engine.identity.slugs import slugify
from hydra_engine.knowledge.bindings import Binding, BindingResolutionError, resolve_binding
from hydra_engine.knowledge.nodes import (
    KnowledgeNode,
    Route,
    discover_knowledge_nodes,
    discover_node_unit_paths,
    knowledge_node_for_path,
    node_roots_by_path,
    node_root,
    resolve_inheritance,
)
from hydra_engine.knowledge.units import read_unit

MIN_CONTEXT_TERM_LENGTH = 2
MIN_PLURAL_STEM_LENGTH = 3
MIN_ROUTE_MATCH_SCORE = 2
MAX_ROUTED_NODES = 2

STOPWORDS = frozenset({
    "the", "and", "for", "are", "was", "were", "with", "that", "this", "from",
    "have", "has", "had", "not", "but", "you", "your", "can", "will", "would",
    "should", "into", "about", "just", "then", "than", "also", "such", "some",
    "any", "all", "each", "more", "most", "other", "only", "own", "same",
    "too", "very", "use", "used", "using", "its", "our", "who", "what",
    "when", "where", "why", "how", "which", "there", "here", "been", "being",
    "does", "did", "doing", "yet", "get", "got", "one", "two",
})


@dataclasses.dataclass(frozen=True)
class NodeSelection:
    node: KnowledgeNode
    reason: str
    score: float


@dataclasses.dataclass(frozen=True)
class RoutePromptPointer:
    node_id: str
    title: str
    state: str
    overview: str
    note: str
    route: str = ""
    priority_units: tuple[tuple[str, str], ...] = ()
    requires: tuple[tuple[str, str], ...] = ()
    avoid_by_default: tuple[str, ...] = ()


def context_terms(text: str) -> set[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    terms: set[str] = set()
    for term in re.findall(r"[a-z0-9]+", expanded.lower()):
        if len(term) <= MIN_CONTEXT_TERM_LENGTH or term in STOPWORDS:
            continue
        terms.add(term)
        if term.endswith("s") and len(term) > MIN_PLURAL_STEM_LENGTH:
            terms.add(term[:-1])
    return terms


def node_keyword_score(node: KnowledgeNode, task_terms: frozenset[str]) -> float:
    corpus = context_terms(" ".join((node.logical_id, node.title, *node.keywords)))
    for route in node.routes:
        corpus.update(context_terms(" ".join((route.name, *route.use_when))))
    if not corpus or not task_terms:
        return 0.0
    overlap = corpus & task_terms
    phrase_terms = context_terms(node.logical_id.rsplit("/", 1)[-1].replace("-", " "))
    phrase_bonus = 2.0 if phrase_terms and phrase_terms <= task_terms else 0.0
    return phrase_bonus + len(overlap) + len(overlap) / max(len(corpus), 1)


def _match_explicit(value: str, nodes: list[KnowledgeNode]) -> list[KnowledgeNode]:
    lowered = value.lower().removeprefix("hydra://knowledge-node/").removeprefix("hydra://knowledge-space/")
    slug = slugify(lowered)
    exact = [node for node in nodes if lowered in {node.logical_id, node.hydra_id}]
    if exact:
        return exact
    return [node for node in nodes if slugify(node.logical_id.rsplit("/", 1)[-1]) == slug]


def _rank_and_cap(scored: list[tuple[float, KnowledgeNode]], cap: int) -> tuple[list[NodeSelection], list[str]]:
    ordered = sorted(scored, key=lambda item: (-item[0], item[1].logical_id))
    if len(ordered) <= cap:
        return [NodeSelection(node, "global index", score) for score, node in ordered], []
    boundary = ordered[cap - 1][0]
    if ordered[cap][0] == boundary:
        tied = [node.logical_id for score, node in ordered if score == boundary]
        kept = [NodeSelection(node, "global index", score) for score, node in ordered if score > boundary]
        return kept, [f"Node selection is ambiguous at the top-{cap} cutoff: {', '.join(tied)}; narrow with --node or --space."]
    return [NodeSelection(node, "global index", score) for score, node in ordered[:cap]], []


def route_nodes(
    task: str,
    node_values: list[str],
    space: str,
    paths,
    *,
    search_results: tuple = (),
    max_routed_nodes: int = MAX_ROUTED_NODES,
) -> tuple[list[NodeSelection], list[str]]:
    nodes = discover_knowledge_nodes(paths)
    warnings: list[str] = []
    selected: dict[str, NodeSelection] = {}
    for value in node_values:
        matches = _match_explicit(value, nodes)
        if len(matches) == 1:
            selected[matches[0].logical_id] = NodeSelection(matches[0], "explicit node", float("inf"))
        elif len(matches) > 1:
            warnings.append(f"Node selector is ambiguous: {value}: {', '.join(node.logical_id for node in matches)}")
        else:
            warnings.append(f"Node not found: {value}")
    if space:
        matches = [node for node in nodes if node.logical_id == slugify(space)]
        if matches:
            selected[matches[0].logical_id] = NodeSelection(matches[0], "explicit space", float("inf"))
        else:
            warnings.append(f"Space not found: {space}")
    if selected or node_values or space:
        return [selected[key] for key in sorted(selected)], warnings

    task_terms = frozenset(context_terms(task))
    scores = {node.logical_id: node_keyword_score(node, task_terms) for node in nodes if node.routable}
    node_roots = node_roots_by_path(nodes) if search_results else {}
    for position, result in enumerate(search_results):
        document = result.document
        if not document.path:
            continue
        node = knowledge_node_for_path(Path(document.path), nodes, paths, node_roots)
        if node is None or not node.routable:
            continue
        scores[node.logical_id] = scores.get(node.logical_id, 0.0) + 1.0 / (position + 1)
    positive = [(score, node) for node in nodes if node.routable and (score := scores.get(node.logical_id, 0.0)) > 0]
    if not positive and len([node for node in nodes if node.routable]) == 1:
        node = next(node for node in nodes if node.routable)
        return [NodeSelection(node, "only routable knowledge node", 0.0)], warnings
    ranked, rank_warnings = _rank_and_cap(positive, max_routed_nodes)
    return ranked, warnings + rank_warnings


def select_route(routes: dict[str, Route], task: str) -> Route | None:
    task_terms = context_terms(task)
    scored = [
        (len(task_terms & context_terms(" ".join((route.name, *route.use_when)))), name, route)
        for name, route in routes.items()
    ]
    if not scored:
        return None
    score, _name, route = max(scored, key=lambda item: (item[0], item[1]))
    return route if score >= MIN_ROUTE_MATCH_SCORE else None


def resolve_named_route(routes: dict[str, Route], name: str) -> Route | None:
    return routes.get(name)


def route_selector_owner(value: str, nodes: list[KnowledgeNode]) -> str:
    """Return the owning logical node for canonical or deprecated selectors."""
    lowered = value.lower()
    if lowered.startswith("hydra://knowledge-route/"):
        return next(
            (
                node.logical_id
                for node in sorted(nodes, key=lambda item: len(item.logical_id), reverse=True)
                if lowered.startswith(f"hydra://knowledge-route/{node.logical_id}/")
            ),
            "",
        )
    owner, separator, _name = lowered.rpartition(":")
    return owner if separator else ""


def routes_for_node(
    selection: NodeSelection, task: str, route_values: list[str], nodes_by_id: dict[str, KnowledgeNode], warnings: list[str],
) -> list[Route]:
    effective = resolve_inheritance(selection.node, nodes_by_id)
    routes = effective["routes"]
    requested: list[str] = []
    for value in route_values:
        lowered = value.lower()
        canonical = next((route for route in routes.values() if route.route_id == lowered), None)
        if canonical is not None:
            requested.append(canonical.name)
            continue
        owner, separator, name = lowered.rpartition(":")
        if separator and owner in {selection.node.logical_id, selection.node.hydra_id}:
            requested.append(name)
    if requested:
        resolved: list[Route] = []
        for name in requested:
            route = resolve_named_route(routes, name)
            if route is None:
                warnings.append(f"Route not found in node {selection.node.logical_id}: {name}")
            else:
                resolved.append(route)
        return resolved
    route = select_route(routes, task)
    return [route] if route is not None else []


def _resolved_pattern(raw: str, bindings: dict[str, Binding], paths) -> str:
    if not raw.startswith("@"):
        return (paths.root / raw).resolve().as_posix()
    names = [name for name in bindings if raw == name or raw.startswith(name + "/")]
    if not names:
        raise BindingResolutionError(f"unresolved logical binding pattern `{raw}`")
    logical = max(names, key=len)
    target = resolve_binding(logical, bindings, paths)
    suffix = raw[len(logical):].lstrip("/")
    return (target / suffix).as_posix()


def route_expansion_ids(route: Route, path_values: list[str], bindings: dict[str, Binding], paths) -> tuple[set[str], list[dict]]:
    selected: set[str] = set()
    diagnostics: list[dict] = []
    resolved_paths = [
        (Path(value).resolve() if Path(value).is_absolute() else (paths.root / value).resolve()).as_posix()
        for value in path_values
    ]
    for expansion in route.expand_when:
        patterns = [_resolved_pattern(raw, bindings, paths) for raw in expansion.when_paths]
        matches = sorted(path for path in resolved_paths if any(fnmatch.fnmatch(path, pattern) for pattern in patterns))
        if not matches:
            continue
        selected.update(expansion.read)
        diagnostics.append({"route": route.route_id, "why": expansion.why, "paths": matches, "read": list(expansion.read)})
    return selected, diagnostics


def node_document_path(node: KnowledgeNode, raw: str, paths, bindings: dict[str, Binding]) -> Path:
    value = raw
    if value.startswith("@"):
        return resolve_binding(value, bindings, paths)
    return node_root(node) / value.removeprefix("./")


def route_prompt_node_pointers(
    prompt: str,
    paths,
    *,
    search_results: tuple = (),
    node_values: tuple[str, ...] = (),
    max_routed_nodes: int = MAX_ROUTED_NODES,
    bindings: dict[str, Binding] | None = None,
) -> tuple[list[RoutePromptPointer], list[str]]:
    try:
        selections, warnings = route_nodes(
            prompt, list(node_values), "", paths, search_results=search_results, max_routed_nodes=max_routed_nodes,
        )
    except HydraYamlError as error:
        return [], [f"Knowledge v3 routing unavailable: {error}"]
    loaded_bindings = bindings or {}
    nodes = discover_knowledge_nodes(paths)
    by_id = {node.logical_id: node for node in nodes}
    pointers: list[RoutePromptPointer] = []
    for selection in selections:
        node = selection.node
        route = select_route(resolve_inheritance(node, by_id)["routes"], prompt)
        units = {
            unit.hydra_id: unit
            for path in discover_node_unit_paths(node)
            if (unit := read_unit(path, paths.root)) is not None
        }

        def labels(values: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
            return tuple((value, units[value].question if value in units else "") for value in values)

        pointers.append(RoutePromptPointer(
            node_id=node.logical_id,
            title=node.title,
            state=display_path(node_document_path(node, node.state or "./state.md", paths, loaded_bindings), paths.root),
            overview=display_path(node_document_path(node, node.overview or "./overview.md", paths, loaded_bindings), paths.root),
            note="This node owns the relevant accountability boundary. Read the route, not the tree.",
            route=route.name if route else "",
            priority_units=labels(route.priority_units) if route else (),
            requires=labels(route.requires) if route else (),
            avoid_by_default=route.avoid_by_default if route else (),
        ))
    return pointers, warnings
