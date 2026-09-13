"""Stable Knowledge v3 query boundary independent of registry layout."""

from __future__ import annotations

import dataclasses
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from hydra_engine.documents.markdown import strip_markdown_code_fences
from hydra_engine.documents.tokens import read_text
from hydra_engine.knowledge.nodes import (
    KnowledgeNode,
    discover_knowledge_nodes,
    discover_node_unit_paths,
    read_node,
)
from hydra_engine.knowledge.units import read_unit
from hydra_engine.knowledge.views import discover_views, read_view


@dataclasses.dataclass(frozen=True)
class StoredKnowledgeObject:
    hydra_id: str
    uid: str
    kind: str
    path: str
    node_id: str
    relations: tuple[tuple[str, str], ...] = ()


class KnowledgeStore(Protocol):
    def by_id(self, hydra_id: str) -> StoredKnowledgeObject | None: ...
    def by_uid(self, uid: str) -> StoredKnowledgeObject | None: ...
    def iter_objects(self) -> Iterable[StoredKnowledgeObject]: ...
    def outgoing(self, hydra_id: str, relation_type: str = "") -> tuple[StoredKnowledgeObject, ...]: ...
    def incoming(self, hydra_id: str, relation_type: str = "") -> tuple[StoredKnowledgeObject, ...]: ...
    def by_path(self, path: str) -> StoredKnowledgeObject | None: ...
    def node_for_path(self, path: str) -> StoredKnowledgeObject | None: ...


class HydrationMismatch(ValueError):
    """A derived locator did not resolve to the canonical object it named.

    This is deliberately distinct from a parse error.  Both require callers
    to abandon the complete cached operation, but retaining the reason makes
    it possible to test the mtime/size false-negative safety boundary.
    """


def hydrate_object(paths, locator: StoredKnowledgeObject):
    """Read and verify one cached locator from canonical files.

    Locators are discovery hints only.  No caller may use one as an object
    until this function has confirmed its path, kind, id and opaque UID.
    """
    path = (paths.root / locator.path).resolve()
    try:
        path.relative_to(paths.root.resolve())
    except ValueError as error:
        raise HydrationMismatch(f"locator escapes repository: {locator.path}") from error
    try:
        if locator.kind in {"knowledge-node", "knowledge-space"}:
            object_value = read_node(path, paths)
        elif locator.kind == "knowledge-unit":
            object_value = read_unit(path, paths.root)
        elif locator.kind == "knowledge-view":
            object_value = read_view(path, paths)
        else:
            raise HydrationMismatch(f"unsupported Knowledge locator kind: {locator.kind}")
    except (OSError, ValueError) as error:
        raise HydrationMismatch(f"cannot hydrate {locator.hydra_id}: {error}") from error
    if object_value is None:
        raise HydrationMismatch(f"locator is no longer a Knowledge object: {locator.path}")
    actual_id = getattr(object_value, "hydra_id", "").lower()
    actual_uid = getattr(object_value, "uid", "")
    actual_path = getattr(object_value, "path", path).resolve()
    if (
        actual_id != locator.hydra_id.lower()
        or actual_uid != locator.uid
        or actual_path != path
    ):
        raise HydrationMismatch(f"locator disagrees with canonical object: {locator.hydra_id}")
    return object_value


def hydrate_node_and_ancestors(paths, store: KnowledgeStore, locator: StoredKnowledgeObject) -> tuple[KnowledgeNode, ...]:
    """Hydrate a selected node and every policy-contributing ancestor.

    A missing parent locator is not an invitation to mix cache and source
    graphs; it is a cache failure, so the caller must use one source snapshot.
    """
    if locator.kind not in {"knowledge-node", "knowledge-space"}:
        raise HydrationMismatch(f"not a node locator: {locator.hydra_id}")
    chain: list[KnowledgeNode] = []
    current = locator
    while True:
        node = hydrate_object(paths, current)
        if not isinstance(node, KnowledgeNode):
            raise HydrationMismatch(f"node locator hydrated to another type: {current.hydra_id}")
        chain.append(node)
        if not node.parent_id:
            break
        parent_id = f"hydra://knowledge-{'space' if '/' not in node.parent_id else 'node'}/{node.parent_id}"
        parent = store.by_id(parent_id)
        if parent is None:
            raise HydrationMismatch(f"missing ancestor locator: {parent_id}")
        current = parent
    return tuple(reversed(chain))


