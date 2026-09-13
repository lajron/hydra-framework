from __future__ import annotations

import dataclasses
import tempfile
import unittest
import sqlite3
import subprocess
from pathlib import Path
from unittest import mock

from hydra_engine.identity.object_families import OBJECT_FAMILIES
from hydra_engine.knowledge import context_providers
from hydra_engine.knowledge import index_cache
from hydra_engine.knowledge import search_index
from hydra_engine.knowledge import snapshot as knowledge_snapshot
from hydra_engine.knowledge import storage
from hydra_engine.knowledge.search_index import SearchDocument, SearchResult
from hydra_engine.objects.discovery import ObjectLocations
from v3_fixtures import paths_for, write_node, write_unit


def _resolver_paths(root: Path) -> ObjectLocations:
    hydra = root / ".hydra-framework"
    return ObjectLocations(root, hydra, root / ".hydra-framework.local", "tasks/personal", hydra / "cognition/graph/registry.yaml")


def _commit(root: Path) -> None:
    for command in (
        ("git", "init"),
        ("git", "config", "user.email", "tests@example.invalid"),
        ("git", "config", "user.name", "Tests"),
        ("git", "add", "-A"),
        ("git", "commit", "-m", "fixture"),
    ):
        subprocess.run(command, cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _request(root: Path, **changes) -> context_providers.ProviderRequest:
    paths = changes.pop("paths", None)
    if paths is None:
        paths = paths_for(root)
    values = {
        "task": "",
        "paths": paths,
        "resolver_paths": _resolver_paths(root),
        "object_seed_ids": frozenset(),
        "chars_per_token": 4,
        "family_cap": context_providers.DEFAULT_FAMILY_CANDIDATE_CAP,
    }
    values.update(changes)
    return context_providers.ProviderRequest(**values)


def _doc(path: str, *, kind: str, hydra_id: str = "") -> SearchDocument:
    return SearchDocument(
        key=path, hydra_id=hydra_id, aliases=(), path=path, kind=kind, package="",
        title=path, keywords=(), routes=(), use_when=(), headings=(), body="fixture body", relations=(),
    )


def _route_block(required: str) -> str:
    return (
        "routes:\n"
        "  adopt:\n"
        "    use_when:\n"
        "      - adopt hydra repository\n"
        "    priority_units:\n"
        "      - hydra://knowledge-unit/demo/adopt\n"
        "    requires:\n"
        f"      - {required}\n"
        "    avoid_by_default:\n"
        "      - generated/**\n"
        "    verify:\n"
        "      - python3 .hydra-framework/scripts/hydra.py validate\n"
        "    expand_when: []\n"
    )


class RegistryConsistencyTests(unittest.TestCase):
    def test_every_object_family_has_exactly_one_context_provider(self):
        self.assertEqual({family.name for family in OBJECT_FAMILIES}, {provider.family for provider in context_providers.CONTEXT_PROVIDERS})


class MatchedFamiliesTests(unittest.TestCase):
    def test_matches_slug_and_reports_unknown(self):
        matched, unknown = context_providers._matched_families(("runtime-engine", "nope"))
        self.assertEqual(matched, {"Runtime/Engine"})
        self.assertEqual(unknown, ["nope"])


class FamilySearchCollectorTests(unittest.TestCase):
    def test_filters_by_family_and_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / ".hydra-framework/repo/source"
            source_dir.mkdir(parents=True)
            for name in ("a", "b"):
                (source_dir / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")
            results = (
                SearchResult(_doc(".hydra-framework/repo/source/a.md", kind="source"), "exact", 0),
                SearchResult(_doc(".hydra-framework/repo/source/b.md", kind="source"), "fts", 1),
            )
            output = context_providers.PROVIDERS_BY_FAMILY["Source"].collect(
                _request(root, family_cap=1, search_results=results)
            )
            self.assertEqual([item["path"] for item in output.candidates], [".hydra-framework/repo/source/a.md"])


class KnowledgeCollectorTests(unittest.TestCase):
    def _fixture(self, root: Path):
        paths = paths_for(root, ("demo", "security"))
        required = "hydra://knowledge-unit/security/baseline"
        write_node(paths, "demo", keywords=("adopt", "hydra"), routes=_route_block(required))
        write_node(paths, "security", keywords=("security",))
        write_unit(paths, "demo", "adopt", requires=(required,))
        write_unit(paths, "security", "baseline")
        _commit(root)
        return paths

    def test_route_selects_priority_and_cross_space_required_closure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._fixture(root)
            output = context_providers.PROVIDERS_BY_FAMILY["Knowledge"].collect(
                _request(root, paths=paths, task="adopt hydra repository", node_values=("demo",))
            )
            unit_ids = {item["source"] for item in output.candidates if item["kind"] == "knowledge-unit"}
            self.assertEqual(unit_ids, {
                "hydra://knowledge-unit/demo/adopt",
                "hydra://knowledge-unit/security/baseline",
            })
            self.assertEqual(output.nodes[0]["routes"], ["adopt"])
            self.assertEqual(output.avoid_by_default, ["generated/**"])

    def test_explicit_route_wins_without_prompt_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._fixture(root)
            output = context_providers.PROVIDERS_BY_FAMILY["Knowledge"].collect(
                _request(root, paths=paths, task="weather", node_values=("demo",), route_values=("demo:adopt",))
            )
            self.assertEqual(output.nodes[0]["routes"], ["adopt"])

    def test_without_route_search_rank_fills_optional_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = paths_for(root)
            write_node(paths, "demo", keywords=("ranking",))
            beta = write_unit(paths, "demo", "beta")
            write_unit(paths, "demo", "alpha")
            result = SearchResult(_doc(str(beta.relative_to(root)), kind="knowledge-unit", hydra_id="hydra://knowledge-unit/demo/beta"), "fts", 0)
            output = context_providers.PROVIDERS_BY_FAMILY["Knowledge"].collect(
                _request(root, paths=paths, task="ranking", node_values=("demo",), search_results=(result,), family_cap=1)
            )
            units = [item["source"] for item in output.candidates if item["kind"] == "knowledge-unit"]
            self.assertEqual(units, ["hydra://knowledge-unit/demo/beta"])

    def test_cached_operation_hydrates_selected_node_and_unit_closure_without_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._fixture(root)
            local = root / ".hydra-framework.local"
            search_index.build_index(paths, _resolver_paths(root), local)
            request = _request(root, paths=paths, task="adopt hydra repository", node_values=("demo",))
            with mock.patch("hydra_engine.knowledge.nodes.discover_knowledge_nodes", side_effect=AssertionError("whole tree")):
                output = context_providers.run_context_providers(request, include_families=("Knowledge",))
            unit_ids = {item["source"] for item in output.candidates if item["kind"] == "knowledge-unit"}
            self.assertEqual(unit_ids, {
                "hydra://knowledge-unit/demo/adopt",
                "hydra://knowledge-unit/security/baseline",
            })

    def test_cached_context_parse_count_is_bounded_with_258_node_locators(self):
        """A warm cache hydrates only the selected policy/unit closure.

        The derived projection has the same 258 node locators as the v3
        decision fixture. The 256 unselected locators deliberately have no
        canonical files, so a whole-tree hydration fails immediately.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = paths_for(root)
            write_node(paths, "demo")
            selected = "demo/node-000"
            write_node(
                paths,
                selected,
                routes=(
                    "routes:\n  adopt:\n    use_when:\n      - adopt hydra repository\n"
                    f"    priority_units:\n      - hydra://knowledge-unit/{selected}/selected\n"
                    "    requires: []\n    avoid_by_default: []\n    verify: []\n    expand_when: []\n"
                ),
            )
            write_unit(paths, selected, "selected")
            db_path = root / ".hydra-framework.local/index/knowledge.db"
            db_path.parent.mkdir(parents=True)
            records = list(storage.build_knowledge_store(paths).iter_objects())
            records.extend(
                storage.StoredKnowledgeObject(
                    hydra_id=f"hydra://knowledge-node/demo/unselected-{number:03d}",
                    uid=f"unselected-{number:03d}", kind="knowledge-node",
                    path=f".hydra-framework/repo/knowledge/spaces/demo/unselected-{number:03d}/node.yaml",
                    node_id=f"demo/unselected-{number:03d}",
                )
                for number in range(256)
            )
            with sqlite3.connect(db_path) as connection:
                storage.write_sqlite_store(connection, storage.InMemoryKnowledgeStore(records))
            snapshot = knowledge_snapshot.KnowledgeSnapshot(paths, storage.SqliteKnowledgeStore.open(db_path))

            hydrated: list[str] = []
            hydrate = storage.hydrate_object

            def count_hydration(*args):
                hydrated.append(args[1].path)
                return hydrate(*args)

            request = _request(
                root, paths=paths, task="adopt hydra repository", node_values=(selected,),
                knowledge_snapshot=snapshot,
            )
            with (
                mock.patch("hydra_engine.knowledge.nodes.discover_knowledge_nodes", side_effect=AssertionError("whole tree")),
                mock.patch("hydra_engine.knowledge.storage.hydrate_object", side_effect=count_hydration),
                mock.patch("hydra_engine.knowledge.snapshot.hydrate_object", side_effect=count_hydration),
            ):
                output = context_providers.run_context_providers(request, include_families=("Knowledge",))

            self.assertEqual([item["node"] for item in output.nodes], [selected])
            self.assertEqual(
                {item["source"] for item in output.candidates if item["kind"] == "knowledge-unit"},
                {f"hydra://knowledge-unit/{selected}/selected"},
            )
            # selected leaf + its space ancestor + the required unit; permit
            # duplicate defensive hydration, never a whole-tree parse.
            self.assertLessEqual(len(hydrated), 4)
            self.assertEqual(
                set(hydrated),
                {
                    ".hydra-framework/repo/knowledge/spaces/demo/space.yaml",
                    ".hydra-framework/repo/knowledge/spaces/demo/node-000/node.yaml",
                    ".hydra-framework/repo/knowledge/spaces/demo/node-000/units/selected.md",
                },
            )

    def test_explicit_cache_locator_miss_abandons_the_operation_for_canonical_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._fixture(root)
            local = root / ".hydra-framework.local"
            search_index.build_index(paths, _resolver_paths(root), local)
            with sqlite3.connect(search_index.default_db_path(local)) as conn:
                conn.execute("DELETE FROM knowledge_objects WHERE node_id = 'demo'")
            output = context_providers.run_context_providers(
                _request(root, paths=paths, task="adopt hydra repository", node_values=("demo",)),
                include_families=("Knowledge",),
            )
            self.assertEqual(output.nodes[0]["node"], "demo")

    def test_warm_cache_path_routing_matches_source_only_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = paths_for(root)
            write_node(paths, "demo", keywords=("demo",))
            unit = write_unit(paths, "demo", "guide")
            _commit(root)
            local = root / ".hydra-framework.local"
            request = _request(
                root,
                paths=paths,
                task="demo",
                path_values=(unit.relative_to(root).as_posix(),),
            )

            with mock.patch("hydra_engine.knowledge.index_cache.query_store_disabled", return_value=True):
                source_output = context_providers.run_context_providers(request, include_families=("Knowledge",))

            search_index.build_index(paths, _resolver_paths(root), local)
            with (
                mock.patch(
                    "hydra_engine.knowledge.context_support.search_for_context_provider",
                    wraps=context_providers.context_support.search_for_context_provider,
                ) as search_provider,
                mock.patch(
                    "hydra_engine.knowledge.context_support.search",
                    wraps=context_providers.context_support.search,
                ) as search,
            ):
                cached_output = context_providers.run_context_providers(request, include_families=("Knowledge",))

            self.assertEqual(cached_output.nodes, source_output.nodes)
            self.assertEqual(cached_output.candidates, source_output.candidates)
            search_provider.assert_called_once()
            search.assert_called_once()
            self.assertTrue(search.call_args.kwargs["force_source"])


class RunContextProvidersTests(unittest.TestCase):
    def test_shared_search_runs_once_for_multiple_families(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request = _request(root, task="anything")
            with mock.patch(
                "hydra_engine.knowledge.context_support.search_for_context_provider",
                return_value=((), None, "source", None),
            ) as search:
                context_providers.run_context_providers(request, include_families=("Source", "Capability", "Work"))
            search.assert_called_once()

    def test_unknown_family_is_a_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = context_providers.run_context_providers(_request(Path(tmp)), include_families=("not-real",))
            self.assertIn("Unknown context-provider family: not-real", output.warnings)

    def test_unrelated_value_error_is_not_treated_as_cache_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = context_providers.ContextProvider(
                "Knowledge", lambda _request: (_ for _ in ()).throw(ValueError("unrelated"))
            )
            with mock.patch.dict(context_providers.PROVIDERS_BY_FAMILY, {"Knowledge": provider}):
                with self.assertRaisesRegex(ValueError, "unrelated"):
                    context_providers.run_context_providers(
                        _request(Path(tmp), knowledge_snapshot=object()), include_families=("Knowledge",)
                    )


class FingerprintCallCountTests(unittest.TestCase):
    """D20/D21 acceptance: one steady-state incremental
    `run_context_providers` operation (a single governed document changed
    since the last publish) costs exactly five `freshness.fingerprint`
    calls, down from six, while the closing revalidation remains a fresh,
    independent Git observation rather than a reused value."""

    def _fixture(self, root: Path):
        paths = paths_for(root, ("demo",))
        write_node(paths, "demo", keywords=("demo",))
        write_unit(paths, "demo", "guide")
        _commit(root)
        return paths

    def _one_document_incremental_setup(self, root: Path):
        paths = self._fixture(root)
        local = root / ".hydra-framework.local"
        resolver_paths = _resolver_paths(root)
        search_index.build_index(paths, resolver_paths, local)
        # One additional governed unit, committed, is exactly the single-
        # document incremental delta this task's benchmark measured.
        write_unit(paths, "demo", "second")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "commit", "-q", "-m", "incremental edit"], cwd=root, check=True)
        return paths, local

    def test_incremental_provider_operation_makes_exactly_five_fingerprint_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths, local = self._one_document_incremental_setup(root)

            real_fingerprint = index_cache.fingerprint
            calls: list = []
            with mock.patch(
                "hydra_engine.knowledge.index_cache.fingerprint",
                side_effect=lambda *a, **k: (calls.append(1), real_fingerprint(*a, **k))[1],
            ):
                output = context_providers.run_context_providers(
                    _request(root, paths=paths, task="demo"), include_families=("Knowledge",),
                )

            self.assertEqual(len(calls), 5)
            self.assertEqual(output.nodes[0]["node"], "demo")

    def test_final_cache_state_is_reused_only_for_the_opening_stamp(self):
        """The exact D20 boundary: the settled `Fresh` state that the
        incremental update produces is turned into the opening stamp with no
        extra Git read (`stamp_from_fresh`, not another `capture_stamp`), and
        that helper is used exactly once, for the opening pin only."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths, local = self._one_document_incremental_setup(root)

            with mock.patch.object(index_cache, "stamp_from_fresh", wraps=index_cache.stamp_from_fresh) as stamp_from_fresh:
                context_providers.run_context_providers(
                    _request(root, paths=paths, task="demo"), include_families=("Knowledge",),
                )
            stamp_from_fresh.assert_called_once()

    def test_closing_revalidation_is_the_one_remaining_capture_stamp_call(self):
        """`_capture_stamp` (the fresh, independent Git read) must still be
        called exactly once per operation -- for the closing revalidation
        only, since the opening pin is now satisfied from the reused settled
        state instead. Combined with the five-call count above, this proves
        the closing observation is a real fingerprint call, not skipped."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths, local = self._one_document_incremental_setup(root)
            with mock.patch(
                "hydra_engine.knowledge.context_providers._capture_stamp",
                wraps=context_providers._capture_stamp,
            ) as capture_stamp:
                context_providers.run_context_providers(
                    _request(root, paths=paths, task="demo"), include_families=("Knowledge",),
                )
            capture_stamp.assert_called_once()


class StampRevalidationTests(unittest.TestCase):
    """Phase 5: operation-scoped read-stamp propagation and final
    revalidation. `run_context_providers` pins one `index_cache.OperationStamp`
    across the whole operation and revalidates it once at the end; a stamp
    that moved mid-operation must discard the accumulated result and rerun
    canonically rather than publish a mix of two generations."""

    def _fixture(self, root: Path):
        paths = paths_for(root, ("demo",))
        write_node(paths, "demo", keywords=("demo",))
        write_unit(paths, "demo", "guide")
        _commit(root)
        return paths

    def _moved_stamp(self, real_stamp: index_cache.OperationStamp) -> index_cache.OperationStamp:
        # A different, non-existent publication path is enough to make the
        # stamp compare unequal without a real second publish.
        return dataclasses.replace(real_stamp, publication=real_stamp.publication.with_name("moved.db"))

    def test_publication_change_midoperation_reruns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._fixture(root)
            local = root / ".hydra-framework.local"
            search_index.build_index(paths, _resolver_paths(root), local)
            real_stamp = index_cache.capture_stamp(paths, local)
            self.assertIsNotNone(real_stamp.publication)
            moved_stamp = self._moved_stamp(real_stamp)

            with (
                mock.patch(
                    "hydra_engine.knowledge.context_providers._capture_stamp",
                    side_effect=[moved_stamp],
                ),
                mock.patch(
                    "hydra_engine.knowledge.context_support.search_for_context_provider",
                    wraps=context_providers.context_support.search_for_context_provider,
                ) as search_provider,
                mock.patch(
                    "hydra_engine.knowledge.context_support.search",
                    wraps=context_providers.context_support.search,
                ) as search,
            ):
                output = context_providers.run_context_providers(
                    _request(root, paths=paths, task="demo"), include_families=("Knowledge",),
                )

            search_provider.assert_called_once()
            search.assert_called_once()
            self.assertTrue(search.call_args.kwargs["force_source"])
            self.assertEqual(output.nodes[0]["node"], "demo")

    def test_no_mixed_cache_and_source_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self._fixture(root)
            local = root / ".hydra-framework.local"
            search_index.build_index(paths, _resolver_paths(root), local)
            real_stamp = index_cache.capture_stamp(paths, local)
            moved_stamp = self._moved_stamp(real_stamp)
            request = _request(root, paths=paths, task="demo")

            with mock.patch("hydra_engine.knowledge.index_cache.query_store_disabled", return_value=True):
                source_output = context_providers.run_context_providers(request, include_families=("Knowledge",))

            with mock.patch(
                "hydra_engine.knowledge.context_providers._capture_stamp",
                side_effect=[moved_stamp],
            ):
                racy_output = context_providers.run_context_providers(request, include_families=("Knowledge",))

            # The mid-operation move must discard every candidate/node
            # gathered against the pinned (now-stale) publication -- the
            # rerun result must match a pure canonical run exactly, never a
            # mix of the two generations.
            self.assertEqual(racy_output.nodes, source_output.nodes)
            self.assertEqual(racy_output.candidates, source_output.candidates)


if __name__ == "__main__":
    unittest.main()
