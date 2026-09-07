from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from hydra_engine.commands.knowledge_migration import command_migrate_v2


class KnowledgeMigrationCommandTests(unittest.TestCase):
    def test_dry_run_writes_review_manifest(self):
        root = Path(tempfile.mkdtemp())
        plan = SimpleNamespace(manifest={"status": "planned", "plan_digest": "sha256:test", "unresolved": []})
        ctx = SimpleNamespace(root=root)
        args = argparse.Namespace(apply=None, output="review.json")
        with mock.patch("hydra_engine.commands.knowledge_migration.migration_v2.build_plan", return_value=plan), mock.patch("hydra_engine.commands.knowledge_migration.migration_format.write_review_manifest") as write:
            self.assertEqual(command_migrate_v2(args, ctx), 0)
        write.assert_called_once_with(plan.manifest, root / "review.json")


if __name__ == "__main__":
    unittest.main()
