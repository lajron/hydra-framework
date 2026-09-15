"""Mirror tests for `hydra_engine.knowledge.search_index`."""

from __future__ import annotations

import sys
import os
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.knowledge import index_collection, packages, search_index  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402
from v3_fixtures import add_documentation_object  # noqa: E402


def _paths(root: Path) -> packages.ContextCompilerPaths:
    return packages.ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")


def _resolver(root: Path) -> ObjectLocations:
    hydra = root / ".hydra-framework"
    return ObjectLocations(root=root, hydra=hydra, local=root / ".hydra-framework.local", personal_tasks_rel="tasks/personal", object_registry=hydra / "cognition/graph/registry.yaml")


def _commit(root: Path) -> None:
    for command in (
        ("git", "init"),
        ("git", "config", "user.email", "tests@example.invalid"),
        ("git", "config", "user.name", "Tests"),
        ("git", "add", "-A"),
        ("git", "commit", "-m", "fixture"),
    ):
        subprocess.run(command, cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _repo() -> Path:
    root = Path(tempfile.mkdtemp(prefix="search-index-"))
    pkg = root / ".hydra-framework/repo/knowledge/knowledge-packages/example"
    pkg.mkdir(parents=True)
    (pkg / "overview.md").write_text(
        "---\nhydra_id: hydra://knowledge-package/example\nuid: example-uid\nschema_version: 3\n"
        "kind: knowledge-package\ntitle: Example Package\nstatus: active\nscope: repo-local\nowners:\n  team: tests\n"
        "relations: []\nprovenance:\n  sources: []\n---\n# Example Overview\nhydra routing adapter exports\n",
        encoding="utf-8",
    )
    (pkg / "routing.yaml").write_text(
        "schema: hydra-framework.package-routing.v2\n"
        "package: example\n"
        "title: Example Package\n"
        "keywords:\n  - adapter exports\n"
        "routes:\n  fix_provider_surface:\n    use_when:\n      - generated provider files drift\n",
        encoding="utf-8",
    )
    unit_doc = root / ".hydra-framework/repo/knowledge-units/0013-routing.md"
    unit_doc.parent.mkdir(parents=True)
    unit_doc.write_text(
        "---\nhydra_id: hydra://knowledge-unit/0013-routing\nuid: routing-uid\nschema_version: 3\n"
        "kind: knowledge-unit\ntitle: Routing Unit\nstatus: active\nscope: repo-local\nowners:\n  team: tests\n"
        "relations:\n  - hydra://knowledge-package/example\nprovenance:\n  sources: []\n---\n# 0013: Routing\nExact unit body\n",
        encoding="utf-8",
    )
    registry = root / ".hydra-framework/cognition/graph/registry.yaml"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        "schema: hydra-framework.object-registry.v1\n"
        "generated_by: hydra.py ref index\n"
        "objects:\n"
        "  hydra://knowledge-package/example:\n"
        "    path: .hydra-framework/repo/knowledge/knowledge-packages/example/overview.md\n"
        "    kind: knowledge-package\n"
        "    title: Example Package\n"
        "    aliases:\n      - hydra://alias/example\n"
        "    relations: []\n"
        "  hydra://knowledge-unit/0013-routing:\n"
        "    path: .hydra-framework/repo/knowledge-units/0013-routing.md\n"
        "    kind: knowledge-unit\n"
        "    title: Routing Unit\n"
        "    aliases: []\n"
        "    relations:\n      - hydra://knowledge-package/example\n",
        encoding="utf-8",
    )
    _commit(root)
    return root


