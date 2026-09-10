"""Mirror test for `hydra_engine.work.task_records`.

Moves `SlugifyTests.test_task_name_strips_date_prefix`, `TaskContractTests`,
`TaskStatusTests`, and the hermetic half of `PersonalTaskNotesTests` from
`scripts/tests/test_hydra.py`, rewritten against the moved logic directly
with a temp `WorkPaths` fixture instead of monkeypatching `hydra.HYDRA`.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.work import task_records  # noqa: E402
from hydra_engine.work.paths import WorkPaths  # noqa: E402

REQUIRED_SECTIONS = ["## Goal", "## Readiness", "## Continuation Notes"]


def _paths() -> WorkPaths:
    root = Path(tempfile.mkdtemp(prefix="work-task-records-"))
    return WorkPaths(root=root, hydra=root / ".hydra-framework", local=root / ".hydra-framework.local")


def _seed_task(
    paths: WorkPaths,
    active_step: str,
    status: str = "active",
    readiness_status: str = "ready",
    blockers: str = "none",
) -> Path:
    path = paths.owner_task_dir("dana") / "2026-01-01-example.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Task: example\n\n"
        f"Status: {status}\n"
        "Owner: dana\n"
        "Updated: 2026-01-01\n\n"
        "## Goal\n\nDo the work.\n\n"
        "## Readiness\n\n"
        f"- Status: {readiness_status}\n"
        f"- Blockers and assumptions: {blockers}\n\n"
        "## Step State\n\n"
        f"- Active step: {active_step}\n",
        encoding="utf-8",
    )
    return path


class TaskHeaderAndBulletFieldTests(unittest.TestCase):
    def test_task_header_field_reads_top_level_label(self) -> None:
        self.assertEqual(task_records.task_header_field("Status: active\n", "Status"), "active")

    def test_task_bullet_field_reads_nested_label(self) -> None:
        self.assertEqual(
            task_records.task_bullet_field("- Blockers and assumptions: none\n", "Blockers and assumptions"), "none"
        )

    def test_task_bullet_field_is_none_matches_bare_none(self) -> None:
        self.assertTrue(task_records.task_bullet_field_is_none("- Active step: none\n", "Active step"))
        self.assertFalse(task_records.task_bullet_field_is_none("- Active step: write the plan\n", "Active step"))


class TaskNameFromPathTests(unittest.TestCase):
    def test_strips_date_prefix(self) -> None:
        path = Path("2026-07-30-token-efficiency-hooks.md")
        self.assertEqual(task_records.task_name_from_path(path), "token-efficiency-hooks")


class ResolveTaskRecordTests(unittest.TestCase):
    def _write(self, paths: WorkPaths, owner: str, filename: str) -> Path:
        path = paths.owner_task_dir(owner) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")
        return path

    def test_prefers_a_unique_caller_owned_name_match(self) -> None:
        paths = _paths()
        own = self._write(paths, "dana", "2026-01-01-example-task.md")
        self._write(paths, "reed", "2026-01-02-example-task.md")
        resolved, errors = task_records.resolve_task_record("Example Task!", paths, "dana")
        self.assertEqual(resolved, own)
        self.assertEqual(errors, [])

    def test_allows_one_unique_global_match(self) -> None:
        paths = _paths()
        other = self._write(paths, "reed", "2026-01-01-example.md")
        resolved, errors = task_records.resolve_task_record("example", paths, "dana")
        self.assertEqual(resolved, other)
        self.assertEqual(errors, [])

    def test_multiple_matches_fail_with_candidate_paths(self) -> None:
        paths = _paths()
        first = self._write(paths, "dana", "2026-01-01-example.md")
        second = self._write(paths, "dana", "2026-02-01-example.md")
        resolved, errors = task_records.resolve_task_record("example", paths, "dana")
        self.assertIsNone(resolved)
        self.assertIn(task_records.display_path(first, paths.root), "\n".join(errors))
        self.assertIn(task_records.display_path(second, paths.root), "\n".join(errors))
        self.assertIn("Use an explicit task record path", errors[-1])

    def test_explicit_repository_path_wins_over_name_fallback(self) -> None:
        paths = _paths()
        self._write(paths, "dana", "2026-01-01-example.md")
        resolved, errors = task_records.resolve_task_record("example.md", paths, "dana")
        self.assertIsNone(resolved)
        self.assertEqual(errors, [f"Task not found: {paths.root / 'example.md'}"])


class TaskSummaryTests(unittest.TestCase):
    def test_summarizes_status_updated_owner_and_goal(self) -> None:
        paths = _paths()
        path = _seed_task(paths, "write the plan")
        summary = task_records.task_summary(path, paths.root)
        self.assertEqual(summary["owner"], "dana")
        self.assertEqual(summary["status"], "active")
        self.assertEqual(summary["updated"], "2026-01-01")
        self.assertEqual(summary["goal"], "Do the work.")


class TaskStatusTests(unittest.TestCase):
    def test_only_the_header_status_is_rewritten(self) -> None:
        content = "Status: active\n\n## Readiness\n\nStatus: not-checked\n"
        updated = task_records.set_task_status(content, "completed")
        self.assertIn("Status: completed", updated)
        self.assertNotIn("Status: active", updated)
        # The readiness block has its own vocabulary and must survive untouched.
        self.assertIn("Status: not-checked", updated)

    def test_updated_header_is_refreshed_not_duplicated(self) -> None:
        content = "Status: active\nUpdated: 2026-01-01\n"
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-02-01"):
            once = task_records.touch_task_updated(content)
            twice = task_records.touch_task_updated(once)
        self.assertEqual(once, twice)
        self.assertEqual(once.count("Updated:"), 1)
        self.assertIn("Updated: 2026-02-01", once)

    def test_updated_header_is_inserted_when_a_record_predates_the_field(self) -> None:
        legacy = "# Task: x\n\nStatus: active\nOwner: dana\nCreated: 2026-01-01\n\n## Goal\n"
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-02-01"):
            updated = task_records.touch_task_updated(legacy)
        self.assertIn("Status: active\nUpdated: 2026-02-01", updated)
        # `Created:` records when the work began and must never be rewritten.
        self.assertIn("Created: 2026-01-01", updated)


class ValidateTaskFileTests(unittest.TestCase):
    def test_incomplete_record_reports_every_missing_section(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="work-task-records-"))
        path = root / "task.md"
        path.write_text("# Task: x\n\n## Goal\n\nDo a thing.\n", encoding="utf-8")
        missing = task_records.validate_task_file(path, REQUIRED_SECTIONS, root)
        self.assertTrue(any("## Readiness" in item for item in missing))
        self.assertTrue(any("## Continuation Notes" in item for item in missing))
        self.assertFalse(any("## Goal" in item for item in missing))

    def test_complete_record_reports_nothing(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="work-task-records-"))
        path = root / "task.md"
        path.write_text("\n".join(REQUIRED_SECTIONS), encoding="utf-8")
        self.assertEqual(task_records.validate_task_file(path, REQUIRED_SECTIONS, root), [])


class ValidatePersonalTaskFileTests(unittest.TestCase):
    def test_owner_header_must_match_the_personal_directory(self) -> None:
        paths = _paths()
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: reed\nUpdated: 2026-01-01\n", encoding="utf-8")
        errors = task_records.validate_personal_task_file(task, paths.root)
        self.assertTrue(errors)
        self.assertIn("does not match directory `dana`", errors[0])

    def test_matching_owner_is_silent(self) -> None:
        paths = _paths()
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: dana\nUpdated: 2026-01-01\n", encoding="utf-8")
        self.assertEqual(task_records.validate_personal_task_file(task, paths.root), [])


class TaskOutcomeRefusalLinesTests(unittest.TestCase):
    def test_existing_file_is_accepted(self) -> None:
        paths = _paths()
        outcome = paths.root / "repo/knowledge/outcome.md"
        outcome.parent.mkdir(parents=True)
        outcome.write_text("x\n", encoding="utf-8")
        self.assertEqual(task_records.task_outcome_refusal_lines("repo/knowledge/outcome.md", paths), [])

    def test_missing_file_is_rejected(self) -> None:
        paths = _paths()
        self.assertEqual(
            task_records.task_outcome_refusal_lines("repo/knowledge/missing.md", paths),
            ["Outcome does not exist: repo/knowledge/missing.md"],
        )

    def test_directory_is_rejected(self) -> None:
        paths = _paths()
        directory = paths.root / "repo/knowledge"
        directory.mkdir(parents=True)
        self.assertEqual(
            task_records.task_outcome_refusal_lines("repo/knowledge", paths),
            ["Outcome is not a file: repo/knowledge"],
        )

    def test_private_and_task_state_paths_are_rejected(self) -> None:
        paths = _paths()
        for rel in [
            ".hydra-framework.local/notes/outcome.md",
            ".hydra-framework/tasks/personal/dana/2026-01-01-x.md",
        ]:
            target = paths.root / rel
            target.parent.mkdir(parents=True)
            target.write_text("x\n", encoding="utf-8")
            self.assertEqual(
                task_records.task_outcome_refusal_lines(rel, paths),
                [f"Outcome is not a durable shared/source artifact: {rel}"],
            )

    def test_paths_outside_the_repo_are_rejected(self) -> None:
        paths = _paths()
        self.assertEqual(
            task_records.task_outcome_refusal_lines("../outside.md", paths),
            ["Outcome must stay inside this repository: ../outside.md"],
        )


class IterPersonalTaskFilesTests(unittest.TestCase):
    def test_finds_every_owners_records(self) -> None:
        paths = _paths()
        for owner, name in [("dana", "a.md"), ("reed", "b.md")]:
            path = paths.owner_task_dir(owner) / name
            path.parent.mkdir(parents=True)
            path.write_text("x\n", encoding="utf-8")
        self.assertEqual(len(task_records.iter_personal_task_files(paths)), 2)

    def test_missing_root_is_empty(self) -> None:
        paths = _paths()
        self.assertEqual(task_records.iter_personal_task_files(paths), [])


class IterPersonalCheckpointsTests(unittest.TestCase):
    def test_finds_checkpoints_under_owners(self) -> None:
        paths = _paths()
        checkpoint = paths.owner_task_dir("dana") / "checkpoints" / "2026-01-01-x-checkpoint.md"
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_text("x\n", encoding="utf-8")
        self.assertEqual(task_records.iter_personal_checkpoints(paths), [checkpoint])


class DuplicateTaskSlugFindingsTests(unittest.TestCase):
    def _write(self, paths: WorkPaths, owner: str, filename: str) -> Path:
        path = paths.owner_task_dir(owner) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")
        return path

    def test_no_tasks_is_silent(self) -> None:
        paths = _paths()
        self.assertEqual(task_records.duplicate_task_slug_findings(paths), [])

    def test_same_owner_reusing_a_slug_is_not_flagged(self) -> None:
        paths = _paths()
        self._write(paths, "dana", "2026-01-01-example.md")
        self._write(paths, "dana", "2026-02-01-example.md")
        self.assertEqual(task_records.duplicate_task_slug_findings(paths), [])

    def test_different_slugs_across_owners_is_not_flagged(self) -> None:
        paths = _paths()
        self._write(paths, "dana", "2026-01-01-example.md")
        self._write(paths, "reed", "2026-01-01-other.md")
        self.assertEqual(task_records.duplicate_task_slug_findings(paths), [])

    def test_same_slug_across_two_owners_is_flagged(self) -> None:
        paths = _paths()
        self._write(paths, "dana", "2026-01-01-example.md")
        self._write(paths, "reed", "2026-01-02-example.md")
        findings = task_records.duplicate_task_slug_findings(paths)
        self.assertEqual(len(findings), 1)
        self.assertIn("example", findings[0].detail)
        self.assertIn("dana", findings[0].detail)
        self.assertIn("reed", findings[0].detail)
        self.assertIn("task handoff", findings[0].detail)


class PersonalTaskNotesTests(unittest.TestCase):
    def test_active_task_with_no_active_step_gets_advisory_note(self) -> None:
        paths = _paths()
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-01"):
            path = _seed_task(paths, "none")
            notes = task_records.personal_task_notes(paths)
        self.assertIn(
            f"{task_records.display_path(path, paths.root)}: active task has `Active step: none`; "
            "complete it or set the active step",
            notes,
        )

    def test_active_task_with_real_active_step_gets_no_hygiene_note(self) -> None:
        paths = _paths()
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-01"):
            _seed_task(paths, "implement focused validation coverage")
            notes = task_records.personal_task_notes(paths)
        self.assertFalse(any("Active step: none" in note for note in notes))

    def test_newly_scaffolded_unready_task_gets_no_active_step_note(self) -> None:
        paths = _paths()
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-01"):
            _seed_task(paths, "none", readiness_status="not-checked")
            notes = task_records.personal_task_notes(paths)
        self.assertFalse(any("Active step: none" in note for note in notes))

    def test_blocked_task_with_no_blocker_gets_advisory_note(self) -> None:
        paths = _paths()
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-01"):
            _seed_task(paths, "confirm dependency state", status="blocked")
            notes = task_records.personal_task_notes(paths)
        self.assertTrue(any("Blockers and assumptions: none" in note for note in notes))

    def test_stale_record_is_flagged_past_the_cutoff(self) -> None:
        paths = _paths()
        path = paths.owner_task_dir("dana") / "2025-01-01-old.md"
        path.parent.mkdir(parents=True)
        path.write_text(
            "# Task: old\n\nStatus: active\nOwner: dana\nUpdated: 2025-01-01\n\n"
            "## Goal\n\nx\n\n## Readiness\n\n- Blockers and assumptions: none\n\n"
            "## Step State\n\n- Active step: doing it\n",
            encoding="utf-8",
        )
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-01"):
            notes = task_records.personal_task_notes(paths)
        self.assertTrue(any("not updated since 2025-01-01" in note for note in notes))

    def test_configured_stale_days_affects_notes(self) -> None:
        paths = _paths()
        path = _seed_task(paths, "doing it")
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-04"):
            default_notes = task_records.personal_task_notes(paths)
            tighter_notes = task_records.personal_task_notes(paths, stale_days=2)
        self.assertFalse(any("not updated since 2026-01-01" in note for note in default_notes))
        self.assertTrue(any(f"{task_records.display_path(path, paths.root)}: not updated since 2026-01-01" in note for note in tighter_notes))


class PruneEmptyOwnerDirTests(unittest.TestCase):
    def test_removes_owner_directory_once_empty(self) -> None:
        paths = _paths()
        owner_dir = paths.owner_task_dir("dana")
        owner_dir.mkdir(parents=True)
        task_records.prune_empty_owner_dir(owner_dir, paths)
        self.assertFalse(owner_dir.exists())

    def test_leaves_non_empty_owner_directory_alone(self) -> None:
        paths = _paths()
        owner_dir = paths.owner_task_dir("dana")
        owner_dir.mkdir(parents=True)
        (owner_dir / "task.md").write_text("x\n", encoding="utf-8")
        task_records.prune_empty_owner_dir(owner_dir, paths)
        self.assertTrue(owner_dir.exists())


if __name__ == "__main__":
    unittest.main()
