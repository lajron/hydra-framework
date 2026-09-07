"""Mirror test for `hydra_engine.commands.knowledge_fingerprint`."""

from __future__ import annotations

import argparse
import contextlib
import io as stdlib_io
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.commands import knowledge_fingerprint  # noqa: E402
from hydra_engine.documents.digests import normalized_digest  # noqa: E402
from hydra_engine.documents.frontmatter_blocks import markdown_frontmatter  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402
from v3_fixtures import paths_for, write_node, write_unit  # noqa: E402


def _paths() -> ContextCompilerPaths:
    root = Path(tempfile.mkdtemp(prefix="commands-knowledge-fingerprint-"))
    return ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")


def _seed_unit(paths: ContextCompilerPaths) -> tuple[Path, Path]:
    source = paths.root / "source.py"
    source.write_text("x = 1\n", encoding="utf-8")
    paths_for(paths.root, ("example",))
    write_node(paths, "example")
    unit_path = write_unit(paths, "example", "demo", sources=("source.py",), checked_on="2026-08-29")
    return source, unit_path


class KnowledgeFingerprintTests(unittest.TestCase):
    def test_writes_source_digests_for_one_unit(self):
        paths = _paths()
        source, unit_path = _seed_unit(paths)
        args = argparse.Namespace(unit="hydra://knowledge-unit/example/demo")
        with contextlib.redirect_stdout(stdlib_io.StringIO()):
            result = knowledge_fingerprint.command_knowledge_fingerprint(args, paths)
        self.assertEqual(result.exit_code, 0)
        data = markdown_frontmatter(unit_path, paths.root)
        self.assertEqual(data["provenance"]["sources"], ["source.py"])
        self.assertEqual(
            data["provenance"]["source_digests"],
            [{"source": "source.py", "digest": normalized_digest(source)}],
        )

    def test_missing_unit_exits_nonzero(self):
        paths = _paths()
        args = argparse.Namespace(unit="hydra://knowledge-unit/example/missing")
        with contextlib.redirect_stderr(stdlib_io.StringIO()) as err:
            result = knowledge_fingerprint.command_knowledge_fingerprint(args, paths)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("unit not found", err.getvalue())

    def test_replace_source_digests_replaces_existing_block(self):
        content = (
            "---\nhydra_id: hydra://knowledge-unit/example/demo\nkind: knowledge-unit\n"
            "provenance:\n  sources:\n    - source.py\n  source_digests:\n"
            "    - source: source.py\n      digest: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
            "checked_on: 2026-08-29\n---\n# Demo\n"
        )
        result = knowledge_fingerprint.replace_source_digests(
            content,
            [("source.py", "sha256:" + ("b" * 64))],
        )
        self.assertNotIn("sha256:" + ("a" * 64), result)
        self.assertIn("sha256:" + ("b" * 64), result)


if __name__ == "__main__":
    unittest.main()
