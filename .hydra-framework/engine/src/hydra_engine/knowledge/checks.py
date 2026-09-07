"""Repository-wide Knowledge v3 validation composed from the frozen contracts."""

from __future__ import annotations

from hydra_engine.documents.frontmatter_blocks import markdown_frontmatter
from hydra_engine.documents.tokens import HydraYamlError, display_path
from hydra_engine.finding import Finding
from hydra_engine.knowledge.bindings import bindings_root, load_bindings, validate_bindings
from hydra_engine.knowledge.graph import KnowledgeGraphError, global_required_closure
from hydra_engine.knowledge.nodes import (
    LEGAL_SCOPES,
    RELATION_TYPES,
    discover_knowledge_nodes,
    discover_node_unit_paths,
    validate_knowledge_nodes,
)
from hydra_engine.knowledge.units import read_unit
from hydra_engine.knowledge.views import discover_views, validate_views


def validate_knowledge_v3(ctx) -> list[Finding]:
    paths = ctx.context_compiler_paths()
    code = "knowledge-v3"
    legacy = paths.hydra / "repo/knowledge/knowledge-packages"
    configured = paths.hydra / "repo/knowledge/spaces.yaml"
    active_legacy = legacy.is_dir() and any(legacy.iterdir())
    if not configured.is_file() and not active_legacy:
        return []
    findings = validate_knowledge_nodes(paths)
    if findings:
        return findings
    nodes = discover_knowledge_nodes(paths)
    bindings = {}
    if (bindings_root(paths) / "manifest.yaml").is_file():
        findings.extend(validate_bindings(paths))
        try:
            bindings = load_bindings(paths)
        except (HydraYamlError, OSError, ValueError):
            bindings = {}

    units: dict = {}
    unit_paths: dict[str, str] = {}
    all_ids = {node.hydra_id for node in nodes}
    for node in nodes:
        if node.binding and node.binding not in bindings:
            findings.append(Finding(
                path=display_path(node.path, paths.root), code=code,
                detail=f"node binding does not resolve: {node.binding}",
            ))
        for path in discover_node_unit_paths(node):
            unit = read_unit(path, paths.root)
            if unit is None:
                continue
            rel = display_path(path, paths.root)
            expected = f"hydra://knowledge-unit/{node.logical_id}/{path.stem}"
            if unit.hydra_id != expected:
                findings.append(Finding(path=rel, code=code, detail=f"unit identity must be `{expected}`"))
            if unit.hydra_id in units:
                findings.append(Finding(path=rel, code=code, detail=f"duplicate global unit id `{unit.hydra_id}`"))
            units[unit.hydra_id] = unit
            unit_paths[unit.hydra_id] = rel
            all_ids.add(unit.hydra_id)
            data = markdown_frontmatter(path, paths.root)
            if data.get("expand_when") not in (None, [], ""):
                findings.append(Finding(path=rel, code=code, detail="unit-level expand_when is invalid in v3; move conditional selection to a route"))
            scope = data.get("scope")
            if scope not in LEGAL_SCOPES:
                findings.append(Finding(path=rel, code=code, detail=f"scope `{scope}` is not one of {LEGAL_SCOPES}"))
            raw_relations = data.get("relations")
            if not isinstance(raw_relations, list) or any(not isinstance(item, dict) for item in raw_relations):
                findings.append(Finding(path=rel, code=code, detail="v3 Knowledge relations must be typed mappings"))
            for relation_type, target in unit.relations:
                if relation_type not in RELATION_TYPES:
                    findings.append(Finding(path=rel, code=code, detail=f"relation type `{relation_type}` is not one of {RELATION_TYPES}"))

    for node in nodes:
        for route in node.routes:
            for target in (*route.priority_units, *route.requires, *(value for expansion in route.expand_when for value in expansion.read)):
                if target not in units:
                    findings.append(Finding(
                        path=display_path(node.path, paths.root), code=code,
                        detail=f"route `{route.route_id}` references unresolved unit `{target}`",
                    ))
            for expansion in route.expand_when:
                for pattern in expansion.when_paths:
                    if not pattern.startswith("@"):
                        findings.append(Finding(
                            path=display_path(node.path, paths.root), code=code,
                            detail=f"route `{route.route_id}` expand_when path must use a logical binding: {pattern}",
                        ))

    for unit_id in sorted(units):
        try:
            global_required_closure(units, {unit_id})
        except KnowledgeGraphError as error:
            findings.append(Finding(path=unit_paths[unit_id], code=code, detail=str(error)))

    all_ids.update(view.hydra_id for view in discover_views(paths))
    findings.extend(validate_views(paths, all_ids))
    if active_legacy:
        findings.append(Finding(
            path=display_path(legacy, paths.root), code=code,
            detail="active v2 knowledge-packages remain; migrate them before v3 validation can pass",
        ))
    return findings
