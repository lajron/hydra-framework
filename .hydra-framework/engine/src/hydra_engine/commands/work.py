"""work commands: task start/checkpoint/handoff/complete, board, note, migrate-state."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from hydra_engine.commands import CommandResult
from hydra_engine.documents.tokens import display_path, read_text, write_text
from hydra_engine.identity.slugs import slugify
from hydra_engine.ports import clock
from hydra_engine.work import board, migration
from hydra_engine.work.owners import HydraOwnerError, resolve_owner
from hydra_engine.work.task_records import (
    append_state_line,
    prune_empty_owner_dir,
    resolve_task_record,
    stage_task_state_file,
    task_owner_write_refusal_lines,
    task_outcome_refusal_lines,
    task_completion_git_status_lines,
    task_completion_staging_lines,
    task_state_git_path,
    task_name_from_path,
    touch_task_updated,
    unrecoverable_task_state_paths,
    write_new_state_file,
)

# `Updated:` is normalized out before comparing a would-be handoff write
# against an existing destination, distinguishing a rerun of this exact
# handoff (see `command_task_handoff`) from a genuine name collision.
_UPDATED_LINE_RE = re.compile(r"^Updated:.*$", flags=re.MULTILINE)

# `paths: WorkPaths` below is a type-hint-only reference (no import), matching
# the codebase-wide convention for per-area location dataclasses (see
# `objects/envelopes.py`'s use of `ObjectLocations` the same way).


def _print_unstaged_creation(path: Path, paths: WorkPaths, noun: str) -> None:
    rel = task_state_git_path(path, paths)
    print(f"{noun} is not staged for Git tracking.")
    print(f"Stage it with: git add -- {rel}")


def _task_owner_write_allowed(task: Path, paths: WorkPaths, caller_owner: str, force: bool) -> bool:
    lines = task_owner_write_refusal_lines(task, paths, caller_owner, force)
    for line in lines:
        print(line)
    return not lines


def command_task_start(args, paths: WorkPaths, env_owner: str, git_email: str) -> CommandResult:
    owner = resolve_owner(args.owner, env_owner, git_email)
    name = slugify(args.name)
    path = paths.owner_task_dir(owner) / f"{clock.today()}-{name}.md"

    template = read_text(paths.hydra / "tasks/templates/task.md")
    content = (
        template.replace("<short-name>", name)
        .replace("Owner: unassigned", f"Owner: {owner}")
        .replace("Created: YYYY-MM-DD", f"Created: {clock.today()}")
        .replace("Updated: YYYY-MM-DD", f"Updated: {clock.today()}")
        .replace("Describe the engineering objective.", args.goal or "Describe the engineering objective.")
    )
    if not write_new_state_file(path, content, force=args.force):
        print(f"Task already exists: {display_path(path, paths.root)}")
        return CommandResult(1)
    print(f"Created task: {display_path(path, paths.root)}")
    if stage_task_state_file(path, paths):
        print(f"Staged task for Git tracking: {task_state_git_path(path, paths)}")
    else:
        _print_unstaged_creation(path, paths, "Task record")
    print("Keep private thinking in .hydra-framework.local/notes/.")
    return CommandResult(0)


def command_task_checkpoint(args, paths: WorkPaths, env_owner: str, git_email: str) -> CommandResult:
    caller_owner = resolve_owner(args.owner, env_owner, git_email)
    task, resolution_lines = resolve_task_record(args.task, paths, caller_owner)
    if task is None:
        for line in resolution_lines:
            print(line)
        return CommandResult(1)
    if not _task_owner_write_allowed(task, paths, caller_owner, args.force):
        return CommandResult(1)

    name = task_name_from_path(task)
    path = task.parent / "checkpoints" / f"{clock.today()}-{name}-checkpoint.md"

    template = read_text(paths.hydra / "tasks/templates/checkpoint.md")
    content = (
        template.replace("<task-name>", name)
        .replace("Task: <link-or-name>", f"Task: {display_path(task, paths.root)}")
        .replace("Created: YYYY-MM-DD", f"Created: {clock.today()}")
    )
    if not write_new_state_file(path, content, force=args.force):
        print(f"Checkpoint already exists: {display_path(path, paths.root)}")
        return CommandResult(1)
    write_text(task, touch_task_updated(read_text(task)))
    print(f"Created checkpoint: {display_path(path, paths.root)}")
    if stage_task_state_file(task, paths) and stage_task_state_file(path, paths):
        print("Staged checkpoint and task update for Git tracking.")
    else:
        print("Checkpoint and task update are not fully staged for Git tracking.")
        print(f"Stage them with: git add -- {task_state_git_path(task, paths)} {task_state_git_path(path, paths)}")
    return CommandResult(0)


def command_task_handoff(args, paths: WorkPaths, env_owner: str, git_email: str) -> CommandResult:
    caller_owner = resolve_owner(args.owner, env_owner, git_email)
    task, resolution_lines = resolve_task_record(args.task, paths, caller_owner)
    if task is None:
        for line in resolution_lines:
            print(line)
        return CommandResult(1)
    if not _task_owner_write_allowed(task, paths, caller_owner, args.force):
        return CommandResult(1)

    new_owner = slugify(args.to)
    destination = paths.owner_task_dir(new_owner) / task.name
    if destination == task:
        print(f"Task is already owned by {new_owner}: {display_path(task, paths.root)}")
        return CommandResult(1)

    content = touch_task_updated(re.sub(r"^Owner:.*$", f"Owner: {new_owner}", read_text(task), count=1, flags=re.MULTILINE))
    if destination.exists() and _UPDATED_LINE_RE.sub("", read_text(destination)) != _UPDATED_LINE_RE.sub("", content):
        print(f"Task already exists for {new_owner}: {display_path(destination, paths.root)}")
        return CommandResult(1)

    # Write every destination file before deleting any source: a crash here
    # leaves both copies present, and rerunning this command finishes the
    # job via the guard above.
    write_text(destination, content)
    checkpoints = sorted((task.parent / "checkpoints").glob(f"*-{task_name_from_path(task)}-checkpoint.md"))
    for checkpoint in checkpoints:
        write_text(destination.parent / "checkpoints" / checkpoint.name, read_text(checkpoint))

    for checkpoint in checkpoints:
        checkpoint.unlink()
    task.unlink()
    prune_empty_owner_dir(task.parent, paths)
    print(f"Handed off to {new_owner}: {display_path(destination, paths.root)}")
    for checkpoint in checkpoints:
        print(f"Moved checkpoint: {display_path(destination.parent / 'checkpoints' / checkpoint.name, paths.root)}")
    print("Tell them directly too. A moved file is not a conversation.")
    return CommandResult(0)


def command_task_complete(args, paths: WorkPaths, env_owner: str, git_email: str) -> CommandResult:
    caller_owner = resolve_owner(args.owner, env_owner, git_email)
    task, resolution_lines = resolve_task_record(args.task, paths, caller_owner)
    if task is None:
        for line in resolution_lines:
            print(line)
        return CommandResult(1)
    if not _task_owner_write_allowed(task, paths, caller_owner, args.force):
        return CommandResult(1)

    outcome = args.outcome.strip()
    if outcome.lower() != "none":
        outcome_refusal = task_outcome_refusal_lines(outcome, paths)
        if outcome_refusal:
            for line in outcome_refusal:
                print(line)
            print("Name the knowledge file, rule, or module this work produced,")
            print("or pass `--outcome none` if it produced no durable artifact.")
            return CommandResult(1)

    checkpoints = sorted((task.parent / "checkpoints").glob(f"*-{task_name_from_path(task)}-checkpoint.md"))
    recoverability_problems = unrecoverable_task_state_paths(paths, [task] + checkpoints)
    if recoverability_problems:
        print("Cannot complete because Git cannot recover the current task state:")
        for rel, reason in recoverability_problems:
            print(f"- {rel}: {reason}")
        print("Stage the current task record and checkpoints, or retire them deliberately, then retry.")
        return CommandResult(1)

    for checkpoint in checkpoints:
        checkpoint.unlink()
    task.unlink()
    prune_empty_owner_dir(task.parent, paths)

    print(f"Completed and removed: {display_path(task, paths.root)}")
    for checkpoint in checkpoints:
        print(f"Removed checkpoint: {display_path(checkpoint, paths.root)}")
    for line in task_completion_staging_lines(paths, [task] + checkpoints):
        print(line)
    if outcome.lower() == "none":
        print("Outcome: none recorded.")
    else:
        print(f"Outcome: {outcome}")
    for line in task_completion_git_status_lines(paths):
        print(line)
    return CommandResult(0)


def command_board(args, paths: WorkPaths) -> CommandResult:
    owner_filter = slugify(args.owner) if args.owner else None
    summaries = board.board_rows(paths, owner_filter, getattr(args, "blocked", False), getattr(args, "stale", None))

    if not summaries:
        print("Hydra board: no active task records.")
        return CommandResult(0)

    if args.json:
        print(json.dumps(summaries, indent=2))
        return CommandResult(0)

    checkpoint_owners = board.checkpoint_counts_by_owner(paths)
    current = ""
    for item in sorted(summaries, key=lambda row: (row["owner"], row["updated"])):
        if item["owner"] != current:
            current = item["owner"]
            extra = f" ({checkpoint_owners.get(current, 0)} checkpoint(s))" if checkpoint_owners.get(current) else ""
            print(f"\n{current}{extra}")
        updated = item["updated"] or "no date"
        print(f"  [{item['status']}] {item['name']} — updated {updated}")
        if item["goal"]:
            print(f"    {item['goal']}")
        print(f"    {item['path']}")
    return CommandResult(0)


def command_note(args, paths: WorkPaths) -> CommandResult:
    """Create a titled private note, or append stdin-only scratch.

    Capture has to cost little or it does not happen, but named notes need a
    recoverable filename. Arguments name a dated note file; stdin-only input
    remains the zero-ceremony daily scratch path.
    """
    if args.text:
        title = " ".join(args.text).strip()
        if not title:
            print("Nothing to note.", file=sys.stderr)
            return CommandResult(1)
        path = paths.local_notes_dir() / f"{clock.today()}-{slugify(title)}.md"
        write_new_state_file(path, f"# {title}\n\n")
        print(f"Noted in {display_path(path, paths.root)}")
        return CommandResult(0)

    scratch = sys.stdin.read().strip()
    if not scratch:
        print("Nothing to note.", file=sys.stderr)
        return CommandResult(1)
    # Append-only: two concurrent scratch notes each land as their own bullet
    # rather than one clobbering the other's read-modify-write of the whole
    # file.
    path = paths.local_notes_dir() / f"{clock.today()}.md"
    write_new_state_file(path, f"# Notes {clock.today()}\n")
    append_state_line(path, f"\n- {scratch}")
    print(f"Noted in {display_path(path, paths.root)}")
    return CommandResult(0)


def command_migrate_state(args, paths: WorkPaths, env_owner: str, git_email: str) -> CommandResult:
    """Move existing state into the tiers the placement rules define."""
    try:
        plan = migration.plan_state_migration(paths, env_owner, git_email)
    except HydraOwnerError as error:
        print(str(error), file=sys.stderr)
        return CommandResult(1)

    moves = plan["move"] + plan["retire"]
    deletes = plan["delete"]
    drops = plan["drop"]
    if not moves and not deletes and not drops:
        print("Hydra migrate-state: nothing to migrate; state already matches the placement rules.")
        return CommandResult(0)

    print(
        f"Hydra migrate-state: {len(plan['move'])} move(s), {len(deletes)} deletion(s), "
        f"{len(plan['retire'])} retired to private staging, {len(drops)} README drop(s)"
    )
    for source, destination in plan["move"]:
        print(f"  move   {display_path(source, paths.root)} -> {display_path(destination, paths.root)}")
    for source, _ in deletes:
        print(f"  delete {display_path(source, paths.root)}")
    for source, destination in plan["retire"]:
        print(f"  retire {display_path(source, paths.root)} -> {display_path(destination, paths.root)}")
    for source, _ in drops:
        print(f"  drop   {display_path(source, paths.root)} (documents a directory that no longer exists)")

    if deletes:
        print("")
        print(f"The {len(deletes)} deleted record(s) are finished work Git already tracks.")
        print("History keeps them: `git log --diff-filter=D -- <path>`.")
    if plan["retire"]:
        print("")
        print(f"The {len(plan['retire'])} retired record(s) are NOT in Git, so the working copy")
        print("is the only copy. They move to private staging rather than being deleted.")

    if not args.apply:
        print("")
        print("Dry run. Re-run with --apply to perform it.")
        return CommandResult(0)

    conflicts = migration.migration_destination_conflicts(moves, paths)
    if conflicts and not args.force:
        print("")
        print("Hydra migrate-state: destination conflict(s); nothing was changed.")
        for conflict in conflicts:
            print(f"- {conflict}")
        print("Move or inspect the destination files, or re-run with --force to overwrite them.")
        return CommandResult(1)

    for source, destination in moves:
        write_text(destination, read_text(source))
        source.unlink()
    for source, _ in deletes + drops:
        source.unlink()

    migration.cleanup_after_apply(paths)

    print("")
    print(f"Migrated {len(moves)} file(s); removed {len(deletes)} finished record(s).")
    print("Next: review `git status`, then commit. Private files are already ignored.")
    return CommandResult(0)


def register(subparsers) -> None:
    """Add task start/checkpoint/handoff/complete, board, note, and
    migrate-state."""
    board_parser = subparsers.add_parser("board", help="Show who is working on what, computed from task records")
    board_parser.add_argument("--owner", default="", help="Limit to one owner")
    board_parser.add_argument("--blocked", action="store_true", help="Limit to records with Status: blocked")
    board_parser.add_argument("--stale", type=int, default=None, metavar="DAYS", help="Limit to records not updated in this many days")
    board_parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    board_parser.set_defaults(func=_dispatch_board)

    note = subparsers.add_parser("note", help="Create a titled private note, or append stdin-only scratch")
    note.add_argument("text", nargs="*", help="Note title; omit to append stdin to today's scratch note")
    note.set_defaults(func=_dispatch_note)

    migrate = subparsers.add_parser("migrate-state", help="Move existing state into the tiers the placement rules define")
    migrate.add_argument("--apply", action="store_true", help="Perform the migration instead of reporting it")
    migrate.add_argument("--force", action="store_true", help="Allow overwriting existing migration destinations")
    migrate.set_defaults(func=_dispatch_migrate_state)

    task = subparsers.add_parser("task", help="Maintain Hydra task records")
    task_sub = task.add_subparsers(dest="task_command", required=True)

    start = task_sub.add_parser("start", help="Create an active task record under your owner directory")
    start.add_argument("name")
    start.add_argument("--goal", default="")
    start.add_argument("--owner", default="", help="Override the resolved owner slug")
    start.add_argument("--force", action="store_true")
    start.set_defaults(func=_dispatch_task_start)

    checkpoint = task_sub.add_parser("checkpoint", help="Create a checkpoint beside a task record")
    checkpoint.add_argument("task")
    checkpoint.add_argument("--owner", default="", help="Override the resolved caller owner slug")
    checkpoint.add_argument("--force", action="store_true")
    checkpoint.set_defaults(func=_dispatch_task_checkpoint)

    handoff = task_sub.add_parser("handoff", help="Reassign a task record to another owner")
    handoff.add_argument("task")
    handoff.add_argument("--to", required=True, help="Owner slug taking the work")
    handoff.add_argument("--owner", default="", help="Override the resolved caller owner slug")
    handoff.add_argument("--force", action="store_true")
    handoff.set_defaults(func=_dispatch_task_handoff)

    complete = task_sub.add_parser("complete", help="Finish a task and remove its record; Git history is the archive")
    complete.add_argument("task")
    complete.add_argument("--outcome", required=True, help="Path to the durable artifact this produced, or `none`")
    complete.add_argument("--owner", default="", help="Override the resolved caller owner slug")
    complete.add_argument("--force", action="store_true")
    complete.set_defaults(func=_dispatch_task_complete)


def _dispatch_board(args, ctx) -> int:
    return command_board(args, ctx.work_paths()).exit_code


def _dispatch_note(args, ctx) -> int:
    return command_note(args, ctx.work_paths()).exit_code


def _dispatch_migrate_state(args, ctx) -> int:
    return command_migrate_state(args, ctx.work_paths(), ctx.env_owner(), ctx.git_email()).exit_code


def _dispatch_task_start(args, ctx) -> int:
    return command_task_start(args, ctx.work_paths(), ctx.env_owner(), ctx.git_email()).exit_code


def _dispatch_task_checkpoint(args, ctx) -> int:
    return command_task_checkpoint(args, ctx.work_paths(), ctx.env_owner(), ctx.git_email()).exit_code


def _dispatch_task_handoff(args, ctx) -> int:
    return command_task_handoff(args, ctx.work_paths(), ctx.env_owner(), ctx.git_email()).exit_code


def _dispatch_task_complete(args, ctx) -> int:
    return command_task_complete(args, ctx.work_paths(), ctx.env_owner(), ctx.git_email()).exit_code
