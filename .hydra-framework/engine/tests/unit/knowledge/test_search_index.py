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
        with mock.patch.object(search_index, "SCHEMA_VERSION", "hydra-framework.knowledge-store.v4"), mock.patch.object(
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


if __name__ == "__main__":
    unittest.main()
