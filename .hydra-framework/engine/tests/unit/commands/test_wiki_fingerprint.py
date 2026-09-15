"""Mirror tests for `hydra_engine.commands.wiki_fingerprint`."""

from __future__ import annotations

import argparse
import contextlib
import io as stdlib_io
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.commands import wiki_fingerprint  # noqa: E402
from hydra_engine.documents.digests import normalized_digest  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402


def _sidecar(entries: str) -> str:
    return "schema: hydra-framework.object-sidecar.v1\n" "title: Fixture Wiki\n" "objects:\n" + entries


def _entry(name: str, hydra_id: str, source_block: str, *, checked_on: str = "2026-01-01", extra: str = "") -> str:
    return (
        f"  {name}:\n"
        f"    hydra_id: {hydra_id}\n"
        f"    uid: uid-{name}\n"
        "    path: project-wiki/fixture.md\n"
        f"    checked_on: {checked_on}\n"
        f"{extra}"
        "    provenance:\n"
        f"{source_block}"
    )


class WikiFingerprintTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.sidecar_root = self.root / ".hydra-framework/surfaces/wiki"
        self.sidecar_root.mkdir(parents=True)
        self.paths = ContextCompilerPaths(root=self.root, hydra=self.root / ".hydra-framework")

    def write_sidecar(self, name: str, entries: str) -> Path:
        path = self.sidecar_root / f"{name}.yaml"
        path.write_text(_sidecar(entries), encoding="utf-8")
        return path

    def run_command(self, page: str) -> tuple[int, str, str]:
        args = argparse.Namespace(page=page)
        stdout = stdlib_io.StringIO()
        stderr = stdlib_io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = wiki_fingerprint.command_wiki_fingerprint(args, self.paths)
        return result.exit_code, stdout.getvalue(), stderr.getvalue()

    def test_rewrites_one_page_and_preserves_other_entries(self) -> None:
        source = self.root / "source.py"
        source.write_text("x = 1\n", encoding="utf-8")
        page_id = "hydra://documentation/page/page"
        other = _entry("other", "hydra://documentation/page/other", "      sources: []\n")
        sidecar = self.write_sidecar(
            "fixture",
            "  # preserve this object comment\n"
            + _entry(
                "page",
                page_id,
                "      sources:\n        - source.py\n",
                extra="    custom: preserve me\n",
            )
            + other
            + "# preserve this trailing comment\n",
        )
        before_other = other

        code, output, error = self.run_command(page_id)

        self.assertEqual(code, 0)
        self.assertEqual(error, "")
        self.assertIn("updated .hydra-framework/surfaces/wiki/fixture.yaml", output)
        content = sidecar.read_text(encoding="utf-8")
        self.assertIn("# preserve this object comment\n", content)
        self.assertIn("    custom: preserve me\n", content)
        self.assertIn("# preserve this trailing comment\n", content)
        self.assertIn(before_other, content)
        self.assertIn(f"checked_on: '{date.today().isoformat()}'", content)
        self.assertIn(f"digest: {normalized_digest(source)}", content)

    def test_idempotent_rewrite(self) -> None:
        source = self.root / "source.py"
        source.write_text("x = 1\n", encoding="utf-8")
        page_id = "hydra://documentation/page/page"
        sidecar = self.write_sidecar(
            "fixture",
            _entry("page", page_id, "      sources:\n        - source.py\n"),
        )

        self.assertEqual(self.run_command(page_id)[0], 0)
        first = sidecar.read_bytes()
        self.assertEqual(self.run_command(page_id)[0], 0)
        self.assertEqual(first, sidecar.read_bytes())

    def test_refuses_directory_source_without_write(self) -> None:
        (self.root / "source-dir").mkdir()
        page_id = "hydra://documentation/page/page"
        sidecar = self.write_sidecar(
            "fixture",
            _entry("page", page_id, "      sources:\n        - source-dir\n"),
        )
        before = sidecar.read_bytes()

        code, _output, error = self.run_command(page_id)

        self.assertEqual(code, 1)
        self.assertIn("source is not one existing file: source-dir", error)
        self.assertEqual(before, sidecar.read_bytes())

    def test_refuses_missing_source_without_write(self) -> None:
        page_id = "hydra://documentation/page/page"
        sidecar = self.write_sidecar(
            "fixture",
            _entry("page", page_id, "      sources:\n        - missing.py\n"),
        )
        before = sidecar.read_bytes()

        code, _output, error = self.run_command(page_id)

        self.assertEqual(code, 1)
        self.assertIn("source is not one existing file: missing.py", error)
        self.assertEqual(before, sidecar.read_bytes())

    def test_refuses_page_with_no_sources_without_write(self) -> None:
        page_id = "hydra://documentation/page/page"
        sidecar = self.write_sidecar("fixture", _entry("page", page_id, "      sources: []\n"))
        before = sidecar.read_bytes()

        code, _output, error = self.run_command(page_id)

        self.assertEqual(code, 1)
        self.assertIn("page has no provenance.sources", error)
        self.assertEqual(before, sidecar.read_bytes())

    def test_rewrite_updates_checked_on(self) -> None:
        source = self.root / "source.py"
        source.write_text("x = 1\n", encoding="utf-8")
        page_id = "hydra://documentation/page/page"
        sidecar = self.write_sidecar(
            "fixture",
            _entry("page", page_id, "      sources:\n        - source.py\n", checked_on="2020-01-01"),
        )

        self.assertEqual(self.run_command(page_id)[0], 0)
        self.assertIn(f"checked_on: '{date.today().isoformat()}'", sidecar.read_text(encoding="utf-8"))

    def test_malformed_target_entry_leaves_file_byte_identical(self) -> None:
        page_id = "hydra://documentation/page/page"
        sidecar = self.write_sidecar(
            "fixture",
            "  page:\n"
            f"    hydra_id: {page_id}\n"
            "    path: project-wiki/fixture.md\n"
            "    provenance:\n"
            "      sources: source.py\n",
        )
        before = sidecar.read_bytes()

        code, _output, error = self.run_command(page_id)

        self.assertEqual(code, 1)
        self.assertIn("sources must be a list", error)
        self.assertEqual(before, sidecar.read_bytes())

    def test_duplicate_target_hydra_id_is_refused_without_write(self) -> None:
        page_id = "hydra://documentation/page/page"
        first = self.write_sidecar(
            "one",
            _entry("page", page_id, "      sources:\n        - source.py\n"),
        )
        second = self.write_sidecar(
            "two",
            _entry("page-copy", page_id, "      sources:\n        - source.py\n"),
        )
        (self.root / "source.py").write_text("x = 1\n", encoding="utf-8")
        before = (first.read_bytes(), second.read_bytes())

        code, _output, error = self.run_command(page_id)

        self.assertEqual(code, 1)
        self.assertIn("duplicate hydra_id", error)
        self.assertEqual(before, (first.read_bytes(), second.read_bytes()))


if __name__ == "__main__":
    unittest.main()
