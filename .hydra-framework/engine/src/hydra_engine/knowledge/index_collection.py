"""Canonical full and safe per-path collection for the Knowledge index."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from pathlib import Path

from hydra_engine.documents.markdown import strip_markdown_code_fences
from hydra_engine.documents.tokens import display_path, read_text
from hydra_engine.knowledge.freshness import SEARCH_EXTENSIONS, SEARCH_ROOTS, is_governed_path
from hydra_engine.knowledge.node_catalog import discover_knowledge_nodes, knowledge_node_for_path, node_root, resolve_inheritance
from hydra_engine.knowledge.units import read_unit
from hydra_engine.knowledge.views import discover_views


@dataclasses.dataclass(frozen=True)
class SearchDocument:
    key: str; hydra_id: str; aliases: tuple[str, ...]; path: str; kind: str; package: str; title: str; keywords: tuple[str, ...]
    routes: tuple[str, ...]; use_when: tuple[str, ...]; headings: tuple[str, ...]; body: str; relations: tuple[str, ...]
    content_id: str = ""


def delta_is_local(paths, resolver_paths, change) -> bool:
    """Reject every delta whose complete local effect cannot be proven cheaply."""
    for rel in (*change.added, *change.modified, *change.deleted):
        if not is_governed_path(rel) or rel.endswith(("spaces.yaml", "space.yaml", "node.yaml", ".view.yaml")):
            return False
        path = paths.root / rel
        if rel in change.deleted and path.suffix in {".yaml", ".yml"}:
            return False
        if rel in (*change.added, *change.modified):
            if not path.is_file():
                return False
            if path.suffix in {".yaml", ".yml"}:
                try:
                    documents = __import__("hydra_engine.documents.yaml_documents", fromlist=("parse_yaml", "yaml_str"))
                    discovery = __import__("hydra_engine.objects.discovery", fromlist=("OBJECT_SIDECAR_SCHEMA",))
                    if documents.yaml_str(documents.parse_yaml(path, paths.root).get("schema")) == discovery.OBJECT_SIDECAR_SCHEMA:
                        return False
                except (OSError, ValueError):
                    return False
    return True


def collect_search_documents(paths, resolver_paths, command_ids: tuple[str, ...] = (), *, content_ids: Mapping[str, str] | None = None, only_paths: frozenset[str] | None = None, _nodes: list | None = None) -> list[SearchDocument]:
    """Collect canonical documents, or the already-classified local subset."""
    nodes = _discover_nodes_or_empty(paths) if _nodes is None else _nodes
    docs: dict[str, SearchDocument] = {}
    if only_paths is not None:
        for rel in sorted(only_paths):
            file_path = paths.root / rel
            if not file_path.is_file():
                continue
            discovery = __import__("hydra_engine.objects.discovery", fromlist=("extract_hydra_object",))
            entry, error = discovery.extract_hydra_object(file_path, resolver_paths)
            if error:
                raise ValueError(error)
            entry = entry or {}
            docs[rel] = _with_content_id(_document_for_path(paths, file_path, rel, _str(entry.get("id")).lower(), entry, nodes), content_ids)
        return list(docs.values())

    discovery = __import__("hydra_engine.objects.discovery", fromlist=("collect_hydra_objects",))
    objects, _errors = discovery.collect_hydra_objects(resolver_paths)
    by_path: dict[str, dict] = {}
    by_id: dict[str, dict] = {}
    for entry in objects:
        hydra_id = _str(entry.get("id")).lower()
        if not hydra_id:
            continue
        by_id[hydra_id] = entry
        path = _str(entry.get("path"))
        if path:
            by_path.setdefault(path, {"ids": [], "entries": []})
            by_path[path]["ids"].append(hydra_id)
            by_path[path]["entries"].append(entry)
    for file_path in _canonical_search_files(paths.root):
        rel = display_path(file_path, paths.root)
        grouped = by_path.get(rel, {"ids": [], "entries": []})
        entry = grouped["entries"][0] if grouped["entries"] else {}
        docs[rel] = _with_content_id(_document_for_path(paths, file_path, rel, grouped["ids"][0] if grouped["ids"] else "", entry, nodes), content_ids)
    for hydra_id, entry in by_id.items():
        path = _str(entry.get("path"))
        if path not in docs:
            docs[f"id:{hydra_id}"] = _with_content_id(_document_for_object(paths, hydra_id, entry, nodes), content_ids)
    for command_id in command_ids:
        key = f"command:{command_id}"
        docs[key] = SearchDocument(key, "", (), "", "command", "", command_id, (command_id,), (), (), (), f"hydra.py {command_id}", ())
    return list(docs.values())


def collect_changed_knowledge_objects(paths, changed: tuple[str, ...], *, _nodes: list | None = None):
    """Collect unit locators only; declarations and views are never local."""
    storage = __import__("hydra_engine.knowledge.storage", fromlist=("StoredKnowledgeObject",))
    nodes = _discover_nodes_or_empty(paths) if _nodes is None else _nodes
    records = []
    for rel in sorted(set(changed)):
        path = paths.root / rel
        if not path.is_file():
            continue
        node = knowledge_node_for_path(path, nodes, paths)
        if node is None or path.parent != node_root(node) / "units" or path.suffix != ".md":
            continue
        unit = read_unit(path, paths.root)
        if unit is not None:
            records.append(storage.StoredKnowledgeObject(unit.hydra_id, unit.uid, "knowledge-unit", rel, node.logical_id, unit.relations))
    return tuple(records)


def build_knowledge_store(paths):
    """Full v3 locator collection, kept behaviorally equivalent to its former home."""
    storage = __import__("hydra_engine.knowledge.storage", fromlist=("InMemoryKnowledgeStore", "StoredKnowledgeObject"))
    records = []
    if not (paths.hydra / "repo/knowledge/spaces.yaml").is_file():
        return storage.InMemoryKnowledgeStore(records)
    for node in discover_knowledge_nodes(paths):
        records.append(storage.StoredKnowledgeObject(node.hydra_id, node.uid, node.kind, node.path.relative_to(paths.root).as_posix(), node.logical_id, tuple((relation.relation_type, relation.target) for relation in node.relations)))
        units = node_root(node) / "units"
        for unit_path in sorted(units.glob("*.md")) if units.is_dir() else ():
            unit = read_unit(unit_path, paths.root)
            if unit is not None:
                records.append(storage.StoredKnowledgeObject(unit.hydra_id, unit.uid, "knowledge-unit", unit.path.relative_to(paths.root).as_posix(), node.logical_id, unit.relations))
    for view in discover_views(paths):
        records.append(storage.StoredKnowledgeObject(view.hydra_id, view.uid, "knowledge-view", view.path.relative_to(paths.root).as_posix(), "", ()))
    return storage.InMemoryKnowledgeStore(records)


def document_for_path(paths, file_path: Path, rel: str, hydra_id: str, entry: dict, nodes: list) -> SearchDocument:
    return _document_for_path(paths, file_path, rel, hydra_id, entry, nodes)


def discover_nodes_or_empty(paths) -> list:
    return _discover_nodes_or_empty(paths)


def _with_content_id(document: SearchDocument, content_ids: Mapping[str, str] | None) -> SearchDocument:
    return dataclasses.replace(document, content_id=(content_ids or {}).get(document.path, ""))


def _canonical_search_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for raw in SEARCH_ROOTS:
        base = root / raw
        if base.exists():
            files.extend(path for path in sorted(base.rglob("*")) if path.is_file() and path.suffix in SEARCH_EXTENSIONS)
    if (root / "AI_SYSTEM.md").exists():
        files.append(root / "AI_SYSTEM.md")
    handlers = __import__("hydra_engine.objects.object_handlers", fromlist=("object_document_paths",))
    files.extend(path for path in handlers.object_document_paths(root / ".hydra-framework") if is_governed_path(display_path(path, root)))
    return sorted(set(files))


def _discover_nodes_or_empty(paths) -> list:
    try:
        return discover_knowledge_nodes(paths)
    except Exception:
        return []


def _document_for_path(paths, file_path: Path, rel: str, hydra_id: str, entry: dict, nodes: list) -> SearchDocument:
    text = read_text(file_path)
    headings = tuple(line.lstrip("#").strip() for line in text.splitlines() if line.startswith("#"))
    package = _package_for(file_path, paths, hydra_id, nodes)
    routes, use_when, keywords = _routing_fields(file_path, paths, nodes)
    return SearchDocument(rel, hydra_id, tuple(_list(entry.get("aliases"))), rel, _str(entry.get("kind"), "file"), package, _str(entry.get("title"), headings[0] if headings else file_path.stem), keywords, routes, use_when, headings, strip_markdown_code_fences(text), tuple(_list(entry.get("relations"))))


def _document_for_object(paths, hydra_id: str, entry: dict, nodes: list) -> SearchDocument:
    path = _str(entry.get("path"))
    return SearchDocument(f"id:{hydra_id}", hydra_id, tuple(_list(entry.get("aliases"))), path, _str(entry.get("kind")), _package_for(paths.root / path, paths, hydra_id, nodes), _str(entry.get("title")), (), (), (), (), _str(entry.get("title")), tuple(_list(entry.get("relations"))))


def _package_for(file_path: Path, paths, hydra_id: str, nodes: list) -> str:
    for prefix in ("hydra://knowledge-space/", "hydra://knowledge-node/"):
        if hydra_id.startswith(prefix):
            return hydra_id.removeprefix(prefix)
    node = knowledge_node_for_path(file_path, nodes, paths)
    return node.logical_id if node else ""


def _routing_fields(file_path: Path, paths, nodes: list) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    node = knowledge_node_for_path(file_path, nodes, paths)
    if node is None:
        return (), (), ()
    routes = resolve_inheritance(node, {item.logical_id: item for item in nodes})["routes"]
    return tuple(routes), tuple(value for route in routes.values() for value in route.use_when), node.keywords


def _list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return [item.strip() for item in value.split(",") if item.strip()] if isinstance(value, str) else []


def _str(value: object, default: str = "") -> str:
    return str(value) if value is not None else default
