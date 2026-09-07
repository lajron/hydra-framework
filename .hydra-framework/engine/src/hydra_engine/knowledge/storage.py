"""Stable Knowledge v3 query boundary independent of registry layout."""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from typing import Protocol

from hydra_engine.knowledge.nodes import discover_knowledge_nodes, discover_node_unit_paths
from hydra_engine.knowledge.units import read_unit
from hydra_engine.knowledge.views import discover_views


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


class InMemoryKnowledgeStore:
    """Canonical-file adapter used by v3 before any registry sharding work."""

    def __init__(self, objects: Iterable[StoredKnowledgeObject]):
        ordered = tuple(sorted(objects, key=lambda item: item.hydra_id))
        self._objects = ordered
        self._by_id = {item.hydra_id.lower(): item for item in ordered}
        self._by_uid = {item.uid: item for item in ordered if item.uid}

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


def build_knowledge_store(paths) -> InMemoryKnowledgeStore:
    records: list[StoredKnowledgeObject] = []
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
