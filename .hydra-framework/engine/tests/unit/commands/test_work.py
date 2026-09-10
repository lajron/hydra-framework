"""Mirror test for `hydra_engine.commands.work`."""

from __future__ import annotations

import argparse
import contextlib
import io as stdlib_io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hydra_engine.commands import work  # noqa: E402
from hydra_engine.work.paths import WorkPaths  # noqa: E402

TASK_TEMPLATE = (
    "# Task: <short-name>\n\nStatus: active\nOwner: unassigned\nCreated: YYYY-MM-DD\n"
    "Updated: YYYY-MM-DD\n\n## Goal\n\nDescribe the engineering objective.\n"
)
CHECKPOINT_TEMPLATE = "# Checkpoint: <task-name>\n\nTask: <link-or-name>\nCreated: YYYY-MM-DD\n"


def _paths() -> WorkPaths:
    root = Path(tempfile.mkdtemp(prefix="commands-work-"))
    paths = WorkPaths(root=root, hydra=root / ".hydra-framework", local=root / ".hydra-framework.local")
    templates = paths.hydra / "tasks/templates"
    templates.mkdir(parents=True)
    (templates / "task.md").write_text(TASK_TEMPLATE, encoding="utf-8")
    (templates / "checkpoint.md").write_text(CHECKPOINT_TEMPLATE, encoding="utf-8")
    return paths


def _run(func, *args):
    out = stdlib_io.StringIO()
    with contextlib.redirect_stdout(out):
        result = func(*args)
    return result, out.getvalue()


def _init_git(paths: WorkPaths) -> None:
    subprocess.run(["git", "init", "-q"], cwd=str(paths.root), check=True)


def _git_add(paths: WorkPaths, *items: Path) -> None:
    rels = [item.relative_to(paths.root).as_posix() for item in items]
    subprocess.run(["git", "add", "--", *rels], cwd=str(paths.root), check=True)


def _git_ls_files(paths: WorkPaths) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=str(paths.root),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def _task_args(path: Path, **overrides):
    values = {"task": str(path), "owner": "", "force": False}
    values.update(overrides)
    return argparse.Namespace(**values)


