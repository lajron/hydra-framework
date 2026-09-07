"""Knowledge v3 recursive accountability-node model and inheritance."""

from __future__ import annotations

import dataclasses
from pathlib import Path

from hydra_engine.documents.tokens import HydraYamlError, display_path
from hydra_engine.documents.frontmatter_blocks import parse_yaml, yaml_int, yaml_list, yaml_map, yaml_str
from hydra_engine.finding import Finding
from hydra_engine.identity.hydra_ids import HYDRA_ID_RE
from hydra_engine.knowledge.contracts import DEFAULT_DEPTH, LEGAL_SCOPES, MAX_DEPTH, RELATION_TYPES
from hydra_engine.knowledge.packages import ContextCompilerPaths

SPACES_SCHEMA = "hydra-framework.knowledge-spaces.v1"
NODE_SCHEMA = "hydra-framework.knowledge-node.v1"


@dataclasses.dataclass(frozen=True)
class Relation:
    relation_type: str
    target: str


@dataclasses.dataclass(frozen=True)
class RouteExpansion:
    when_paths: tuple[str, ...]
    read: tuple[str, ...]
    why: str


@dataclasses.dataclass(frozen=True)
class Route:
    name: str
    route_id: str
    use_when: tuple[str, ...]
    priority_units: tuple[str, ...]
    requires: tuple[str, ...]
    avoid_by_default: tuple[str, ...]
    verify: tuple[str, ...]
    expand_when: tuple[RouteExpansion, ...]
    overrides: str = ""


@dataclasses.dataclass(frozen=True)
class KnowledgeNode:
    path: Path
    logical_id: str
    hydra_id: str
    uid: str
    kind: str
    title: str
    status: str
    scope: str
    owners: dict
    relations: tuple[Relation, ...]
    provenance: dict
    role: str
    routable: bool
    state: str
    overview: str
    binding: str
    keywords: tuple[str, ...]
    defaults: dict
    routes: tuple[Route, ...]
    parent_id: str
    depth: int


@dataclasses.dataclass(frozen=True)
class SpacesConfig:
    path: Path
    spaces: tuple[str, ...]
    default_depth: int = DEFAULT_DEPTH
    max_depth: int = MAX_DEPTH


def knowledge_root(paths: ContextCompilerPaths) -> Path:
    return paths.hydra / "repo/knowledge"


def spaces_root(paths: ContextCompilerPaths) -> Path:
    return knowledge_root(paths) / "spaces"


def load_spaces_config(paths: ContextCompilerPaths) -> SpacesConfig:
    path = knowledge_root(paths) / "spaces.yaml"
    data = parse_yaml(path, paths.root, required=True)
    if yaml_str(data.get("schema")) != SPACES_SCHEMA:
        raise HydraYamlError(f"{display_path(path, paths.root)} schema must be `{SPACES_SCHEMA}`")
    return SpacesConfig(
        path=path,
        spaces=tuple(yaml_list(data.get("spaces"))),
        default_depth=yaml_int(data.get("default_depth"), DEFAULT_DEPTH),
        max_depth=yaml_int(data.get("max_depth"), MAX_DEPTH),
    )


def _mapping_list(value: object) -> list[dict]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _read_relations(data: dict) -> tuple[Relation, ...]:
    return tuple(
        Relation(yaml_str(item.get("type")), yaml_str(item.get("target")).lower())
        for item in _mapping_list(data.get("relations"))
    )


def _route_id(logical_id: str, name: str) -> str:
    return f"hydra://knowledge-route/{logical_id}/{name.replace('_', '-')}"


def _read_routes(data: dict, logical_id: str) -> tuple[Route, ...]:
    result: list[Route] = []
    for name, raw in sorted(yaml_map(data.get("routes")).items()):
        route = yaml_map(raw)
        expansions = tuple(
            RouteExpansion(
                when_paths=tuple(yaml_list(item.get("when_paths"))),
                read=tuple(value.lower() for value in yaml_list(item.get("read"))),
                why=yaml_str(item.get("why")),
            )
            for item in _mapping_list(route.get("expand_when"))
        )
        result.append(Route(
            name=name,
            route_id=_route_id(logical_id, name),
            use_when=tuple(yaml_list(route.get("use_when"))),
            priority_units=tuple(value.lower() for value in yaml_list(route.get("priority_units"))),
            requires=tuple(value.lower() for value in yaml_list(route.get("requires"))),
            avoid_by_default=tuple(yaml_list(route.get("avoid_by_default"))),
            verify=tuple(yaml_list(route.get("verify"))),
            expand_when=expansions,
            overrides=yaml_str(route.get("overrides")).lower(),
        ))
    return tuple(result)


