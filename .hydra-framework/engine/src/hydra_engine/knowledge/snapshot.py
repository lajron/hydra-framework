"""Operation-scoped canonical hydration over the private KnowledgeStore."""

from __future__ import annotations

import dataclasses

from hydra_engine.knowledge.storage import (
    HydrationMismatch, KnowledgeStore, SqliteKnowledgeStore, StoredKnowledgeObject,
    hydrate_node_and_ancestors, hydrate_object,
)
from hydra_engine.knowledge.units import read_unit
from hydra_engine.knowledge.views import discover_views


@dataclasses.dataclass
class KnowledgeSnapshot:
    """One operation-scoped view; cached values merely narrow canonical reads."""

    paths: object
    store: KnowledgeStore | None = None
    # The read stamp this snapshot's `store` was opened against, or `None` in
    # source mode. The caller that opened this snapshot threads it through
    # search, routing, views and unit hydration by simply reusing the one
    # snapshot instance, then revalidates it once at the end of the
    # observable operation: a fresh `index_cache.capture_stamp(...)` unequal
    # to this value means the governed corpus or the publication moved
    # during the operation, so the whole result must be discarded and rerun
    # canonically rather than published as a mix of two generations.
    stamp: object | None = None
    _nodes: tuple[object, ...] | None = None
    _views: tuple[object, ...] | None = None
    _bindings: dict | None = None
    _units: dict | None = None
    _unit_owners: dict[str, str] | None = None

    @property
    def cached(self) -> bool:
        return self.store is not None

    def canonical_nodes(self) -> tuple[object, ...]:
        if self._nodes is None:
            discover_knowledge_nodes = __import__("hydra_engine.knowledge.nodes", fromlist=("discover_knowledge_nodes",)).discover_knowledge_nodes
            self._nodes = tuple(discover_knowledge_nodes(self.paths))
        return self._nodes

    def routing_nodes(self, results, node_values: tuple[str, ...] = (), space: str = "") -> tuple[object, ...]:
        if self.store is None:
            return self.canonical_nodes()
        locators: dict[str, StoredKnowledgeObject] = {}
        all_nodes = tuple(item for item in self.store.iter_objects() if item.kind in {"knowledge-node", "knowledge-space"})
        for value in node_values:
            raw = value.lower().removeprefix("hydra://knowledge-node/").removeprefix("hydra://knowledge-space/")
            leaf = raw.rsplit("/", 1)[-1]
            matches = [item for item in all_nodes if item.node_id == raw or item.hydra_id.lower() == value.lower()]
            if not matches:
                matches = [item for item in all_nodes if item.node_id.rsplit("/", 1)[-1] == leaf]
            if not matches:
                raise HydrationMismatch(f"explicit node locator missing: {value}")
            locators.update({item.hydra_id: item for item in matches})
        if space:
            matches = [item for item in all_nodes if item.node_id == space.lower()]
            if not matches:
                raise HydrationMismatch(f"explicit space locator missing: {space}")
            locators.update({item.hydra_id: item for item in matches})
        if not node_values and not space:
            for result in results:
                document = result.document
                locator = self.store.by_id(document.hydra_id) if document.hydra_id else None
                locator = locator or self.store.node_for_path(document.path)
                if locator is not None and locator.kind in {"knowledge-node", "knowledge-space"}:
                    locators[locator.hydra_id] = locator
            if not locators and len(all_nodes) == 1:
                locators[all_nodes[0].hydra_id] = all_nodes[0]
        hydrated: dict[str, object] = {}
        for locator in locators.values():
            hydrated.update({node.logical_id: node for node in hydrate_node_and_ancestors(self.paths, self.store, locator)})
        return tuple(sorted(hydrated.values(), key=lambda node: (node.depth, node.logical_id)))

    def bindings(self) -> dict:
        if self._bindings is None:
            from hydra_engine.knowledge.bindings import BindingResolutionError, bindings_root, load_bindings, verify_binding
            self._bindings = load_bindings(self.paths) if (bindings_root(self.paths) / "manifest.yaml").is_file() else {}
            for binding in self._bindings.values():
                if verify_binding(binding, self.paths).state != "verified":
                    raise BindingResolutionError(f"binding `{binding.logical_name}` is not verified")
        return self._bindings

    def node_for_reference(self, reference: str) -> object:
        if self.store is None:
            match = next((node for node in self.canonical_nodes() if node.hydra_id == reference), None)
            if match is None:
                raise HydrationMismatch(f"missing canonical node: {reference}")
            return match
        locator = self.store.by_id(reference)
        if locator is None:
            raise HydrationMismatch(f"missing node locator: {reference}")
        return hydrate_node_and_ancestors(self.paths, self.store, locator)[-1]

    def views_for_request(self, results, requested: tuple[str, ...]) -> tuple[object, ...]:
        if self.store is None:
            if self._views is None:
                self._views = tuple(discover_views(self.paths))
            return self._views
        selected: dict[str, StoredKnowledgeObject] = {}
        views = tuple(item for item in self.store.iter_objects() if item.kind == "knowledge-view")
        for value in requested:
            normalized = value.lower()
            matches = [item for item in views if item.hydra_id == normalized or item.hydra_id.rsplit("/", 1)[-1] == normalized]
            if not matches:
                raise HydrationMismatch(f"explicit view locator missing: {value}")
            selected.update({item.hydra_id: item for item in matches})
        if not requested:
            for result in results:
                locator = self.store.by_id(result.document.hydra_id) if result.document.hydra_id else None
                locator = locator or self.store.by_path(result.document.path)
                if locator is not None and locator.kind == "knowledge-view":
                    selected[locator.hydra_id] = locator
        hydrated: dict[str, object] = {}
        def load(locator: StoredKnowledgeObject) -> None:
            if locator.hydra_id in hydrated:
                return
            view = hydrate_object(self.paths, locator)
            hydrated[locator.hydra_id] = view
            for reference in view.include:
                if reference.startswith("hydra://knowledge-view/"):
                    target = self.store.by_id(reference)
                    if target is None:
                        raise HydrationMismatch(f"missing transitive view locator: {reference}")
                    load(target)
        for locator in selected.values():
            load(locator)
        return tuple(sorted(hydrated.values(), key=lambda view: view.hydra_id))

    def units_for_selection(self, nodes, results, seed_ids: set[str]) -> tuple[dict, dict[str, str]]:
        if self.store is None:
            if self._units is None:
                self._units, self._unit_owners = {}, {}
                discover_node_unit_paths = __import__("hydra_engine.knowledge.nodes", fromlist=("discover_node_unit_paths",)).discover_node_unit_paths
                for node in self.canonical_nodes():
                    for path in discover_node_unit_paths(node):
                        if (unit := read_unit(path, self.paths.root)) is not None and unit.hydra_id:
                            self._units[unit.hydra_id.lower()] = unit
                            self._unit_owners[unit.hydra_id.lower()] = node.logical_id
            return self._units, self._unit_owners
        units, owners, wanted = {}, {}, {value.lower() for value in seed_ids}
        selected_nodes = {node.logical_id for node in nodes}
        for result in results:
            locator = self.store.by_id(result.document.hydra_id) if result.document.hydra_id else self.store.by_path(result.document.path)
            if locator is not None and locator.kind == "knowledge-unit" and locator.node_id in selected_nodes:
                wanted.add(locator.hydra_id.lower())
        def load(unit_id: str) -> None:
            if unit_id in units:
                return
            locator = self.store.by_id(unit_id)
            if locator is None or locator.kind != "knowledge-unit":
                raise HydrationMismatch(f"missing unit locator: {unit_id}")
            unit = hydrate_object(self.paths, locator)
            units[unit.hydra_id.lower()], owners[unit.hydra_id.lower()] = unit, locator.node_id
            for target in unit.requires:
                load(target.lower())
            for superseder in self.store.incoming(unit.hydra_id, "supersedes"):
                if superseder.kind == "knowledge-unit":
                    load(superseder.hydra_id.lower())
        for unit_id in sorted(wanted):
            load(unit_id)
        return units, owners


def open_knowledge_snapshot(paths, db_path, source: str, *, stamp: object | None = None) -> KnowledgeSnapshot:
    store = SqliteKnowledgeStore.open(db_path) if source == "sqlite" else None
    if source == "sqlite" and store is None:
        raise HydrationMismatch("SQLite store became unavailable during operation")
    return KnowledgeSnapshot(paths, store, stamp if source == "sqlite" else None)
