from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hydra_engine.knowledge import migration_git


class MigrationGitTests(unittest.TestCase):
    def test_changed_checkpoint_and_dirty_tree_fail(self):
        root = Path(tempfile.mkdtemp())
        with mock.patch.object(migration_git, "checkpoint", return_value="new"):
            with self.assertRaisesRegex(ValueError, "checkpoint commit changed"):
                migration_git.require_clean(root, "old")
        with mock.patch.object(migration_git, "checkpoint", return_value="same"), mock.patch.object(migration_git, "_output", return_value=" M file"):
            with self.assertRaisesRegex(ValueError, "not clean"):
                migration_git.require_clean(root, "same")


if __name__ == "__main__":
    unittest.main()