def read_node(path: Path, paths: ContextCompilerPaths) -> KnowledgeNode:
    data = parse_yaml(path, paths.root, required=True)
    if yaml_str(data.get("schema")) != NODE_SCHEMA:
        raise HydraYamlError(f"{display_path(path, paths.root)} schema must be `{NODE_SCHEMA}`")
    logical_id = yaml_str(data.get("node")).lower()
    parts = tuple(part for part in logical_id.split("/") if part)
    parent_id = "/".join(parts[:-1])
    return KnowledgeNode(
        path=path,
        logical_id=logical_id,
        hydra_id=yaml_str(data.get("hydra_id")).lower(),
        uid=yaml_str(data.get("uid")),
        kind=yaml_str(data.get("kind")),
        title=yaml_str(data.get("title")),
        status=yaml_str(data.get("status")),
        scope=yaml_str(data.get("scope")),
        owners=yaml_map(data.get("owners")),
        relations=_read_relations(data),
        provenance=yaml_map(data.get("provenance")),
        role=yaml_str(data.get("role")),
        routable=data.get("routable") is True or yaml_str(data.get("routable")).lower() == "true",
        state=yaml_str(data.get("state")),
        overview=yaml_str(data.get("overview")),
        binding=yaml_str(data.get("binding")),
        keywords=tuple(yaml_list(data.get("keywords"))),
        defaults=yaml_map(data.get("defaults")),
        routes=_read_routes(data, logical_id),
        parent_id=parent_id,
        depth=len(parts),
    )


def discover_knowledge_nodes(paths: ContextCompilerPaths) -> list[KnowledgeNode]:
    config = load_spaces_config(paths)
    nodes: list[KnowledgeNode] = []
    for space in sorted(set(config.spaces)):
        root = spaces_root(paths) / space
        space_file = root / "space.yaml"
        if space_file.is_file():
            nodes.append(read_node(space_file, paths))
        for path in sorted(root.rglob("node.yaml")) if root.is_dir() else []:
            nodes.append(read_node(path, paths))
    return sorted(nodes, key=lambda node: (node.depth, node.logical_id))


def node_root(node: KnowledgeNode) -> Path:
    return node.path.parent


def knowledge_node_for_path(path: Path, nodes: list[KnowledgeNode], paths: ContextCompilerPaths) -> KnowledgeNode | None:
    """Deepest declared node containing `path`, never a lexical guess."""
    resolved = path.resolve() if path.is_absolute() else (paths.root / path).resolve()
    matches = [node for node in nodes if resolved == node_root(node).resolve() or node_root(node).resolve() in resolved.parents]
    return max(matches, key=lambda node: node.depth) if matches else None


def discover_node_unit_paths(node: KnowledgeNode) -> list[Path]:
    units = node_root(node) / "units"
    return sorted(units.glob("*.md")) if units.is_dir() else []


def expected_node_path(node: KnowledgeNode, paths: ContextCompilerPaths) -> Path:
    parts = node.logical_id.split("/")
    root = spaces_root(paths).joinpath(*parts)
    return root / ("space.yaml" if len(parts) == 1 else "node.yaml")


def _deep_merge(base: dict, incoming: dict, prefix: str, source: str, trace: dict[str, str]) -> dict:
    merged = dict(base)
    for key, value in incoming.items():
        field = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value, field, source, trace)
        else:
            merged[key] = value
            trace[field] = source
    return merged


def resolve_inheritance(node: KnowledgeNode, nodes_by_id: dict[str, KnowledgeNode]) -> dict:
    chain: list[KnowledgeNode] = []
    current: KnowledgeNode | None = node
    while current is not None:
        chain.append(current)
        current = nodes_by_id.get(current.parent_id)
    chain.reverse()

    owners: dict = {}
    defaults: dict = {}
    routes: dict[str, Route] = {}
    trace: dict[str, str] = {}
    avoid: list[str] = []
    for ancestor in chain:
        source = ancestor.hydra_id
        owners = _deep_merge(owners, ancestor.owners, "owners", source, trace)
        incoming_defaults = dict(ancestor.defaults)
        incoming_avoid = yaml_list(incoming_defaults.pop("avoid_by_default", []))
        defaults = _deep_merge(defaults, incoming_defaults, "defaults", source, trace)
        for value in incoming_avoid:
            if value not in avoid:
                avoid.append(value)
                trace[f"defaults.avoid_by_default.{value}"] = source
        for route in ancestor.routes:
            routes[route.name] = route
            trace[f"routes.{route.name}"] = source
    if avoid:
        defaults["avoid_by_default"] = avoid
    return {"owners": owners, "defaults": defaults, "routes": routes, "trace": trace}