def hydrate_search_candidates(paths, db_path: Path, results) -> list | None:
    """Verify SQLite-nominated Knowledge candidates before observable use.

    Candidates below the v3 tree must agree byte-for-byte with their canonical
    files; their object and inherited policy chain are then hydrated as well.
    Failure deliberately returns no partial result so the caller can rerun one
    canonical search/snapshot instead of mixing source and cache graphs.
    """
    store = SqliteKnowledgeStore.open(db_path)
    if store is None:
        return None
    prefixes = (".hydra-framework/repo/knowledge/spaces/", ".hydra-framework/repo/knowledge/views/")
    try:
        for result in results:
            document = result.document
            if not document.path.startswith(prefixes):
                continue
            path = paths.root / document.path
            if not path.is_file() or strip_markdown_code_fences(read_text(path)) != document.body:
                raise HydrationMismatch(f"cached document disagrees with canonical file: {document.path}")
            locator = (store.by_id(document.hydra_id) if document.hydra_id.startswith("hydra://knowledge-") else None)
            locator = locator or store.by_path(document.path) or store.node_for_path(document.path)
            if locator is None:
                raise HydrationMismatch(f"missing locator for {document.path}")
            if locator.kind in {"knowledge-node", "knowledge-space"}:
                hydrate_node_and_ancestors(paths, store, locator)
            else:
                hydrate_object(paths, locator)
    except (OSError, ValueError):
        return None
    return results


class InMemoryKnowledgeStore:
    """Canonical-file adapter used by v3 before any registry sharding work."""

    def __init__(self, objects: Iterable[StoredKnowledgeObject]):
        ordered = tuple(sorted(objects, key=lambda item: item.hydra_id))
        self._objects = ordered
        self._by_id = {item.hydra_id.lower(): item for item in ordered}
        self._by_uid = {item.uid: item for item in ordered if item.uid}
        self._by_path = {item.path.lstrip("./"): item for item in ordered if item.path}
        # Node/space locators keyed by the directory their declaration sits in,
        # so `node_for_path` walks the queried path's own parents instead of
        # rebuilding a `node.yaml`/`space.yaml` probe per ancestor per call.
        # `routing_nodes` asks this once per search result, so the per-call
        # `Path` construction showed up as real warm-cache cost.
        # `node.yaml` is probed before `space.yaml`, as the ancestor walk did,
        # so a directory declaring both resolves the same way it always has.
        # Keyed through the same `lstrip("./")` normalization `by_path` applies
        # to both sides, so a stored `.hydra-framework/...` locator and a
        # queried document path meet on one spelling.
        self._nodes_by_dir: dict[str, StoredKnowledgeObject] = {}
        for basename in ("space.yaml", "node.yaml"):
            self._nodes_by_dir.update({
                item.path.lstrip("./").rpartition("/")[0]: item
                for item in ordered
                if item.path
                and item.kind in {"knowledge-node", "knowledge-space"}
                and item.path.rpartition("/")[2] == basename
            })

    def by_id(self, hydra_id: str) -> StoredKnowledgeObject | None:
        return self._by_id.get(hydra_id.lower())

    def by_uid(self, uid: str) -> StoredKnowledgeObject | None:
        return self._by_uid.get(uid)

    def iter_objects(self) -> Iterable[StoredKnowledgeObject]:
        return iter(self._objects)

    def outgoing(self, hydra_id: str, relation_type: str = "") -> tuple[StoredKnowledgeObject, ...]:
        source = self.by_id(hydra_id)
        if source is None:
            return ()
        return tuple(
            target
            for edge_type, target_id in source.relations
            if (not relation_type or edge_type == relation_type) and (target := self.by_id(target_id)) is not None
        )

    def incoming(self, hydra_id: str, relation_type: str = "") -> tuple[StoredKnowledgeObject, ...]:
        wanted = hydra_id.lower()
        return tuple(
            source
            for source in self._objects
            if any(target.lower() == wanted and (not relation_type or edge_type == relation_type) for edge_type, target in source.relations)
        )

    def by_path(self, path: str) -> StoredKnowledgeObject | None:
        return self._by_path.get(path.lstrip("./"))

    def node_for_path(self, path: str) -> StoredKnowledgeObject | None:
        candidate = path.lstrip("./")
        while candidate:
            found = self._nodes_by_dir.get(candidate)
            if found is not None:
                return found
            candidate = candidate.rpartition("/")[0]
        return None


