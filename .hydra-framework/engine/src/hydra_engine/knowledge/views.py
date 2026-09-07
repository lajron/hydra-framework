"""Reference-only Knowledge v3 views and partial-order composition."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from hydra_engine.documents.tokens import HydraYamlError, display_path
from hydra_engine.documents.frontmatter_blocks import parse_yaml, yaml_list, yaml_map, yaml_str
from hydra_engine.finding import Finding
from hydra_engine.identity.hydra_ids import HYDRA_ID_RE
from hydra_engine.knowledge.nodes import knowledge_root
from hydra_engine.knowledge.packages import ContextCompilerPaths

VIEW_SCHEMA = "hydra-framework.knowledge-view.v1"
VIEW_KEYS = frozenset({
    "schema", "view", "hydra_id", "uid", "schema_version", "kind", "title", "status", "scope",
    "owners", "reviewers", "relations", "provenance", "constraints", "include", "dynamic_include",
    "routes", "resolve",
})


class ViewConflictError(ValueError):
    pass


@dataclasses.dataclass(frozen=True)
class ViewRoute:
    name: str
    intent: str
    use_when: tuple[str, ...]
    order: tuple[str, ...]
    budget_hint: int


@dataclasses.dataclass(frozen=True)
class KnowledgeView:
    path: Path
    view_id: str
    hydra_id: str
    uid: str
    title: str
    owner: str
    reviewers: tuple[str, ...]
    include: tuple[str, ...]
    dynamic_bound_paths: bool
    routes: tuple[ViewRoute, ...]
    resolutions: dict[str, str]
    raw_keys: frozenset[str]
    reference_only: bool


@dataclasses.dataclass(frozen=True)
class ComposedView:
    includes: tuple[str, ...]
    order: tuple[str, ...]
    resolutions: dict[str, str]
    sources: tuple[str, ...]


def views_root(paths: ContextCompilerPaths) -> Path:
    return knowledge_root(paths) / "views"


def read_view(path: Path, paths: ContextCompilerPaths) -> KnowledgeView:
    data = parse_yaml(path, paths.root, required=True)
    view_id = yaml_str(data.get("view"))
    routes: list[ViewRoute] = []
    for name, raw in sorted(yaml_map(data.get("routes")).items()):
        route = yaml_map(raw)
        budget = route.get("budget_hint")
        routes.append(ViewRoute(
            name=name,
            intent=yaml_str(route.get("intent")).lower(),
            use_when=tuple(yaml_list(route.get("use_when"))),
            order=tuple(yaml_list(route.get("order"))),
            budget_hint=int(budget) if str(budget).isdigit() else 0,
        ))
    constraints = yaml_map(data.get("constraints"))
    dynamic = yaml_map(data.get("dynamic_include"))
    owners = yaml_map(data.get("owners"))
    return KnowledgeView(
        path=path,
        view_id=view_id,
        hydra_id=yaml_str(data.get("hydra_id")).lower(),
        uid=yaml_str(data.get("uid")),
        title=yaml_str(data.get("title")),
        owner=yaml_str(owners.get("team")),
        reviewers=tuple(yaml_list(data.get("reviewers"))),
        include=tuple(value.lower() for value in yaml_list(data.get("include"))),
        dynamic_bound_paths=dynamic.get("from_bound_paths") is True or yaml_str(dynamic.get("from_bound_paths")).lower() == "true",
        routes=tuple(routes),
        resolutions={str(key).lower(): yaml_str(value).lower() for key, value in yaml_map(data.get("resolve")).items()},
        raw_keys=frozenset(data),
        reference_only=constraints.get("reference_only") is True or yaml_str(constraints.get("reference_only")).lower() == "true",
    )


def discover_views(paths: ContextCompilerPaths) -> list[KnowledgeView]:
    root = views_root(paths)
    if not root.is_dir():
        return []
    return [read_view(path, paths) for path in sorted(root.glob("*.view.yaml"))]


def _view_refs(view: KnowledgeView) -> list[str]:
    return [value for value in view.include if value.startswith("hydra://knowledge-view/")]


def _check_view_cycles(views: dict[str, KnowledgeView]) -> None:
    def visit(view_id: str, stack: tuple[str, ...], done: set[str]) -> None:
        if view_id in stack:
            raise ViewConflictError(f"view cycle detected: {' -> '.join((*stack, view_id))}")
        if view_id in done:
            return
        view = views.get(view_id)
        if view is None:
            raise ViewConflictError(f"unresolved view reference `{view_id}`")
        for target in _view_refs(view):
            visit(target, (*stack, view_id), done)
        done.add(view_id)

    done: set[str] = set()
    for view_id in sorted(views):
        visit(view_id, (), done)


def _topological_order(edges: set[tuple[str, str]]) -> tuple[str, ...]:
    nodes = {value for edge in edges for value in edge}
    incoming = {node: set() for node in nodes}
    outgoing = {node: set() for node in nodes}
    for before, after in edges:
        outgoing[before].add(after)
        incoming[after].add(before)
    ordered: list[str] = []
    ready = sorted(node for node in nodes if not incoming[node])
    while ready:
        node = ready.pop(0)
        ordered.append(node)
        for target in sorted(outgoing[node]):
            incoming[target].discard(node)
            if not incoming[target] and target not in ordered and target not in ready:
                ready.append(target)
                ready.sort()
    if len(ordered) != len(nodes):
        cycle_nodes = sorted(node for node in nodes if incoming[node])
        raise ViewConflictError(f"view ordering cycle: {', '.join(cycle_nodes)}")
    return tuple(ordered)


def compose_views(
    selected_view_ids: set[str], views: dict[str, KnowledgeView], *, bound_node_ids: set[str] | None = None,
) -> ComposedView:
    _check_view_cycles(views)
    includes: list[str] = []
    sources: list[str] = []
    edges: set[tuple[str, str]] = set()
    resolutions: dict[str, str] = {}
    visited: set[str] = set()

    def add(view_id: str) -> None:
        if view_id in visited:
            return
        view = views.get(view_id)
        if view is None:
            raise ViewConflictError(f"selected view does not resolve: {view_id}")
        visited.add(view_id)
        sources.append(view_id)
        for value in view.include:
            if value.startswith("hydra://knowledge-view/"):
                add(value)
            elif value not in includes:
                includes.append(value)
        if view.dynamic_bound_paths:
            for node_id in sorted(bound_node_ids or set()):
                ref = f"hydra://knowledge-node/{node_id}"
                if ref not in includes:
                    includes.append(ref)
        for route in view.routes:
            edges.update(zip(route.order, route.order[1:]))
        for target, winner in view.resolutions.items():
            existing = resolutions.get(target)
            if existing and existing != winner:
                raise ViewConflictError(f"conflicting view resolutions for `{target}`: `{existing}` versus `{winner}`")
            resolutions[target] = winner

    for view_id in sorted(selected_view_ids):
        add(view_id)
    return ComposedView(tuple(includes), _topological_order(edges), resolutions, tuple(sources))


def validate_views(paths: ContextCompilerPaths, known_ids: set[str]) -> list[Finding]:
    code = "knowledge-v3-view"
    findings: list[Finding] = []
    views: list[KnowledgeView] = []
    for path in sorted(views_root(paths).glob("*.view.yaml")) if views_root(paths).is_dir() else []:
        try:
            views.append(read_view(path, paths))
        except HydraYamlError as error:
            findings.append(Finding(path=display_path(path, paths.root), code=code, detail=str(error)))
    by_id = {view.hydra_id: view for view in views}
    for view in views:
        rel = display_path(view.path, paths.root)
        expected_id = f"hydra://knowledge-view/{view.view_id}"
        if view.hydra_id != expected_id or not HYDRA_ID_RE.match(view.hydra_id):
            findings.append(Finding(path=rel, code=code, detail=f"view identity must be `{expected_id}`"))
        if not view.reference_only:
            findings.append(Finding(path=rel, code=code, detail="view requires constraints.reference_only: true"))
        for key in sorted(view.raw_keys - VIEW_KEYS):
            findings.append(Finding(path=rel, code=code, detail=f"reference-only view contains forbidden field `{key}`"))
        if not view.owner or not view.reviewers:
            findings.append(Finding(path=rel, code=code, detail="view requires owner and reviewers"))
        for ref in view.include:
            if ref not in known_ids and ref not in by_id:
                findings.append(Finding(path=rel, code=code, detail=f"view include does not resolve: {ref}"))
        for route in view.routes:
            expected_intent = f"hydra://knowledge-view-route/{view.view_id}/{route.name.replace('_', '-')}"
            if route.intent != expected_intent:
                findings.append(Finding(path=rel, code=code, detail=f"view route `{route.name}` intent must be `{expected_intent}`"))
            if not route.use_when:
                findings.append(Finding(path=rel, code=code, detail=f"view route `{route.name}` requires use_when"))
    try:
        _check_view_cycles(by_id)
        compose_views(set(by_id), by_id)
    except ViewConflictError as error:
        findings.append(Finding(path=display_path(views_root(paths), paths.root), code=code, detail=str(error)))
    return findings