class SearchIndexTests(unittest.TestCase):
    def test_documentation_is_suppressed_for_ordinary_queries_in_source_and_sqlite(self):
        root = add_documentation_object(_repo())
        paths, resolver, local = _paths(root), _resolver(root), root / ".hydra-framework.local"
        source_results, _features, source = search_index.search(
            "Routing Guide", paths=paths, resolver_paths=resolver, local=local, force_source=True,
        )
        self.assertEqual(source, "source")
        self.assertFalse(any(result.document.hydra_id == "hydra://documentation/wiki" for result in source_results))

        search_index.build_index(paths, resolver, local)
        sqlite_results, _features, source = search_index.search(
            "human documentation", paths=paths, resolver_paths=resolver, local=local,
        )
        self.assertEqual(source, "sqlite")
        self.assertFalse(any(result.document.hydra_id == "hydra://documentation/wiki" for result in sqlite_results))

    def test_suppressed_documentation_does_not_consume_result_limit(self):
        root = add_documentation_object(_repo())
        results, _features, _source = search_index.search(
            "routing", paths=_paths(root), resolver_paths=_resolver(root), local=root / ".hydra-framework.local", limit=1,
        )
        self.assertEqual(len(results), 1)
        self.assertNotEqual(results[0].document.hydra_id, "hydra://documentation/wiki")

    def test_documentation_id_alias_and_path_are_explicit_search_authority(self):
        root = add_documentation_object(_repo())
        paths, resolver, local = _paths(root), _resolver(root), root / ".hydra-framework.local"
        search_index.build_index(paths, resolver, local)
        for query, path_refs in (
            ("hydra://documentation/wiki", ()),
            ("hydra://alias/wiki", ()),
            ("anything", ("project-wiki/wiki.md",)),
        ):
            with self.subTest(query=query, path_refs=path_refs):
                results, _features, _source = search_index.search(
                    query, paths=paths, resolver_paths=resolver, local=local, path_refs=path_refs,
                )
                self.assertTrue(results)
                self.assertEqual(results[0].document.hydra_id, "hydra://documentation/wiki")
    def test_same_stat_cache_mutation_abandons_cached_routing_candidate(self):
        root = Path(tempfile.mkdtemp(prefix="search-index-v3-"))
        hydra = root / ".hydra-framework"
        knowledge = hydra / "repo/knowledge"
        node = knowledge / "spaces/demo/space.yaml"
        node.parent.mkdir(parents=True)
        (knowledge / "spaces.yaml").write_text(
            "schema: hydra-framework.knowledge-spaces.v1\nmax_depth: 4\nspaces:\n  - demo\n", encoding="utf-8",
        )
        node.write_text(
            "schema: hydra-framework.knowledge-node.v1\nnode: demo\nhydra_id: hydra://knowledge-space/demo\n"
            "uid: node-uid\nschema_version: 3\nkind: knowledge-space\ntitle: Demo\nstatus: active\n"
            "scope: repo-local\nowners:\n  team: test\nrelations: []\nprovenance:\n  sources: []\n"
            "routable: true\nkeywords:\n  - old-keyword\n",
            encoding="utf-8",
        )
        _commit(root)
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)
        original = node.stat()
        node.write_text(node.read_text(encoding="utf-8").replace("old-keyword", "new-keyword"), encoding="utf-8")
        self.assertEqual(node.stat().st_size, original.st_size)
        os.utime(node, ns=(original.st_atime_ns, original.st_mtime_ns))

        results, _features, source = search_index.search(
            "old-keyword", paths=_paths(root), resolver_paths=_resolver(root), local=local,
        )

        self.assertEqual(source, "sqlite")
        self.assertEqual(results, [])

    def test_exact_lookup_bypasses_lexical_ranking(self):
        root = _repo()
        results, _features, _source = search_index.search(
            "hydra://knowledge-unit/0013-routing", paths=_paths(root), resolver_paths=_resolver(root), local=root / ".hydra-framework.local"
        )
        self.assertEqual(results[0].channel, "exact")
        self.assertEqual(results[0].document.hydra_id, "hydra://knowledge-unit/0013-routing")

    def test_exact_lookup_includes_command_names(self):
        root = _repo()
        results, _features, _source = search_index.search(
            "validate", paths=_paths(root), resolver_paths=_resolver(root), local=root / ".hydra-framework.local", command_ids=("validate",)
        )
        self.assertEqual(results[0].channel, "exact")
        self.assertEqual(results[0].document.kind, "command")

    def test_sqlite_probe_reports_capabilities_without_raising(self):
        features = search_index.probe_sqlite_features()
        self.assertIsInstance(features.fts5, bool)
        self.assertIsInstance(features.trigram, bool)

    def test_negative_fts_probe_falls_back_to_substring_results(self):
        root = _repo()
        search_index.build_index(_paths(root), _resolver(root), root / ".hydra-framework.local")
        with mock.patch.object(search_index, "probe_sqlite_features", return_value=search_index.SqliteFeatures(False, False, "disabled")):
            results, features, source = search_index.search(
                "generated files drift", paths=_paths(root), resolver_paths=_resolver(root), local=root / ".hydra-framework.local"
            )
        self.assertFalse(features.fts5)
        self.assertEqual(source, "sqlite")
        self.assertTrue(results)
        self.assertTrue(all(result.channel in {"substring", "path-route"} for result in results))

    def test_persisted_documents_load_in_rowid_order(self):
        root = _repo()
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local, ("validate",))
        docs = search_index.collect_search_documents(
            _paths(root), _resolver(root), ("validate",), content_ids=search_index.fingerprint(root),
        )
        loaded = search_index._load_documents(search_index.default_db_path(local))
        self.assertEqual([doc.key for doc in loaded], [doc.key for doc in docs])

    def test_build_index_uses_the_persistent_wal_database(self):
        root = _repo()
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)
        db_path = search_index.default_db_path(local)
        self.assertIsNotNone(db_path)
        assert db_path is not None
        with sqlite3.connect(db_path) as conn:
            self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal")

    def test_invalid_private_database_falls_back_to_source(self):
        root = _repo()
        index_dir = root / ".hydra-framework.local/index"
        index_dir.mkdir(parents=True)
        (index_dir / "knowledge-current.json").write_text("not json", encoding="utf-8")
        results, _features, source = search_index.search(
            "adapter exports", paths=_paths(root), resolver_paths=_resolver(root), local=root / ".hydra-framework.local"
        )
        self.assertEqual(source, "sqlite")
        self.assertTrue(results)

    def test_index_status_reports_missing_fresh_and_stale(self):
        root = _repo()
        local = root / ".hydra-framework.local"
        self.assertEqual(search_index.index_status(_paths(root), _resolver(root), local), "missing")

        search_index.build_index(_paths(root), _resolver(root), local)
        self.assertEqual(search_index.index_status(_paths(root), _resolver(root), local), "fresh")

        (root / ".hydra-framework/repo/knowledge/knowledge-packages/example/overview.md").write_text(
            "# Example Overview\nfresh phrase after stale index\n", encoding="utf-8"
        )
        self.assertEqual(search_index.index_status(_paths(root), _resolver(root), local), "stale")

    def test_stale_private_database_falls_back_to_source(self):
        root = _repo()
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)
        (root / ".hydra-framework/repo/knowledge/knowledge-packages/example/overview.md").write_text(
            "# Example Overview\nfresh phrase after stale index\n", encoding="utf-8"
        )
        results, _features, source = search_index.search(
            "fresh phrase", paths=_paths(root), resolver_paths=_resolver(root), local=local
        )
        self.assertEqual(source, "sqlite")
        self.assertIn("fresh phrase", results[0].document.body)

    def test_fresh_store_does_not_recollect_the_corpus(self):
        root = _repo()
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)
        with mock.patch.object(search_index, "collect_search_documents", side_effect=AssertionError("source parse")):
            results, _features, source = search_index.search(
                "adapter exports", paths=_paths(root), resolver_paths=_resolver(root), local=local,
            )
        self.assertEqual(source, "sqlite")
        self.assertTrue(results)

    def test_clean_read_does_not_walk_directories(self):
        root = _repo()
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)
        with mock.patch.object(Path, "rglob", side_effect=AssertionError("directory walk")):
            results, _features, source = search_index.search(
                "adapter exports", paths=_paths(root), resolver_paths=_resolver(root), local=local,
            )
        self.assertEqual(source, "sqlite")
        self.assertTrue(results)

    def test_incremental_update_reparses_only_changed_document(self):
        root = _repo()
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)
        overview = root / ".hydra-framework/repo/knowledge/knowledge-packages/example/overview.md"
        overview.write_text(overview.read_text(encoding="utf-8") + "incremental phrase\n", encoding="utf-8")
        with mock.patch.object(index_collection, "_document_for_path", wraps=index_collection._document_for_path) as parse:
            results, _features, source = search_index.search(
                "incremental phrase", paths=_paths(root), resolver_paths=_resolver(root), local=local,
            )
        self.assertEqual(source, "sqlite")
        self.assertEqual(parse.call_count, 1)
        self.assertIn("incremental phrase", results[0].document.body)

    def test_correctness_holds_with_all_hooks_removed(self):
        """Phase 6 acceptance: hooks are never load-bearing for correctness.

        Point `core.hooksPath` at hooks that always fail for every trigger
        Phase 6 adds (`post-commit`/`post-checkout`/`post-merge`/
        `post-rewrite`) -- strictly harder than hooks being merely absent,
        since these actually run and exit nonzero -- then perform a real
        `git commit` and confirm `search()` still detects and repairs the
        resulting staleness entirely on its own. `search()` never invokes a
        hook; its own guarded fingerprint comparison is the whole correctness
        mechanism, so a hook doing nothing here should change nothing but
        latency.
        """
        root = _repo()
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)

        failing_hooks = root / "broken-hooks"
        failing_hooks.mkdir()
        for name in ("post-commit", "post-checkout", "post-merge", "post-rewrite"):
            hook = failing_hooks / name
            hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            hook.chmod(0o755)
        subprocess.run(
            ["git", "config", "core.hooksPath", str(failing_hooks)],
            cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

        overview = root / ".hydra-framework/repo/knowledge/knowledge-packages/example/overview.md"
        overview.write_text(overview.read_text(encoding="utf-8") + "hooks removed phrase\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        commit = subprocess.run(["git", "commit", "-m", "edit"], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(commit.returncode, 0, commit.stderr)

        with mock.patch.object(index_collection, "_document_for_path", wraps=index_collection._document_for_path) as parse:
            results, _features, source = search_index.search(
                "hooks removed phrase", paths=_paths(root), resolver_paths=_resolver(root), local=local,
            )
        self.assertEqual(source, "sqlite")
        self.assertEqual(parse.call_count, 1)
        self.assertIn("hooks removed phrase", results[0].document.body)

    def test_command_ids_change_forces_full_rebuild(self):
        root = _repo()
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)
        with mock.patch.object(search_index, "build_index", wraps=search_index.build_index) as rebuild:
            results, _features, source = search_index.search(
                "validate", paths=_paths(root), resolver_paths=_resolver(root), local=local, command_ids=("validate",),
            )
        self.assertEqual(source, "sqlite")
        rebuild.assert_called_once()
        self.assertEqual(results[0].document.kind, "command")

    def test_schema_change_forces_full_rebuild(self):
        root = _repo()
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)
        with mock.patch.object(search_index, "SCHEMA_VERSION", "hydra-framework.knowledge-store.v5"), mock.patch.object(
            search_index, "build_index", wraps=search_index.build_index,
        ) as rebuild:
            _results, _features, source = search_index.search(
                "adapter exports", paths=_paths(root), resolver_paths=_resolver(root), local=local,
            )
        self.assertEqual(source, "sqlite")
        rebuild.assert_called_once()

    def test_explicit_selector_miss_reruns_canonically(self):
        root = _repo()
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)
        db_path = search_index.default_db_path(local)
        assert db_path is not None
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE documents SET hydra_id = '' WHERE hydra_id = 'hydra://knowledge-package/example'")
        results, _features, source = search_index.search(
            "hydra://knowledge-package/example", paths=_paths(root), resolver_paths=_resolver(root), local=local,
        )
        self.assertEqual(source, "source")
        self.assertEqual(results[0].document.hydra_id, "hydra://knowledge-package/example")

    def test_collect_search_documents_discovers_nodes_once_not_per_document(self):
        root = _repo()
        with mock.patch.object(index_collection, "discover_knowledge_nodes", wraps=index_collection.discover_knowledge_nodes) as discover:
            docs = search_index.collect_search_documents(_paths(root), _resolver(root))
        self.assertGreater(len(docs), 1)
        self.assertEqual(discover.call_count, 1)

    def test_query_store_escape_hatch_forces_canonical_fallback(self):
        root = _repo()
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)
        with mock.patch.dict("os.environ", {"HYDRA_QUERY_STORE": "off"}):
            _results, _features, source = search_index.search(
                "adapter exports", paths=_paths(root), resolver_paths=_resolver(root), local=local,
            )
        self.assertEqual(source, "source")

    def test_explicit_path_hint_materializes_existing_file_outside_default_corpus(self):
        root = _repo()
        path = root / "project-wiki/example.md"
        path.parent.mkdir()
        path.write_text("# Wiki Page\noutside default corpus\n", encoding="utf-8")
        results, _features, _source = search_index.search(
            "anything", paths=_paths(root), resolver_paths=_resolver(root), local=root / ".hydra-framework.local",
            path_refs=("project-wiki/example.md",),
        )
        self.assertEqual(results[0].channel, "exact")
        self.assertEqual(results[0].document.path, "project-wiki/example.md")

    def test_ranking_is_lexicographic_by_channel_tier(self):
        exact = search_index.SearchResult(search_index.SearchDocument("a", "hydra://knowledge-unit/0013-routing", (), "a.md", "knowledge-unit", "", "A", (), (), (), (), "alpha", ()), "exact", 0)
        lexical = search_index.SearchResult(search_index.SearchDocument("b", "", (), "b.md", "file", "", "B", (), (), (), (), "alpha alpha alpha", ()), "substring", -3)
        self.assertEqual(search_index.sorted_results([lexical, exact]), [exact, lexical])