def build_knowledge_store(paths) -> InMemoryKnowledgeStore:
    records: list[StoredKnowledgeObject] = []
    # The general search corpus still supports repositories mid-migration that
    # have no Knowledge v3 tree.  They receive an empty v3 projection, not a
    # failed reindex.
    if not (paths.hydra / "repo/knowledge/spaces.yaml").is_file():
        return InMemoryKnowledgeStore(records)
    for node in discover_knowledge_nodes(paths):
        records.append(StoredKnowledgeObject(
            hydra_id=node.hydra_id, uid=node.uid, kind=node.kind,
            path=node.path.relative_to(paths.root).as_posix(), node_id=node.logical_id,
            relations=tuple((relation.relation_type, relation.target) for relation in node.relations),
        ))
        for unit_path in discover_node_unit_paths(node):
            unit = read_unit(unit_path, paths.root)
            if unit is None:
                continue
            records.append(StoredKnowledgeObject(
                hydra_id=unit.hydra_id, uid=unit.uid, kind="knowledge-unit",
                path=unit.path.relative_to(paths.root).as_posix(), node_id=node.logical_id,
                relations=unit.relations,
            ))
    for view in discover_views(paths):
        records.append(StoredKnowledgeObject(
            hydra_id=view.hydra_id, uid=view.uid, kind="knowledge-view",
            path=view.path.relative_to(paths.root).as_posix(), node_id="", relations=(),
        ))
    return InMemoryKnowledgeStore(records)


def write_sqlite_store(conn: sqlite3.Connection, store: KnowledgeStore) -> None:
    """Persist a derived locator/edge projection in the private KnowledgeStore."""
    conn.execute(
        "CREATE TABLE knowledge_objects (hydra_id TEXT PRIMARY KEY, uid TEXT, kind TEXT, path TEXT, node_id TEXT)"
    )
    conn.execute(
        "CREATE TABLE knowledge_relations (source_id TEXT, relation_type TEXT, target_id TEXT, "
        "PRIMARY KEY(source_id, relation_type, target_id))"
    )
    objects = tuple(store.iter_objects())
    conn.executemany(
        "INSERT INTO knowledge_objects VALUES (?, ?, ?, ?, ?)",
        [(item.hydra_id, item.uid, item.kind, item.path, item.node_id) for item in objects],
    )
    conn.executemany(
        "INSERT INTO knowledge_relations VALUES (?, ?, ?)",
        [(item.hydra_id, relation_type, target) for item in objects for relation_type, target in item.relations],
    )
    conn.execute("CREATE INDEX idx_objects_uid ON knowledge_objects(uid)")
    conn.execute("CREATE INDEX idx_objects_path ON knowledge_objects(path)")
    conn.execute("CREATE INDEX idx_objects_node ON knowledge_objects(node_id)")
    conn.execute("CREATE INDEX idx_objects_kind ON knowledge_objects(kind)")
    conn.execute("CREATE INDEX idx_relations_source ON knowledge_relations(source_id)")
    conn.execute("CREATE INDEX idx_relations_target ON knowledge_relations(target_id)")


