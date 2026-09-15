"""Mirror tests for `hydra_engine.commands.wiki_audit`."""

from __future__ import annotations

import argparse
import contextlib
import io as stdlib_io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.commands import wiki_audit  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402


def _entry(name: str, hydra_id: str, source_block: str, checked_on: str | None = "2026-01-01") -> str:
    checked = f"    checked_on: {checked_on}\n" if checked_on is not None else ""
    return (
        f"  {name}:\n"
        f"    hydra_id: {hydra_id}\n"
        f"    path: project-wiki/{name}.md\n"
        f"{checked}"
        "    provenance:\n"
        f"{source_block}"
    )


def _sidecar(entries: str) -> str:
    return "schema: hydra-framework.object-sidecar.v1\ntitle: Fixture Wiki\nobjects:\n" + entries


class WikiAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.sidecar_root = self.root / ".hydra-framework/surfaces/wiki"
        self.sidecar_root.mkdir(parents=True)
        self.paths = ContextCompilerPaths(root=self.root, hydra=self.root / ".hydra-framework")

    def write_sidecar(self, name: str, entries: str) -> None:
        (self.sidecar_root / f"{name}.yaml").write_text(_sidecar(entries), encoding="utf-8")

    def run_audit(
        self,
        *,
        wiki: str | None = None,
        json_output: bool = False,
        changed_in: str | None = None,
    ) -> tuple[int, str]:
        args = argparse.Namespace(wiki=wiki, json=json_output, changed_in=changed_in)
        output = stdlib_io.StringIO()
        with contextlib.redirect_stdout(output):
            result = wiki_audit.command_wiki_audit(args, self.paths)
        return result.exit_code, output.getvalue()

    def init_git(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=str(self.root), check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=str(self.root), check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=str(self.root), check=True)

    def commit(self, message: str) -> str:
        subprocess.run(["git", "add", "."], cwd=str(self.root), check=True)
        subprocess.run(["git", "commit", "-q", "-m", message], cwd=str(self.root), check=True)
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(self.root), text=True).strip()

    def test_clean_page_reports_clean_and_exits_zero(self) -> None:
        source = self.root / "source.py"
        source.write_text("x = 1\n", encoding="utf-8")
        self.write_sidecar("fixture", _entry(
            "page", "hydra://documentation/page/page", "      sources:\n        - source.py\n"
        ))
        code, output = self.run_audit()
        self.assertEqual(code, 0)
        self.assertIn("hydra://documentation/page/page", output)
        self.assertIn(": clean", output)

    def test_page_with_empty_sources_reports_no_declared_sources(self) -> None:
        self.write_sidecar("fixture", _entry(
            "page", "hydra://documentation/page/page", "      sources: []\n"
        ))
        code, output = self.run_audit()
        self.assertEqual(code, 0)
        self.assertIn("no declared sources", output)

    def test_no_declared_sources_emits_no_fingerprint_remediation(self) -> None:
        self.write_sidecar("fixture", _entry(
            "page", "hydra://documentation/page/page", "      sources: []\n"
        ))
        _code, output = self.run_audit()
        self.assertNotIn("wiki fingerprint", output)

    def test_directory_source_reports_not_one_existing_file(self) -> None:
        (self.root / "source-dir").mkdir()
        self.write_sidecar("fixture", _entry(
            "page", "hydra://documentation/page/page", "      sources:\n        - source-dir\n"
        ))
        code, output = self.run_audit()
        self.assertEqual(code, 0)
        self.assertIn("source is not one existing file: source-dir", output)
        self.assertIn("objects.page.provenance.sources", output)

    def test_sourced_page_without_checked_on_is_unverifiable_not_clean(self) -> None:
        (self.root / "source.py").write_text("x = 1\n", encoding="utf-8")
        self.write_sidecar("fixture", _entry(
            "page", "hydra://documentation/page/page", "      sources:\n        - source.py\n", checked_on=None
        ))
        _code, output = self.run_audit()
        self.assertIn("cannot assess because checked_on is absent or invalid", output)
        self.assertNotIn("): clean", output)

    def test_sourced_page_with_invalid_checked_on_is_unverifiable_not_clean(self) -> None:
        (self.root / "source.py").write_text("x = 1\n", encoding="utf-8")
        self.write_sidecar("fixture", _entry(
            "page", "hydra://documentation/page/page", "      sources:\n        - source.py\n", checked_on="2026-1-1"
        ))
        _code, output = self.run_audit()
        self.assertIn("cannot assess because checked_on is absent or invalid", output)
        self.assertNotIn("): clean", output)

    def test_stale_page_still_exits_zero(self) -> None:
        (self.root / "source.py").write_text("x = 1\n", encoding="utf-8")
        self.write_sidecar("fixture", _entry(
            "page", "hydra://documentation/page/page", "      sources:\n        - source.py\n"
        ))
        with mock.patch("hydra_engine.ports.git.last_commit_iso", return_value="2026-01-02T00:00:00+00:00"):
            code, output = self.run_audit()
        self.assertEqual(code, 0)
        self.assertIn("committed after checked_on", output)
        self.assertIn("hydra.py wiki fingerprint --page hydra://documentation/page/page", output)

    def test_digest_mismatch_is_reported(self) -> None:
        source = self.root / "source.py"
        source.write_text("x = 1\n", encoding="utf-8")
        wrong = "sha256:" + "0" * 64
        self.write_sidecar("fixture", _entry(
            "page", "hydra://documentation/page/page",
            "      sources:\n        - source.py\n"
            "      source_digests:\n"
            f"        - source: source.py\n          digest: {wrong}\n",
        ))
        _code, output = self.run_audit()
        self.assertIn("digest mismatch: source.py", output)

    def test_unknown_wiki_name_reports_no_sidecar_and_exits_zero(self) -> None:
        code, output = self.run_audit(wiki="missing")
        self.assertEqual(code, 0)
        self.assertIn("no sidecar found", output)
        self.assertIn("missing.yaml", output)

    def test_malformed_sidecar_reports_unreadable_not_no_sources(self) -> None:
        (self.sidecar_root / "broken.yaml").write_text(
            _sidecar(
                "  page:\n"
                "    hydra_id: hydra://documentation/page/page\n"
                "    path: page.md\n"
            ),
            encoding="utf-8",
        )
        _code, output = self.run_audit(wiki="broken")
        self.assertIn("sidecar-unreadable", output)
        self.assertNotIn("no declared sources", output)

    def test_one_malformed_sidecar_does_not_hide_valid_sidecars(self) -> None:
        (self.sidecar_root / "broken.yaml").write_text("schema: hydra-framework.object-sidecar.v1\nobjects:\n  broken:\n", encoding="utf-8")
        self.write_sidecar("valid", _entry(
            "page", "hydra://documentation/page/page", "      sources: []\n"
        ))
        _code, output = self.run_audit()
        self.assertIn("sidecar-unreadable", output)
        self.assertIn("hydra://documentation/page/page", output)
        self.assertIn("no declared sources", output)

    def test_wiki_filter_selects_one_sidecar_of_two(self) -> None:
        self.write_sidecar("one", _entry(
            "page", "hydra://documentation/page/one", "      sources: []\n"
        ))
        self.write_sidecar("two", _entry(
            "page", "hydra://documentation/page/two", "      sources: []\n"
        ))
        args = argparse.Namespace(wiki="one", json=True)
        report = wiki_audit.audit_report(args, self.paths)
        self.assertEqual(report["summary"]["sidecars"], 1)
        self.assertEqual(report["sidecars"][0]["name"], "one")
        self.assertEqual(json.loads(json.dumps(report))["sidecars"][0]["pages"][0]["hydra_id"], "hydra://documentation/page/one")

    def test_deleted_source_reports_the_page_without_a_fingerprint_line(self):
        source = self.root / "source.py"
        source.write_text("x = 1\n", encoding="utf-8")
        self.write_sidecar("fixture", _entry(
            "page", "hydra://documentation/page/page", "      sources:\n        - source.py\n"
        ))
        self.init_git()
        self.commit("initial")
        source.unlink()
        revision = self.commit("delete source")
        code, output = self.run_audit(changed_in=revision)
        self.assertEqual(code, 0)
        self.assertIn("source.py was deleted in this commit", output)
        self.assertIn("hydra://documentation/page/page", output)
        self.assertNotIn("wiki fingerprint", output)

    def test_renamed_source_reports_the_old_path_as_missing(self):
        source = self.root / "source.py"
        source.write_text("x = 1\n", encoding="utf-8")
        self.write_sidecar("fixture", _entry(
            "page", "hydra://documentation/page/page", "      sources:\n        - source.py\n"
        ))
        self.init_git()
        self.commit("initial")
        source.rename(self.root / "renamed.py")
        revision = self.commit("rename source")
        code, output = self.run_audit(changed_in=revision)
        self.assertEqual(code, 0)
        self.assertIn("source.py was deleted in this commit", output)
        self.assertNotIn("wiki fingerprint", output)

    def test_commit_touching_no_declared_source_prints_nothing(self):
        source = self.root / "source.py"
        source.write_text("x = 1\n", encoding="utf-8")
        self.write_sidecar("fixture", _entry(
            "page", "hydra://documentation/page/page", "      sources:\n        - source.py\n"
        ))
        self.init_git()
        self.commit("initial")
        (self.root / "unrelated.txt").write_text("unrelated\n", encoding="utf-8")
        revision = self.commit("unrelated change")
        code, output = self.run_audit(changed_in=revision)
        self.assertEqual(code, 0)
        self.assertEqual(output, "")


if __name__ == "__main__":
    unittest.main()
