"""Mirror test for `hydra_engine.knowledge.package_checks`."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.knowledge import package_checks  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402
from hydra_engine.objects.discovery import ObjectLocations  # noqa: E402


def _locations() -> tuple[ContextCompilerPaths, ObjectLocations]:
    root = Path(tempfile.mkdtemp(prefix="package-checks-test-"))
    hydra = root / ".hydra-framework"
    paths = ContextCompilerPaths(root=root, hydra=hydra)
    resolver_paths = ObjectLocations(
        root=root,
        hydra=hydra,
        local=root / ".hydra-framework.local",
        personal_tasks_rel="tasks/personal",
        object_registry=hydra / "cognition/graph/registry.yaml",
    )
    return paths, resolver_paths


def _write_unit(units_dir: Path, slug: str, *, extra: str = "", question: str = "What does this answer?") -> Path:
    units_dir.mkdir(parents=True, exist_ok=True)
    text = f"""---
hydra_id: hydra://knowledge-unit/demo/{slug}
uid: 11111111-1111-4111-8111-111111111111
schema_version: 3
kind: knowledge-unit
unit_kind: answer
title: Demo Unit
status: active
scope: repo
owners:
  team: fixture
relations: []
provenance:
  sources: []
question: "{question}"
{extra}---

# Demo Unit

## Answer