class SqliteKnowledgeStore:
    """Read-only private projection backed by its SQLite connection."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    @staticmethod
    def _objects(rows) -> tuple[StoredKnowledgeObject, ...]:
        grouped: list[StoredKnowledgeObject] = []
        current_key = object()
        current: list | None = None
        relations: list[tuple[str, str]] = []
        for row in rows:
            key, hydra_id, uid, kind, path, node_id, relation_type, target_id = row
            if key != current_key:
                if current is not None:
                    grouped.append(StoredKnowledgeObject(*current, tuple(relations)))
                current_key = key
                current = [hydra_id, uid, kind, path, node_id]
                relations = []
            if relation_type is not None:
                relations.append((relation_type, target_id))
        if current is not None:
            grouped.append(StoredKnowledgeObject(*current, tuple(relations)))
        return tuple(grouped)

    def _one(self, statement: str, parameters: tuple = ()) -> StoredKnowledgeObject | None:
        return next(iter(self._objects(self._conn.execute(statement, parameters))), None)

    def _lookup(self, predicate: str, parameters: tuple) -> StoredKnowledgeObject | None:
        return self._one(
            f"""
            WITH found AS (
                SELECT hydra_id, uid, kind, path, node_id
                FROM knowledge_objects WHERE {predicate}
            )
            SELECT found.hydra_id, found.hydra_id, found.uid, found.kind, found.path, found.node_id, relations.relation_type, relations.target_id
            FROM found LEFT JOIN knowledge_relations AS relations ON relations.source_id = found.hydra_id
            ORDER BY relations.rowid
            """,
            parameters,
        )

    @classmethod
    def open(cls, db_path: Path) -> "SqliteKnowledgeStore | None":
        try:
            return cls(sqlite3.connect(f"file:{db_path}?mode=ro", uri=True))
        except sqlite3.Error:
            return None

    def by_id(self, hydra_id: str) -> StoredKnowledgeObject | None:
        return self._lookup("hydra_id = ?", (hydra_id.lower(),))

    def by_uid(self, uid: str) -> StoredKnowledgeObject | None:
        return self._lookup("uid = ?", (uid,))

    def iter_objects(self) -> Iterable[StoredKnowledgeObject]:
        rows = self._conn.execute(
            """
            SELECT objects.hydra_id, objects.hydra_id, objects.uid, objects.kind, objects.path, objects.node_id, relations.relation_type, relations.target_id
            FROM knowledge_objects AS objects
            LEFT JOIN knowledge_relations AS relations ON relations.source_id = objects.hydra_id
            ORDER BY objects.hydra_id, relations.rowid
            """
        )
        return iter(self._objects(rows))

    def outgoing(self, hydra_id: str, relation_type: str = "") -> tuple[StoredKnowledgeObject, ...]:
        return self._objects(self._conn.execute(
            """
            WITH edges AS (
                SELECT rowid AS edge_id, target_id
                FROM knowledge_relations
                WHERE source_id = ? AND (? = '' OR relation_type = ?)
            )
            SELECT edges.edge_id, target.hydra_id, target.uid, target.kind, target.path, target.node_id, relations.relation_type, relations.target_id
            FROM edges
            JOIN knowledge_objects AS target ON target.hydra_id = edges.target_id
            LEFT JOIN knowledge_relations AS relations ON relations.source_id = target.hydra_id
            ORDER BY edges.edge_id, relations.rowid
            """,
            (hydra_id.lower(), relation_type, relation_type),
        ))

    def incoming(self, hydra_id: str, relation_type: str = "") -> tuple[StoredKnowledgeObject, ...]:
        return self._objects(self._conn.execute(
            """
            WITH sources AS (
                SELECT DISTINCT source_id
                FROM knowledge_relations
                WHERE target_id = ? AND (? = '' OR relation_type = ?)
            )
            SELECT source.hydra_id, source.hydra_id, source.uid, source.kind, source.path, source.node_id, relations.relation_type, relations.target_id
            FROM sources
            JOIN knowledge_objects AS source ON source.hydra_id = sources.source_id
            LEFT JOIN knowledge_relations AS relations ON relations.source_id = source.hydra_id
            ORDER BY source.hydra_id, relations.rowid
            """,
            (hydra_id.lower(), relation_type, relation_type),
        ))

    def by_path(self, path: str) -> StoredKnowledgeObject | None:
        normalized = path.lstrip("./")
        return self._lookup("path IN (?, ?)", (normalized, f".{normalized}"))

    def node_for_path(self, path: str) -> StoredKnowledgeObject | None:
        candidate = path.lstrip("./")
        probes: list[str] = []
        while candidate:
            probes.extend((
                f".{candidate}/node.yaml", f".{candidate}/space.yaml",
                f"{candidate}/node.yaml", f"{candidate}/space.yaml",
            ))
            candidate = candidate.rpartition("/")[0]
        if not probes: return None
        placeholders = ", ".join("?" for _ in probes)
        precedence = " ".join(f"WHEN ? THEN {index}" for index in range(len(probes)))
        statement = f"""
            WITH found AS (
                SELECT hydra_id, uid, kind, path, node_id
                FROM knowledge_objects
                WHERE path IN ({placeholders}) AND kind IN ('knowledge-node', 'knowledge-space')
                ORDER BY CASE path {precedence} END
                LIMIT 1
            )
            SELECT found.hydra_id, found.hydra_id, found.uid, found.kind, found.path, found.node_id, relations.relation_type, relations.target_id
            FROM found LEFT JOIN knowledge_relations AS relations ON relations.source_id = found.hydra_id
            ORDER BY relations.rowid
        """
        return self._one(statement, (*probes, *probes))
