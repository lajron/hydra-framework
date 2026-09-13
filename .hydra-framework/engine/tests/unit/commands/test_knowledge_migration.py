from __future__ import annotations

import argparse
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from hydra_engine.commands.knowledge_migration import KNOWLEDGE_WRITE_LOCK_REL, command_migrate_v2, refresh_knowledge_index
from hydra_engine.knowledge.packages import ContextCompilerPaths
from hydra_engine.knowledge import search_index
from hydra_engine.objects.discovery import ObjectLocations
from hydra_engine.ports import lock as lock_port


class KnowledgeMigrationCommandTests(unittest.TestCase):
    def test_dry_run_writes_review_manifest(self):
        root = Path(tempfile.mkdtemp())
        plan = SimpleNamespace(manifest={"status": "planned", "plan_digest": "sha256:test", "unresolved": []})
        ctx = SimpleNamespace(root=root)
        args = argparse.Namespace(apply=None, output="review.json")
        with mock.patch("hydra_engine.commands.knowledge_migration.migration_v2.build_plan", return_value=plan), mock.patch("hydra_engine.commands.knowledge_migration.migration_format.write_review_manifest") as write:
            self.assertEqual(command_migrate_v2(args, ctx), 0)
        write.assert_called_once_with(plan.manifest, root / "review.json")

    def test_apply_holds_quiescence_lock_around_apply_reviewed_plan(self):
        """The multi-file write this Phase 6 bracket protects: while
        `migration_v2.apply_reviewed_plan` is writing and deleting an
        arbitrary number of governed files with no atomic worktree boundary
        between them, a concurrent hook-triggered `refresh_knowledge_index`
        must find `KNOWLEDGE_WRITE_LOCK_REL` contended, not free."""
        root = Path(tempfile.mkdtemp())
        lock_path = root / KNOWLEDGE_WRITE_LOCK_REL
        checked = []

        def fake_apply(applied_root, applied_reviewed):
            checked.append(True)
            with self.assertRaises(lock_port.LockUnavailableError):
                with lock_port.try_acquire(lock_path, timeout=0.0):
                    pass
            return SimpleNamespace(manifest={"packages": [], "checkpoint_commit": "abc"})

        ctx = SimpleNamespace(
            root=root, command_ids=(), local=root / ".hydra-framework.local",
            resolver_paths=lambda: None, context_compiler_paths=lambda: None,
        )
        args = argparse.Namespace(apply="review.json")
        with mock.patch("hydra_engine.commands.knowledge_migration.migration_format.load_review_manifest", return_value={}), \
                mock.patch("hydra_engine.commands.knowledge_migration.migration_v2.apply_reviewed_plan", side_effect=fake_apply), \
                mock.patch("hydra_engine.commands.knowledge_migration.references.command_ref_index", return_value=SimpleNamespace(exit_code=0)), \
                mock.patch("hydra_engine.commands.knowledge_migration.search_index.build_index", return_value=(0, None)):
            result = command_migrate_v2(args, ctx)
        self.assertEqual(result, 0)
        self.assertTrue(checked)
        # The lock is released once the write window closes.
        with lock_port.try_acquire(lock_path, timeout=0.0):
            pass


def _paths(root: Path) -> ContextCompilerPaths:
    return ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")


def _resolver(root: Path) -> ObjectLocations:
    hydra = root / ".hydra-framework"
    return ObjectLocations(root=root, hydra=hydra, local=root / ".hydra-framework.local", personal_tasks_rel="tasks/personal", object_registry=hydra / "cognition/graph/registry.yaml")


def _seed_governed_doc(root: Path) -> None:
    # `knowledge-packages` rather than `knowledge/spaces`: a bare file under
    # `spaces/` is validated as a v3 node with ancestors on cache hydration,
    # which this minimal fixture (no space.yaml, no registry) does not have.
    doc = root / ".hydra-framework/repo/knowledge/knowledge-packages/example/overview.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("# Example\nrefresh phrase\n", encoding="utf-8")


class RefreshKnowledgeIndexTests(unittest.TestCase):
    def test_builds_when_absent(self):
        root = Path(tempfile.mkdtemp())
        _seed_governed_doc(root)
        local = root / ".hydra-framework.local"
        self.assertIsNone(search_index.default_db_path(local))
        outcome = refresh_knowledge_index(_paths(root), _resolver(root), local)
        self.assertIsNotNone(outcome)
        self.assertIsNotNone(search_index.default_db_path(local))

    def test_backs_off_while_lock_is_held(self):
        root = Path(tempfile.mkdtemp())
        _seed_governed_doc(root)
        local = root / ".hydra-framework.local"
        with lock_port.acquire(root / KNOWLEDGE_WRITE_LOCK_REL):
            outcome = refresh_knowledge_index(_paths(root), _resolver(root), local)
        self.assertIsNone(outcome)
        self.assertIsNone(search_index.default_db_path(local))

    def test_warms_an_already_published_index_via_search_without_rebuilding(self):
        root = Path(tempfile.mkdtemp())
        _seed_governed_doc(root)
        for command in (
            ("git", "init"),
            ("git", "config", "user.email", "tests@example.invalid"),
            ("git", "config", "user.name", "Tests"),
            ("git", "add", "-A"),
            ("git", "commit", "-m", "seed"),
        ):
            subprocess.run(command, cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        local = root / ".hydra-framework.local"
        search_index.build_index(_paths(root), _resolver(root), local)

        overview = root / ".hydra-framework/repo/knowledge/knowledge-packages/example/overview.md"
        overview.write_text(overview.read_text(encoding="utf-8") + "warmed phrase\n", encoding="utf-8")

        with mock.patch.object(search_index, "build_index", wraps=search_index.build_index) as rebuild:
            outcome = refresh_knowledge_index(_paths(root), _resolver(root), local)
        rebuild.assert_not_called()
        self.assertIsNone(outcome)

        results, _features, source = search_index.search(
            "warmed phrase", paths=_paths(root), resolver_paths=_resolver(root), local=local,
        )
        self.assertEqual(source, "sqlite")
        self.assertIn("warmed phrase", results[0].document.body)


if __name__ == "__main__":
    unittest.main()