class SearchForContextProviderTests(unittest.TestCase):
    """D20: the internal context-provider search entry point may return a
    reusable opening `OperationStamp` only when the settled cache state is
    `Fresh` and the search actually answered from that publication; every
    other case must return `None` so the caller pins its own fresh stamp."""

    def test_fresh_cache_hit_returns_a_stamp_matching_a_fresh_capture(self):
        root = _repo()
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)
        results, _features, source, stamp = search_index.search_for_context_provider(
            "adapter exports", paths=_paths(root), resolver_paths=_resolver(root), local=local,
        )
        self.assertEqual(source, "sqlite")
        self.assertTrue(results)
        self.assertIsNotNone(stamp)
        from hydra_engine.knowledge import index_cache
        self.assertEqual(stamp, index_cache.capture_stamp(_paths(root), local))

    def test_incremental_update_settling_fresh_shares_final_state_as_stamp(self):
        """The exact D20 scenario: a single-document incremental update
        settles to `Fresh`, and the stamp returned is built from that same
        settled state, never from a fresh independent Git read."""
        root = _repo()
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)
        overview = root / ".hydra-framework/repo/knowledge/knowledge-packages/example/overview.md"
        overview.write_text(overview.read_text(encoding="utf-8") + "incremental phrase\n", encoding="utf-8")
        from hydra_engine.knowledge import index_cache

        with mock.patch.object(index_cache, "stamp_from_fresh", wraps=index_cache.stamp_from_fresh) as stamp_from_fresh:
            results, _features, source, stamp = search_index.search_for_context_provider(
                "incremental phrase", paths=_paths(root), resolver_paths=_resolver(root), local=local,
            )
        self.assertEqual(source, "sqlite")
        self.assertTrue(results)
        stamp_from_fresh.assert_called_once()
        (settled_state,), _kwargs = stamp_from_fresh.call_args
        self.assertIsInstance(settled_state, index_cache.Fresh)
        self.assertEqual(stamp, index_cache.OperationStamp(settled_state.fingerprint, settled_state.db_path, settled_state.generation))

    def test_force_source_never_shares_a_stamp(self):
        """`search_for_context_provider` never itself forces source, but the
        stamp-sharing rule it applies (`state is Fresh and source == "sqlite"`)
        must reject a forced-source outcome even though `state` may still be
        a stale `Fresh` object left over from a prior settle."""
        root = _repo()
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)
        outcome = search_index._search_outcome(
            "adapter exports", paths=_paths(root), resolver_paths=_resolver(root), local=local, force_source=True,
        )
        self.assertEqual(outcome.source, "source")
        from hydra_engine.knowledge import index_cache
        self.assertNotIsInstance(outcome.state, index_cache.Fresh)

    def test_failed_update_never_shares_a_stamp(self):
        root = _repo()
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)
        overview = root / ".hydra-framework/repo/knowledge/knowledge-packages/example/overview.md"
        overview.write_text(overview.read_text(encoding="utf-8") + "incremental phrase\n", encoding="utf-8")
        with mock.patch.object(search_index, "_update_index", side_effect=OSError("update failed")):
            results, _features, source, stamp = search_index.search_for_context_provider(
                "incremental phrase", paths=_paths(root), resolver_paths=_resolver(root), local=local,
            )
        self.assertEqual(source, "source")
        self.assertIsNone(stamp)

    def test_reentrant_canonical_retry_never_shares_a_stamp(self):
        root = _repo()
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)
        with mock.patch.object(search_index, "_hydrate_cached_candidates", return_value=None):
            results, _features, source, stamp = search_index.search_for_context_provider(
                "adapter exports", paths=_paths(root), resolver_paths=_resolver(root), local=local,
            )
        self.assertEqual(source, "source")
        self.assertTrue(results)
        self.assertIsNone(stamp)

    def test_public_search_return_shape_is_unchanged(self):
        root = _repo()
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)
        outcome = search_index.search(
            "adapter exports", paths=_paths(root), resolver_paths=_resolver(root), local=local,
        )
        self.assertEqual(len(outcome), 3)
        results, features, source = outcome
        self.assertTrue(results)
        self.assertEqual(source, "sqlite")
        self.assertIsInstance(features, search_index.SqliteFeatures)


