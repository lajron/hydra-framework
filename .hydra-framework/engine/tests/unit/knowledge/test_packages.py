"""Mirror test for the shared context-compiler path bundle."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hydra_engine.knowledge.packages import ContextCompilerPaths


class ContextCompilerPathsTests(unittest.TestCase):
    def test_hydra_script_is_derived_from_the_hydra_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hydra = root / ".hydra-framework"
            paths = ContextCompilerPaths(root=root, hydra=hydra)
            self.assertEqual(paths.hydra_script(), hydra / "scripts/hydra.py")


if __name__ == "__main__":
    unittest.main()
