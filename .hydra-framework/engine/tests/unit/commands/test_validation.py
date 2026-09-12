"""Mirror test for `hydra_engine.commands.validation`."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.commands import validation  # noqa: E402
from hydra_engine.finding import Finding  # noqa: E402
from hydra_engine.work.paths import WorkPaths  # noqa: E402
from hydra_engine.work.task_records import personal_task_notes  # noqa: E402


def _run(func, *args, **kwargs):
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        result = func(*args, **kwargs)
    return result, stdout.getvalue()


class CommandValidateTests(unittest.TestCase):
    def test_no_findings_reports_ok_and_prints_notes(self) -> None:
        result, output = _run(validation.command_validate, [lambda: []], ["a note"])
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(output.splitlines(), ["Hydra validate: ok", "note: a note"])

    def test_findings_report_failed_and_every_finding(self) -> None:
        finding = Finding(path="a.md", code="example", detail="a.md is bad")
        result, output = _run(validation.command_validate, [lambda: [finding]], ["ignored note"])
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(output.splitlines(), ["Hydra validate: failed", "- a.md is bad"])

    def test_checks_run_in_order_and_concatenate(self) -> None:
        one = Finding(path="a", code="one", detail="first")
        two = Finding(path="b", code="two", detail="second")
        result, output = _run(validation.command_validate, [lambda: [one], lambda: [two]], [])
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(output.splitlines(), ["Hydra validate: failed", "- first", "- second"])


class CommandDoctorTests(unittest.TestCase):
    def _doctor(self, **overrides):
        defaults = dict(
            missing_required_paths=[],
            tasks=[],
            owner="example-owner",
            local_exists=True,
            private_tier={
                "gitignore_rule_present": True,
                "ignored": True,
                "directory_exists": True,
                "seeded_areas_present": True,
                "missing_seeded_areas": [],
            },
            hooks_installed=True,
            knowledge_index_status="fresh",
            object_store_status="fresh",
            surfaces=[],
            desired_plan_nonempty=False,
            lineage={},
            checks=[],
            notes=[],
        )
        defaults.update(overrides)
        return _run(validation.command_doctor, **defaults)

    def test_missing_required_paths_short_circuits(self) -> None:
        result, output = self._doctor(missing_required_paths=["AI_SYSTEM.md"])
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(output.splitlines(), ["Hydra doctor: missing required paths", "- AI_SYSTEM.md"])

    def test_unresolved_owner_reports_unresolved(self) -> None:
        _, output = self._doctor(owner=None)
        self.assertIn("Owner: UNRESOLVED.", output)

    def test_active_tasks_are_summarized_by_owner(self) -> None:
        _, output = self._doctor(tasks=[Path("tasks/personal/dana/x.md"), Path("tasks/personal/dana/y.md")])
        self.assertIn("Active task records: 2 across 1 owner(s): dana", output)

    def test_unmanaged_surfaces_are_listed_and_prompt_reclaim(self) -> None:
        _, output = self._doctor(surfaces=[{"path": "x", "status": "orphaned", "detail": "d"}])
        self.assertIn("Provider surfaces: 0 generated, 1 unmanaged", output)
        self.assertIn("- orphaned: x", output)
        self.assertIn("Run `hydra.py reclaim` for the promotion plan.", output)

    def test_no_surfaces_and_nothing_desired_is_only_a_note(self) -> None:
        result, output = self._doctor(surfaces=[], desired_plan_nonempty=False)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Note: no provider surfaces found.", output)

    def test_no_surfaces_but_something_desired_fails_closed(self) -> None:
        result, output = self._doctor(surfaces=[], desired_plan_nonempty=True)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Hydra doctor: no provider surfaces are materialized", output)
        self.assertIn("hydra.py export-adapters", output)

    def test_private_tier_ignore_failure_short_circuits(self) -> None:
        result, output = self._doctor(private_tier={
            "gitignore_rule_present": False,
            "ignored": False,
            "directory_exists": False,
            "seeded_areas_present": False,
            "missing_seeded_areas": ["private"],
        })
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Hydra doctor: private tier is not effectively ignored", output)

    def test_cache_lifecycle_reports_status_and_hints(self) -> None:
        _, output = self._doctor(
            hooks_installed=False,
            knowledge_index_status="missing",
            object_store_status="stale",
        )
        self.assertIn("Cache lifecycle:", output)
        self.assertIn("- git hooks installed: no", output)
        self.assertIn("hydra.py install-hooks", output)
        self.assertIn("- knowledge.db: missing", output)
        self.assertIn("hydra.py hook-reindex-knowledge", output)
        self.assertIn("- object-store.db: stale", output)
        self.assertIn("hydra.py ref store rebuild", output)

    def test_clean_doctor_delegates_its_verdict_to_validate(self) -> None:
        finding = Finding(path="a", code="example", detail="a is bad")
        result, output = self._doctor(checks=[lambda: [finding]])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Hydra validate: failed", output)
        self.assertIn("- a is bad", output)


class PersonalTaskNotesIntegrationTests(unittest.TestCase):
    """`personal_task_notes` itself is mirror-tested in `work/test_task_records.py`;
    this integration test is the one place that exercises the real seam --
    `command_validate` printing real, on-disk-computed task notes after its
    verdict line, not just a hand-built notes list. Moved from
    `scripts/tests/test_hydra.py`'s
    `PersonalTaskNotesIntegrationTests`, which monkeypatched `hydra.*`
    validators to no-ops -- unneeded now that `command_validate` takes its
    check list and notes as plain parameters."""

    def setUp(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="commands-validation-task-notes-"))
        self.paths = WorkPaths(root=root, hydra=root / ".hydra-framework", local=root / ".hydra-framework.local")

    def seed_task(self, active_step: str) -> None:
        path = self.paths.owner_task_dir("dana") / "2026-01-01-example.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Task: example\n\n"
            "Status: active\n"
            "Owner: dana\n"
            "Updated: 2026-01-01\n\n"
            "## Goal\n\nDo the work.\n\n"
            "## Readiness\n\n- Status: ready\n\n"
            "## Step State\n\n"
            f"- Active step: {active_step}\n"
            "- Next step: none\n"
            "- Completed steps: none\n"
            "\n## Continuation Notes\n\n"
            "- Running state: none\n"
            "- Resume check: unit test\n",
            encoding="utf-8",
        )

    def test_validate_command_keeps_task_notes_advisory(self) -> None:
        self.seed_task("none")
        notes = personal_task_notes(self.paths)
        result, output = _run(validation.command_validate, [], notes)
        lines = output.splitlines()
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(lines[0], "Hydra validate: ok")
        self.assertTrue(any(line.startswith("note: ") and "Active step: none" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