class LexicalNarrowingDifferentialTests(unittest.TestCase):
    """Phase 3 acceptance (P13/D10): the FTS5-narrowed candidate path must
    return byte-identical `SearchResult` lists, in the same order, to the old
    whole-corpus scan it replaces, across every query channel -- and the
    substring-scan fallback for a host without the trigram tokenizer must
    match both of them too."""

    QUERIES_AND_CHANNELS = (
        ("hydra://knowledge-unit/0013-routing", "exact"),  # exact id
        ("Please read .hydra-framework/repo/knowledge-units/0013-routing.md", "exact"),  # exact path
        ("Example Package", "exact"),  # exact slug
        ("knowledge-packages", "path-route"),  # path-route
        ("adapter exports", "substring"),  # substring
        ("no match anywhere for this text string zz", None),  # empty
    )

    def _search(self, root, query, *, narrow: bool):
        paths, resolver, local = _paths(root), _resolver(root), root / ".hydra-framework.local"
        if narrow:
            return search_index.search(query, paths=paths, resolver_paths=resolver, local=local)
        with mock.patch.object(search_index, "_narrowed_documents", return_value=None):
            return search_index.search(query, paths=paths, resolver_paths=resolver, local=local)

    def test_narrowed_path_matches_whole_corpus_scan_across_channels(self):
        root = _repo()
        search_index.build_index(_paths(root), _resolver(root), root / ".hydra-framework.local")
        for query, channel in self.QUERIES_AND_CHANNELS:
            with self.subTest(query=query):
                narrowed_results, _narrowed_features, narrowed_source = self._search(root, query, narrow=True)
                full_results, _full_features, full_source = self._search(root, query, narrow=False)
                self.assertEqual(narrowed_source, "sqlite")
                self.assertEqual(full_source, "sqlite")
                self.assertEqual(narrowed_results, full_results)
                if channel is None:
                    self.assertEqual(narrowed_results, [])
                else:
                    self.assertTrue(narrowed_results)
                    self.assertEqual(narrowed_results[0].channel, channel)

    def test_forced_no_fts5_substring_fallback_matches_the_narrowed_and_full_scan_results(self):
        """A host without the trigram tokenizer never narrows at all (its
        index is built without an FTS5 table); its whole-corpus substring
        scan must still agree with both the narrowed and forced-full results
        a trigram host produces for the same corpus and query."""
        root = _repo()
        with mock.patch.object(search_index, "probe_sqlite_features", return_value=search_index.SqliteFeatures(False, False)):
            search_index.build_index(_paths(root), _resolver(root), root / ".hydra-framework.local")
        for query, channel in self.QUERIES_AND_CHANNELS:
            with self.subTest(query=query):
                results, _features, source = search_index.search(
                    query, paths=_paths(root), resolver_paths=_resolver(root), local=root / ".hydra-framework.local",
                )
                self.assertEqual(source, "sqlite")
                if channel is None:
                    self.assertEqual(results, [])
                else:
                    self.assertTrue(results)
                    self.assertEqual(results[0].channel, channel)
        # And the same corpus built *with* trigram support must reach the
        # identical answer for the lexical-channel query, proving the
        # fallback is not merely plausible but actually correct.
        trigram_root = _repo()
        search_index.build_index(_paths(trigram_root), _resolver(trigram_root), trigram_root / ".hydra-framework.local")
        substring_query = "adapter exports"
        no_fts_results, _f1, _s1 = search_index.search(
            substring_query, paths=_paths(root), resolver_paths=_resolver(root), local=root / ".hydra-framework.local",
        )
        trigram_results, _f2, _s2 = search_index.search(
            substring_query, paths=_paths(trigram_root), resolver_paths=_resolver(trigram_root), local=trigram_root / ".hydra-framework.local",
        )
        self.assertEqual(
            [(r.channel, r.document.hydra_id, r.document.path, r.rank, r.graph_count) for r in no_fts_results],
            [(r.channel, r.document.hydra_id, r.document.path, r.rank, r.graph_count) for r in trigram_results],
        )

    def test_reported_mode_matches_what_the_index_actually_contains(self):
        root = _repo()
        search_index.build_index(_paths(root), _resolver(root), root / ".hydra-framework.local")
        self.assertEqual(search_index.lexical_mode(root / ".hydra-framework.local"), "fts5-trigram")

        fallback_root = _repo()
        with mock.patch.object(search_index, "probe_sqlite_features", return_value=search_index.SqliteFeatures(False, False)):
            search_index.build_index(_paths(fallback_root), _resolver(fallback_root), fallback_root / ".hydra-framework.local")
        self.assertEqual(search_index.lexical_mode(fallback_root / ".hydra-framework.local"), "substring-scan")

    def test_reported_mode_with_no_index_yet_is_substring_scan(self):
        root = _repo()
        self.assertEqual(search_index.lexical_mode(root / ".hydra-framework.local"), "substring-scan")


if __name__ == "__main__":
    unittest.main()
