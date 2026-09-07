"""Mirror test for `hydra_engine.knowledge.candidates`."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.documents.digests import normalized_digest  # noqa: E402
from hydra_engine.knowledge import candidates  # noqa: E402
from hydra_engine.knowledge.packages import ContextCompilerPaths  # noqa: E402
from hydra_engine.knowledge.units import Unit  # noqa: E402
from v3_fixtures import paths_for, write_node, write_unit  # noqa: E402


def _unit(root: Path, *, hydra_id: str, reads: tuple[str, ...] = ()) -> Unit:
    path = root / f"{hydra_id.rsplit('/', 1)[-1]}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Unit\n", encoding="utf-8")
    return Unit(
        path=path, hydra_id=hydra_id, unit_kind="answer",
        title="Demo", question="", group="", certainty="", checked_on="",
        reads=reads, requires=(), see_also=(), verify=(), expand_when=(), sources=(),
    )


class ApproxTokensTests(unittest.TestCase):
    def test_empty_text_is_zero(self):
        self.assertEqual(candidates.approx_tokens(""), 0)

    def test_longer_text_estimates_more_tokens(self):
        self.assertLess(candidates.approx_tokens("abcd"), candidates.approx_tokens("abcd" * 10))

    def test_configured_chars_per_token_changes_estimate(self):
        self.assertEqual(candidates.approx_tokens("abcdefgh", chars_per_token=4), 2)
        self.assertEqual(candidates.approx_tokens("abcdefgh", chars_per_token=2), 4)


class CandidateTests(unittest.TestCase):
    def test_file_candidate_reports_size_and_approx_tokens(self):
        root = Path(tempfile.mkdtemp(prefix="candidates-test-"))
        path = root / "note.md"
        path.write_text("some content\n", encoding="utf-8")
        paths = ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")
        candidate = candidates.file_candidate(path, kind="path", reason="explicit", priority=5, paths=paths)
        self.assertEqual(candidate["path"], "note.md")
        self.assertGreater(candidate["approx_tokens"], 0)

    def test_add_candidate_merges_duplicate_reasons(self):
        seen: set[str] = set()
        pool: list[dict] = []
        candidates.add_candidate(pool, seen, {"path": "a.md", "reason": "first"})
        candidates.add_candidate(pool, seen, {"path": "a.md", "reason": "second"})
        self.assertEqual(len(pool), 1)
        self.assertEqual(pool[0]["reason"], "first; second")

    def test_add_candidate_propagates_required_from_a_later_duplicate(self):
        # An explicit `--object` reference and a unit's own required-unit
        # candidate can name the same path; whichever arrives first must not
        # cause the merged candidate to lose `required`.
        seen: set[str] = set()
        pool: list[dict] = []
        candidates.add_candidate(pool, seen, {"path": "a.md", "reason": "explicit object a"})
        candidates.add_candidate(pool, seen, {"path": "a.md", "reason": "unit a", "required": True})
        self.assertTrue(pool[0]["required"])

    def test_add_candidate_keeps_required_when_a_later_duplicate_is_optional(self):
        seen: set[str] = set()
        pool: list[dict] = []
        candidates.add_candidate(pool, seen, {"path": "a.md", "reason": "unit a", "required": True})
        candidates.add_candidate(pool, seen, {"path": "a.md", "reason": "explicit object a"})
        self.assertTrue(pool[0]["required"])

    def test_resolve_context_path_handles_absolute_and_relative(self):
        root = Path(tempfile.mkdtemp(prefix="candidates-test-"))
        paths = ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")
        self.assertEqual(candidates.resolve_context_path("sub/file.md", paths), root / "sub/file.md")
        self.assertEqual(candidates.resolve_context_path("/abs/file.md", paths), Path("/abs/file.md"))

    def test_object_lookup_indexes_by_id_and_aliases(self):
        obj = {"id": "hydra://knowledge-unit/0001-test", "aliases": ["hydra://knowledge-unit/alt"]}
        lookup = candidates.object_lookup([obj])
        self.assertIs(lookup["hydra://knowledge-unit/0001-test"], obj)
        self.assertIs(lookup["hydra://knowledge-unit/alt"], obj)


class UnitCandidatesTests(unittest.TestCase):
    def test_emits_a_unit_candidate_and_its_resolved_reads(self):
        root = Path(tempfile.mkdtemp(prefix="unit-candidates-test-"))
        paths = ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")
        (root / "source.py").write_text("x = 1\n", encoding="utf-8")
        unit = _unit(root / "units", hydra_id="hydra://knowledge-unit/demo/one", reads=("source.py",))
        warnings: list[str] = []
        result = candidates.unit_candidates(
            [unit], package="demo", paths=paths, required_ids=set(), warnings=warnings,
        )
        kinds = [c["kind"] for c in result]
        self.assertEqual(kinds, ["knowledge-unit", "knowledge-unit-read"])
        self.assertEqual(warnings, [])
        self.assertFalse(result[0]["required"])
        self.assertFalse(result[1]["required"])

    def test_required_id_marks_only_the_unit_file_required(self):
        root = Path(tempfile.mkdtemp(prefix="unit-candidates-test-"))
        paths = ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")
        (root / "source.py").write_text("x = 1\n", encoding="utf-8")
        unit = _unit(root / "units", hydra_id="hydra://knowledge-unit/demo/one", reads=("source.py",))
        result = candidates.unit_candidates(
            [unit], package="demo", paths=paths, required_ids={"hydra://knowledge-unit/demo/one"}, warnings=[],
        )
        by_kind = {c["kind"]: c for c in result}
        self.assertTrue(by_kind["knowledge-unit"]["required"])
        self.assertFalse(by_kind["knowledge-unit-read"]["required"])

    def test_unresolvable_read_path_warns_and_is_skipped(self):
        root = Path(tempfile.mkdtemp(prefix="unit-candidates-test-"))
        paths = ContextCompilerPaths(root=root, hydra=root / ".hydra-framework")
        unit = _unit(root / "units", hydra_id="hydra://knowledge-unit/demo/one", reads=("missing.py",))
        warnings: list[str] = []
        result = candidates.unit_candidates(
            [unit], package="demo", paths=paths, required_ids=set(), warnings=warnings,
        )
        self.assertEqual([c["kind"] for c in result], ["knowledge-unit"])
        self.assertTrue(any("missing.py" in w for w in warnings))


class StaleUnitSourcesTests(unittest.TestCase):
    """A staleness signal: a `provenance.sources` entry
    committed after `checked_on`. Real `git init`/`commit` in a tempdir
    (matching `tests.unit.ports.test_git`'s own fixture shape) rather than
    mocking the git port, so `checked_on` is set far in the past or future
    instead of asserting an exact commit timestamp."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=str(self.root), check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.com"], cwd=str(self.root), check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=str(self.root), check=True)
        (self.root / "source.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "source.py"], cwd=str(self.root), check=True)
        subprocess.run(["git", "commit", "-q", "-m", "fixture commit"], cwd=str(self.root), check=True)
        self.paths = ContextCompilerPaths(root=self.root, hydra=self.root / ".hydra-framework")

    def _unit_with(self, *, checked_on: str, sources: tuple[str, ...], source_digests: object = ()) -> Unit:
        path = self.root / "units" / "one.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Unit\n", encoding="utf-8")
        return Unit(
            path=path, hydra_id="hydra://knowledge-unit/demo/one", unit_kind="answer",
            title="Demo", question="", group="", certainty="", checked_on=checked_on,
            reads=(), requires=(), see_also=(), verify=(), expand_when=(), sources=sources,
            source_digests=source_digests,
        )

    def test_source_committed_after_checked_on_is_stale(self):
        unit = self._unit_with(checked_on="2000-01-01", sources=("source.py",))
        self.assertEqual(candidates.stale_unit_sources(unit, self.paths), ["source.py"])

    def test_source_committed_before_checked_on_is_not_stale(self):
        unit = self._unit_with(checked_on="2099-01-01", sources=("source.py",))
        self.assertEqual(candidates.stale_unit_sources(unit, self.paths), [])

    def test_no_checked_on_is_never_stale(self):
        unit = self._unit_with(checked_on="", sources=("source.py",))
        self.assertEqual(candidates.stale_unit_sources(unit, self.paths), [])

    def test_missing_source_path_is_skipped_not_flagged(self):
        unit = self._unit_with(checked_on="2000-01-01", sources=("missing.py",))
        self.assertEqual(candidates.stale_unit_sources(unit, self.paths), [])

    def test_fingerprinted_source_match_does_not_fall_back_to_date_rule(self):
        digest = normalized_digest(self.root / "source.py")
        unit = self._unit_with(
            checked_on="2000-01-01",
            sources=("source.py",),
            source_digests=[{"source": "source.py", "digest": digest}],
        )
        self.assertEqual(candidates.stale_unit_sources(unit, self.paths), [])

    def test_fingerprinted_source_change_is_stale_without_a_commit(self):
        digest = normalized_digest(self.root / "source.py")
        (self.root / "source.py").write_text("x = 2\n", encoding="utf-8")
        unit = self._unit_with(
            checked_on="2099-01-01",
            sources=("source.py",),
            source_digests=[{"source": "source.py", "digest": digest}],
        )
        self.assertEqual(candidates.stale_unit_sources(unit, self.paths), ["source.py"])

    def test_unit_candidates_annotates_the_unit_candidate_with_stale_sources(self):
        unit = self._unit_with(checked_on="2000-01-01", sources=("source.py",))
        result = candidates.unit_candidates([unit], package="demo", paths=self.paths, required_ids=set(), warnings=[])
        by_kind = {c["kind"]: c for c in result}
        self.assertEqual(by_kind["knowledge-unit"]["stale_sources"], ["source.py"])

    def test_stale_unit_source_report_walks_every_unit_in_every_node(self):
        self.paths = paths_for(self.root, ("alpha", "beta"))
        for node, slug, checked_on in [
            ("alpha", "old", "2000-01-01"),
            ("beta", "fresh", "2099-01-01"),
        ]:
            write_node(self.paths, node)
            write_unit(self.paths, node, slug, checked_on=checked_on, sources=("source.py",))

        checked_units, rows = candidates.stale_unit_source_report(self.paths)

        self.assertEqual(checked_units, 2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["node"], "alpha")
        self.assertEqual(rows[0]["hydra_id"], "hydra://knowledge-unit/alpha/old")
        self.assertEqual(rows[0]["stale_sources"], ["source.py"])


if __name__ == "__main__":
    unittest.main()