def validate_knowledge_nodes(paths: ContextCompilerPaths) -> list[Finding]:
    code = "knowledge-v3-node"
    findings: list[Finding] = []
    try:
        config = load_spaces_config(paths)
    except HydraYamlError as error:
        return [Finding(path=".hydra-framework/repo/knowledge/spaces.yaml", code=code, detail=str(error))]
    label = display_path(config.path, paths.root)
    if not config.spaces:
        findings.append(Finding(path=label, code=code, detail=f"{label} must declare a non-empty closed `spaces` list"))
    if len(config.spaces) != len(set(config.spaces)):
        findings.append(Finding(path=label, code=code, detail=f"{label} contains duplicate spaces"))
    if config.default_depth < 1 or config.default_depth > config.max_depth:
        findings.append(Finding(path=label, code=code, detail=f"{label} default_depth must be between 1 and max_depth"))
    if config.max_depth != MAX_DEPTH:
        findings.append(Finding(path=label, code=code, detail=f"{label} max_depth must be the frozen hard ceiling {MAX_DEPTH}"))

    declared = set(config.spaces)
    root = spaces_root(paths)
    if root.is_dir():
        for item in sorted(root.iterdir()):
            if item.is_dir() and item.name not in declared:
                findings.append(Finding(path=display_path(item, paths.root), code=code, detail=f"unlisted knowledge space `{item.name}`"))

    nodes: list[KnowledgeNode] = []
    for space in sorted(declared):
        space_file = root / space / "space.yaml"
        if not space_file.is_file():
            findings.append(Finding(path=display_path(space_file, paths.root), code=code, detail=f"listed space `{space}` is missing space.yaml"))
            continue
        candidates = [space_file, *sorted((root / space).rglob("node.yaml"))]
        for path in candidates:
            try:
                nodes.append(read_node(path, paths))
            except HydraYamlError as error:
                findings.append(Finding(path=display_path(path, paths.root), code=code, detail=str(error)))

    nodes.sort(key=lambda node: (node.depth, node.logical_id))
    by_id: dict[str, KnowledgeNode] = {}
    for node in nodes:
        rel = display_path(node.path, paths.root)
        if node.logical_id in by_id:
            findings.append(Finding(path=rel, code=code, detail=f"duplicate logical node `{node.logical_id}`"))
        by_id[node.logical_id] = node
        expected_kind = "knowledge-space" if node.depth == 1 else "knowledge-node"
        expected_hydra_id = f"hydra://{expected_kind}/{node.logical_id}"
        if node.path.resolve() != expected_node_path(node, paths).resolve():
            findings.append(Finding(path=rel, code=code, detail=f"node `{node.logical_id}` does not match its directory placement"))
        if node.kind != expected_kind or node.hydra_id != expected_hydra_id:
            findings.append(Finding(path=rel, code=code, detail=f"node identity must be `{expected_hydra_id}` with kind `{expected_kind}`"))
        if node.depth > config.max_depth:
            findings.append(Finding(path=rel, code=code, detail=f"node depth {node.depth} exceeds {config.max_depth}; attach to the containing node, promote a stable boundary, or use a relation/view"))
        if node.depth > 1 and node.parent_id not in by_id and node.parent_id not in {item.logical_id for item in nodes}:
            findings.append(Finding(path=rel, code=code, detail=f"node parent does not resolve: {node.parent_id}"))
        if node.scope not in LEGAL_SCOPES:
            findings.append(Finding(path=rel, code=code, detail=f"scope `{node.scope}` is not one of {LEGAL_SCOPES}"))
        required_fields = [("uid", node.uid), ("title", node.title), ("status", node.status)]
        if node.depth == 1:
            required_fields.append(("owners", node.owners))
        for field, value in required_fields:
            if not value:
                findings.append(Finding(path=rel, code=code, detail=f"node is missing `{field}`"))
        for raw in (node.state, node.overview):
            if raw and (Path(raw).is_absolute() or (not raw.startswith(("./", "@")))):
                findings.append(Finding(path=rel, code=code, detail=f"node document path must be node-relative or logical: {raw}"))
        owned_content = bool(discover_node_unit_paths(node) or node.routes or node.state or node.overview)
        children = any(item.parent_id == node.logical_id for item in nodes)
        if owned_content and not node.routable:
            findings.append(Finding(path=rel, code=code, detail="only a routable node may own units, routes, state, or overview"))
        if not owned_content and not children:
            findings.append(Finding(path=rel, code=code, detail="empty structural node has neither children nor owned content"))
        for relation in node.relations:
            if relation.relation_type not in RELATION_TYPES:
                findings.append(Finding(path=rel, code=code, detail=f"relation type `{relation.relation_type}` is not one of {RELATION_TYPES}"))
            if not HYDRA_ID_RE.match(relation.target):
                findings.append(Finding(path=rel, code=code, detail=f"relation target is not a valid hydra id: {relation.target}"))
        ancestor_routes: dict[str, Route] = {}
        parent = by_id.get(node.parent_id)
        if parent:
            ancestor_routes = resolve_inheritance(parent, by_id)["routes"]
        for route in node.routes:
            inherited = ancestor_routes.get(route.name)
            if inherited and route.overrides != inherited.route_id:
                findings.append(Finding(path=rel, code=code, detail=f"route `{route.name}` overrides `{inherited.route_id}` and must declare it explicitly"))
            if route.overrides and (not inherited or route.overrides != inherited.route_id):
                findings.append(Finding(path=rel, code=code, detail=f"route `{route.name}` has invalid overrides target `{route.overrides}`"))
            if not route.use_when:
                findings.append(Finding(path=rel, code=code, detail=f"route `{route.name}` requires non-empty use_when"))
            for expansion in route.expand_when:
                if not expansion.when_paths or not expansion.read or not expansion.why:
                    findings.append(Finding(path=rel, code=code, detail=f"route `{route.name}` expand_when requires when_paths, read, and why"))
    return findings