class CommandTaskStartTests(unittest.TestCase):
    def test_creates_a_task_record(self) -> None:
        paths = _paths()
        _init_git(paths)
        args = argparse.Namespace(owner="", name="fixture task", goal="Do the fixture thing.", force=False)
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-01"):
            result, out = _run(work.command_task_start, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Created task:", out)
        self.assertIn("Staged task for Git tracking:", out)
        created = paths.owner_task_dir("dana") / "2026-01-01-fixture-task.md"
        self.assertTrue(created.exists())
        self.assertIn("Owner: dana", created.read_text(encoding="utf-8"))
        self.assertIn(".hydra-framework/tasks/personal/dana/2026-01-01-fixture-task.md", _git_ls_files(paths))

    def test_does_not_claim_tracking_when_git_staging_fails(self) -> None:
        paths = _paths()
        args = argparse.Namespace(owner="", name="fixture task", goal="Do the fixture thing.", force=False)
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-01"):
            result, out = _run(work.command_task_start, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Task record is not staged for Git tracking.", out)
        self.assertNotIn("This record is tracked.", out)

    def test_refuses_to_overwrite_without_force(self) -> None:
        paths = _paths()
        args = argparse.Namespace(owner="", name="fixture-task", goal="", force=False)
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-01"):
            _run(work.command_task_start, args, paths, "dana", "")
            result, out = _run(work.command_task_start, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("already exists", out)


class CommandTaskCheckpointTests(unittest.TestCase):
    def test_creates_a_checkpoint_and_touches_the_task(self) -> None:
        paths = _paths()
        _init_git(paths)
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Status: active\n", encoding="utf-8")
        _git_add(paths, task)
        args = _task_args(Path("x"))
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-02"):
            result, out = _run(work.command_task_checkpoint, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Created checkpoint:", out)
        self.assertIn("Staged checkpoint and task update", out)
        self.assertIn("Updated: 2026-01-02", task.read_text(encoding="utf-8"))
        self.assertIn(".hydra-framework/tasks/personal/dana/checkpoints/2026-01-02-x-checkpoint.md", _git_ls_files(paths))

    def test_missing_task_is_a_refusal(self) -> None:
        paths = _paths()
        args = argparse.Namespace(task="nope.md", owner="", force=False)
        result, out = _run(work.command_task_checkpoint, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Task not found", out)

    def test_refuses_to_checkpoint_another_owners_task_without_force(self) -> None:
        paths = _paths()
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: dana\n", encoding="utf-8")
        args = _task_args(task)
        result, out = _run(work.command_task_checkpoint, args, paths, "reed", "")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Refusing to edit dana's task as reed", out)
        self.assertFalse((task.parent / "checkpoints").exists())

    def test_force_allows_checkpointing_another_owners_task(self) -> None:
        paths = _paths()
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: dana\n", encoding="utf-8")
        args = _task_args(task, force=True)
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-02"):
            result, out = _run(work.command_task_checkpoint, args, paths, "reed", "")
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Created checkpoint:", out)
        self.assertTrue((task.parent / "checkpoints" / "2026-01-02-x-checkpoint.md").exists())


class CommandTaskHandoffTests(unittest.TestCase):
    def test_reassigns_owner_and_moves_checkpoints(self) -> None:
        paths = _paths()
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: dana\n", encoding="utf-8")
        checkpoint = task.parent / "checkpoints" / "2026-01-02-x-checkpoint.md"
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_text("x\n", encoding="utf-8")
        args = _task_args(Path("x"), to="reed")
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-03"):
            result, out = _run(work.command_task_handoff, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 0)
        destination = paths.owner_task_dir("reed") / "2026-01-01-x.md"
        self.assertTrue(destination.exists())
        self.assertIn("Owner: reed", destination.read_text(encoding="utf-8"))
        self.assertTrue((destination.parent / "checkpoints" / checkpoint.name).exists())
        self.assertFalse(task.exists())

    def test_refuses_when_destination_already_exists_with_unrelated_content(self) -> None:
        # A genuine name collision, distinct from a rerun of this exact
        # handoff (see test_rerun_completes_an_interrupted_handoff below):
        # the destination's content does not match what this handoff would
        # produce from the still-present source, so it is refused rather
        # than silently overwritten.
        paths = _paths()
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: dana\nsource goal\n", encoding="utf-8")
        existing = paths.owner_task_dir("reed") / "2026-01-01-x.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("Owner: reed\nunrelated goal\n", encoding="utf-8")
        args = _task_args(task, to="reed")
        result, out = _run(work.command_task_handoff, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("already exists", out)
        self.assertEqual("Owner: reed\nunrelated goal\n", existing.read_text(encoding="utf-8"))
        self.assertTrue(task.exists())

    def test_rerun_completes_an_interrupted_handoff(self) -> None:
        # Simulates a crash after the destination task was written but
        # before the source checkpoint/task deletes ran: the destination
        # already holds exactly what this handoff would (re)produce from the
        # still-present source, so a rerun finishes the job instead of
        # refusing it as a collision.
        paths = _paths()
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: dana\n", encoding="utf-8")
        checkpoint = task.parent / "checkpoints" / "2026-01-02-x-checkpoint.md"
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_text("x\n", encoding="utf-8")
        destination = paths.owner_task_dir("reed") / "2026-01-01-x.md"
        destination.parent.mkdir(parents=True)
        destination.write_text("Owner: reed\n", encoding="utf-8")
        args = _task_args(task, to="reed")
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-03"):
            result, out = _run(work.command_task_handoff, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Handed off to reed", out)
        self.assertFalse(task.exists())
        self.assertFalse(checkpoint.exists())
        self.assertTrue((destination.parent / "checkpoints" / checkpoint.name).exists())

    def test_force_does_not_clobber_destination_task(self) -> None:
        paths = _paths()
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: dana\nsource\n", encoding="utf-8")
        existing = paths.owner_task_dir("reed") / "2026-01-01-x.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("Owner: reed\nunrelated\n", encoding="utf-8")
        args = _task_args(task, to="reed", force=True)
        result, out = _run(work.command_task_handoff, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("already exists", out)
        self.assertTrue(task.exists())
        self.assertEqual("Owner: reed\nunrelated\n", existing.read_text(encoding="utf-8"))

    def test_refuses_to_handoff_another_owners_task_without_force(self) -> None:
        paths = _paths()
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: dana\n", encoding="utf-8")
        args = _task_args(task, to="reed")
        result, out = _run(work.command_task_handoff, args, paths, "mira", "")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Refusing to edit dana's task as mira", out)
        self.assertTrue(task.exists())

    def test_force_allows_handoff_of_another_owners_task(self) -> None:
        paths = _paths()
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: dana\n", encoding="utf-8")
        args = _task_args(task, to="reed", force=True)
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-03"):
            result, out = _run(work.command_task_handoff, args, paths, "mira", "")
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Handed off to reed", out)
        self.assertFalse(task.exists())
        self.assertTrue((paths.owner_task_dir("reed") / "2026-01-01-x.md").exists())

    def test_missing_task_is_a_refusal(self) -> None:
        paths = _paths()
        args = argparse.Namespace(task="nope.md", to="reed", owner="", force=False)
        result, out = _run(work.command_task_handoff, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Task not found", out)


class CommandTaskCompleteTests(unittest.TestCase):
    def test_removes_the_task_record(self) -> None:
        paths = _paths()
        _init_git(paths)
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: dana\n", encoding="utf-8")
        _git_add(paths, task)
        args = _task_args(Path("x"), outcome="none")
        result, out = _run(work.command_task_complete, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 0)
        self.assertFalse(task.exists())
        self.assertIn("Completed and removed:", out)
        self.assertIn("Staged completed task deletion for Git.", out)
        self.assertIn("Git status after completion:", out)
        self.assertIn("Next: review `git status`, then commit.", out)

    def test_refuses_to_complete_untracked_task_record(self) -> None:
        paths = _paths()
        _init_git(paths)
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: dana\n", encoding="utf-8")
        args = _task_args(task, outcome="none")
        result, out = _run(work.command_task_complete, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 1)
        self.assertTrue(task.exists())
        self.assertIn("not tracked by Git", out)
        self.assertNotIn("Staged completed task deletion", out)

    def test_refuses_to_complete_task_with_unstaged_changes(self) -> None:
        paths = _paths()
        _init_git(paths)
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: dana\n", encoding="utf-8")
        _git_add(paths, task)
        task.write_text("Owner: dana\nUpdated: 2026-01-02\n", encoding="utf-8")
        args = _task_args(task, outcome="none")
        result, out = _run(work.command_task_complete, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 1)
        self.assertTrue(task.exists())
        self.assertIn("unstaged changes Git cannot recover", out)

    def test_checkpoint_must_be_recoverable_before_completion_deletes_it(self) -> None:
        paths = _paths()
        _init_git(paths)
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: dana\n", encoding="utf-8")
        checkpoint = task.parent / "checkpoints" / "2026-01-02-x-checkpoint.md"
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_text("# Checkpoint: x\n", encoding="utf-8")
        _git_add(paths, task)

        args = _task_args(task, outcome="none")
        result, out = _run(work.command_task_complete, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 1)
        self.assertTrue(task.exists())
        self.assertTrue(checkpoint.exists())
        self.assertIn("checkpoints/2026-01-02-x-checkpoint.md: not tracked by Git", out)

        _git_add(paths, task, checkpoint)
        result, out = _run(work.command_task_complete, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 0)
        self.assertFalse(task.exists())
        self.assertFalse(checkpoint.exists())
        self.assertIn("Staged completed task deletion for Git.", out)
        self.assertIn("Git status after completion:", out)

    def test_missing_task_is_a_refusal(self) -> None:
        paths = _paths()
        args = argparse.Namespace(task="nope.md", owner="", force=False, outcome="none")
        result, out = _run(work.command_task_complete, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Task not found", out)

    def test_refuses_when_outcome_does_not_exist(self) -> None:
        paths = _paths()
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: dana\n", encoding="utf-8")
        args = _task_args(task, outcome="no/such/file.md")
        result, out = _run(work.command_task_complete, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Outcome does not exist", out)
        self.assertTrue(task.exists())

    def test_refuses_when_outcome_is_private_local_state(self) -> None:
        paths = _paths()
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: dana\n", encoding="utf-8")
        outcome = paths.local / "notes/outcome.md"
        outcome.parent.mkdir(parents=True)
        outcome.write_text("private\n", encoding="utf-8")
        args = _task_args(task, outcome=".hydra-framework.local/notes/outcome.md")
        result, out = _run(work.command_task_complete, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("not a durable shared/source artifact", out)
        self.assertTrue(task.exists())

    def test_refuses_to_complete_another_owners_task_without_force(self) -> None:
        paths = _paths()
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: dana\n", encoding="utf-8")
        args = _task_args(task, outcome="none")
        result, out = _run(work.command_task_complete, args, paths, "reed", "")
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Refusing to edit dana's task as reed", out)
        self.assertTrue(task.exists())

    def test_force_allows_completing_another_owners_task(self) -> None:
        paths = _paths()
        _init_git(paths)
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Owner: dana\n", encoding="utf-8")
        _git_add(paths, task)
        args = _task_args(task, outcome="none", force=True)
        result, out = _run(work.command_task_complete, args, paths, "reed", "")
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Completed and removed:", out)
        self.assertFalse(task.exists())


class CommandBoardTests(unittest.TestCase):
    def test_no_records_reports_the_empty_board(self) -> None:
        paths = _paths()
        args = argparse.Namespace(owner="", json=False)
        result, out = _run(work.command_board, args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("no active task records", out)

    def test_json_output_is_a_list_of_summaries(self) -> None:
        paths = _paths()
        task = paths.owner_task_dir("dana") / "2026-01-01-x.md"
        task.parent.mkdir(parents=True)
        task.write_text("Status: active\nOwner: dana\nUpdated: 2026-01-01\n\n## Goal\n\nx\n", encoding="utf-8")
        args = argparse.Namespace(owner="", json=True)
        result, out = _run(work.command_board, args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn('"owner": "dana"', out)

    def test_blocked_filters_to_blocked_records(self) -> None:
        paths = _paths()
        active = paths.owner_task_dir("dana") / "2026-01-01-a.md"
        active.parent.mkdir(parents=True)
        active.write_text("Status: active\nOwner: dana\nUpdated: 2026-01-01\n\n## Goal\n\nx\n", encoding="utf-8")
        blocked = paths.owner_task_dir("reed") / "2026-01-01-b.md"
        blocked.parent.mkdir(parents=True)
        blocked.write_text("Status: blocked\nOwner: reed\nUpdated: 2026-01-01\n\n## Goal\n\nx\n", encoding="utf-8")
        args = argparse.Namespace(owner="", json=True, blocked=True, stale=None)
        result, out = _run(work.command_board, args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertIn('"owner": "reed"', out)
        self.assertNotIn('"owner": "dana"', out)


class CommandNoteTests(unittest.TestCase):
    def test_title_creates_a_named_note_file(self) -> None:
        paths = _paths()
        args = argparse.Namespace(text=["hello", "world"])
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-01"):
            result, _out = _run(work.command_note, args, paths)
        self.assertEqual(result.exit_code, 0)
        note_path = paths.local_notes_dir() / "2026-01-01-hello-world.md"
        self.assertEqual("# hello world\n\n", note_path.read_text(encoding="utf-8"))

    def test_stdin_only_appends_to_daily_scratch_note(self) -> None:
        paths = _paths()
        args = argparse.Namespace(text=[])
        with (
            mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-01"),
            mock.patch("sys.stdin", stdlib_io.StringIO("hello world")),
        ):
            result, _out = _run(work.command_note, args, paths)
        self.assertEqual(result.exit_code, 0)
        note_path = paths.local_notes_dir() / "2026-01-01.md"
        self.assertIn("- hello world", note_path.read_text(encoding="utf-8"))

    def test_title_note_does_not_overwrite_existing_file(self) -> None:
        paths = _paths()
        note_path = paths.local_notes_dir() / "2026-01-01-hello-world.md"
        note_path.parent.mkdir(parents=True)
        note_path.write_text("# Existing\n\nbody\n", encoding="utf-8")
        args = argparse.Namespace(text=["hello", "world"])
        with mock.patch("hydra_engine.ports.clock.today", return_value="2026-01-01"):
            result, _out = _run(work.command_note, args, paths)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual("# Existing\n\nbody\n", note_path.read_text(encoding="utf-8"))

    def test_empty_text_is_a_refusal(self) -> None:
        paths = _paths()
        args = argparse.Namespace(text=[])
        with mock.patch("sys.stdin", stdlib_io.StringIO("")):
            result, _out = _run(work.command_note, args, paths)
        self.assertEqual(result.exit_code, 1)


class CommandMigrateStateTests(unittest.TestCase):
    def test_nothing_to_migrate_is_a_clean_no_op(self) -> None:
        paths = _paths()
        args = argparse.Namespace(apply=False, force=False)
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            result, out = _run(work.command_migrate_state, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 0)
        self.assertIn("nothing to migrate", out)

    def test_apply_moves_files_and_cleans_up_source_directories(self) -> None:
        paths = _paths()
        source = paths.hydra / "tasks/active/2026-01-01-x.md"
        source.parent.mkdir(parents=True)
        source.write_text("Status: active\nOwner: dana\n", encoding="utf-8")
        args = argparse.Namespace(apply=True, force=False)
        with mock.patch("hydra_engine.ports.git.tracked_files", return_value=[]):
            result, _out = _run(work.command_migrate_state, args, paths, "dana", "")
        self.assertEqual(result.exit_code, 0)
        self.assertTrue((paths.owner_task_dir("dana") / "2026-01-01-x.md").exists())
        self.assertFalse(source.exists())
        self.assertFalse((paths.hydra / "tasks/active").exists())


if __name__ == "__main__":
    unittest.main()