It answers the demo question.
"""
    path = units_dir / f"{slug}.md"
    path.write_text(text, encoding="utf-8")
    return path


def _write_unit_with_provenance(package_root: Path, slug: str, provenance: str, *, extra: str = "") -> Path:
    units_dir = package_root / "units"
    units_dir.mkdir(parents=True, exist_ok=True)
    path = units_dir / f"{slug}.md"
    path.write_text(
        f"---\nhydra_id: hydra://knowledge-unit/demo/{slug}\n"
        "uid: 11111111-1111-4111-8111-111111111111\n"
        "schema_version: 3\nkind: knowledge-unit\nunit_kind: answer\n"
        "title: Demo Unit\nstatus: active\nscope: repo\n"
        "owners:\n  team: fixture\nrelations: []\n"
        f"{provenance}"
        "question: \"What does this answer?\"\n"
        f"{extra}---\n# Demo Unit\n\n## Answer\n\nIt answers.\n",
        encoding="utf-8",
    )
    return path


class RenderDotDiagramsTests(unittest.TestCase):
    def test_no_diagrams_directory_is_a_no_op(self):
        root = Path(tempfile.mkdtemp(prefix="render-dot-test-"))
        errors = package_checks.render_dot_diagrams(root, root)
        self.assertEqual(errors, [])

    @unittest.skipUnless(shutil.which("dot"), "Graphviz `dot` not installed")
    def test_renders_a_valid_dot_file_to_svg_and_png(self):
        root = Path(tempfile.mkdtemp(prefix="render-dot-test-"))
        diagrams = root / "diagrams"
        diagrams.mkdir()
        (diagrams / "example.dot").write_text("digraph { a -> b; }\n", encoding="utf-8")
        errors = package_checks.render_dot_diagrams(root, root)
        self.assertEqual(errors, [])
        self.assertTrue((root / "images" / "example.svg").exists())
        self.assertTrue((root / "images" / "example.png").exists())

    def test_missing_dot_binary_skips_without_error(self):
        root = Path(tempfile.mkdtemp(prefix="render-dot-test-"))
        diagrams = root / "diagrams"
        diagrams.mkdir()
        (diagrams / "example.dot").write_text("digraph { a -> b; }\n", encoding="utf-8")
        with mock.patch("hydra_engine.knowledge.package_checks.shutil.which", return_value=None):
            errors = package_checks.render_dot_diagrams(root, root)
        self.assertEqual(errors, [])
        self.assertFalse((root / "images").exists())


class ValidatePackageRootTests(unittest.TestCase):
    def test_missing_directory_is_reported(self):
        paths, resolver_paths = _locations()
        missing = paths.root / "does-not-exist"
        errors = package_checks.validate_package_root(missing, paths, resolver_paths)
        self.assertEqual(len(errors), 1)
        self.assertIn("not a directory", errors[0])

    def test_empty_package_directory_has_no_errors(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        package_root.mkdir()
        errors = package_checks.validate_package_root(package_root, paths, resolver_paths)
        self.assertEqual(errors, [])

    def test_broken_markdown_link_is_reported(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        package_root.mkdir()
        (package_root / "overview.md").write_text("[broken](missing.md)\n", encoding="utf-8")
        errors = package_checks.validate_package_root(package_root, paths, resolver_paths)
        self.assertEqual(len(errors), 1)
        self.assertIn("missing.md", errors[0])

    def test_render_false_does_not_touch_diagrams(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        diagrams = package_root / "diagrams"
        diagrams.mkdir(parents=True)
        (diagrams / "example.dot").write_text("digraph { a -> b; }\n", encoding="utf-8")
        errors = package_checks.validate_package_root(package_root, paths, resolver_paths, render=False)
        self.assertEqual(errors, [])
        self.assertFalse((package_root / "images").exists())


class ValidateUnitsDirTests(unittest.TestCase):
    def test_no_units_dir_has_no_findings(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        package_root.mkdir()
        self.assertEqual(package_checks.validate_units_dir(package_root, paths, resolver_paths), [])

    def test_a_clean_unit_has_no_findings(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        _write_unit(package_root / "units", "clean")
        self.assertEqual(package_checks.validate_units_dir(package_root, paths, resolver_paths), [])

    def test_markdown_file_with_no_frontmatter_is_reported(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        units_dir = package_root / "units"
        units_dir.mkdir(parents=True)
        (units_dir / "plain.md").write_text("# Just prose\n", encoding="utf-8")
        findings = package_checks.validate_units_dir(package_root, paths, resolver_paths)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "unit-not-recognized")

    def test_wrong_kind_markdown_file_is_reported(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        units_dir = package_root / "units"
        units_dir.mkdir(parents=True)
        (units_dir / "wrong.md").write_text(
            "---\nhydra_id: hydra://knowledge-slice/demo/x\nkind: knowledge-slice\n---\n# X\n",
            encoding="utf-8",
        )
        findings = package_checks.validate_units_dir(package_root, paths, resolver_paths)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "unit-not-recognized")

    def test_unknown_unit_kind_is_reported(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        _write_unit(package_root / "units", "bad-kind", extra="unit_kind: nonsense\n")
        findings = package_checks.validate_units_dir(package_root, paths, resolver_paths)
        self.assertTrue(any(f.code == "unit-kind" for f in findings))

    def test_missing_question_is_reported(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        units_dir = package_root / "units"
        units_dir.mkdir(parents=True)
        (units_dir / "no-question.md").write_text(
            "---\nhydra_id: hydra://knowledge-unit/demo/x\nkind: knowledge-unit\nunit_kind: answer\n---\n# X\n",
            encoding="utf-8",
        )
        findings = package_checks.validate_units_dir(package_root, paths, resolver_paths)
        self.assertTrue(any(f.code == "unit-question" and "missing" in f.detail for f in findings))

    def test_question_not_ending_in_question_mark_is_reported(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        _write_unit(package_root / "units", "no-mark", question="This is not a question")
        findings = package_checks.validate_units_dir(package_root, paths, resolver_paths)
        self.assertTrue(any(f.code == "unit-question" and "end with" in f.detail for f in findings))

    def test_question_containing_and_is_a_warning(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        _write_unit(package_root / "units", "and-question", question="What is this and that?")
        findings = package_checks.validate_units_dir(package_root, paths, resolver_paths)
        self.assertTrue(any(f.code == "unit-question" and "warning" in f.detail for f in findings))

    def test_rule_kind_requires_sources(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        _write_unit(package_root / "units", "rule-no-sources", extra="unit_kind: rule\n")
        findings = package_checks.validate_units_dir(package_root, paths, resolver_paths)
        self.assertTrue(any(f.code == "unit-rule-sources" for f in findings))

    def test_status_kind_requires_checked_on(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        _write_unit(package_root / "units", "status-no-checked-on", extra="unit_kind: status\n")
        findings = package_checks.validate_units_dir(package_root, paths, resolver_paths)
        self.assertTrue(any(f.code == "unit-status-checked-on" for f in findings))

    def test_divergence_kind_requires_conflicting_certainty_and_effect_section(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        _write_unit(package_root / "units", "div", extra="unit_kind: divergence\n")
        findings = package_checks.validate_units_dir(package_root, paths, resolver_paths)
        codes = {f.code for f in findings}
        self.assertIn("unit-divergence-certainty", codes)
        self.assertIn("unit-divergence-effect", codes)

    def test_missing_reads_path_is_reported(self):
        paths, resolver_paths = _locations()
        (paths.root / "src").mkdir()
        package_root = paths.root / "package"
        _write_unit(package_root / "units", "bad-read", extra="reads:\n  - src/does-not-exist.py\n")
        findings = package_checks.validate_units_dir(package_root, paths, resolver_paths)
        self.assertTrue(any(f.code == "unit-read-path" for f in findings))

    def test_unresolved_certainty_exempts_the_reads_path_check(self):
        paths, resolver_paths = _locations()
        (paths.root / "src").mkdir()
        package_root = paths.root / "package"
        _write_unit(
            package_root / "units", "unshipped",
            extra="reads:\n  - src/does-not-exist.py\ncertainty: unresolved\n",
        )
        findings = package_checks.validate_units_dir(package_root, paths, resolver_paths)
        self.assertFalse(any(f.code == "unit-read-path" for f in findings))

    def test_confirmed_certainty_still_checks_the_reads_path(self):
        paths, resolver_paths = _locations()
        (paths.root / "src").mkdir()
        package_root = paths.root / "package"
        _write_unit(
            package_root / "units", "shipped",
            extra="reads:\n  - src/does-not-exist.py\ncertainty: confirmed\n",
        )
        findings = package_checks.validate_units_dir(package_root, paths, resolver_paths)
        self.assertTrue(any(f.code == "unit-read-path" for f in findings))

    def test_malformed_requires_id_is_reported(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        _write_unit(package_root / "units", "bad-ref", extra="requires:\n  - not-a-hydra-id\n")
        findings = package_checks.validate_units_dir(package_root, paths, resolver_paths)
        self.assertTrue(any(f.code == "unit-ref-shape" for f in findings))

    def test_requires_cycle_is_reported_and_terminates(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        units_dir = package_root / "units"
        _write_unit(units_dir, "a", extra="requires:\n  - hydra://knowledge-unit/demo/b\n")
        _write_unit(units_dir, "b", extra="requires:\n  - hydra://knowledge-unit/demo/a\n")
        findings = package_checks.validate_units_dir(package_root, paths, resolver_paths)
        self.assertTrue(any(f.code == "unit-requires-cycle" for f in findings))

    def test_valid_source_digest_metadata_has_no_findings(self):
        paths, resolver_paths = _locations()
        (paths.root / "source.py").write_text("x = 1\n", encoding="utf-8")
        package_root = paths.root / "package"
        _write_unit_with_provenance(
            package_root,
            "fingerprinted",
            "provenance:\n  sources:\n    - source.py\n  source_digests:\n"
            "    - source: source.py\n      digest: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
        )
        findings = package_checks.validate_units_dir(package_root, paths, resolver_paths)
        self.assertFalse(any(f.code == "unit-source-digest" for f in findings))

    def test_malformed_source_digest_metadata_is_reported(self):
        paths, resolver_paths = _locations()
        (paths.root / "source.py").write_text("x = 1\n", encoding="utf-8")
        package_root = paths.root / "package"
        _write_unit_with_provenance(
            package_root,
            "bad-fingerprints",
            "provenance:\n  sources:\n    - source.py\n  source_digests:\n"
            "    - not-a-map\n"
            "    - source: source.py\n"
            "    - source: source.py\n      digest: nope\n"
            "    - source: other.py\n      digest: sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n"
            "    - source: missing.py\n      digest: sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc\n"
            "    - source: source.py\n      digest: sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd\n",
        )
        findings = [f for f in package_checks.validate_units_dir(package_root, paths, resolver_paths) if f.code == "unit-source-digest"]
        details = "\n".join(f.detail for f in findings)
        self.assertIn("must be a mapping", details)
        self.assertIn("requires `source` and `digest`", details)
        self.assertIn("must match sha256:<64 hex>", details)
        self.assertIn("not listed in `provenance.sources`: other.py", details)
        self.assertIn("does not resolve to one existing file: missing.py", details)
        self.assertIn("duplicate `provenance.source_digests` source: source.py", details)

    def test_source_digests_must_be_a_list(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        _write_unit_with_provenance(
            package_root,
            "scalar-fingerprints",
            "provenance:\n  sources:\n    - source.py\n  source_digests: nope\n",
        )
        findings = package_checks.validate_units_dir(package_root, paths, resolver_paths)
        self.assertTrue(any(f.code == "unit-source-digest" and "must be a list" in f.detail for f in findings))

    def test_unresolved_certainty_exempts_missing_source_digest_file(self):
        paths, resolver_paths = _locations()
        package_root = paths.root / "package"
        _write_unit_with_provenance(
            package_root,
            "unresolved-fingerprint",
            "provenance:\n  sources:\n    - missing.py\n  source_digests:\n"
            "    - source: missing.py\n      digest: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
            extra="certainty: unresolved\n",
        )
        findings = package_checks.validate_units_dir(package_root, paths, resolver_paths)
        self.assertFalse(any(f.code == "unit-source-digest" for f in findings))


class ValidatePackageFileSizesTests(unittest.TestCase):
    def test_small_file_has_no_findings(self):
        paths, _ = _locations()
        package_root = paths.root / "package"
        package_root.mkdir()
        (package_root / "overview.md").write_text("small\n", encoding="utf-8")
        self.assertEqual(package_checks.validate_package_file_sizes(package_root, paths), [])

    def test_file_at_the_ceiling_has_no_findings(self):
        paths, _ = _locations()
        package_root = paths.root / "package"
        package_root.mkdir()
        (package_root / "overview.md").write_text(
            "a" * (package_checks.PACKAGE_FILE_FAIL_TOKENS * 4), encoding="utf-8",
        )
        self.assertEqual(package_checks.validate_package_file_sizes(package_root, paths), [])

    def test_oversized_file_is_reported(self):
        paths, _ = _locations()
        package_root = paths.root / "package"
        nested = package_root / "playbooks"
        nested.mkdir(parents=True)
        (nested / "evidence.md").write_text(
            "a" * (package_checks.PACKAGE_FILE_FAIL_TOKENS * 4 + 4), encoding="utf-8",
        )
        findings = package_checks.validate_package_file_sizes(package_root, paths)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "package-file-size")
        self.assertIn("playbooks/evidence.md", findings[0].path)

    def test_configured_file_size_ceiling_affects_validation(self):
        paths, _ = _locations()
        package_root = paths.root / "package"
        package_root.mkdir()
        (package_root / "overview.md").write_text("small but over one token\n", encoding="utf-8")
        findings = package_checks.validate_package_file_sizes(package_root, paths, fail_tokens=1)
        self.assertEqual(len(findings), 1)
        self.assertIn("1-token hard ceiling", findings[0].detail)

    def test_configured_token_approximation_affects_validation(self):
        paths, _ = _locations()
        package_root = paths.root / "package"
        package_root.mkdir()
        (package_root / "overview.md").write_text("abcdefgh", encoding="utf-8")
        self.assertEqual(package_checks.validate_package_file_sizes(package_root, paths, fail_tokens=2, chars_per_token=4), [])
        findings = package_checks.validate_package_file_sizes(package_root, paths, fail_tokens=2, chars_per_token=2)
        self.assertEqual(len(findings), 1)

    def test_oversized_unit_file_is_reported_too(self):
        paths, _ = _locations()
        package_root = paths.root / "package"
        units_dir = package_root / "units"
        unit_path = _write_unit(units_dir, "huge")
        with unit_path.open("a", encoding="utf-8") as handle:
            handle.write("x" * (package_checks.PACKAGE_FILE_FAIL_TOKENS * 4 + 4))
        findings = package_checks.validate_package_file_sizes(package_root, paths)
        self.assertTrue(any(f.code == "package-file-size" and "units/huge.md" in f.path for f in findings))

    def test_non_markdown_files_are_ignored_regardless_of_size(self):
        paths, _ = _locations()
        package_root = paths.root / "package"
        package_root.mkdir()
        (package_root / "evidence.log").write_text(
            "a" * (package_checks.PACKAGE_FILE_FAIL_TOKENS * 4 + 4), encoding="utf-8",
        )
        self.assertEqual(package_checks.validate_package_file_sizes(package_root, paths), [])


if __name__ == "__main__":
    unittest.main()
